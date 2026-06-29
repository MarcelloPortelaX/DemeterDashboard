import numpy as np
import pandas as pd
from .schema import EXPECTED_COLUMNS

def quality_report(df):
    rows = []

    for col in EXPECTED_COLUMNS:
        if col in df.columns:
            missing = int(df[col].isna().sum())
            status = "OK" if missing == 0 else "Atenção"
            detail = f"{missing} valores ausentes"
        else:
            status = "Ausente"
            detail = "Coluna não encontrada"
        rows.append({"Checagem": col, "Status": status, "Detalhe": detail})

    checks = [
        ("DAP_cm", "DAP <= 0", lambda s: s <= 0),
        ("Altura_m", "Altura <= 0", lambda s: s <= 0),
        ("Volume_m3", "Volume < 0", lambda s: s < 0),
        ("DensidadeMadeira_t_m3", "Densidade fora de faixa", lambda s: (s < 0.1) | (s > 1.2)),
    ]

    for col, name, rule in checks:
        if col in df.columns:
            count = int(rule(df[col]).fillna(False).sum())
            rows.append({
                "Checagem": name,
                "Status": "Atenção" if count else "OK",
                "Detalhe": f"{count} registros",
            })

    if "Status_Anomalia" in df.columns:
        count = int((df["Status_Anomalia"] == "Suspeito").sum())
        rows.append({
            "Checagem": "Anomalias por ML",
            "Status": "Atenção" if count else "OK",
            "Detalhe": f"{count} registros suspeitos",
        })

    return pd.DataFrame(rows)

def quality_score(report):
    if report is None or report.empty:
        return 0
    penalty = 0
    for status in report["Status"]:
        if status == "Ausente":
            penalty += 10
        elif status == "Atenção":
            penalty += 4
    return max(0, 100 - penalty)
