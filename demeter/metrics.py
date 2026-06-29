import math
import numpy as np
import pandas as pd

def coerce_numeric(df, column):
    if column not in df.columns:
        return df
    df[column] = (
        df[column]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .str.replace(" ", "", regex=False)
    )
    df[column] = pd.to_numeric(df[column], errors="coerce")
    return df

def prepare_inventory(df, form_factor=0.42):
    df = df.copy()

    defaults = {
        "Talhao": "Projeto único",
        "Parcela": "P01",
        "Especie": "Não informada",
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    if "Num_Arvore" not in df.columns:
        df["Num_Arvore"] = np.arange(1, len(df) + 1)

    for col in ["DAP_cm", "Altura_m", "Volume_m3", "Coord_X", "Coord_Y", "Idade_anos", "DensidadeMadeira_t_m3"]:
        df = coerce_numeric(df, col)

    if "DAP_cm" in df.columns:
        df["Classe_DAP"] = pd.cut(
            df["DAP_cm"],
            bins=[0, 5, 10, 15, 20, 25, 30, 40, 60, 1000],
            labels=["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-40", "40-60", "60+"],
            include_lowest=True,
        )
    else:
        df["Classe_DAP"] = "N/A"

    if "DAP_cm" in df.columns and "Altura_m" in df.columns:
        df["AreaBasal_m2"] = math.pi * (df["DAP_cm"] / 200) ** 2
    else:
        df["AreaBasal_m2"] = np.nan

    if "Volume_m3" not in df.columns:
        df["Volume_m3"] = np.nan

    if "DAP_cm" in df.columns and "Altura_m" in df.columns:
        missing = df["Volume_m3"].isna()
        df.loc[missing, "Volume_m3"] = df.loc[missing, "AreaBasal_m2"] * df.loc[missing, "Altura_m"] * form_factor

    return df

def filter_inventory(df, stands=None, species=None, status=None):
    out = df.copy()
    if stands:
        out = out[out["Talhao"].astype(str).isin(stands)]
    if species:
        out = out[out["Especie"].astype(str).isin(species)]
    if status and "Status_Anomalia" in out.columns:
        out = out[out["Status_Anomalia"].astype(str).isin(status)]
    return out

def kpi_summary(df):
    return {
        "registros": len(df),
        "arvores": df["Num_Arvore"].nunique() if "Num_Arvore" in df.columns else len(df),
        "dap_medio": df["DAP_cm"].mean() if "DAP_cm" in df.columns else np.nan,
        "altura_media": df["Altura_m"].mean() if "Altura_m" in df.columns else np.nan,
        "volume_total": df["Volume_m3"].sum(skipna=True) if "Volume_m3" in df.columns else np.nan,
        "area_basal_total": df["AreaBasal_m2"].sum(skipna=True) if "AreaBasal_m2" in df.columns else np.nan,
        "co2e_total": df["CO2e_Expandido_t"].sum(skipna=True) if "CO2e_Expandido_t" in df.columns else np.nan,
    }

def stand_summary(df):
    return (
        df.groupby("Talhao", as_index=False)
        .agg(
            Arvores=("Num_Arvore", "count"),
            Especies=("Especie", "nunique"),
            DAP_medio=("DAP_cm", "mean"),
            Altura_media=("Altura_m", "mean"),
            AreaBasal_m2=("AreaBasal_m2", "sum"),
            Volume_m3=("Volume_m3", "sum"),
            Carbono_tC=("Carbono_tC", "sum"),
            CO2e_t=("CO2e_Expandido_t", "sum"),
        )
        .sort_values("CO2e_t", ascending=False)
    )

def species_summary(df):
    return (
        df.groupby("Especie", as_index=False)
        .agg(
            Arvores=("Num_Arvore", "count"),
            Talhoes=("Talhao", "nunique"),
            DAP_medio=("DAP_cm", "mean"),
            Altura_media=("Altura_m", "mean"),
            Volume_m3=("Volume_m3", "sum"),
            Carbono_tC=("Carbono_tC", "sum"),
            CO2e_t=("CO2e_Expandido_t", "sum"),
        )
        .sort_values("CO2e_t", ascending=False)
    )
