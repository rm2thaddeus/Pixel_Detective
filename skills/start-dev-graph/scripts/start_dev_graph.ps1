param(
  [ValidateSet('full','backend','services','frontend','status','stop')]
  [string]$Mode = 'full',
  [string]$Page = '',
  [switch]$Open,
  [switch]$SkipWait
)

function Resolve-RepoRoot {
  $current = Resolve-Path $PSScriptRoot
  for ($i = 0; $i -lt 6; $i++) {
    if ((Test-Path (Join-Path $current 'docker-compose.yml')) -and (Test-Path (Join-Path $current 'developer_graph')) -and (Test-Path (Join-Path $current 'tools'))) {
      return $current
    }
    $parent = Split-Path $current -Parent
    if ($parent -eq $current) { break }
    $current = $parent
  }
  if (Test-Path (Join-Path $PWD 'start_dev_graph.ps1')) {
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
    [string]$ApiUrl,
    [string]$UiUrl
  )
  Write-Host 'Ready summary:' -ForegroundColor Cyan
  foreach ($port in 7474,7687,8080,3001) {
    $state = if (Test-Port -Port $port) { 'open' } else { 'closed' }
    Write-Host ("Port {0}: {1}" -f $port, $state)
  }
  if ($ApiUrl) {
    $apiOk = Test-Http -Url ($ApiUrl.TrimEnd('/') + '/api/v1/dev-graph/stats')
    Write-Host ("API {0}: {1}" -f $ApiUrl, ($(if ($apiOk) { 'ok' } else { 'unreachable' })))
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
  if (-not $Open) { return }
  if ([string]::IsNullOrWhiteSpace($Path)) {
    Start-Process $BaseUrl
    return
  }
  if (-not $Path.StartsWith('/')) {
    $Path = '/' + $Path
  }
  Start-Process ($BaseUrl + $Path)
}

function Stop-AppProcesses {
  param([string]$RepoRoot)
  $patterns = @(
    'developer_graph\.api',
    'tools\\dev-graph-ui.*npm run dev',
    'tools\\dev-graph-ui.*next dev'
  )
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine }
  foreach ($pattern in $patterns) {
    $matches = $procs | Where-Object { $_.CommandLine -match $pattern -and $_.CommandLine -match [regex]::Escape($RepoRoot) }
    foreach ($proc in $matches) {
      try { Stop-Process -Id $proc.ProcessId -Force } catch {}
    }
  }
}

$repoRoot = Resolve-RepoRoot
if (-not $repoRoot) {
  Write-Host 'Error: Could not find repo root with start_dev_graph.ps1' -ForegroundColor Red
  exit 1
}

Set-Location $repoRoot

if (-not (Test-Docker)) {
  Write-Host 'Error: Docker is not available or not running.' -ForegroundColor Red
  exit 1
}

$baseUrl = 'http://localhost:3001'
$apiUrl = 'http://localhost:8080'

switch ($Mode) {
  'full' {
    & "$repoRoot\start_dev_graph.ps1"
    if (-not $SkipWait) {
      Wait-Port -Port 8080 -TimeoutSec 120 | Out-Null
      Wait-Port -Port 3001 -TimeoutSec 120 | Out-Null
      Write-ReadySummary -ApiUrl $apiUrl -UiUrl $baseUrl
    }
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'backend' {
    docker compose up -d neo4j
    Start-WindowProcess -Command "cd '$repoRoot'; uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload"
    if (-not $SkipWait) {
      Wait-Port -Port 8080 -TimeoutSec 120 | Out-Null
      Write-ReadySummary -ApiUrl $apiUrl -UiUrl $null
    }
  }
  'services' {
    docker compose up -d neo4j
  }
  'frontend' {
    Start-WindowProcess -Command "cd '$repoRoot\tools\dev-graph-ui'; npm run dev"
    if (-not $SkipWait) {
      Wait-Port -Port 3001 -TimeoutSec 120 | Out-Null
      Write-ReadySummary -ApiUrl $null -UiUrl $baseUrl
    }
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'status' {
    docker compose ps
    Write-ReadySummary -ApiUrl $apiUrl -UiUrl $baseUrl
  }
  'stop' {
    docker compose down
    Stop-AppProcesses -RepoRoot $repoRoot
    Write-Host 'Stopped Docker services and attempted to close uvicorn/npm processes.' -ForegroundColor Yellow
  }
}
