@echo off
REM ==================================================================
REM  CG CELL Repair - Dashboard Inteligente
REM  Abre o app no navegador com dois cliques.
REM  Na primeira vez, prepara o ambiente virtual e instala as dependencias.
REM  Para fechar o app, feche esta janela preta.
REM ==================================================================
cd /d "%~dp0"
title CG CELL Repair - Dashboard

REM Se o app ja estiver aberto, so abre o navegador de novo.
netstat -ano | findstr /r /c:":8501 .*LISTENING" >nul
if not errorlevel 1 (
    start "" http://localhost:8501
    exit /b 0
)

REM Primeira execucao: cria o ambiente virtual e instala as bibliotecas.
if not exist ".venv\Scripts\python.exe" (
    echo Preparando o ambiente pela primeira vez. Isso pode levar alguns minutos...
    python -m venv .venv || goto erro
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto erro
)

echo.
echo  CG CELL Repair - Dashboard
echo  O app vai abrir no navegador em instantes: http://localhost:8501
echo  Para FECHAR o app, feche esta janela.
echo.

REM Abre o navegador alguns segundos depois, quando o servidor ja estiver pronto.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://localhost:8501'"

".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8501
goto fim

:erro
echo.
echo Nao foi possivel preparar o ambiente.
echo Verifique se o Python 3.12 esta instalado e tente de novo.
pause

:fim
