@echo off
REM Pixel Detective - Complete Application Startup Script (Windows)
REM Launches all required services for the AI-powered media search platform

echo.
echo ========================================
echo    Starting Pixel Detective
echo ========================================
echo.

REM Check if we're in the repo root
if not exist "frontend\package.json" (
    echo ERROR: Must run from repository root
    pause
    exit /b 1
)

REM Step 1: Start Qdrant Vector Database
echo Step 1/5: Starting Qdrant Vector Database...
docker compose up -d qdrant_db
if errorlevel 1 (
    echo ERROR: Failed to start Qdrant
    pause
    exit /b 1
)
echo SUCCESS: Qdrant running on port 6333
timeout /t 3 /nobreak >nul

REM Step 2: Start GPU-UMAP Service
echo.
echo Step 2/5: Starting GPU-UMAP Service...
cd backend\gpu_umap_service
docker compose -f docker-compose.dev.yml up -d --build
if errorlevel 1 (
    echo WARNING: GPU-UMAP service failed (will use CPU fallback)
) else (
    echo SUCCESS: GPU-UMAP Service running on port 8003
)
cd ..\..
timeout /t 5 /nobreak >nul

REM Step 3: Start ML Inference Service
echo.
echo Step 3/5: Starting ML Inference Service...
start "ML Inference Service" cmd /k "uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload"
echo SUCCESS: ML Inference Service starting on port 8001...
timeout /t 8 /nobreak >nul

REM Step 4: Start Ingestion Orchestration Service
echo.
echo Step 4/5: Starting Ingestion Orchestration Service...
start "Ingestion Service" cmd /k "uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload"
echo SUCCESS: Ingestion Service starting on port 8002...
timeout /t 5 /nobreak >nul

REM Step 5: Start Frontend
echo.
echo Step 5/5: Starting Next.js Frontend...
cd frontend
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)
start "Frontend" cmd /k "npm run dev"
cd ..
echo SUCCESS: Frontend starting on port 3000...

REM Wait for services
echo.
echo Waiting for all services to initialize...
timeout /t 10 /nobreak >nul

REM Summary
echo.
echo ========================================
echo   Pixel Detective Started Successfully!
echo ========================================
echo.
echo Service URLs:
echo   - Frontend:        http://localhost:3000
echo   - Ingestion API:   http://localhost:8002/docs
echo   - ML Inference:    http://localhost:8001/docs
echo   - GPU-UMAP:        http://localhost:8003/docs
echo   - Qdrant:          http://localhost:6333/dashboard
echo.
echo Key Features:
echo   - AI-Powered Search
echo   - Automatic Image Captioning
echo   - Visual Similarity Search
echo   - Latent Space Visualization
echo   - GPU-Accelerated Clustering
echo.
echo Quick Start:
echo   1. Open http://localhost:3000
echo   2. Navigate to 'Collections'
echo   3. Use 'Ingest' to add images
echo   4. Try 'Search' for semantic queries
echo   5. Explore 'Latent Space' for visualization
echo.
echo To stop: docker compose down (then close windows)
echo.
pause

