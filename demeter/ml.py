import math
import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

def detect_anomalies(df, contamination=0.06):
    df = df.copy()
    df["Status_Anomalia"] = "Não avaliado"
    df["Score_Anomalia"] = np.nan

    features = [c for c in ["DAP_cm", "Altura_m", "Volume_m3", "AreaBasal_m2", "CO2e_t"] if c in df.columns]
    clean = df[features].replace([np.inf, -np.inf], np.nan).dropna()

    if len(features) < 2 or len(clean) < 25:
        return df

    model = IsolationForest(
        n_estimators=240,
        contamination=min(max(contamination, 0.01), 0.30),
        random_state=42,
    )
    labels = model.fit_predict(clean)
    scores = model.decision_function(clean)

    df.loc[clean.index, "Status_Anomalia"] = np.where(labels == -1, "Suspeito", "Normal")
    df.loc[clean.index, "Score_Anomalia"] = scores
    return df

def train_volume_model(df):
    needed = ["DAP_cm", "Altura_m", "Volume_m3"]
    if not all(col in df.columns for col in needed):
        return None

    model_df = df.dropna(subset=needed).copy()
    if len(model_df) < 45:
        return None

    features = ["DAP_cm", "Altura_m"]
    for col in ["Especie", "Talhao", "Idade_anos", "DensidadeMadeira_t_m3"]:
        if col in model_df.columns:
            features.append(col)

    x = pd.get_dummies(model_df[features], dummy_na=True)
    y = model_df["Volume_m3"]

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)

    model = RandomForestRegressor(
        n_estimators=320,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    model_df["Volume_Previsto_ML_m3"] = model.predict(x)
    model_df["Erro_ML_m3"] = model_df["Volume_Previsto_ML_m3"] - model_df["Volume_m3"]

    importance = (
        pd.DataFrame({"Variavel": x.columns, "Importancia": model.feature_importances_})
        .sort_values("Importancia", ascending=False)
        .head(14)
    )

    return {
        "r2": r2_score(y_test, y_pred),
        "mae": mean_absolute_error(y_test, y_pred),
        "rmse": math.sqrt(mean_squared_error(y_test, y_pred)),
        "predictions": model_df,
        "importance": importance,
    }

def cluster_stands(df, n_clusters=3):
    if "Talhao" not in df.columns:
        return None

    stand_df = (
        df.groupby("Talhao", as_index=False)
        .agg(
            Arvores=("Num_Arvore", "count"),
            DAP_medio=("DAP_cm", "mean"),
            Altura_media=("Altura_m", "mean"),
            Volume_m3=("Volume_m3", "sum"),
            CO2e_t=("CO2e_Expandido_t", "sum"),
        )
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    if len(stand_df) < 3:
        return None

    n_clusters = int(min(max(n_clusters, 2), len(stand_df)))
    features = ["Arvores", "DAP_medio", "Altura_media", "Volume_m3", "CO2e_t"]

    scaled = StandardScaler().fit_transform(stand_df[features])
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    stand_df["Grupo_ML"] = model.fit_predict(scaled).astype(str)

    return stand_df
