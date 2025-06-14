import os # Added import
# Add project root to sys.path to allow importing 'utils'
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from fastapi import FastAPI, HTTPException, APIRouter, Depends, Request, BackgroundTasks # Added BackgroundTasks
from fastapi.responses import JSONResponse # Added JSONResponse
from fastapi.exceptions import RequestValidationError # Added RequestValidationError
from fastapi.middleware.cors import CORSMiddleware # Added CORS middleware
import httpx
from pydantic import BaseModel
from typing import List, Dict, Any, Tuple, Optional # Added Tuple and Optional
import aiofiles # For async file reading
import base64 # For encoding image data
from qdrant_client import QdrantClient # Qdrant client
from qdrant_client.http import models # Ensures models.PointStruct is valid
from qdrant_client.http.models import Distance, VectorParams, UpdateStatus # For collection creation
from utils.metadata_extractor import extract_metadata # Import the new extractor
import uuid # Added for generating UUIDs for point_id
import hashlib # Added for image content hashing
from PIL import Image # For DNG->RGB conversion
import io # For encoding PIL images to bytes
import diskcache
import time # For logging timestamps
import asyncio # Added for sleep in background task
from functools import partial # Import partial for to_thread

import logging

# --- Configuration ---
IMG_RESIZE_MAX_DIM = int(os.environ.get("IMG_RESIZE_MAX_DIM", 1024)) # Max dimension for resizing

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Create a router for API version 1
v1_router = APIRouter(prefix="/api/v1")

ML_INFERENCE_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
ML_INFERENCE_BATCH_SIZE = int(os.environ.get("ML_INFERENCE_BATCH_SIZE", 128))  # Increased default per roadmap (safe on 6 GB GPUs)
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost") # Assuming Qdrant might run locally or in Docker
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "") # Corrected default
active_collection_name = QDRANT_COLLECTION_NAME  # Global active collection that can be changed via API
# Define standard vector parameters for the collection (e.g., for ViT-B/32 CLIP model)
QDRANT_VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", 512))
QDRANT_DISTANCE_METRIC = Distance[os.environ.get("QDRANT_DISTANCE_METRIC", "Cosine").upper()]
QDRANT_UPSERT_BATCH_SIZE = int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", 32))

# Global Qdrant client instance is now managed via app.state
# qdrant_client_global: Optional[QdrantClient] = None
# Persistent cache for image hashes to embeddings and captions
DISKCACHE_DIR = os.environ.get("DISKCACHE_DIR", "./.diskcache")
image_content_cache = diskcache.Cache(DISKCACHE_DIR)

# In-memory job status database
# Format: { "job_id": {"status": "pending/processing/completed/failed", "progress": 0.0-100.0, "logs": ["log message1", ...], "result": {}}}
job_status_db: Dict[str, Dict[str, Any]] = {}

# --- Pydantic Models for structured job results ---

class ProcessedFileDetail(BaseModel):
    file: str
    source: str
    details: Optional[Dict[str, Any]] = None

class FailedFileDetail(BaseModel):
    file: str
    error: str
    details: Optional[str] = None

class IngestionResult(BaseModel):
    total_processed: int
    total_failed: int
    total_from_cache: int
    processed_files: List[ProcessedFileDetail]
    failed_files: List[FailedFileDetail]

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

# --- New Helper function for resizing images ---
def _resize_image(image_bytes: bytes, max_dim: int) -> bytes:
    """
    Resizes an image to have its largest dimension be `max_dim`, preserving aspect ratio.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if max(img.width, img.height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            # Save as PNG to handle transparency and avoid JPEG artifacts
            img.save(buf, format='PNG')
            return buf.getvalue()
    except Exception as e:
        logger.warning(f"Could not resize image, returning original. Error: {e}", exc_info=True)
        return image_bytes

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
    # Prepare images, decoding DNG locally, resizing, and converting to PNG where needed
    images_payload = []
    for image_hash, image_b64, filename, file_path in batch_items_to_ml:
        filename_to_send = filename  # Default to original filename; may change if conversion occurs
        try:
            current_bytes = base64.b64decode(image_b64)
            # No local DNG → PNG conversion; send RAW bytes directly (saves ~35% CPU)
            is_raw_dng = file_path.lower().endswith('.dng')

            if is_raw_dng:
                # Keep original bytes and file name; ML service can handle DNG directly
                final_b64 = image_b64  # Already base64-encoded upstream
            else:
                # --- Image Resizing Step ---
                # Offload resizing to a thread to keep the event loop non-blocked
                resized_bytes = await asyncio.to_thread(_resize_image, current_bytes, IMG_RESIZE_MAX_DIM)
                final_b64 = base64.b64encode(resized_bytes).decode('utf-8')
                # -------------------------

            images_payload.append(
                MLBatchRequestItem(unique_id=image_hash, image_base64=final_b64, filename=filename_to_send).dict()
            )
        except Exception as e:
            log_to_job(job_id, f"Error preparing image {filename} for ML service: {e}", level="ERROR")
            # Add to failed files and skip this image
            failed_files_details.append({"file": file_path, "error": f"Failed during prep/resize: {e}"})
            continue # Move to the next image

    # Ensure there's still a payload to send after potential prep failures
    if not images_payload:
        log_to_job(job_id, "No images left to process after preparation/resizing step.", level="WARNING")
        return

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
                # Offload metadata extraction to a thread
                comprehensive_metadata = await asyncio.to_thread(extract_metadata, file_path)
                log_to_job(job_id, f"Metadata extracted for {filename}: {comprehensive_metadata}")

                async with aiofiles.open(file_path, "rb") as f_img_bytes:
                    image_bytes_for_size = await f_img_bytes.read()

                if qdrant_conn:
                    point_id_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
                    qdrant_payload = comprehensive_metadata.copy()
                    
                    # Store base64 image data for fast serving
                    image_base64 = base64.b64encode(image_bytes_for_size).decode('utf-8')
                    
                    # Create thumbnail (200x200) for faster loading
                    try:
                        thumbnail_img = Image.open(io.BytesIO(image_bytes_for_size))
                        thumbnail_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                        thumbnail_buffer = io.BytesIO()
                        thumbnail_img.save(thumbnail_buffer, format='JPEG', quality=85)
                        thumbnail_base64 = base64.b64encode(thumbnail_buffer.getvalue()).decode('utf-8')
                    except Exception as e:
                        log_to_job(job_id, f"Failed to create thumbnail for {filename}: {e}", level="WARNING")
                        thumbnail_base64 = image_base64  # Fallback to full image
                    
                    qdrant_payload.update({
                        "caption": caption, 
                        "original_size_bytes": len(image_bytes_for_size),
                        "full_path": file_path, 
                        "ml_embedding_model": model_name_clip,
                        "ml_caption_model": model_name_blip,
                        "filename": qdrant_payload.get("filename", filename),
                        "image_base64": image_base64,  # Store full image as base64
                        "thumbnail_base64": thumbnail_base64  # Store thumbnail as base64
                    })
                    qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                    log_to_job(job_id, f"Queueing point for Qdrant upsert: {filename} (ID: {point_id_str}) with base64 data")
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
    from_cache_count = 0
    batch_items_to_ml = []
    
    all_files = []
    for root, _, files in os.walk(directory_path):
        for name in files:
            all_files.append(os.path.join(root, name))
    
    job_status_db[job_id]["total_files"] = len(all_files)
    total_files = len(all_files)
    if total_files == 0:
        log_to_job(job_id, "No files found in the directory.", level="WARNING")
        job_status_db[job_id]["status"] = "completed"
        job_status_db[job_id]["progress"] = 100.0
        job_status_db[job_id]["result"] = IngestionResult(
            total_processed=0,
            total_failed=0,
            total_from_cache=0,
            processed_files=[],
            failed_files=[]
        ).dict()
        return

    try:
        async with httpx.AsyncClient() as client:
            for i, file_path in enumerate(all_files):
                progress = (i + 1) / total_files * 100
                job_status_db[job_id]["progress"] = progress
                filename = os.path.basename(file_path)

                try:
                    log_to_job(job_id, f"Processing file {i+1}/{total_files}: {filename}")
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                    
                    # Offload potentially CPU-heavy SHA-256 calculation to a worker thread
                    image_hash = await asyncio.to_thread(lambda: hashlib.sha256(content).hexdigest())
                    
                    cached_data = disk_cache_bg.get(image_hash)
                    if cached_data:
                        log_to_job(job_id, f"Cache hit for {filename} (hash: {image_hash}). Skipping ML inference.")
                        from_cache_count += 1
                        
                        point_id_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, file_path))
                        comprehensive_metadata = await asyncio.to_thread(extract_metadata, file_path)
                        
                        # Store base64 image data for fast serving (cached items)
                        image_base64 = base64.b64encode(content).decode('utf-8')
                        
                        # Create thumbnail for cached items
                        try:
                            thumbnail_img = Image.open(io.BytesIO(content))
                            thumbnail_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                            thumbnail_buffer = io.BytesIO()
                            thumbnail_img.save(thumbnail_buffer, format='JPEG', quality=85)
                            thumbnail_base64 = base64.b64encode(thumbnail_buffer.getvalue()).decode('utf-8')
                        except Exception as e:
                            log_to_job(job_id, f"Failed to create thumbnail for cached {filename}: {e}", level="WARNING")
                            thumbnail_base64 = image_base64  # Fallback to full image
                        
                        qdrant_payload = comprehensive_metadata.copy()
                        qdrant_payload.update({
                            "caption": cached_data.get("caption_data", {}).get("caption", ""),
                            "original_size_bytes": len(content),
                            "full_path": file_path,
                            "ml_embedding_model": cached_data.get("embedding_data", {}).get("model_name"),
                            "ml_caption_model": cached_data.get("caption_data", {}).get("model_name"),
                            "filename": qdrant_payload.get("filename", filename),
                            "image_base64": image_base64,  # Store full image as base64
                            "thumbnail_base64": thumbnail_base64  # Store thumbnail as base64
                        })
                        qdrant_payload = {k: v for k, v in qdrant_payload.items() if v is not None}

                        point = models.PointStruct(
                            id=point_id_str,
                            vector=cached_data.get("embedding_data", {}).get("embedding"),
                            payload=qdrant_payload
                        )
                        await _upsert_points(qdrant_conn_bg, collection_name_bg, [point])
                        processed_files_details.append(ProcessedFileDetail(
                            file=file_path,
                            source="cache",
                            details=qdrant_payload
                        ).dict())
                    else:
                        log_to_job(job_id, f"Cache miss for {filename}. Adding to ML batch.")
                        image_b64 = base64.b64encode(content).decode('utf-8')
                        batch_items_to_ml.append((image_hash, image_b64, filename, file_path))

                        if len(batch_items_to_ml) >= ml_batch_size_bg:
                            await process_batch_with_ml_service(
                                client, batch_items_to_ml, processed_files_details, failed_files_details,
                                job_id, qdrant_conn_bg, collection_name_bg, ml_service_url_bg
                            )
                            batch_items_to_ml = []
                
                except Exception as e_file:
                    log_to_job(job_id, f"Failed to process file {filename}: {e_file}", level="ERROR")
                    failed_files_details.append(FailedFileDetail(
                        file=file_path,
                        error=str(e_file),
                        details="File processing loop"
                    ).dict())

            if batch_items_to_ml:
                await process_batch_with_ml_service(
                    client, batch_items_to_ml, processed_files_details, failed_files_details,
                    job_id, qdrant_conn_bg, collection_name_bg, ml_service_url_bg
                )

        log_to_job(job_id, "Ingestion task finished.")
        job_status_db[job_id]["status"] = "completed"
        job_status_db[job_id]["progress"] = 100.0
        job_status_db[job_id]["result"] = IngestionResult(
            total_processed=len(processed_files_details),
            total_failed=len(failed_files_details),
            total_from_cache=from_cache_count,
            processed_files=processed_files_details,
            failed_files=failed_files_details
        ).dict()
    except Exception as e:
        error_message = f"An unexpected error occurred in the ingestion task: {e}"
        log_to_job(job_id, error_message, level="ERROR")
        logger.exception(error_message)
        job_status_db[job_id]["status"] = "failed"
        job_status_db[job_id]["result"] = {"error": str(e), "message": error_message}
        # Preserve any partial results
        job_status_db[job_id]["result"]["processed_files"] = processed_files_details
        job_status_db[job_id]["result"]["failed_files"] = failed_files_details

@app.get("/")
async def root():
    return {"message": "Ingestion Orchestration Service is running"}

@app.get("/health")
async def health():
    return {"service": "ingestion-orchestration", "status": "ok"}

@app.on_event("startup")
async def startup_event():
    """
    On startup, connect to Qdrant and try to get the batch size from the ML service.
    The Qdrant client is attached to the app state for dependency injection.
    """
    global active_collection_name, ML_INFERENCE_BATCH_SIZE
    logger.info("Ingestion Orchestration Service starting up...")

    # --- Qdrant Connection ---
    logger.info(f"Connecting to Qdrant at: {QDRANT_HOST}:{QDRANT_PORT}")
    try:
        # Initialize the client and attach it to the app's state
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Verify connection
        qdrant_client.get_collections()
        app.state.qdrant_client = qdrant_client
        logger.info(f"Successfully connected to Qdrant instance at {QDRANT_HOST}:{QDRANT_PORT}.")
    except Exception as e:
        logger.critical(f"Could not connect to Qdrant. Please check if it is running. Error: {e}", exc_info=True)
        # Set client to None on state so dependencies can check for it
        app.state.qdrant_client = None

    # --- ML Service Capability Check ---
    logger.info(f"Expecting ML Inference Service at: {ML_INFERENCE_SERVICE_URL}")
    max_retries = 5
    retry_delay = 3  # seconds
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{ML_INFERENCE_SERVICE_URL}/api/v1/capabilities", timeout=10.0)
                res.raise_for_status()
                capabilities = res.json()
                batch_size = capabilities.get("safe_clip_batch")
                if batch_size and isinstance(batch_size, int):
                    ML_INFERENCE_BATCH_SIZE = batch_size
                    logger.info(f"Successfully retrieved ML service capabilities. Batch size set to: {ML_INFERENCE_BATCH_SIZE}")
                else:
                    logger.warning(f"ML service responded but 'safe_clip_batch' was invalid. Using default: {ML_INFERENCE_BATCH_SIZE}")
                break  # Exit loop on success
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} to connect to ML service failed. "
                f"Retrying in {retry_delay} seconds... Error: {e}"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    "Could not retrieve ML service capabilities after multiple retries. "
                    f"Falling back to configured batch size ({ML_INFERENCE_BATCH_SIZE}). "
                    "The ML service might be down or misconfigured."
                )

    # --- Initialize Active Collection ---
    try:
        if qdrant_client:
            collections_response = qdrant_client.get_collections()
            existing_collections = [col.name for col in collections_response.collections]
            if existing_collections:
                if not active_collection_name or active_collection_name not in existing_collections:
                    active_collection_name = existing_collections[0]
                    logger.info(f"No active collection set or previous one not found. Defaulting to first available: '{active_collection_name}'")
            else:
                logger.warning("No collections found in Qdrant. Please create a collection via the API.")
    except Exception as e:
        logger.error(f"Failed to initialize active collection on startup. Error: {e}", exc_info=True)


    logger.info("Ingestion Orchestration Service startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Ingestion Orchestration Service shutting down...")
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
async def ingest_directory_v1(request: IngestRequest, background_tasks: BackgroundTasks, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    if not active_collection_name:
        raise HTTPException(status_code=400, detail="No collection selected. Please select a collection first using the /api/v1/collections/select endpoint.")
    
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

    # Use a per-collection cache directory
    collection_cache_dir = os.path.join(DISKCACHE_DIR, active_collection_name)
    collection_cache = diskcache.Cache(collection_cache_dir)
    background_tasks.add_task(
        _run_ingestion_task,
        directory_path=request.directory_path,
        job_id=job_id,
        qdrant_conn_bg=q_client,
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
    result: Optional[IngestionResult] = None
    directory_path: Optional[str] = None
    total_files: Optional[int] = None

@v1_router.get("/ingest/status/{job_id}", response_model=JobStatusResponse)
async def get_ingestion_status_v1(job_id: str):
    logger.info(f"APIv1: Received request for ingestion status for job_id: {job_id}")
    job_info = job_status_db.get(job_id)
    if not job_info:
        raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found.")
    
    # or better, ensure frontend can read 'logs' (which is cleaner).
    # The task breakdown mentioned: *Decision: Confirm if this field is sufficient or if a new logs: List[str] field is preferred...*
    # We've opted for logs: List[str] in JobStatusResponse here.
    # The frontend will need a minor adaptation if it strictly expects a single "message" string for logs.

    # Handle the case where the result might be a simple dict on failure instead of IngestionResult
    result_data = job_info.get("result")
    if result_data and not isinstance(result_data, IngestionResult):
        # If it's a dict (e.g., from a generic exception), wrap it for consistency or handle as needed
        # For now, we'll allow it to be a dict, Pydantic will validate
        pass

    return JobStatusResponse(
        job_id=job_id,
        status=job_info["status"],
        progress=job_info.get("progress", 0.0),
        logs=job_info["logs"],
        result=result_data,
        directory_path=job_info.get("directory_path"),
        total_files=job_info.get("total_files")
    )

# ... (rest of the file: search endpoints, routers, uvicorn.run, etc.)
# Include new routers into v1_router
v1_router.include_router(search_router.router, prefix="/search", tags=["Qdrant Search Extensions"]) # Path from plan
v1_router.include_router(images_router.router, prefix="/images", tags=["Qdrant Image Listing Extensions"]) # Path from plan
v1_router.include_router(duplicates_router.router, prefix="/duplicates", tags=["Qdrant Duplicate Detection Extensions"]) # Path from plan
v1_router.include_router(random_router.router, prefix="/random", tags=["Qdrant Random Image Extensions"]) # Path from plan

# --- Text Search Endpoint ---
class TextSearchRequest(BaseModel):
    text: str
    limit: int = 10
    offset: int = 0

class SearchResultItem(BaseModel):
    id: str
    filename: str
    caption: Optional[str] = None
    score: float
    thumbnail_url: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

class TextSearchResponse(BaseModel):
    total_approx: int
    page: int
    per_page: int
    results: List[SearchResultItem]
    query: str
    embedding_model: Optional[str] = None

@v1_router.post("/search/text", response_model=TextSearchResponse)
async def search_text_v1(request: TextSearchRequest, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """
    Search images using natural language text queries.
    Converts text to embedding using ML service and searches Qdrant.
    """
    global active_collection_name
    if not active_collection_name:
        raise HTTPException(status_code=400, detail="No collection selected. Please select a collection first.")
    
    try:
        # Step 1: Convert text to embedding using ML service
        logger.info(f"Converting text query to embedding: '{request.text[:50]}{'...' if len(request.text) > 50 else ''}'")
        
        async with httpx.AsyncClient() as client:
            ml_response = await client.post(
                f"{ML_INFERENCE_SERVICE_URL}/api/v1/embed_text",
                json={"text": request.text}
            )
            
        if ml_response.status_code != 200:
            logger.error(f"ML service failed to generate text embedding: {ml_response.status_code} - {ml_response.text}")
            raise HTTPException(status_code=500, detail="Failed to generate text embedding from ML service")
        
        ml_data = ml_response.json()
        text_embedding = ml_data["embedding"]
        embedding_model = ml_data.get("model_name", "unknown")
        
        logger.info(f"Text embedding generated: {len(text_embedding)} dimensions using {embedding_model}")
        
        # Step 2: Search Qdrant with the embedding
        search_results = await asyncio.to_thread(
            q_client.search,
            collection_name=active_collection_name,
            query_vector=text_embedding,
            limit=request.limit,
            offset=request.offset,
            with_payload=True
        )
        
        # Step 3: Format results
        formatted_results = []
        for result in search_results:
            result_item = SearchResultItem(
                id=str(result.id),
                filename=result.payload.get("filename", "unknown"),
                caption=result.payload.get("caption"),
                score=float(result.score),
                thumbnail_url=f"http://localhost:8002/api/v1/images/{result.id}/thumbnail",  # Full URL for frontend
                payload=result.payload
            )
            formatted_results.append(result_item)
        
        logger.info(f"Text search returned {len(formatted_results)} results")
        
        return TextSearchResponse(
            total_approx=len(formatted_results),  # TODO: Get actual total count from Qdrant
            page=request.offset // request.limit + 1,
            per_page=request.limit,
            results=formatted_results,
            query=request.text,
            embedding_model=embedding_model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in text search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Text search failed: {str(e)}")

# --- Qdrant Collection Management Endpoints ---
class CollectionNameRequest(BaseModel):
    collection_name: str
    vector_size: Optional[int] = None
    distance: Optional[str] = None

@v1_router.get("/collections", response_model=List[str])
async def list_collections(q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """List all Qdrant collections"""
    collections_info = q_client.get_collections().collections
    return [c.name for c in collections_info]

@v1_router.post("/collections", response_model=Dict[str, Any])
async def create_collection(req: CollectionNameRequest, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Create a new Qdrant collection with optional, specific vector params"""
    try:
        # Check if collection already exists
        existing_collections = q_client.get_collections().collections
        existing_names = [c.name for c in existing_collections]
        
        if req.collection_name in existing_names:
            logger.warning(f"Collection '{req.collection_name}' already exists")
            raise HTTPException(
                status_code=409,
                detail=f"Collection '{req.collection_name}' already exists"
            )
        
        vector_size = req.vector_size or QDRANT_VECTOR_SIZE
        distance_metric_str = req.distance or "COSINE"  # Use hardcoded default for now
        
        logger.info(f"Creating collection '{req.collection_name}' with vector_size={vector_size}, distance={distance_metric_str}")
        
        try:
            distance_metric = Distance[distance_metric_str.upper()]
        except KeyError:
            available_metrics = [d.name for d in Distance]
            logger.error(f"Invalid distance metric '{distance_metric_str}'. Available: {available_metrics}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid distance metric '{distance_metric_str}'. Must be one of: {', '.join(available_metrics)}"
            )

        # Create the collection
        q_client.create_collection(
            collection_name=req.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance_metric)
        )
        
        logger.info(f"Successfully created collection '{req.collection_name}'")
        return {
            "collection": req.collection_name, 
            "status": "created",
            "vector_size": vector_size, 
            "distance": distance_metric.value
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error creating collection '{req.collection_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")

@v1_router.delete("/collections/{collection_name}", response_model=Dict[str, Any])
async def delete_collection(collection_name: str, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Delete a Qdrant collection by name."""
    try:
        result = q_client.delete_collection(collection_name=collection_name)
        if result:
            # If the collection was active, reset the active_collection_name
            global active_collection_name
            if active_collection_name == collection_name:
                active_collection_name = ""
                # Also clear from app state
                app.state.active_collection_name = ""
                logger.info(f"Active collection '{collection_name}' was deleted. Active collection has been reset.")
            return {"status": "success", "message": f"Collection '{collection_name}' deleted successfully."}
        else:
            # This case might indicate the operation was accepted but execution is pending, or it failed silently.
            # Qdrant's delete_collection returns True on success, so False might mean it didn't exist or another issue.
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' could not be deleted or was not found.")
    except Exception as e:
        # Catching potential exceptions from the client, e.g., if Qdrant is down or responds with an error.
        logger.error(f"Error deleting collection '{collection_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@v1_router.post("/collections/select", response_model=Dict[str, str])
async def select_collection(req: CollectionNameRequest):
    """Select the active Qdrant collection for future operations"""
    global active_collection_name
    active_collection_name = req.collection_name
    
    # Also store in app state for dependency injection
    app.state.active_collection_name = req.collection_name
    
    logger.info(f"Selected collection: {req.collection_name}")
    return {"selected_collection": req.collection_name}

@v1_router.get("/collections/{collection_name}/info", response_model=Dict[str, Any])
async def get_collection_info(collection_name: str, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Get detailed information about a specific collection"""
    try:
        # Get collection info from Qdrant
        collection_info = q_client.get_collection(collection_name=collection_name)
        
        # Get a few sample points to understand the data structure
        sample_result = q_client.scroll(
            collection_name=collection_name,
            limit=3,
            with_payload=True
        )
        
        sample_points = sample_result[0] if sample_result else []
        
        # Extract metadata from sample points
        sample_metadata = []
        for point in sample_points:
            if point.payload:
                sample_metadata.append({
                    "id": str(point.id),
                    "filename": point.payload.get("filename", "unknown"),
                    "timestamp": point.payload.get("timestamp", "unknown"),
                    "has_thumbnail": "thumbnail_base64" in point.payload,
                    "has_caption": "caption" in point.payload,
                })
        
        return {
            "name": collection_name,
            "status": collection_info.status.value if collection_info.status else "unknown",
            "points_count": collection_info.points_count,
            "vectors_count": collection_info.vectors_count,
            "indexed_vectors_count": collection_info.indexed_vectors_count,
            "config": {
                "vector_size": collection_info.config.params.vectors.size if collection_info.config.params.vectors else None,
                "distance": collection_info.config.params.vectors.distance.value if collection_info.config.params.vectors else None,
            },
            "sample_points": sample_metadata,
            "is_active": collection_name == active_collection_name,
        }
        
    except Exception as e:
        logger.error(f"Error getting collection info for '{collection_name}': {e}")
        raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found or error retrieving info")

@v1_router.post("/collections/cache/clear", response_model=Dict[str, str])
async def clear_collection_cache():
    """Clear the disk cache for the currently active Qdrant collection."""
    cache_dir = os.path.join(DISKCACHE_DIR, active_collection_name)
    cache = diskcache.Cache(cache_dir)
    cache.clear()
    return {"cache_cleared_for": active_collection_name}

# --- Image Serving Endpoints ---
from fastapi.responses import FileResponse, Response
import io
import base64

@v1_router.get("/images/{image_id}/thumbnail")
async def get_image_thumbnail(image_id: str, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Serve image thumbnail by ID - optimized for speed with base64 data"""
    global active_collection_name
    if not active_collection_name:
        raise HTTPException(status_code=400, detail="No collection selected")
    
    try:
        # Get the image data from Qdrant
        result = q_client.retrieve(
            collection_name=active_collection_name,
            ids=[image_id],
            with_payload=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = result[0]
        payload = point.payload
        
        # Fast path: use pre-generated thumbnail
        if "thumbnail_base64" in payload:
            thumbnail_data = base64.b64decode(payload["thumbnail_base64"])
            return Response(content=thumbnail_data, media_type="image/jpeg")
        
        # Fallback: use full image and create thumbnail
        image_data = None
        if "image_base64" in payload:
            image_data = base64.b64decode(payload["image_base64"])
        elif "full_path" in payload or "file_path" in payload:
            # Fast file system fallback - read from file path
            file_path = payload.get("full_path") or payload.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # Create thumbnail on-the-fly (should rarely happen with new ingestion)
        try:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85)
            thumbnail_data = img_byte_arr.getvalue()
            
            return Response(content=thumbnail_data, media_type="image/jpeg")
            
        except Exception as e:
            logger.error(f"Error creating thumbnail for {image_id}: {e}")
            # Return original image if thumbnail creation fails
            filename = payload.get("filename", "image.jpg")
            content_type = "image/jpeg"
            if filename.lower().endswith('.png'):
                content_type = "image/png"
            elif filename.lower().endswith('.gif'):
                content_type = "image/gif"
            elif filename.lower().endswith('.webp'):
                content_type = "image/webp"
            
            return Response(content=image_data, media_type=content_type)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail for {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image thumbnail")

@v1_router.get("/images/{image_id}/image")
async def get_full_image(image_id: str, q_client: QdrantClient = Depends(get_qdrant_dependency)):
    """Serve full image by ID - optimized for speed with base64 data"""
    global active_collection_name
    if not active_collection_name:
        raise HTTPException(status_code=400, detail="No collection selected")
    
    try:
        # Get the image data from Qdrant
        result = q_client.retrieve(
            collection_name=active_collection_name,
            ids=[image_id],
            with_payload=True
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Image with ID {image_id} not found")
        
        point = result[0]
        payload = point.payload
        
        # Fast path: use stored base64 data
        image_data = None
        if "image_base64" in payload:
            image_data = base64.b64decode(payload["image_base64"])
        elif "full_path" in payload or "file_path" in payload:
            # Fast file system fallback - read from file path
            file_path = payload.get("full_path") or payload.get("file_path")
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    image_data = f.read()
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # Determine content type from filename
        filename = payload.get("filename", "image.jpg")
        if filename.lower().endswith('.png'):
            content_type = "image/png"
        elif filename.lower().endswith('.gif'):
            content_type = "image/gif"
        elif filename.lower().endswith('.webp'):
            content_type = "image/webp"
        elif filename.lower().endswith('.dng'):
            content_type = "image/jpeg"  # DNG is converted to JPEG during processing
        else:
            content_type = "image/jpeg"
        
        return Response(content=image_data, media_type=content_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to serve image")

# Include the v1 router in the main app
app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 