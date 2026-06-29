# Demeter Dashboard

Dashboard técnico em Python para análise exploratória de inventários florestais.

O projeto organiza dados tabulares em módulos de leitura: resumo executivo, inventário florestal, biomassa e carbono, qualidade dos dados, modelagem inicial e clima. O objetivo é apoiar interpretação, visualização e identificação de inconsistências em dados florestais.

## Funcionalidades

- Upload de arquivos CSV, XLSX e XLS
- Padronização automática de nomes de colunas
- Filtros por talhão, espécie e status de anomalia
- Indicadores de inventário florestal
- Estimativas exploratórias de biomassa, carbono e CO₂e
- Estimativa de potencial de carbono com parâmetros configuráveis
- Visualizações interativas com Plotly
- Tabelas interativas com Dash AG Grid
- Detecção experimental de anomalias
- Agrupamento exploratório de talhões
- Consulta climática por coordenadas

## Módulos da interface

### 1. Resumo executivo

Apresenta os principais indicadores do conjunto de dados, como número de registros, volume total, carbono estimado, CO₂e e alertas gerais.

### 2. Inventário florestal

Reúne análises de DAP, altura, volume, área basal, distribuição diamétrica, espécies, talhões e coordenadas, quando disponíveis.

### 3. Biomassa e carbono

Apresenta estimativas exploratórias de biomassa, carbono e CO₂e com parâmetros ajustáveis, como densidade da madeira, fração de carbono, fator de expansão de biomassa e razão raiz/parte aérea.

### 4. Qualidade dos dados

Verifica colunas ausentes, valores inválidos, inconsistências numéricas e registros potencialmente suspeitos.

### 5. Modelagem e IA

Inclui modelos experimentais para detecção de anomalias, previsão exploratória de volume e agrupamento de talhões por similaridade.

### 6. Clima

Consulta dados climáticos históricos por latitude, longitude e intervalo de datas.

### 7. Tabelas

Exibe os dados tratados e enriquecidos após o processamento.

## Tecnologias

- Python
- Dash
- Plotly
- Pandas
- NumPy
- Scikit-learn
- Dash AG Grid
- Requests
- OpenPyXL

## Como executar

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente virtual no Windows:

```bash
.venv\Scripts\activate.bat
```

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Execute o dashboard:

```bash
python app.py
```

Acesse no navegador:

```text
http://127.0.0.1:8050
```

## Dados esperados

A planilha pode conter colunas como:

| Coluna | Descrição |
|---|---|
| Talhao | Identificação do talhão ou área |
| Parcela | Identificação da parcela |
| Num_Arvore | Identificação do indivíduo |
| Especie | Nome da espécie |
| DAP_cm | Diâmetro à altura do peito, em cm |
| Altura_m | Altura da árvore, em m |
| Volume_m3 | Volume individual, em m³ |
| Coord_X | Coordenada X, longitude ou UTM X |
| Coord_Y | Coordenada Y, latitude ou UTM Y |
| Idade_anos | Idade do povoamento ou indivíduo |
| DensidadeMadeira_t_m3 | Densidade básica da madeira, em t/m³ |

O sistema tenta reconhecer variações como `DAP`, `dbh`, `height`, `species`, `stand`, `plot`, `latitude` e `longitude`.

## Aviso metodológico

As estimativas de biomassa, carbono, CO₂e e potencial de carbono são exploratórias. Os resultados dependem dos dados de entrada, dos parâmetros definidos pelo usuário e das simplificações adotadas no modelo.

O sistema não substitui inventário técnico oficial, equações locais ajustadas, validação de campo, auditoria independente ou metodologia certificada de crédito de carbono.

## Status

Projeto em desenvolvimento.
