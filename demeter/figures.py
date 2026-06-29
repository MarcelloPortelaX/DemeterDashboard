import plotly.express as px
import plotly.graph_objects as go

DEMETER_COLORS = [
    "#39ff88",
    "#9dffc3",
    "#38d97f",
    "#f6c453",
    "#ffe29a",
    "#ff4d6d",
    "#ff8fa3",
    "#d8ffe8",
]

COLOR_SCALE = ["#030604", "#0b1811", "#1f7f4a", "#39ff88", "#f6c453"]

LABELS = {
    "Talhao": "Talhão",
    "Especie": "Espécie",
    "Parcela": "Parcela",
    "Num_Arvore": "Árvore",
    "DAP_cm": "DAP (cm)",
    "Altura_m": "Altura (m)",
    "Volume_m3": "Volume (m³)",
    "Coord_X": "Coordenada X",
    "Coord_Y": "Coordenada Y",
    "CO2e_t": "CO₂e (t)",
    "CO2e_Expandido_t": "CO₂e expandido (t)",
    "Carbono_tC": "Carbono (tC)",
    "Status_Anomalia": "Status de anomalia",
    "Score_Anomalia": "Score de anomalia",
    "temperature_2m_mean": "Temperatura média (°C)",
    "precipitation_sum": "Precipitação (mm)",
}


def style_figure(fig, height=430):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(57,255,136,0.025)",
        font={"family": "Inter, Segoe UI, Arial", "color": "#f0fff6"},
        title={"font": {"size": 18, "color": "#9dffc3"}, "x": 0.02, "xanchor": "left"},
        colorway=DEMETER_COLORS,
        margin={"l": 42, "r": 28, "t": 64, "b": 42},
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": "rgba(57,255,136,0.18)",
            "borderwidth": 1,
            "font": {"color": "#d8ffe8"},
        },
        hoverlabel={"bgcolor": "#07110c", "bordercolor": "#39ff88", "font": {"color": "#f0fff6"}},
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(57,255,136,0.08)", zeroline=False, linecolor="rgba(57,255,136,0.20)", tickfont={"color": "#a9c8b5"})
    fig.update_yaxes(showgrid=True, gridcolor="rgba(57,255,136,0.08)", zeroline=False, linecolor="rgba(57,255,136,0.20)", tickfont={"color": "#a9c8b5"})
    return fig


def empty_figure(title="Carregue dados para visualizar"):
    fig = go.Figure()
    fig.update_layout(title=title)
    return style_figure(fig)


def fig_co2_by_stand(stand_df):
    fig = px.bar(
        stand_df,
        x="Talhao",
        y="CO2e_t",
        text_auto=".1f",
        title="CO₂e por talhão",
        color="CO2e_t",
        color_continuous_scale=COLOR_SCALE,
        labels=LABELS,
    )
    return style_figure(fig, 460)


def fig_species_donut(species_df):
    fig = px.pie(
        species_df,
        names="Especie",
        values="CO2e_t",
        hole=0.58,
        title="Participação de CO₂e por espécie",
        color_discrete_sequence=DEMETER_COLORS,
        labels=LABELS,
    )
    return style_figure(fig, 460)


def fig_diameter_distribution(df):
    fig = px.histogram(
        df,
        x="DAP_cm",
        color="Especie",
        nbins=26,
        title="Distribuição de DAP",
        color_discrete_sequence=DEMETER_COLORS,
        labels=LABELS,
    )
    return style_figure(fig, 430)


def fig_dap_height(df):
    fig = px.scatter(
        df,
        x="DAP_cm",
        y="Altura_m",
        color="Especie",
        size="Volume_m3",
        hover_data=["Talhao", "Parcela", "Num_Arvore", "Volume_m3", "CO2e_t"],
        title="DAP × altura",
        color_discrete_sequence=DEMETER_COLORS,
        labels=LABELS,
    )
    return style_figure(fig, 430)


def fig_volume_heatmap(df):
    matrix = df.groupby(["Talhao", "Especie"], as_index=False).agg(Volume_m3=("Volume_m3", "sum"))
    fig = px.density_heatmap(
        matrix,
        x="Especie",
        y="Talhao",
        z="Volume_m3",
        histfunc="sum",
        title="Volume por talhão e espécie",
        color_continuous_scale=COLOR_SCALE,
        labels=LABELS,
    )
    return style_figure(fig, 500)


def fig_tree_map(df):
    coord = df.dropna(subset=["Coord_X", "Coord_Y"]).copy()
    if coord.empty:
        return empty_figure("Coordenadas ausentes")
    fig = px.scatter(
        coord,
        x="Coord_X",
        y="Coord_Y",
        color="Especie",
        size="DAP_cm",
        hover_data=["Talhao", "Parcela", "Num_Arvore", "DAP_cm", "Altura_m", "Volume_m3"],
        title="Mapa 2D dos indivíduos",
        color_discrete_sequence=DEMETER_COLORS,
        labels=LABELS,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return style_figure(fig, 560)


def fig_credit_waterfall(credit):
    fig = go.Figure(
        go.Waterfall(
            measure=["absolute", "relative", "relative", "relative", "relative", "total"],
            x=["CO₂e bruto", "Baseline", "Leakage", "Buffer", "Incerteza", "Elegível"],
            y=[
                credit["co2e_bruto"],
                -credit["baseline"],
                -credit["leakage"],
                -credit["buffer"],
                -credit["incerteza"],
                credit["elegivel"],
            ],
            connector={"line": {"color": "rgba(57,255,136,0.28)"}},
            decreasing={"marker": {"color": "#ff4d6d"}},
            increasing={"marker": {"color": "#39ff88"}},
            totals={"marker": {"color": "#f6c453"}},
        )
    )
    fig.update_layout(title="Funil de potencial estimado", yaxis_title="tCO₂e")
    return style_figure(fig, 500)


def fig_anomaly(df):
    fig = px.scatter(
        df,
        x="DAP_cm",
        y="Altura_m",
        color="Status_Anomalia",
        size="Volume_m3",
        hover_data=["Talhao", "Especie", "Score_Anomalia"],
        title="Anomalias em DAP × altura",
        color_discrete_map={"Normal": "#39ff88", "Suspeito": "#ff4d6d", "Não avaliado": "#8faf9b"},
        labels=LABELS,
    )
    return style_figure(fig, 460)


def fig_climate(climate_df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=climate_df["time"], y=climate_df["temperature_2m_mean"], mode="lines", name="Temperatura média", line={"color": "#f6c453"}))
    fig.add_trace(go.Bar(x=climate_df["time"], y=climate_df["precipitation_sum"], name="Precipitação", opacity=0.45, yaxis="y2", marker={"color": "#39ff88"}))
    fig.update_layout(
        title="Série climática histórica",
        yaxis={"title": "Temperatura média (°C)"},
        yaxis2={"title": "Precipitação (mm)", "overlaying": "y", "side": "right"},
    )
    return style_figure(fig, 520)
