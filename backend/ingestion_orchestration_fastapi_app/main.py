import sys # Added import
import os # Added import
# Add project root to sys.path to allow importing 'utils'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, BackgroundTasks # Added BackgroundTasks
from fastapi.responses import JSONResponse # Added JSONResponse
from fastapi.exceptions import RequestValidationError # Added RequestValidationError
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
import rawpy # Decode DNG upstream
from PIL import Image # For DNG->RGB conversion
import io # For encoding PIL images to bytes
import diskcache
import time # For logging timestamps
import asyncio # Added for sleep in background task

import logging

# Configure basic logging - Uvicorn might override this, but good for standalone potential
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# Import new routers
from .routers import search as search_router
from .routers import images as images_router
from .routers import duplicates as duplicates_router
from .routers import random as random_router
from .routers.duplicates import on_shutdown as duplicates_on_shutdown # Import shutdown handler
from .dependencies import get_qdrant_dependency

app = FastAPI(title="Ingestion Orchestration Service")
# Create a router for API version 1
v1_router = APIRouter(prefix="/api/v1")

ML_INFERENCE_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
ML_INFERENCE_BATCH_SIZE = int(os.environ.get("ML_INFERENCE_BATCH_SIZE", 8)) # New config for batch size
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost") # Assuming Qdrant might run locally or in Docker
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "development_test") # Corrected default
active_collection_name = QDRANT_COLLECTION_NAME  # Global active collection that can be changed via API
# Define standard vector parameters for the collection (e.g., for ViT-B/32 CLIP model)
QDRANT_VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", 512))
QDRANT_DISTANCE_METRIC = Distance[os.environ.get("QDRANT_DISTANCE_METRIC", "Cosine").upper()]
QDRANT_UPSERT_BATCH_SIZE = int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", 32))

# Global Qdrant client instance
qdrant_client_global: Optional[QdrantClient] = None
# Persistent cache for image hashes to embeddings and captions
DISKCACHE_DIR = os.environ.get("DISKCACHE_DIR", "./.diskcache")
image_content_cache = diskcache.Cache(DISKCACHE_DIR)

# In-memory job status database
# Format: { "job_id": {"status": "pending/processing/completed/failed", "progress": 0.0-100.0, "logs": ["log message1", ...], "result": {}}}
job_status_db: Dict[str, Dict[str, Any]] = {}

def log_to_job(job_id: str, message: str, level: str = "INFO"):
    """Helper to add a log message to a specific job's log list."""
    if job_id in job_status_db:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        job_status_db[job_id]["logs"].append(log_entry)
        # Also log to main logger for system-wide visibility
        if level.upper() == "ERROR":
            logger.error(f"Job {job_id}: {message}")
        elif level.upper() == "WARNING":
            logger.warning(f"Job {job_id}: {message}")
        else:
            logger.info(f"Job {job_id}: {message}")

# --- Helper type for items to send to ML Service Batch Endpoint ---
class MLBatchRequestItem(BaseModel):
    unique_id: str # Typically image_hash
    image_base64: str
    filename: str

# --- Internal async helper to upsert a list of points to Qdrant without
# blocking the main event loop ---
async def _upsert_points(q_client: QdrantClient, collection: str, points: List[models.PointStruct]):
    if not points:
        return
    await asyncio.to_thread(
        q_client.upsert,
        collection_name=collection,
        wait=True,
        points=points,
    )

# --- Helper function to process a batch with ML Service and update DB/Cache ---
async def process_batch_with_ml_service(
    client: httpx.AsyncClient,
    batch_items_to_ml: List[Tuple[str, str, str, str]], # hash, base64, filename, file_path
    processed_files_details: List[Dict],
    failed_files_details: List[Dict],
    job_id: str, # Added job_id for logging
    qdrant_conn: QdrantClient, # Pass Qdrant client
    collection_name: str, # Pass collection name
    ml_service_url: str # Pass ML service URL
):
    if not batch_items_to_ml:
        return

    log_to_job(job_id, f"Sending batch of {len(batch_items_to_ml)} items to ML Inference Service...")
    # Prepare images, decoding DNG locally and converting to PNG where needed
    images_payload = []
    for image_hash, image_b64, filename, file_path in batch_items_to_ml:
        # If raw DNG file, decode and re-encode as PNG
        if file_path.lower().endswith('.dng'):
            try:
                with rawpy.imread(file_path) as raw:
                    rgb = raw.postprocess()
                img = Image.fromarray(rgb).convert('RGB')
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                new_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            except Exception as e:
                log_to_job(job_id, f"Error decoding DNG {filename} upstream: {e}", level="ERROR")
                # Fall back to original bytes
                new_b64 = image_b64
        else:
            new_b64 = image_b64
        images_payload.append(
            MLBatchRequestItem(unique_id=image_hash, image_base64=new_b64, filename=filename).dict()
        )
    ml_request_payload = {"images": images_payload}

    try:
        batch_ml_response = await client.post(
            f"{ml_service_url}/api/v1/batch_embed_and_caption",
            json=ml_request_payload,
            timeout=60.0 # Potentially longer timeout for batch processing
        )
        batch_ml_response.raise_for_status()
        ml_results = batch_ml_response.json().get("results", [])
        log_to_job(job_id, f"Received {len(ml_results)} results from ML batch processing.")

        ml_results_map = {result["unique_id"]: result for result in ml_results}

        qdrant_points: List[models.PointStruct] = []
        for image_hash, _, filename, file_path in batch_items_to_ml:
            ml_result = ml_results_map.get(image_hash)

            if not ml_result or ml_result.get("error"):
                error_detail = ml_result.get("error", "Unknown error from ML service batch response") if ml_result else "No result in ML service batch response"
                log_to_job(job_id, f"Error for {filename} (hash: {image_hash}) from ML batch: {error_detail}", level="ERROR")
                failed_files_details.append({"file": file_path, "error": error_detail, "details": "ML Batch Processing"})
                continue

            embedding = ml_result.get("embedding")
            caption = ml_result.get("caption")
            embedding_shape = ml_result.get("embedding_shape")
            model_name_clip = ml_result.get("model_name_clip")
            model_name_blip = ml_result.get("model_name_blip")

            if embedding is None or caption is None:
                log_to_job(job_id, f"Missing embedding or caption for {filename} (hash: {image_hash}) in ML batch response.", level="ERROR")
                failed_files_details.append({"file": file_path, "error": "Missing embedding or caption in ML batch response", "hash": image_hash})
                continue

            embedding_data_for_cache = {
                "filename": filename, "embedding": embedding, "embedding_shape": embedding_shape,
                "model_name": model_name_clip, "device_used": ml_result.get("device_used")
            }
            caption_data_for_cache = {
                "filename": filename, "caption": caption, "model_name": model_name_blip,
                "device_used": ml_result.get("device_used")
            }
            image_content_cache[image_hash] = {
                "embedding_data": embedding_data_for_cache, "caption_data": caption_data_for_cache
            }
            log_to_job(job_id, f"Stored batch-processed embedding and caption for hash {image_hash} in persistent cache.")

            try:
                log_to_job(job_id, f"Extracting metadata for batch-processed {filename}...")
                comprehensive_metadata = extract_metadata(file_path)
                log_to_job(job_id, f"Metadata extracted for {filename}: {comprehensive_metadata}")

                async with aiofiles.open(file_path, "rb") as f_img_bytes:
                    image_bytes_for_size = await f_img_bytes.read()

                if qdrant_conn:
                    point_id_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
                    qdrant_payload = comprehensive_metadata.copy()
                    qdrant_payload.update({
                        "caption": caption, "original_size_bytes": len(image_bytes_for_size),
                        "full_path": file_path, "ml_embedding_model": model_name_clip,
                        "ml_caption_model": model_name_blip,
                        "filename": qdrant_payload.get("filename", filename)
                    })
                    qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                    log_to_job(job_id, f"Queueing point for Qdrant upsert: {filename} (ID: {point_id_str})")
                    qdrant_points.append(
                        models.PointStruct(id=point_id_str, vector=embedding, payload=qdrant_payload)
                    )
                    processed_files_details.append({
                        "file": file_path, "embedding_info": embedding_shape, "caption": caption,
                        "metadata": comprehensive_metadata, "source": "batch_ml"
                    })
                else:
                    log_to_job(job_id, f"Qdrant client not initialized. Skipping storage for batch-processed {filename}.", level="WARNING")
                    failed_files_details.append({"file": file_path, "error": "Qdrant client not initialized (batch)"})
            except Exception as e_inner:
                log_to_job(job_id, f"Error processing/storing item {filename} from batch: {e_inner}", level="ERROR")
                failed_files_details.append({"file": file_path, "error": str(e_inner), "details": "Post ML Batch Processing"})

        if qdrant_points:
            await _upsert_points(qdrant_conn, collection_name, qdrant_points)
            log_to_job(job_id, f"Upserted {len(qdrant_points)} points to Qdrant in bulk")
    except httpx.HTTPStatusError as e_http:
        log_to_job(job_id, f"HTTP error calling ML batch service: {e_http.response.status_code} - {e_http.response.text}", level="ERROR")
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service HTTP Error: {e_http.response.status_code}", "details": e_http.response.text})
    except httpx.RequestError as e_req:
        log_to_job(job_id, f"Request error calling ML batch service: {e_req}", level="ERROR")
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service Request Error: {str(e_req)}"})
    except Exception as e_outer:
        log_to_job(job_id, f"Unexpected error during ML batch processing call: {e_outer}", level="ERROR")
        for _, _, filename, file_path in batch_items_to_ml:
            failed_files_details.append({"file": file_path, "error": f"ML Batch Service Unexpected Error: {str(e_outer)}"})

# --- Worker function for background ingestion ---
async def _run_ingestion_task(
    directory_path: str,
    job_id: str,
    qdrant_conn_bg: QdrantClient,
    ml_service_url_bg: str,
    ml_batch_size_bg: int,
    disk_cache_bg: diskcache.Cache,
    collection_name_bg: str
):
    log_to_job(job_id, f"Background ingestion task started for directory: {directory_path}")
    job_status_db[job_id]["status"] = "processing"
    processed_files_details = []
    failed_files_details = []
    current_batch_to_ml_service: List[Tuple[str, str, str, str]] = []
    qdrant_points_batch: List[models.PointStruct] = []

    try:
        if not os.path.isdir(directory_path):
            log_to_job(job_id, f"Directory not found: {directory_path}", level="ERROR")
            job_status_db[job_id]["status"] = "failed"
            job_status_db[job_id]["result"] = {"error": f"Directory not found: {directory_path}"}
            return

        all_files = os.listdir(directory_path)
        total_files_to_scan = len(all_files)
        job_status_db[job_id]["progressMax"] = total_files_to_scan # Store max for progress calculation
        files_processed_count = 0

        log_to_job(job_id, f"Scanning {total_files_to_scan} potential files in {directory_path}")

        async with httpx.AsyncClient() as client:
            for i, filename in enumerate(all_files):
                files_processed_count +=1
                job_status_db[job_id]["progress"] = (files_processed_count / total_files_to_scan) * 100 if total_files_to_scan > 0 else 0

                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path):
                    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.dng')):
                        log_to_job(job_id, f"Skipping non-image file: {file_path}")
                        failed_files_details.append({"file": file_path, "error": "Skipped non-image file"})
                        continue

                    log_to_job(job_id, f"Processing file: {file_path} ({i+1}/{total_files_to_scan})")
                    try:
                        async with aiofiles.open(file_path, "rb") as f:
                            image_bytes = await f.read()
                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                        image_hash = hashlib.sha256(image_bytes).hexdigest()
                        log_to_job(job_id, f"Image hash for {filename}: {image_hash}")

                        cached_data = disk_cache_bg.get(image_hash)

                        if cached_data:
                            log_to_job(job_id, f"Cache hit for {filename} (hash: {image_hash}). Using cached embedding and caption.")
                            embedding_data = cached_data["embedding_data"]
                            caption_data = cached_data["caption_data"]
                            log_to_job(job_id, f"Extracting metadata for cached {filename}...")
                            comprehensive_metadata = extract_metadata(file_path)
                            if qdrant_conn_bg:
                                vector = embedding_data.get("embedding")
                                caption = caption_data.get("caption")
                                if vector is None:
                                    raise ValueError("Cached embedding not found")

                                point_id_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
                                qdrant_payload = comprehensive_metadata.copy()
                                qdrant_payload.update({
                                    "caption": caption, "original_size_bytes": len(image_bytes),
                                    "full_path": file_path,
                                    "ml_embedding_model": embedding_data.get("model_name", os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")),
                                    "ml_caption_model": caption_data.get("model_name", os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")),
                                    "filename": qdrant_payload.get("filename", filename)
                                })
                                qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                                qdrant_points_batch.append(
                                    models.PointStruct(id=point_id_str, vector=vector, payload=qdrant_payload)
                                )
                                if len(qdrant_points_batch) >= QDRANT_UPSERT_BATCH_SIZE:
                                    await _upsert_points(qdrant_conn_bg, collection_name_bg, qdrant_points_batch)
                                    log_to_job(job_id, f"Bulk upserted {len(qdrant_points_batch)} cached points")
                                    qdrant_points_batch.clear()
                                log_to_job(job_id, f"Queued cached data for {filename} for Qdrant upsert.")
                                processed_files_details.append({
                                    "file": file_path, "embedding_info": embedding_data.get("embedding_shape", "N/A"),
                                    "caption": caption, "metadata": comprehensive_metadata, "source": "cache"
                                })
                            else:
                                log_to_job(job_id, "Qdrant client not initialized (cache)", level="WARNING")
                                failed_files_details.append({"file": file_path, "error": "Qdrant client not initialized (cache)"})
                        else:
                            log_to_job(job_id, f"Cache miss for {filename} (hash: {image_hash}). Adding to ML batch queue.")
                            current_batch_to_ml_service.append((image_hash, image_base64, filename, file_path))

                            if len(current_batch_to_ml_service) >= ml_batch_size_bg:
                                log_to_job(job_id, f"ML batch size reached ({ml_batch_size_bg}). Processing batch...")
                                await process_batch_with_ml_service(client, current_batch_to_ml_service, processed_files_details, failed_files_details, job_id, qdrant_conn_bg, collection_name_bg, ml_service_url_bg)
                                current_batch_to_ml_service.clear()
                    except Exception as e:
                        log_to_job(job_id, f"An unexpected error occurred while preparing {filename} for batching or processing cache: {e}", level="ERROR")
                        failed_files_details.append({"file": file_path, "error": str(e), "details": "Pre-batch/Cache Processing"})
                else:
                    log_to_job(job_id, f"Skipping non-file item: {file_path} ({i+1}/{total_files_to_scan})")
                # Brief sleep to allow other tasks, if any, and to make progress updates more granular in UI
                await asyncio.sleep(0.01)


            if current_batch_to_ml_service: # Process any remaining items
                log_to_job(job_id, f"Processing remaining {len(current_batch_to_ml_service)} items in ML batch...")
                await process_batch_with_ml_service(client, current_batch_to_ml_service, processed_files_details, failed_files_details, job_id, qdrant_conn_bg, collection_name_bg, ml_service_url_bg)
                current_batch_to_ml_service.clear()

        if qdrant_points_batch:
            await _upsert_points(qdrant_conn_bg, collection_name_bg, qdrant_points_batch)
            log_to_job(job_id, f"Bulk upserted {len(qdrant_points_batch)} cached points at end")
            qdrant_points_batch.clear()

        job_status_db[job_id]["status"] = "completed"
        job_status_db[job_id]["progress"] = 100.0
        final_message = f"Ingestion process completed for {directory_path}. Processed: {len(processed_files_details)}, Failed: {len(failed_files_details)}"
        log_to_job(job_id, final_message)
        job_status_db[job_id]["result"] = {
            "message": final_message,
            "directory": directory_path,
            "processed_count": len(processed_files_details),
            "failed_count": len(failed_files_details),
            "processed_details": processed_files_details, # Optional: could be large
            "failed_details": failed_files_details      # Optional: could be large
        }

    except Exception as e:
        error_message = f"Critical error in ingestion task for job {job_id}, directory {directory_path}: {e}"
        log_to_job(job_id, error_message, level="CRITICAL") # Use a higher level if defined, or ERROR
        logger.exception(error_message) # Log full traceback to main logger
        job_status_db[job_id]["status"] = "failed"
        job_status_db[job_id]["result"] = {"error": str(e), "message": error_message}
        job_status_db[job_id]["progress"] = job_status_db[job_id].get("progress", 0.0) # Keep last known progress

@app.get("/")
async def root():
    return {"message": "Ingestion Orchestration Service is running"}

@app.on_event("startup")
async def startup_event():
    global qdrant_client_global
    logger.info("Ingestion Orchestration Service starting up...")

    logger.info(f"Expecting ML Inference Service at: {ML_INFERENCE_SERVICE_URL}")
    logger.info(f"Connecting to Qdrant at: {QDRANT_HOST}:{QDRANT_PORT}")
    try:
        qdrant_client_instance = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=20)
        # Attach the Qdrant client to FastAPI app state for dependency injection without circular imports
        # However, for background tasks, it's often simpler to pass globals if they are configured at startup
        # and their state doesn't change per request in a way that background tasks would misuse.
        # For this refactor, _run_ingestion_task will receive qdrant_client as an argument.
        app.state.qdrant_client = qdrant_client_instance # For router dependencies
        globals()['qdrant_client_global'] = qdrant_client_instance # For direct use if needed, and for passing to BG task
        logger.info(f"Successfully connected to Qdrant instance at {QDRANT_HOST}:{QDRANT_PORT}.")

        try:
            collection_info = qdrant_client_instance.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' already exists. Details: {collection_info}")
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                logger.info(f"Qdrant collection '{QDRANT_COLLECTION_NAME}' not found. Attempting to create it...")
                try:
                    qdrant_client_instance.create_collection(
                        collection_name=QDRANT_COLLECTION_NAME,
                        vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=QDRANT_DISTANCE_METRIC)
                    )
                    logger.info(f"Successfully created Qdrant collection '{QDRANT_COLLECTION_NAME}'")
                except Exception as create_e:
                    logger.error(f"Failed to create Qdrant collection '{QDRANT_COLLECTION_NAME}': {create_e}", exc_info=True)
            else:
                logger.error(f"Error checking Qdrant collection '{QDRANT_COLLECTION_NAME}': {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant or ensure collection: {e}", exc_info=True)
        # qdrant_client_global will remain None if startup fails. Dependencies will handle this.

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Ingestion Orchestration Service shutting down...")
    # if qdrant_client_global: # qdrant_client_global is now accessed via app.state or passed directly
    #     try:
    #         # qdrant_client_global.close() # Check Qdrant client documentation
    #         logger.info("Qdrant client closed (if applicable).")
    #     except Exception as e:
    #         logger.error(f"Error closing Qdrant client: {e}", exc_info=True)
    await duplicates_on_shutdown()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Request validation error: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": exc.body})

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Please check logs for more details."})

class IngestRequest(BaseModel):
    directory_path: str

@v1_router.post("/ingest/")
async def ingest_directory_v1(request: IngestRequest, background_tasks: BackgroundTasks, q_client: QdrantClient = Depends(get_qdrant_dependency)): # Use dependency for endpoint check
    job_id = str(uuid.uuid4())
    initial_log_message = f"Job {job_id} initiated for directory: {request.directory_path}"
    
    job_status_db[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "logs": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {initial_log_message}"],
        "result": None,
        "directory_path": request.directory_path, # Store for reference
        "total_files": 0
    }
    logger.info(f"APIv1: Queuing ingestion job {job_id} for directory: {request.directory_path}")

    # Ensure qdrant_client_global is available for the background task
    if qdrant_client_global is None:
        error_msg = "Qdrant client not initialized globally. Cannot start background ingestion."
        logger.error(error_msg)
        # Log to a temporary job entry if possible, or just raise
        job_status_db[job_id] = {
            "status": "failed", "progress": 0.0, "logs": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] {error_msg}"],
            "result": {"error": error_msg}, "directory_path": request.directory_path
        }
        raise HTTPException(status_code=503, detail=error_msg)

    # Use a per-collection cache directory
    collection_cache_dir = os.path.join(DISKCACHE_DIR, active_collection_name)
    collection_cache = diskcache.Cache(collection_cache_dir)
    background_tasks.add_task(
        _run_ingestion_task,
        directory_path=request.directory_path,
        job_id=job_id,
        qdrant_conn_bg=qdrant_client_global,
        ml_service_url_bg=ML_INFERENCE_SERVICE_URL,
        ml_batch_size_bg=ML_INFERENCE_BATCH_SIZE,
        disk_cache_bg=collection_cache,
        collection_name_bg=active_collection_name
    )
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": initial_log_message,
        "details_url": f"/api/v1/ingest/status/{job_id}" # Helpful for direct API users
    }

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    logs: List[str] # Changed 'message' to 'logs' for clarity and frontend expectation
    result: Optional[Dict] = None
    directory_path: Optional[str] = None
    total_files: Optional[int] = None

@v1_router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
async def get_ingestion_status_v1(job_id: str):
    logger.info(f"APIv1: Received request for ingestion status for job_id: {job_id}")
    job_info = job_status_db.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    
    # Ensure frontend compatibility: The frontend's background_loader currently expects
    # log messages in a field called "message" or "details".
    # We have 'logs' in job_info and in JobStatusResponse.
    # For now, let's construct the 'message' field for the response if needed,
    # or better, ensure frontend can read 'logs' (which is cleaner).
    # The task breakdown mentioned: *Decision: Confirm if this field is sufficient or if a new logs: List[str] field is preferred...*
    # We've opted for logs: List[str] in JobStatusResponse here.
    # The frontend will need a minor adaptation if it strictly expects a single "message" string for logs.

    return JobStatusResponse(
        job_id=job_id,
        status=job_info["status"],
        progress=job_info.get("progress", 0.0),
        logs=job_info["logs"],
        result=job_info.get("result"),
        directory_path=job_info.get("directory_path"),
        total_files=job_info.get("total_files")
    )

# ... (rest of the file: search endpoints, routers, uvicorn.run, etc.)
# Include new routers into v1_router
v1_router.include_router(search_router.router, prefix="/search", tags=["Qdrant Search Extensions"]) # Path from plan
v1_router.include_router(images_router.router, prefix="/images", tags=["Qdrant Image Listing Extensions"]) # Path from plan
v1_router.include_router(duplicates_router.router, prefix="/duplicates", tags=["Qdrant Duplicate Detection Extensions"]) # Path from plan
v1_router.include_router(random_router.router, prefix="/random", tags=["Qdrant Random Image Extensions"]) # Path from plan

# --- Qdrant Collection Management Endpoints ---
class CollectionNameRequest(BaseModel):
    collection_name: str

@v1_router.get("/collections", response_model=List[str])
async def list_collections(q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """List all Qdrant collections"""
    collections_info = q_client.get_collections().collections
    return [c.name for c in collections_info]

@v1_router.post("/collections", response_model=Dict[str, str])
async def create_collection(req: CollectionNameRequest, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Create a new Qdrant collection with default vector params"""
    q_client.create_collection(
        collection_name=req.collection_name,
        vectors_config=VectorParams(size=QDRANT_VECTOR_SIZE, distance=QDRANT_DISTANCE_METRIC)
    )
    return {"collection": req.collection_name}

@v1_router.post("/collections/select", response_model=Dict[str, str])
async def select_collection(req: CollectionNameRequest):
    """Select the active Qdrant collection for future operations"""
    global active_collection_name
    active_collection_name = req.collection_name
    return {"selected_collection": active_collection_name}

@v1_router.post("/collections/cache/clear", response_model=Dict[str, str])
async def clear_collection_cache():
    """Clear the disk cache for the currently active Qdrant collection."""
    cache_dir = os.path.join(DISKCACHE_DIR, active_collection_name)
    cache = diskcache.Cache(cache_dir)
    cache.clear()
    return {"cache_cleared_for": active_collection_name}

# Include the v1 router in the main app
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 