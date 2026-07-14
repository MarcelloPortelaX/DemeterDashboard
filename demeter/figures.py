from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DEMETER_COLORS = [
    "#39ff88", "#f6c453", "#5ec9a4", "#a0ffbd",
    "#ff8f5c", "#75a7ff", "#d485ff", "#e8ff73",
]
COLOR_SCALE = [
    [0.00, "#07110c"],
    [0.25, "#164f33"],
    [0.55, "#39b96f"],
    [0.78, "#7deda2"],
    [1.00, "#f6c453"],
]


def style_figure(fig: go.Figure, height: int = 440) -> go.Figure:
    # O título vive no cabeçalho do painel. Mantê-lo também no Plotly duplicava
    # informação e roubava área útil do gráfico.
    fig.update_layout(
        title_text=None,
        height=height,
        autosize=True,
        uirevision="demeter",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": "#dbece1",
            "family": "Inter, Segoe UI, sans-serif",
            "size": 12,
        },
        margin={"l": 52, "r": 24, "t": 18, "b": 48},
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "#a9c3b1", "size": 11},
            "title": {"font": {"color": "#dbece1", "size": 11}},
        },
        coloraxis_colorbar={
            "title": "",
            "thickness": 12,
            "len": 0.72,
            "outlinewidth": 0,
            "tickfont": {"size": 10},
        },
        hoverlabel={
            "bgcolor": "#102419",
            "font_color": "#f0fff6",
            "bordercolor": "#39ff88",
        },
        hovermode="closest",
    )
    fig.update_xaxes(
        automargin=True,
        gridcolor="rgba(153,190,164,.08)",
        zerolinecolor="rgba(153,190,164,.12)",
        linecolor="rgba(57,255,136,.14)",
        tickfont={"size": 11, "color": "#a9c3b1"},
        title_font={"size": 11, "color": "#b9d2c0"},
    )
    fig.update_yaxes(
        automargin=True,
        gridcolor="rgba(153,190,164,.08)",
        zerolinecolor="rgba(153,190,164,.12)",
        linecolor="rgba(57,255,136,.14)",
        tickfont={"size": 11, "color": "#a9c3b1"},
        title_font={"size": 11, "color": "#b9d2c0"},
    )
    return fig


def empty_figure(title: str = "Sem dados para exibir") -> go.Figure:
    fig = go.Figure().add_annotation(
        text=title, x=0.5, y=0.5, showarrow=False,
        font={"size": 16, "color": "#9dffc3"},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_figure(fig, 320)


def fig_diameter_distribution(df: pd.DataFrame) -> go.Figure:
    if "DAP_cm" not in df or df["DAP_cm"].dropna().empty:
        return empty_figure()
    fig = px.histogram(
        df, x="DAP_cm", color="Especie", nbins=24, marginal="box",
        title="Distribuição diamétrica e dispersão por espécie",
        labels={"DAP_cm": "DAP (cm)", "count": "Árvores"},
        color_discrete_sequence=DEMETER_COLORS,
    )
    return style_figure(fig, 540)


def fig_height_distribution(df: pd.DataFrame) -> go.Figure:
    if "Altura_m" not in df or df["Altura_m"].dropna().empty:
        return empty_figure()
    fig = px.histogram(
        df, x="Altura_m", color="Talhao", nbins=24,
        title="Distribuição de alturas por talhão",
        labels={"Altura_m": "Altura (m)", "count": "Árvores"},
        color_discrete_sequence=DEMETER_COLORS,
    )
    return style_figure(fig, 470)


def fig_dap_height(df: pd.DataFrame) -> go.Figure:
    if not {"DAP_cm", "Altura_m"}.issubset(df.columns):
        return empty_figure()
    size = "Volume_m3" if "Volume_m3" in df.columns else None
    fig = px.scatter(
        df, x="DAP_cm", y="Altura_m", color="Especie", size=size,
        hover_data=[c for c in ["Talhao", "Parcela", "Num_Arvore", "Volume_m3"] if c in df.columns],
        title="Relação hipsométrica: DAP × altura",
        labels={"DAP_cm": "DAP (cm)", "Altura_m": "Altura (m)"},
        color_discrete_sequence=DEMETER_COLORS,
        opacity=0.82,
    )
    return style_figure(fig, 520)


def fig_dap_box_species(df: pd.DataFrame) -> go.Figure:
    if not {"DAP_cm", "Especie"}.issubset(df.columns):
        return empty_figure()
    top = df["Especie"].value_counts().head(12).index
    work = df[df["Especie"].isin(top)]
    fig = px.box(
        work, x="Especie", y="DAP_cm", color="Especie", points="outliers",
        title="Variação diamétrica das espécies mais frequentes",
        labels={"DAP_cm": "DAP (cm)", "Especie": "Espécie"},
        color_discrete_sequence=DEMETER_COLORS,
    )
    fig.update_xaxes(tickangle=-25)
    return style_figure(fig, 500)


def fig_species_donut(species: pd.DataFrame) -> go.Figure:
    if species.empty:
        return empty_figure()
    value = "CO2e_t" if "CO2e_t" in species.columns else "Arvores"
    fig = px.pie(
        species, values=value, names="Especie", hole=0.58,
        title="Participação das espécies",
        color_discrete_sequence=DEMETER_COLORS,
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    return style_figure(fig, 470)


def fig_co2_by_stand(stands: pd.DataFrame) -> go.Figure:
    if stands.empty:
        return empty_figure()
    fig = px.bar(
        stands, x="Talhao", y="CO2e_t", color="CO2e_t",
        title="CO₂e estimado por talhão",
        labels={"Talhao": "Talhão", "CO2e_t": "CO₂e (t)"},
        color_continuous_scale=COLOR_SCALE,
        text_auto=".2s",
    )
    return style_figure(fig, 470)


def fig_basal_area_by_stand(stands: pd.DataFrame) -> go.Figure:
    if stands.empty or "AreaBasal_m2_ha" not in stands.columns:
        return empty_figure()
    fig = px.bar(
        stands.sort_values("AreaBasal_m2_ha"),
        x="AreaBasal_m2_ha", y="Talhao", orientation="h",
        color="Volume_m3_ha",
        title="Área basal e volume por hectare",
        labels={
            "AreaBasal_m2_ha": "Área basal (m²/ha)",
            "Volume_m3_ha": "Volume (m³/ha)",
            "Talhao": "Talhão",
        },
        color_continuous_scale=COLOR_SCALE,
    )
    return style_figure(fig, 500)


def fig_volume_heatmap(df: pd.DataFrame) -> go.Figure:
    if not {"Talhao", "Especie", "Volume_m3"}.issubset(df.columns):
        return empty_figure()
    pivot = df.pivot_table(
        index="Especie", columns="Talhao", values="Volume_m3",
        aggfunc="sum", fill_value=0,
    )
    if pivot.empty:
        return empty_figure()
    fig = px.imshow(
        pivot, text_auto=".2f", aspect="auto",
        title="Volume por espécie e talhão",
        color_continuous_scale=COLOR_SCALE,
        labels={"color": "Volume (m³)"},
    )
    return style_figure(fig, max(500, 280 + 26 * len(pivot)))


def fig_volume_by_class(classes: pd.DataFrame) -> go.Figure:
    if classes.empty:
        return empty_figure()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=classes["Classe_DAP"].astype(str), y=classes["Arvores"],
        name="Árvores", marker_color="#39ff88", opacity=0.72,
    ))
    fig.add_trace(go.Scatter(
        x=classes["Classe_DAP"].astype(str), y=classes["Volume_m3"],
        name="Volume", mode="lines+markers", yaxis="y2",
        line={"color": "#f6c453", "width": 3},
    ))
    fig.update_layout(
        title="Estrutura por classe diamétrica",
        yaxis={"title": "Número de árvores"},
        yaxis2={"title": "Volume (m³)", "overlaying": "y", "side": "right"},
        xaxis={"title": "Classe de DAP (cm)"},
        legend={"orientation": "h", "y": 1.12},
    )
    return style_figure(fig, 500)


def fig_species_importance(importance: pd.DataFrame) -> go.Figure:
    if importance.empty:
        return empty_figure()
    top = importance.head(15).sort_values("IVI")
    fig = px.bar(
        top, x="IVI", y="Especie", orientation="h", color="IVI",
        title="Índice de Valor de Importância (IVI)",
        hover_data=[
            "Densidade_Relativa_pct",
            "Dominancia_Relativa_pct",
            "Frequencia_Relativa_pct",
        ],
        color_continuous_scale=COLOR_SCALE,
    )
    return style_figure(fig, 520)


def fig_tree_map(df: pd.DataFrame) -> go.Figure:
    if not {"Coord_X", "Coord_Y"}.issubset(df.columns):
        return empty_figure()
    fig = px.scatter(
        df, x="Coord_X", y="Coord_Y",
        color="Especie" if "Especie" in df.columns else None,
        size="DAP_cm" if "DAP_cm" in df.columns else None,
        hover_data=[c for c in ["Talhao", "Parcela", "Num_Arvore", "Altura_m", "Volume_m3"] if c in df.columns],
        title="Distribuição espacial dos indivíduos",
        color_discrete_sequence=DEMETER_COLORS,
        opacity=0.80,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig = style_figure(fig, 530)
    fig.update_layout(
        margin={"l": 58, "r": 150, "t": 16, "b": 52},
        legend={
            "x": 1.02,
            "xanchor": "left",
            "y": 1,
            "yanchor": "top",
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"size": 11, "color": "#a9c3b1"},
        },
    )
    return fig


def fig_spatial_density(df: pd.DataFrame) -> go.Figure:
    if not {"Coord_X", "Coord_Y"}.issubset(df.columns):
        return empty_figure()
    work = df[["Coord_X", "Coord_Y"]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(work) < 3:
        return empty_figure("Poucos pontos para calcular densidade espacial")
    fig = px.density_heatmap(
        work, x="Coord_X", y="Coord_Y", nbinsx=24, nbinsy=24,
        title="Densidade espacial de indivíduos",
        color_continuous_scale=COLOR_SCALE,
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig = style_figure(fig, 470)
    fig.update_layout(margin={"l": 56, "r": 60, "t": 16, "b": 48})
    fig.update_coloraxes(colorbar={"thickness": 10, "len": 0.68, "x": 1.01})
    return fig


def fig_biomass_components(df: pd.DataFrame) -> go.Figure:
    columns = ["BiomassaFuste_t", "BiomassaRaiz_t"]
    if not {"Talhao", *columns}.issubset(df.columns):
        return empty_figure()
    grouped = df.groupby("Talhao")[columns].sum().reset_index()
    long = grouped.melt(id_vars="Talhao", var_name="Componente", value_name="Biomassa_t")
    long["Componente"] = long["Componente"].replace(
        {"BiomassaFuste_t": "Fuste", "BiomassaRaiz_t": "Raízes"}
    )
    fig = px.bar(
        long, x="Talhao", y="Biomassa_t", color="Componente", barmode="stack",
        title="Componentes de biomassa por talhão",
        labels={"Talhao": "Talhão", "Biomassa_t": "Biomassa (t)"},
        color_discrete_sequence=["#39ff88", "#f6c453"],
    )
    return style_figure(fig, 490)


def fig_carbon_treemap(df: pd.DataFrame) -> go.Figure:
    if not {"Talhao", "Especie", "CO2e_Expandido_t"}.issubset(df.columns):
        return empty_figure()
    grouped = (
        df.groupby(["Talhao", "Especie"], dropna=False)["CO2e_Expandido_t"]
        .sum().reset_index()
    )
    fig = px.treemap(
        grouped, path=["Talhao", "Especie"], values="CO2e_Expandido_t",
        color="CO2e_Expandido_t",
        title="Estrutura hierárquica do carbono",
        color_continuous_scale=COLOR_SCALE,
    )
    return style_figure(fig, 560)


def fig_credit_waterfall(credit: dict[str, float]) -> go.Figure:
    fig = go.Figure(go.Waterfall(
        x=["CO₂e bruto", "Baseline", "Leakage", "Buffer", "Incerteza", "Elegível"],
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        y=[
            credit["co2e_bruto"], -credit["baseline"], -credit["leakage"],
            -credit["buffer"], -credit["incerteza"], credit["elegivel"],
        ],
        connector={"line": {"color": "#557263"}},
        increasing={"marker": {"color": "#39ff88"}},
        decreasing={"marker": {"color": "#ff6f75"}},
        totals={"marker": {"color": "#f6c453"}},
    ))
    fig.update_layout(title="Composição do cenário de carbono")
    return style_figure(fig, 520)


def fig_sensitivity(sensitivity: pd.DataFrame) -> go.Figure:
    if sensitivity.empty:
        return empty_figure()
    pivot = sensitivity.pivot(
        index="Buffer_pct", columns="Baseline_pct", values="Elegivel_tCO2e"
    )
    fig = px.imshow(
        pivot, text_auto=".1f", aspect="auto",
        color_continuous_scale=COLOR_SCALE,
        title="Sensibilidade do CO₂e elegível",
        labels={"x": "Baseline (%)", "y": "Buffer (%)", "color": "tCO₂e elegível"},
    )
    return style_figure(fig, 500)


def fig_growth(growth: pd.DataFrame) -> go.Figure:
    if growth.empty:
        return empty_figure("Dados de idade insuficientes")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=growth["Idade_anos"], y=growth["Volume_total_m3"],
        mode="lines+markers", name="Volume total",
        line={"color": "#39ff88", "width": 3},
    ))
    fig.add_trace(go.Scatter(
        x=growth["Idade_anos"], y=growth["DAP_medio_cm"],
        mode="lines+markers", name="DAP médio", yaxis="y2",
        line={"color": "#f6c453", "width": 3},
    ))
    fig.update_layout(
        title="Trajetória por idade",
        xaxis={"title": "Idade (anos)"},
        yaxis={"title": "Volume total (m³)"},
        yaxis2={"title": "DAP médio (cm)", "overlaying": "y", "side": "right"},
    )
    return style_figure(fig, 520)


def fig_mai_cai(growth: pd.DataFrame) -> go.Figure:
    if growth.empty:
        return empty_figure("Dados de idade insuficientes")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=growth["Idade_anos"], y=growth["IMA_volume"],
        mode="lines+markers", name="IMA",
        line={"color": "#39ff88", "width": 3},
    ))
    fig.add_trace(go.Scatter(
        x=growth["Idade_anos"], y=growth["ICA_volume"],
        mode="lines+markers", name="ICA",
        line={"color": "#f6c453", "width": 3},
    ))
    fig.update_layout(
        title="Incremento médio anual e incremento corrente",
        xaxis={"title": "Idade (anos)"},
        yaxis={"title": "Incremento de volume"},
    )
    return style_figure(fig, 500)


def fig_stand_productivity(stands: pd.DataFrame) -> go.Figure:
    needed = {"Volume_m3_ha", "AreaBasal_m2_ha", "Talhao"}
    if stands.empty or not needed.issubset(stands.columns):
        return empty_figure()
    fig = px.scatter(
        stands, x="AreaBasal_m2_ha", y="Volume_m3_ha",
        size="Arvores_ha", color="CO2e_t_ha", hover_name="Talhao",
        hover_data=["DAP_medio", "Altura_media", "Especies"],
        title="Produtividade estrutural dos talhões",
        labels={
            "AreaBasal_m2_ha": "Área basal (m²/ha)",
            "Volume_m3_ha": "Volume (m³/ha)",
            "CO2e_t_ha": "CO₂e (t/ha)",
        },
        color_continuous_scale=COLOR_SCALE,
    )
    return style_figure(fig, 520)


def fig_missing_values(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure()
    missing = df.isna().sum().reset_index()
    missing.columns = ["Coluna", "Ausentes"]
    missing["Percentual"] = missing["Ausentes"] / max(len(df), 1) * 100
    missing = missing.sort_values("Ausentes").tail(25)
    fig = px.bar(
        missing, x="Percentual", y="Coluna", orientation="h",
        color="Percentual", title="Completude por coluna",
        labels={"Percentual": "Valores ausentes (%)"},
        color_continuous_scale=COLOR_SCALE, text_auto=".1f",
    )
    return style_figure(fig, 540)


def fig_correlation(correlation: pd.DataFrame) -> go.Figure:
    if correlation.empty:
        return empty_figure("Não há variáveis numéricas suficientes")
    fig = px.imshow(
        correlation, text_auto=".2f", zmin=-1, zmax=1,
        color_continuous_scale=[[0, "#ff6f75"], [0.5, "#102419"], [1, "#39ff88"]],
        title="Correlação entre variáveis biométricas e de carbono",
    )
    return style_figure(fig, 600)


def fig_anomaly(df: pd.DataFrame) -> go.Figure:
    if not {"DAP_cm", "Altura_m", "Status_Anomalia"}.issubset(df.columns):
        return empty_figure()
    fig = px.scatter(
        df, x="DAP_cm", y="Altura_m", color="Status_Anomalia",
        size="Volume_m3" if "Volume_m3" in df.columns else None,
        hover_data=[c for c in ["Talhao", "Especie", "Volume_m3", "Score_Anomalia"] if c in df.columns],
        title="Registros sinalizados pela análise de anomalias",
        color_discrete_map={"Normal": "#39ff88", "Suspeito": "#ff6f75", "Não avaliado": "#8d9a91"},
    )
    return style_figure(fig, 520)


def fig_observed_predicted(predictions: pd.DataFrame) -> go.Figure:
    if predictions.empty:
        return empty_figure()
    maximum = max(
        float(predictions["Volume_m3"].max()),
        float(predictions["Volume_Previsto_ML_m3"].max()),
    )
    fig = px.scatter(
        predictions, x="Volume_m3", y="Volume_Previsto_ML_m3",
        color="Especie",
        hover_data=[c for c in ["Talhao", "DAP_cm", "Altura_m", "Erro_ML_m3"] if c in predictions.columns],
        title="Volume observado × previsto",
        color_discrete_sequence=DEMETER_COLORS,
    )
    fig.add_trace(go.Scatter(
        x=[0, maximum], y=[0, maximum], mode="lines",
        name="Referência 1:1", line={"dash": "dash", "color": "#f6c453"},
    ))
    return style_figure(fig, 500)


def fig_residuals(predictions: pd.DataFrame) -> go.Figure:
    if predictions.empty or "Erro_ML_m3" not in predictions.columns:
        return empty_figure()
    fig = px.scatter(
        predictions, x="Volume_Previsto_ML_m3", y="Erro_ML_m3",
        color="Especie",
        hover_data=[c for c in ["Talhao", "Volume_m3"] if c in predictions.columns],
        title="Resíduos do modelo de volume",
        labels={
            "Volume_Previsto_ML_m3": "Volume previsto (m³)",
            "Erro_ML_m3": "Erro observado − previsto (m³)",
        },
        color_discrete_sequence=DEMETER_COLORS,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#f6c453")
    return style_figure(fig, 480)


def fig_feature_importance(importance: pd.DataFrame) -> go.Figure:
    if importance.empty:
        return empty_figure()
    fig = px.bar(
        importance, x="Importancia", y="Variavel", orientation="h",
        color="Importancia", color_continuous_scale=COLOR_SCALE,
        title="Importância das variáveis no modelo",
    )
    return style_figure(fig, 460)


def fig_clusters(clusters: pd.DataFrame) -> go.Figure:
    if clusters is None or clusters.empty:
        return empty_figure()
    fig = px.scatter(
        clusters, x="Volume_m3", y="CO2e_t", size="Arvores",
        color="Grupo_ML", hover_data=["Talhao", "DAP_medio", "Altura_media"],
        title="Agrupamento de talhões por volume e carbono",
        color_discrete_sequence=DEMETER_COLORS,
    )
    return style_figure(fig, 500)


def fig_cluster_radar(clusters: pd.DataFrame) -> go.Figure:
    if clusters is None or clusters.empty:
        return empty_figure()
    features = ["DAP_medio", "Altura_media", "Volume_m3", "CO2e_t"]
    grouped = clusters.groupby("Grupo_ML")[features].mean()
    normalized = grouped.copy()
    for column in features:
        maximum = float(grouped[column].max())
        normalized[column] = grouped[column] / maximum if maximum > 0 else 0
    fig = go.Figure()
    for group, row in normalized.iterrows():
        values = [float(row[c]) for c in features]
        fig.add_trace(go.Scatterpolar(
            r=values + values[:1], theta=features + features[:1],
            fill="toself", name=f"Grupo {group}",
        ))
    fig.update_layout(
        title="Perfil relativo dos grupos de talhões",
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
    )
    return style_figure(fig, 520)


def fig_climate(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Nenhum dado climático retornado")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["temperature_2m_mean"], mode="lines",
        name="Temperatura média", line={"color": "#f6c453", "width": 2.4},
    ))
    fig.add_trace(go.Bar(
        x=df["time"], y=df["precipitation_sum"], name="Precipitação",
        yaxis="y2", opacity=0.42, marker_color="#39ff88",
    ))
    fig.update_layout(
        title="Série climática histórica",
        yaxis={"title": "Temperatura média (°C)"},
        yaxis2={"title": "Precipitação (mm)", "overlaying": "y", "side": "right"},
    )
    return style_figure(fig, 540)


def fig_water_balance(df: pd.DataFrame) -> go.Figure:
    needed = {"time", "precipitation_sum", "et0_fao_evapotranspiration"}
    if df.empty or not needed.issubset(df.columns):
        return empty_figure()
    work = df.copy()
    work["Balanco_mm"] = (
        pd.to_numeric(work["precipitation_sum"], errors="coerce").fillna(0)
        - pd.to_numeric(work["et0_fao_evapotranspiration"], errors="coerce").fillna(0)
    )
    fig = px.area(
        work, x="time", y="Balanco_mm",
        title="Balanço hídrico climático simplificado (P − ET₀)",
        labels={"time": "Data", "Balanco_mm": "Balanço (mm)"},
        color_discrete_sequence=["#39ff88"],
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#f6c453")
    return style_figure(fig, 480)
