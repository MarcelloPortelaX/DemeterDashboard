@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (echo Python não encontrado.& pause & exit /b 1)
py -m venv .build-venv
call ".build-venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean demeter_dashboard.spec
if errorlevel 1 (echo Falha na geração.& pause & exit /b 1)
echo.
echo Executável criado em dist\DemeterDashboard\DemeterDashboard.exe
pause
