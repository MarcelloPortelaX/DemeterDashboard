# Notas metodológicas

## Volume

Quando `Volume_m3` está ausente, o sistema utiliza:

```text
Volume = área basal × altura × fator de forma
```

A área basal individual é calculada por:

```text
g = π × (DAP / 200)²
```

## Estrutura

- **Dq:** raiz quadrada da média dos DAPs ao quadrado.
- **Altura dominante:** média das alturas associadas aos 20% maiores DAPs.
- **Altura de Lorey:** altura ponderada pela área basal.
- **IVI:** soma da densidade relativa, dominância relativa e frequência relativa.
- **Shannon e Simpson:** indicadores de diversidade florística.

## Biomassa e carbono

```text
Volume × densidade = biomassa do fuste
Biomassa do fuste × BEF = biomassa acima do solo
Biomassa acima do solo × razão raiz/parte aérea = biomassa de raízes
Biomassa total × fração de carbono = carbono
Carbono × 44/12 = CO₂e
```

## Crescimento

O IMA e o ICA são aproximações tabulares baseadas nos volumes agrupados por
idade. Não substituem parcelas permanentes nem modelos de crescimento ajustados.

## IA

- Isolation Forest: triagem de registros atípicos.
- Random Forest / Extra Trees: regressão exploratória de volume.
- K-Means: agrupamento de talhões por similaridade.

Os modelos devem ser validados antes de qualquer decisão operacional.
