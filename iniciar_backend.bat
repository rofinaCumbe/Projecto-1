@echo off
chcp 65001 > nul
title Backend API - FastAPI (Render)
echo =========================================================
echo       INICIANDO O BACKEND FASTAPI (PORTA 8000)
echo =========================================================
echo.
echo Documentação interativa (Swagger UI): http://localhost:8000/docs
echo Pressione Ctrl+C na janela para encerrar quando terminar.
echo.

python -m uvicorn backend.main:app --reload --port 8000

if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao iniciar o Backend.
    pause
)
