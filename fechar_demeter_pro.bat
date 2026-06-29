@echo off
title Fechar Demeter Dashboard Pro

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8050"') do (
    taskkill /PID %%a /F
)

exit
