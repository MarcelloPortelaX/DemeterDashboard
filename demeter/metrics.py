import math
import numpy as np
import pandas as pd

NUMERIC_COLUMNS = ["DAP_cm", "Altura_m", "Volume_m3", "Coord_X", "Coord_Y", "Idade_anos", "DensidadeMadeira_t_m3"]


def coerce_numeric(df, column):
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")


def prepare_inventory(df, form_factor=0.42):
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        coerce_numeric(df, col)
    if "Talhao" not in df.columns:
        df["Talhao"] = "Projeto único"
    if "Especie" not in df.columns:
        df["Especie"] = "Não informada"
    if "Parcela" not in df.columns:
        df["Parcela"] = "Sem parcela"
    if "Num_Arvore" not in df.columns:
        df["Num_Arvore"] = np.arange(1, len(df) + 1)
    if "DAP_cm" in df.columns:
        df["AreaBasal_m2"] = math.pi * (df["DAP_cm"] / 200) ** 2
    else:
        df["AreaBasal_m2"] = np.nan
    if "Volume_m3" not in df.columns:
        df["Volume_m3"] = np.nan
    if {"DAP_cm", "Altura_m"}.issubset(df.columns):
        estimated = df["AreaBasal_m2"] * df["Altura_m"] * float(form_factor)
        df["Volume_m3"] = df["Volume_m3"].fillna(estimated)
    return df


def filter_inventory(df, stands=None, species=None, status=None):
    result = df.copy()
    if stands:
        result = result[result["Talhao"].astype(str).isin([str(v) for v in stands])]
    if species:
        result = result[result["Especie"].astype(str).isin([str(v) for v in species])]
    if status and "Status_Anomalia" in result.columns:
        result = result[result["Status_Anomalia"].isin(status)]
    return result


def kpi_summary(df):
    def total(col):
        return float(pd.to_numeric(df.get(col, pd.Series(dtype=float)), errors="coerce").sum())
    return {
        "registros": len(df),
        "volume_total": total("Volume_m3"),
        "carbono_total": total("Carbono_tC"),
        "co2e_total": total("CO2e_Expandido_t"),
    }


def stand_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["Talhao", "Arvores", "DAP_medio", "Altura_media", "Volume_m3", "Carbono_tC", "CO2e_t"])
    return (df.groupby("Talhao", dropna=False)
        .agg(Arvores=("Num_Arvore", "count"), DAP_medio=("DAP_cm", "mean"), Altura_media=("Altura_m", "mean"),
             Volume_m3=("Volume_m3", "sum"), Carbono_tC=("Carbono_tC", "sum"), CO2e_t=("CO2e_Expandido_t", "sum"))
        .reset_index().sort_values("CO2e_t", ascending=False))


def species_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["Especie", "Arvores", "Volume_m3", "Carbono_tC", "CO2e_t"])
    return (df.groupby("Especie", dropna=False)
        .agg(Arvores=("Num_Arvore", "count"), Volume_m3=("Volume_m3", "sum"),
             Carbono_tC=("Carbono_tC", "sum"), CO2e_t=("CO2e_Expandido_t", "sum"))
        .reset_index().sort_values("CO2e_t", ascending=False))
