@echo off
chcp 65001 > nul
title Dashboard de Vendas - Streamlit
echo =========================================================
echo       INICIANDO A DASHBOARD DE VENDAS (STREAMLIT)
echo =========================================================
echo.
echo Abrindo o servidor e iniciando no navegador...
echo Pressione Ctrl+C na janela para encerrar quando terminar.
echo.

python -m streamlit run app.py

if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao iniciar a Dashboard.
    pause
)
