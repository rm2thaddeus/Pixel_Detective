from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
import logging
from ..app_state import driver, chunk_service


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/v1/dev-graph/chunks/statistics")
def get_chunk_statistics():
    try:
        return chunk_service.get_chunk_statistics()
    except Exception as e:
        logger.exception("Failed to get chunk statistics")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/chunks")
def list_chunks(
    kind: Optional[str] = Query(None, description="Filter by chunk kind (doc/code)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of chunks"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    try:
        with driver.session() as session:
            if kind:
                cypher = """
                    MATCH (ch:Chunk {kind: $kind})
                    RETURN ch, labels(ch) AS labels
                    SKIP $offset LIMIT $limit
                """
                records = session.run(cypher, kind=kind, offset=offset, limit=limit)
            else:
                cypher = """
                    MATCH (ch:Chunk)
                    RETURN ch, labels(ch) AS labels
                    SKIP $offset LIMIT $limit
                """
                records = session.run(cypher, offset=offset, limit=limit)
            chunks = []
            for record in records:
                chunk_data = record["ch"]
                labels = record.get("labels", [])
                chunk_id = chunk_data.get("id", "unknown")
                chunks.append({
                    "id": chunk_id,
                    "kind": chunk_data.get("kind"),
                    "heading": chunk_data.get("heading"),
                    "section": chunk_data.get("section"),
                    "file_path": chunk_data.get("file_path"),
                    "span": chunk_data.get("span"),
                    "length": chunk_data.get("length"),
                    "has_embedding": chunk_data.get("embedding") is not None,
                    "symbol": chunk_data.get("symbol"),
                    "symbol_type": chunk_data.get("symbol_type"),
                    "labels": labels,
                })
            return {"chunks": chunks, "total": len(chunks), "offset": offset, "limit": limit}
    except Exception as e:
        logger.exception("Failed to list chunks")
        raise HTTPException(status_code=500, detail=str(e))

