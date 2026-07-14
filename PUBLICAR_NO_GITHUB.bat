@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Publicar Demeter Dashboard no GitHub
cd /d "%~dp0"

set "REPO_URL=https://github.com/MarcelloPortelaX/demeter-dashboard.git"
set "COMMIT_MESSAGE=Refina UX do dashboard sem remover analises"
set "TEMP_CLONE=%TEMP%\demeter-publish-%RANDOM%%RANDOM%"
set "TEMP_GIT=%TEMP_CLONE%-gitmeta"

where git >nul 2>&1
if errorlevel 1 (
    echo.
    echo Git nao foi encontrado. Instale o Git for Windows e execute novamente.
    pause
    exit /b 1
)

echo.
echo 1/4 - Baixando o repositorio atual...
git clone "%REPO_URL%" "%TEMP_CLONE%"
if errorlevel 1 goto :ERRO

echo.
echo 2/4 - Substituindo o projeto remoto pela versao desta pasta...
move "%TEMP_CLONE%\.git" "%TEMP_GIT%" >nul
if errorlevel 1 goto :ERRO
robocopy "%~dp0" "%TEMP_CLONE%" /MIR /R:2 /W:1 /XD ".venv" "__pycache__" "build" "dist" ".pytest_cache" /XF "*.pyc" "*.pyo" "*.log" >nul
set "ROBOCOPY_CODE=!ERRORLEVEL!"
if !ROBOCOPY_CODE! GEQ 8 goto :ERRO
move "%TEMP_GIT%" "%TEMP_CLONE%\.git" >nul
if errorlevel 1 goto :ERRO

cd /d "%TEMP_CLONE%"

echo.
echo 3/4 - Criando o commit...
git add -A
git diff --cached --quiet
if not errorlevel 1 (
    echo.
    echo O GitHub ja possui exatamente estes arquivos. Nada precisou ser enviado.
    goto :SUCESSO
)

git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 goto :ERRO

echo.
echo 4/4 - Enviando para a branch main...
git push origin main
if errorlevel 1 goto :ERRO

:SUCESSO
echo.
echo Publicacao concluida:
echo https://github.com/MarcelloPortelaX/demeter-dashboard
start "" "https://github.com/MarcelloPortelaX/demeter-dashboard"
cd /d "%TEMP%"
rmdir /S /Q "%TEMP_CLONE%" >nul 2>&1
rmdir /S /Q "%TEMP_GIT%" >nul 2>&1
pause
exit /b 0

:ERRO
echo.
echo A publicacao falhou.
echo O Git pode abrir o navegador para autenticar sua conta do GitHub.
echo Nenhum arquivo da pasta original foi apagado.
cd /d "%TEMP%"
rmdir /S /Q "%TEMP_CLONE%" >nul 2>&1
rmdir /S /Q "%TEMP_GIT%" >nul 2>&1
pause
exit /b 1
