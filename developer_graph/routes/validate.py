from __future__ import annotations

from fastapi import APIRouter, HTTPException
from ..app_state import validator


router = APIRouter()


@router.get("/api/v1/dev-graph/validate/schema")
def validate_schema():
    return validator.validate_schema_completeness()


@router.get("/api/v1/dev-graph/validate/temporal")
def validate_temporal():
    return validator.validate_temporal_consistency()


@router.get("/api/v1/dev-graph/validate/relationships")
def validate_relationships():
    return validator.validate_relationship_integrity()


@router.get("/api/v1/dev-graph/validate/temporal-semantic")
def validate_temporal_semantic():
    return validator.validate_temporal_semantic_graph()


@router.post("/api/v1/dev-graph/cleanup/orphans")
def cleanup_orphans():
    try:
        deleted = validator.cleanup_orphaned_nodes()
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/maintenance/backfill-timestamps")
def backfill_timestamps():
    try:
        result = validator.backfill_missing_timestamps()
        return {"updated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

