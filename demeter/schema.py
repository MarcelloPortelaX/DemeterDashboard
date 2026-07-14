import re
import unicodedata

EXPECTED_COLUMNS = [
    "Talhao", "Parcela", "Num_Arvore", "Especie", "DAP_cm", "Altura_m",
    "Volume_m3", "Coord_X", "Coord_Y", "Idade_anos", "DensidadeMadeira_t_m3",
]

ALIASES = {
    "Talhao": {"talhao", "talhaoes", "stand", "area", "unidade_manejo"},
    "Parcela": {"parcela", "plot", "amostra"},
    "Num_Arvore": {"num_arvore", "numero_arvore", "arvore", "tree", "tree_id", "id_arvore"},
    "Especie": {"especie", "species", "nome_cientifico", "nome_popular"},
    "DAP_cm": {"dap", "dap_cm", "dbh", "dbh_cm", "diametro", "diametro_cm"},
    "Altura_m": {"altura", "altura_m", "height", "height_m", "ht"},
    "Volume_m3": {"volume", "volume_m3", "vol", "vol_m3"},
    "Coord_X": {"coord_x", "x", "longitude", "lon", "utm_x", "easting"},
    "Coord_Y": {"coord_y", "y", "latitude", "lat", "utm_y", "northing"},
    "Idade_anos": {"idade", "idade_anos", "age", "age_years"},
    "DensidadeMadeira_t_m3": {"densidade_madeira", "densidade_madeira_t_m3", "wood_density", "densidade"},
}

def normalize(value):
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return value

def infer_column_mapping(columns):
    lookup = {normalize(alias): canonical for canonical, aliases in ALIASES.items() for alias in aliases}
    mapping = {}
    for column in columns:
        norm = normalize(column)
        if norm in lookup:
            mapping[column] = lookup[norm]
    return mapping

def standardize_dataframe(df):
    mapping = infer_column_mapping(df.columns)
    return df.rename(columns=mapping), mapping
