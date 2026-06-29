import pandas as pd
import requests

def fetch_open_meteo(latitude, longitude, start_date, end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily": ",".join([
            "temperature_2m_mean",
            "precipitation_sum",
            "et0_fao_evapotranspiration",
            "vapour_pressure_deficit_max",
            "soil_moisture_0_to_7cm_mean",
        ]),
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if "daily" not in payload:
        return pd.DataFrame()

    df = pd.DataFrame(payload["daily"])
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    return df
