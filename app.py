from datetime import date, timedelta

import dash_ag_grid as dag
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dcc, html

from demeter.carbon import credit_scenario, enrich_carbon
from demeter.climate import fetch_open_meteo
from demeter.figures import (
    DEMETER_COLORS,
    COLOR_SCALE,
    empty_figure,
    fig_anomaly,
    fig_climate,
    fig_co2_by_stand,
    fig_credit_waterfall,
    fig_dap_height,
    fig_diameter_distribution,
    fig_species_donut,
    fig_tree_map,
    fig_volume_heatmap,
    style_figure,
)
from demeter.io import df_to_json, json_to_df, parse_upload
from demeter.metrics import filter_inventory, kpi_summary, prepare_inventory, species_summary, stand_summary
from demeter.ml import cluster_stands, detect_anomalies, train_volume_model
from demeter.schema import EXPECTED_COLUMNS, standardize_dataframe
from demeter.validation import quality_report, quality_score

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

DISPLAY_LABELS = {
    "Talhao": "Talhão",
    "Parcela": "Parcela",
    "Num_Arvore": "Árvore",
    "Especie": "Espécie",
    "DAP_cm": "DAP (cm)",
    "Altura_m": "Altura (m)",
    "Volume_m3": "Volume (m³)",
    "Coord_X": "Coordenada X",
    "Coord_Y": "Coordenada Y",
    "Idade_anos": "Idade (anos)",
    "DensidadeMadeira_t_m3": "Densidade da madeira (t/m³)",
    "AreaBasal_m2": "Área basal (m²)",
    "BiomassaFuste_t": "Biomassa do fuste (t)",
    "BiomassaAcimaSolo_t": "Biomassa acima do solo (t)",
    "BiomassaRaiz_t": "Biomassa de raízes (t)",
    "BiomassaTotal_t": "Biomassa total (t)",
    "Carbono_tC": "Carbono (tC)",
    "CO2e_t": "CO₂e (t)",
    "CO2e_Expandido_t": "CO₂e expandido (t)",
    "Status_Anomalia": "Status de anomalia",
    "Score_Anomalia": "Score de anomalia",
    "Grupo_ML": "Grupo de IA",
    "DAP_medio": "DAP médio",
    "Altura_media": "Altura média",
    "Volume_total": "Volume total",
    "CO2e_total": "CO₂e total",
    "CO2e_total_t": "CO₂e total (t)",
    "Carbono_total_tC": "Carbono total (tC)",
    "Volume_Previsto_ML_m3": "Volume previsto por IA (m³)",
    "Erro_ML_m3": "Erro do modelo (m³)",
    "Variavel": "Variável",
    "Importancia": "Importância",
    "Ausentes": "Valores ausentes",
    "Coluna": "Coluna",
    "Item": "Item",
    "Status": "Status",
    "time": "Data",
    "temperature_2m_mean": "Temperatura média (°C)",
    "precipitation_sum": "Precipitação (mm)",
    "et0_fao_evapotranspiration": "ET₀ FAO (mm)",
    "vapour_pressure_deficit_max": "VPD máximo (kPa)",
    "soil_moisture_0_to_7cm_mean": "Umidade do solo 0-7 cm",
}


def nice_label(value):
    text = DISPLAY_LABELS.get(str(value), str(value))
    text = text.replace("_", " ")
    return text


def human_list(values, limit=6):
    readable = [nice_label(v) for v in values]
    if len(readable) > limit:
        return ", ".join(readable[:limit]) + f" e mais {len(readable) - limit}"
    return ", ".join(readable) if readable else "Nenhum"


def fmt(value, decimals=2, suffix=""):
    try:
        if value is None or pd.isna(value) or not np.isfinite(float(value)):
            return "N/A"
    except Exception:
        return "N/A"
    text = f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text}{suffix}"


def metric_card(title, value, subtitle="", tone=""):
    cls = "metric-card" if not tone else f"metric-card metric-{tone}"
    return html.Div(
        className=cls,
        children=[
            html.Div(title, className="metric-title"),
            html.Div(value, className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


def section_heading(title, subtitle):
    return html.Div(className="section-heading", children=[html.H2(title), html.P(subtitle)])


def module_card(tag, title, text):
    return html.Div(
        className="module-card",
        children=[html.Div(tag, className="module-tag"), html.H3(title), html.P(text)],
    )


def parameter_group(title, children, open=False):
    return html.Details(
        className="parameter-group",
        open=open,
        children=[html.Summary(title), html.Div(className="parameter-group-body", children=children)],
    )


def make_grid(df, height="460px"):
    if df is None or df.empty:
        row_data = []
        column_defs = []
    else:
        clean = df.replace([np.inf, -np.inf], np.nan).fillna("")
        row_data = clean.to_dict("records")
        column_defs = [
            {
                "field": col,
                "headerName": nice_label(col),
                "filter": True,
                "sortable": True,
                "resizable": True,
                "tooltipField": col,
            }
            for col in clean.columns
        ]

    return dag.AgGrid(
        columnDefs=column_defs,
        rowData=row_data,
        defaultColDef={"filter": True, "sortable": True, "resizable": True, "floatingFilter": True},
        dashGridOptions={"pagination": True, "paginationPageSize": 15, "animateRows": True},
        className="ag-theme-alpine-dark demeter-grid",
        style={"height": height, "width": "100%"},
    )


def empty_state(title="Comece enviando uma planilha", text="Use CSV ou XLSX. O painel organiza inventário, carbono, qualidade, IA e clima em módulos separados."):
    return html.Div(
        className="empty-state empty-state-large",
        children=[
            html.H3(title),
            html.P(text),
            html.Div(
                className="module-grid",
                children=[
                    module_card("1", "Enviar dados", "Carregue a planilha de inventário ou use data/exemplo_teste.csv."),
                    module_card("2", "Ajustar parâmetros", "Abra apenas o grupo necessário na barra lateral."),
                    module_card("3", "Ler por módulos", "Resumo primeiro. Depois inventário, carbono, qualidade, IA e clima."),
                ],
            ),
        ],
    )


def dropdown_options(values):
    return [{"label": str(v).replace("_", " "), "value": str(v)} for v in sorted(pd.Series(values).dropna().astype(str).unique())]


app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="raw-store"),
        dcc.Store(id="processed-store"),

        html.Aside(
            className="sidebar",
            children=[
                html.Div(className="brand", children="DEMETER"),
                html.Div(className="brand-subtitle", children="Dashboard Pro"),

                html.Div(
                    className="sidebar-help",
                    children=[
                        html.Div("Fluxo recomendado", className="sidebar-help-title"),
                        html.Div("1. Envie a planilha"),
                        html.Div("2. Confira o resumo"),
                        html.Div("3. Ajuste carbono se necessário"),
                    ],
                ),

                html.Div(className="sidebar-section-title", children="Entrada de dados"),
                dcc.Upload(
                    id="upload-data",
                    className="upload-box",
                    children=html.Div([
                        html.Div("Enviar CSV/XLSX", className="upload-title"),
                        html.Div("Inventário florestal real", className="upload-subtitle"),
                    ]),
                    multiple=False,
                ),
                html.Div(id="upload-status", className="upload-status", children="Nenhum arquivo carregado."),

                parameter_group(
                    "Filtros principais",
                    open=True,
                    children=[
                        html.Label("Talhão"),
                        dcc.Dropdown(id="filter-stand", multi=True, className="demeter-dropdown", placeholder="Todos"),
                        html.Label("Espécie"),
                        dcc.Dropdown(id="filter-species", multi=True, className="demeter-dropdown", placeholder="Todas"),
                        html.Label("Status de anomalia"),
                        dcc.Dropdown(
                            id="filter-status",
                            multi=True,
                            className="demeter-dropdown",
                            value=["Normal", "Suspeito", "Não avaliado"],
                            options=[
                                {"label": "Normal", "value": "Normal"},
                                {"label": "Suspeito", "value": "Suspeito"},
                                {"label": "Não avaliado", "value": "Não avaliado"},
                            ],
                        ),
                    ],
                ),

                parameter_group(
                    "Inventário",
                    children=[
                        html.Label("Área do projeto (ha)"),
                        dcc.Input(id="project-area", type="number", value=10, min=0.01, step=0.1, className="input"),
                        html.Label("Área amostrada no CSV (ha)"),
                        dcc.Input(id="sample-area", type="number", value=1, min=0.01, step=0.1, className="input"),
                        html.Label("Fator de forma"),
                        dcc.Input(id="form-factor", type="number", value=0.42, min=0.1, max=1, step=0.01, className="input"),
                    ],
                ),

                parameter_group(
                    "Carbono",
                    children=[
                        html.Label("Densidade madeira padrão (t/m³)"),
                        dcc.Input(id="wood-density", type="number", value=0.50, min=0.1, max=1.2, step=0.01, className="input"),
                        html.Label("Fração de carbono"),
                        dcc.Input(id="carbon-fraction", type="number", value=0.47, min=0.3, max=0.7, step=0.01, className="input"),
                        html.Label("BEF biomassa aérea"),
                        dcc.Input(id="bef", type="number", value=1.20, min=1, max=3, step=0.05, className="input"),
                        html.Label("Razão raiz/parte aérea"),
                        dcc.Input(id="root-ratio", type="number", value=0.24, min=0, max=1, step=0.01, className="input"),
                    ],
                ),

                parameter_group(
                    "Potencial estimado",
                    children=[
                        html.Label("Baseline (%)"),
                        dcc.Input(id="baseline", type="number", value=30, min=0, max=100, step=1, className="input"),
                        html.Label("Leakage (%)"),
                        dcc.Input(id="leakage", type="number", value=8, min=0, max=100, step=1, className="input"),
                        html.Label("Buffer de risco (%)"),
                        dcc.Input(id="buffer", type="number", value=15, min=0, max=100, step=1, className="input"),
                        html.Label("Incerteza (%)"),
                        dcc.Input(id="uncertainty", type="number", value=10, min=0, max=100, step=1, className="input"),
                        html.Label("US$/tCO₂e"),
                        dcc.Input(id="price-usd", type="number", value=12, min=0, step=1, className="input"),
                        html.Label("Câmbio US$ → R$"),
                        dcc.Input(id="usd-brl", type="number", value=5.40, min=1, step=0.1, className="input"),
                    ],
                ),

                parameter_group(
                    "IA e agrupamentos",
                    children=[
                        html.Label("Sensibilidade a anomalias"),
                        dcc.Input(id="contamination", type="number", value=0.06, min=0.01, max=0.30, step=0.01, className="input"),
                        html.Label("Grupos de talhões"),
                        dcc.Input(id="cluster-count", type="number", value=3, min=2, max=8, step=1, className="input"),
                    ],
                ),
            ],
        ),

        html.Main(
            className="main",
            children=[
                html.Div(
                    className="hero",
                    children=[
                        html.Div("INVENTÁRIO · CARBONO · QUALIDADE · IA", className="eyebrow"),
                        html.H1(["Demeter ", html.Span("Dashboard")]),
                        html.P("Análise florestal organizada por módulos, com leitura progressiva: resumo executivo, inventário florestal, biomassa e carbono, qualidade dos dados, modelagem e clima."),
                    ],
                ),

                html.Div(id="schema-bar"),
                html.Div(id="kpi-row", className="metrics-grid"),

                dcc.Tabs(
                    id="tabs",
                    value="overview",
                    className="tabs",
                    children=[
                        dcc.Tab(label="Resumo", value="overview"),
                        dcc.Tab(label="Inventário", value="inventory"),
                        dcc.Tab(label="Carbono", value="carbon"),
                        dcc.Tab(label="Qualidade", value="quality"),
                        dcc.Tab(label="IA", value="ml"),
                        dcc.Tab(label="Clima", value="climate"),
                        dcc.Tab(label="Tabelas", value="data"),
                    ],
                ),
                html.Div(id="tab-content", className="tab-content"),
            ],
        ),
    ],
)


@app.callback(
    Output("raw-store", "data"),
    Output("upload-status", "children"),
    Output("filter-stand", "options"),
    Output("filter-stand", "value"),
    Output("filter-species", "options"),
    Output("filter-species", "value"),
    Output("schema-bar", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def load_file(contents, filename):
    if contents is None:
        schema = html.Div(
            className="schema-grid",
            children=[
                html.Div(className="schema-card", children=[html.Div("Status", className="schema-title"), html.Div("Vazio", className="schema-value"), html.Div("Envie um CSV ou XLSX para começar.", className="schema-text")]),
                html.Div(className="schema-card", children=[html.Div("Modelo esperado", className="schema-title"), html.Div(str(len(EXPECTED_COLUMNS)), className="schema-value"), html.Div("DAP, altura, espécie, talhão, volume e coordenadas.", className="schema-text")]),
                html.Div(className="schema-card", children=[html.Div("Estimativa", className="schema-title"), html.Div("CO₂e", className="schema-value"), html.Div("Exploratória, não certificação oficial.", className="schema-text")]),
            ],
        )
        return None, "Nenhum arquivo carregado.", [], [], [], [], schema

    try:
        df = parse_upload(contents, filename)
        df, mapping = standardize_dataframe(df)

        if "Talhao" not in df.columns:
            df["Talhao"] = "Projeto único"
        if "Especie" not in df.columns:
            df["Especie"] = "Não informada"

        found = [col for col in EXPECTED_COLUMNS if col in df.columns]
        missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]

        schema = html.Div(
            className="schema-grid",
            children=[
                html.Div(className="schema-card", children=[html.Div("Leitura", className="schema-title"), html.Div("OK", className="schema-value"), html.Div(f"Arquivo: {filename}", className="schema-text")]),
                html.Div(className="schema-card", children=[html.Div("Colunas encontradas", className="schema-title"), html.Div(str(len(found)), className="schema-value"), html.Div(human_list(found), className="schema-text")]),
                html.Div(className="schema-card", children=[html.Div("Atenção", className="schema-title"), html.Div(str(len(missing)), className="schema-value"), html.Div(human_list(missing) if missing else "Nenhuma coluna crítica ausente.", className="schema-text")]),
            ],
        )

        return (
            df_to_json(df),
            f"Arquivo carregado: {filename}",
            dropdown_options(df["Talhao"]),
            list(pd.Series(df["Talhao"]).dropna().astype(str).unique()),
            dropdown_options(df["Especie"]),
            list(pd.Series(df["Especie"]).dropna().astype(str).unique()),
            schema,
        )

    except Exception as exc:
        schema = html.Div(className="empty-state error", children=[html.H3("Erro ao carregar"), html.P(str(exc))])
        return None, f"Erro: {exc}", [], [], [], [], schema


@app.callback(
    Output("processed-store", "data"),
    Output("kpi-row", "children"),
    Input("raw-store", "data"),
    Input("filter-stand", "value"),
    Input("filter-species", "value"),
    Input("filter-status", "value"),
    Input("project-area", "value"),
    Input("sample-area", "value"),
    Input("form-factor", "value"),
    Input("wood-density", "value"),
    Input("carbon-fraction", "value"),
    Input("bef", "value"),
    Input("root-ratio", "value"),
    Input("baseline", "value"),
    Input("leakage", "value"),
    Input("buffer", "value"),
    Input("uncertainty", "value"),
    Input("price-usd", "value"),
    Input("usd-brl", "value"),
    Input("contamination", "value"),
)
def process_data(
    raw_json, stands, species, status, project_area, sample_area, form_factor,
    wood_density, carbon_fraction, bef, root_ratio, baseline, leakage, buffer,
    uncertainty, price_usd, usd_brl, contamination
):
    if raw_json is None:
        return None, [
            metric_card("Registros", "0", "aguardando planilha"),
            metric_card("Volume", "N/A", "m³"),
            metric_card("CO₂e", "N/A", "tCO₂e"),
            metric_card("Créditos", "N/A", "tCO₂e"),
            metric_card("Receita", "N/A", "R$"),
        ]

    df = json_to_df(raw_json)
    df = prepare_inventory(df, form_factor=form_factor or 0.42)
    df = enrich_carbon(
        df,
        project_area_ha=project_area or 10,
        sample_area_ha=sample_area or 1,
        default_density=wood_density or 0.50,
        carbon_fraction=carbon_fraction or 0.47,
        bef=bef or 1.20,
        root_ratio=root_ratio or 0.24,
    )
    df = detect_anomalies(df, contamination=contamination or 0.06)
    df = filter_inventory(df, stands=stands, species=species, status=status)

    summary = kpi_summary(df)
    credit = credit_scenario(
        df,
        baseline_pct=baseline or 0,
        leakage_pct=leakage or 0,
        buffer_pct=buffer or 0,
        uncertainty_pct=uncertainty or 0,
        price_usd=price_usd or 0,
        usd_brl=usd_brl or 1,
    )

    kpis = [
        metric_card("Registros", fmt(summary["registros"], 0), "linhas filtradas"),
        metric_card("Volume", fmt(summary["volume_total"], 2, " m³"), "total analisado"),
        metric_card("CO₂e", fmt(summary["co2e_total"], 2, " t"), "expandido pela área"),
        metric_card("Créditos", fmt(credit["elegivel"], 2, " tCO₂e"), "estimativa elegível"),
        metric_card("Receita", f"R$ {fmt(credit['receita_brl'], 2)}", "cenário, não certificado", "gold"),
    ]

    return df_to_json(df), kpis


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("processed-store", "data"),
    State("baseline", "value"),
    State("leakage", "value"),
    State("buffer", "value"),
    State("uncertainty", "value"),
    State("price-usd", "value"),
    State("usd-brl", "value"),
    State("cluster-count", "value"),
)
def render_tab(tab, processed_json, baseline, leakage, buffer, uncertainty, price_usd, usd_brl, cluster_count):
    if processed_json is None:
        return empty_state()

    df = json_to_df(processed_json)

    if tab == "overview":
        stands = stand_summary(df)
        species = species_summary(df)
        top_stand = stands.iloc[0]["Talhao"] if not stands.empty else "N/A"
        top_species = species.iloc[0]["Especie"] if not species.empty else "N/A"
        return html.Div([
            section_heading("Resumo executivo", "O painel principal mostra só o essencial. Detalhes ficam nas outras abas, porque entupir tela não é inteligência, é ansiedade com CSS."),
            html.Div(className="module-grid", children=[
                module_card("Prioridade", "Talhão dominante", f"Maior contribuição estimada: {str(top_stand).replace('_', ' ')}."),
                module_card("Espécie", "Maior participação", f"Espécie mais relevante no conjunto filtrado: {str(top_species).replace('_', ' ')}."),
                module_card("Leitura", "Use as abas", "Inventário explica estrutura, Carbono explica CO₂e, Qualidade mostra problemas."),
            ]),
            html.Div(className="two-column", children=[
                html.Div(className="panel", children=[dcc.Graph(figure=fig_co2_by_stand(stands))]),
                html.Div(className="panel", children=[dcc.Graph(figure=fig_species_donut(species))]),
            ]),
            html.Div(className="panel", children=[html.H3("Ranking de talhões"), make_grid(stands, "420px")]),
        ])

    if tab == "inventory":
        children = [
            section_heading("Inventário", "Estrutura biométrica: distribuição de DAP, relação DAP × altura, volume por espécie e posição dos indivíduos."),
            html.Div(className="two-column", children=[
                html.Div(className="panel", children=[dcc.Graph(figure=fig_diameter_distribution(df))]),
                html.Div(className="panel", children=[dcc.Graph(figure=fig_dap_height(df))]),
            ]),
            html.Div(className="panel", children=[dcc.Graph(figure=fig_volume_heatmap(df))]),
        ]
        if "Coord_X" in df.columns and "Coord_Y" in df.columns:
            children.append(html.Div(className="panel", children=[dcc.Graph(figure=fig_tree_map(df))]))
        return html.Div(children)

    if tab == "carbon":
        credit = credit_scenario(df, baseline or 0, leakage or 0, buffer or 0, uncertainty or 0, price_usd or 0, usd_brl or 1)
        by_species = species_summary(df)
        fig_bar = px.bar(
            by_species,
            x="CO2e_t",
            y="Especie",
            orientation="h",
            color="CO2e_t",
            color_continuous_scale=COLOR_SCALE,
            title="CO₂e por espécie",
            text_auto=".1f",
            labels={"CO2e_t": "CO₂e (t)", "Especie": "Espécie"},
        )
        fig_bar = style_figure(fig_bar, 500)
        return html.Div([
            section_heading("Carbono", "Estimativa exploratória de biomassa, carbono e CO₂e. Útil para análise e portfólio; não substitui certificação."),
            html.Div(className="metrics-grid", children=[
                metric_card("CO₂e bruto", fmt(credit["co2e_bruto"], 2, " t")),
                metric_card("Adicional", fmt(credit["adicional"], 2, " t")),
                metric_card("Elegível", fmt(credit["elegivel"], 2, " t")),
                metric_card("Receita US$", f"US$ {fmt(credit['receita_usd'], 2)}", tone="gold"),
                metric_card("Receita R$", f"R$ {fmt(credit['receita_brl'], 2)}", tone="gold"),
            ]),
            html.Div(className="two-column", children=[
                html.Div(className="panel", children=[dcc.Graph(figure=fig_credit_waterfall(credit))]),
                html.Div(className="panel", children=[dcc.Graph(figure=fig_bar)]),
            ]),
        ])

    if tab == "quality":
        report = quality_report(df)
        score = quality_score(report)
        missing = df.isna().sum().reset_index()
        missing.columns = ["Coluna", "Ausentes"]
        missing["Coluna"] = missing["Coluna"].map(nice_label)
        missing = missing.sort_values("Ausentes", ascending=False).head(18)

        fig_missing = px.bar(
            missing,
            x="Ausentes",
            y="Coluna",
            orientation="h",
            title="Valores ausentes por coluna",
            color="Ausentes",
            color_continuous_scale=COLOR_SCALE,
            labels={"Ausentes": "Valores ausentes", "Coluna": "Coluna"},
        )
        fig_missing = style_figure(fig_missing, 430)

        suspicious = df[df["Status_Anomalia"] == "Suspeito"] if "Status_Anomalia" in df.columns else pd.DataFrame()

        return html.Div([
            section_heading("Qualidade", "Validação das colunas, valores ausentes, faixas inválidas e registros suspeitos."),
            html.Div(className="metrics-grid", children=[
                metric_card("Score", f"{score}/100", "heurística simples"),
                metric_card("Suspeitos", fmt(len(suspicious), 0), "registros por IA", "danger" if len(suspicious) else ""),
                metric_card("Colunas", fmt(len(df.columns), 0), "após padronização"),
                metric_card("Linhas", fmt(len(df), 0), "filtradas"),
                metric_card("Ausentes", fmt(df.isna().sum().sum(), 0), "células vazias"),
            ]),
            html.Div(className="two-column", children=[
                html.Div(className="panel", children=[dcc.Graph(figure=fig_missing)]),
                html.Div(className="panel", children=[html.H3("Checklist técnico"), make_grid(report, "430px")]),
            ]),
            html.Div(className="panel", children=[html.H3("Registros suspeitos"), make_grid(suspicious, "420px")]),
        ])

    if tab == "ml":
        ml_result = train_volume_model(df)
        children = [
            section_heading("IA", "Anomalias, previsão experimental de volume e agrupamento de talhões por similaridade."),
            html.Div(className="panel", children=[dcc.Graph(figure=fig_anomaly(df))]),
        ]

        if ml_result is not None:
            pred = ml_result["predictions"]
            max_value = max(pred["Volume_m3"].max(), pred["Volume_Previsto_ML_m3"].max())

            fig_pred = px.scatter(
                pred,
                x="Volume_m3",
                y="Volume_Previsto_ML_m3",
                color="Especie",
                hover_data=["Talhao", "DAP_cm", "Altura_m"],
                title="Volume real × previsto",
                color_discrete_sequence=DEMETER_COLORS,
                labels={"Volume_m3": "Volume real (m³)", "Volume_Previsto_ML_m3": "Volume previsto (m³)", "Especie": "Espécie"},
            )
            fig_pred.add_trace(go.Scatter(
                x=[0, max_value],
                y=[0, max_value],
                mode="lines",
                name="Linha ideal",
                line={"color": "#f6c453", "dash": "dash"},
            ))
            fig_pred = style_figure(fig_pred, 460)

            fig_importance = px.bar(
                ml_result["importance"],
                x="Importancia",
                y="Variavel",
                orientation="h",
                color="Importancia",
                color_continuous_scale=COLOR_SCALE,
                title="Importância das variáveis",
                labels={"Importancia": "Importância", "Variavel": "Variável"},
            )
            fig_importance = style_figure(fig_importance, 460)

            children.extend([
                html.Div(className="metrics-grid", children=[
                    metric_card("R²", fmt(ml_result["r2"], 3)),
                    metric_card("MAE", fmt(ml_result["mae"], 4, " m³")),
                    metric_card("RMSE", fmt(ml_result["rmse"], 4, " m³")),
                ]),
                html.Div(className="two-column", children=[
                    html.Div(className="panel", children=[dcc.Graph(figure=fig_pred)]),
                    html.Div(className="panel", children=[dcc.Graph(figure=fig_importance)]),
                ]),
            ])
        else:
            children.append(empty_state("Modelo não treinado", "São necessários pelo menos 45 registros com DAP, altura e volume."))

        clusters = cluster_stands(df, cluster_count or 3)
        if clusters is not None:
            fig_cluster = px.scatter(
                clusters,
                x="Volume_m3",
                y="CO2e_t",
                size="Arvores",
                color="Grupo_ML",
                hover_data=["Talhao", "DAP_medio", "Altura_media"],
                title="Agrupamento de talhões por volume e carbono",
                color_discrete_sequence=DEMETER_COLORS,
                labels={"Volume_m3": "Volume (m³)", "CO2e_t": "CO₂e (t)", "Grupo_ML": "Grupo de IA"},
            )
            fig_cluster = style_figure(fig_cluster, 460)
            children.append(html.Div(className="panel", children=[dcc.Graph(figure=fig_cluster), html.H3("Grupos de talhões"), make_grid(clusters, "360px")]))

        return html.Div(children)

    if tab == "climate":
        return html.Div([
            section_heading("Clima", "Consulta histórica por latitude e longitude usando Open-Meteo."),
            html.Div(className="panel climate-controls", children=[
                html.Div([html.Label("Latitude"), dcc.Input(id="climate-lat", type="number", value=-21.245, step=0.000001, className="input")]),
                html.Div([html.Label("Longitude"), dcc.Input(id="climate-lon", type="number", value=-44.999, step=0.000001, className="input")]),
                html.Div([html.Label("Início"), dcc.DatePickerSingle(id="climate-start", date=str(date.today() - timedelta(days=365)))]),
                html.Div([html.Label("Fim"), dcc.DatePickerSingle(id="climate-end", date=str(date.today() - timedelta(days=7)))]),
                html.Button("Consultar clima", id="climate-button", className="button"),
            ]),
            html.Div(id="climate-output"),
        ])

    if tab == "data":
        numeric = df.select_dtypes(include=[np.number])
        describe = numeric.describe().T.reset_index().rename(columns={"index": "Variavel"}) if not numeric.empty else pd.DataFrame()
        return html.Div([
            section_heading("Tabelas", "Dados enriquecidos e resumo estatístico. Aqui ficam os detalhes brutos, porque alguém precisava guardar a bagunça em algum lugar."),
            html.Div(className="panel", children=[html.H3("Dados enriquecidos"), make_grid(df, "560px")]),
            html.Div(className="panel", children=[html.H3("Resumo estatístico"), make_grid(describe, "420px")]),
        ])

    return empty_state("Aba não encontrada", "O roteamento de abas falhou.")


@app.callback(
    Output("climate-output", "children"),
    Input("climate-button", "n_clicks"),
    State("climate-lat", "value"),
    State("climate-lon", "value"),
    State("climate-start", "date"),
    State("climate-end", "date"),
    prevent_initial_call=True,
)
def update_climate(_n, lat, lon, start_date, end_date):
    try:
        climate_df = fetch_open_meteo(lat, lon, start_date, end_date)
        if climate_df.empty:
            return empty_state("Sem dados climáticos", "A API não retornou dados para esse intervalo.")

        kpis = html.Div(className="metrics-grid", children=[
            metric_card("Temperatura", fmt(climate_df["temperature_2m_mean"].mean(), 2, " °C"), "média do período", "gold"),
            metric_card("Precipitação", fmt(climate_df["precipitation_sum"].sum(), 1, " mm"), "acumulada"),
            metric_card("ET₀", fmt(climate_df["et0_fao_evapotranspiration"].sum(), 1, " mm"), "total"),
            metric_card("VPD", fmt(climate_df["vapour_pressure_deficit_max"].mean(), 2, " kPa"), "média máxima"),
            metric_card("Umidade solo", fmt(climate_df["soil_moisture_0_to_7cm_mean"].mean(), 3), "0-7 cm"),
        ])

        return html.Div([
            kpis,
            html.Div(className="panel", children=[dcc.Graph(figure=fig_climate(climate_df))]),
            html.Div(className="panel", children=[html.H3("Dados climáticos"), make_grid(climate_df, "420px")]),
        ])
    except Exception as exc:
        return html.Div(className="empty-state error", children=[html.H3("Erro na consulta climática"), html.P(str(exc))])


if __name__ == "__main__":
    print("======================================")
    print("Demeter Dashboard Pro iniciando...")
    print("Abra: http://127.0.0.1:8050")
    print("======================================")
    app.run(host="127.0.0.1", port=8050, debug=False)
