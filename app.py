from __future__ import annotations

import os
import sys
import threading
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path

import dash_ag_grid as dag
import numpy as np
import pandas as pd
from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

from demeter.analytics import (
    advanced_stand_summary,
    correlation_matrix,
    data_profile,
    diameter_classes,
    diversity_metrics,
    forest_structure_metrics,
    growth_summary,
    scenario_sensitivity,
    species_importance,
)
from demeter.carbon import credit_scenario, enrich_carbon
from demeter.climate import fetch_open_meteo
from demeter.figures import (
    fig_anomaly,
    fig_basal_area_by_stand,
    fig_biomass_components,
    fig_carbon_treemap,
    fig_climate,
    fig_cluster_radar,
    fig_clusters,
    fig_co2_by_stand,
    fig_correlation,
    fig_credit_waterfall,
    fig_dap_box_species,
    fig_dap_height,
    fig_diameter_distribution,
    fig_feature_importance,
    fig_growth,
    fig_height_distribution,
    fig_mai_cai,
    fig_missing_values,
    fig_observed_predicted,
    fig_residuals,
    fig_sensitivity,
    fig_spatial_density,
    fig_species_donut,
    fig_species_importance,
    fig_stand_productivity,
    fig_tree_map,
    fig_volume_by_class,
    fig_volume_heatmap,
    fig_water_balance,
)
from demeter.io import df_to_json, json_to_df, parse_upload
from demeter.metrics import (
    filter_inventory,
    kpi_summary,
    prepare_inventory,
    species_summary,
    stand_summary,
)
from demeter.ml import cluster_stands, detect_anomalies, train_volume_model
from demeter.schema import EXPECTED_COLUMNS, standardize_dataframe
from demeter.validation import quality_report, quality_score

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA_DIR = BASE_DIR / "data"

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=str(BASE_DIR / "assets"),
    title="Demeter Dashboard Pro",
)
server = app.server

DISPLAY_LABELS = {
    "Talhao": "Talhão",
    "Parcela": "Parcela",
    "Num_Arvore": "Árvore",
    "Especie": "Espécie",
    "DAP_cm": "DAP (cm)",
    "Altura_m": "Altura (m)",
    "Volume_m3": "Volume (m³)",
    "Volume_Estimado_m3": "Volume estimado (m³)",
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
    "Volume_Previsto_ML_m3": "Volume previsto por IA (m³)",
    "Erro_ML_m3": "Erro do modelo (m³)",
    "Variavel": "Variável",
    "Importancia": "Importância",
    "Ausentes": "Valores ausentes",
    "Coluna": "Coluna",
    "Item": "Item",
    "Status": "Status",
    "Detalhe": "Detalhe",
    "time": "Data",
    "temperature_2m_mean": "Temperatura média (°C)",
    "precipitation_sum": "Precipitação (mm)",
    "et0_fao_evapotranspiration": "ET₀ FAO (mm)",
    "vapour_pressure_deficit_max": "VPD máximo (kPa)",
    "soil_moisture_0_to_7cm_mean": "Umidade do solo 0–7 cm",
}


def nice_label(value):
    return DISPLAY_LABELS.get(str(value), str(value).replace("_", " "))


def fmt(value, decimals=2, suffix=""):
    try:
        if value is None or pd.isna(value) or not np.isfinite(float(value)):
            return "N/A"
    except Exception:
        return "N/A"
    text = (
        f"{float(value):,.{decimals}f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )
    return f"{text}{suffix}"


def metric_card(title, value, subtitle="", tone=""):
    return html.Div(
        className="metric-card" + (f" metric-{tone}" if tone else ""),
        children=[
            html.Div(title, className="metric-title"),
            html.Div(value, className="metric-value"),
            html.Div(subtitle, className="metric-subtitle"),
        ],
    )


def section_heading(title, subtitle):
    return html.Div(
        className="section-heading",
        children=[html.H2(title), html.P(subtitle)],
    )


def module_card(tag, title, text):
    return html.Div(
        className="module-card",
        children=[
            html.Div(tag, className="module-tag"),
            html.H3(title),
            html.P(text),
        ],
    )


def parameter_group(title, children, open=False):
    return html.Details(
        className="parameter-group",
        open=open,
        children=[
            html.Summary(title),
            html.Div(className="parameter-group-body", children=children),
        ],
    )


def dropdown_options(values):
    if isinstance(values, pd.DataFrame):
        if values.shape[1] == 0:
            series = pd.Series(dtype=object)
        else:
            series = (
                values.replace(r"^\s*$", pd.NA, regex=True)
                .bfill(axis=1)
                .iloc[:, 0]
            )
    elif isinstance(values, pd.Series):
        series = values
    else:
        series = pd.Series(values)

    return [
        {"label": str(value).replace("_", " "), "value": str(value)}
        for value in sorted(series.dropna().astype(str).unique())
    ]


def make_grid(df, height="460px", page_size=18):
    if df is None:
        clean = pd.DataFrame()
    else:
        clean = df.replace([np.inf, -np.inf], np.nan).copy()
        # Colunas categóricas não aceitam uma string vazia como nova categoria.
        # Convertemos apenas essas colunas para object antes da serialização.
        for column in clean.select_dtypes(include=["category"]).columns:
            clean[column] = clean[column].astype(object)
        clean = clean.where(pd.notna(clean), "")
    definitions = [
        {
            "field": column,
            "headerName": nice_label(column),
            "filter": True,
            "sortable": True,
            "resizable": True,
            "tooltipField": column,
            "minWidth": 120,
        }
        for column in clean.columns
    ]
    return dag.AgGrid(
        columnDefs=definitions,
        rowData=clean.to_dict("records"),
        defaultColDef={
            "filter": True,
            "sortable": True,
            "resizable": True,
            "floatingFilter": True,
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": page_size,
            "animateRows": True,
            "rowSelection": {"mode": "multiRow"},
            "enableCellTextSelection": True,
            "ensureDomOrder": True,
        },
        csvExportParams={
            "fileName": "demeter_grade.csv",
            "columnSeparator": ";",
        },
        className="ag-theme-alpine-dark demeter-grid",
        style={"height": height, "width": "100%"},
    )


def empty_state(
    title="Comece enviando uma planilha",
    text=(
        "Use CSV, TXT, XLSX ou XLS. O painel reúne inventário, estrutura, "
        "carbono, crescimento, qualidade, IA, clima e exportação."
    ),
):
    return html.Div(
        className="empty-state empty-state-large",
        children=[
            html.H3(title),
            html.P(text),
            html.Div(
                className="module-grid",
                children=[
                    module_card(
                        "1",
                        "Carregar o inventário",
                        "Envie sua planilha ou use a base de demonstração incluída.",
                    ),
                    module_card(
                        "2",
                        "Conferir parâmetros",
                        "Ajuste área, fator de forma, carbono e sensibilidade dos modelos.",
                    ),
                    module_card(
                        "3",
                        "Analisar em profundidade",
                        "Navegue pelos módulos e exporte CSV, Excel ou HTML.",
                    ),
                ],
            ),
        ],
    )


PLOT_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
        "toggleSpikelines",
    ],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "demeter_grafico",
        "height": None,
        "width": None,
        "scale": 2,
    },
}


def chart(figure, class_name="chart"):
    return dcc.Graph(
        figure=figure,
        config=PLOT_CONFIG,
        responsive=True,
        className=class_name,
        style={"width": "100%"},
    )


def panel(title, children, subtitle=None, panel_class="panel"):
    header = html.Div(
        className="panel-header",
        children=[
            html.H3(title),
            html.P(subtitle, className="panel-subtitle") if subtitle else None,
        ],
    )
    body = html.Div(
        className="panel-body",
        children=children if isinstance(children, list) else [children],
    )
    return html.Div(className=panel_class, children=[header, body])


def details_panel(title, children, subtitle=None, open=False):
    return html.Details(
        className="details-panel",
        open=open,
        children=[
            html.Summary(
                children=[
                    html.Span(title, className="details-title"),
                    html.Span(subtitle or "Abrir detalhes", className="details-subtitle"),
                ]
            ),
            html.Div(className="details-body", children=children if isinstance(children, list) else [children]),
        ],
    )


app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Store(id="raw-store"),
        dcc.Store(id="processed-store"),
        dcc.Store(id="source-meta-store"),
        dcc.Download(id="download-csv"),
        dcc.Download(id="download-excel"),
        dcc.Download(id="download-html"),
        dcc.Download(id="download-template"),
        html.Aside(
            className="sidebar",
            children=[
                html.Div(className="brand", children="DEMETER"),
                html.Div(
                    className="brand-subtitle",
                    children="Dashboard Pro · análise florestal avançada",
                ),
                html.Details(
                    className="sidebar-guide",
                    children=[
                        html.Summary("Como usar"),
                        html.Div(
                            className="sidebar-guide-body",
                            children=[
                                html.Div("1. Carregue o inventário"),
                                html.Div("2. Aplique os filtros"),
                                html.Div("3. Abra o módulo necessário"),
                                html.Div("4. Exporte o resultado"),
                            ],
                        ),
                    ],
                ),
                html.Div("Entrada de dados", className="sidebar-section-title"),
                dcc.Upload(
                    id="upload-data",
                    className="upload-box",
                    children=html.Div(
                        [
                            html.Div("Enviar CSV / Excel", className="upload-title"),
                            html.Div("CSV, TXT, XLSX ou XLS", className="upload-subtitle"),
                        ]
                    ),
                    multiple=False,
                ),
                html.Button(
                    "Carregar base de demonstração",
                    id="sample-button",
                    n_clicks=0,
                    className="button button-secondary",
                ),
                html.Div(
                    id="upload-status",
                    className="upload-status",
                    children="Nenhum arquivo carregado.",
                ),
                parameter_group(
                    "Filtros principais",
                    [
                        html.Label("Talhão"),
                        dcc.Dropdown(
                            id="filter-stand",
                            multi=True,
                            className="demeter-dropdown",
                            placeholder="Todos",
                        ),
                        html.Label("Espécie"),
                        dcc.Dropdown(
                            id="filter-species",
                            multi=True,
                            className="demeter-dropdown",
                            placeholder="Todas",
                        ),
                        html.Label("Status de anomalia"),
                        dcc.Dropdown(
                            id="filter-status",
                            multi=True,
                            className="demeter-dropdown",
                            value=["Normal", "Suspeito", "Não avaliado"],
                            options=[
                                {"label": value, "value": value}
                                for value in ["Normal", "Suspeito", "Não avaliado"]
                            ],
                        ),
                    ],
                    open=True,
                ),
                parameter_group(
                    "Inventário e estrutura",
                    [
                        html.Label("Área total do projeto (ha)"),
                        dcc.Input(
                            id="project-area",
                            type="number",
                            value=10,
                            min=0.01,
                            step=0.1,
                            className="input",
                        ),
                        html.Label("Área efetivamente amostrada (ha)"),
                        dcc.Input(
                            id="sample-area",
                            type="number",
                            value=1,
                            min=0.01,
                            step=0.1,
                            className="input",
                        ),
                        html.Label("Fator de forma"),
                        dcc.Input(
                            id="form-factor",
                            type="number",
                            value=0.42,
                            min=0.1,
                            max=1,
                            step=0.01,
                            className="input",
                        ),
                        html.Label("Amplitude da classe de DAP (cm)"),
                        dcc.Input(
                            id="diameter-class-width",
                            type="number",
                            value=5,
                            min=1,
                            max=20,
                            step=1,
                            className="input",
                        ),
                    ],
                ),
                parameter_group(
                    "Biomassa e carbono",
                    [
                        html.Label("Densidade da madeira padrão (t/m³)"),
                        dcc.Input(
                            id="wood-density",
                            type="number",
                            value=0.50,
                            min=0.1,
                            max=1.2,
                            step=0.01,
                            className="input",
                        ),
                        html.Label("Fração de carbono"),
                        dcc.Input(
                            id="carbon-fraction",
                            type="number",
                            value=0.47,
                            min=0.3,
                            max=0.7,
                            step=0.01,
                            className="input",
                        ),
                        html.Label("BEF — expansão de biomassa aérea"),
                        dcc.Input(
                            id="bef",
                            type="number",
                            value=1.20,
                            min=1,
                            max=3,
                            step=0.05,
                            className="input",
                        ),
                        html.Label("Razão raiz / parte aérea"),
                        dcc.Input(
                            id="root-ratio",
                            type="number",
                            value=0.24,
                            min=0,
                            max=1,
                            step=0.01,
                            className="input",
                        ),
                    ],
                ),
                parameter_group(
                    "Cenário de carbono",
                    [
                        html.Label("Baseline (%)"),
                        dcc.Input(id="baseline", type="number", value=30, min=0, max=100, step=1, className="input"),
                        html.Label("Leakage (%)"),
                        dcc.Input(id="leakage", type="number", value=8, min=0, max=100, step=1, className="input"),
                        html.Label("Buffer de risco (%)"),
                        dcc.Input(id="buffer", type="number", value=15, min=0, max=100, step=1, className="input"),
                        html.Label("Incerteza (%)"),
                        dcc.Input(id="uncertainty", type="number", value=10, min=0, max=100, step=1, className="input"),
                        html.Label("Preço (US$/tCO₂e)"),
                        dcc.Input(id="price-usd", type="number", value=12, min=0, step=1, className="input"),
                        html.Label("Câmbio US$ → R$"),
                        dcc.Input(id="usd-brl", type="number", value=5.40, min=1, step=0.1, className="input"),
                    ],
                ),
                parameter_group(
                    "IA e modelagem",
                    [
                        html.Label("Sensibilidade a anomalias"),
                        dcc.Input(id="contamination", type="number", value=0.06, min=0.01, max=0.30, step=0.01, className="input"),
                        html.Label("Número de grupos de talhões"),
                        dcc.Input(id="cluster-count", type="number", value=3, min=2, max=8, step=1, className="input"),
                        html.Label("Algoritmo de volume"),
                        dcc.Dropdown(
                            id="ml-algorithm",
                            className="demeter-dropdown",
                            clearable=False,
                            value="Random Forest",
                            options=[
                                {"label": "Random Forest", "value": "Random Forest"},
                                {"label": "Extra Trees", "value": "Extra Trees"},
                            ],
                        ),
                    ],
                ),
                parameter_group(
                    "Exportar resultados",
                    [
                        html.Div(
                            className="export-grid",
                            children=[
                                html.Button("CSV processado", id="export-csv-button", n_clicks=0, className="button"),
                                html.Button("Excel completo", id="export-excel-button", n_clicks=0, className="button"),
                                html.Button("Relatório HTML", id="export-html-button", n_clicks=0, className="button"),
                                html.Button("Modelo de planilha", id="export-template-button", n_clicks=0, className="button button-secondary"),
                            ],
                        )
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
                        html.Div(
                            "INVENTÁRIO · ESTRUTURA · CARBONO · CRESCIMENTO · IA",
                            className="eyebrow",
                        ),
                        html.H1(["Demeter ", html.Span("Dashboard")]),
                        html.P(
                            "Inventário florestal, estrutura, carbono, crescimento e modelagem em uma leitura modular."
                        ),
                        html.Div(
                            className="hero-badges",
                            children=[
                                html.Span("Local-first"),
                                html.Span("CSV e Excel"),
                                html.Span("Análises avançadas"),
                                html.Span("Exportação completa"),
                            ],
                        ),
                    ],
                ),
                html.Div(id="schema-bar"),
                html.Div(id="kpi-row", className="metrics-grid metrics-grid-wide"),
                dcc.Tabs(
                    id="tabs",
                    value="overview",
                    className="tabs",
                    children=[
                        dcc.Tab(label="Resumo", value="overview", className="tab"),
                        dcc.Tab(label="Inventário", value="inventory", className="tab"),
                        dcc.Tab(label="Estrutura", value="structure", className="tab"),
                        dcc.Tab(label="Carbono", value="carbon", className="tab"),
                        dcc.Tab(label="Crescimento", value="growth", className="tab"),
                        dcc.Tab(label="Espacial", value="spatial", className="tab"),
                        dcc.Tab(label="Qualidade", value="quality", className="tab"),
                        dcc.Tab(label="IA", value="ml", className="tab"),
                        dcc.Tab(label="Clima", value="climate", className="tab"),
                        dcc.Tab(label="Dados", value="data", className="tab"),
                    ],
                ),
                dcc.Loading(
                    type="dot",
                    color="#39ff88",
                    children=html.Div(id="tab-content", className="tab-content"),
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("raw-store", "data"),
    Output("source-meta-store", "data"),
    Output("upload-status", "children"),
    Output("filter-stand", "options"),
    Output("filter-stand", "value"),
    Output("filter-species", "options"),
    Output("filter-species", "value"),
    Output("schema-bar", "children"),
    Input("upload-data", "contents"),
    Input("sample-button", "n_clicks"),
    State("upload-data", "filename"),
)
def load_file(contents, sample_clicks, filename):
    trigger = ctx.triggered_id
    if trigger not in {"upload-data", "sample-button"}:
        schema = html.Div(
            className="data-status-bar data-status-empty",
            children=[
                html.Div(
                    className="data-status-main",
                    children=[
                        html.Span("Nenhum inventário carregado", className="data-status-title"),
                        html.Span("Envie CSV ou Excel, ou carregue a demonstração.", className="data-status-description"),
                    ],
                ),
                html.Div(
                    className="status-chips",
                    children=[
                        html.Span("11 campos reconhecidos", className="status-chip"),
                        html.Span("CSV · XLSX · XLS", className="status-chip"),
                        html.Span("CSV · Excel · HTML", className="status-chip"),
                    ],
                ),
            ],
        )
        return None, None, "Nenhum arquivo carregado.", [], [], [], [], schema

    try:
        if trigger == "sample-button":
            source_path = DATA_DIR / "exemplo_teste.csv"
            raw = pd.read_csv(source_path, sep=";", encoding="utf-8-sig")
            source_name = source_path.name
        else:
            raw = parse_upload(contents, filename)
            source_name = filename or "arquivo"

        standardized, mapping = standardize_dataframe(raw)
        if standardized.empty:
            raise ValueError("A planilha não contém linhas de inventário.")

        stands = dropdown_options(standardized.get("Talhao", pd.Series(dtype=object)))
        species = dropdown_options(standardized.get("Especie", pd.Series(dtype=object)))
        found = [column for column in EXPECTED_COLUMNS if column in standardized.columns]
        missing = [column for column in EXPECTED_COLUMNS if column not in standardized.columns]

        missing_label = ", ".join(nice_label(value) for value in missing[:4]) or "Nenhum"
        schema = html.Div(
            className="data-status-bar",
            children=[
                html.Div(
                    className="data-status-main",
                    children=[
                        html.Span(source_name, className="data-status-title", title=source_name),
                        html.Span(
                            f"{len(standardized):,} linhas · {len(standardized.columns)} colunas".replace(",", "."),
                            className="data-status-description",
                        ),
                    ],
                ),
                html.Div(
                    className="status-chips",
                    children=[
                        html.Span(
                            f"{len(found)}/{len(EXPECTED_COLUMNS)} reconhecidos",
                            className="status-chip status-chip-good",
                        ),
                        html.Span(
                            f"{len(mapping)} aliases ajustados",
                            className="status-chip",
                        ),
                        html.Span(
                            f"{len(missing)} opcionais ausentes",
                            className="status-chip status-chip-muted",
                            title=missing_label,
                        ),
                    ],
                ),
            ],
        )

        meta = {
            "filename": source_name,
            "loaded_at": datetime.now().isoformat(timespec="seconds"),
            "mapping": mapping,
        }
        return (
            df_to_json(standardized),
            meta,
            f"{source_name} carregado: {len(standardized):,} registros.".replace(",", "."),
            stands,
            [option["value"] for option in stands],
            species,
            [option["value"] for option in species],
            schema,
        )
    except Exception as exc:
        error = html.Div(
            className="empty-state error compact-error",
            children=[
                html.Strong("Não foi possível carregar o arquivo."),
                html.Div(str(exc)),
            ],
        )
        return None, None, error, [], [], [], [], no_update


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
    Input("contamination", "value"),
)
def process_data(
    raw_json,
    stands,
    species,
    status,
    project_area,
    sample_area,
    form_factor,
    wood_density,
    carbon_fraction,
    bef,
    root_ratio,
    contamination,
):
    if raw_json is None:
        cards = [
            metric_card("Registros", "0", "aguardando inventário"),
            metric_card("Volume", "0,00 m³", "dados não carregados"),
            metric_card("Área basal", "0,00 m²", "dados não carregados"),
            metric_card("CO₂e", "0,00 t", "dados não carregados"),
            metric_card("Qualidade", "—", "dados não carregados"),
        ]
        return None, cards

    try:
        df = json_to_df(raw_json)
        df = prepare_inventory(df, form_factor or 0.42)
        df = enrich_carbon(
            df,
            project_area or 10,
            sample_area or 1,
            wood_density or 0.50,
            carbon_fraction or 0.47,
            bef or 1.20,
            root_ratio or 0.24,
        )
        df = detect_anomalies(df, contamination or 0.06)
        df = filter_inventory(df, stands, species, status)

        kpis = kpi_summary(df)
        structure = forest_structure_metrics(df, sample_area or 1, project_area or 10)
        diversity = diversity_metrics(df)
        report = quality_report(df)
        score = quality_score(report)
        suspicious = (
            int((df["Status_Anomalia"] == "Suspeito").sum())
            if "Status_Anomalia" in df.columns
            else 0
        )

        cards = [
            metric_card("Árvores", fmt(kpis["registros"], 0), "registros no filtro"),
            metric_card("Espécies", fmt(diversity["riqueza"], 0), f"Shannon {fmt(diversity['shannon'], 2)}"),
            metric_card("Área basal", fmt(structure["area_basal_ha"], 2), "m²/ha"),
            metric_card("Volume", fmt(structure["volume_ha"], 2), "m³/ha"),
            metric_card("CO₂e", fmt(kpis["co2e_total"], 2), "t no projeto", "gold"),
            metric_card("Qualidade", f"{score}/100", f"{suspicious} sinalizados", "danger" if score < 75 else ""),
        ]
        return df_to_json(df), cards
    except Exception as exc:
        return None, [
            html.Div(
                className="empty-state error",
                children=[html.H3("Falha no processamento"), html.P(str(exc))],
            )
        ]


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value"),
    Input("processed-store", "data"),
    Input("baseline", "value"),
    Input("leakage", "value"),
    Input("buffer", "value"),
    Input("uncertainty", "value"),
    Input("price-usd", "value"),
    Input("usd-brl", "value"),
    Input("cluster-count", "value"),
    Input("diameter-class-width", "value"),
    Input("sample-area", "value"),
    Input("project-area", "value"),
    Input("ml-algorithm", "value"),
)
def render_tab(
    tab,
    processed_json,
    baseline,
    leakage,
    buffer,
    uncertainty,
    price_usd,
    usd_brl,
    cluster_count,
    class_width,
    sample_area,
    project_area,
    ml_algorithm,
):
    if processed_json is None:
        return empty_state()

    df = json_to_df(processed_json)
    if df is None or df.empty:
        return empty_state("Nenhum registro no filtro", "Remova algum filtro ou carregue outra base.")

    stands_basic = stand_summary(df)
    stands = advanced_stand_summary(df, sample_area or 1)
    species = species_summary(df)
    diversity = diversity_metrics(df)
    structure = forest_structure_metrics(df, sample_area or 1, project_area or 10)
    classes = diameter_classes(df, class_width or 5)
    importance = species_importance(df)

    if tab == "overview":
        top_stand = stands.iloc[0]["Talhao"] if not stands.empty else "N/A"
        top_species = importance.iloc[0]["Especie"] if not importance.empty else "N/A"
        return html.Div(
            [
                section_heading(
                    "Resumo executivo",
                    "Síntese estrutural, produtiva, florística e de carbono do inventário filtrado.",
                ),
                html.Div(
                    className="insight-grid",
                    children=[
                        module_card(
                            "Estrutura",
                            f"Dq {fmt(structure['dq_cm'], 1)} cm",
                            f"Altura de Lorey: {fmt(structure['altura_lorey'], 1)} m.",
                        ),
                        module_card(
                            "Diversidade",
                            f"Shannon {fmt(diversity['shannon'], 3)}",
                            f"Simpson {fmt(diversity['simpson'], 3)} · {diversity['riqueza']} espécies.",
                        ),
                        module_card(
                            "Destaques",
                            str(top_stand),
                            f"Talhão de maior volume · espécie dominante: {top_species}.",
                        ),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Carbono por talhão", chart(fig_co2_by_stand(stands_basic)), "Comparação do estoque estimado"),
                        panel("Participação por espécie", chart(fig_species_donut(species)), "Composição do recorte atual"),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Produtividade dos talhões", chart(fig_stand_productivity(stands))),
                        panel("Importância ecológica", chart(fig_species_importance(importance))),
                    ],
                ),
                details_panel(
                    "Resumo avançado por talhão",
                    make_grid(stands, "470px"),
                    "Tabela completa e indicadores por talhão",
                ),
            ]
        )

    if tab == "inventory":
        return html.Div(
            [
                section_heading(
                    "Inventário florestal",
                    "Distribuições biométricas, relações hipsométricas e variação entre espécies.",
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Distribuição diamétrica", chart(fig_diameter_distribution(df)), "Frequência de árvores por classe de DAP"),
                        panel("Distribuição de alturas", chart(fig_height_distribution(df)), "Variação vertical por talhão"),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Relação DAP × altura", chart(fig_dap_height(df)), "Padrão hipsométrico dos indivíduos"),
                        panel("DAP por espécie", chart(fig_dap_box_species(df)), "Amplitude e valores atípicos"),
                    ],
                ),
                panel("Matriz de volume", chart(fig_volume_heatmap(df))),
                details_panel("Resumo por espécie", make_grid(species, "430px"), "Tabela e totais por espécie"),
            ]
        )

    if tab == "structure":
        return html.Div(
            [
                section_heading(
                    "Estrutura florestal",
                    "Classes diamétricas, dominância, frequência, densidade e produtividade dos talhões.",
                ),
                html.Div(
                    className="metrics-grid",
                    children=[
                        metric_card("Dq", fmt(structure["dq_cm"], 2, " cm"), "diâmetro quadrático"),
                        metric_card("Altura dominante", fmt(structure["altura_dominante"], 2, " m"), "20% maiores DAPs"),
                        metric_card("Altura de Lorey", fmt(structure["altura_lorey"], 2, " m"), "ponderada por área basal"),
                        metric_card("Volume/ha", fmt(structure["volume_ha"], 2, " m³"), "área amostrada"),
                        metric_card("Equitabilidade", fmt(diversity["equitabilidade"], 3), "Pielou"),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Classes diamétricas", chart(fig_volume_by_class(classes))),
                        panel("Área basal por talhão", chart(fig_basal_area_by_stand(stands))),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("IVI das espécies", chart(fig_species_importance(importance))),
                        panel("Produtividade estrutural", chart(fig_stand_productivity(stands))),
                    ],
                ),
                details_panel("Tabela de classes de DAP", make_grid(classes, "390px"), "Frequência, volume e área basal"),
                details_panel("Índice de valor de importância", make_grid(importance, "440px"), "Densidade, dominância e frequência"),
            ]
        )

    if tab == "carbon":
        credit = credit_scenario(
            df,
            baseline or 0,
            leakage or 0,
            buffer or 0,
            uncertainty or 0,
            price_usd or 0,
            usd_brl or 1,
        )
        sensitivity = scenario_sensitivity(
            credit["co2e_bruto"],
            leakage_pct=leakage or 0,
            uncertainty_pct=uncertainty or 0,
        )
        return html.Div(
            [
                section_heading(
                    "Biomassa, carbono e cenário econômico",
                    "Estimativas exploratórias com decomposição dos componentes e análise de sensibilidade.",
                ),
                html.Div(
                    className="metrics-grid",
                    children=[
                        metric_card("CO₂e bruto", fmt(credit["co2e_bruto"], 2, " t")),
                        metric_card("Baseline", fmt(credit["baseline"], 2, " t")),
                        metric_card("Adicional", fmt(credit["adicional"], 2, " t")),
                        metric_card("Elegível", fmt(credit["elegivel"], 2, " t"), "cenário configurado", "gold"),
                        metric_card("Receita US$", f"US$ {fmt(credit['receita_usd'], 2)}", "estimativa"),
                        metric_card("Receita R$", f"R$ {fmt(credit['receita_brl'], 2)}", "estimativa", "gold"),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Cenário de carbono", chart(fig_credit_waterfall(credit))),
                        panel("Sensibilidade", chart(fig_sensitivity(sensitivity))),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Componentes de biomassa", chart(fig_biomass_components(df))),
                        panel("Carbono por hierarquia", chart(fig_carbon_treemap(df))),
                    ],
                ),
                html.Div(
                    className="method-note",
                    children=[
                        html.Strong("Aviso metodológico: "),
                        "os resultados são exploratórios e não constituem certificação, verificação independente ou emissão de créditos.",
                    ],
                ),
            ]
        )

    if tab == "growth":
        growth = growth_summary(df)
        return html.Div(
            [
                section_heading(
                    "Crescimento e produção",
                    "Leitura exploratória por idade, incremento médio anual e incremento corrente.",
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Trajetória por idade", chart(fig_growth(growth))),
                        panel("IMA e ICA", chart(fig_mai_cai(growth))),
                    ],
                ),
                panel("Produção por talhão", chart(fig_stand_productivity(stands))),
                details_panel(
                    "Tabela de crescimento",
                    make_grid(growth, "440px")
                    if not growth.empty
                    else empty_state(
                        "Idade insuficiente",
                        "Inclua Idade_anos com pelo menos duas idades distintas para calcular incrementos.",
                    ),
                    "Série agrupada por idade",
                ),
            ]
        )

    if tab == "spatial":
        has_coords = {"Coord_X", "Coord_Y"}.issubset(df.columns)
        return html.Div(
            [
                section_heading(
                    "Análise espacial",
                    "Distribuição dos indivíduos, densidade de pontos e comparação espacial entre talhões.",
                ),
                panel(
                    "Mapa de indivíduos",
                    chart(fig_tree_map(df), "chart chart-spatial-main"),
                    "Coordenadas, dimensão dos indivíduos e espécie.",
                    panel_class="panel panel-featured",
                ),
                html.Div(
                    className="two-column two-column-balanced",
                    children=[
                        panel(
                            "Densidade de pontos",
                            chart(fig_spatial_density(df)),
                            "Concentração relativa dos indivíduos no plano.",
                        ),
                        details_panel(
                            "Resumo espacial por talhão",
                            make_grid(stands, "470px"),
                            "Indicadores por área",
                            open=True,
                        ),
                    ],
                ),
                (
                    html.Div(
                        className="method-note",
                        children=[
                            html.Strong("Coordenadas detectadas. "),
                            "O painel usa os valores como plano cartesiano/UTM. Para mapas geográficos, forneça longitude e latitude em graus decimais.",
                        ],
                    )
                    if has_coords
                    else empty_state(
                        "Coordenadas ausentes",
                        "Inclua Coord_X e Coord_Y, longitude/latitude ou UTM X/Y para ativar o módulo espacial.",
                    )
                ),
            ]
        )

    if tab == "quality":
        report = quality_report(df)
        score = quality_score(report)
        correlation = correlation_matrix(df)
        suspicious = (
            df[df["Status_Anomalia"] == "Suspeito"]
            if "Status_Anomalia" in df.columns
            else pd.DataFrame()
        )
        duplicates = int(df.duplicated().sum())
        return html.Div(
            [
                section_heading(
                    "Qualidade e consistência dos dados",
                    "Completude, duplicidades, faixas biométricas, correlações e registros estatisticamente atípicos.",
                ),
                html.Div(
                    className="metrics-grid",
                    children=[
                        metric_card("Score", f"{score}/100", "indicador heurístico"),
                        metric_card("Ausentes", fmt(df.isna().sum().sum(), 0), "células vazias"),
                        metric_card("Duplicados", fmt(duplicates, 0), "linhas idênticas", "danger" if duplicates else ""),
                        metric_card("Sinalizados", fmt(len(suspicious), 0), "anomalias", "danger" if len(suspicious) else ""),
                        metric_card("Colunas", fmt(len(df.columns), 0), "após padronização"),
                    ],
                ),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Completude", chart(fig_missing_values(df)), "Percentual de valores ausentes"),
                        panel("Anomalias biométricas", chart(fig_anomaly(df)), "Triagem estatística de registros"),
                    ],
                ),
                panel("Matriz de correlação", chart(fig_correlation(correlation))),
                html.Div(
                    className="two-column",
                    children=[
                        details_panel("Checklist técnico", make_grid(report, "430px"), "Regras verificadas", open=True),
                        details_panel("Registros sinalizados", make_grid(suspicious, "430px"), "Linhas para revisão"),
                    ],
                ),
            ]
        )

    if tab == "ml":
        model_result = train_volume_model(df, ml_algorithm or "Random Forest")
        clusters = cluster_stands(df, cluster_count or 3)
        children = [
            section_heading(
                "Inteligência artificial e modelagem",
                "Isolation Forest para anomalias, regressão de volume e K-Means para grupos de talhões.",
            ),
            panel("Análise de anomalias", chart(fig_anomaly(df))),
        ]

        if model_result:
            predictions = model_result["predictions"]
            children.extend(
                [
                    html.Div(
                        className="metrics-grid",
                        children=[
                            metric_card("Algoritmo", model_result["algoritmo"], "modelo ativo"),
                            metric_card("R²", fmt(model_result["r2"], 3), "ajuste no conjunto teste"),
                            metric_card("MAE", fmt(model_result["mae"], 4, " m³")),
                            metric_card("RMSE", fmt(model_result["rmse"], 4, " m³")),
                            metric_card("Teste", fmt(len(predictions), 0), "registros avaliados"),
                        ],
                    ),
                    html.Div(
                        className="two-column",
                        children=[
                            panel("Observado × previsto", chart(fig_observed_predicted(predictions))),
                            panel("Resíduos", chart(fig_residuals(predictions))),
                        ],
                    ),
                    panel(
                        "Importância de variáveis",
                        chart(fig_feature_importance(model_result["importance"])),
                    ),
                    details_panel("Predições do conjunto teste", make_grid(predictions, "430px"), "Observado, previsto e erro"),
                ]
            )
        else:
            children.append(
                empty_state(
                    "Modelo de volume não treinado",
                    "São necessários pelo menos 40 registros completos, volume observado e duas variáveis biométricas.",
                )
            )

        if clusters is not None and not clusters.empty:
            children.extend(
                [
                    html.Div(
                        className="two-column",
                        children=[
                            panel("Grupos de talhões", chart(fig_clusters(clusters))),
                            panel("Perfil dos grupos", chart(fig_cluster_radar(clusters))),
                        ],
                    ),
                    details_panel("Tabela de agrupamentos", make_grid(clusters, "400px"), "Métricas dos grupos"),
                ]
            )
        return html.Div(children)

    if tab == "climate":
        default_lat = -21.245
        default_lon = -44.999
        if {"Coord_X", "Coord_Y"}.issubset(df.columns):
            x = pd.to_numeric(df["Coord_X"], errors="coerce")
            y = pd.to_numeric(df["Coord_Y"], errors="coerce")
            if (
                not x.dropna().empty
                and not y.dropna().empty
                and x.dropna().between(-180, 180).all()
                and y.dropna().between(-90, 90).all()
            ):
                default_lon = float(x.mean())
                default_lat = float(y.mean())

        return html.Div(
            [
                section_heading(
                    "Clima",
                    "Consulta histórica pela API Open-Meteo e balanço simplificado entre precipitação e ET₀.",
                ),
                html.Div(
                    className="panel climate-controls",
                    children=[
                        html.Div(
                            [
                                html.Label("Latitude"),
                                dcc.Input(
                                    id="climate-lat",
                                    type="number",
                                    value=default_lat,
                                    step=0.000001,
                                    className="input",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Longitude"),
                                dcc.Input(
                                    id="climate-lon",
                                    type="number",
                                    value=default_lon,
                                    step=0.000001,
                                    className="input",
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Início"),
                                dcc.DatePickerSingle(
                                    id="climate-start",
                                    date=str(date.today() - timedelta(days=365)),
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Label("Fim"),
                                dcc.DatePickerSingle(
                                    id="climate-end",
                                    date=str(date.today() - timedelta(days=7)),
                                ),
                            ]
                        ),
                        html.Button(
                            "Consultar clima",
                            id="climate-button",
                            n_clicks=0,
                            className="button",
                        ),
                    ],
                ),
                dcc.Loading(
                    type="dot",
                    color="#39ff88",
                    children=html.Div(id="climate-output"),
                ),
            ]
        )

    if tab == "data":
        numeric = df.select_dtypes(include=[np.number])
        describe = (
            numeric.describe().T.reset_index().rename(columns={"index": "Variavel"})
            if not numeric.empty
            else pd.DataFrame()
        )
        profile = data_profile(df)
        return html.Div(
            [
                section_heading(
                    "Dados, estatísticas e exportação",
                    "Tabela enriquecida, perfil das colunas e estatísticas descritivas do filtro atual.",
                ),
                html.Div(
                    className="export-callout",
                    children=[
                        html.H3("Exportações completas na barra lateral"),
                        html.P(
                            "CSV processado, Excel com múltiplas planilhas, relatório HTML e modelo de entrada."
                        ),
                    ],
                ),
                details_panel("Dados enriquecidos", make_grid(df, "620px", 25), "Abrir grade completa", open=True),
                html.Div(
                    className="two-column",
                    children=[
                        panel("Perfil das colunas", make_grid(profile, "480px")),
                        panel("Estatísticas descritivas", make_grid(describe, "480px")),
                    ],
                ),
            ]
        )

    return empty_state("Aba não encontrada", "Não foi possível abrir a seção solicitada.")


@app.callback(
    Output("climate-output", "children"),
    Input("climate-button", "n_clicks"),
    State("climate-lat", "value"),
    State("climate-lon", "value"),
    State("climate-start", "date"),
    State("climate-end", "date"),
    prevent_initial_call=True,
)
def update_climate(_clicks, latitude, longitude, start_date, end_date):
    try:
        climate = fetch_open_meteo(latitude, longitude, start_date, end_date)
        if climate.empty:
            return empty_state(
                "Sem dados climáticos",
                "A consulta não retornou dados para o período informado.",
            )

        cards = html.Div(
            className="metrics-grid",
            children=[
                metric_card(
                    "Temperatura",
                    fmt(climate["temperature_2m_mean"].mean(), 2, " °C"),
                    "média do período",
                    "gold",
                ),
                metric_card(
                    "Precipitação",
                    fmt(climate["precipitation_sum"].sum(), 1, " mm"),
                    "acumulada",
                ),
                metric_card(
                    "ET₀",
                    fmt(climate["et0_fao_evapotranspiration"].sum(), 1, " mm"),
                    "total",
                ),
                metric_card(
                    "VPD",
                    fmt(climate["vapour_pressure_deficit_max"].mean(), 2, " kPa"),
                    "média máxima",
                ),
                metric_card(
                    "Umidade do solo",
                    fmt(climate["soil_moisture_0_to_7cm_mean"].mean(), 3),
                    "camada 0–7 cm",
                ),
            ],
        )
        return html.Div(
            [
                cards,
                html.Div(
                    className="two-column",
                    children=[
                        panel("Série histórica", chart(fig_climate(climate))),
                        panel("Balanço hídrico", chart(fig_water_balance(climate))),
                    ],
                ),
                panel("Dados climáticos", make_grid(climate, "430px")),
            ]
        )
    except Exception as exc:
        return html.Div(
            className="empty-state error",
            children=[html.H3("Erro na consulta climática"), html.P(str(exc))],
        )


@app.callback(
    Output("download-csv", "data"),
    Input("export-csv-button", "n_clicks"),
    State("processed-store", "data"),
    prevent_initial_call=True,
)
def export_csv(_clicks, processed_json):
    if not processed_json:
        return no_update
    df = json_to_df(processed_json)
    return dcc.send_data_frame(
        df.to_csv,
        "demeter_dados_processados.csv",
        index=False,
        sep=";",
        decimal=",",
        encoding="utf-8-sig",
    )


@app.callback(
    Output("download-excel", "data"),
    Input("export-excel-button", "n_clicks"),
    State("processed-store", "data"),
    State("sample-area", "value"),
    State("baseline", "value"),
    State("leakage", "value"),
    State("buffer", "value"),
    State("uncertainty", "value"),
    State("price-usd", "value"),
    State("usd-brl", "value"),
    prevent_initial_call=True,
)
def export_excel(
    _clicks,
    processed_json,
    sample_area,
    baseline,
    leakage,
    buffer,
    uncertainty,
    price_usd,
    usd_brl,
):
    if not processed_json:
        return no_update

    df = json_to_df(processed_json)
    stands = advanced_stand_summary(df, sample_area or 1)
    species = species_summary(df)
    importance = species_importance(df)
    quality = quality_report(df)
    profile = data_profile(df)
    credit = credit_scenario(
        df,
        baseline or 0,
        leakage or 0,
        buffer or 0,
        uncertainty or 0,
        price_usd or 0,
        usd_brl or 1,
    )
    parameters = pd.DataFrame(
        [
            {"Parametro": "Baseline (%)", "Valor": baseline},
            {"Parametro": "Leakage (%)", "Valor": leakage},
            {"Parametro": "Buffer (%)", "Valor": buffer},
            {"Parametro": "Incerteza (%)", "Valor": uncertainty},
            {"Parametro": "Preço US$/tCO2e", "Valor": price_usd},
            {"Parametro": "Câmbio US$/R$", "Valor": usd_brl},
            *[
                {"Parametro": key, "Valor": value}
                for key, value in credit.items()
            ],
        ]
    )

    def write_excel(bytes_io):
        with pd.ExcelWriter(bytes_io, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Dados processados", index=False)
            stands.to_excel(writer, sheet_name="Talhões", index=False)
            species.to_excel(writer, sheet_name="Espécies", index=False)
            importance.to_excel(writer, sheet_name="IVI", index=False)
            quality.to_excel(writer, sheet_name="Qualidade", index=False)
            profile.to_excel(writer, sheet_name="Perfil de dados", index=False)
            parameters.to_excel(writer, sheet_name="Cenário carbono", index=False)

    return dcc.send_bytes(write_excel, "demeter_relatorio_completo.xlsx")


@app.callback(
    Output("download-html", "data"),
    Input("export-html-button", "n_clicks"),
    State("processed-store", "data"),
    State("source-meta-store", "data"),
    State("sample-area", "value"),
    State("project-area", "value"),
    prevent_initial_call=True,
)
def export_html(_clicks, processed_json, source_meta, sample_area, project_area):
    if not processed_json:
        return no_update

    df = json_to_df(processed_json)
    structure = forest_structure_metrics(df, sample_area or 1, project_area or 10)
    diversity = diversity_metrics(df)
    stands = advanced_stand_summary(df, sample_area or 1).head(25)
    species = species_importance(df).head(25)
    score = quality_score(quality_report(df))
    source_name = (source_meta or {}).get("filename", "inventário")

    html_report = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Relatório Demeter</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#07110c;color:#e8fff0;margin:0;padding:32px}}
main{{max-width:1200px;margin:auto}}
h1,h2{{color:#39ff88}} .muted{{color:#9bb5a4}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.card{{background:#102419;border:1px solid rgba(57,255,136,.25);border-radius:16px;padding:16px}}
.value{{font-size:1.6rem;font-weight:800;color:#d9ffe6}}
table{{width:100%;border-collapse:collapse;background:#0b1811;margin:14px 0 30px}}
th,td{{border:1px solid rgba(57,255,136,.16);padding:8px;text-align:left}}
th{{background:#164f33}} small{{color:#9bb5a4}}
</style>
</head>
<body><main>
<h1>Demeter Dashboard — Relatório técnico</h1>
<p class="muted">Fonte: {source_name} · gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
<div class="grid">
<div class="card"><small>Registros</small><div class="value">{len(df)}</div></div>
<div class="card"><small>Árvores/ha</small><div class="value">{fmt(structure["arvores_ha"],1)}</div></div>
<div class="card"><small>Dq</small><div class="value">{fmt(structure["dq_cm"],2)} cm</div></div>
<div class="card"><small>Área basal</small><div class="value">{fmt(structure["area_basal_ha"],2)} m²/ha</div></div>
<div class="card"><small>Volume</small><div class="value">{fmt(structure["volume_ha"],2)} m³/ha</div></div>
<div class="card"><small>Espécies</small><div class="value">{diversity["riqueza"]}</div></div>
<div class="card"><small>Shannon</small><div class="value">{fmt(diversity["shannon"],3)}</div></div>
<div class="card"><small>Qualidade</small><div class="value">{score}/100</div></div>
</div>
<h2>Resumo por talhão</h2>
{stands.to_html(index=False, border=0, classes="table")}
<h2>Importância das espécies</h2>
{species.to_html(index=False, border=0, classes="table")}
<p class="muted">Estimativas de biomassa, carbono e cenários são exploratórias e exigem validação técnica para uso oficial.</p>
</main></body></html>"""
    return {
        "content": html_report,
        "filename": "demeter_relatorio.html",
        "type": "text/html",
    }


@app.callback(
    Output("download-template", "data"),
    Input("export-template-button", "n_clicks"),
    prevent_initial_call=True,
)
def export_template(_clicks):
    template_path = DATA_DIR / "modelo_demeter.csv"
    if template_path.exists():
        return dcc.send_file(str(template_path))
    empty = pd.DataFrame(columns=EXPECTED_COLUMNS)
    return dcc.send_data_frame(
        empty.to_csv,
        "modelo_demeter.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("DEMETER_PORT", "8051")))
    url = f"http://127.0.0.1:{port}"
    print(f"Demeter Dashboard disponível em {url}")
    if not os.getenv("PORT") and os.getenv("DEMETER_NO_BROWSER") != "1":
        threading.Timer(1.3, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
