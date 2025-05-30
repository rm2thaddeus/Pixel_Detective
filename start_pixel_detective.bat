@echo off
REM Pixel Detective: Full System Startup Script (Windows)
REM This script launches the Streamlit app, backend FastAPI services, and Docker (Qdrant) in the recommended order.

REM 1. Start the Streamlit app (frontend)
echo [1/4] Starting Streamlit app (frontend)...
start "Streamlit UI" cmd /k "cd /d %~dp0frontend && streamlit run app.py"

REM 2. Start backend FastAPI services
echo [2/4] Starting backend FastAPI services...
start "ML Inference API" cmd /k "cd /d %~dp0backend\ml_inference_fastapi_app && uvicorn main:app --host 0.0.0.0 --port 8001"
start "Ingestion Orchestration API" cmd /k "cd /d %~dp0backend\ingestion_orchestration_fastapi_app && uvicorn main:app --host 0.0.0.0 --port 8002"

REM 3. Start Docker services (Qdrant)
echo [3/4] Starting Docker services (Qdrant)...
start "Qdrant Docker" cmd /k "cd /d %~dp0 && docker-compose up"

REM 4. Final instructions
echo ----------------------------------------
echo All services are starting in separate terminals.
echo You can now interact with the app at http://localhost:8501 (Streamlit UI).
echo Monitor backend and Docker terminals for logs and status.
echo ----------------------------------------
pause 