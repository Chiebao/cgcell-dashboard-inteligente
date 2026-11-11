@echo off
REM ==================================================================
REM  CG CELL Repair - MODO DEMONSTRACAO (dados SIMULADOS)
REM  Abre o app com um banco SEPARADO (data\demo.db), so com dados ficticios.
REM  O banco principal (data\cgcell.db) nao e usado nem alterado.
REM  Usa a porta 8502, para poder ficar aberto junto com o app normal (8501).
REM  Para fechar, feche esta janela preta.
REM ==================================================================
cd /d "%~dp0"
title CG CELL Repair - MODO DEMONSTRACAO (dados simulados)

set "CGCELL_CAMINHO_BANCO=data/demo.db"
set "CGCELL_MODO_DEMO=1"

REM Se a demonstracao ja estiver aberta, so abre o navegador de novo.
netstat -ano | findstr /r /c:":8502 .*LISTENING" >nul
if not errorlevel 1 (
    start "" http://localhost:8502
    exit /b 0
)

REM Primeira execucao: cria o ambiente virtual e instala as bibliotecas.
if not exist ".venv\Scripts\python.exe" (
    echo Preparando o ambiente pela primeira vez. Isso pode levar alguns minutos...
    python -m venv .venv || goto erro
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto erro
)

REM Se o banco de demonstracao ainda nao existe, gera os dados simulados.
if not exist "data\demo.db" (
    echo Gerando dados SIMULADOS de demonstracao. Aguarde alguns segundos...
    ".venv\Scripts\python.exe" -m scripts.gerar_dados_simulados || goto erro
)

echo.
echo  ==============================================================
echo    MODO DEMONSTRACAO - TODOS OS DADOS SAO SIMULADOS
echo    Nada aqui representa a operacao real da CG CELL Repair.
echo    Banco usado: data\demo.db (o banco principal nao e tocado)
echo  ==============================================================
echo.
echo  O app vai abrir no navegador em instantes: http://localhost:8502
echo  Para FECHAR a demonstracao, feche esta janela.
echo.

REM Abre o navegador alguns segundos depois, quando o servidor ja estiver pronto.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process 'http://localhost:8502'"

".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8502
goto fim

:erro
echo.
echo Nao foi possivel preparar a demonstracao.
echo Verifique se o Python 3.12 esta instalado e tente de novo.
pause

:fim
