#!/usr/bin/env pwsh
# Pixel Detective - Complete Application Startup Script
# Launches all required services for the AI-powered media search platform

Write-Host "🎨 Starting Pixel Detective..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Check if we're in the repo root
if (-Not (Test-Path "frontend/package.json")) {
    Write-Host "❌ Error: Must run from repository root" -ForegroundColor Red
    exit 1
}

# Step 1: Start Qdrant Vector Database
Write-Host "`n📦 Step 1/5: Starting Qdrant Vector Database..." -ForegroundColor Yellow
docker compose up -d qdrant_db
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Qdrant" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Qdrant running on port 6333" -ForegroundColor Green
Start-Sleep -Seconds 3

# Step 2: Start GPU-UMAP Service (Docker)
Write-Host "`n⚡ Step 2/5: Starting GPU-UMAP Service..." -ForegroundColor Yellow
Push-Location backend/gpu_umap_service
docker compose -f docker-compose.dev.yml up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: GPU-UMAP service failed (will use CPU fallback)" -ForegroundColor Yellow
} else {
    Write-Host "✅ GPU-UMAP Service running on port 8003" -ForegroundColor Green
}
Pop-Location
Start-Sleep -Seconds 5

# Step 3: Start ML Inference Service
Write-Host "`n🤖 Step 3/5: Starting ML Inference Service..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD'; uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload" -WindowStyle Normal
Write-Host "✅ ML Inference Service starting on port 8001..." -ForegroundColor Green
Start-Sleep -Seconds 8

# Step 4: Start Ingestion Orchestration Service
Write-Host "`n📥 Step 4/5: Starting Ingestion Orchestration Service..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD'; uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload" -WindowStyle Normal
Write-Host "✅ Ingestion Service starting on port 8002..." -ForegroundColor Green
Start-Sleep -Seconds 5

# Step 5: Start Frontend
Write-Host "`n🎨 Step 5/5: Starting Next.js Frontend..." -ForegroundColor Yellow
Push-Location frontend

# Check if node_modules exists
if (-Not (Test-Path "node_modules")) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
}

# Start frontend
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "cd '$PWD'; npm run dev" -WindowStyle Normal
Pop-Location
Write-Host "✅ Frontend starting on port 3000..." -ForegroundColor Green

# Wait for services to fully start
Write-Host "`n⏳ Waiting for all services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "🎉 Pixel Detective Started Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 Service URLs:" -ForegroundColor Cyan
Write-Host "  • Frontend:        http://localhost:3000" -ForegroundColor White
Write-Host "  • Ingestion API:   http://localhost:8002/docs" -ForegroundColor White
Write-Host "  • ML Inference:    http://localhost:8001/docs" -ForegroundColor White
Write-Host "  • GPU-UMAP:        http://localhost:8003/docs" -ForegroundColor White
Write-Host "  • Qdrant:          http://localhost:6333/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "📊 Key Features:" -ForegroundColor Cyan
Write-Host "  • AI-Powered Search" -ForegroundColor White
Write-Host "  • Automatic Image Captioning" -ForegroundColor White
Write-Host "  • Visual Similarity Search" -ForegroundColor White
Write-Host "  • Latent Space Visualization" -ForegroundColor White
Write-Host "  • GPU-Accelerated Clustering" -ForegroundColor White
Write-Host ""
Write-Host "💡 Quick Start:" -ForegroundColor Cyan
Write-Host "  1. Open http://localhost:3000" -ForegroundColor White
Write-Host "  2. Navigate to 'Collections' to create a new collection" -ForegroundColor White
Write-Host "  3. Use 'Ingest' to add images from a folder" -ForegroundColor White
Write-Host "  4. Try 'Search' for semantic queries" -ForegroundColor White
Write-Host "  5. Explore 'Latent Space' for clustering visualization" -ForegroundColor White
Write-Host ""
Write-Host "🛑 To stop all services:" -ForegroundColor Yellow
Write-Host "  docker compose down" -ForegroundColor White
Write-Host "  (Then close PowerShell windows)" -ForegroundColor White
Write-Host ""

