from fastapi import APIRouter, HTTPException, Query, Body, Depends
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, PointStruct, Distance, VectorParams, SearchRequest
from typing import List, Dict, Any, Optional
import logging
import httpx
from pydantic import BaseModel, Field

# Assuming main.py is in the parent directory of 'routers'
# Adjust the import path if your structure is different.
from ..dependencies import get_qdrant_dependency, get_active_collection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# Dependency to get the global Qdrant client instance from main.py
# This assumes main.py initializes `app.state.qdrant_client` or provides it via a similar mechanism.
# For this to work, main.py needs to attach the client to app.state or use a global that this can access.
# A common way is to use a dependency in main.py that yields the client.

# Simplified: We'll modify this to expect it from app.state after updating main.py
# For now, this is a placeholder for the refactored dependency.
# from ..main import get_qdrant_client_dependency # This would be ideal if main.py provides it

# Placeholder until main.py is updated
# def get_qdrant_client():
#    from ..main import qdrant_client # Access global client from main
#    if qdrant_client is None:
#        logger.error("Qdrant client not initialized globally.")
#        raise HTTPException(status_code=503, detail="Qdrant service not available - client not initialized.")
#    return qdrant_client

# We will define a common qdrant client dependency in main.py and import it here.
# For now, let's assume it will be available as `from ..dependencies import get_qdrant_client_dep`
# So, the Depends will look like: Depends(get_qdrant_client_dep)
# I will adjust this after creating the dependency in main.py.
# For now, I will keep the original local get_qdrant_client to ensure the file is runnable in isolation temporarily
# and will make a note to update it once main.py is refactored.

# Removed get_qdrant_client_local_temp as we now use the dependency from main.py

# TODO: Define Pydantic models for request and response bodies for better validation and OpenAPI docs
# Example:
# class SearchQuery(BaseModel):
#     embedding: List[float]
#     filters: Optional[Dict[str, Any]] = None
#     limit: int = 10
#     offset: int = 0

class TextSearchRequest(BaseModel):
    text: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class SearchResultItem(BaseModel):
    id: str
    payload: Dict[str, Any]
    score: float
    filename: Optional[str] = None
    caption: Optional[str] = None
    thumbnail_url: Optional[str] = None

class TextSearchResponse(BaseModel):
    total_approx: int
    page: int
    per_page: int
    results: List[SearchResultItem]
    query: str
    embedding_model: Optional[str] = None

@router.post("/search", summary="Search images by vector and filters")
async def search_images(
    # Using Body(...) for now, replace with Pydantic model later
    embedding: List[float] = Body(..., description="Query vector for similarity search."),
    filters: Optional[Dict[str, Any]] = Body(None, description="Key-value pairs for filtering metadata."),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return per page."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    qdrant: QdrantClient = Depends(get_qdrant_dependency), # Use dependency from main.py
    collection_name: str = Depends(get_active_collection)  # Get active collection
):
    """
    Search for images based on a query vector and optional metadata filters.
    Returns paginated results with image metadata.
    """
    COLLECTION_NAME = collection_name

    try:
        qdrant_filter = None
        if filters:
            must_conditions = []
            for key, value in filters.items():
                # This is a simplistic filter creation. Qdrant supports more complex conditions.
                # Adjust based on actual metadata structure and filtering needs.
                if isinstance(value, dict) and "gte" in value and "lte" in value: # Range filter
                     must_conditions.append(FieldCondition(key=key, range=Range(gte=value["gte"], lte=value["lte"])))
                elif isinstance(value, list): # Match any of these values
                    should_conditions = [FieldCondition(key=key, match={"value": v}) for v in value]
                    if should_conditions:
                         must_conditions.append(Filter(should=should_conditions)) # Or logic for list of values
                else: # Exact match
                    must_conditions.append(FieldCondition(key=key, match={"value": value}))
            
            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)

        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            query_filter=qdrant_filter,
            limit=limit,
            offset=offset,
            with_payload=True, # To get metadata
            with_vectors=False # Usually not needed for search results display
        )

        results = []
        for hit in search_result:
            results.append({
                "id": hit.id,
                "payload": hit.payload,
                "score": hit.score
            })
        
        # For 'total', Qdrant doesn't directly give total matching filter without iterating all.
        # A common approach is to get count for the filter separately if exact total is needed,
        # or rely on client-side understanding that more pages might exist.
        # For simplicity, we'll estimate total based on if we got 'limit' results or less for this page + offset.
        # A more accurate count requires a count API call.
        
        # Simplified total for now. Replace with actual count from Qdrant if performance allows.
        # count_result = qdrant.count(collection_name=COLLECTION_NAME, query_filter=qdrant_filter, exact=True)
        # total_hits = count_result.count
        
        # This is a placeholder for total.
        # In a real scenario, you might need a separate count or adjust how total is reported.
        total_hits_approximation = offset + len(results)
        if len(results) == limit:
             # Could be more, this is just an approximation
             total_hits_approximation += limit 

        return {
            "total_approx": total_hits_approximation, # Emphasize this is an approximation
            "page": (offset // limit) + 1 if limit > 0 else 1,
            "per_page": limit,
            "results": results
        }

    except HTTPException:
        raise # Re-raise HTTPException from get_qdrant_client
    except Exception as e:
        logger.error(f"Error during image search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during search: {str(e)}")

@router.post("/search/text", response_model=TextSearchResponse, summary="Search images by text query")
async def search_images_by_text(
    request: TextSearchRequest,
    qdrant: QdrantClient = Depends(get_qdrant_dependency),
    collection_name: str = Depends(get_active_collection)  # Get active collection
):
    """
    Search for images using natural language text queries.
    Converts text to embeddings via ML service, then searches Qdrant.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text query cannot be empty")
    
    logger.info(f"Text search request: '{text[:50]}{'...' if len(text) > 50 else ''}' (limit={request.limit}, offset={request.offset})")
    
    try:
        # Step 1: Convert text to embedding via ML service
        ml_service_url = "http://localhost:8001/api/v1/embed_text"  # TODO: Make configurable
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            ml_response = await client.post(
                ml_service_url,
                json={"text": text, "description": f"Search query: {text}"}
            )
            
            if ml_response.status_code != 200:
                logger.error(f"ML service error: {ml_response.status_code} - {ml_response.text}")
                raise HTTPException(
                    status_code=503, 
                    detail=f"ML service unavailable for text embedding: {ml_response.status_code}"
                )
            
            ml_data = ml_response.json()
            embedding = ml_data["embedding"]
            embedding_model = ml_data.get("model_name", "unknown")
            
            logger.info(f"Generated embedding: shape={len(embedding)}, model={embedding_model}")
        
        # Step 2: Search Qdrant with the embedding
        COLLECTION_NAME = collection_name
        
        qdrant_filter = None
        if request.filters:
            must_conditions = []
            for key, value in request.filters.items():
                if isinstance(value, dict) and "gte" in value and "lte" in value:
                    must_conditions.append(FieldCondition(key=key, range=Range(gte=value["gte"], lte=value["lte"])))
                elif isinstance(value, list):
                    should_conditions = [FieldCondition(key=key, match={"value": v}) for v in value]
                    if should_conditions:
                        must_conditions.append(Filter(should=should_conditions))
                else:
                    must_conditions.append(FieldCondition(key=key, match={"value": value}))
            
            if must_conditions:
                qdrant_filter = Filter(must=must_conditions)
        
        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding,
            query_filter=qdrant_filter,
            limit=request.limit,
            offset=request.offset,
            with_payload=True,
            with_vectors=False
        )
        
        # Step 3: Format results for frontend
        results = []
        for hit in search_result:
            # Extract common fields from payload
            payload = hit.payload or {}
            result_item = SearchResultItem(
                id=str(hit.id),
                payload=payload,
                score=float(hit.score),
                filename=payload.get("filename"),
                caption=payload.get("caption"),
                thumbnail_url=f"http://localhost:8002/api/v1/images/{hit.id}/thumbnail"  # Correct URL format
            )
            results.append(result_item)
        
        # Approximate total calculation
        total_hits_approximation = request.offset + len(results)
        if len(results) == request.limit:
            total_hits_approximation += request.limit
        
        logger.info(f"Text search completed: {len(results)} results found")
        
        return TextSearchResponse(
            total_approx=total_hits_approximation,
            page=(request.offset // request.limit) + 1 if request.limit > 0 else 1,
            per_page=request.limit,
            results=results,
            query=text,
            embedding_model=embedding_model
        )
        
    except httpx.RequestError as e:
        logger.error(f"Network error connecting to ML service: {e}")
        raise HTTPException(status_code=503, detail="ML service unavailable for text embedding")
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error during text search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during text search: {str(e)}")

# Placeholder for further Pydantic models and refinements 