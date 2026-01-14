param(
  [ValidateSet('full','backend','services','frontend','status','stop')]
  [string]$Mode = 'full',
  [string]$Page = '',
  [switch]$Open
)

function Resolve-RepoRoot {
  $current = Resolve-Path $PSScriptRoot
  for ($i = 0; $i -lt 6; $i++) {
    if (Test-Path (Join-Path $current 'start_dev_graph.ps1')) {
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
  Write-Host 'Error: Could not find repo root with start_dev_graph.ps1' -ForegroundColor Red
  exit 1
}

Set-Location $repoRoot

if (-not (Test-Docker)) {
  Write-Host 'Error: Docker is not available or not running.' -ForegroundColor Red
  exit 1
}

$baseUrl = 'http://localhost:3001'

switch ($Mode) {
  'full' {
    & "$repoRoot\start_dev_graph.ps1"
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'backend' {
    docker compose up -d neo4j
    Start-WindowProcess -Command "cd '$repoRoot'; uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload"
  }
  'services' {
    docker compose up -d neo4j
  }
  'frontend' {
    Start-WindowProcess -Command "cd '$repoRoot\tools\dev-graph-ui'; npm run dev"
    Open-PageUrl -BaseUrl $baseUrl -Path $Page
  }
  'status' {
    docker compose ps
    foreach ($port in 7474,7687,8080,3001) {
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
