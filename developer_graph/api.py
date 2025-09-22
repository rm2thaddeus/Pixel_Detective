"""FastAPI app wiring for Developer Graph API (modular routers)."""
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure app state (driver/services) is initialized
from . import app_state  # noqa: F401

# Routers
from .routes.health_stats import router as health_stats_router
from .routes.nodes_relations import router as nodes_relations_router
from .routes.search import router as search_router
from .routes.commits_timeline import router as commits_timeline_router
from .routes.sprints import router as sprints_router
from .routes.graph import router as graph_router
from .routes.analytics import router as analytics_router
from .routes.ingest import router as ingest_router
from .routes.chunks import router as chunks_router
from .routes.metrics import router as metrics_router
from .routes.validate import router as validate_router
from .routes.quality import router as quality_router
from .routes.data_quality import router as data_quality_router
from .routes.unified_ingest import router as unified_ingest_router
from .routes.admin import router as admin_router
from .routes.evolution import router as evolution_router


app = FastAPI(title="Developer Graph API", version="1.0.0")

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_env_origins = os.environ.get("CORS_ORIGINS")
_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(health_stats_router)
app.include_router(nodes_relations_router)
app.include_router(search_router)
app.include_router(commits_timeline_router)
app.include_router(sprints_router)
app.include_router(graph_router)
app.include_router(analytics_router)
app.include_router(ingest_router)
app.include_router(chunks_router)
app.include_router(metrics_router)
app.include_router(validate_router)
app.include_router(quality_router)
app.include_router(data_quality_router)
app.include_router(unified_ingest_router)
app.include_router(admin_router)
app.include_router(evolution_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

