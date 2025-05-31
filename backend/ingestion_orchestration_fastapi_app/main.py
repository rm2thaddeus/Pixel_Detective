import sys # Added import
import os # Added import
# Add project root to sys.path to allow importing 'utils'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import FastAPI, HTTPException, APIRouter # Added APIRouter
import httpx
from pydantic import BaseModel
from typing import List, Dict, Any, Tuple, Optional # Added Tuple and Optional
import aiofiles # For async file reading
import base64 # For encoding image data
from qdrant_client import QdrantClient # Qdrant client
from qdrant_client.http import models # Ensures models.PointStruct is valid
from qdrant_client.http.models import Distance, VectorParams # For collection creation
from utils.metadata_extractor import extract_metadata # Import the new extractor
import uuid # Added for generating UUIDs for point_id
import hashlib # Added for image content hashing
import diskcache

import logging

# Configure basic logging - Uvicorn might override this, but good for standalone potential
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="Ingestion Orchestration Service")
# Create a router for API version 1
v1_router = APIRouter(prefix="/api/v1")

ML_INFERENCE_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
ML_INFERENCE_BATCH_SIZE = int(os.environ.get("ML_INFERENCE_BATCH_SIZE", 8)) # New config for batch size
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost") # Assuming Qdrant might run locally or in Docker
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "development test")
# Define standard vector parameters for the collection (e.g., for ViT-B/32 CLIP model)
QDRANT_VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", 512))
QDRANT_DISTANCE_METRIC = Distance[os.environ.get("QDRANT_DISTANCE_METRIC", "Cosine").upper()]

# Global Qdrant client instance
qdrant_client: QdrantClient = None
# Persistent cache for image hashes to embeddings and captions
# Format: { "image_hash_sha256": {"embedding": [...], "caption": "...", "embedding_data": {...}, "caption_data": {...}} }
DISKCACHE_DIR = os.environ.get("DISKCACHE_DIR", "./.diskcache")
image_content_cache = diskcache.Cache(DISKCACHE_DIR)

# --- Helper type for items to send to ML Service Batch Endpoint ---
class MLBatchRequestItem(BaseModel):
    unique_id: str # Typically image_hash
    image_base64: str
    filename: str

# --- Helper function to process a batch with ML Service and update DB/Cache ---
async def process_batch_with_ml_service(
    client: httpx.AsyncClient,
    batch_items_to_ml: List[Tuple[str, str, str, str]], # hash, base64, filename, file_path
    processed_files_details: List[Dict],
    failed_files_details: List[Dict]
):
    if not batch_items_to_ml:
        return

    logger.info(f"Sending batch of {len(batch_items_to_ml)} items to ML Inference Service...")
    ml_request_payload = {
        "images": [
            MLBatchRequestItem(unique_id=item[0], image_base64=item[1], filename=item[2]).dict() 
            for item in batch_items_to_ml
        ]
    }

    try:
        batch_ml_response = await client.post(
            f"{ML_INFERENCE_SERVICE_URL}/api/v1/batch_embed_and_caption",
            json=ml_request_payload,
            timeout=60.0 # Potentially longer timeout for batch processing
        )
        batch_ml_response.raise_for_status()
        ml_results = batch_ml_response.json().get("results", [])
        logger.info(f"Received {len(ml_results)} results from ML batch processing.")

        # Create a dictionary for quick lookup of ML results by unique_id (image_hash)
        ml_results_map = {result["unique_id"]: result for result in ml_results}

        for image_hash, _, filename, file_path in batch_items_to_ml:
            ml_result = ml_results_map.get(image_hash)
            
            if not ml_result or ml_result.get("error"):
                error_detail = ml_result.get("error", "Unknown error from ML service batch response") if ml_result else "No result in ML service batch response"
                logger.error(f"  Error for {filename} (hash: {image_hash}) from ML batch: {error_detail}")
                failed_files_details.append({"file": file_path, "error": error_detail, "details": "ML Batch Processing"})
                continue # Skip to next item in our original batch_items_to_ml

            embedding = ml_result.get("embedding")
            caption = ml_result.get("caption")
            embedding_shape = ml_result.get("embedding_shape")
            model_name_clip = ml_result.get("model_name_clip")
            model_name_blip = ml_result.get("model_name_blip")

            if embedding is None or caption is None:
                logger.error(f"  Missing embedding or caption for {filename} (hash: {image_hash}) in ML batch response.")
                failed_files_details.append({"file": file_path, "error": "Missing embedding or caption in ML batch response", "hash": image_hash})
                continue
            
            # Construct embedding_data and caption_data as they would be from single calls, for cache consistency
            # This might need adjustment based on what /batch_embed_and_caption actually returns per item
            embedding_data_for_cache = {
                "filename": filename,
                "embedding": embedding,
                "embedding_shape": embedding_shape,
                "model_name": model_name_clip, # Assuming these are part of BatchResultItem
                "device_used": ml_result.get("device_used")
            }
            caption_data_for_cache = {
                "filename": filename,
                "caption": caption,
                "model_name": model_name_blip,
                "device_used": ml_result.get("device_used")
            }

            # Store in persistent cache
            image_content_cache[image_hash] = {
                "embedding_data": embedding_data_for_cache,
                "caption_data": caption_data_for_cache
            }
            logger.info(f"  Stored batch-processed embedding and caption for hash {image_hash} in persistent cache.")

            # Proceed with metadata extraction and Qdrant storage for this item
            try:
                logger.info(f"  Extracting metadata for batch-processed {filename}...")
                comprehensive_metadata = extract_metadata(file_path)
                logger.info(f"  Metadata extracted for {filename}: {comprehensive_metadata}")
                
                # Read image_bytes again for original_size_bytes - could optimize this by passing it along
                async with aiofiles.open(file_path, "rb") as f_img_bytes:
                    image_bytes_for_size = await f_img_bytes.read()

                if qdrant_client:
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path)) # Consistent ID generation
                    qdrant_payload = comprehensive_metadata.copy()
                    qdrant_payload["caption"] = caption
                    qdrant_payload["original_size_bytes"] = len(image_bytes_for_size)
                    qdrant_payload["full_path"] = file_path
                    qdrant_payload["ml_embedding_model"] = model_name_clip
                    qdrant_payload["ml_caption_model"] = model_name_blip
                    if "filename" not in qdrant_payload: qdrant_payload["filename"] = filename
                    qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                    logger.info(f"  Upserting batch-processed point to Qdrant: {filename} (ID: {point_id})")
                    qdrant_client.upsert(
                        collection_name=QDRANT_COLLECTION_NAME, wait=True,
                        points=[models.PointStruct(id=point_id, vector=embedding, payload=qdrant_payload)]
                    )
                    logger.info(f"  Successfully stored batch-processed data for {filename} in Qdrant.")
                    processed_files_details.append({
                        "file": file_path, "embedding_info": embedding_shape,
                        "caption": caption, "metadata": comprehensive_metadata, "source": "batch_ml"
                    })
                else:
                    logger.warning(f"  Qdrant client not initialized. Skipping storage for batch-processed {filename}.")
                    failed_files_details.append({"file": file_path, "error": "Qdrant client not initialized (batch)"})
            except Exception as e_inner:
                logger.error(f"  Error processing/storing item {filename} from batch: {e_inner}", exc_info=True)
                failed_files_details.append({"file": file_path, "error": str(e_inner), "details": "Post ML Batch Processing"})

    except httpx.HTTPStatusError as e_http:
        logger.error(f"HTTP error calling ML batch service: {e_http.response.status_code} - {e_http.response.text}")
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service HTTP Error: {e_http.response.status_code}", "details": e_http.response.text})
    except httpx.RequestError as e_req:
        logger.error(f"Request error calling ML batch service: {e_req}")
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service Request Error: {str(e_req)}"})
    except Exception as e_outer:
        logger.error(f"Unexpected error during ML batch processing call: {e_outer}", exc_info=True)
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service Unexpected Error: {str(e_outer)}"})

@app.get("/")
async def root():
    return {"message": "Ingestion Orchestration Service is running"}

@app.on_event("startup")
async def startup_event():
    global qdrant_client
    logger.info("Ingestion Orchestration Service starting up...")
    
    logger.info(f"Expecting ML Inference Service at: {ML_INFERENCE_SERVICE_URL}")
    logger.info(f"Connecting to Qdrant at: {QDRANT_HOST}:{QDRANT_PORT}")
    try:
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=20) # Added timeout
        logger.info(f"Successfully connected to Qdrant instance at {QDRANT_HOST}:{QDRANT_PORT}.")

        # Check if collection exists
        try:
            collection_info = qdrant_client.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' already exists. Details: {collection_info}")
            # Optionally, verify vector_size and distance match QDRANT_VECTOR_SIZE, QDRANT_DISTANCE_METRIC
            # If not, it could be an issue or require re-creation depending on policy.
            # For now, we assume it's compatible if it exists.
        except Exception as e: # Broad exception, specific Qdrant client error might be better
            if "404" in str(e) or "not found" in str(e).lower(): # Heuristic for collection not found
                logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' not found. Attempting to create it...")
                try:
                    qdrant_client.create_collection(
                        collection_name=QDRANT_COLLECTION_NAME,
                        vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=QDRANT_DISTANCE_METRIC)
                    )
                    logger.info(f"Successfully created Qdrant collection '{QDRANT_COLLECTION_NAME}' with vector size {QDRANT_VECTOR_SIZE} and distance {QDRANT_DISTANCE_METRIC.value}")
                except Exception as create_e:
                    logger.error(f"Failed to create Qdrant collection '{QDRANT_COLLECTION_NAME}': {create_e}", exc_info=True)
                    # Decide if service should fail if collection can't be ensured
            else:
                logger.error(f"Error checking Qdrant collection '{QDRANT_COLLECTION_NAME}': {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Failed to connect to Qdrant or ensure collection: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Ingestion Orchestration Service shutting down...")

# Placeholder for actual ingestion endpoint
class IngestRequest(BaseModel):
    directory_path: str

@v1_router.post("/ingest/") # Changed path from /ingest_directory and added to v1_router
async def ingest_directory_v1(request: IngestRequest): # Renamed function for clarity
    """
    Receives a directory path, processes files, calls ML inference, 
    and stores results in Qdrant.
    """
    logger.info(f"APIv1: Received request to ingest directory: {request.directory_path}")
    
    processed_files_details = []
    failed_files_details = []
    current_batch_to_ml_service: List[Tuple[str, str, str, str]] = [] # hash, base64, filename, file_path

    if not os.path.isdir(request.directory_path):
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.directory_path}")

    all_files = os.listdir(request.directory_path)
    total_files_to_scan = len(all_files)
    
    async with httpx.AsyncClient() as client: # Default timeout for individual calls, batch has its own
        for i, filename in enumerate(all_files):
            file_path = os.path.join(request.directory_path, filename)
            if os.path.isfile(file_path):
                # Check for image file extensions
                if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.dng')):
                    logger.info(f"Skipping non-image file: {file_path}")
                    failed_files_details.append({"file": file_path, "error": "Skipped non-image file"})
                    continue

                logger.info(f"Processing file: {file_path} ({i+1}/{total_files_to_scan})")
                try:
                    async with aiofiles.open(file_path, "rb") as f:
                        image_bytes = await f.read()
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    image_hash = hashlib.sha256(image_bytes).hexdigest()
                    logger.info(f"  Image hash for {filename}: {image_hash}")

                    cached_data = image_content_cache.get(image_hash)

                    if cached_data:
                        logger.info(f"  Cache hit for {filename} (hash: {image_hash}). Using cached embedding and caption.")
                        embedding_data = cached_data["embedding_data"]
                        caption_data = cached_data["caption_data"]
                        # Metadata extraction and Qdrant storage for cached items (similar to single item processing)
                        logger.info(f"  Extracting metadata for cached {filename}...")
                        comprehensive_metadata = extract_metadata(file_path)
                        if qdrant_client:
                            vector = embedding_data.get("embedding")
                            caption = caption_data.get("caption")
                            if vector is None:
                                raise ValueError("Cached embedding not found")

                            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
                            qdrant_payload = comprehensive_metadata.copy()
                            qdrant_payload["caption"] = caption
                            qdrant_payload["original_size_bytes"] = len(image_bytes)
                            qdrant_payload["full_path"] = file_path
                            qdrant_payload["ml_embedding_model"] = embedding_data.get("model_name", os.environ.get("CLIP_MODEL_NAME", "ViT-B/32"))
                            qdrant_payload["ml_caption_model"] = caption_data.get("model_name", os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large"))
                            if "filename" not in qdrant_payload: qdrant_payload["filename"] = filename
                            qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                            qdrant_client.upsert(
                                collection_name=QDRANT_COLLECTION_NAME, wait=True,
                                points=[models.PointStruct(id=point_id, vector=vector, payload=qdrant_payload)]
                            )
                            logger.info(f"  Successfully stored cached data for {filename} in Qdrant.")
                            processed_files_details.append({
                                "file": file_path, "embedding_info": embedding_data.get("embedding_shape", "N/A"),
                                "caption": caption, "metadata": comprehensive_metadata, "source": "cache"
                            })
                        else:
                            failed_files_details.append({"file": file_path, "error": "Qdrant client not initialized (cache)"})
                    else:
                        logger.info(f"  Cache miss for {filename} (hash: {image_hash}). Adding to ML batch queue.")
                        current_batch_to_ml_service.append((image_hash, image_base64, filename, file_path))

                        if len(current_batch_to_ml_service) >= ML_INFERENCE_BATCH_SIZE:
                            logger.info(f"ML batch size reached ({ML_INFERENCE_BATCH_SIZE}). Processing batch...")
                            await process_batch_with_ml_service(client, current_batch_to_ml_service, processed_files_details, failed_files_details)
                            current_batch_to_ml_service.clear()
                
                except Exception as e: # Catch errors for individual file processing before batching
                    logger.error(f"  An unexpected error occurred while preparing {filename} for batching or processing cache: {e}", exc_info=True)
                    failed_files_details.append({"file": file_path, "error": str(e), "details": "Pre-batch/Cache Processing"})
            else:
                logger.info(f"Skipping non-file item: {file_path} ({i+1}/{total_files_to_scan})")

        # Process any remaining items in the batch
        if current_batch_to_ml_service:
            logger.info(f"Processing remaining {len(current_batch_to_ml_service)} items in ML batch...")
            await process_batch_with_ml_service(client, current_batch_to_ml_service, processed_files_details, failed_files_details)
            current_batch_to_ml_service.clear()

    logger.info(f"Ingestion process completed for {request.directory_path}. Processed: {len(processed_files_details)}, Failed: {len(failed_files_details)}")
    return {
        "message": f"Ingestion process completed for {request.directory_path}.", 
        "directory": request.directory_path,
        "processed_count": len(processed_files_details),
        "failed_count": len(failed_files_details),
        "processed_details": processed_files_details,
        "failed_details": failed_files_details
    }

# --- Placeholder Endpoints for API v1 ---

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str

@v1_router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
async def get_ingestion_status_v1(job_id: str):
    logger.info(f"APIv1: Received request for ingestion status for job_id: {job_id}")
    # Placeholder logic: In a real scenario, you'd look up the job status
    return JobStatusResponse(
        job_id=job_id,
        status="processing", # Or "completed", "failed", "pending"
        progress=50.0,      # Example progress
        message=f"Status for job {job_id}: Placeholder - In progress"
    )

class SearchTextRequest(BaseModel): # Although GET, using BaseModel for clarity if params grow
    query: str
    top_k: int = 10

class SearchResultItem(BaseModel):
    path: str
    score: float
    caption: Optional[str] = None 

@v1_router.get("/search/text/", response_model=List[SearchResultItem])
async def search_images_by_text_v1(query: str, top_k: int = 10):
    logger.info(f"APIv1: Received text search request: query='{query}', top_k={top_k}")
    # Placeholder
    return [
        SearchResultItem(path="/example/image1.jpg", score=0.9, caption="Example image 1"),
        SearchResultItem(path="/example/image2.png", score=0.85, caption="Example image 2")
    ]

# For POST /search/image/, we'd typically expect a file upload.
# FastAPI handles this with File(...). For simplicity as a placeholder:
class ImageSearchResponseItem(BaseModel):
    path: str
    score: float

@v1_router.post("/search/image/", response_model=List[ImageSearchResponseItem])
async def search_images_by_image_v1(top_k: int = 10): # Actual implementation would take image_file: UploadFile
    logger.info(f"APIv1: Received image search request: top_k={top_k}. (File upload not processed in placeholder)")
    # Placeholder
    return [
        ImageSearchResponseItem(path="/similar/imageA.jpg", score=0.92),
        ImageSearchResponseItem(path="/similar/imageB.png", score=0.88)
    ]

class ProcessedImageItem(BaseModel):
    id: str # Or path, depending on what uniquely identifies an image
    path: str
    thumbnail_url: Optional[str] = None # Example field
    caption: Optional[str] = None

class GetProcessedImagesResponse(BaseModel):
    images: List[ProcessedImageItem]
    total: int
    page: int
    limit: int

@v1_router.get("/images/", response_model=GetProcessedImagesResponse)
async def get_processed_images_v1(page: int = 1, limit: int = 20):
    logger.info(f"APIv1: Received request for processed images: page={page}, limit={limit}")
    # Placeholder
    example_images = [
        ProcessedImageItem(id="img1", path="/processed/img1.jpg", caption="Processed image 1"),
        ProcessedImageItem(id="img2", path="/processed/img2.jpg", caption="Processed image 2")
    ]
    return GetProcessedImagesResponse(
        images=example_images[:limit],
        total=len(example_images),
        page=page,
        limit=limit
    )

# Include the v1 router in the main app
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 