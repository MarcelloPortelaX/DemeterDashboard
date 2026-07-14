import numpy as np


def enrich_carbon(df, project_area_ha=10, sample_area_ha=1, default_density=0.50,
                  carbon_fraction=0.47, bef=1.20, root_ratio=0.24):
    df = df.copy()
    expansion_factor = float(project_area_ha) / max(float(sample_area_ha), 0.000001)
    if "DensidadeMadeira_t_m3" not in df.columns:
        df["DensidadeMadeira_t_m3"] = default_density
    else:
        df["DensidadeMadeira_t_m3"] = df["DensidadeMadeira_t_m3"].fillna(default_density)
    df["BiomassaFuste_t"] = df["Volume_m3"] * df["DensidadeMadeira_t_m3"]
    df["BiomassaAcimaSolo_t"] = df["BiomassaFuste_t"] * float(bef)
    df["BiomassaRaiz_t"] = df["BiomassaAcimaSolo_t"] * float(root_ratio)
    df["BiomassaTotal_t"] = df["BiomassaAcimaSolo_t"] + df["BiomassaRaiz_t"]
    df["Carbono_tC"] = df["BiomassaTotal_t"] * float(carbon_fraction)
    df["CO2e_t"] = df["Carbono_tC"] * (44 / 12)
    df["CO2e_Expandido_t"] = df["CO2e_t"] * expansion_factor
    df["Fator_Expansao_Area"] = expansion_factor
    return df


def credit_scenario(df, baseline_pct=30, leakage_pct=8, buffer_pct=15, uncertainty_pct=10, price_usd=12, usd_brl=5.40):
    total = float(df["CO2e_Expandido_t"].replace([np.inf, -np.inf], np.nan).sum(skipna=True))
    baseline = total * float(baseline_pct) / 100
    additional = max(total - baseline, 0)
    leakage = additional * float(leakage_pct) / 100
    buffer = additional * float(buffer_pct) / 100
    uncertainty = additional * float(uncertainty_pct) / 100
    eligible = max(additional - leakage - buffer - uncertainty, 0)
    return {"co2e_bruto": total, "baseline": baseline, "adicional": additional, "leakage": leakage,
            "buffer": buffer, "incerteza": uncertainty, "elegivel": eligible,
            "receita_usd": eligible * float(price_usd), "receita_brl": eligible * float(price_usd) * float(usd_brl)}
