"""Helpers for user-facing labels."""

DISPLAY_LABELS = {'Talhao': 'Talhão', 'Parcela': 'Parcela', 'Num_Arvore': 'Árvore', 'Especie': 'Espécie', 'DAP_cm': 'DAP (cm)', 'Altura_m': 'Altura (m)', 'Volume_m3': 'Volume (m³)', 'Coord_X': 'Coordenada X', 'Coord_Y': 'Coordenada Y', 'Idade_anos': 'Idade (anos)', 'DensidadeMadeira_t_m3': 'Densidade da madeira (t/m³)', 'AreaBasal_m2': 'Área basal (m²)', 'BiomassaFuste_t': 'Biomassa do fuste (t)', 'BiomassaAcimaSolo_t': 'Biomassa acima do solo (t)', 'BiomassaRaiz_t': 'Biomassa de raízes (t)', 'BiomassaTotal_t': 'Biomassa total (t)', 'Carbono_tC': 'Carbono (tC)', 'CO2e_t': 'CO₂e (t)', 'CO2e_Expandido_t': 'CO₂e expandido (t)', 'Status_Anomalia': 'Status de anomalia', 'Score_Anomalia': 'Score de anomalia'}

def display_label(column_name):
    """Return a readable label for interface tables and charts."""
    return DISPLAY_LABELS.get(str(column_name), str(column_name).replace('_', ' '))

def rename_for_display(df):
    """Return a copy of a DataFrame with readable column labels."""
    if df is None:
        return df
    return df.rename(columns={col: display_label(col) for col in df.columns})
