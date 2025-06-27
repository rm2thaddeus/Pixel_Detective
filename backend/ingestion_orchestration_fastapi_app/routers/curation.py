from fastapi import APIRouter, Depends, Body
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointIdsList
from pydantic import BaseModel
from typing import List
import os
import shutil
import logging

from ..dependencies import get_qdrant_client, get_active_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/curation", tags=["curation"])


class ArchiveSelectionRequest(BaseModel):
    point_ids: List[str] = Body(..., description="IDs of points to archive")


@router.post("/archive-selection")
async def archive_selection(
    req: ArchiveSelectionRequest,
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection),
):
    """Archive selected images and remove their points."""
    # Snapshot for safety
    snapshot = qdrant.create_snapshot(collection_name=collection_name)
    archived = []
    for pid in req.point_ids:
        try:
            pts = qdrant.retrieve(
                collection_name=collection_name,
                ids=[pid],
                with_payload=True,
                with_vectors=False,
            )
            if not pts:
                continue
            payload = pts[0].payload or {}
            path = payload.get("full_path")
            if path and os.path.exists(path):
                dest_dir = os.path.join(os.path.dirname(path), "_VibeArchive")
                os.makedirs(dest_dir, exist_ok=True)
                shutil.move(path, os.path.join(dest_dir, os.path.basename(path)))
                archived.append(path)
        except Exception as e:
            logger.error(f"Failed to archive {pid}: {e}")
    if req.point_ids:
        qdrant.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=req.point_ids),
        )
    return {"archived": archived, "snapshot": snapshot.name if snapshot else None}
