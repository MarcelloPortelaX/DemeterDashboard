import unicodedata

EXPECTED_COLUMNS = [
    "Talhao", "Parcela", "Num_Arvore", "Especie",
    "DAP_cm", "Altura_m", "Volume_m3",
    "Coord_X", "Coord_Y", "Idade_anos", "DensidadeMadeira_t_m3",
]

COLUMN_SYNONYMS = {
    "Talhao": ["talhao", "talhão", "stand", "stand_id", "area", "área", "unidade", "projeto"],
    "Parcela": ["parcela", "plot", "plot_id", "amostra", "sample"],
    "Num_Arvore": ["num_arvore", "numero_arvore", "n_arvore", "arvore", "árvore", "tree", "tree_id", "id", "individuo"],
    "Especie": ["especie", "espécie", "species", "sp", "nome_cientifico", "nome_popular"],
    "DAP_cm": ["dap_cm", "dap", "dbh", "diametro", "diâmetro", "diametro_cm", "cap_cm"],
    "Altura_m": ["altura_m", "altura", "height", "h_m", "ht"],
    "Volume_m3": ["volume_m3", "volume", "vol", "vol_m3", "v_m3"],
    "Coord_X": ["coord_x", "x", "utm_x", "longitude", "lon", "long"],
    "Coord_Y": ["coord_y", "y", "utm_y", "latitude", "lat"],
    "Idade_anos": ["idade", "idade_anos", "age", "anos"],
    "DensidadeMadeira_t_m3": ["densidade", "densidade_madeira", "wood_density", "basic_density", "densidade_t_m3"],
}

def normalize_text(value):
    value = str(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace(" ", "_").replace("-", "_").replace("/", "_")
    return "".join(char for char in value if char.isalnum() or char == "_")

def infer_column_mapping(columns):
    normalized_columns = {normalize_text(col): col for col in columns}
    mapping = {}
    used = set()

    for canonical, synonyms in COLUMN_SYNONYMS.items():
        normalized_synonyms = {normalize_text(item) for item in synonyms}
        for normalized, original in normalized_columns.items():
            if original in used:
                continue
            if normalized in normalized_synonyms:
                mapping[original] = canonical
                used.add(original)
                break

    return mapping

def standardize_dataframe(df):
    mapping = infer_column_mapping(df.columns)
    return df.rename(columns=mapping), mapping
