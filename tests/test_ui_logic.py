from pathlib import Path

import pandas as pd

from app import process_data, render_tab, server
from demeter.io import df_to_json
from demeter.schema import standardize_dataframe


def _processed_sample():
    path = Path(__file__).resolve().parents[1] / "data" / "exemplo_teste.csv"
    raw = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    standardized, _ = standardize_dataframe(raw)
    processed, cards = process_data(
        df_to_json(standardized),
        None,
        None,
        ["Normal", "Suspeito", "Não avaliado"],
        10,
        1,
        0.42,
        0.50,
        0.47,
        1.20,
        0.24,
        0.06,
    )
    return processed, cards


def test_home_responds_and_primary_kpis_are_limited():
    response = server.test_client().get("/")
    assert response.status_code == 200

    processed, cards = _processed_sample()
    assert processed
    assert len(cards) == 6
    assert [card.children[0].children for card in cards] == [
        "Árvores",
        "Espécies",
        "Área basal",
        "Volume",
        "CO₂e",
        "Qualidade",
    ]


def test_all_analytical_tabs_render():
    processed, _ = _processed_sample()
    tabs = [
        "overview",
        "inventory",
        "structure",
        "carbon",
        "growth",
        "spatial",
        "quality",
        "ml",
        "climate",
        "data",
    ]
    for tab in tabs:
        result = render_tab(
            tab,
            processed,
            30,
            8,
            15,
            10,
            12,
            5.4,
            3,
            5,
            1,
            10,
            "Random Forest",
        )
        assert result is not None
