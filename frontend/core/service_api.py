"""
Service API layer for the Frontend.

This module centralizes all HTTP calls from the Streamlit UI to the backend FastAPI services
(ML Inference and Ingestion Orchestration). It uses the 'requests' library for making
synchronous HTTP calls. Backend service URLs should be configurable, typically via
environment variables or a dedicated frontend configuration mechanism.
"""
import requests
import os
import logging

logger = logging.getLogger(__name__)

# Configuration for backend services - these should ideally come from environment variables
# For example: os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
ML_INFERENCE_URL = os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001/api/v1")
INGESTION_ORCHESTRATION_URL = os.getenv("INGESTION_ORCHESTRATION_SERVICE_URL", "http://localhost:8000/api/v1") # Assuming 8000 for ingestion

# --- ML Inference Service Endpoints ---

def get_embedding(image_bytes: bytes, model_name: str = "clip"):
    """
    Gets an embedding for a given image using the ML Inference service.
    
    Args:
        image_bytes: The image file in bytes.
        model_name: The name of the model to use (e.g., 'clip', 'blip').
                   This might be determined by the backend or configurable.
                   
    Returns:
        A dictionary containing the embedding or an error response.
    """
    try:
        files = {'image_file': ('image.jpg', image_bytes)} # Backend might expect a specific filename or type
        response = requests.post(f"{ML_INFERENCE_URL}/embed/", files=files, params={"model_name": model_name})
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling ML inference service for embedding: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error getting embedding: {e}")
        return {"error": str(e)}

def get_caption(image_bytes: bytes, model_name: str = "blip"):
    """
    Gets a caption for a given image using the ML Inference service.
    
    Args:
        image_bytes: The image file in bytes.
        model_name: The name of the captioning model to use.
        
    Returns:
        A dictionary containing the caption or an error response.
    """
    try:
        files = {'image_file': ('image.jpg', image_bytes)}
        response = requests.post(f"{ML_INFERENCE_URL}/caption/", files=files, params={"model_name": model_name})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling ML inference service for captioning: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error getting caption: {e}")
        return {"error": str(e)}

# --- Ingestion Orchestration Service Endpoints ---

def ingest_directory(path: str):
    """
    Triggers directory ingestion via the Ingestion Orchestration service.
    
    Args:
        path: The directory path to ingest.
        
    Returns:
        A dictionary with the job ID and status or an error response.
    """
    try:
        response = requests.post(f"{INGESTION_ORCHESTRATION_URL}/ingest/", json={"directory_path": path})
        response.raise_for_status()
        return response.json() # Expected: {"job_id": "some_id", "status": "started", "message": "..."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling ingestion service to ingest directory: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error ingesting directory: {e}")
        return {"error": str(e)}

def get_ingestion_status(job_id: str):
    """
    Gets the status of an ingestion job.
    
    Args:
        job_id: The ID of the ingestion job.
        
    Returns:
        A dictionary with the job status or an error response.
    """
    try:
        response = requests.get(f"{INGESTION_ORCHESTRATION_URL}/ingest/status/{job_id}")
        response.raise_for_status()
        return response.json() # Expected: {"job_id": job_id, "status": "processing/completed/failed", "progress": ..., "details": ...}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting ingestion status for job {job_id}: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error getting ingestion status: {e}")
        return {"error": str(e)}

def search_images_by_text(query: str, top_k: int = 10):
    """
    Searches for images based on a text query via the Ingestion Orchestration service.
    (This endpoint would exist on the Ingestion Orchestration service, which queries Qdrant)
    
    Args:
        query: The text query.
        top_k: The number of results to return.
        
    Returns:
        A list of search results or an error response.
    """
    try:
        response = requests.get(f"{INGESTION_ORCHESTRATION_URL}/search/text/", params={"query": query, "top_k": top_k})
        response.raise_for_status()
        return response.json() # Expected: list of results like [{"path": "...", "score": ...}]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling search service for text query '{query}': {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error during text search: {e}")
        return {"error": str(e)}

def search_images_by_image(image_bytes: bytes, top_k: int = 10):
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
    try:
        files = {'image_file': ('query_image.jpg', image_bytes)}
        response = requests.post(f"{INGESTION_ORCHESTRATION_URL}/search/image/", files=files, params={"top_k": top_k})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling search service for image query: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None}
    except Exception as e:
        logger.error(f"Unexpected error during image search: {e}")
        return {"error": str(e)}

# --- Other potential API calls as needed by the UI ---

def get_processed_images(page: int = 1, limit: int = 20):
    """
    Retrieves a paginated list of processed images from the Ingestion Orchestration service.
    (As per UI-07-01 in TASK_BREAKDOWN.md)
    """
    try:
        response = requests.get(f"{INGESTION_ORCHESTRATION_URL}/images/", params={"page": page, "limit": limit})
        response.raise_for_status()
        return response.json() # Expected: {"images": [...], "total": ..., "page": ..., "limit": ...}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting processed images: {e}")
        return {"error": str(e), "status_code": e.response.status_code if e.response else None, "images": []}
    except Exception as e:
        logger.error(f"Unexpected error getting processed images: {e}")
        return {"error": str(e), "images": []}

# Add more functions here as UI requirements evolve, e.g., for:
# - Getting image metadata
# - Advanced search filters
# - User preferences, etc.

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    print("Testing service_api.py (ensure backend services are running)")
    
    # Note: For these tests to work, you need:
    # 1. Backend services (ML Inference, Ingestion Orchestration) running.
    # 2. An image file named 'test_image.jpg' in the same directory as this script.
    # 3. A directory named 'test_images_to_ingest/' for the ingestion test.

    # Create a dummy image for testing if it doesn't exist
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
        except Exception as e:
            print(f"Error creating dummy image: {e}")

    if os.path.exists("test_image.jpg"):
        with open("test_image.jpg", "rb") as f:
            test_image_bytes = f.read()

        print("\n--- Testing ML Inference Service ---")
        embedding_response = get_embedding(test_image_bytes)
        print(f"Get Embedding Response: {embedding_response}")
        
        caption_response = get_caption(test_image_bytes)
        print(f"Get Caption Response: {caption_response}")

        print("\n--- Testing Ingestion Orchestration Service ---")
        # Create a dummy directory for ingestion test
        if not os.path.exists("test_images_to_ingest"):
            os.makedirs("test_images_to_ingest")
            # Optionally, put a copy of the test image in it
            if os.path.exists("test_image.jpg"):
                import shutil
                shutil.copy("test_image.jpg", "test_images_to_ingest/test_image_copy.jpg")
            print("Created dummy 'test_images_to_ingest/' directory.")

        ingest_response = ingest_directory("test_images_to_ingest")
        print(f"Ingest Directory Response: {ingest_response}")
        
        if ingest_response and "job_id" in ingest_response:
            job_id = ingest_response["job_id"]
            import time
            time.sleep(2) # Give some time for processing to start
            status_response = get_ingestion_status(job_id)
            print(f"Get Ingestion Status Response: {status_response}")
        
        print("\n--- Testing Search (via Ingestion Service) ---")
        text_search_response = search_images_by_text("test")
        print(f"Text Search Response: {text_search_response}")
        
        image_search_response = search_images_by_image(test_image_bytes)
        print(f"Image Search Response: {image_search_response}")

        print("\n--- Testing Get Processed Images ---")
        processed_images_response = get_processed_images(page=1, limit=5)
        print(f"Get Processed Images Response: {processed_images_response}")
    else:
        print("Skipping direct API call tests as 'test_image.jpg' not found.") 