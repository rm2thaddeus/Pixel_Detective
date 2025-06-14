from fastapi import APIRouter, HTTPException, Depends
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition # For potential future use if needed
import random # For a basic random selection if not using a specific Qdrant feature
import logging
from typing import Dict, Any

from ..dependencies import get_qdrant_client, get_active_collection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# TODO: Define Pydantic model for the response
# class RandomImageResponse(BaseModel):
#     id: str
#     payload: Dict[str, Any]
#     # vector: Optional[List[float]] = None # If needed

@router.get("/random", summary="Get a random image from the collection")
async def get_random_image(
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
) -> Dict[str, Any]: # Replace with Pydantic model later
    """
    Retrieves a single random image (point) from the Qdrant collection.
    
    Current implementation detail:
    - Fetches the count of all items.
    - Selects a random offset within that count.
    - Scrolls to that random offset to retrieve one item.
    This might not be the most performant way for extremely large collections if Qdrant
    offers a more direct random sampling method.
    """
    try:
        # Get the total number of points in the collection
        collection_info = qdrant.get_collection(collection_name=collection_name)
        total_points = collection_info.points_count

        if total_points == 0:
            raise HTTPException(status_code=404, detail="No images found in the collection.")

        # Select a random offset
        # Qdrant's scroll `offset` is point ID if `next_page_offset` from previous scroll is used.
        # If we want a truly random Nth item, we need to scroll with a numeric offset.
        # However, Qdrant scroll `offset` parameter directly takes an integer for the number of points to skip.
        random_offset = random.randint(0, total_points - 1)

        # Scroll to retrieve one point at the random offset
        scroll_result = qdrant.scroll(
            collection_name=collection_name,
            limit=1,
            offset=random_offset,
            with_payload=True,
            with_vectors=False # Typically not needed for displaying a random image
        )

        if not scroll_result[0]: # scroll_result is a tuple (points, next_page_offset)
            # This case should ideally not happen if total_points > 0 and offset is correct
            logger.error(f"No point found at random offset {random_offset} when total_points={total_points}")
            raise HTTPException(status_code=404, detail="Could not retrieve a random image despite collection not being empty.")

        random_point = scroll_result[0][0]
        
        return {
            "id": random_point.id,
            "payload": random_point.payload
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting random image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error getting random image: {str(e)}") 