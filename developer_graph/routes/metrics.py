from __future__ import annotations

from fastapi import APIRouter
from ..app_state import engine


router = APIRouter()


@router.get("/api/v1/dev-graph/metrics")
def get_metrics():
    metrics = engine.get_metrics() if hasattr(engine, "get_metrics") else {}
    mem_mb = 0.0
    try:
        import psutil, os as _os
        mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_000_000.0
    except Exception:
        mem_mb = 0.0
    return {**metrics, "memory_usage_mb": round(mem_mb, 2)}

