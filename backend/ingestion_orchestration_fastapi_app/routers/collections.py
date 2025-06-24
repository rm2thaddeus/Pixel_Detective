from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import logging

from ..dependencies import get_qdrant_client, app_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])

class CreateCollectionRequest(BaseModel):
    collection_name: str = Field(..., min_length=1, max_length=128)
    vector_size: int = Field(512, gt=0, description="Dimensionality of the embedding vector")
    distance: str = Field('Cosine', description="Distance metric: Cosine|Dot|Euclid")

class CollectionInfo(BaseModel):
    name: str
    status: str
    points_count: int
    vectors_count: int
    indexed_vectors_count: int
    config: Dict[str, Any]
    sample_points: List[Dict[str, Any]]
    is_active: bool

# === NEW: Create Collection From Selection ===

class CreateCollectionFromSelectionRequest(BaseModel):
    """Request body for creating a new collection from a subset (selection) of an existing one."""
    new_collection_name: str = Field(..., min_length=1, max_length=128,
                                     description="Name of the collection that will be created and populated with the selected points")
    source_collection: str = Field(..., min_length=1, description="Name of the collection from which the points are sourced")
    point_ids: List[str] = Field(..., min_items=1, description="IDs of the points to copy into the new collection")

@router.get("/", response_model=List[str])
async def list_collections(qdrant: QdrantClient = Depends(get_qdrant_client)):
    """Return a list of all collection names in Qdrant."""
    try:
        resp = qdrant.get_collections()
        return [c.name for c in resp.collections]
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to list collections")

@router.get("/{collection_name}/info", response_model=CollectionInfo)
async def get_collection_info(collection_name: str, qdrant: QdrantClient = Depends(get_qdrant_client)):
    """Get detailed information about a specific collection."""
    try:
        # Check if collection exists
        collections = qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if collection_name not in collection_names:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        # Get collection info
        collection_info = qdrant.get_collection(collection_name)
        
        # Get some sample points (up to 5)
        sample_points = []
        try:
            search_result = qdrant.scroll(
                collection_name=collection_name,
                limit=5,
                with_payload=True,
                with_vectors=False
            )
            
            for point in search_result[0]:  # search_result is (points, next_page_offset)
                sample_points.append({
                    "id": point.id,
                    "filename": point.payload.get("filename", "unknown"),
                    "timestamp": point.payload.get("timestamp", ""),
                    "has_thumbnail": bool(point.payload.get("thumbnail_url")),
                    "has_caption": bool(point.payload.get("caption"))
                })
        except Exception as e:
            logger.warning(f"Could not fetch sample points for {collection_name}: {e}")
        
        return CollectionInfo(
            name=collection_name,
            status=collection_info.status.name.lower(),
            points_count=collection_info.points_count,
            vectors_count=collection_info.vectors_count or 0,
            indexed_vectors_count=collection_info.indexed_vectors_count or 0,
            config={
                "vector_size": collection_info.config.params.vectors.size if collection_info.config.params.vectors else None,
                "distance": collection_info.config.params.vectors.distance.name if collection_info.config.params.vectors else None
            },
            sample_points=sample_points,
            is_active=(collection_name == app_state.active_collection)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection info for {collection_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection info: {str(e)}")

@router.post("/", response_model=Dict[str, Any])
async def create_collection(req: CreateCollectionRequest, qdrant: QdrantClient = Depends(get_qdrant_client)):
    """Create a new collection with given vector_size and distance metric."""
    try:
        dist_enum = Distance[req.distance.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Unsupported distance metric")

    qdrant.create_collection(
        collection_name=req.collection_name,
        vectors_config=VectorParams(size=req.vector_size, distance=dist_enum)
    )
    return {"status": "success", "collection": req.collection_name}

@router.post("/from_selection", response_model=Dict[str, Any], status_code=201)
async def create_collection_from_selection(
    req: CreateCollectionFromSelectionRequest,
    qdrant: QdrantClient = Depends(get_qdrant_client)
):
    """Create a new collection and populate it with the given point IDs from *source_collection*.

    This powers the *"Create collection from UMAP selection"* feature in the latent-space tab.
    """

    # 1) Guard: destination collection must not already exist
    existing_collections = [c.name for c in qdrant.get_collections().collections]
    if req.new_collection_name in existing_collections:
        raise HTTPException(status_code=400, detail=f"Collection '{req.new_collection_name}' already exists")

    if req.source_collection not in existing_collections:
        raise HTTPException(status_code=404, detail=f"Source collection '{req.source_collection}' not found")

    # 2) Fetch vector configuration from source so the destination is compatible
    src_info = qdrant.get_collection(req.source_collection)
    vec_params = src_info.config.params.vectors
    if vec_params is None:
        raise HTTPException(status_code=500, detail="Source collection has no vector configuration")

    # 3) Create destination collection with the same vector size / distance
    qdrant.create_collection(
        collection_name=req.new_collection_name,
        vectors_config=VectorParams(size=vec_params.size, distance=vec_params.distance)
    )

    # 4) Retrieve the selected points (vectors + payload) in batches to avoid URL length limits
    BATCH = 256
    remaining_ids = req.point_ids.copy()
    total_copied = 0

    while remaining_ids:
        batch_ids, remaining_ids = remaining_ids[:BATCH], remaining_ids[BATCH:]
        try:
            points = qdrant.retrieve(
                collection_name=req.source_collection,
                ids=batch_ids,
                with_vectors=True,
                with_payload=True
            )
        except Exception as e:
            logger.error(f"Failed to retrieve points from {req.source_collection}: {e}")
            raise HTTPException(status_code=500, detail="Failed to retrieve selected points")

        if not points:
            logger.warning(f"No points returned for ID batch: {batch_ids[:3]}… (len={len(batch_ids)})")
            continue

        # Convert Record -> dict["id","vector","payload"] expected by PointStruct
        formatted_points = [
            {
                "id": p.id,
                "vector": p.vector,
                "payload": p.payload,
            }
            for p in points
        ]

        # Upsert into new collection
        qdrant.upsert(collection_name=req.new_collection_name, points=formatted_points)
        total_copied += len(formatted_points)

    logger.info(
        "Created collection '%s' with %d points copied from '%s'",
        req.new_collection_name, total_copied, req.source_collection
    )

    return {
        "status": "success",
        "new_collection": req.new_collection_name,
        "copied_from": req.source_collection,
        "points_copied": total_copied,
    }

class SelectCollectionRequest(BaseModel):
    collection_name: str = Field(..., min_length=1)

@router.post("/select", response_model=Dict[str, str])
async def select_collection(req: SelectCollectionRequest):
    """Set the active collection in global state."""
    app_state.active_collection = req.collection_name
    logger.info(f"Active collection set to {req.collection_name}")
    return {"selected_collection": req.collection_name}

@router.get("/active", response_model=Dict[str, str])
async def get_active_collection():
    """Get the currently active collection."""
    if app_state.active_collection is None:
        return {"active_collection": None}
    return {"active_collection": app_state.active_collection}

@router.delete("/{collection_name}", response_model=Dict[str, Any])
async def delete_collection(collection_name: str, qdrant: QdrantClient = Depends(get_qdrant_client)):
    """Delete a collection and all its data."""
    try:
        result = qdrant.delete_collection(collection_name=collection_name)
        if result:
            logger.info(f"Collection '{collection_name}' deleted successfully.")
            # If the deleted collection was the active one, clear it
            if app_state.active_collection == collection_name:
                app_state.active_collection = None
                logger.info("Active collection was deleted, now no collection is active.")
            return {"status": "success", "message": f"Collection '{collection_name}' deleted."}
        else:
            # This case might happen if the delete operation fails for some reason other than an exception
            raise HTTPException(status_code=400, detail=f"Failed to delete collection '{collection_name}'.")
    except Exception as e:
        # Qdrant client often raises a generic Exception or ValueError for non-existent collections
        logger.error(f"Error deleting collection '{collection_name}': {e}")
        # A more specific check could be to inspect the error message, but this is a reasonable fallback
        raise HTTPException(status_code=500, detail=f"An error occurred while trying to delete collection '{collection_name}'. It might not exist or there was a connection issue.") 