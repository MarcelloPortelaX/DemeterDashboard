@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Demeter Dashboard

if exist "DemeterDashboard\DemeterDashboard.exe" (
  start "" "DemeterDashboard\DemeterDashboard.exe"
  exit /b 0
)

if exist ".venv\Scripts\pythonw.exe" goto RUN

where py >nul 2>nul
if %errorlevel%==0 (
  set PYTHON=py
) else (
  where python >nul 2>nul
  if errorlevel 1 goto NOPYTHON
  set PYTHON=python
)

echo Preparando o ambiente local do Demeter. Isso ocorre apenas na primeira execução.
%PYTHON% -m venv .venv
if errorlevel 1 goto ERROR
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto ERROR

:RUN
start "Demeter Dashboard" ".venv\Scripts\pythonw.exe" "demeter_launcher.py"
exit /b 0

:NOPYTHON
echo.
echo Python não foi encontrado neste computador.
echo Para uma versão que não exige Python, baixe o artefato portátil criado pelo GitHub Actions.
echo Consulte README.md, seção "Executável portátil".
pause
exit /b 1

:ERROR
echo.
echo Não foi possível preparar o Demeter Dashboard.
pause
exit /b 1
