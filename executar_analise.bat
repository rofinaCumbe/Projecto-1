@echo off
chcp 65001 > nul
title Relatorio de Analise de Vendas - Terminal
echo =========================================================
echo       EXECUTANDO RELATÓRIO DE ANÁLISE DE VENDAS
echo =========================================================
echo.

python analise_vendas.py

echo.
echo =========================================================
echo Pressione qualquer tecla para fechar esta janela...
pause > nul
