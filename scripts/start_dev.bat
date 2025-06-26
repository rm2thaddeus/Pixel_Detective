@echo off
rem =============================================================
rem  Vibe Coding – One-Click Local Development Launcher (Windows)
rem  -----------------------------------------------------------
rem  Starts:
rem    • Qdrant vector DB (Docker Compose)
rem    • GPU-accelerated UMAP micro-service (Docker Compose, hot-reload)
rem    • Ingestion Orchestration FastAPI (host Python, hot-reload)
rem    • ML Inference FastAPI (host Python, hot-reload)
rem
rem  Requirements:
rem    1. Docker Desktop + WSL2 backend (for GPU passthrough)
rem    2. A Python ≥3.11 environment with project deps installed
rem       (e.g.  `pip install -r requirements.txt` from repo root).
rem =============================================================

:: Change to repo root (where this script lives)
cd /d "%~dp0.."

:: Make sure the shared Docker network exists
FOR /F "tokens=*" %%i IN ('docker network ls --filter name=^vibe_net$ --format "{{ .Name }}"') DO (
    SET network_exists=%%i
)
IF NOT DEFINED network_exists (
    echo Creating shared Docker network "vibe_net"...
    docker network create vibe_net
)

:: -------- 1️⃣  Qdrant DB -------------------------------------------------
ECHO.
ECHO Starting Qdrant vector DB...
Docker compose up -d qdrant_db || GOTO :error

:: -------- 2️⃣  GPU-UMAP micro-service -----------------------------------
ECHO.
ECHO Building & starting GPU-UMAP micro-service (hot-reload)...
Docker compose -f backend\gpu_umap_service\docker-compose.dev.yml up -d --build || GOTO :error

:: -------- 3️⃣  Ingestion Orchestration API --------------------------------
ECHO.
ECHO Launching Ingestion Orchestration FastAPI (port 8002)...
START "Ingestion API" cmd /k "python -m uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002 --reload"

:: -------- 4️⃣  ML Inference API ------------------------------------------
ECHO.
ECHO Launching ML Inference FastAPI (port 8001)...
START "ML Inference API" cmd /k "python -m uvicorn backend.ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001 --reload"

:: -------- 5️⃣  Frontend --------------------------------------------------
ECHO.
ECHO Launching Next.js frontend...
START "Frontend" cmd /k "cd frontend && npm run dev"

ECHO.
ECHO ✅ All services are starting!   API Documentation:
ECHO   • http://localhost:8003/docs   (GPU UMAP - Docker)
ECHO   • http://localhost:8002/docs   (Ingestion Orchestration)
ECHO   • http://localhost:8001/docs   (ML Inference - Host Python)
ECHO.
ECHO 🌐 Frontend will auto-open at: http://localhost:3000
ECHO    Frontend auto-detects GPU UMAP (8003) or ML Inference (8001) services.
ECHO.
ECHO Press any key to close this launcher...
PAUSE
GOTO :eof

:error
ECHO.
ECHO ***** ERROR starting dev stack – see messages above *****
PAUSE
exit /b 1 