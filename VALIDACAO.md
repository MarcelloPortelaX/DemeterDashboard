# Validação do pacote

Verificações executadas na versão final:

- compilação sintática de `app.py` e de todos os módulos;
- resposta HTTP 200 da aplicação pelo cliente de teste do Flask;
- processamento integral da base `data/exemplo_teste.csv`;
- consolidação de aliases duplicados;
- renderização lógica das dez abas analíticas;
- seis KPIs principais, sem duplicidade;
- gráficos Plotly sem título interno duplicado;
- exportações CSV, Excel, HTML e modelo de planilha;
- tabelas com colunas categóricas;
- quatro testes automatizados.

A base de demonstração possui 72 registros e percorreu inventário, estrutura,
carbono, crescimento, espacial, qualidade, IA e dados sem exceção.

A interface foi iniciada localmente na porta 8051 e respondeu corretamente.
A captura automática pelo Chromium deste ambiente foi bloqueada por política de
acesso a localhost, por isso a validação visual foi feita pela estrutura do DOM,
CSS, callbacks e pelas capturas fornecidas pelo usuário.
