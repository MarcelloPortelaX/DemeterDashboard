# Demeter Dashboard

Painel técnico em Python para exploração de inventários florestais, estimativas de biomassa e carbono, verificação da qualidade dos dados, modelagem exploratória e consulta climática.

## Abrir no Windows

Dê dois cliques em **INICIAR_DEMETER.bat**. Na primeira execução, o arquivo cria um ambiente isolado dentro da própria pasta e prepara as dependências automaticamente. Nas próximas execuções, a abertura é direta.

O Demeter utiliza por padrão o endereço `http://127.0.0.1:8051`, permitindo que o ClaraJuris continue na porta 8050.

## Executável portátil, sem instalar Python ou bibliotecas

O repositório inclui uma rotina de compilação com PyInstaller:

- No próprio Windows: execute `GERAR_EXECUTAVEL_WINDOWS.bat`.
- Pelo GitHub: abra **Actions → Gerar executável Windows → Run workflow**.

O artefato gerado contém a pasta `DemeterDashboard` com o arquivo `DemeterDashboard.exe`. Essa pasta é portátil e funciona sem instalar Python, Pandas, Dash ou as demais bibliotecas no computador de destino.

## Funcionalidades

- Upload de CSV, XLSX e XLS
- Reconhecimento de nomes alternativos de colunas
- Filtros por talhão, espécie e status de anomalia
- Indicadores biométricos e gráficos interativos
- Estimativas exploratórias de biomassa, carbono e CO₂e
- Cenário parametrizável de potencial de carbono
- Verificação de valores ausentes e faixas inválidas
- Detecção de anomalias, previsão de volume e agrupamento de talhões
- Consulta climática histórica via Open-Meteo

## Execução manual

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python demeter_launcher.py
```

## Aviso metodológico

As estimativas são exploratórias e dependem dos dados de entrada e dos parâmetros escolhidos. O sistema não substitui inventário oficial, equações locais ajustadas, validação de campo, auditoria independente ou metodologia certificada de crédito de carbono.
