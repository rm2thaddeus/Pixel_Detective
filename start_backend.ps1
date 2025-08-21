# =============================================================================
#  Vibe Coding – All-in-One Backend Launcher (PowerShell)
# =============================================================================
<#
.SYNOPSIS
    Starts every backend dependency (containers & FastAPI apps) required for
    a local Vibe Coding development session – with one single command.

.DESCRIPTION
    Workflow:
      1. Ensure the shared Docker network  "vibe_net" exists
      2. Spin-up Qdrant (vector database) via root docker-compose.yml
      3. Spin-up the GPU-accelerated UMAP service via
         backend/gpu_umap_service/docker-compose.dev.yml
      4. Launch the ML Inference FastAPI app (CLIP + BLIP)  -> port 8001
      5. Launch the Ingestion Orchestrator FastAPI app      -> port 8002

    Resulting local endpoints:
      * Qdrant UI               http://localhost:6333
      * GPU UMAP API            http://localhost:8003
      * ML Inference Service    http://localhost:8001
      * Ingestion Orchestrator  http://localhost:8002

    Run from repository root:
        ./start_backend.ps1

    Stop services afterwards with:
        docker compose down
        docker compose -f backend/gpu_umap_service/docker-compose.dev.yml down
        Get-Job | Stop-Job; Get-Job | Remove-Job
#>

param(
    [switch]$SkipContainers,   # allows: ./start_backend.ps1 -SkipContainers to only run python apps
    [switch]$UseJobs           # use background jobs instead of separate windows
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg)  { Write-Host "[Info] $msg"  -ForegroundColor Cyan }
function Write-Done($msg)  { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[Warn] $msg" -ForegroundColor Yellow }

# ----------------------------------------------------------------------------
# 1) Verify prerequisites
# ----------------------------------------------------------------------------
Write-Info "Checking for Docker CLI..."
try { docker --version | Out-Null } catch { throw "Docker CLI not found. Please install Docker Desktop." }
Write-Done  "Docker is available."

# Determine repository root (directory containing this script)
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

# ----------------------------------------------------------------------------
# 2) Docker-side services (unless user skipped with -SkipContainers)
# ----------------------------------------------------------------------------
if (-not $SkipContainers) {
    # 2.1  Create the shared network – harmless if it already exists
    Write-Info "Ensuring docker network 'vibe_net' exists..."
    # Avoid terminating on missing network when $ErrorActionPreference is 'Stop'
    # by querying the list of networks instead of inspecting a non-existent one.
    $networkNames = docker network ls --format "{{.Name}}"
    if ($networkNames -notcontains 'vibe_net') {
        docker network create vibe_net | Out-Null
        Write-Done "Created network 'vibe_net'."
    } else {
        Write-Done "Network 'vibe_net' already present."
    }

    # 2.2  Start / refresh Qdrant via root docker-compose
    Write-Info "Starting Qdrant container (root docker-compose)..."
    docker compose up -d qdrant_db
    Write-Done "Qdrant is (re)started."

    # 2.3  Start GPU UMAP service via its own compose file
    $umapCompose = Join-Path $RepoRoot "backend/gpu_umap_service/docker-compose.dev.yml"
    Write-Info "Starting GPU-UMAP container via $umapCompose ..."
    docker compose -f $umapCompose up -d gpu_umap_service
    Write-Done "UMAP API container is up (port 8003)."

    # 2.4  Start Neo4j and Developer Graph API via root docker-compose
    Write-Info "Starting Neo4j and Developer Graph API (root docker-compose)..."
    docker compose up -d neo4j dev_graph_api
    Write-Done "Neo4j and Developer Graph API are up."
}
else {
    Write-Warn "-- SkipContainers flag detected -> skipping all Docker workflows."
}

# ----------------------------------------------------------------------------
# 3) Python FastAPI services
# ----------------------------------------------------------------------------

if ($UseJobs) {
    # Use background jobs (better for Cursor integration)
    Write-Info "Starting services as background jobs..."
    
    # 3.1  ML Inference Service
    # Run from repository root using package path to enable relative imports
    $mlDir = $RepoRoot
    $mlCmd = "uvicorn backend.ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001 --reload"
    Write-Info "Starting ML Inference FastAPI service (port 8001) as background job..."
    Start-Job -Name "MLInference" -ScriptBlock {
        param($dir, $cmd)
        Set-Location $dir
        Invoke-Expression $cmd
    } -ArgumentList $mlDir, $mlCmd | Out-Null
    Write-Done "ML Inference Service job started."

    # 3.2  Ingestion Orchestration Service
    $ingestCmd = "uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002 --reload"
    Write-Info "Starting Ingestion Orchestrator (port 8002) as background job..."
    Start-Job -Name "IngestionOrchestrator" -ScriptBlock {
        param($dir, $cmd)
        Set-Location $dir
        Invoke-Expression $cmd
    } -ArgumentList $RepoRoot, $ingestCmd | Out-Null
    Write-Done "Ingestion Orchestrator job started."
    
    # 3.3  Developer Graph Service is managed via docker-compose; skip local job
    Write-Info "Developer Graph FastAPI runs in Docker compose; skipping local job."
    
    Write-Info "Background jobs status:"
    Get-Job | Format-Table -AutoSize
    
} else {
    # Original approach with separate windows (fixed syntax)
    function Start-ServiceWindow($workingDir, $command, $title) {
        Start-Process -FilePath "powershell" `
            -ArgumentList @("-NoExit", "-Command", $command) `
            -WorkingDirectory $workingDir `
            -WindowStyle Normal
        Write-Done "$title window launched."
    }

    # 3.1  ML Inference Service
    # Run from repository root using package path to enable relative imports
    $mlDir = $RepoRoot
    $mlCmd = "uvicorn backend.ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001 --reload"
    Write-Info "Launching ML Inference FastAPI service (port 8001)..."
    Start-ServiceWindow $mlDir $mlCmd "ML Inference Service"

    # 3.2  Ingestion Orchestration Service
    $ingestCmd = "uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002 --reload"
    Write-Info "Launching Ingestion Orchestrator (port 8002)..."
    Start-ServiceWindow $RepoRoot $ingestCmd "Ingestion Orchestrator"

    # 3.3  Developer Graph Service is managed via docker-compose; skip separate window
    Write-Info "Developer Graph FastAPI runs in Docker compose; skipping separate window."
}

Write-Done "All backend services started!"
Write-Host ""
Write-Host "=== AVAILABLE ENDPOINTS ===" -ForegroundColor Magenta
Write-Host "Qdrant UI (vector DB):              http://localhost:6333" -ForegroundColor Magenta
Write-Host "ML Inference Swagger UI:            http://localhost:8001/docs" -ForegroundColor Magenta
Write-Host "Ingestion Orchestrator Swagger UI:  http://localhost:8002/docs" -ForegroundColor Magenta
Write-Host "GPU UMAP API Swagger UI:             http://localhost:8003/docs" -ForegroundColor Magenta
Write-Host "Developer Graph API (Neo4j):           http://localhost:8080/docs" -ForegroundColor Magenta
Write-Host "Neo4j Browser:                         http://localhost:7474" -ForegroundColor Magenta
Write-Host ""

if ($UseJobs) {
    Write-Host "=== JOB MANAGEMENT ===" -ForegroundColor Yellow
    Write-Host "To check job status:    Get-Job" -ForegroundColor Yellow
    Write-Host "To view job output:     Receive-Job -Name 'MLInference' -Keep" -ForegroundColor Yellow
    Write-Host "To stop all jobs:       Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "=== SHUTDOWN COMMANDS ===" -ForegroundColor Yellow
Write-Host "To stop containers:  docker compose down; docker compose -f backend/gpu_umap_service/docker-compose.dev.yml down" -ForegroundColor Yellow
if ($UseJobs) {
    Write-Host "To stop services:    Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Yellow
} 
Write-Host "To stop Neo4j:        docker stop vibe_neo4j; docker rm vibe_neo4j" -ForegroundColor Yellow 