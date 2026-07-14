@echo off
setlocal EnableExtensions
title Demeter Dashboard Pro
cd /d "%~dp0"

set "DEMETER_PORT=8051"

if exist "%~dp0DemeterDashboard\DemeterDashboard.exe" (
    start "" "%~dp0DemeterDashboard\DemeterDashboard.exe"
    exit /b 0
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto :SEM_PYTHON
    set "PYTHON_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Preparando o ambiente local do Demeter...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :ERRO
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :ERRO
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :ERRO
)

echo.
echo Abrindo Demeter Dashboard Pro em http://127.0.0.1:8051
echo Para encerrar o servidor, pressione Ctrl+C nesta janela.
echo.
".venv\Scripts\python.exe" app.py
exit /b %errorlevel%

:SEM_PYTHON
echo.
echo Python nao foi encontrado neste computador.
echo Use a versao portatil gerada na aba Actions do GitHub.
pause
exit /b 1

:ERRO
echo.
echo Nao foi possivel preparar ou iniciar o Demeter.
pause
exit /b 1
