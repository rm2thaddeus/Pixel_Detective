param(
  [ValidateSet('full','backend','services','frontend','status','stop')]
  [string]$Mode = 'full',
  [string]$Page = '',
  [switch]$Open,
  [switch]$UseGpuUmap
)

function Resolve-RepoRoot {
  $current = Resolve-Path $PSScriptRoot
  for ($i = 0; $i -lt 6; $i++) {
    if (Test-Path (Join-Path $current 'start_pixel_detective.ps1')) {
      return $current
    }
    $parent = Split-Path $current -Parent
    if ($parent -eq $current) { break }
    $current = $parent
  }
  if (Test-Path (Join-Path $PWD 'start_pixel_detective.ps1')) {
    return $PWD
  }
  return $null
}

function Test-Docker {
  try { docker version | Out-Null } catch { return $false }
  try { docker compose version | Out-Null } catch { return $false }
  return $true
}

function Start-WindowProcess {
  param(
    [string]$Command
  )
  Start-Process pwsh -ArgumentList '-NoExit', '-Command', $Command -WindowStyle Normal
}

function Open-PageUrl {
  param(
    [string]$BaseUrl,
    [string]$Path
  )
  if (-not $Open -and [string]::IsNullOrWhiteSpace($Path)) {
    return
  }
  if ([string]::IsNullOrWhiteSpace($Path)) {
    Start-Process $BaseUrl
    return
  }
  if (-not $Path.StartsWith('/')) {
    $Path = '/' + $Path
  }
  Start-Process ($BaseUrl + $Path)
}

$repoRoot = Resolve-RepoRoot
if (-not $repoRoot) {
  Write-Host 'Error: Could not find repo root with start_pixel_detective.ps1' -ForegroundColor Red
  exit 1
}

Set-Location $repoRoot

if (-not (Test-Docker)) {
  Write-Host 'Error: Docker is not available or not running.' -ForegroundColor Red
  exit 1
}

$baseUrl = 'http://localhost:3000'

switch ($Mode) {
  'full' {
    & "$repoRoot\start_pixel_detective.ps1"
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'backend' {
    docker compose up -d qdrant_db
    if ($UseGpuUmap) {
      Push-Location "$repoRoot\backend\gpu_umap_service"
      docker compose -f docker-compose.dev.yml up -d --build
      Pop-Location
    }
    Start-WindowProcess -Command "cd '$repoRoot'; uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload"
    Start-WindowProcess -Command "cd '$repoRoot'; uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload"
  }
  'services' {
    docker compose up -d qdrant_db
    if ($UseGpuUmap) {
      Push-Location "$repoRoot\backend\gpu_umap_service"
      docker compose -f docker-compose.dev.yml up -d --build
      Pop-Location
    }
  }
  'frontend' {
    Start-WindowProcess -Command "cd '$repoRoot\frontend'; npm run dev"
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'status' {
    docker compose ps
    foreach ($port in 6333,8001,8002,8003,3000) {
      $result = Test-NetConnection -ComputerName 'localhost' -Port $port -WarningAction SilentlyContinue
      $state = if ($result.TcpTestSucceeded) { 'open' } else { 'closed' }
      Write-Host ("Port {0}: {1}" -f $port, $state)
    }
  }
  'stop' {
    docker compose down
    Write-Host 'Close any uvicorn or npm windows that are still running.' -ForegroundColor Yellow
  }
}
