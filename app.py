import os
import sys
from datetime import date, timedelta
from pathlib import Path
import dash_ag_grid as dag
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html
from demeter.carbon import credit_scenario, enrich_carbon
from demeter.climate import fetch_open_meteo
from demeter.figures import (DEMETER_COLORS, COLOR_SCALE, fig_anomaly, fig_climate, fig_co2_by_stand,
    fig_credit_waterfall, fig_dap_height, fig_diameter_distribution, fig_species_donut, fig_tree_map,
    fig_volume_heatmap, style_figure)
from demeter.io import df_to_json, json_to_df, parse_upload
from demeter.metrics import filter_inventory, kpi_summary, prepare_inventory, species_summary, stand_summary
from demeter.ml import cluster_stands, detect_anomalies, train_volume_model
from demeter.schema import EXPECTED_COLUMNS, standardize_dataframe
from demeter.validation import quality_report, quality_score

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
app = Dash(__name__, suppress_callback_exceptions=True, assets_folder=str(BASE_DIR / "assets"), title="Demeter Dashboard")
server = app.server

DISPLAY_LABELS = {"Talhao":"Talhão","Parcela":"Parcela","Num_Arvore":"Árvore","Especie":"Espécie","DAP_cm":"DAP (cm)","Altura_m":"Altura (m)","Volume_m3":"Volume (m³)","Coord_X":"Coordenada X","Coord_Y":"Coordenada Y","Idade_anos":"Idade (anos)","DensidadeMadeira_t_m3":"Densidade da madeira (t/m³)","AreaBasal_m2":"Área basal (m²)","BiomassaFuste_t":"Biomassa do fuste (t)","BiomassaAcimaSolo_t":"Biomassa acima do solo (t)","BiomassaRaiz_t":"Biomassa de raízes (t)","BiomassaTotal_t":"Biomassa total (t)","Carbono_tC":"Carbono (tC)","CO2e_t":"CO₂e (t)","CO2e_Expandido_t":"CO₂e expandido (t)","Status_Anomalia":"Status de anomalia","Score_Anomalia":"Score de anomalia","Grupo_ML":"Grupo estatístico","DAP_medio":"DAP médio","Altura_media":"Altura média","Volume_Previsto_ML_m3":"Volume previsto pelo modelo (m³)","Erro_ML_m3":"Erro do modelo (m³)","Variavel":"Variável","Importancia":"Importância","Ausentes":"Valores ausentes","Coluna":"Coluna","Item":"Item","Status":"Status","Detalhe":"Detalhe","time":"Data","temperature_2m_mean":"Temperatura média (°C)","precipitation_sum":"Precipitação (mm)","et0_fao_evapotranspiration":"ET₀ FAO (mm)","vapour_pressure_deficit_max":"VPD máximo (kPa)","soil_moisture_0_to_7cm_mean":"Umidade do solo 0–7 cm"}

def nice_label(v): return DISPLAY_LABELS.get(str(v), str(v).replace("_"," "))
def fmt(v, decimals=2, suffix=""):
    try:
        if v is None or pd.isna(v) or not np.isfinite(float(v)): return "N/A"
    except Exception: return "N/A"
    return f"{float(v):,.{decimals}f}".replace(",","X").replace(".",",").replace("X",".") + suffix

def metric_card(title,value,subtitle="",tone=""):
    return html.Div(className="metric-card"+(f" metric-{tone}" if tone else ""), children=[html.Div(title,className="metric-title"),html.Div(value,className="metric-value"),html.Div(subtitle,className="metric-subtitle")])
def section_heading(title,subtitle): return html.Div(className="section-heading",children=[html.H2(title),html.P(subtitle)])
def module_card(tag,title,text): return html.Div(className="module-card",children=[html.Div(tag,className="module-tag"),html.H3(title),html.P(text)])
def parameter_group(title,children,open=False): return html.Details(className="parameter-group",open=open,children=[html.Summary(title),html.Div(className="parameter-group-body",children=children)])
def dropdown_options(values): return [{"label":str(v),"value":str(v)} for v in sorted(pd.Series(values).dropna().astype(str).unique())]
def make_grid(df,height="460px"):
    clean=pd.DataFrame() if df is None else df.replace([np.inf,-np.inf],np.nan).fillna("")
    defs=[{"field":c,"headerName":nice_label(c),"filter":True,"sortable":True,"resizable":True,"tooltipField":c} for c in clean.columns]
    return dag.AgGrid(columnDefs=defs,rowData=clean.to_dict("records"),defaultColDef={"filter":True,"sortable":True,"resizable":True,"floatingFilter":True},dashGridOptions={"pagination":True,"paginationPageSize":15,"animateRows":True},className="ag-theme-alpine-dark demeter-grid",style={"height":height,"width":"100%"})
def empty_state(title="Envie uma planilha para começar",text="O painel aceita arquivos CSV, XLSX e XLS de inventário florestal."):
    return html.Div(className="empty-state empty-state-large",children=[html.H3(title),html.P(text),html.Div(className="module-grid",children=[module_card("1","Carregar dados","Selecione a planilha do inventário ou utilize o arquivo de exemplo."),module_card("2","Conferir parâmetros","Revise área, fator de forma e parâmetros de carbono."),module_card("3","Analisar resultados","Consulte as abas de resumo, inventário, carbono, qualidade, modelagem e clima.")])])

app.layout=html.Div(className="app-shell",children=[dcc.Store(id="raw-store"),dcc.Store(id="processed-store"),
 html.Aside(className="sidebar",children=[html.Div(className="brand",children="DEMETER"),html.Div(className="brand-subtitle",children="Dashboard Florestal"),
  html.Div(className="sidebar-help",children=[html.Div("Etapas",className="sidebar-help-title"),html.Div("1. Envie a planilha"),html.Div("2. Confira os indicadores"),html.Div("3. Ajuste os parâmetros quando necessário")]),
  html.Div("Entrada de dados",className="sidebar-section-title"),dcc.Upload(id="upload-data",className="upload-box",children=html.Div([html.Div("Enviar CSV/XLSX",className="upload-title"),html.Div("Inventário florestal",className="upload-subtitle")]),multiple=False),html.Div(id="upload-status",className="upload-status",children="Nenhum arquivo carregado."),
  parameter_group("Filtros principais",[html.Label("Talhão"),dcc.Dropdown(id="filter-stand",multi=True,className="demeter-dropdown",placeholder="Todos"),html.Label("Espécie"),dcc.Dropdown(id="filter-species",multi=True,className="demeter-dropdown",placeholder="Todas"),html.Label("Status de anomalia"),dcc.Dropdown(id="filter-status",multi=True,className="demeter-dropdown",value=["Normal","Suspeito","Não avaliado"],options=[{"label":v,"value":v} for v in ["Normal","Suspeito","Não avaliado"]])],True),
  parameter_group("Inventário",[html.Label("Área do projeto (ha)"),dcc.Input(id="project-area",type="number",value=10,min=.01,step=.1,className="input"),html.Label("Área amostrada (ha)"),dcc.Input(id="sample-area",type="number",value=1,min=.01,step=.1,className="input"),html.Label("Fator de forma"),dcc.Input(id="form-factor",type="number",value=.42,min=.1,max=1,step=.01,className="input")]),
  parameter_group("Carbono",[html.Label("Densidade padrão (t/m³)"),dcc.Input(id="wood-density",type="number",value=.50,min=.1,max=1.2,step=.01,className="input"),html.Label("Fração de carbono"),dcc.Input(id="carbon-fraction",type="number",value=.47,min=.3,max=.7,step=.01,className="input"),html.Label("BEF — biomassa aérea"),dcc.Input(id="bef",type="number",value=1.20,min=1,max=3,step=.05,className="input"),html.Label("Razão raiz/parte aérea"),dcc.Input(id="root-ratio",type="number",value=.24,min=0,max=1,step=.01,className="input")]),
  parameter_group("Cenário de potencial",[html.Label("Baseline (%)"),dcc.Input(id="baseline",type="number",value=30,min=0,max=100,step=1,className="input"),html.Label("Leakage (%)"),dcc.Input(id="leakage",type="number",value=8,min=0,max=100,step=1,className="input"),html.Label("Buffer de risco (%)"),dcc.Input(id="buffer",type="number",value=15,min=0,max=100,step=1,className="input"),html.Label("Incerteza (%)"),dcc.Input(id="uncertainty",type="number",value=10,min=0,max=100,step=1,className="input"),html.Label("US$/tCO₂e"),dcc.Input(id="price-usd",type="number",value=12,min=0,step=1,className="input"),html.Label("Câmbio US$ → R$"),dcc.Input(id="usd-brl",type="number",value=5.40,min=1,step=.1,className="input")]),
  parameter_group("Modelagem",[html.Label("Sensibilidade a anomalias"),dcc.Input(id="contamination",type="number",value=.06,min=.01,max=.30,step=.01,className="input"),html.Label("Número de grupos"),dcc.Input(id="cluster-count",type="number",value=3,min=2,max=8,step=1,className="input")])]),
 html.Main(className="main",children=[html.Div(className="hero",children=[html.Div("INVENTÁRIO · CARBONO · QUALIDADE · MODELAGEM",className="eyebrow"),html.H1(["Demeter ",html.Span("Dashboard")]),html.P("Painel técnico para explorar inventários florestais, estimar biomassa e carbono, avaliar a qualidade dos dados e consultar séries climáticas.")]),html.Div(id="schema-bar"),html.Div(id="kpi-row",className="metrics-grid"),dcc.Tabs(id="tabs",value="overview",className="tabs",children=[dcc.Tab(label="Resumo",value="overview"),dcc.Tab(label="Inventário",value="inventory"),dcc.Tab(label="Carbono",value="carbon"),dcc.Tab(label="Qualidade",value="quality"),dcc.Tab(label="Modelagem",value="ml"),dcc.Tab(label="Clima",value="climate"),dcc.Tab(label="Tabelas",value="data")]),html.Div(id="tab-content",className="tab-content")])])

@app.callback(Output("raw-store","data"),Output("upload-status","children"),Output("filter-stand","options"),Output("filter-stand","value"),Output("filter-species","options"),Output("filter-species","value"),Output("schema-bar","children"),Input("upload-data","contents"),State("upload-data","filename"))
def load_file(contents,filename):
    if contents is None:
        schema=html.Div(className="schema-grid",children=[html.Div(className="schema-card",children=[html.Div("Status",className="schema-title"),html.Div("Aguardando",className="schema-value"),html.Div("Envie um arquivo para iniciar a análise.",className="schema-text")]),html.Div(className="schema-card",children=[html.Div("Colunas de referência",className="schema-title"),html.Div(str(len(EXPECTED_COLUMNS)),className="schema-value"),html.Div("DAP, altura, espécie, talhão, volume e coordenadas.",className="schema-text")]),html.Div(className="schema-card",children=[html.Div("Uso dos resultados",className="schema-title"),html.Div("Exploratório",className="schema-value"),html.Div("As estimativas não constituem certificação.",className="schema-text")])])
        return None,"Nenhum arquivo carregado.",[],[],[],[],schema
    try:
        df=parse_upload(contents,filename); df,_=standardize_dataframe(df)
        if "Talhao" not in df: df["Talhao"]="Projeto único"
        if "Especie" not in df: df["Especie"]="Não informada"
        found=[c for c in EXPECTED_COLUMNS if c in df]; missing=[c for c in EXPECTED_COLUMNS if c not in df]
        schema=html.Div(className="schema-grid",children=[html.Div(className="schema-card",children=[html.Div("Arquivo",className="schema-title"),html.Div("Carregado",className="schema-value"),html.Div(filename,className="schema-text")]),html.Div(className="schema-card",children=[html.Div("Colunas reconhecidas",className="schema-title"),html.Div(str(len(found)),className="schema-value"),html.Div(", ".join(nice_label(x) for x in found[:6]),className="schema-text")]),html.Div(className="schema-card",children=[html.Div("Colunas não encontradas",className="schema-title"),html.Div(str(len(missing)),className="schema-value"),html.Div(", ".join(nice_label(x) for x in missing[:6]) or "Nenhuma.",className="schema-text")])])
        return df_to_json(df),f"Arquivo carregado: {filename}",dropdown_options(df["Talhao"]),list(df["Talhao"].dropna().astype(str).unique()),dropdown_options(df["Especie"]),list(df["Especie"].dropna().astype(str).unique()),schema
    except Exception as exc:
        return None,f"Erro: {exc}",[],[],[],[],html.Div(className="empty-state error",children=[html.H3("Não foi possível carregar o arquivo"),html.P(str(exc))])

@app.callback(Output("processed-store","data"),Output("kpi-row","children"),Input("raw-store","data"),Input("filter-stand","value"),Input("filter-species","value"),Input("filter-status","value"),Input("project-area","value"),Input("sample-area","value"),Input("form-factor","value"),Input("wood-density","value"),Input("carbon-fraction","value"),Input("bef","value"),Input("root-ratio","value"),Input("baseline","value"),Input("leakage","value"),Input("buffer","value"),Input("uncertainty","value"),Input("price-usd","value"),Input("usd-brl","value"),Input("contamination","value"))
def process_data(raw_json,stands,species,status,project_area,sample_area,form_factor,wood_density,carbon_fraction,bef,root_ratio,baseline,leakage,buffer,uncertainty,price_usd,usd_brl,contamination):
    if raw_json is None: return None,[metric_card("Registros","0","aguardando planilha"),metric_card("Volume","N/A","m³"),metric_card("CO₂e","N/A","tCO₂e"),metric_card("Potencial","N/A","tCO₂e"),metric_card("Receita","N/A","R$")]
    df=prepare_inventory(json_to_df(raw_json),form_factor or .42); df=enrich_carbon(df,project_area or 10,sample_area or 1,wood_density or .5,carbon_fraction or .47,bef or 1.2,root_ratio or .24); df=detect_anomalies(df,contamination or .06); df=filter_inventory(df,stands,species,status)
    summary=kpi_summary(df); credit=credit_scenario(df,baseline or 0,leakage or 0,buffer or 0,uncertainty or 0,price_usd or 0,usd_brl or 1)
    cards=[metric_card("Registros",fmt(summary["registros"],0),"linhas filtradas"),metric_card("Volume",fmt(summary["volume_total"],2," m³"),"total analisado"),metric_card("CO₂e",fmt(summary["co2e_total"],2," t"),"estimativa expandida"),metric_card("Potencial",fmt(credit["elegivel"],2," tCO₂e"),"cenário configurado"),metric_card("Receita",f"R$ {fmt(credit['receita_brl'],2)}","estimativa de cenário","gold")]
    return df_to_json(df),cards

@app.callback(Output("tab-content","children"),Input("tabs","value"),Input("processed-store","data"),State("baseline","value"),State("leakage","value"),State("buffer","value"),State("uncertainty","value"),State("price-usd","value"),State("usd-brl","value"),State("cluster-count","value"))
def render_tab(tab,processed_json,baseline,leakage,buffer,uncertainty,price_usd,usd_brl,cluster_count):
    if processed_json is None: return empty_state()
    df=json_to_df(processed_json)
    if tab=="overview":
        stands=stand_summary(df); species=species_summary(df); top_stand=stands.iloc[0]["Talhao"] if not stands.empty else "N/A"; top_species=species.iloc[0]["Especie"] if not species.empty else "N/A"
        return html.Div([section_heading("Resumo executivo","Síntese dos principais indicadores e distribuições do conjunto de dados filtrado."),html.Div(className="module-grid",children=[module_card("Talhão","Maior contribuição",f"Talhão com maior CO₂e estimado: {top_stand}."),module_card("Espécie","Maior participação",f"Espécie com maior contribuição no filtro atual: {top_species}."),module_card("Navegação","Análises detalhadas","Use as demais abas para consultar inventário, carbono, qualidade e modelagem.")]),html.Div(className="two-column",children=[html.Div(className="panel",children=[dcc.Graph(figure=fig_co2_by_stand(stands))]),html.Div(className="panel",children=[dcc.Graph(figure=fig_species_donut(species))])]),html.Div(className="panel",children=[html.H3("Resumo por talhão"),make_grid(stands,"420px")])])
    if tab=="inventory":
        children=[section_heading("Inventário florestal","Distribuições e relações biométricas dos indivíduos presentes no conjunto de dados."),html.Div(className="two-column",children=[html.Div(className="panel",children=[dcc.Graph(figure=fig_diameter_distribution(df))]),html.Div(className="panel",children=[dcc.Graph(figure=fig_dap_height(df))])]),html.Div(className="panel",children=[dcc.Graph(figure=fig_volume_heatmap(df))])]
        if {"Coord_X","Coord_Y"}.issubset(df.columns): children.append(html.Div(className="panel",children=[dcc.Graph(figure=fig_tree_map(df))]))
        return html.Div(children)
    if tab=="carbon":
        credit=credit_scenario(df,baseline or 0,leakage or 0,buffer or 0,uncertainty or 0,price_usd or 0,usd_brl or 1); by_species=species_summary(df)
        fig=style_figure(px.bar(by_species,x="CO2e_t",y="Especie",orientation="h",color="CO2e_t",color_continuous_scale=COLOR_SCALE,title="CO₂e por espécie",labels={"CO2e_t":"CO₂e (t)","Especie":"Espécie"}),500)
        return html.Div([section_heading("Biomassa e carbono","Estimativas exploratórias calculadas a partir dos dados e parâmetros informados."),html.Div(className="metrics-grid",children=[metric_card("CO₂e bruto",fmt(credit["co2e_bruto"],2," t")),metric_card("Adicional",fmt(credit["adicional"],2," t")),metric_card("Elegível",fmt(credit["elegivel"],2," t")),metric_card("Receita US$",f"US$ {fmt(credit['receita_usd'],2)}",tone="gold"),metric_card("Receita R$",f"R$ {fmt(credit['receita_brl'],2)}",tone="gold")]),html.Div(className="two-column",children=[html.Div(className="panel",children=[dcc.Graph(figure=fig_credit_waterfall(credit))]),html.Div(className="panel",children=[dcc.Graph(figure=fig)])])])
    if tab=="quality":
        report=quality_report(df); score=quality_score(report); missing=df.isna().sum().reset_index(); missing.columns=["Coluna","Ausentes"]; missing["Coluna"]=missing["Coluna"].map(nice_label); missing=missing.sort_values("Ausentes",ascending=False).head(18)
        fig=style_figure(px.bar(missing,x="Ausentes",y="Coluna",orientation="h",title="Valores ausentes por coluna",color="Ausentes",color_continuous_scale=COLOR_SCALE),430); suspicious=df[df["Status_Anomalia"]=="Suspeito"] if "Status_Anomalia" in df else pd.DataFrame()
        return html.Div([section_heading("Qualidade dos dados","Verificação de estrutura, valores ausentes, faixas inválidas e registros estatisticamente atípicos."),html.Div(className="metrics-grid",children=[metric_card("Score",f"{score}/100","indicador heurístico"),metric_card("Sinalizados",fmt(len(suspicious),0),"registros atípicos","danger" if len(suspicious) else ""),metric_card("Colunas",fmt(len(df.columns),0),"após padronização"),metric_card("Linhas",fmt(len(df),0),"filtradas"),metric_card("Ausentes",fmt(df.isna().sum().sum(),0),"células vazias")]),html.Div(className="two-column",children=[html.Div(className="panel",children=[dcc.Graph(figure=fig)]),html.Div(className="panel",children=[html.H3("Checklist técnico"),make_grid(report,"430px")])]),html.Div(className="panel",children=[html.H3("Registros sinalizados"),make_grid(suspicious,"420px")])])
    if tab=="ml":
        result=train_volume_model(df); children=[section_heading("Modelagem exploratória","Detecção de anomalias, previsão de volume e agrupamento de talhões por similaridade."),html.Div(className="panel",children=[dcc.Graph(figure=fig_anomaly(df))])]
        if result:
            pred=result["predictions"]; maxv=max(pred["Volume_m3"].max(),pred["Volume_Previsto_ML_m3"].max()); figp=px.scatter(pred,x="Volume_m3",y="Volume_Previsto_ML_m3",color="Especie",hover_data=["Talhao","DAP_cm","Altura_m"],title="Volume observado × previsto",color_discrete_sequence=DEMETER_COLORS); figp.add_trace(go.Scatter(x=[0,maxv],y=[0,maxv],mode="lines",name="Referência 1:1",line={"dash":"dash"})); figp=style_figure(figp,460); figi=style_figure(px.bar(result["importance"],x="Importancia",y="Variavel",orientation="h",color="Importancia",color_continuous_scale=COLOR_SCALE,title="Importância das variáveis"),460)
            children += [html.Div(className="metrics-grid",children=[metric_card("R²",fmt(result["r2"],3)),metric_card("MAE",fmt(result["mae"],4," m³")),metric_card("RMSE",fmt(result["rmse"],4," m³"))]),html.Div(className="two-column",children=[html.Div(className="panel",children=[dcc.Graph(figure=figp)]),html.Div(className="panel",children=[dcc.Graph(figure=figi)])])]
        else: children.append(empty_state("Modelo não treinado","São necessários pelo menos 45 registros completos com variáveis biométricas e volume."))
        clusters=cluster_stands(df,cluster_count or 3)
        if clusters is not None:
            figc=style_figure(px.scatter(clusters,x="Volume_m3",y="CO2e_t",size="Arvores",color="Grupo_ML",hover_data=["Talhao","DAP_medio","Altura_media"],title="Agrupamento de talhões por volume e carbono",color_discrete_sequence=DEMETER_COLORS),460); children.append(html.Div(className="panel",children=[dcc.Graph(figure=figc),html.H3("Grupos de talhões"),make_grid(clusters,"360px")]))
        return html.Div(children)
    if tab=="climate":
        return html.Div([section_heading("Clima","Consulta de séries históricas por coordenadas geográficas e intervalo de datas."),html.Div(className="panel climate-controls",children=[html.Div([html.Label("Latitude"),dcc.Input(id="climate-lat",type="number",value=-21.245,step=.000001,className="input")]),html.Div([html.Label("Longitude"),dcc.Input(id="climate-lon",type="number",value=-44.999,step=.000001,className="input")]),html.Div([html.Label("Início"),dcc.DatePickerSingle(id="climate-start",date=str(date.today()-timedelta(days=365)))]),html.Div([html.Label("Fim"),dcc.DatePickerSingle(id="climate-end",date=str(date.today()-timedelta(days=7)))]),html.Button("Consultar clima",id="climate-button",className="button")]),html.Div(id="climate-output")])
    if tab=="data":
        numeric=df.select_dtypes(include=[np.number]); describe=numeric.describe().T.reset_index().rename(columns={"index":"Variavel"}) if not numeric.empty else pd.DataFrame()
        return html.Div([section_heading("Tabelas","Dados processados e estatísticas descritivas do conjunto atualmente filtrado."),html.Div(className="panel",children=[html.H3("Dados enriquecidos"),make_grid(df,"560px")]),html.Div(className="panel",children=[html.H3("Resumo estatístico"),make_grid(describe,"420px")])])
    return empty_state("Aba não encontrada","Não foi possível abrir a seção solicitada.")

@app.callback(Output("climate-output","children"),Input("climate-button","n_clicks"),State("climate-lat","value"),State("climate-lon","value"),State("climate-start","date"),State("climate-end","date"),prevent_initial_call=True)
def update_climate(_n,lat,lon,start_date,end_date):
    try:
        c=fetch_open_meteo(lat,lon,start_date,end_date)
        if c.empty: return empty_state("Sem dados climáticos","A consulta não retornou dados para o período informado.")
        cards=html.Div(className="metrics-grid",children=[metric_card("Temperatura",fmt(c["temperature_2m_mean"].mean(),2," °C"),"média do período","gold"),metric_card("Precipitação",fmt(c["precipitation_sum"].sum(),1," mm"),"acumulada"),metric_card("ET₀",fmt(c["et0_fao_evapotranspiration"].sum(),1," mm"),"total"),metric_card("VPD",fmt(c["vapour_pressure_deficit_max"].mean(),2," kPa"),"média máxima"),metric_card("Umidade do solo",fmt(c["soil_moisture_0_to_7cm_mean"].mean(),3),"0–7 cm")])
        return html.Div([cards,html.Div(className="panel",children=[dcc.Graph(figure=fig_climate(c))]),html.Div(className="panel",children=[html.H3("Dados climáticos"),make_grid(c,"420px")])])
    except Exception as exc: return html.Div(className="empty-state error",children=[html.H3("Erro na consulta climática"),html.P(str(exc))])

if __name__=="__main__":
    port=int(os.getenv("PORT",os.getenv("DEMETER_PORT","8051")))
    print(f"Demeter Dashboard disponível em http://127.0.0.1:{port}")
    app.run(host="127.0.0.1",port=port,debug=False)
