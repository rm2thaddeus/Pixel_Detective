from __future__ import annotations

from fastapi import APIRouter, Query
from ..app_state import engine


router = APIRouter()


@router.get("/api/v1/dev-graph/evolution/requirement/{req_id}")
def requirement_evolution(req_id: str, limit: int = Query(500, le=2000)):
    return engine.build_evolution_timeline_for_requirement(req_id=req_id, limit=limit)


@router.get("/api/v1/dev-graph/evolution/file")
def file_evolution(path: str, limit: int = Query(500, le=2000)):
    return engine.build_evolution_timeline_for_file(path=path, limit=limit)

