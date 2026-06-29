# Notas metodológicas

## Inventário florestal

O dashboard calcula métricas exploratórias a partir dos dados fornecidos pelo usuário. Quando o volume individual não está disponível, o sistema pode estimar volume por uma aproximação simples:

```text
Volume = área basal × altura × fator de forma
```

Essa estimativa deve ser tratada como aproximação inicial. Para aplicações técnicas, recomenda-se o uso de equações volumétricas ajustadas por espécie, região, idade, espaçamento e sistema de manejo.

## Biomassa e carbono

A estimativa exploratória segue a estrutura geral:

```text
Volume × densidade da madeira = biomassa do fuste
Biomassa do fuste × BEF = biomassa acima do solo
Biomassa acima do solo × razão raiz/parte aérea = biomassa de raízes
Biomassa total × fração de carbono = carbono
Carbono × 44/12 = CO₂e
```

Os parâmetros devem ser ajustados conforme literatura, espécie, região e objetivo da análise.

## Potencial de carbono

O módulo de potencial de carbono não gera créditos certificados. Ele estima um potencial analítico a partir de parâmetros configuráveis, como baseline, leakage, buffer de risco, incerteza e preço por tonelada de CO₂e.

A geração real de créditos depende de metodologia reconhecida, validação, verificação, adicionalidade, permanência, risco, leakage e registro em padrão aplicável.

## Modelagem e IA

Os modelos incluídos são experimentais e voltados para análise exploratória:

- Detecção de anomalias: identifica registros com comportamento estatístico incomum.
- Previsão de volume: estima volume a partir de variáveis disponíveis quando há dados suficientes.
- Agrupamento de talhões: organiza áreas por similaridade biométrica e de carbono.

Os resultados não devem ser usados isoladamente para decisão técnica sem validação.
