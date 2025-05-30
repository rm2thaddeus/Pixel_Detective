#!/bin/bash
# Pixel Detective: Full System Startup Script
# This script launches the Streamlit app, backend FastAPI services, and Docker (Qdrant) in the recommended order.
# On Windows, use 'start' to open new terminals. On Unix, replace with 'gnome-terminal --' or 'xterm -e'.

# 1. Start the Streamlit app (frontend)
echo "[1/3] Starting Streamlit app (frontend)..."
start cmd /k "cd frontend && streamlit run app.py"
sleep 2

# 2. Start backend FastAPI services
# (Adjust paths and ports as needed for your setup)
echo "[2/3] Starting backend FastAPI services..."
start cmd /k "cd backend/ml_inference_fastapi_app && uvicorn main:app --host 0.0.0.0 --port 8001"
start cmd /k "cd backend/ingestion_orchestration_fastapi_app && uvicorn main:app --host 0.0.0.0 --port 8002"
sleep 2

# 3. Start Docker services (Qdrant)
echo "[3/3] Starting Docker services (Qdrant)..."
start cmd /k "docker-compose up"

# Final instructions
echo "---"
echo "All services are starting in separate terminals."
echo "You can now interact with the app at http://localhost:8501 (Streamlit UI)."
echo "Monitor backend and Docker terminals for logs and status."
echo "---"

# End of script 