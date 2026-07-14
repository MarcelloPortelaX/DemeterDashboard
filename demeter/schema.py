from __future__ import annotations

import re
import unicodedata
import pandas as pd

EXPECTED_COLUMNS = [
    "Talhao", "Parcela", "Num_Arvore", "Especie", "DAP_cm", "Altura_m",
    "Volume_m3", "Coord_X", "Coord_Y", "Idade_anos", "DensidadeMadeira_t_m3",
]

ALIASES = {
    "Talhao": {"talhao", "talhoes", "stand", "area", "unidade_manejo", "unidade_de_manejo", "projeto"},
    "Parcela": {"parcela", "plot", "amostra", "sample_plot"},
    "Num_Arvore": {"num_arvore", "numero_arvore", "arvore", "tree", "tree_id", "id_arvore", "individuo"},
    "Especie": {"especie", "species", "nome_cientifico", "nome_popular", "taxon"},
    "DAP_cm": {"dap", "dap_cm", "dbh", "dbh_cm", "diametro", "diametro_cm", "circunferencia_convertida"},
    "Altura_m": {"altura", "altura_m", "height", "height_m", "ht", "altura_total"},
    "Volume_m3": {"volume", "volume_m3", "vol", "vol_m3", "volume_individual"},
    "Coord_X": {"coord_x", "x", "longitude", "lon", "utm_x", "easting", "long"},
    "Coord_Y": {"coord_y", "y", "latitude", "lat", "utm_y", "northing"},
    "Idade_anos": {"idade", "idade_anos", "age", "age_years", "idade_povoamento"},
    "DensidadeMadeira_t_m3": {
        "densidade_madeira", "densidade_madeira_t_m3", "wood_density",
        "densidade", "basic_density",
    },
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")


def infer_column_mapping(columns):
    lookup = {
        normalize(alias): canonical
        for canonical, aliases in ALIASES.items()
        for alias in aliases
    }
    mapping = {}
    for column in columns:
        norm = normalize(column)
        if norm in lookup:
            mapping[column] = lookup[norm]
    return mapping


def standardize_dataframe(df):
    """Padroniza nomes e consolida aliases repetidos em uma única coluna."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Os dados carregados não formam uma tabela válida.")
    mapping = infer_column_mapping(df.columns)
    renamed = df.rename(columns=mapping)
    if renamed.columns.is_unique:
        return renamed, mapping

    consolidated = pd.DataFrame(index=renamed.index)
    ordered_columns = list(dict.fromkeys(renamed.columns))
    for column in ordered_columns:
        matching = renamed.loc[:, renamed.columns == column]
        if matching.shape[1] == 1:
            consolidated[column] = matching.iloc[:, 0]
            continue
        matching = matching.replace(r"^\s*$", pd.NA, regex=True)
        consolidated[column] = matching.bfill(axis=1).iloc[:, 0]
    return consolidated, mapping
