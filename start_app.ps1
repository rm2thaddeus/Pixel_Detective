<#
.SYNOPSIS
    Starts the complete Vibe Coding application stack:
    1. All backend services via ./start_backend.ps1 (as background jobs).
    2. The Next.js frontend application in the current terminal.
.DESCRIPTION
    This script provides a single command to get a full development environment running.
    It's the recommended way to start working on the application.
    Run from repository root:
        ./start_app.ps1
#>
$ErrorActionPreference = 'Stop'

function Write-Info($msg)  { Write-Host "[Info] $msg"  -ForegroundColor Cyan }
function Write-Done($msg)  { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[Warn] $msg" -ForegroundColor Yellow }

# Get the repository root directory
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $RepoRoot

# --- 1. Start Backend Services ---
$BackendScript = Join-Path $RepoRoot "start_backend.ps1"
if (-not (Test-Path $BackendScript)) {
    throw "Fatal: start_backend.ps1 not found at root. Cannot proceed."
}

Write-Info "Starting core backend services using start_backend.ps1 with background jobs (Dev Graph API excluded)..."
& $BackendScript -UseJobs
Write-Done "Core backend services are starting in the background."
Write-Info "Dev Graph API is not started automatically to avoid ingestion interference. Start manually if needed."

# --- 2. Start Frontend Service ---
$FrontendDir = Join-Path $RepoRoot "frontend"
if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    throw "Fatal: /frontend/package.json not found. Cannot start UI."
}

Write-Info "Changing directory to frontend..."
Set-Location $FrontendDir

# Check if node_modules exists
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Warn "Node modules not found. Running 'npm install'. This might take a moment..."
    npm install
    Write-Done "'npm install' completed."
}

Write-Info "Starting Next.js frontend development server (this will take over the terminal)..."
npm run dev 