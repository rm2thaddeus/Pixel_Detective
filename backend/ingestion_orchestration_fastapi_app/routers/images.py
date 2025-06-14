from fastapi import APIRouter, HTTPException, Query, Depends
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, ScrollRequest, OrderBy
from typing import List, Dict, Any, Optional
import logging

from ..dependencies import get_qdrant_dependency, get_active_collection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# Removed get_qdrant_client_local_temp

# TODO: Define Pydantic models for response

@router.get("/", summary="List images with pagination, filtering, and sorting")
async def list_images(
    page: int = Query(1, ge=1, description="Page number for pagination."),
    per_page: int = Query(10, ge=1, le=100, description="Number of results to return per page."),
    filters: Optional[str] = Query(None, description="JSON string for filters (e.g., '{\"tag\": \"animal\", \"date_range\": {\"gte\": \"2023-01-01\", \"lte\": \"2023-12-31\"}}')."),
    sort_by: Optional[str] = Query(None, description="Field to sort by (e.g., 'created_at', 'name')."),
    sort_order: Optional[str] = Query("desc", description="Sort order: 'asc' or 'desc'."),
    qdrant: QdrantClient = Depends(get_qdrant_dependency),
    collection_name: str = Depends(get_active_collection)
):
    """
    List images with pagination, filtering, and sorting options.
    """
    offset = (page - 1) * per_page

    try:
        qdrant_filter = None
        if filters:
            try:
                import json
                filter_dict = json.loads(filters)
                must_conditions = []
                for key, value in filter_dict.items():
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
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for filters.")
            except Exception as e:
                logger.error(f"Error processing filters: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Error processing filters: {str(e)}")

        qdrant_order_by = None
        if sort_by:
            # Use string direction as 'asc' or 'desc'
            direction = sort_order.lower() if sort_order and sort_order.lower() in ("asc", "desc") else "desc"
            qdrant_order_by = OrderBy(key=sort_by, direction=direction)
        
        # Using scroll API for pagination
        # Note: Qdrant's scroll API uses `offset` as a point ID to start from if `page_offset` is not None.
        # For simple limit/offset pagination, it's often easier to use search with a null vector if not sorting by score,
        # or use scroll with careful offset management. Here, we'll use the basic limit/offset approach with scroll.
        # If sorting by a field other than score, `search` might be more direct with a `match_all: {}` query filter.
        
        scroll_request = ScrollRequest(
            collection_name=collection_name,
            scroll_filter=qdrant_filter,
            limit=per_page,
            offset=offset, # This offset for scroll is a numeric offset of points
            with_payload=True,
            with_vectors=False,
            order_by=qdrant_order_by
        )
        
        scroll_result = qdrant.scroll(**scroll_request.dict(exclude_none=True))

        results = []
        for hit in scroll_result[0]: # scroll_result is a tuple (points, next_page_offset)
            results.append({
                "id": hit.id,
                "payload": hit.payload
                # No score in scroll results unless it was part of payload or used for sorting
            })
        
        # Get total count matching the filter for accurate pagination meta
        count_result = qdrant.count(collection_name=collection_name, scroll_filter=qdrant_filter, exact=True)
        total_hits = count_result.count

        return {
            "total": total_hits,
            "page": page,
            "per_page": per_page,
            "results": results,
            "next_page_offset": scroll_result[1] # Can be used for more efficient subsequent scrolls
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error listing images: {str(e)}") 