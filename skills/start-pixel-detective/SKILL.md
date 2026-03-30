---
name: start-pixel-detective
description: "Start, stop, or check Pixel Detective services on this machine. Use when the user asks to start Pixel Detective, launch backend only, start full stack, restart, stop, or check Docker, Qdrant, ML inference, UMAP, or frontend status, or to provide a specific Pixel Detective page URL."
---

# Start Pixel Detective

Run Pixel Detective locally with the right subset of services.

## Quickstart

```bash
# Full stack
powershell -ExecutionPolicy Bypass -File skills\start-pixel-detective\scripts\start_pixel_detective.ps1 -Mode full

# Backend only (+ optional GPU UMAP)
powershell -ExecutionPolicy Bypass -File skills\start-pixel-detective\scripts\start_pixel_detective.ps1 -Mode backend -UseGpuUmap

# Frontend + open browser
powershell -ExecutionPolicy Bypass -File skills\start-pixel-detective\scripts\start_pixel_detective.ps1 -Mode frontend -Open -Page /search
```

Note: `-Open` is required to open a browser; `-Page` alone will not open anything.

## Workflow

1. **Confirm repo root** — Require `frontend/package.json` and `start_pixel_detective.ps1`. If missing, stop and ask for the correct working directory.

2. **Decide mode:**
   | Mode | Services |
   |------|----------|
   | `full` | All services + frontend |
   | `backend` | Qdrant + ML + ingestion (optional UMAP) |
   | `services` | Docker only (Qdrant, optional GPU UMAP) |
   | `frontend` | Next.js dev server only |
   | `status` | Report what is running |
   | `stop` | Stop Docker services |

3. **Docker preflight** — Verify Docker is running: `docker version` and `docker compose version`. If Docker is installed but not running, say so and stop.

4. **Start services** per mode:
   - `services`: `docker compose up -d qdrant_db` (optional GPU UMAP: `docker compose -f backend/gpu_umap_service/docker-compose.dev.yml up -d --build`)
   - `backend`: Start Qdrant, then ML inference (`uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload`) and ingestion (`uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload`)
   - `frontend`: `cd frontend && npm run dev`
   - `full`: Run the startup script (combines all above)

   Launch uvicorn or npm in new terminal windows so the main session stays responsive.

5. **Verify** — Check `docker compose ps` and confirm ports are reachable:
   - Frontend: http://localhost:3000
   - Ingestion API: http://localhost:8002/docs
   - ML inference API: http://localhost:8001/docs
   - GPU UMAP API: http://localhost:8003/docs
   - Qdrant dashboard: http://localhost:6333/dashboard

6. **Stop** — `docker compose down`. The script attempts to close uvicorn and npm windows tied to this repo.

## Notes

- GPU UMAP can fail without blocking the rest — treat it as optional.
- Qdrant is the only required Docker service; ML and ingestion run on the host.
- If port 3000 is in use, Next.js picks another port; report the actual port from terminal output.
- If ML or ingestion uvicorn exits immediately, check for missing Python dependencies or an inactive virtualenv.
