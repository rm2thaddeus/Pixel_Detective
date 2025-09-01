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
      2. Set up Neo4j environment variables
      3. Spin-up Qdrant (vector database) via root docker-compose.yml
      4. Spin-up Neo4j (graph database) via root docker-compose.yml
      5. Spin-up the Developer Graph API service via root docker-compose.yml
      6. Spin-up the GPU-accelerated UMAP service via
         backend/gpu_umap_service/docker-compose.dev.yml
      7. Launch the ML Inference FastAPI app (CLIP + BLIP)  -> port 8001
      8. Launch the Ingestion Orchestrator FastAPI app      -> port 8002

    Resulting local endpoints:
      * Qdrant UI               http://localhost:6333
      * Neo4j Browser          http://localhost:7474
      * Developer Graph API     http://localhost:8080/docs
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
function Write-Error($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

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
# 2) Environment Setup
# ----------------------------------------------------------------------------
Write-Info "Setting up environment variables..."

# Set Neo4j password if not already set
if (-not $env:NEO4J_PASSWORD) {
    $env:NEO4J_PASSWORD = "password"
    Write-Warn "NEO4J_PASSWORD not set, using default 'password'. Set this environment variable for production use."
} else {
    Write-Done "NEO4J_PASSWORD is already set."
}

# ----------------------------------------------------------------------------
# 3) Docker-side services (unless user skipped with -SkipContainers)
# ----------------------------------------------------------------------------
if (-not $SkipContainers) {
    # 3.1  Create the shared network – harmless if it already exists
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

    # 3.2  Start / refresh Qdrant via root docker-compose
    Write-Info "Starting Qdrant container (root docker-compose)..."
    docker compose up -d qdrant_db
    Write-Done "Qdrant is (re)started."

    # 3.3  Start Neo4j (graph database) via root docker-compose
    Write-Info "Starting Neo4j container (root docker-compose)..."
    docker compose up -d neo4j
    Write-Done "Neo4j is (re)started."

    # 3.4  Start Developer Graph API service via root docker-compose
    Write-Info "Starting Developer Graph API service (root docker-compose)..."
    docker compose up -d dev_graph_api
    Write-Done "Developer Graph API is (re)started."

    # 3.5  Start GPU UMAP service via its own compose file
    $umapCompose = Join-Path $RepoRoot "backend/gpu_umap_service/docker-compose.dev.yml"
    Write-Info "Starting GPU-UMAP container via $umapCompose ..."
    docker compose -f $umapCompose up -d gpu_umap_service
    Write-Done "UMAP API container is up (port 8003)."

    # 3.6  Wait for Neo4j to be ready before proceeding
    Write-Info "Waiting for Neo4j to be ready..."
    $maxAttempts = 30
    $attempt = 0
    do {
        $attempt++
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:7474" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Done "Neo4j is ready and responding."
                break
            }
        } catch {
            if ($attempt -ge $maxAttempts) {
                Write-Warn "Neo4j may not be fully ready, but continuing with startup..."
                break
            }
            Write-Info "Waiting for Neo4j... (attempt $attempt/$maxAttempts)"
            Start-Sleep -Seconds 2
        }
    } while ($attempt -lt $maxAttempts)
}
else {
    Write-Warn "-- SkipContainers flag detected -> skipping all Docker workflows."
}

# ----------------------------------------------------------------------------
# 4) Python FastAPI services
# ----------------------------------------------------------------------------

if ($UseJobs) {
    # Use background jobs (better for Cursor integration)
    Write-Info "Starting services as background jobs..."
    
    # 4.1  ML Inference Service
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

    # 4.2  Ingestion Orchestration Service
    $ingestCmd = "uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002 --reload"
    Write-Info "Starting Ingestion Orchestrator (port 8002) as background job..."
    Start-Job -Name "IngestionOrchestrator" -ScriptBlock {
        param($dir, $cmd)
        Set-Location $dir
        Invoke-Expression $cmd
    } -ArgumentList $RepoRoot, $ingestCmd | Out-Null
    Write-Done "Ingestion Orchestrator job started."
    
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

    # 4.1  ML Inference Service
    # Run from repository root using package path to enable relative imports
    $mlDir = $RepoRoot
    $mlCmd = "uvicorn backend.ml_inference_fastapi_app.main:app --host 0.0.0.0 --port 8001 --reload"
    Write-Info "Launching ML Inference FastAPI service (port 8001)..."
    Start-ServiceWindow $mlDir $mlCmd "ML Inference Service"

    # 4.2  Ingestion Orchestration Service
    $ingestCmd = "uvicorn backend.ingestion_orchestration_fastapi_app.main:app --host 0.0.0.0 --port 8002 --reload"
    Write-Info "Launching Ingestion Orchestrator (port 8002)..."
    Start-ServiceWindow $RepoRoot $ingestCmd "Ingestion Orchestrator"
}

# ----------------------------------------------------------------------------
# 5) Service Status Check
# ----------------------------------------------------------------------------
Write-Info "Checking service status..."
Start-Sleep -Seconds 3

$services = @(
    @{Name="Qdrant"; URL="http://localhost:6333"; Port="6333"},
    @{Name="Neo4j"; URL="http://localhost:7474"; Port="7474"},
    @{Name="Developer Graph API"; URL="http://localhost:8080"; Port="8080"},
    @{Name="GPU UMAP API"; URL="http://localhost:8003"; Port="8003"},
    @{Name="ML Inference Service"; URL="http://localhost:8001"; Port="8001"},
    @{Name="Ingestion Orchestrator"; URL="http://localhost:8002"; Port="8002"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.URL -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Done "$($service.Name) is running on port $($service.Port)"
        } else {
            Write-Warn "$($service.Name) responded with status $($response.StatusCode)"
        }
    } catch {
        Write-Warn "$($service.Name) is not responding on port $($service.Port)"
    }
}

Write-Done "All backend services started!"
Write-Host ""
Write-Host "=== AVAILABLE ENDPOINTS ===" -ForegroundColor Magenta
Write-Host "Qdrant UI (vector DB):              http://localhost:6333" -ForegroundColor Magenta
Write-Host "Neo4j Browser (graph DB):           http://localhost:7474" -ForegroundColor Magenta
Write-Host "Developer Graph API:                 http://localhost:8080/docs" -ForegroundColor Magenta
Write-Host "ML Inference Swagger UI:            http://localhost:8001/docs" -ForegroundColor Magenta
Write-Host "Ingestion Orchestrator Swagger UI:  http://localhost:8002/docs" -ForegroundColor Magenta
Write-Host "GPU UMAP API Swagger UI:             http://localhost:8003/docs" -ForegroundColor Magenta
Write-Host ""

if ($UseJobs) {
    Write-Host "=== JOB MANAGEMENT ===" -ForegroundColor Yellow
    Write-Host "To check job status:    Get-Job" -ForegroundColor Yellow
    Write-Host "To view job output:     Receive-Job -Name 'MLInference' -Keep" -ForegroundColor Yellow
    Write-Host "To stop all jobs:       Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "=== SHUTDOWN COMMANDS ===" -ForegroundColor Yellow
Write-Host "To stop all containers:  docker compose down; docker compose -f backend/gpu_umap_service/docker-compose.dev.yml down" -ForegroundColor Yellow
if ($UseJobs) {
    Write-Host "To stop services:    Get-Job | Stop-Job; Get-Job | Remove-Job" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=== NEO4J SETUP ===" -ForegroundColor Cyan
Write-Host "Neo4j default credentials: neo4j/password" -ForegroundColor Cyan
Write-Host "To change password: Set NEO4J_PASSWORD environment variable" -ForegroundColor Cyan
Write-Host "To access Neo4j: http://localhost:7474" -ForegroundColor Cyan
Write-Host "" 