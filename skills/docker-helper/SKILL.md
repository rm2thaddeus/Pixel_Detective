---
name: docker-helper
description: Inspect Docker containers, volumes, and compose services for Pixel Detective and Dev Graph. Use when the user asks to check Docker state, list containers or volumes, or extract data from Docker without running heavy services.
---

# Docker Helper

Use this skill to read Docker state for the repo and list stored data sources.

## Workflow

1. Confirm Docker is available
- `docker version`
- `docker compose version`

2. Inspect containers and compose services
- `docker ps -a`
- `docker compose ps`

3. Inspect volumes and storage
- `docker volume ls`
- `docker system df`
- For repo volumes, run:
  - `docker volume inspect qdrant_storage`
  - `docker volume inspect neo4j_data`

4. Report findings
- Note which services are up, stopped, or missing.
- Identify which volumes exist and their mountpoints.

## Script
- Run: `powershell -ExecutionPolicy Bypass -File skills\docker-helper\scripts\docker_inventory.ps1`
- With volume details: `-ShowVolumes`
