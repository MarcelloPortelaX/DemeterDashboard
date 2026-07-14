# Demeter Dashboard Pro — UX revisada

Dashboard local e modular para análise exploratória de inventários florestais.

Esta versão restaura a arquitetura rica do Demeter: vários módulos, grande
quantidade de gráficos, tabelas interativas, filtros, parâmetros técnicos e
modelos estatísticos. O visual verde escuro original foi preservado.

## Módulos

1. **Resumo executivo**
   - indicadores estruturais e de carbono;
   - diversidade de Shannon, Simpson e equitabilidade;
   - produtividade por talhão;
   - Índice de Valor de Importância.

2. **Inventário**
   - distribuição diamétrica e de alturas;
   - relação DAP × altura;
   - boxplots por espécie;
   - matriz de volume espécie × talhão.

3. **Estrutura florestal**
   - Dq, altura dominante e altura de Lorey;
   - árvores, área basal e volume por hectare;
   - classes diamétricas;
   - densidade, dominância, frequência e IVI.

4. **Carbono**
   - biomassa do fuste, parte aérea, raízes e total;
   - carbono e CO₂e;
   - baseline, leakage, buffer e incerteza;
   - receita estimada e matriz de sensibilidade.

5. **Crescimento**
   - séries por idade;
   - incremento médio anual;
   - incremento corrente;
   - produtividade de talhões.

6. **Espacial**
   - mapa cartesiano/UTM dos indivíduos;
   - densidade espacial;
   - resumo espacial por talhão.

7. **Qualidade**
   - completude;
   - duplicidades;
   - faixas inválidas;
   - correlações;
   - Isolation Forest.

8. **IA**
   - Random Forest e Extra Trees;
   - observado × previsto;
   - resíduos;
   - importância das variáveis;
   - K-Means e radar dos grupos.

9. **Clima**
   - consulta Open-Meteo;
   - temperatura, precipitação, ET₀, VPD e umidade;
   - balanço hídrico simplificado.

10. **Dados**
    - grade interativa;
    - perfil das colunas;
    - estatísticas descritivas;
    - exportação CSV, Excel e HTML.

## Abrir

Dê dois cliques em:

```text
ABRIR_DEMETER.bat
```

Na primeira execução, o BAT cria `.venv` e instala as bibliotecas sozinho.
O Demeter abre em:

```text
http://127.0.0.1:8051
```

O ClaraJuris pode continuar na porta 8050.

## Publicar no GitHub

Dê dois cliques em:

```text
PUBLICAR_NO_GITHUB.bat
```

O BAT:

- clona o repositório atual em uma pasta temporária;
- substitui os arquivos pela versão desta pasta;
- cria o commit;
- envia para `main`;
- abre o repositório no navegador.

Não é necessário digitar comandos. O Git poderá abrir o navegador apenas para
autenticação, caso a conta ainda não esteja conectada no computador.

## Executável sem Python

Depois do push, abra **Actions → Gerar executável Windows → Run workflow**.
Baixe o artefato `DemeterDashboard-Windows`.

## Aviso

As estimativas de biomassa, carbono, CO₂e e potencial econômico são
exploratórias. O sistema não substitui inventário oficial, equações locais,
validação de campo, auditoria ou metodologia certificada.


## Revisão de experiência

A interface usa hierarquia progressiva: seis indicadores principais, status do
arquivo em uma barra compacta, títulos únicos nos painéis e tabelas avançadas
disponíveis sob demanda. As dez áreas analíticas e as exportações continuam no
projeto; somente a apresentação foi reorganizada para reduzir sobreposição e
carga visual.

### O que mudou visualmente

- a faixa do arquivo foi condensada em uma linha de status;
- o topo mostra apenas seis KPIs essenciais;
- métricas secundárias permanecem nas abas correspondentes;
- os títulos não são repetidos dentro dos gráficos;
- o mapa espacial ocupa a largura principal;
- tabelas extensas ficam em seções expansíveis;
- a navegação horizontal rola em telas menores sem esmagar os nomes;
- os gráficos continuam responsivos e exportáveis.
