from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import logging
import os
import uuid
import asyncio
from pathlib import Path
import base64
import hashlib
import httpx
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition
import diskcache
from PIL import Image, ExifTags
import io
import rawpy
import tempfile
import shutil
import exifread
import glob
from datetime import datetime

from ..dependencies import get_qdrant_client, get_active_collection, app_state
from ..pipeline import manager as pipeline_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])

# In-memory job tracking (in production, use Redis or database)
job_status = {}
# Track the most recent ingestion job per collection so the UI can link
# directly to the latest logs without polling all jobs.
recent_jobs: Dict[str, str] = {}

# Configuration
# Prefer ML_INFERENCE_SERVICE_URL but fall back to ML_SERVICE_URL for
# legacy compatibility, so operators can define either one.
ML_SERVICE_URL = (
    os.getenv("ML_INFERENCE_SERVICE_URL")
    or os.getenv("ML_SERVICE_URL", "http://localhost:8001")
)
ML_BATCH_SIZE = int(os.getenv("ML_INFERENCE_BATCH_SIZE", "25"))
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "32"))

# NEW ➡️  Feature flag to enable multipart uploads (pre-decoded PNG streaming)
USE_MULTIPART_UPLOAD = os.getenv("USE_MULTIPART_UPLOAD", "0") not in {"0", "false", "False"}

# Initialize disk cache for deduplication
cache = diskcache.Cache('.diskcache')

# Supported image file extensions
SUPPORTED_EXTENSIONS = [
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', 
    '.webp', '.dng', '.raw', '.cr2', '.nef', '.arw', '.orf', 
    '.rw2', '.pef', '.srw', '.heic', '.heif'
]

# ---------------------------------------------------------------------------
# Optional XMP support
# ---------------------------------------------------------------------------
# libxmp requires the native «Exempi» library which is often missing on
# Windows systems.  When that happens libxmp raises *ExempiLoadError*, not
# ImportError, so we must guard against any Exception during the import.
# If it fails we silently disable XMP keyword extraction – the rest of the
# ingestion pipeline continues to work.
# ---------------------------------------------------------------------------

try:
    from libxmp import XMPFiles, consts as xmp_consts  # type: ignore
except Exception:  # pragma: no cover – includes ExempiLoadError
    XMPFiles = None  # type: ignore
    xmp_consts = None  # type: ignore
    logger.info("libxmp unavailable – XMP keyword extraction disabled (Exempi missing?)")

class IngestRequest(BaseModel):
    directory_path: str = Field(..., description="Absolute path to the directory containing images")

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

@router.post("/", response_model=JobResponse)
async def start_ingestion(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Starts a background ingestion job for a local directory path.
    This endpoint is suitable for server-side execution where the backend
    has direct access to the file system.
    """
    if not os.path.isdir(request.directory_path):
        raise HTTPException(status_code=400, detail="Directory not found.")

    job_id = await pipeline_manager.start_pipeline(
        directory_path=request.directory_path,
        collection_name=collection_name,
        background_tasks=background_tasks,
        qdrant_client=qdrant_client
    )
    return JobResponse(job_id=job_id, status="started", message="Ingestion job started successfully.")

@router.post("/scan", response_model=JobResponse)
async def start_ingestion_from_path(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Alias for the main ingestion endpoint. Starts a background ingestion job for a given path.
    """
    if not os.path.isdir(request.directory_path):
        raise HTTPException(status_code=400, detail="Directory not found.")
        
    job_id = await pipeline_manager.start_pipeline(
        directory_path=request.directory_path,
        collection_name=collection_name,
        background_tasks=background_tasks,
        qdrant_client=qdrant_client
    )
    return JobResponse(job_id=job_id, status="started", message="Ingestion scan started successfully.")

def cleanup_temp_dir(path: str):
    """Safely remove a temporary directory."""
    logger.info(f"Cleaning up temporary directory: {path}")
    shutil.rmtree(path, ignore_errors=True)

@router.post("/upload", response_model=JobResponse)
async def upload_and_ingest_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    collection_name: str = Depends(get_active_collection)
):
    """
    Accepts file uploads, saves them to a temporary directory,
    and starts an ingestion job for that directory.
    """
    # Create a unique temporary directory for this upload batch
    temp_dir = tempfile.mkdtemp(prefix="vibe_upload_")
    
    # Add a background task to clean up the directory after the response is sent
    # This task will run after the pipeline has finished with the directory.
    # Note: We create a new BackgroundTasks object for the cleanup.
    cleanup_tasks = BackgroundTasks()
    cleanup_tasks.add_task(cleanup_temp_dir, temp_dir)

    # Save uploaded files to the temporary directory
    for file in files:
        try:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

    # Start the pipeline on the temporary directory
    job_id = await pipeline_manager.start_pipeline(
        directory_path=temp_dir,
        collection_name=collection_name,
        background_tasks=background_tasks,
        qdrant_client=qdrant_client
    )
    
    # The cleanup will be handled by the background task associated with the request that started the pipeline
    # To ensure cleanup happens *after* ingestion, a more robust system would involve the pipeline
    # itself triggering the cleanup. For now, we rely on the original background_tasks object.
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message=f"Started ingestion for {len(files)} uploaded files."
    )

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Retrieves the status of a specific ingestion job.
    """
    job_ctx = pipeline_manager.get_job_status(job_id)
    if not job_ctx:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_ctx.job_id,
        "status": job_ctx.status.value,
        "progress": job_ctx.progress,
        "total_files": job_ctx.total_files,
        "processed_files": job_ctx.processed_files,
        "cached_files": job_ctx.cached_files,
        "failed_files": job_ctx.failed_files,
        "start_time": datetime.fromtimestamp(job_ctx.start_time).isoformat() if job_ctx.start_time else None,
        "end_time": datetime.fromtimestamp(job_ctx.end_time).isoformat() if job_ctx.end_time else None,
        "logs": job_ctx.logs[-100:],  # Return last 100 log entries
        "message": job_ctx.logs[-1]["message"] if job_ctx.logs else "",
        "errors": [],
        "exact_duplicates": [],
    }

@router.get("/recent_jobs")
async def get_recent_jobs():
    """
    Retrieves a summary of recent ingestion jobs.
    """
    return pipeline_manager.get_recent_jobs()

@router.post("/archive_duplicates/{job_id}", response_model=JobResponse)
async def archive_duplicates(job_id: str):
    """Move every file listed in ``exact_duplicates`` into a
    ``duplicates_archive`` folder *while* ingestion is still running.

    The endpoint is idempotent – files already moved or missing are skipped.
    Successfully archived entries are removed from ``exact_duplicates`` so
    subsequent calls only act on the remaining ones.
    """

    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    js = job_status[job_id]
    dup_list = js.get("exact_duplicates", [])
    if not dup_list:
        raise HTTPException(status_code=400, detail="No duplicates recorded for this job")

    # Determine archive destination (sibling folder of the source dir)
    src_dir = js.get("directory_path") or os.path.dirname(dup_list[0]["file_path"])
    archive_dir = os.path.join(src_dir, "duplicates_archive")
    os.makedirs(archive_dir, exist_ok=True)

    moved = 0
    remaining: list[dict] = []

    for entry in dup_list:
        src_path = entry.get("file_path")
        if not src_path or not os.path.exists(src_path):
            # Already moved / missing – skip
            continue

        try:
            dest_path = os.path.join(archive_dir, os.path.basename(src_path))
            # Resolve collision by adding short suffix
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                dest_path = f"{base}_{uuid.uuid4().hex[:6]}{ext}"

            # Off-load the blocking I/O to a thread so we don't freeze the API
            await asyncio.to_thread(shutil.move, src_path, dest_path)
            moved += 1
        except Exception as exc:
            err = f"Archive failed for {src_path}: {exc}"
            js.setdefault("errors", []).append(err)
            remaining.append(entry)  # Keep for another try

    # Keep only the duplicates that we did *not* manage to move
    js["exact_duplicates"] = remaining

    msg = f"Archived {moved}/{len(dup_list)} duplicate files to {archive_dir}"
    js.setdefault("logs", []).append(msg)
    js["message"] = msg

    return JobResponse(job_id=job_id, status=js.get("status", "processing"), message=msg)

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

from typing import List as TypingList

def _extract_keyword_tags(path: str) -> TypingList[str]:
    """Attempt to extract keyword tags from IPTC/XMP metadata."""
    tags: TypingList[str] = []
    # Try EXIF XPKeywords first (Windows specific UTF-16LE)
    try:
        with open(path, 'rb') as fh:
            exif_tags = exifread.process_file(fh, details=False, stop_tag="Image XPKeywords")
            xp_val = exif_tags.get("Image XPKeywords")
            if xp_val:
                raw_bytes = xp_val.values
                if isinstance(raw_bytes, bytes):
                    try:
                        decoded = raw_bytes.decode('utf-16le').rstrip('\x00')
                        keywords = [k.strip() for k in decoded.split(';') if k.strip()]
                        tags.extend(keywords)
                    except Exception:
                        pass
    except Exception:
        pass

    # Try XMP subject / hierarchicalSubject if libxmp available
    if XMPFiles is not None:
        try:
            xmpfile = XMPFiles(filename=path, open_forupdate=False)
            xmp = xmpfile.get_xmp()
            if xmp:
                # dc:subject
                if xmp.does_property_exist(xmp_consts.XMP_NS_DC, 'subject'):
                    count = xmp.count_array_items(xmp_consts.XMP_NS_DC, 'subject')
                    for i in range(1, count + 1):
                        item = xmp.get_array_item(xmp_consts.XMP_NS_DC, 'subject', i)
                        if item and item not in tags:
                            tags.append(item)
                # lr:hierarchicalSubject
                LR_NS = 'http://ns.adobe.com/lightroom/1.0/'
                if xmp.does_property_exist(LR_NS, 'hierarchicalSubject'):
                    count = xmp.count_array_items(LR_NS, 'hierarchicalSubject')
                    for i in range(1, count + 1):
                        item = xmp.get_array_item(LR_NS, 'hierarchicalSubject', i)
                        if item and item not in tags:
                            tags.append(item)
        except Exception:
            pass
    return tags

def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from an image file.

    RAW formats (e.g. .dng, .cr2) are handled with *rawpy* to avoid the
    `cannot identify image file` Pillow error that was spamming the logs
    during ingestion. For standard image formats Pillow is still used to
    leverage its rich EXIF utilities.
    """
    # Common RAW extensions that Pillow cannot open reliably
    raw_exts = ('.dng', '.cr2', '.nef', '.arw', '.rw2', '.orf')
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext in raw_exts:
            # Use rawpy for RAW files to obtain basic dimensions. Detailed EXIF
            # parsing for RAW files is outside the current scope and varies by
            # camera vendor, so we only capture the most relevant fields.
            with rawpy.imread(file_path) as raw:
                width = raw.sizes.width
                height = raw.sizes.height
                metadata = {
                    "width": width,
                    "height": height,
                    "format": "RAW",
                    "mode": "RGB"  # rawpy outputs RGB arrays
                }
                # Attempt to extract EXIF tags from RAW container using exifread
                try:
                    with open(file_path, 'rb') as fh:
                        tags = exifread.process_file(fh, details=False)

                    exif_map = {
                        "Image Make": "Make",
                        "Image Model": "Model",
                        "EXIF LensModel": "LensModel",
                        "EXIF DateTimeOriginal": "DateTimeOriginal",
                        "EXIF ISOSpeedRatings": "ISO",
                        "EXIF FNumber": "FNumber",
                        "EXIF ExposureTime": "ExposureTime",
                        "EXIF FocalLength": "FocalLength",
                    }

                    for tag_name, friendly in exif_map.items():
                        if tag_name in tags:
                            metadata[f"exif_{friendly}"] = str(tags[tag_name])
                except Exception as ex:
                    logger.debug(f"EXIF extraction for RAW file {file_path} failed: {ex}")

                # Tags
                kw = _extract_keyword_tags(file_path)
                if kw:
                    metadata["tags"] = kw
                return metadata
        else:
            # --- Standard image path ---
            with Image.open(file_path) as img:
                width, height = img.size
                metadata = {
                    "width": width,
                    "height": height,
                    "format": img.format,
                    "mode": img.mode
                }

            # EXIF extraction via exifread for broader format support
            try:
                with open(file_path, 'rb') as fh:
                    tags = exifread.process_file(fh, details=False)

                exif_map = {
                    "Image Make": "Make",
                    "Image Model": "Model",
                    "EXIF LensModel": "LensModel",
                    "EXIF DateTimeOriginal": "DateTimeOriginal",
                    "EXIF ISOSpeedRatings": "ISO",
                    "EXIF FNumber": "FNumber",
                    "EXIF ExposureTime": "ExposureTime",
                    "EXIF FocalLength": "FocalLength",
                }

                for tag_name, friendly in exif_map.items():
                    if tag_name in tags:
                        metadata[f"exif_{friendly}"] = str(tags[tag_name])
            except Exception as ex:
                logger.debug(f"EXIF extraction with exifread failed for {file_path}: {ex}")

            # Tags
            kw = _extract_keyword_tags(file_path)
            if kw:
                metadata["tags"] = kw
            return metadata
    except Exception as e:
        logger.warning(f"Could not extract metadata from {file_path}: {e}")
        return {"width": 0, "height": 0, "format": "unknown", "mode": "unknown"}

def create_thumbnail_base64(image_path: str, size: tuple = (200, 200)) -> str:
    """Create a thumbnail and return as base64 string."""
    try:
        img: Image.Image
        # Use rawpy for RAW image formats
        if image_path.lower().endswith(('.dng', '.cr2', '.nef', '.arw', '.rw2', '.orf')):
            with rawpy.imread(image_path) as raw:
                # Postprocessing with camera white balance is usually a good starting point
                rgb = raw.postprocess(use_camera_wb=True)
            img = Image.fromarray(rgb).convert('RGB')
        else:
            # Use Pillow for standard image formats
            img = Image.open(image_path)

        # Convert to RGB if necessary (e.g., for PNG with transparency, palette-based images)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Create thumbnail in-place
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save to an in-memory bytes buffer
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85) # Save as JPEG for web efficiency
        thumbnail_bytes = img_byte_arr.getvalue()
        
        # Return base64 encoded string
        return base64.b64encode(thumbnail_bytes).decode('utf-8')
    except Exception as e:
        logger.warning(f"Could not create thumbnail for {image_path}: {e}")
        return ""

async def send_batch_to_ml_service(batch_items: list[dict]) -> list[dict]:
    """Send batch to ML service for embedding and captioning with robust error handling."""
    batch_data = {
        "images": [
            {
                "unique_id": item.get("file_path", item["full_path"]),
                "image_base64": item["image_base64"],
                "filename": item["filename"]
            }
            for item in batch_items
        ]
    }
    
    # More generous timeout based on observed processing times:
    # Base timeout of 300s + 6s per image + 60s buffer for large batches
    timeout_seconds = max(300.0, 300.0 + (len(batch_items) * 6.0) + 60.0)
    
    logger.info(f"Sending batch of {len(batch_items)} images to ML service with {timeout_seconds:.1f}s timeout")
    
    try:
        # Use more robust HTTP configuration
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds, read=timeout_seconds, write=60.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        ) as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
                json=batch_data
            )
            response.raise_for_status()
            results = response.json()["results"]
            logger.info(f"Successfully received ML results for {len(results)} images")
            return results
            
    except httpx.TimeoutException as e:
        error_msg = f"ML service timeout after {timeout_seconds:.1f}s for batch of {len(batch_items)} images"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except httpx.HTTPStatusError as e:
        error_msg = f"ML service HTTP error {e.response.status_code}: {e.response.text}"
        logger.error(error_msg)
        raise Exception(error_msg) from e
    except Exception as e:
        error_msg = f"ML service request failed: {str(e)}"
        logger.error(error_msg)
        raise Exception(error_msg) from e

async def process_directory(job_id: str, directory_path: str, collection_name: str):
    """
    TRUE CONCURRENT PIPELINE INGESTION - Implements the TIP architecture
    
    🧚 Architecture: Four stages running concurrently with streaming data:
    
    [I/O Scanner] ──→ raw_queue ──→ [CPU Processor] ──→ ml_queue ──→ [GPU Worker] ──→ db_queue ──→ [DB Upserter]
                                         ↓                              ↓                      ↓
                                    File reading              ML inference              Qdrant upsert
                                   Hash/dedup check         Embedding/caption          Batch writes
                                   Metadata extraction        Cache storage
    
    Key Improvements:
    - ✅ True streaming pipeline (no batch blocking)
    - ✅ Robust error handling with detailed logging
    - ✅ Back-pressure control with queue limits
    - ✅ Independent stage monitoring
    - ✅ Graceful failure recovery
    
    Environment Variables:
    - INGEST_ML_CONCURRENCY: Parallel ML workers (default: 3)
    - INGEST_BATCH_SIZE: Images per ML batch (default: 32) 
    - INGEST_QUEUE_SIZE: Inter-stage queue depth (default: 100)
    """
    logger.info(f"Job {job_id}: Starting TRUE concurrent pipeline for {directory_path}")
    
    # Initialize Qdrant client for background task
    qdrant_client = get_qdrant_client()
    
    # Initialize job status with detailed tracking
    job_status[job_id] = {
        "status": "processing",
        "message": "Initializing concurrent pipeline...",
        "progress": 0.0,
        "logs": [],
        "errors": [],
        "exact_duplicates": [],  # Frontend expects this field
        "stage_status": {
            "io_scanner": "starting",
            "cpu_processor": "starting", 
            "gpu_workers": "starting",
            "db_upserter": "starting"
        },
        "counters": {
            "files_found": 0,
            "files_scanned": 0,
            "files_processed": 0,
            "files_embedded": 0,
            "files_upserted": 0,
            "cache_hits": 0,
            "duplicates": 0,
            "errors": 0
        },
        "timing": {
            "start_time": asyncio.get_event_loop().time(),
            "stage_times": {}
        }
    }

    try:
        # Warm up ML service
        logger.info(f"Job {job_id}: Warming up ML service...")
        try:
            async with httpx.AsyncClient(timeout=60.0) as warmup_client:
                warmup_response = await warmup_client.post(f"{ML_SERVICE_URL}/api/v1/warmup")
                warmup_response.raise_for_status()
                warmup_result = warmup_response.json()
                logger.info(f"Job {job_id}: ML warmup result: {warmup_result}")
        except Exception as warmup_error:
            logger.warning(f"Job {job_id}: ML warmup failed: {warmup_error}")

        # Get ML service capabilities
        effective_batch_size = 32  # Conservative default
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                _resp = await client.get(f"{ML_SERVICE_URL}/api/v1/capabilities")
                _resp.raise_for_status()
                service_safe_batch = int(_resp.json().get("safe_clip_batch", 32))
                effective_batch_size = max(1, min(service_safe_batch, ML_BATCH_SIZE, 64))
                logger.info(f"Job {job_id}: Using ML batch size {effective_batch_size} (service reports {service_safe_batch})")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to get ML capabilities: {e}")

        # Discover all image files
        image_files = []
        for ext in SUPPORTED_EXTENSIONS:
            image_files.extend(glob.glob(os.path.join(directory_path, f"**/*{ext}"), recursive=True))
        
        total_files = len(image_files)
        if total_files == 0:
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["message"] = "No images found"
            return

        job_status[job_id]["counters"]["files_found"] = total_files
        logger.info(f"Job {job_id}: Found {total_files} image files")
        job_status[job_id]["logs"].append(f"Found {total_files} images - starting TRUE concurrent pipeline")

        # Configure pipeline queues with back-pressure control
        QUEUE_SIZE = int(os.getenv("INGEST_QUEUE_SIZE", "100"))
        ML_CONCURRENCY = int(os.getenv("INGEST_ML_CONCURRENCY", "3"))
        
        # Inter-stage queues for streaming data
        raw_queue = asyncio.Queue(maxsize=QUEUE_SIZE)      # File paths to process
        ml_queue = asyncio.Queue(maxsize=QUEUE_SIZE)       # Data ready for ML
        db_queue = asyncio.Queue(maxsize=QUEUE_SIZE)       # Points ready for DB
        
        # Shared state with locks
        pipeline_stats = {
            "files_scanned": 0,
            "files_processed": 0, 
            "files_embedded": 0,
            "files_upserted": 0,
            "cache_hits": 0,
            "duplicates": 0,
            "errors": 0
        }
        stats_lock = asyncio.Lock()
        
        # Error aggregation
        pipeline_errors = []
        error_lock = asyncio.Lock()

        async def update_progress():
            """Update job progress based on pipeline stats"""
            async with stats_lock:
                total_processed = pipeline_stats["files_upserted"] + pipeline_stats["cache_hits"] + pipeline_stats["duplicates"]
                progress = min(100.0, (total_processed / total_files) * 100) if total_files > 0 else 0
                
                job_status[job_id]["progress"] = progress
                job_status[job_id]["counters"].update(pipeline_stats.copy())
                
                if total_processed % 25 == 0 and total_processed > 0:
                    job_status[job_id]["logs"].append(
                        f"Pipeline progress: {total_processed}/{total_files} files ({progress:.1f}%) - "
                        f"Embedded: {pipeline_stats['files_embedded']}, Cached: {pipeline_stats['cache_hits']}, "
                        f"Duplicates: {pipeline_stats['duplicates']}, Errors: {pipeline_stats['errors']}"
                    )

        # ==================== STAGE 1: I/O SCANNER ====================
        async def io_scanner():
            """Stage 1: Scan directory and feed file paths to pipeline"""
            try:
                job_status[job_id]["stage_status"]["io_scanner"] = "running"
                logger.info(f"Job {job_id}: I/O Scanner started")
                
                for file_path in image_files:
                    await raw_queue.put(file_path)
                    
                    async with stats_lock:
                        pipeline_stats["files_scanned"] += 1
                
                # Signal end of files
                await raw_queue.put(None)
                job_status[job_id]["stage_status"]["io_scanner"] = "completed"
                logger.info(f"Job {job_id}: I/O Scanner completed - queued {total_files} files")
                
            except Exception as e:
                job_status[job_id]["stage_status"]["io_scanner"] = "failed"
                logger.error(f"Job {job_id}: I/O Scanner failed: {e}", exc_info=True)
                await raw_queue.put(None)  # Signal end even on failure

        # ==================== STAGE 2: CPU PROCESSOR ====================
        async def cpu_processor():
            """Stage 2: Process files (hash, metadata, duplicate check, cache check)"""
            try:
                job_status[job_id]["stage_status"]["cpu_processor"] = "running"
                logger.info(f"Job {job_id}: CPU Processor started")
                
                while True:
                    file_path = await raw_queue.get()
                    if file_path is None:  # End signal
                        break
                    
                    try:
                        # Compute file hash for deduplication
                        file_hash = await asyncio.to_thread(compute_sha256, file_path)
                        
                        # Check if file already exists in collection
                        duplicate_check = await asyncio.to_thread(
                            qdrant_client.scroll,
                            collection_name=collection_name,
                            scroll_filter=Filter(must=[FieldCondition(key="file_hash", match={"value": file_hash})]),
                            limit=1,
                            with_payload=True,
                            with_vectors=False,
                        )
                        
                        if duplicate_check[0]:
                            # File is a duplicate - store duplicate info for frontend
                            duplicate_info = {
                                "file_path": file_path,
                                "existing_id": duplicate_check[0][0].id,
                                "existing_payload": duplicate_check[0][0].payload
                            }
                            job_status[job_id]["exact_duplicates"].append(duplicate_info)
                            
                            async with stats_lock:
                                pipeline_stats["duplicates"] += 1
                            await update_progress()
                            continue
                        
                        # Check cache
                        cache_key = f"sha256:{file_hash}"
                        cached_result = cache.get(cache_key)
                        
                        if cached_result:
                            # Cache hit - create point directly
                            metadata = await asyncio.to_thread(extract_image_metadata, file_path)
                            thumbnail_base64 = await asyncio.to_thread(create_thumbnail_base64, file_path)
                            
                            point = PointStruct(
                                id=str(uuid.uuid4()),
                                vector=cached_result["embedding"],
                                payload={
                                    "filename": os.path.basename(file_path),
                                    "full_path": file_path,
                                    "file_hash": file_hash,
                                    "caption": cached_result.get("caption", ""),
                                    "thumbnail_base64": thumbnail_base64,
                                    **metadata
                                }
                            )
                            
                            # Send directly to database queue
                            await db_queue.put(("cached_point", point))
                            async with stats_lock:
                                pipeline_stats["cache_hits"] += 1
                            await update_progress()
                            
                        else:
                            # Needs ML processing - offload file read and base64 encoding to thread
                            image_base64 = await asyncio.to_thread(
                                lambda path: base64.b64encode(open(path, 'rb').read()).decode('utf-8'),
                                file_path
                            )
                            ml_item = {
                                "unique_id": file_hash,
                                "image_base64": image_base64,
                                "filename": os.path.basename(file_path),
                                "full_path": file_path,
                                "file_hash": file_hash
                            }
                            await ml_queue.put(ml_item)
                            async with stats_lock:
                                pipeline_stats["files_processed"] += 1
                    
                    except Exception as e:
                        async with error_lock:
                            pipeline_errors.append(f"CPU processing failed for {file_path}: {e}")
                        async with stats_lock:
                            pipeline_stats["errors"] += 1
                        logger.error(f"Job {job_id}: CPU processing failed for {file_path}: {e}")

                # Signal end to ML workers
                for _ in range(ML_CONCURRENCY):
                    await ml_queue.put(None)
                
                job_status[job_id]["stage_status"]["cpu_processor"] = "completed"
                logger.info(f"Job {job_id}: CPU Processor completed")
                
            except Exception as e:
                job_status[job_id]["stage_status"]["cpu_processor"] = "failed"
                logger.error(f"Job {job_id}: CPU Processor failed: {e}", exc_info=True)

        # ==================== STAGE 3: GPU WORKERS ====================
        async def gpu_worker(worker_id: int):
            """Stage 3: ML processing worker"""
            try:
                logger.info(f"Job {job_id}: GPU Worker {worker_id} started")
                while True:
                    # Collect up to effective_batch_size items
                    batch = []
                    for _ in range(effective_batch_size):
                        item = await ml_queue.get()
                        if item is None:
                            # Re-enqueue sentinel for other workers and exit
                            await ml_queue.put(None)
                            break
                        batch.append(item)
                    if not batch:
                        # No more work to process
                        break
                    try:
                        logger.info(f"Job {job_id}: Worker {worker_id} processing batch of {len(batch)}")
                        ml_results = await send_batch_to_ml_service(batch)
                        # Build points and cache results
                        for ml_result, src_item in zip(ml_results, batch):
                            if ml_result.get("error"):
                                async with error_lock:
                                    pipeline_errors.append(
                                        f"ML processing failed for {src_item['full_path']}: {ml_result['error']}"
                                    )
                                async with stats_lock:
                                    pipeline_stats["errors"] += 1
                                continue
                            # Cache result for future use
                            cache.set(
                                f"sha256:{ml_result['unique_id']}",
                                {"embedding": ml_result["embedding"], "caption": ml_result.get("caption", "")}   
                            )
                            # Extract metadata and create point
                            metadata = await asyncio.to_thread(extract_image_metadata, src_item["full_path"])
                            thumbnail_base64 = await asyncio.to_thread(create_thumbnail_base64, src_item["full_path"])
                            point = PointStruct(
                                id=str(uuid.uuid4()),
                                vector=ml_result["embedding"],
                                payload={
                                    "filename": src_item["filename"],
                                    "full_path": src_item["full_path"],
                                    "file_hash": src_item["file_hash"],
                                    "caption": ml_result.get("caption", ""),
                                    "thumbnail_base64": thumbnail_base64,
                                    **metadata,
                                }
                            )
                            await db_queue.put(("ml_point", point))
                            async with stats_lock:
                                pipeline_stats["files_embedded"] += 1
                        logger.info(f"Job {job_id}: Worker {worker_id} completed batch of {len(batch)}")
                    except Exception as e:
                        async with error_lock:
                            pipeline_errors.append(f"GPU Worker {worker_id} failed: {e}")
                        async with stats_lock:
                            pipeline_stats["errors"] += len(batch)
                        logger.error(
                            f"Job {job_id}: GPU Worker {worker_id} batch failed: {e}",
                            exc_info=True
                        )
                logger.info(f"Job {job_id}: GPU Worker {worker_id} completed")
            except Exception as e:
                logger.error(f"Job {job_id}: GPU Worker {worker_id} failed: {e}", exc_info=True)
        
        # ==================== STAGE 4: DATABASE UPSERTER ====================
        async def database_upserter():
            """Stage 4: Upsert points to Qdrant database"""
            try:
                job_status[job_id]["stage_status"]["db_upserter"] = "running"
                logger.info(f"Job {job_id}: Database Upserter started")
                
                batch_points = []
                UPSERT_BATCH_SIZE = 32
                active_workers = ML_CONCURRENCY
                timeout_count = 0
                MAX_TIMEOUTS = 6  # Max 60 seconds of timeouts before giving up
                
                while active_workers > 0:
                    try:
                        item = await asyncio.wait_for(db_queue.get(), timeout=10.0)
                        timeout_count = 0  # Reset timeout counter on successful receive
                        
                        if item is None:  # Worker finished signal
                            active_workers -= 1
                            logger.info(f"Job {job_id}: Database upserter received end signal, {active_workers} workers remaining")
                            continue
                        
                        item_type, point = item
                        batch_points.append(point)
                        
                        # Upsert when batch is full or timeout
                        if len(batch_points) >= UPSERT_BATCH_SIZE:
                            await asyncio.to_thread(
                                qdrant_client.upsert,
                                collection_name=collection_name,
                                points=batch_points
                            )
                            
                            async with stats_lock:
                                pipeline_stats["files_upserted"] += len(batch_points)
                            await update_progress()
                            
                            logger.info(f"Job {job_id}: Upserted batch of {len(batch_points)} points")
                            batch_points = []
                    
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        logger.info(f"Job {job_id}: Database upserter timeout {timeout_count}/{MAX_TIMEOUTS}, active_workers={active_workers}")
                        
                        # Check if we've timed out too many times (safety valve)
                        if timeout_count >= MAX_TIMEOUTS:
                            logger.warning(f"Job {job_id}: Database upserter giving up after {MAX_TIMEOUTS} timeouts")
                            break
                        
                        # Process remaining points on timeout
                        if batch_points:
                            await asyncio.to_thread(
                                qdrant_client.upsert,
                                collection_name=collection_name,
                                points=batch_points
                            )
                            
                            async with stats_lock:
                                pipeline_stats["files_upserted"] += len(batch_points)
                            await update_progress()
                            
                            logger.info(f"Job {job_id}: Upserted timeout batch of {len(batch_points)} points")
                            batch_points = []
                
                # Upsert any remaining points
                if batch_points:
                    await asyncio.to_thread(
                        qdrant_client.upsert,
                        collection_name=collection_name,
                        points=batch_points
                    )
                    
                    async with stats_lock:
                        pipeline_stats["files_upserted"] += len(batch_points)
                    await update_progress()
                    
                    logger.info(f"Job {job_id}: Upserted final batch of {len(batch_points)} points")
                
                job_status[job_id]["stage_status"]["db_upserter"] = "completed"
                logger.info(f"Job {job_id}: Database Upserter completed")
                
            except Exception as e:
                job_status[job_id]["stage_status"]["db_upserter"] = "failed"
                logger.error(f"Job {job_id}: Database Upserter failed: {e}", exc_info=True)

        # ==================== START CONCURRENT PIPELINE ====================
        logger.info(f"Job {job_id}: Starting all pipeline stages concurrently...")
        
        # Start all stages concurrently
        tasks = [
            asyncio.create_task(io_scanner()),
            asyncio.create_task(cpu_processor()),
            *[asyncio.create_task(gpu_worker(i)) for i in range(ML_CONCURRENCY)],
            asyncio.create_task(database_upserter())
        ]
        
        # Signal end to database when all GPU workers finish
        async def signal_db_end():
            # Wait for all GPU workers to finish
            gpu_tasks = tasks[2:2+ML_CONCURRENCY]
            await asyncio.gather(*gpu_tasks, return_exceptions=True)
            logger.info(f"Job {job_id}: All GPU workers completed, signaling database upserter to finish")
            # Signal database to finish
            for i in range(ML_CONCURRENCY):
                await db_queue.put(None)
                logger.info(f"Job {job_id}: Sent end signal {i+1}/{ML_CONCURRENCY} to database upserter")
        
        tasks.append(asyncio.create_task(signal_db_end()))
        
        # Wait for all stages to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for stage failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Job {job_id}: Pipeline stage {i} failed: {result}")

        # Cool down ML service
        try:
            async with httpx.AsyncClient(timeout=30.0) as cooldown_client:
                cooldown_response = await cooldown_client.post(f"{ML_SERVICE_URL}/api/v1/cooldown")
                cooldown_response.raise_for_status()
                logger.info(f"Job {job_id}: ML service cooled down")
        except Exception as cooldown_error:
            logger.warning(f"Job {job_id}: ML cooldown failed: {cooldown_error}")

        # Final status update
        final_stats = pipeline_stats.copy()
        total_processed = final_stats["files_upserted"] + final_stats["cache_hits"] + final_stats["duplicates"]
        
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["message"] = (
            f"Pipeline completed: {total_processed}/{total_files} files processed "
            f"({final_stats['files_embedded']} embedded, {final_stats['cache_hits']} cached, "
            f"{final_stats['duplicates']} duplicates, {final_stats['errors']} errors)"
        )
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["errors"] = pipeline_errors
        
        elapsed_time = asyncio.get_event_loop().time() - job_status[job_id]["timing"]["start_time"]
        job_status[job_id]["timing"]["total_time"] = elapsed_time
        
        logger.info(f"Job {job_id} completed in {elapsed_time:.1f}s: {job_status[job_id]['message']}")

    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["message"] = f"Pipeline failed: {str(e)}"
        logger.error(f"Job {job_id}: Pipeline failed: {e}", exc_info=True)
        raise

async def process_and_cleanup_directory(job_id: str, directory_path: str, collection_name: str):
    """A wrapper task that runs ingestion and then cleans up the temporary directory."""
    try:
        await process_directory(job_id, directory_path, collection_name)
    finally:
        logger.info(f"Cleaning up temporary directory: {directory_path}")
        try:
            shutil.rmtree(directory_path)
            logger.info(f"Successfully removed temporary directory: {directory_path}")
        except Exception as e:
            logger.error(f"Failed to remove temporary directory {directory_path}: {e}")

@router.post("/", status_code=202)
async def schedule_ingestion(
    payload: IngestRequest,
    background_tasks: BackgroundTasks,
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
):
    """
    Schedules a new ingestion pipeline run for a given directory.
    This is the primary endpoint for starting a new import/scan job.
    """
    # --- Readiness Check ---
    if not app_state.is_ready_for_ingestion:
        logger.warning(
            "Rejecting ingestion request: Service is not ready. "
            "ML service capabilities have not been successfully fetched."
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Service is not ready for ingestion. This usually means it cannot "
                "connect to the ML inference service to determine safe batch sizes. "
                "Please check the ML service logs and restart the ingestion service."
            ),
        )

    # Use the globally active collection
    collection_name = get_active_collection.__wrapped__()

    if not collection_name:
        raise HTTPException(
            status_code=500,
            detail="No active collection found. Please configure a collection before starting ingestion."
        )

    if not os.path.isdir(payload.directory_path):
        raise HTTPException(status_code=400, detail="Directory not found.")

    job_id = await pipeline_manager.start_pipeline(
        directory_path=payload.directory_path,
        collection_name=collection_name,
        background_tasks=background_tasks,
        qdrant_client=qdrant_client
    )
    return JobResponse(job_id=job_id, status="started", message="Ingestion job started successfully.")
