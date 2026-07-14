from __future__ import annotations

import math
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import ExtraTreesRegressor, IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def detect_anomalies(df, contamination=0.06):
    df = df.copy()
    features = [
        c for c in ["DAP_cm", "Altura_m", "Volume_m3", "AreaBasal_m2"]
        if c in df.columns
    ]
    valid = (
        df[features].apply(pd.to_numeric, errors="coerce")
        if features else pd.DataFrame(index=df.index)
    )
    mask = valid.notna().all(axis=1)
    df["Status_Anomalia"] = "Não avaliado"
    df["Score_Anomalia"] = np.nan

    if mask.sum() >= 20 and features:
        model = IsolationForest(
            n_estimators=260,
            contamination=min(max(float(contamination or 0.06), 0.01), 0.30),
            random_state=42,
        )
        prediction = model.fit_predict(valid.loc[mask])
        score = -model.score_samples(valid.loc[mask])
        df.loc[mask, "Status_Anomalia"] = np.where(
            prediction == -1, "Suspeito", "Normal"
        )
        df.loc[mask, "Score_Anomalia"] = score
    return df


def train_volume_model(df, algorithm="Random Forest"):
    features = [
        c for c in [
            "DAP_cm", "Altura_m", "Idade_anos",
            "DensidadeMadeira_t_m3", "AreaBasal_m2",
        ] if c in df.columns
    ]
    if "Volume_m3" not in df.columns or len(features) < 2:
        return None

    meta = [c for c in ["Talhao", "Especie", "Parcela", "Num_Arvore"] if c in df.columns]
    data = df[features + ["Volume_m3"] + meta].copy()
    for column in features + ["Volume_m3"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=features + ["Volume_m3"])
    if len(data) < 40:
        return None

    X, y = data[features], data["Volume_m3"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    if algorithm == "Extra Trees":
        model = ExtraTreesRegressor(
            n_estimators=360, min_samples_leaf=2,
            random_state=42, n_jobs=-1,
        )
    else:
        model = RandomForestRegressor(
            n_estimators=360, min_samples_leaf=2,
            max_features=0.9, random_state=42, n_jobs=-1,
        )

    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    result = data.loc[X_test.index].copy()
    result["Volume_Previsto_ML_m3"] = predicted
    result["Erro_ML_m3"] = result["Volume_m3"] - result["Volume_Previsto_ML_m3"]
    importance = (
        pd.DataFrame({"Variavel": features, "Importancia": model.feature_importances_})
        .sort_values("Importancia")
        .reset_index(drop=True)
    )
    return {
        "algoritmo": algorithm,
        "r2": r2_score(y_test, predicted),
        "mae": mean_absolute_error(y_test, predicted),
        "rmse": math.sqrt(mean_squared_error(y_test, predicted)),
        "predictions": result,
        "importance": importance,
    }


def cluster_stands(df, n_clusters=3):
    needed = {
        "Talhao", "Volume_m3", "CO2e_Expandido_t",
        "DAP_cm", "Altura_m", "Num_Arvore",
    }
    if not needed.issubset(df.columns):
        return None

    stand = (
        df.groupby("Talhao")
        .agg(
            Arvores=("Num_Arvore", "count"),
            DAP_medio=("DAP_cm", "mean"),
            Altura_media=("Altura_m", "mean"),
            Volume_m3=("Volume_m3", "sum"),
            CO2e_t=("CO2e_Expandido_t", "sum"),
        )
        .reset_index()
        .dropna()
    )
    if len(stand) < 2:
        return None

    n_clusters = min(max(int(n_clusters or 3), 2), len(stand))
    features = ["DAP_medio", "Altura_media", "Volume_m3", "CO2e_t"]
    scaled = StandardScaler().fit_transform(stand[features])
    stand["Grupo_ML"] = (
        KMeans(n_clusters=n_clusters, random_state=42, n_init=20)
        .fit_predict(scaled) + 1
    ).astype(str)
    return stand
