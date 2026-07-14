from __future__ import annotations

import base64
import io
from pathlib import Path
import pandas as pd


def _read_csv(raw: bytes) -> pd.DataFrame:
    errors = []
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        for separator in (None, ";", ",", "\t"):
            try:
                kwargs = {"encoding": encoding, "decimal": ",", "thousands": "."}
                if separator is None:
                    kwargs.update({"sep": None, "engine": "python"})
                else:
                    kwargs.update({"sep": separator})
                df = pd.read_csv(io.BytesIO(raw), **kwargs)
                if len(df.columns) > 1 or not df.empty:
                    return df
            except Exception as exc:
                errors.append(exc)
    raise ValueError(
        "Não foi possível interpretar o CSV. Verifique separador, codificação e cabeçalhos."
    ) from (errors[-1] if errors else None)


def parse_upload(contents, filename):
    if not contents or not filename:
        raise ValueError("Arquivo não informado.")
    _, encoded = contents.split(",", 1)
    raw = base64.b64decode(encoded)
    suffix = Path(filename).suffix.lower()

    if suffix in {".csv", ".txt"}:
        df = _read_csv(raw)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(io.BytesIO(raw))
    else:
        raise ValueError("Formato não aceito. Use CSV, TXT, XLSX ou XLS.")

    if len(df.columns) == 0:
        raise ValueError("O arquivo não contém colunas reconhecíveis.")
    if df.empty:
        raise ValueError("A planilha contém cabeçalhos, mas nenhuma linha de dados.")
    return df


def df_to_json(df):
    return df.to_json(date_format="iso", orient="split")


def json_to_df(value):
    if value is None:
        return None
    return pd.read_json(io.StringIO(value), orient="split")
