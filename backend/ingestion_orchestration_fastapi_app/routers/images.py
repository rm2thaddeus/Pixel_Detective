from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, ScrollRequest, OrderBy
from typing import List, Dict, Any, Optional, Union
import logging
import json
import base64
import os
import os

from ..dependencies import get_qdrant_client, get_active_collection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/api/v1/images", tags=["images"])

# Removed get_qdrant_client_local_temp

# TODO: Define Pydantic models for response

@router.get("/", summary="List images with pagination, filtering, and sorting")
async def list_images(
    page: int = Query(1, ge=1, description="Page number for pagination."),
    per_page: int = Query(10, ge=1, le=100, description="Number of results to return per page."),
    filters: Optional[str] = Query(None, description="JSON string for filters (e.g., '{\"tag\": \"animal\", \"date_range\": {\"gte\": \"2023-01-01\", \"lte\": \"2023-12-31\"}}')."),
    sort_by: Optional[str] = Query(None, description="Field to sort by (e.g., 'created_at', 'name')."),
    sort_order: Optional[str] = Query("desc", description="Sort order: 'asc' or 'desc'."),
    qdrant: QdrantClient = Depends(get_qdrant_client),
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

@router.get("/{image_id}/thumbnail", summary="Get image thumbnail")
async def get_image_thumbnail(
    image_id: str,
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Get a thumbnail for a specific image by ID.
    Returns the base64 thumbnail stored in Qdrant payload.
    """
    try:
        # Retrieve the point from Qdrant
        points = qdrant.retrieve(
            collection_name=collection_name,
            ids=[image_id],
            with_payload=True,
            with_vectors=False
        )
        
        if not points:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = points[0]
        payload = point.payload
        
        if not payload:
            raise HTTPException(status_code=404, detail=f"No payload data found for image {image_id}")
        
        # Get the base64 thumbnail from payload
        thumbnail_base64 = payload.get("thumbnail_base64")
        if not thumbnail_base64:
            raise HTTPException(status_code=404, detail=f"No thumbnail available for image {image_id}")
        
        # Decode base64 and return as JPEG
        try:
            thumbnail_bytes = base64.b64decode(thumbnail_base64)
            return Response(
                content=thumbnail_bytes,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=3600"}  # Cache for 1 hour
            )
        except Exception as e:
            logger.error(f"Error decoding thumbnail for image {image_id}: {e}")
            raise HTTPException(status_code=500, detail="Error processing thumbnail")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving thumbnail for image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{image_id}/image", summary="Get full image")
async def get_full_image(
    image_id: str,
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Get the full image file by ID.
    Returns the original image file from the file system.
    """
    try:
        # Retrieve the point from Qdrant
        points = qdrant.retrieve(
            collection_name=collection_name,
            ids=[image_id],
            with_payload=True,
            with_vectors=False
        )
        
        if not points:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = points[0]
        payload = point.payload
        
        if not payload:
            raise HTTPException(status_code=404, detail=f"No payload data found for image {image_id}")
        
        # Get the full path from payload
        full_path = payload.get("full_path")
        if not full_path:
            raise HTTPException(status_code=404, detail=f"No file path available for image {image_id}")
        
        # Check if file exists
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"Image file not found at {full_path}")
        
        file_extension = os.path.splitext(full_path)[1].lower()

        # Browsers cannot render RAW files like .dng/.nef/etc. Convert to JPEG on-the-fly
        raw_exts = ('.dng', '.cr2', '.nef', '.arw', '.rw2', '.orf')

        try:
            if file_extension in raw_exts:
                import rawpy
                from PIL import Image
                import io

                with rawpy.imread(full_path) as raw:
                    rgb = raw.postprocess(use_camera_wb=True)
                img = Image.fromarray(rgb).convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                image_data = buf.getvalue()
                media_type = 'image/jpeg'
                filename = os.path.splitext(os.path.basename(full_path))[0] + '.jpg'
            else:
                media_type_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.tiff': 'image/tiff',
                    '.webp': 'image/webp'
                }
                media_type = media_type_map.get(file_extension, 'application/octet-stream')
                with open(full_path, 'rb') as f:
                    image_data = f.read()
                filename = os.path.basename(full_path)

            return Response(
                content=image_data,
                media_type=media_type,
                headers={
                    "Cache-Control": "public, max-age=3600",
                    "Content-Disposition": f"inline; filename=\"{filename}\""
                }
            )
        except Exception as e:
            logger.error(f"Error reading image file {full_path}: {e}")
            raise HTTPException(status_code=500, detail="Error reading image file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving full image for {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{image_id}/info", summary="Get image information")
async def get_image_info(
    image_id: str,
    qdrant: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Get detailed information about a specific image.
    """
    try:
        # Retrieve the point from Qdrant
        points = qdrant.retrieve(
            collection_name=collection_name,
            ids=[image_id],
            with_payload=True,
            with_vectors=False
        )
        
        if not points:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = points[0]
        payload = point.payload
        
        if not payload:
            raise HTTPException(status_code=404, detail=f"No data found for image {image_id}")
        
        # Return image information (excluding the base64 thumbnail for performance)
        info = {
            "id": image_id,
            "filename": payload.get("filename"),
            "full_path": payload.get("full_path"),
            "caption": payload.get("caption"),
            "file_hash": payload.get("file_hash"),
            "width": payload.get("width"),
            "height": payload.get("height"),
            "format": payload.get("format"),
            "mode": payload.get("mode"),
            "has_thumbnail": bool(payload.get("thumbnail_base64"))
        }
        
        # Include tags if present
        if "tags" in payload:
            info["tags"] = payload.get("tags")
        
        # Add EXIF data if available
        exif_data = {}
        for key, value in payload.items():
            if key.startswith("exif_"):
                exif_data[key[5:]] = value  # Remove "exif_" prefix
        
        if exif_data:
            info["exif"] = exif_data
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving info for image {image_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 