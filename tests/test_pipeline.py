from pathlib import Path

import pandas as pd

from demeter.analytics import (
    diversity_metrics,
    diameter_classes,
    forest_structure_metrics,
    species_importance,
)
from demeter.carbon import enrich_carbon
from demeter.metrics import prepare_inventory
from demeter.ml import detect_anomalies
from demeter.schema import standardize_dataframe


def load_sample():
    path = Path(__file__).resolve().parents[1] / "data" / "exemplo_teste.csv"
    return pd.read_csv(path, sep=";", encoding="utf-8-sig")


def test_pipeline():
    raw = load_sample()
    standardized, _ = standardize_dataframe(raw)
    prepared = prepare_inventory(standardized)
    carbon = enrich_carbon(prepared)
    analyzed = detect_anomalies(carbon)

    assert not analyzed.empty
    assert "CO2e_Expandido_t" in analyzed.columns
    assert "Status_Anomalia" in analyzed.columns
    assert forest_structure_metrics(analyzed)["volume_total"] > 0
    assert diversity_metrics(analyzed)["riqueza"] > 0
    assert not diameter_classes(analyzed).empty
    assert not species_importance(analyzed).empty


def test_duplicate_aliases_are_consolidated():
    raw = pd.DataFrame(
        {
            "Talhao": ["T1", None],
            "stand": [None, "T2"],
            "DAP": [20, 22],
            "Altura": [15, 16],
        }
    )
    standardized, _ = standardize_dataframe(raw)
    assert standardized.columns.is_unique
    assert standardized["Talhao"].tolist() == ["T1", "T2"]
