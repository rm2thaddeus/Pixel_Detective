"""
Service API layer for the Frontend.

This module centralizes all HTTP calls from the Streamlit UI to the backend FastAPI services
(ML Inference and Ingestion Orchestration). It uses the 'requests' library for making
synchronous HTTP calls. Backend service URLs should be configurable, typically via
environment variables or a dedicated frontend configuration mechanism.
"""
import httpx
import asyncio
import os
import logging
import streamlit as st
import base64 # New import
import json
from utils.logger import get_logger

logger = get_logger(__name__)

# Configuration for backend services - these should ideally come from environment variables
# For example: os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
ML_INFERENCE_URL = os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
INGESTION_ORCHESTRATION_URL = os.getenv("INGESTION_ORCHESTRATION_SERVICE_URL", "http://localhost:8002/api/v1") # Assuming 8002 for ingestion

# Cached HTTPX client
def get_async_client():
    """
    Returns a new HTTPX AsyncClient to ensure fresh event loop context for each call.
    """
    return httpx.AsyncClient(timeout=30.0) # Increased timeout for potentially long operations

# --- ML Inference Service Endpoints ---

async def get_embedding(image_bytes: bytes, model_name: str = "clip"):
    """
    Gets an embedding for a given image using the ML Inference service.
    
    Args:
        image_bytes: The image file in bytes.
        model_name: The name of the model to use (e.g., 'clip', 'blip').
                   This might be determined by the backend or configurable.
                   
    Returns:
        A dictionary containing the embedding or an error response.
    """
    client = get_async_client()
    try:
        image_base64_str = base64.b64encode(image_bytes).decode('utf-8')
        payload = {"image_base64": image_base64_str, "filename": "uploaded_image.jpg"} # Assuming a generic filename
        response = await client.post(f"{ML_INFERENCE_URL}/embed?model_name={model_name}", json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling ML inference service for embedding: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling ML inference service for embedding: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error getting embedding: {e}")
        return {"error": str(e)}

async def get_caption(image_bytes: bytes, model_name: str = "blip"):
    """
    Gets a caption for a given image using the ML Inference service.
    
    Args:
        image_bytes: The image file in bytes.
        model_name: The name of the captioning model to use.
        
    Returns:
        A dictionary containing the caption or an error response.
    """
    client = get_async_client()
    try:
        image_base64_str = base64.b64encode(image_bytes).decode('utf-8')
        payload = {"image_base64": image_base64_str, "filename": "uploaded_image.jpg"}
        response = await client.post(f"{ML_INFERENCE_URL}/caption?model_name={model_name}", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling ML inference service for captioning: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling ML inference service for captioning: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error getting caption: {e}")
        return {"error": str(e)}

async def batch_embed_and_caption(images: list):
    """
    Batch embed and caption images using the ML Inference backend.
    Args:
        images: List of dicts with keys 'unique_id', 'image_bytes', 'filename'.
    Returns:
        Backend response (list of results or error).
    """
    client = get_async_client()
    try:
        # Prepare payload: base64 encode each image
        payload = {
            "images": [
                {
                    "unique_id": img["unique_id"],
                    "image_base64": base64.b64encode(img["image_bytes"]).decode("utf-8"),
                    "filename": img["filename"]
                }
                for img in images
            ]
        }
        response = await client.post(f"{ML_INFERENCE_URL}/batch_embed_and_caption", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling batch_embed_and_caption: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling batch_embed_and_caption: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error in batch_embed_and_caption: {e}")
        return {"error": str(e)}

# --- Ingestion Orchestration Service Endpoints ---

async def start_ingestion(folder_path: str):
    """
    Starts the ingestion process for a given folder.
    Corresponds to POST /api/v1/ingest in the backend.
    """
    client = get_async_client()
    payload = {"directory_path": folder_path}
    url = f"{INGESTION_ORCHESTRATION_URL}/ingest/"
    
    logger.info(f"Requesting ingestion start for folder: {folder_path}")
    logger.debug(f"POST {url} with payload: {payload}")

    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"Ingestion started successfully for {folder_path}. Response: {response.status_code}")
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error starting ingestion: {e.response.status_code} - {e.response.text}", exc_info=True)
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error starting ingestion: {e}", exc_info=True)
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.critical(f"Unexpected error in start_ingestion: {e}", exc_info=True)
        return {"error": str(e)}

async def get_ingestion_status(job_id: str):
    """
    Gets the status of an ingestion job.
    
    Args:
        job_id: The ID of the ingestion job.
        
    Returns:
        A dictionary with the job status or an error response.
    """
    client = get_async_client()
    url = f"{INGESTION_ORCHESTRATION_URL}/ingest/status/{job_id}"
    logger.debug(f"Polling ingestion status: GET {url}")
    try:
        response = await client.get(url)
        response.raise_for_status()
        logger.debug(f"Ingestion status for job {job_id}: {response.json()}")
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting ingestion status for job {job_id}: {e.response.status_code} - {e.response.text}", exc_info=True)
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error getting ingestion status for job {job_id}: {e}", exc_info=True)
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.critical(f"Unexpected error in get_ingestion_status: {e}", exc_info=True)
        return {"error": str(e)}

async def search_images_by_text(query: str, top_k: int = 10):
    """
    Searches for images based on a text query via the Ingestion Orchestration service.
    (This endpoint would exist on the Ingestion Orchestration service, which queries Qdrant)
    
    Args:
        query: The text query.
        top_k: The number of results to return.
        
    Returns:
        A list of search results or an error response.
    """
    client = get_async_client()
    try:
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/search/text/", params={"query": query, "top_k": top_k})
        response.raise_for_status()
        return response.json() # Expected: list of results like [{"path": "...", "score": ...}]
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling search service for text query '{query}': {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling search service for text query '{query}': {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error during text search: {e}")
        return {"error": str(e)}

async def search_images_by_image(image_bytes: bytes, top_k: int = 10):
    """
    Searches for images similar to an uploaded image via the Ingestion Orchestration service.
    The service would first get an embedding for the image (potentially by calling the ML service)
    and then query Qdrant.
    
    Args:
        image_bytes: The image file in bytes.
        top_k: The number of results to return.
        
    Returns:
        A list of search results or an error response.
    """
    client = get_async_client()
    try:
        files = {'image_file': ('query_image.jpg', image_bytes)}
        response = await client.post(f"{INGESTION_ORCHESTRATION_URL}/search/image/", files=files, params={"top_k": top_k})
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling search service for image query: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling search service for image query: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error during image search: {e}")
        return {"error": str(e)}

# --- Other potential API calls as needed by the UI ---

async def get_processed_images(page: int = 1, limit: int = 10, sort_by: str = None, sort_order: str = "asc", filters: dict = None):
    """
    Retrieves a paginated list of processed images from the backend.
    Corresponds to GET /images in the backend.
    """
    client = get_async_client()
    params = {
        "page": page,
        "per_page": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "filters": json.dumps(filters) if filters else None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    url = f"{INGESTION_ORCHESTRATION_URL}/images"
    logger.debug(f"Requesting processed images: GET {url} with params: {params}")

    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        logger.debug("Successfully retrieved processed images.")
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting processed images: {e.response.status_code} - {e.response.text}", exc_info=True)
        return {"error": str(e), "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error getting processed images: {e}", exc_info=True)
        return {"error": str(e)}
    except Exception as e:
        logger.critical(f"Unexpected error getting processed images: {e}", exc_info=True)
        return {"error": str(e)}

# --- New Qdrant-backed Endpoints (Sprint 08) ---

async def search_images_vector(embedding: list, filters: dict = None, limit: int = 10, offset: int = 0):
    """
    Searches for images based on a query vector and optional metadata filters using the new Qdrant search endpoint.
    Corresponds to POST /api/v1/search in the backend.
    """
    client = get_async_client()
    payload = {
        "embedding": embedding,
        "filters": filters,
        # limit and offset are passed as query parameters in the backend for this POST endpoint
        # but the backend /search router actually expects them in the body or as query. Let's assume query for now.
    }
    params = {
        "limit": limit,
        "offset": offset
    }
    try:
        response = await client.post(f"{INGESTION_ORCHESTRATION_URL}/search", json=payload, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error vector searching images: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error vector searching images: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error vector searching images: {e}")
        return {"error": str(e)}

async def list_images_qdrant(page: int = 1, per_page: int = 10, filters_json_str: str = None, sort_by: str = None, sort_order: str = "desc"):
    """
    Lists images with pagination, filtering, and sorting from the new Qdrant /images endpoint.
    Corresponds to GET /api/v1/images in the backend.
    """
    client = get_async_client()
    params = {
        "page": page,
        "per_page": per_page,
        "filters": filters_json_str, # Backend expects a JSON string for filters
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    # Remove None params to keep URL clean
    params = {k: v for k, v in params.items() if v is not None}
    try:
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/images", params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error listing images (qdrant): {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error listing images (qdrant): {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error listing images (qdrant): {e}")
        return {"error": str(e)}

async def get_duplicates_qdrant():
    """
    Triggers duplicate image detection process from the new Qdrant /duplicates endpoint.
    Corresponds to POST /api/v1/duplicates in the backend.
    """
    client = get_async_client()
    try:
        # This endpoint might take parameters like threshold in the future, passed in JSON body
        response = await client.post(f"{INGESTION_ORCHESTRATION_URL}/duplicates", json={}) # Empty JSON body for now
        response.raise_for_status()
        return response.json() # Expected: {"status": "acknowledged", "message": "..."}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error triggering duplicate detection: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error triggering duplicate detection: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error triggering duplicate detection: {e}")
        return {"error": str(e)}

async def get_random_image_qdrant():
    """
    Gets a random image from the new Qdrant /random endpoint.
    Corresponds to GET /api/v1/random in the backend.
    """
    client = get_async_client()
    try:
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/random")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting random image: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error getting random image: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error getting random image: {e}")
        return {"error": str(e)}

async def get_all_vectors_for_latent_space():
    """
    Retrieves all vectors (or a representative sample) suitable for latent space visualization.
    This would typically fetch IDs, vectors, and minimal payload (like path, caption).
    Corresponds to a new backend endpoint, e.g., GET /api/v1/vectors/all-for-visualization.
    """
    client = get_async_client()
    try:
        # Adjust endpoint as per your backend implementation
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/vectors/all-for-visualization")
        response.raise_for_status()
        # Expected: {"data": [{"id": "...", "vector": [...], "payload": {"path": "...", "caption": "..."}}, ...]}
        # or simply a list of such items. Adapt based on actual backend response.
        # For latent_space.py, it expects a list of dicts that can be made into a DataFrame
        # with 'vector', 'path', 'caption' columns.
        # Let's assume the backend returns data in a "data" key, which is a list of items.
        # Each item should have 'vector' and 'payload' (with 'path', 'caption').
        # We will transform it slightly here if needed to match latent_space.py expectations more directly.
        
        raw_response_data = response.json()
        # Assuming raw_response_data is like: {"data": [{"id": "id1", "vector": [], "payload": {"path": "/p1", "caption": "c1"}}]}
        # Transform into: [{"vector": [], "path": "/p1", "caption": "c1"}] for easier DataFrame creation
        
        processed_vectors = []
        if "data" in raw_response_data and isinstance(raw_response_data["data"], list):
            for item in raw_response_data["data"]:
                # Ensure 'vector' and 'payload' exist
                if "vector" in item and "payload" in item:
                    entry = {"vector": item["vector"]}
                    entry["path"] = item["payload"].get("path")
                    entry["caption"] = item["payload"].get("caption")
                    # Add other payload fields if needed by latent_space.py visualization
                    entry["id"] = item.get("id") # Keep id if present
                    processed_vectors.append(entry)
                else:
                    logger.warning(f"Skipping item in all_vectors due to missing 'vector' or 'payload': {item.get('id', 'Unknown ID')}")
            return {"vectors": processed_vectors} # latent_space.py expects a dict with a "vectors" key
        else:
            logger.error(f"Unexpected response structure from /vectors/all-for-visualization: {raw_response_data}")
            return {"error": "Invalid data structure from backend", "vectors": []}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting all vectors for latent space: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None, "vectors": []}
    except httpx.RequestError as e:
        logger.error(f"Request error getting all vectors for latent space: {e}")
        return {"error": str(e), "status_code": None, "vectors": []}
    except Exception as e:
        logger.error(f"Unexpected error getting all vectors for latent space: {e}")
        return {"error": str(e), "vectors": []}

# Add more functions here as UI requirements evolve, e.g., for:
# - Getting image metadata
# - Advanced search filters
# - User preferences, etc.

# --- Qdrant Collection Management Endpoints (Sprint 09) ---
async def get_collection_status():
    """
    Checks if a Qdrant collection exists.
    Corresponds to GET /api/v1/collection/status in the backend.
    """
    client = get_async_client()
    url = f"{INGESTION_ORCHESTRATION_URL}/collection/status"
    logger.debug(f"GET {url}")
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting collection status: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error getting collection status: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error getting collection status: {e}")
        return {"error": str(e)}

async def create_collection(directory_path: str):
    """
    Creates a new Qdrant collection from a folder of images.
    Corresponds to POST /api/v1/collection/create in the backend.
    """
    client = get_async_client()
    payload = {"directory_path": directory_path}
    url = f"{INGESTION_ORCHESTRATION_URL}/collection/create"
    logger.info(f"Requesting collection creation for folder: {directory_path}")
    logger.debug(f"POST {url} with payload: {payload}")
    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error creating collection: {e} - Response: {e.response.text}", exc_info=True)
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error creating collection: {e}", exc_info=True)
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error creating collection: {e}", exc_info=True)
        return {"error": str(e)}

async def merge_folder(directory_path: str):
    """
    Merges a new folder of images into the existing Qdrant collection.
    Corresponds to POST /api/v1/ingest/merge in the backend.
    """
    client = get_async_client()
    payload = {"directory_path": directory_path}
    url = f"{INGESTION_ORCHESTRATION_URL}/ingest/merge"
    logger.info(f"Requesting merge for folder: {directory_path}")
    logger.debug(f"POST {url} with payload: {payload}")
    try:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error merging folder: {e} - Response: {e.response.text}", exc_info=True)
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error merging folder: {e}", exc_info=True)
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error merging folder: {e}", exc_info=True)
        return {"error": str(e)}

async def _test_main():
    print("Testing service_api.py (ensure backend services are running)")
    
    if not os.path.exists("test_image.jpg"):
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 100), color = 'red')
            draw = ImageDraw.Draw(img)
            draw.text((10,10), "Test", fill=(255,255,0))
            img.save("test_image.jpg")
            print("Created dummy 'test_image.jpg'.")
        except ImportError:
            print("Pillow not installed, can't create dummy image. Skipping some tests.")
            return
        except Exception as e:
            print(f"Error creating dummy image: {e}")
            return

    if os.path.exists("test_image.jpg"):
        with open("test_image.jpg", "rb") as f:
            test_image_bytes = f.read()

        print("\n--- Testing ML Inference Service ---")
        embedding_response = await get_embedding(test_image_bytes)
        print(f"Get Embedding Response: {embedding_response}")
        
        caption_response = await get_caption(test_image_bytes)
        print(f"Get Caption Response: {caption_response}")

        print("\n--- Testing Ingestion Orchestration Service ---")
        if not os.path.exists("test_images_to_ingest"):
            os.makedirs("test_images_to_ingest")
            if os.path.exists("test_image.jpg"):
                import shutil
                shutil.copy("test_image.jpg", "test_images_to_ingest/test_image_copy.jpg")
            print("Created dummy 'test_images_to_ingest/' directory.")

        # Use absolute path for ingestion to avoid issues with backend's CWD
        ingest_dir_absolute_path = os.path.abspath("test_images_to_ingest")
        ingest_response = await start_ingestion(ingest_dir_absolute_path)
        print(f"Ingest Directory Response: {ingest_response}")
        
        if ingest_response and "job_id" in ingest_response and ingest_response.get("error") is None:
            job_id = ingest_response["job_id"]
            await asyncio.sleep(2)
            status_response = await get_ingestion_status(job_id)
            print(f"Get Ingestion Status Response: {status_response}")
        
        print("\n--- Testing Search (via Ingestion Service) ---")
        text_search_response = await search_images_by_text("test")
        print(f"Text Search Response: {text_search_response}")
        
        image_search_response = await search_images_by_image(test_image_bytes)
        print(f"Image Search Response: {image_search_response}")

        print("\n--- Testing Get Processed Images ---")
        processed_images_response = await get_processed_images(page=1, limit=5)
        print(f"Get Processed Images Response: {processed_images_response}")
    else:
        print("Skipping direct API call tests as 'test_image.jpg' not found.")

async def get_collections():
    """Retrieve list of Qdrant collections from the backend."""
    client = get_async_client()
    response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/collections")
    response.raise_for_status()
    return response.json()

async def select_collection(collection_name: str):
    """Select the active Qdrant collection for future operations."""
    client = get_async_client()
    response = await client.post(
        f"{INGESTION_ORCHESTRATION_URL}/collections/select",
        json={"collection_name": collection_name}
    )
    response.raise_for_status()
    return response.json()

async def clear_collection_cache():
    """Clear the disk cache for the currently active Qdrant collection via the backend."""
    client = get_async_client()
    response = await client.post(
        f"{INGESTION_ORCHESTRATION_URL}/collections/cache/clear"
    )
    response.raise_for_status()
    return response.json()

if __name__ == '__main__':
    asyncio.run(_test_main()) 