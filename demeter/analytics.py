from __future__ import annotations

import math
import numpy as np
import pandas as pd


def safe_numeric(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def diversity_metrics(df: pd.DataFrame) -> dict[str, float]:
    if df.empty or "Especie" not in df.columns:
        return {"riqueza": 0, "shannon": 0.0, "simpson": 0.0, "equitabilidade": 0.0}
    counts = df["Especie"].fillna("Não informada").astype(str).value_counts()
    total = counts.sum()
    if total <= 0:
        return {"riqueza": 0, "shannon": 0.0, "simpson": 0.0, "equitabilidade": 0.0}
    proportions = counts / total
    shannon = float(-(proportions * np.log(proportions)).sum())
    simpson = float(1 - np.square(proportions).sum())
    richness = int(len(counts))
    evenness = float(shannon / math.log(richness)) if richness > 1 else 1.0
    return {"riqueza": richness, "shannon": shannon, "simpson": simpson, "equitabilidade": evenness}


def forest_structure_metrics(
    df: pd.DataFrame,
    sample_area_ha: float = 1.0,
    project_area_ha: float = 10.0,
) -> dict[str, float]:
    sample_area = max(float(sample_area_ha or 1), 1e-9)
    project_area = max(float(project_area_ha or sample_area), 1e-9)
    dap = safe_numeric(df, "DAP_cm")
    height = safe_numeric(df, "Altura_m")
    basal = safe_numeric(df, "AreaBasal_m2")
    volume = safe_numeric(df, "Volume_m3")

    valid_dap = dap.dropna()
    dq = float(np.sqrt(np.square(valid_dap).mean())) if not valid_dap.empty else 0.0

    dominant_height = 0.0
    if not valid_dap.empty and not height.dropna().empty:
        n_top = max(1, int(math.ceil(len(df) * 0.20)))
        top_index = dap.nlargest(n_top).index
        value = height.loc[top_index].mean(skipna=True)
        dominant_height = 0.0 if pd.isna(value) else float(value)

    lorey_height = 0.0
    if basal.notna().any() and height.notna().any():
        weights = basal.fillna(0)
        denominator = float(weights.sum())
        if denominator > 0:
            lorey_height = float((height.fillna(0) * weights).sum() / denominator)

    trees = int(len(df))
    total_basal = float(basal.sum(skipna=True))
    total_volume = float(volume.sum(skipna=True))
    dap_mean = dap.mean(skipna=True)
    height_mean = height.mean(skipna=True)

    return {
        "arvores": trees,
        "arvores_ha": trees / sample_area,
        "dap_medio": 0.0 if pd.isna(dap_mean) else float(dap_mean),
        "dq_cm": dq,
        "altura_media": 0.0 if pd.isna(height_mean) else float(height_mean),
        "altura_dominante": dominant_height,
        "altura_lorey": lorey_height,
        "area_basal_total": total_basal,
        "area_basal_ha": total_basal / sample_area,
        "volume_total": total_volume,
        "volume_ha": total_volume / sample_area,
        "volume_projeto": total_volume * (project_area / sample_area),
    }


def diameter_classes(df: pd.DataFrame, class_width: float = 5.0) -> pd.DataFrame:
    dap = safe_numeric(df, "DAP_cm")
    valid = df.loc[dap.notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=["Classe_DAP", "Centro_cm", "Arvores", "Volume_m3", "AreaBasal_m2"])

    width = max(float(class_width or 5), 1)
    valid["DAP_cm"] = dap.loc[valid.index]
    max_dap = max(float(valid["DAP_cm"].max()), width)
    upper = math.ceil(max_dap / width) * width + width
    bins = np.arange(0, upper + width, width)
    labels = [f"{int(a)}–{int(b)}" for a, b in zip(bins[:-1], bins[1:])]
    valid["Classe_DAP"] = pd.cut(valid["DAP_cm"], bins=bins, labels=labels, include_lowest=True, right=False)
    codes = valid["Classe_DAP"].cat.codes
    valid["Centro_cm"] = codes.map(lambda code: float(bins[code] + width / 2) if code >= 0 else np.nan)

    for col in ["Volume_m3", "AreaBasal_m2"]:
        if col not in valid.columns:
            valid[col] = np.nan
        valid[col] = pd.to_numeric(valid[col], errors="coerce")

    return (
        valid.groupby(["Classe_DAP", "Centro_cm"], observed=True)
        .agg(Arvores=("DAP_cm", "size"), Volume_m3=("Volume_m3", "sum"), AreaBasal_m2=("AreaBasal_m2", "sum"))
        .reset_index()
    )


def species_importance(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Especie", "Arvores", "AreaBasal_m2", "Parcelas",
        "Densidade_Relativa_pct", "Dominancia_Relativa_pct",
        "Frequencia_Relativa_pct", "IVI",
    ]
    if df.empty or "Especie" not in df.columns:
        return pd.DataFrame(columns=columns)

    work = df.copy()
    work["Especie"] = work["Especie"].fillna("Não informada").astype(str)
    if "Parcela" not in work.columns:
        work["Parcela"] = "Sem parcela"
    if "AreaBasal_m2" not in work.columns:
        work["AreaBasal_m2"] = 0.0
    work["AreaBasal_m2"] = pd.to_numeric(work["AreaBasal_m2"], errors="coerce").fillna(0)

    summary = (
        work.groupby("Especie", dropna=False)
        .agg(Arvores=("Especie", "size"), AreaBasal_m2=("AreaBasal_m2", "sum"), Parcelas=("Parcela", "nunique"))
        .reset_index()
    )
    total_trees = max(float(summary["Arvores"].sum()), 1)
    total_basal = max(float(summary["AreaBasal_m2"].sum()), 1e-12)
    total_frequency = max(float(summary["Parcelas"].sum()), 1)

    summary["Densidade_Relativa_pct"] = summary["Arvores"] / total_trees * 100
    summary["Dominancia_Relativa_pct"] = summary["AreaBasal_m2"] / total_basal * 100
    summary["Frequencia_Relativa_pct"] = summary["Parcelas"] / total_frequency * 100
    summary["IVI"] = summary[
        ["Densidade_Relativa_pct", "Dominancia_Relativa_pct", "Frequencia_Relativa_pct"]
    ].sum(axis=1)
    return summary.sort_values("IVI", ascending=False).reset_index(drop=True)


def advanced_stand_summary(df: pd.DataFrame, sample_area_ha: float = 1.0) -> pd.DataFrame:
    if df.empty or "Talhao" not in df.columns:
        return pd.DataFrame()

    area = max(float(sample_area_ha or 1), 1e-9)
    work = df.copy()
    for col in ["DAP_cm", "Altura_m", "Volume_m3", "AreaBasal_m2", "Carbono_tC", "CO2e_Expandido_t"]:
        if col not in work.columns:
            work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    if "Especie" not in work.columns:
        work["Especie"] = "Não informada"

    grouped = (
        work.groupby("Talhao", dropna=False)
        .agg(
            Arvores=("Talhao", "size"),
            Especies=("Especie", "nunique"),
            DAP_medio=("DAP_cm", "mean"),
            DAP_maximo=("DAP_cm", "max"),
            Altura_media=("Altura_m", "mean"),
            Altura_maxima=("Altura_m", "max"),
            AreaBasal_m2=("AreaBasal_m2", "sum"),
            Volume_m3=("Volume_m3", "sum"),
            Carbono_tC=("Carbono_tC", "sum"),
            CO2e_t=("CO2e_Expandido_t", "sum"),
        )
        .reset_index()
    )
    n_stands = max(len(grouped), 1)
    assumed_area_per_stand = area / n_stands
    grouped["Arvores_ha"] = grouped["Arvores"] / assumed_area_per_stand
    grouped["AreaBasal_m2_ha"] = grouped["AreaBasal_m2"] / assumed_area_per_stand
    grouped["Volume_m3_ha"] = grouped["Volume_m3"] / assumed_area_per_stand
    grouped["CO2e_t_ha"] = grouped["CO2e_t"] / assumed_area_per_stand
    return grouped.sort_values("Volume_m3", ascending=False).reset_index(drop=True)


def growth_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not {"Idade_anos", "Volume_m3"}.issubset(df.columns):
        return pd.DataFrame()

    work = df.copy()
    for col in ["Idade_anos", "Volume_m3", "DAP_cm", "Altura_m"]:
        if col not in work.columns:
            work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=["Idade_anos", "Volume_m3"])
    work = work[work["Idade_anos"] > 0]
    if work.empty:
        return pd.DataFrame()

    grouped = (
        work.groupby("Idade_anos")
        .agg(
            Arvores=("Volume_m3", "size"),
            Volume_total_m3=("Volume_m3", "sum"),
            Volume_medio_m3=("Volume_m3", "mean"),
            DAP_medio_cm=("DAP_cm", "mean"),
            Altura_media_m=("Altura_m", "mean"),
        )
        .reset_index()
        .sort_values("Idade_anos")
    )
    grouped["IMA_volume"] = grouped["Volume_total_m3"] / grouped["Idade_anos"]
    grouped["ICA_volume"] = grouped["Volume_total_m3"].diff() / grouped["Idade_anos"].diff()
    return grouped


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    preferred = [
        "DAP_cm", "Altura_m", "Volume_m3", "AreaBasal_m2", "Idade_anos",
        "DensidadeMadeira_t_m3", "BiomassaTotal_t", "Carbono_tC", "CO2e_t",
    ]
    columns = [col for col in preferred if col in df.columns]
    if len(columns) < 2:
        return pd.DataFrame()
    numeric = df[columns].apply(pd.to_numeric, errors="coerce")
    return numeric.corr(min_periods=3)


def scenario_sensitivity(
    gross_co2e: float,
    baseline_values: list[int] | None = None,
    buffer_values: list[int] | None = None,
    leakage_pct: float = 8,
    uncertainty_pct: float = 10,
) -> pd.DataFrame:
    baseline_values = baseline_values or [0, 10, 20, 30, 40, 50]
    buffer_values = buffer_values or [0, 5, 10, 15, 20, 25, 30]
    rows = []
    total = max(float(gross_co2e or 0), 0)
    for baseline in baseline_values:
        additional = max(total * (1 - baseline / 100), 0)
        for buffer in buffer_values:
            eligible = additional * (
                1 - float(leakage_pct or 0) / 100
                - buffer / 100
                - float(uncertainty_pct or 0) / 100
            )
            rows.append({
                "Baseline_pct": baseline,
                "Buffer_pct": buffer,
                "Elegivel_tCO2e": max(eligible, 0),
            })
    return pd.DataFrame(rows)


def data_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.columns:
        series = df[column]
        numeric = pd.to_numeric(series, errors="coerce")
        is_numeric = numeric.notna().sum() >= max(3, int(len(series) * 0.5))
        rows.append({
            "Coluna": column,
            "Tipo": "Numérica" if is_numeric else str(series.dtype),
            "Registros": len(series),
            "Ausentes": int(series.isna().sum()),
            "Únicos": int(series.nunique(dropna=True)),
            "Mínimo": float(numeric.min()) if is_numeric and numeric.notna().any() else "",
            "Média": float(numeric.mean()) if is_numeric and numeric.notna().any() else "",
            "Máximo": float(numeric.max()) if is_numeric and numeric.notna().any() else "",
        })
    return pd.DataFrame(rows)
