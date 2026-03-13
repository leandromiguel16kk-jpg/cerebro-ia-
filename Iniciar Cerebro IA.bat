@echo off
title Cerebro IA
color 0B
echo.
echo  ==========================================
echo   Cerebro IA - Super Inteligencia Artificial
echo  ==========================================
echo.
cd /d "%~dp0"
set PYTHON=
for %%P in (py python python3) do (
    if not defined PYTHON (
        %%P --version >nul 2>&1 && set PYTHON=%%P
    )
)
if not defined PYTHON (
    echo  [ERRO] Python nao encontrado!
    echo  Baixe em: https://www.python.org/downloads/
    pause & exit /b 1
)
echo  Instalando dependencias...
%PYTHON% -m pip install -r requirements.txt -q
echo.
echo  Iniciando Cerebro IA...
echo  Acesse: http://localhost:5001
echo.
start http://localhost:5001
%PYTHON% app.py
pause
