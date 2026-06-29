@echo off
title Demeter Dashboard Pro
cd /d "%~dp0"

set APP_URL=http://127.0.0.1:8050
set EDGE_PATH=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe

netstat -ano | findstr ":8050" >nul

if %errorlevel%==0 (
    echo Demeter Dashboard Pro ja esta rodando.
) else (
    echo Iniciando Demeter Dashboard Pro...
    start "Demeter Server" /min cmd /c ".venv\Scripts\python.exe app.py"
)

timeout /t 4 >nul

if exist "%EDGE_PATH%" (
    start "" "%EDGE_PATH%" --app=%APP_URL%
) else (
    start "" %APP_URL%
)

exit
