import base64
import io
import pandas as pd

def parse_upload(contents, filename):
    if contents is None:
        raise ValueError("Nenhum arquivo enviado.")

    _content_type, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)

    lower = filename.lower()

    if lower.endswith(".csv"):
        errors = []
        for encoding in ("utf-8-sig", "utf-8", "latin1"):
            try:
                return pd.read_csv(io.StringIO(decoded.decode(encoding)), sep=None, engine="python")
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError("Não consegui ler o CSV. Tente salvar como CSV UTF-8.")

    if lower.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(decoded))

    raise ValueError("Formato não suportado. Use CSV, XLSX ou XLS.")

def df_to_json(df):
    return df.to_json(date_format="iso", orient="split")

def json_to_df(value):
    if value is None:
        return None
    return pd.read_json(io.StringIO(value), orient="split")
