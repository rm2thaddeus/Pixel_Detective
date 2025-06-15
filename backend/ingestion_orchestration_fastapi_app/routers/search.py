from fastapi import APIRouter, Depends, HTTPException, Body, Query
from qdrant_client import QdrantClient, models
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import logging
import httpx
import os

# Import the new dependency getters, NOT the main app or old dependencies
from ..dependencies import get_qdrant_client, get_active_collection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/search",
    tags=["search"]
)

# Configuration
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")

# --- Pydantic Models for API validation and documentation ---

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class SearchResultItem(BaseModel):
    id: Union[str, int]
    score: float
    payload: Optional[Dict[str, Any]] = None
    filename: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


# --- API Endpoints ---

@router.post("/text", response_model=SearchResponse, summary="Search images by text query")
async def search_images_by_text(
    search_request: SearchRequest,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Performs a vector search based on a natural language text query.
    1. Encodes the text query into a vector using the ML service.
    2. Searches for the most similar vectors in the specified Qdrant collection.
    """
    logger.info(f"Searching in collection '{collection_name}' for: '{search_request.query}'")

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

    # 2. Perform the search in Qdrant
    try:
        hits = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=search_request.limit,
            offset=search_request.offset,
            with_payload=True  # Ensure we get metadata back
        )
    except Exception as e:
        # This is a critical error, often because the collection doesn't exist
        # or Qdrant is unavailable.
        logger.error(f"Search failed for collection '{collection_name}'. Error: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Search failed. Collection '{collection_name}' may not exist or Qdrant is down.")

    # 3. Format the results into our response model
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
