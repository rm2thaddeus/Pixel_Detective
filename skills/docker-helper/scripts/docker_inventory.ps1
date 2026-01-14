param(
  [ValidateSet('status','start','stop','restart','logs','none')]
  [string]$Action = 'status',
  [string]$Target = '',
  [int]$LogsTail = 200,
  [switch]$ShowVolumes,
  [switch]$ListCapabilities
)

function Test-Docker {
  try { docker version | Out-Null } catch { return $false }
  try { docker compose version | Out-Null } catch { return $false }
  return $true
}

if (-not (Test-Docker)) {
  Write-Host 'Error: Docker is not available or not running.' -ForegroundColor Red
  exit 1
}

if ($ListCapabilities) {
  Write-Host 'Capabilities:' -ForegroundColor Cyan
  Write-Host 'Compose services: qdrant_db, neo4j, dev_graph_api, dev_graph_ui'
  Write-Host 'Actions: status, start, stop, restart, logs'
  Write-Host 'Use -Target <service> for start/stop/restart/logs.'
}

Write-Host 'Docker Containers:' -ForegroundColor Cyan
docker ps -a

Write-Host ''
Write-Host 'Docker Compose Services (repo root only):' -ForegroundColor Cyan
if (Test-Path "${PWD}\docker-compose.yml") {
  docker compose ps
} else {
  Write-Host 'docker-compose.yml not found in current directory.' -ForegroundColor Yellow
}

switch ($Action) {
  'status' { }
  'none' { }
  default {
    if ([string]::IsNullOrWhiteSpace($Target)) {
      Write-Host 'Error: -Target is required for this action.' -ForegroundColor Red
      exit 1
    }
    if (-not (Test-Path "${PWD}\docker-compose.yml")) {
      Write-Host 'Error: docker-compose.yml not found; actions require repo root.' -ForegroundColor Red
      exit 1
    }
    switch ($Action) {
      'start' { docker compose up -d $Target }
      'stop' { docker compose stop $Target }
      'restart' { docker compose restart $Target }
      'logs' { docker compose logs --tail $LogsTail $Target }
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
