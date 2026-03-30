---
name: start-dev-graph
description: "Start, stop, or check Dev Graph services on this machine. Use when the user asks to start Dev Graph, launch backend only, start full stack, restart, stop, or check Docker, Neo4j, API, or UI status, or to provide a specific Dev Graph page URL."
---

# Start Dev Graph

Run Dev Graph locally with the right subset of services.

## Quickstart

```bash
# Full stack (Neo4j + API + UI)
powershell -ExecutionPolicy Bypass -File skills\start-dev-graph\scripts\start_dev_graph.ps1 -Mode full

# Backend only (Neo4j + API)
powershell -ExecutionPolicy Bypass -File skills\start-dev-graph\scripts\start_dev_graph.ps1 -Mode backend

# Frontend + open browser
powershell -ExecutionPolicy Bypass -File skills\start-dev-graph\scripts\start_dev_graph.ps1 -Mode frontend -Open -Page /dev-graph/structure
```

Note: `-Open` is required to open a browser; `-Page` alone will not open anything.

## Workflow

1. **Confirm repo root** — Require `developer_graph/api.py` and `start_dev_graph.ps1`. If missing, stop and ask for the correct working directory.

2. **Decide mode:**
   | Mode | Services |
   |------|----------|
   | `full` | Neo4j + API + UI |
   | `backend` | Neo4j + API only |
   | `services` | Neo4j only |
   | `frontend` | Dev Graph UI only |
   | `status` | Report what is running |
   | `stop` | Stop Docker services |

3. **Docker preflight** — Verify Docker is running: `docker version` and `docker compose version`. If Docker is installed but not running, say so and stop.

4. **Start services** per mode:
   - `services`: `docker compose up -d neo4j`
   - `backend`: `docker compose up -d neo4j` then `uvicorn developer_graph.api:app --host 0.0.0.0 --port 8080 --reload`
   - `frontend`: `cd tools/dev-graph-ui && npm run dev`
   - `full`: Run the startup script (combines all above)

   Launch uvicorn or npm in new terminal windows so the main session stays responsive.

5. **Verify** — Check `docker compose ps` and confirm ports are reachable:
   - UI: http://localhost:3001
   - API docs: http://localhost:8080/docs
   - Neo4j browser: http://localhost:7474
   - Timeline: http://localhost:3001/dev-graph/timeline
   - Structure: http://localhost:3001/dev-graph/structure

6. **Stop** — `docker compose down`. Remind the user to close any uvicorn or npm terminal windows.

## Notes

- Docker Compose service name is `neo4j` (not `neo4j_db` from the batch script).
- Do not redirect uvicorn output to `dev_graph_api.log` — the app writes the same file and raises a permission error.
- The UI defaults to port 3001 if 3000 is in use; the script expects 3001.
