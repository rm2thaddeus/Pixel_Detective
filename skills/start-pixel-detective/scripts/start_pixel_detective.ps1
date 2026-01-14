param(
  [ValidateSet('full','backend','services','frontend','status','stop')]
  [string]$Mode = 'full',
  [string]$Page = '',
  [switch]$Open,
  [switch]$UseGpuUmap,
  [switch]$SkipWait
)

function Resolve-RepoRoot {
  $current = Resolve-Path $PSScriptRoot
  for ($i = 0; $i -lt 6; $i++) {
    if ((Test-Path (Join-Path $current 'docker-compose.yml')) -and (Test-Path (Join-Path $current 'backend')) -and (Test-Path (Join-Path $current 'frontend'))) {
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
  Start-Process powershell -ArgumentList '-NoExit', '-Command', $Command -WindowStyle Normal
}

function Test-Port {
  param([int]$Port)
  $result = Test-NetConnection -ComputerName 'localhost' -Port $Port -WarningAction SilentlyContinue
  return [bool]$result.TcpTestSucceeded
}

function Wait-Port {
  param(
    [int]$Port,
    [int]$TimeoutSec = 60
  )
  $start = Get-Date
  while (((Get-Date) - $start).TotalSeconds -lt $TimeoutSec) {
    if (Test-Port -Port $Port) { return $true }
    Start-Sleep -Seconds 2
  }
  return $false
}

function Test-Http {
  param([string]$Url)
  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500)
  } catch {
    return $false
  }
}

function Write-ReadySummary {
  param(
    [string]$UiUrl,
    [string]$MlUrl,
    [string]$IngestUrl,
    [string]$UmapUrl
  )
  Write-Host 'Ready summary:' -ForegroundColor Cyan
  foreach ($port in 6333,8001,8002,8003,3000) {
    $state = if (Test-Port -Port $port) { 'open' } else { 'closed' }
    Write-Host ("Port {0}: {1}" -f $port, $state)
  }
  if ($MlUrl) {
    $mlOk = Test-Http -Url ($MlUrl.TrimEnd('/') + '/docs')
    Write-Host ("ML  {0}: {1}" -f $MlUrl, ($(if ($mlOk) { 'ok' } else { 'unreachable' })))
  }
  if ($IngestUrl) {
    $ingestOk = Test-Http -Url ($IngestUrl.TrimEnd('/') + '/docs')
    Write-Host ("Ingest {0}: {1}" -f $IngestUrl, ($(if ($ingestOk) { 'ok' } else { 'unreachable' })))
  }
  if ($UmapUrl) {
    $umapOk = Test-Http -Url $UmapUrl
    Write-Host ("UMAP {0}: {1}" -f $UmapUrl, ($(if ($umapOk) { 'ok' } else { 'unreachable' })))
  }
  if ($UiUrl) {
    $uiOk = Test-Http -Url $UiUrl
    Write-Host ("UI  {0}: {1}" -f $UiUrl, ($(if ($uiOk) { 'ok' } else { 'unreachable' })))
  }
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
$mlUrl = 'http://localhost:8001'
$ingestUrl = 'http://localhost:8002'
$umapUrl = 'http://localhost:8003'
$umapTarget = if ($UseGpuUmap) { $umapUrl } else { $null }

switch ($Mode) {
  'full' {
    & "$repoRoot\start_pixel_detective.ps1"
    if (-not $SkipWait) {
      Wait-Port -Port 8001 -TimeoutSec 120 | Out-Null
      Wait-Port -Port 8002 -TimeoutSec 120 | Out-Null
      Wait-Port -Port 3000 -TimeoutSec 120 | Out-Null
      if ($UseGpuUmap) { Wait-Port -Port 8003 -TimeoutSec 120 | Out-Null }
      Write-ReadySummary -UiUrl $baseUrl -MlUrl $mlUrl -IngestUrl $ingestUrl -UmapUrl $umapTarget
    }
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
    if (-not $SkipWait) {
      Wait-Port -Port 8001 -TimeoutSec 120 | Out-Null
      Wait-Port -Port 8002 -TimeoutSec 120 | Out-Null
      if ($UseGpuUmap) { Wait-Port -Port 8003 -TimeoutSec 120 | Out-Null }
      Write-ReadySummary -UiUrl $null -MlUrl $mlUrl -IngestUrl $ingestUrl -UmapUrl $umapTarget
    }
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
    if (-not $SkipWait) {
      Wait-Port -Port 3000 -TimeoutSec 120 | Out-Null
      Write-ReadySummary -UiUrl $baseUrl -MlUrl $null -IngestUrl $null -UmapUrl $null
    }
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'status' {
    docker compose ps
    Write-ReadySummary -UiUrl $baseUrl -MlUrl $mlUrl -IngestUrl $ingestUrl -UmapUrl $umapTarget
  }
  'stop' {
    docker compose down
    Write-Host 'Close any uvicorn or npm windows that are still running.' -ForegroundColor Yellow
  }
}
