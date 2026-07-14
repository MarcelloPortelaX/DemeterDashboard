import pandas as pd
from .schema import EXPECTED_COLUMNS


def quality_report(df):
    rows = []
    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            rows.append({"Item": col, "Status": "Ausente", "Detalhe": "Coluna não encontrada"})
        else:
            missing = int(df[col].isna().sum())
            status = "OK" if missing == 0 else "Atenção"
            rows.append({"Item": col, "Status": status, "Detalhe": f"{missing} valor(es) ausente(s)"})
    rules = [("DAP_cm", 0, 400), ("Altura_m", 0, 120), ("Volume_m3", 0, None)]
    for col, lower, upper in rules:
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            invalid = int((s <= lower).sum())
            if upper is not None:
                invalid += int((s > upper).sum())
            rows.append({"Item": f"Faixa de {col}", "Status": "OK" if invalid == 0 else "Atenção", "Detalhe": f"{invalid} registro(s) fora da faixa"})
    return pd.DataFrame(rows)


def quality_score(report):
    penalty = 0
    for status in report.get("Status", []):
        penalty += 10 if status == "Ausente" else 4 if status == "Atenção" else 0
    return max(0, 100 - penalty)
