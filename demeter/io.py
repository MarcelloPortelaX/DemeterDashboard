import base64
import io
from pathlib import Path
import pandas as pd


def parse_upload(contents, filename):
    if not contents or not filename:
        raise ValueError("Arquivo não informado.")
    _, encoded = contents.split(",", 1)
    raw = base64.b64decode(encoded)
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        # Tenta detectar separador e codificação comuns.
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw), sep=None, engine="python", encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Não foi possível identificar a codificação do CSV.")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(io.BytesIO(raw))
    raise ValueError("Formato não aceito. Use CSV, XLSX ou XLS.")


def df_to_json(df):
    return df.to_json(date_format="iso", orient="split")


def json_to_df(value):
    if value is None:
        return None
    return pd.read_json(io.StringIO(value), orient="split")
