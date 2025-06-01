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

logger = logging.getLogger(__name__)

# Configuration for backend services - these should ideally come from environment variables
# For example: os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
ML_INFERENCE_URL = os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
INGESTION_ORCHESTRATION_URL = os.getenv("INGESTION_ORCHESTRATION_SERVICE_URL", "http://localhost:8002/api/v1") # Assuming 8002 for ingestion

# Cached HTTPX client
@st.cache_resource
def get_async_client():
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

# --- Ingestion Orchestration Service Endpoints ---

async def ingest_directory(path: str):
    """
    Triggers directory ingestion via the Ingestion Orchestration service.
    
    Args:
        path: The directory path to ingest.
        
    Returns:
        A dictionary with the job ID and status or an error response.
    """
    client = get_async_client()
    try:
        response = await client.post(f"{INGESTION_ORCHESTRATION_URL}/ingest/", json={"directory_path": path})
        response.raise_for_status()
        return response.json() # Expected: {"job_id": "some_id", "status": "started", "message": "..."}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling ingestion service to ingest directory: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error calling ingestion service to ingest directory: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error ingesting directory: {e}")
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
    try:
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/ingest/status/{job_id}")
        response.raise_for_status()
        return response.json() # Expected: {"job_id": job_id, "status": "processing/completed/failed", "progress": ..., "details": ...}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting ingestion status for job {job_id}: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None}
    except httpx.RequestError as e:
        logger.error(f"Request error getting ingestion status for job {job_id}: {e}")
        return {"error": str(e), "status_code": None}
    except Exception as e:
        logger.error(f"Unexpected error getting ingestion status: {e}")
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

async def get_processed_images(page: int = 1, limit: int = 20):
    """
    Retrieves a paginated list of processed images from the Ingestion Orchestration service.
    (As per UI-07-01 in TASK_BREAKDOWN.md)
    """
    client = get_async_client()
    try:
        response = await client.get(f"{INGESTION_ORCHESTRATION_URL}/images/", params={"page": page, "limit": limit})
        response.raise_for_status()
        return response.json() # Expected: {"images": [...], "total": ..., "page": ..., "limit": ...}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error getting processed images: {e} - Response: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.json() if e.response.content else None, "images": []}
    except httpx.RequestError as e:
        logger.error(f"Request error getting processed images: {e}")
        return {"error": str(e), "status_code": None, "images": []}
    except Exception as e:
        logger.error(f"Unexpected error getting processed images: {e}")
        return {"error": str(e), "images": []}

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

# Add more functions here as UI requirements evolve, e.g., for:
# - Getting image metadata
# - Advanced search filters
# - User preferences, etc.

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
        ingest_response = await ingest_directory(ingest_dir_absolute_path)
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

if __name__ == '__main__':
    asyncio.run(_test_main()) 