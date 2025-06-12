from fastapi import APIRouter, HTTPException, Query, Body, Depends
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, PointStruct, Distance, VectorParams, SearchRequest
from typing import List, Dict, Any, Optional
import logging

# Assuming main.py is in the parent directory of 'routers'
# Adjust the import path if your structure is different.
from ..dependencies import get_qdrant_dependency 

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

# class SearchResultItem(BaseModel):
#     id: str
#     payload: Dict[str, Any]
#     score: float

# class SearchResponse(BaseModel):
#     total: int
#     page: int
#     per_page: int
#     results: List[SearchResultItem]

@router.post("/search", summary="Search images by vector and filters")
async def search_images(
    # Using Body(...) for now, replace with Pydantic model later
    embedding: List[float] = Body(..., description="Query vector for similarity search."),
    filters: Optional[Dict[str, Any]] = Body(None, description="Key-value pairs for filtering metadata."),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return per page."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    qdrant: QdrantClient = Depends(get_qdrant_dependency) # Use dependency from main.py
):
    """
    Search for images based on a query vector and optional metadata filters.
    Returns paginated results with image metadata.
    """
    # This collection_name should come from config or constants
    COLLECTION_NAME = "images" # Example collection name

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

# Placeholder for further Pydantic models and refinements 