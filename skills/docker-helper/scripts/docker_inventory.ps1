param(
  [ValidateSet('status','start','stop','restart','logs','none')]
  [string]$Action = 'status',
  [string]$Target = '',
  [int]$LogsTail = 200,
  [switch]$ShowVolumes,
  [switch]$ListCapabilities
)

function Resolve-RepoRoot {
  $current = Resolve-Path $PSScriptRoot
  for ($i = 0; $i -lt 6; $i++) {
    if (Test-Path (Join-Path $current 'docker-compose.yml')) {
      return $current
    }
    $parent = Split-Path $current -Parent
    if ($parent -eq $current) { break }
    $current = $parent
  }
  if (Test-Path (Join-Path $PWD 'docker-compose.yml')) {
    return $PWD
  }
  return $null
}

function Test-Docker {
  try { docker version | Out-Null } catch { return $false }
  try { docker compose version | Out-Null } catch { return $false }
  return $true
}

if (-not (Test-Docker)) {
  Write-Host 'Error: Docker is not available or not running.' -ForegroundColor Red
  exit 1
}

$repoRoot = Resolve-RepoRoot

function Get-ComposeServices {
  param([string]$RepoRoot)
  if (-not $RepoRoot) { return @() }
  Push-Location $RepoRoot
  try {
    $services = docker compose config --services 2>$null
    if ($services) { return @($services) }
    return @()
  } catch {
    return @()
  } finally {
    Pop-Location
  }
}

if ($ListCapabilities) {
  $services = Get-ComposeServices -RepoRoot $repoRoot
  Write-Host 'Capabilities:' -ForegroundColor Cyan
  if ($services.Count -gt 0) {
    Write-Host ("Compose services: {0}" -f ($services -join ', '))
  } else {
    Write-Host 'Compose services: (repo root not detected)'
  }
  Write-Host 'Actions: status, start, stop, restart, logs'
  Write-Host 'Use -Target <service> for start/stop/restart/logs.'
}

Write-Host 'Docker Containers:' -ForegroundColor Cyan
docker ps -a

Write-Host ''
Write-Host 'Docker Compose Services (repo root only):' -ForegroundColor Cyan
if ($repoRoot) {
  Push-Location $repoRoot
  try { docker compose ps } finally { Pop-Location }
} else {
  Write-Host 'Repo root not detected (docker-compose.yml not found). Compose status/actions are unavailable.' -ForegroundColor Yellow
}

switch ($Action) {
  'status' { }
  'none' { }
  default {
    if ([string]::IsNullOrWhiteSpace($Target)) {
      Write-Host 'Error: -Target is required for this action.' -ForegroundColor Red
      exit 1
    }
    if (-not $repoRoot) {
      Write-Host 'Error: docker-compose.yml not found; actions require repo root.' -ForegroundColor Red
      exit 1
    }
    Push-Location $repoRoot
    try {
      switch ($Action) {
        'start' { docker compose up -d $Target }
        'stop' { docker compose stop $Target }
        'restart' { docker compose restart $Target }
        'logs' { docker compose logs --tail $LogsTail $Target }
      }
    } finally {
      Pop-Location
    }
  }
}

Write-Host ''
Write-Host 'Docker Volumes:' -ForegroundColor Cyan
docker volume ls

docker system df

if ($ShowVolumes) {
  Write-Host ''
  Write-Host 'Volume Details:' -ForegroundColor Cyan
  foreach ($name in 'qdrant_storage','neo4j_data') {
    try {
      docker volume inspect $name
    } catch {
      Write-Host ("Volume not found: {0}" -f $name) -ForegroundColor Yellow
    }
  }
}
