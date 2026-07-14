import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DEMETER_COLORS = ["#77d48b", "#c4a95b", "#4fa779", "#88b8a0", "#d6c47b", "#508c68"]
COLOR_SCALE = [[0, "#183e2b"], [.5, "#4fa779"], [1, "#d6c47b"]]


def style_figure(fig, height=440):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dbe8df", "family": "Inter, Segoe UI, sans-serif"},
        margin={"l": 42, "r": 28, "t": 62, "b": 42}, legend={"bgcolor": "rgba(0,0,0,0)"},
        coloraxis_colorbar={"title": ""})
    fig.update_xaxes(gridcolor="rgba(153,190,164,.10)", zerolinecolor="rgba(153,190,164,.14)")
    fig.update_yaxes(gridcolor="rgba(153,190,164,.10)", zerolinecolor="rgba(153,190,164,.14)")
    return fig


def empty_figure(title="Sem dados para exibir"):
    fig = go.Figure().add_annotation(text=title, x=.5, y=.5, showarrow=False, font={"size": 16})
    fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
    return style_figure(fig, 320)


def fig_diameter_distribution(df):
    if "DAP_cm" not in df or df["DAP_cm"].dropna().empty: return empty_figure()
    return style_figure(px.histogram(df, x="DAP_cm", color="Especie", nbins=18, title="Distribuição diamétrica", labels={"DAP_cm":"DAP (cm)","count":"Árvores"}, color_discrete_sequence=DEMETER_COLORS))


def fig_dap_height(df):
    if not {"DAP_cm","Altura_m"}.issubset(df.columns): return empty_figure()
    return style_figure(px.scatter(df, x="DAP_cm", y="Altura_m", color="Especie", hover_data=["Talhao"], title="Relação entre DAP e altura", labels={"DAP_cm":"DAP (cm)","Altura_m":"Altura (m)"}, color_discrete_sequence=DEMETER_COLORS))


def fig_species_donut(species):
    if species.empty: return empty_figure()
    fig=px.pie(species, values="CO2e_t", names="Especie", hole=.58, title="Participação por espécie", color_discrete_sequence=DEMETER_COLORS)
    return style_figure(fig)


def fig_co2_by_stand(stands):
    if stands.empty: return empty_figure()
    return style_figure(px.bar(stands, x="Talhao", y="CO2e_t", color="CO2e_t", title="CO₂e estimado por talhão", labels={"Talhao":"Talhão","CO2e_t":"CO₂e (t)"}, color_continuous_scale=COLOR_SCALE))


def fig_volume_heatmap(df):
    if not {"Talhao","Especie","Volume_m3"}.issubset(df.columns): return empty_figure()
    p=df.pivot_table(index="Especie", columns="Talhao", values="Volume_m3", aggfunc="sum", fill_value=0)
    return style_figure(px.imshow(p, text_auto=".2f", aspect="auto", title="Volume por espécie e talhão", color_continuous_scale=COLOR_SCALE, labels={"color":"Volume (m³)"}), 500)


def fig_tree_map(df):
    if not {"Coord_X","Coord_Y"}.issubset(df.columns): return empty_figure()
    return style_figure(px.scatter(df, x="Coord_X", y="Coord_Y", color="Especie", size="DAP_cm", hover_data=["Talhao","Num_Arvore"], title="Distribuição espacial dos indivíduos", color_discrete_sequence=DEMETER_COLORS), 520)


def fig_anomaly(df):
    if not {"DAP_cm","Altura_m","Status_Anomalia"}.issubset(df.columns): return empty_figure()
    return style_figure(px.scatter(df, x="DAP_cm", y="Altura_m", color="Status_Anomalia", hover_data=["Talhao","Especie","Volume_m3"], title="Registros sinalizados pela análise de anomalias", color_discrete_map={"Normal":"#77d48b","Suspeito":"#e27a69","Não avaliado":"#8d9a91"}))


def fig_credit_waterfall(credit):
    fig=go.Figure(go.Waterfall(x=["CO₂e bruto","Baseline","Leakage","Buffer","Incerteza","Elegível"],
      measure=["absolute","relative","relative","relative","relative","total"],
      y=[credit["co2e_bruto"],-credit["baseline"],-credit["leakage"],-credit["buffer"],-credit["incerteza"],credit["elegivel"]], connector={"line":{"color":"#557263"}}))
    fig.update_layout(title="Composição do cenário de carbono")
    return style_figure(fig, 500)


def fig_climate(df):
    if df.empty: return empty_figure("Nenhum dado climático retornado")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=df["time"], y=df["temperature_2m_mean"], mode="lines", name="Temperatura média"))
    fig.add_trace(go.Bar(x=df["time"], y=df["precipitation_sum"], name="Precipitação", yaxis="y2", opacity=.45))
    fig.update_layout(title="Série climática histórica", yaxis={"title":"Temperatura média (°C)"}, yaxis2={"title":"Precipitação (mm)","overlaying":"y","side":"right"})
    return style_figure(fig, 520)
