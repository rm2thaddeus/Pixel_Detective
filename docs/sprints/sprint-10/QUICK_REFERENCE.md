# Sprint 10 Quick Reference

> Keep this file open in a side pane – it saves context-switch time.

---

## 1. Daily Dev Commands
```bash
# start backend stack (from repo root)
docker-compose up -d qdrant
uvicorn backend.ml_inference_fastapi_app.main:app --port 8001 --reload &
uvicorn backend.ingestion_orchestration_fastapi_app.main:app --port 8002 --reload &

# start frontend
cd frontend
npm install       # first time
npm run dev       # http://localhost:3000
```

### Helpful NPM scripts (to add in package.json)
| Script | Purpose |
|--------|---------|
| `npm run lint` | ESLint check |
| `npm run test` | Jest + RTL |
| `npm run build` | Next.js production build |
| `npm run typecheck` | `tsc --noEmit` |

---

## 2. Environment Variables
| Variable | Example | Notes |
|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8002` | Base REST URL |
| `NEXT_PUBLIC_SOCKET_URL` | `http://localhost:8002` | Will point to WebSocket when implemented |
| `ALLOWED_ORIGIN` | `http://localhost:3000` | Added to FastAPI CORS list |

---

## 3. Backend Endpoints Used
```
GET    /health
GET    /collections
POST   /collections           {collection_name}
POST   /collections/select    {collection_name}
POST   /ingest/               {directory_path}
GET    /ingest/status/{id}
POST   /search                {embedding, limit}
```

---

## 4. Folder Structure Cheatsheet
```
frontend/
  pages/            # Next.js routes
  components/       # Dumb presentational components
  features/         # Smart feature bundles (optional improvement)
  store/            # Zustand slices
  lib/              # api.ts, socket.ts
```

---

## 5. Common Errors & Fixes
| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| CORS 403 | FastAPI missing origin | Check `ALLOWED_ORIGIN`, restart backend |
| 404 on `/health` | Endpoint not added | Implement quick handler as in Tech Plan |
| `TypeError: socket.io...` | Backend WebSocket not ready | Keep `autoConnect:false` for now |
| Images not showing | No thumbnail strategy | Use placeholder for Sprint 10 |

---

## 6. Useful Links
* Critical UI Refactor blueprint – `docs/sprints/critical-ui-refactor/`
* Backend architecture spec – `backend/ARCHITECTURE.md`
* FastAPI docs – https://fastapi.tiangolo.com
* Chakra UI docs – https://chakra-ui.com

---

Happy coding!  Update this cheat-sheet with any recurring commands or tips you discover. 