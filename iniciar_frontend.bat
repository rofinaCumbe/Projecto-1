@echo off
chcp 65001 > nul
title Frontend Dashboard - Vercel
echo =========================================================
echo       ABRINDO O FRONTEND DA DASHBOARD
echo =========================================================
echo.
echo Abrindo a interface no navegador...
echo.

start "" "%~dp0frontend\index.html"
