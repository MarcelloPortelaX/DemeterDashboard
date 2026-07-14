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
    features = [c for c in ["DAP_cm", "Altura_m", "Volume_m3"] if c in df.columns]
    valid = df[features].apply(pd.to_numeric, errors="coerce") if features else pd.DataFrame(index=df.index)
    mask = valid.notna().all(axis=1)
    df["Status_Anomalia"] = "Não avaliado"
    df["Score_Anomalia"] = np.nan
    if mask.sum() >= 20 and features:
        model = IsolationForest(contamination=min(max(float(contamination), .01), .30), random_state=42)
        pred = model.fit_predict(valid.loc[mask])
        score = -model.score_samples(valid.loc[mask])
        df.loc[mask, "Status_Anomalia"] = np.where(pred == -1, "Suspeito", "Normal")
        df.loc[mask, "Score_Anomalia"] = score
    return df


def train_volume_model(df):
    features = [c for c in ["DAP_cm", "Altura_m", "Idade_anos", "DensidadeMadeira_t_m3"] if c in df.columns]
    if "Volume_m3" not in df.columns or len(features) < 2:
        return None
    data = df[features + ["Volume_m3", "Talhao", "Especie"]].copy().dropna(subset=features + ["Volume_m3"])
    if len(data) < 45:
        return None
    X, y = data[features], data["Volume_m3"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.25, random_state=42)
    model = RandomForestRegressor(n_estimators=240, min_samples_leaf=2, random_state=42)
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)
    result = data.loc[X_test.index].copy()
    result["Volume_Previsto_ML_m3"] = predicted
    result["Erro_ML_m3"] = result["Volume_m3"] - result["Volume_Previsto_ML_m3"]
    importance = pd.DataFrame({"Variavel": features, "Importancia": model.feature_importances_}).sort_values("Importancia")
    return {"r2": r2_score(y_test, predicted), "mae": mean_absolute_error(y_test, predicted),
            "rmse": math.sqrt(mean_squared_error(y_test, predicted)), "predictions": result, "importance": importance}


def cluster_stands(df, n_clusters=3):
    needed = {"Talhao", "Volume_m3", "CO2e_Expandido_t", "DAP_cm", "Altura_m", "Num_Arvore"}
    if not needed.issubset(df.columns):
        return None
    stand = (df.groupby("Talhao").agg(Arvores=("Num_Arvore", "count"), DAP_medio=("DAP_cm", "mean"),
             Altura_media=("Altura_m", "mean"), Volume_m3=("Volume_m3", "sum"), CO2e_t=("CO2e_Expandido_t", "sum")).reset_index().dropna())
    n_clusters = min(max(int(n_clusters), 2), len(stand))
    if len(stand) < 2:
        return None
    features = ["DAP_medio", "Altura_media", "Volume_m3", "CO2e_t"]
    scaled = StandardScaler().fit_transform(stand[features])
    stand["Grupo_ML"] = (KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(scaled) + 1).astype(str)
    return stand
