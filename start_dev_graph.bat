@echo off
REM Dev Graph - Standalone Startup Script (Windows)
REM Launches the temporal knowledge graph visualization platform

echo.
echo ========================================
echo    Starting Dev Graph
echo ========================================
echo.

REM Check if we're in the repo root
if not exist "developer_graph\api.py" (
    echo ERROR: Must run from repository root
    pause
    exit /b 1
)

REM Step 1: Start Neo4j Database
echo Step 1/3: Starting Neo4j Graph Database...
docker compose up -d neo4j_db
if errorlevel 1 (
    echo ERROR: Failed to start Neo4j
    echo Make sure Docker is running and neo4j_db is defined
    pause
    exit /b 1
)
echo SUCCESS: Neo4j running on ports 7687 and 7474
timeout /t 8 /nobreak >nul

REM Step 2: Start Dev Graph API
echo.
echo Step 2/3: Starting Dev Graph API...
start "Dev Graph API" cmd /k "uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload"
echo SUCCESS: Dev Graph API starting on port 8080...
timeout /t 8 /nobreak >nul

REM Step 3: Start Frontend
echo.
echo Step 3/3: Starting Dev Graph Frontend...
cd tools\dev-graph-ui
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)
start "Dev Graph UI" cmd /k "npm run dev"
cd ..\..
echo SUCCESS: Frontend starting on port 3001...

REM Wait for services
echo.
echo Waiting for all services to initialize...
timeout /t 10 /nobreak >nul

REM Summary
echo.
echo ========================================
echo   Dev Graph Started Successfully!
echo ========================================
echo.
echo Service URLs:
echo   - Dev Graph UI:    http://localhost:3001
echo   - API Docs:        http://localhost:8080/docs
echo   - Neo4j Browser:   http://localhost:7474
echo   - Timeline View:   http://localhost:3001/dev-graph/timeline
echo   - Structure View:  http://localhost:3001/dev-graph/structure
echo.
echo Key Features:
echo   - Temporal Code Evolution Tracking
echo   - Semantic Code-Documentation Links
echo   - Sprint-Commit-Requirement Mapping
echo   - WebGL Timeline Visualization
echo   - Interactive Knowledge Graph
echo.
echo Quick Start:
echo   1. Open http://localhost:3001
echo   2. Click 'Ingest' to build the graph
echo   3. Explore 'Timeline' for commit history
echo   4. Use 'Structure' to browse relationships
echo   5. Check 'Search' to query the graph
echo.
echo Initial Setup:
echo   Run unified ingestion to populate the graph
echo   Or use the UI ingestion button (recommended)
echo.
echo To stop: docker compose down (then close windows)
echo.
pause

