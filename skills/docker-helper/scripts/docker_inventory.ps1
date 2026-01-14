param(
  [switch]$ShowVolumes
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

Write-Host 'Docker Containers:' -ForegroundColor Cyan
docker ps -a

Write-Host ''
Write-Host 'Docker Compose Services (repo root only):' -ForegroundColor Cyan
if (Test-Path "${PWD}\docker-compose.yml") {
  docker compose ps
} else {
  Write-Host 'docker-compose.yml not found in current directory.' -ForegroundColor Yellow
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
