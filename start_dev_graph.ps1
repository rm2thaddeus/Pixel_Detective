#!/usr/bin/env pwsh
# Dev Graph - Standalone Startup Script
# Launches the temporal knowledge graph visualization platform

Write-Host "Dev Graph Starting..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if we're in the repo root
if (-Not (Test-Path "developer_graph/api.py")) {
    Write-Host "Error: Must run from repository root" -ForegroundColor Red
    exit 1
}

# Step 1: Start Neo4j Database
Write-Host "`nStep 1/3: Starting Neo4j Graph Database..." -ForegroundColor Yellow
docker compose up -d neo4j
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start Neo4j" -ForegroundColor Red
    Write-Host "Make sure Docker is running and neo4j is defined in docker-compose.yml" -ForegroundColor Yellow
    exit 1
}
Write-Host "Neo4j running on port 7687 (Bolt) and 7474 (Browser)" -ForegroundColor Green
Start-Sleep -Seconds 8

# Step 2: Start Dev Graph API
Write-Host "`nStep 2/3: Starting Dev Graph API..." -ForegroundColor Yellow
$apiPath = $PWD.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$apiPath'; uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload" -WindowStyle Normal
Write-Host "Dev Graph API starting on port 8080..." -ForegroundColor Green
Start-Sleep -Seconds 8

# Step 3: Start Frontend (Dev Graph UI)
Write-Host "`nStep 3/3: Starting Dev Graph Frontend..." -ForegroundColor Yellow
Push-Location tools/dev-graph-ui

# Check if node_modules exists
if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
}

# Start frontend
$frontendPath = $PWD.Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev" -WindowStyle Normal
Pop-Location
Write-Host "Frontend starting on port 3001..." -ForegroundColor Green

# Wait for services to fully start
Write-Host "`nWaiting for all services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Dev Graph Started Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
Write-Host "  - Dev Graph UI:    http://localhost:3001" -ForegroundColor White
Write-Host "  - API Docs:        http://localhost:8080/docs" -ForegroundColor White
Write-Host "  - Neo4j Browser:   http://localhost:7474" -ForegroundColor White
Write-Host "  - Timeline View:   http://localhost:3001/dev-graph/timeline" -ForegroundColor White
Write-Host "  - Structure View:  http://localhost:3001/dev-graph/structure" -ForegroundColor White
Write-Host ""
Write-Host "Key Features:" -ForegroundColor Cyan
Write-Host "  - Temporal Code Evolution Tracking" -ForegroundColor White
Write-Host "  - Semantic Code-Documentation Links" -ForegroundColor White
Write-Host "  - Sprint-Commit-Requirement Mapping" -ForegroundColor White
Write-Host "  - WebGL Timeline Visualization" -ForegroundColor White
Write-Host "  - Interactive Knowledge Graph" -ForegroundColor White
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Cyan
Write-Host "  1. Open http://localhost:3001" -ForegroundColor White
Write-Host "  2. Click 'Ingest' to build the knowledge graph" -ForegroundColor White
Write-Host "  3. Explore 'Timeline' for commit history" -ForegroundColor White
Write-Host "  4. Use 'Structure' to browse code relationships" -ForegroundColor White
Write-Host "  5. Check 'Search' to query the graph" -ForegroundColor White
Write-Host ""
Write-Host "Initial Setup:" -ForegroundColor Yellow
Write-Host "  Run unified ingestion to populate the graph:" -ForegroundColor White
Write-Host "  POST http://localhost:8080/api/v1/dev-graph/ingest/unified?reset_graph=true" -ForegroundColor White
Write-Host ""
Write-Host "  Or use the UI ingestion button (recommended)" -ForegroundColor White
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - Developer Guide: developer_graph/AGENTS.md" -ForegroundColor White
Write-Host "  - Architecture:    developer_graph/architecture.md" -ForegroundColor White
Write-Host "  - Migration Plan:  docs/DEV_GRAPH_MIGRATION_PLAN.md" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  docker compose down" -ForegroundColor White
Write-Host "  (Then close PowerShell windows)" -ForegroundColor White
Write-Host ""
