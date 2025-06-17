from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Dict, Any
from ..dependencies import get_qdrant_client, get_active_collection
from qdrant_client import QdrantClient
import numpy as np
import umap

router = APIRouter(prefix="/umap", tags=["umap"])


@router.get("/projection", summary="Get 2-D UMAP projection for a sample of points")
async def umap_projection(
    sample_size: int = Query(500, ge=10, le=5000, description="Number of points to project"),
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection),
):
    """Return a 2-D UMAP projection of CLIP embeddings for quick scatter-plot visualisation.

    The endpoint randomly samples up to *sample_size* points from the active collection,
    runs UMAP (n_components=2, metric='cosine') on their vectors, and returns a list of
    objects: `{id, x, y, thumbnail_base64}`.  This allows the frontend to render an
    interactive 2-D layout.
    """
    try:
        # 1. Sample points (random seed fixed for determinism per call)
        search_result = qdrant.scroll(
            collection_name=collection_name,
            with_vectors=True,
            with_payload=True,
            limit=sample_size,
        )
        points, _ = search_result
        if not points:
            raise HTTPException(status_code=404, detail="Collection is empty")

        ids = [p.id for p in points]
        vectors = np.vstack([p.vector for p in points]).astype(np.float32)

        # 2. Run UMAP on the embeddings
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42)
        embedding_2d = reducer.fit_transform(vectors)

        # 3. Build response objects
        results: List[Dict[str, Any]] = []
        for idx, p in enumerate(points):
            payload = p.payload or {}
            results.append({
                "id": ids[idx],
                "x": float(embedding_2d[idx, 0]),
                "y": float(embedding_2d[idx, 1]),
                "thumbnail_base64": payload.get("thumbnail_base64"),
                "filename": payload.get("filename")
            })

        return {"points": results, "collection": collection_name}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UMAP projection failed: {e}") 