---
name: start-dev-graph
description: Start, stop, or check Dev Graph services on this machine. Use when the user asks to start Dev Graph, start backend only, start full stack, restart, stop, or check Docker, Neo4j, API, or UI status, or to provide a specific Dev Graph page URL.
---

# Start Dev Graph

Use this skill to run Dev Graph locally with the right subset of services.

## Workflow

1. Confirm repo root
- Require `developer_graph/api.py` and `start_dev_graph.ps1`.
- If missing, stop and ask for the correct working directory.

2. Decide the requested mode
- full: Neo4j + API + UI
- backend: Neo4j + API only
- services: just Neo4j
- frontend: only Dev Graph UI
- status: report what is running
- stop: stop Docker services and list any remaining processes

3. Docker preflight
- Check Docker CLI and Docker Compose:
  - `docker version`
  - `docker compose version`
- If Docker is installed but not running, say so and stop.

4. Start sequence
- full: run `.\start_dev_graph.ps1`
- backend:
  - `docker compose up -d neo4j`
  - `uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload`
- services:
  - `docker compose up -d neo4j`
- frontend:
  - `cd tools/dev-graph-ui` then `npm run dev`

When launching uvicorn or npm, use new terminal windows so the main session stays responsive.

5. Status checks
- `docker compose ps`
- `Test-NetConnection localhost -Port 7474,7687,8080,3001`
- Report URLs:
  - http://localhost:3001
  - http://localhost:8080/docs
  - http://localhost:7474
  - http://localhost:3001/dev-graph/timeline
  - http://localhost:3001/dev-graph/structure

6. Stop sequence
- `docker compose down`
- Remind the user to close any uvicorn or npm windows still running.

## Notes
- Docker Compose service name is `neo4j` in `docker-compose.yml`.
- The Windows batch script uses `neo4j_db`; do not copy that name here.
- Do not redirect uvicorn output to `dev_graph_api.log` in the repo root. The app writes the same file and will raise a permission error.
- The UI may choose port 3001 if 3000 is already in use; the script expects 3001.

## Script
- Run: `powershell -ExecutionPolicy Bypass -File skills\\start-dev-graph\\scripts\\start_dev_graph.ps1 -Mode full`
- Backend only: `-Mode backend`
- Frontend + open page: `-Mode frontend -Page /dev-graph/structure -Open`
