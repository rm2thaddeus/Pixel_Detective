from fastapi import APIRouter, Depends, HTTPException, Body, Query, File, UploadFile
from qdrant_client import QdrantClient, models
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import logging
import httpx
import os
import base64
import json

# Import the new dependency getters, NOT the main app or old dependencies
from ..dependencies import get_qdrant_client, get_active_collection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"]
)

# Configuration
# Prefer the explicit ML_SERVICE_URL env var, but fall back to the older
# ML_INFERENCE_SERVICE_URL alias so operators only need to set **one**.
ML_SERVICE_URL = (
    os.getenv("ML_SERVICE_URL")
    or os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
)

# --- Pydantic Models for API validation and documentation ---

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata filters for hybrid search")

class SearchResultItem(BaseModel):
    id: Union[str, int]
    score: float
    payload: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


# --- Helper function for building Qdrant filters ---
def build_qdrant_filter(filters: Optional[Dict[str, Any]]) -> Optional[models.Filter]:
    """Convert simple filter dict to Qdrant Filter object."""
    if not filters:
        return None
    
    must_conditions = []
    for key, value in filters.items():
        if isinstance(value, dict) and "gte" in value and "lte" in value:
            # Range filter
            must_conditions.append(models.FieldCondition(
                key=key, 
                range=models.Range(gte=value["gte"], lte=value["lte"])
            ))
        elif isinstance(value, list):
            # Multiple values - use SHOULD for any match
            should_conditions = [
                models.FieldCondition(key=key, match=models.MatchValue(value=v)) 
                for v in value
            ]
            if should_conditions:
                must_conditions.append(models.Filter(should=should_conditions))
        else:
            # Single value match
            must_conditions.append(models.FieldCondition(
                key=key, 
                match=models.MatchValue(value=value)
            ))
    
    return models.Filter(must=must_conditions) if must_conditions else None


# --- API Endpoints ---

@router.post("", response_model=SearchResponse, summary="Search images by text query")
@router.post("/", response_model=SearchResponse, summary="Search images by text query")
async def search_images_by_text(
    search_request: SearchRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Performs a hybrid search based on a natural language text query.
    1. Encodes the text query into a vector using the ML service.
    2. Searches for the most similar vectors in the specified Qdrant collection.
    3. Optionally applies metadata filters for hybrid search.
    """
    logger.info(f"Searching in collection '{collection_name}' for: '{search_request.query}' with filters: {search_request.filters}")

    # 1. Encode the text query into a vector using the ML service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/v1/embed_text",
                json={"text": search_request.query, "description": f"Search query: {search_request.query}"}
            )
            response.raise_for_status()
            query_vector = response.json()["embedding"]
    except Exception as e:
        logger.error(f"Failed to encode query '{search_request.query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to encode query: {e}")

    # 2. Build Qdrant filter if filters provided
    query_filter = build_qdrant_filter(search_request.filters)

    # 3. Perform the search in Qdrant
    try:
        hits = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=search_request.limit,
            offset=search_request.offset,
            with_payload=True,  # Ensure we get metadata back
            query_filter=query_filter  # Add hybrid search support
        )
    except Exception as e:
        # This is a critical error, often because the collection doesn't exist
        # or Qdrant is unavailable.
        logger.error(f"Search failed for collection '{collection_name}'. Error: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Search failed. Collection '{collection_name}' may not exist or Qdrant is down.")

    # 4. Format the results into our response model
    results = [
        SearchResultItem(
            id=hit.id,
            score=hit.score,
            payload=hit.payload,
            filename=hit.payload.get("filename") if hit.payload else None,
            thumbnail_url=f"/api/v1/images/{hit.id}/thumbnail" # Example URL
        )
        for hit in hits
    ]
    
    logger.info(f"Found {len(results)} results for query.")
    return SearchResponse(results=results)

@router.post("/image", response_model=SearchResponse, summary="Search images by reference image")
async def search_images_by_image(
    file: UploadFile = File(...),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    filters: Optional[str] = Query(None, description="JSON string for metadata filters"),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """Search the collection for images visually similar to an uploaded image.

    Workflow:
    1. Read the uploaded file and base64-encode it.
    2. Forward the image to the ML inference service `/embed` endpoint to obtain a
       CLIP embedding.
    3. Perform a vector search in the active Qdrant collection with that
       embedding and optional metadata filters.
    """
    # 1. Read file into memory
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # 2. Parse filters if provided
    filter_dict = None
    if filters:
        try:
            filter_dict = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for filters")
    
    query_filter = build_qdrant_filter(filter_dict)

    # 3. Get embedding from ML service
    try:
        image_b64 = base64.b64encode(image_bytes).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/api/v1/embed",
                json={
                    "image_base64": image_b64,
                    "filename": file.filename or "uploaded_image"
                },
                timeout=120.0
            )
            resp.raise_for_status()
            embedding = resp.json().get("embedding")
            if embedding is None:
                raise ValueError("ML service did not return an embedding")
    except Exception as e:
        logger.error(f"Failed to obtain embedding from ML service: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate embedding for uploaded image")

    # 4. Vector search in Qdrant with optional filters
    try:
        hits = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=limit,
            offset=offset,
            with_payload=True,
            query_filter=query_filter  # Add hybrid search support
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="Vector search failed")

    results = [
        SearchResultItem(
            id=hit.id,
            score=hit.score,
            payload=hit.payload,
            filename=hit.payload.get("filename") if hit.payload else None,
            thumbnail_url=f"/api/v1/images/{hit.id}/thumbnail"
        )
        for hit in hits
    ]

    return SearchResponse(results=results)
