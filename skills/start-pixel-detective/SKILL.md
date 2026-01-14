---
name: start-pixel-detective
description: Start, stop, or check Pixel Detective services on this machine. Use when the user asks to start Pixel Detective, start backend only, start full stack, restart, stop, or check Docker, Qdrant, ML, UMAP, or frontend status, or to provide a specific Pixel Detective page URL.
---

# Start Pixel Detective

Use this skill to run Pixel Detective locally with the right subset of services.

## Workflow

1. Confirm repo root
- Require `frontend/package.json` and `start_pixel_detective.ps1`.
- If missing, stop and ask for the correct working directory.

2. Decide the requested mode
- full: all services plus frontend
- backend: Qdrant + ML + ingestion (optional UMAP)
- services: just Docker services (Qdrant and optional GPU UMAP)
- frontend: only Next.js dev server
- status: report what is running
- stop: stop Docker services and list any remaining processes

3. Docker preflight
- Check Docker CLI and Docker Compose:
  - `docker version`
  - `docker compose version`
- If Docker is installed but not running, say so and stop.

4. Start sequence
- full: run `.\start_pixel_detective.ps1`
- backend:
  - `docker compose up -d qdrant_db`
  - optional GPU UMAP: `docker compose -f backend/gpu_umap_service/docker-compose.dev.yml up -d --build`
  - start ML service: `uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload`
  - start ingestion: `uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload`
- services:
  - `docker compose up -d qdrant_db`
  - optional GPU UMAP (same command as above)
- frontend:
  - `cd frontend` then `npm run dev`

When launching uvicorn or npm, use new terminal windows so the main session stays responsive.

5. Status checks
- `docker compose ps`
- `Test-NetConnection localhost -Port 6333,8001,8002,8003,3000`
- Report URLs:
  - http://localhost:3000
  - http://localhost:8002/docs
  - http://localhost:8001/docs
  - http://localhost:8003/docs
  - http://localhost:6333/dashboard

6. Stop sequence
- `docker compose down`
- Remind the user to close any uvicorn or npm windows still running.

## Notes
- The GPU UMAP service can fail without blocking the rest. Treat it as optional.
- Use existing startup scripts whenever possible to stay aligned with repo behavior.
- Qdrant is the only required Docker service for Pixel Detective; ML and ingestion run on the host.
- If port 3000 is already in use, Next.js will choose 3001 or another port; report the actual port from the terminal output.
- If the ML or ingestion uvicorn process exits immediately, check for missing Python dependencies or a virtualenv not being activated.

## Script
- Run: `powershell -ExecutionPolicy Bypass -File skills\\start-pixel-detective\\scripts\\start_pixel_detective.ps1 -Mode full`
- Backend only: `-Mode backend -UseGpuUmap`
- Frontend + open page: `-Mode frontend -Page /search -Open`
