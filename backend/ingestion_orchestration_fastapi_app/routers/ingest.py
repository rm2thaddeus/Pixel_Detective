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

from ..dependencies import get_qdrant_client, get_active_collection

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
    collection_name: str = Depends(get_active_collection)
):
    """
    Start ingestion of images from a directory into the active collection.
    Returns a job ID for tracking progress.
    """
    # Enhanced logging for debugging 400 errors
    logger.info(f"Received ingestion request: directory_path='{request.directory_path}', collection='{collection_name}'")
    
    # Validate directory exists
    if not request.directory_path:
        logger.error("Empty directory path provided")
        raise HTTPException(status_code=400, detail="Directory path cannot be empty")
    
    if not os.path.exists(request.directory_path):
        logger.error(f"Directory not found: {request.directory_path}")
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.directory_path}")
    
    if not os.path.isdir(request.directory_path):
        logger.error(f"Path is not a directory: {request.directory_path}")
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.directory_path}")
    
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job status
    job_status[job_id] = {
        "status": "started",
        "message": "Ingestion job started",
        "directory_path": request.directory_path,
        "collection_name": collection_name,
        "processed_files": 0,
        "total_files": 0,
        "errors": [],
        "cached_files": 0,
        "progress": 0.0,
        "logs": [],  # Add logs array for frontend
        "exact_duplicates": []
    }

    # Remember latest job for this collection
    recent_jobs[collection_name] = job_id
    
    # Start background processing
    background_tasks.add_task(process_directory, job_id, request.directory_path, collection_name)
    
    logger.info(f"Started ingestion job {job_id} for directory: {request.directory_path}")
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message=f"Ingestion job started for directory: {request.directory_path}"
    )

@router.post("/scan", response_model=JobResponse)
async def start_ingestion_from_path(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    collection_name: str = Depends(get_active_collection)
):
    """
    Start ingestion of images from a directory path on the server
    into the active collection.
    Returns a job ID for tracking progress.
    """
    logger.info(f"Received ingestion request for server path: directory_path='{request.directory_path}', collection='{collection_name}'")
    
    # Validate directory exists on the server
    if not request.directory_path or not os.path.isabs(request.directory_path):
        logger.error(f"Invalid path provided: {request.directory_path}")
        raise HTTPException(status_code=400, detail="An absolute server path is required.")
    
    if not os.path.exists(request.directory_path):
        logger.error(f"Directory not found on server: {request.directory_path}")
        raise HTTPException(status_code=400, detail=f"Directory not found on server: {request.directory_path}")
    
    if not os.path.isdir(request.directory_path):
        logger.error(f"Path is not a directory: {request.directory_path}")
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.directory_path}")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "started",
        "message": "Ingestion job started",
        "directory_path": request.directory_path,
        "collection_name": collection_name,
        "processed_files": 0,
        "total_files": 0,
        "errors": [],
        "cached_files": 0,
        "progress": 0.0,
        "logs": [],
        "exact_duplicates": []
    }

    recent_jobs[collection_name] = job_id
    
    # Start background processing
    background_tasks.add_task(process_directory, job_id, request.directory_path, collection_name)
    
    logger.info(f"Started ingestion job {job_id} for server directory: {request.directory_path}")
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message=f"Ingestion job started for server directory: {request.directory_path}"
    )

@router.post("/upload", response_model=JobResponse)
async def upload_and_ingest_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    collection_name: str = Depends(get_active_collection)
):
    """
    Accept file uploads, save them to a temporary directory,
    and start the ingestion process.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    # Create a temporary directory to store uploaded files
    temp_dir = tempfile.mkdtemp()
    
    logger.info(f"Created temporary directory for upload: {temp_dir}")

    for file in files:
        try:
            # Sanitize filename to prevent security issues like directory traversal
            sanitized_filename = os.path.basename(file.filename or "unknown_file")
            if not sanitized_filename:
                 logger.warning(f"Skipping file with empty filename.")
                 continue

            file_location = os.path.join(temp_dir, sanitized_filename)
            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            logger.info(f"Saved uploaded file to {file_location}")
        finally:
            file.file.close()
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job status
    job_status[job_id] = {
        "status": "started",
        "message": "Ingestion job started from uploaded files.",
        "directory_path": temp_dir,  # The temp dir is the source
        "collection_name": collection_name,
        "processed_files": 0,
        "total_files": len(files),
        "errors": [],
        "cached_files": 0,
        "progress": 0.0,
        "logs": ["Starting ingestion from uploaded files..."],
        "exact_duplicates": []
    }

    recent_jobs[collection_name] = job_id
    
    # Start background processing on the temporary directory
    # We add another task to clean up the directory after processing
    background_tasks.add_task(process_and_cleanup_directory, job_id, temp_dir, collection_name)
    
    logger.info(f"Started ingestion job {job_id} for uploaded files in temp dir: {temp_dir}")
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message=f"Ingestion job started for {len(files)} uploaded files."
    )

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of an ingestion job."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status[job_id]


@router.get("/recent_jobs")
async def get_recent_jobs():
    """Return the most recent job ID for each collection."""
    return recent_jobs

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
    """Send batch to ML service for embedding and captioning."""
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
    # Dynamic timeout based on batch size: 60s base + 4.5s per image + 30s buffer
    # Based on observed processing times of ~100-105s for 28 images
    timeout_seconds = max(60.0, 60.0 + (len(batch_items) * 4.5) + 30.0)
    
    logger.info(f"Sending batch of {len(batch_items)} images to ML service with timeout {timeout_seconds:.1f}s")
    
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
            json=batch_data
        )
        response.raise_for_status()
        results = response.json()["results"]
        logger.info(f"Successfully received ML results for {len(results)} images")
        return results

async def process_directory(job_id: str, directory_path: str, collection_name: str):
    """
    High-performance ingestion with concurrent I/O, GPU, and database pipelines.
    
    Architecture:
    [I/O Producer] → gpu_queue → [GPU Processor] → upsert_queue → [DB Upserter]
    
    All three stages run concurrently at maximum capacity:
    - I/O Producer: Processes files in chunks of 50, computes hashes, checks duplicates/cache
    - GPU Processor: Runs 6 concurrent ML batches (61 images each) with semaphore control
    - DB Upserter: Async upserts to Qdrant while next ML batch is processing
    
    Environment Variables for Tuning:
    - INGEST_ML_MAX_INFLIGHT: Max concurrent ML batches (default: 6)
    - INGEST_IO_CHUNK_SIZE: Files processed in parallel per chunk (default: 50)  
    - INGEST_CACHED_BATCH_SIZE: Cached points batched together (default: 200)
    """
    logger.info(f"Job {job_id}: Starting concurrent pipeline ingestion for {directory_path}")
    
    job_status[job_id] = {
        "status": "processing",
        "message": "Starting concurrent pipeline...",
        "progress": 0.0,
        "logs": [],
        "errors": [],
        "scanned_files": 0,
        "processed_files": 0,
        "cached_files": 0,
        "exact_duplicates": []
    }

    try:
        # Warm up ML service first
        logger.info(f"Job {job_id}: Warming up ML service...")
        try:
            async with httpx.AsyncClient(timeout=60.0) as warmup_client:
                warmup_response = await warmup_client.post(f"{ML_SERVICE_URL}/api/v1/warmup")
                warmup_response.raise_for_status()
                warmup_result = warmup_response.json()
                logger.info(f"Job {job_id}: ML warmup result: {warmup_result}")
        except Exception as warmup_error:
            logger.warning(f"Job {job_id}: ML warmup failed: {warmup_error}")

        # Get ML service batch size
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                _resp = await client.get(f"{ML_SERVICE_URL}/api/v1/capabilities")
                _resp.raise_for_status()
                service_safe_batch = int(_resp.json().get("safe_clip_batch", 1))
                effective_ml_batch = max(1, min(service_safe_batch, ML_BATCH_SIZE, 512))
                logger.info(f"Job {job_id}: Using ML batch size {effective_ml_batch} (service reports {service_safe_batch})")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to get ML capabilities: {e}")
            effective_ml_batch = 32

        # Discover all image files
        image_files = []
        for ext in SUPPORTED_EXTENSIONS:
            image_files.extend(glob.glob(os.path.join(directory_path, f"**/*{ext}"), recursive=True))
        
        total_files = len(image_files)
        if total_files == 0:
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["message"] = "No images found"
            return

        logger.info(f"Job {job_id}: Found {total_files} image files")
        job_status[job_id]["logs"].append(f"Starting directory scan... Found {total_files} images")

        # Concurrent pipeline queues and counters (larger for better throughput)
        file_queue = asyncio.Queue(maxsize=500)  # Increased for better I/O buffering
        gpu_queue = asyncio.Queue(maxsize=20)    # Increased for better GPU pipeline depth
        
        # Thread-safe counters
        stats = {
            "scanned": 0,
            "processed": 0, 
            "cached": 0,
            "duplicates": 0,
            "errors": 0
        }
        stats_lock = asyncio.Lock()
        
        # ------------------ I/O PRODUCER STAGE ------------------
        async def io_producer():
            """Stage 1: Scan files, compute hashes, check duplicates"""
            try:
                batch_for_ml = []
                cached_points = []
                
                # Process files in optimized chunks for maximum I/O throughput
                CHUNK_SIZE = int(os.getenv("INGEST_IO_CHUNK_SIZE", "50"))
                for chunk_start in range(0, total_files, CHUNK_SIZE):
                    chunk_end = min(chunk_start + CHUNK_SIZE, total_files)
                    chunk_files = image_files[chunk_start:chunk_end]
                    
                    # Process chunk in parallel
                    chunk_tasks = [
                        asyncio.create_task(process_single_file(file_path, collection_name))
                        for file_path in chunk_files
                    ]
                    
                    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(chunk_results):
                        if isinstance(result, Exception):
                            async with stats_lock:
                                stats["errors"] += 1
                            job_status[job_id]["errors"].append(f"Error processing {chunk_files[i]}: {result}")
                            continue
                            
                        if result["type"] == "duplicate":
                            async with stats_lock:
                                stats["duplicates"] += 1
                            job_status[job_id]["exact_duplicates"].append(result["data"])
                        elif result["type"] == "cached":
                            async with stats_lock:
                                stats["cached"] += 1
                            cached_points.append(result["data"])
                        elif result["type"] == "ml_needed":
                            batch_for_ml.append(result["data"])
                        
                        async with stats_lock:
                            stats["scanned"] += 1
                            progress = (stats["scanned"] / total_files) * 100
                            job_status[job_id]["progress"] = progress
                            job_status[job_id]["scanned_files"] = stats["scanned"]
                            
                            if stats["scanned"] % 50 == 0:
                                job_status[job_id]["logs"].append(
                                    f"Scanned {stats['scanned']}/{total_files} files ({progress:.1f}%)"
                                )
                        
                        # Send batches to GPU queue when ready
                        if len(batch_for_ml) >= effective_ml_batch:
                            await gpu_queue.put(("ml_batch", batch_for_ml.copy()))
                            batch_for_ml = []
                        
                        # Send cached points in larger batches for better DB throughput
                        CACHED_BATCH_SIZE = int(os.getenv("INGEST_CACHED_BATCH_SIZE", "200"))
                        if len(cached_points) >= CACHED_BATCH_SIZE:
                            await gpu_queue.put(("cached_batch", cached_points.copy()))
                            cached_points = []
                
                # Send remaining batches
                if batch_for_ml:
                    await gpu_queue.put(("ml_batch", batch_for_ml))
                if cached_points:
                    await gpu_queue.put(("cached_batch", cached_points))
                    
                # Signal end of I/O
                await gpu_queue.put(("end", None))
                logger.info(f"Job {job_id}: I/O producer finished")
                
            except Exception as e:
                logger.error(f"Job {job_id}: I/O producer failed: {e}", exc_info=True)
                await gpu_queue.put(("error", str(e)))

        async def process_single_file(file_path: str, collection_name: str):
            """Process a single file: hash, duplicate check, cache check"""
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
                    return {
                        "type": "duplicate",
                        "data": {
                            "file_path": file_path,
                            "existing_id": duplicate_check[0][0].id,
                            "existing_payload": duplicate_check[0][0].payload
                        }
                    }
                
                # Check cache
                cache_key = f"sha256:{file_hash}"
                cached_result = cache.get(cache_key)
                
                if cached_result:
                    # Build cached point
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
                    return {"type": "cached", "data": point}
                
                else:
                    # Needs ML processing
                    if USE_MULTIPART_UPLOAD:
                        return {
                            "type": "ml_needed",
                            "data": {
                                "unique_id": file_hash,
                                "file_path": file_path,
                                "filename": os.path.basename(file_path),
                                "full_path": file_path
                            }
                        }
                    else:
                        with open(file_path, 'rb') as f:
                            image_data = f.read()
                        return {
                            "type": "ml_needed", 
                            "data": {
                                "unique_id": file_hash,
                                "image_base64": base64.b64encode(image_data).decode('utf-8'),
                                "filename": os.path.basename(file_path),
                                "full_path": file_path
                            }
                        }
                        
            except Exception as e:
                raise Exception(f"Failed to process {file_path}: {e}")

        # ------------------ GPU PROCESSOR STAGE ------------------
        async def gpu_processor():
            """Stage 2: Process ML batches and forward to database"""
            # Higher concurrency for better GPU utilization (tuned for batch size 61)
            MAX_CONCURRENT_ML = int(os.getenv("INGEST_ML_MAX_INFLIGHT", "6"))
            ml_semaphore = asyncio.Semaphore(MAX_CONCURRENT_ML)
            upsert_queue = asyncio.Queue(maxsize=20)
            
            async def ml_worker(batch_items):
                """Process one ML batch"""
                try:
                    async with ml_semaphore:
                        ml_results = await send_batch_to_ml_service(batch_items)
                    
                    # Build points
                    points = []
                    for ml_result, src in zip(ml_results, batch_items):
                        if ml_result.get("error"):
                            continue
                            
                        # Cache result
                        cache.set(
                            f"sha256:{ml_result['unique_id']}",
                            {"embedding": ml_result["embedding"], "caption": ml_result.get("caption", "")}
                        )
                        
                        metadata = await asyncio.to_thread(extract_image_metadata, src["full_path"])
                        thumb_b64 = await asyncio.to_thread(create_thumbnail_base64, src["full_path"])
                        
                        points.append(PointStruct(
                            id=str(uuid.uuid4()),
                            vector=ml_result["embedding"],
                            payload={
                                "filename": src["filename"],
                                "full_path": src["full_path"],
                                "file_hash": ml_result["unique_id"],
                                "caption": ml_result.get("caption", ""),
                                "thumbnail_base64": thumb_b64,
                                **metadata,
                            }
                        ))
                    
                    if points:
                        await upsert_queue.put(points)
                        
                except Exception as e:
                    logger.error(f"Job {job_id}: ML worker failed: {e}", exc_info=True)
                    job_status[job_id]["errors"].append(f"ML batch failed: {e}")
            
            ml_tasks = []
            
            try:
                while True:
                    item = await gpu_queue.get()
                    item_type, data = item
                    
                    if item_type == "end":
                        break
                    elif item_type == "error":
                        raise Exception(f"I/O producer error: {data}")
                    elif item_type == "ml_batch":
                        # Schedule ML processing
                        task = asyncio.create_task(ml_worker(data))
                        ml_tasks.append(task)
                    elif item_type == "cached_batch":
                        # Forward cached points directly to upsert
                        await upsert_queue.put(data)
                
                # Wait for all ML tasks
                if ml_tasks:
                    await asyncio.gather(*ml_tasks, return_exceptions=True)
                
                # Signal database stage to finish
                await upsert_queue.put("end")
                logger.info(f"Job {job_id}: GPU processor finished")
                
            except Exception as e:
                logger.error(f"Job {job_id}: GPU processor failed: {e}", exc_info=True)
                await upsert_queue.put("error")
            
            # Start database upserter
            return await database_upserter(upsert_queue)

        # ------------------ DATABASE UPSERTER STAGE ------------------
        async def database_upserter(upsert_queue):
            """Stage 3: Upsert points to Qdrant"""
            try:
                while True:
                    points = await upsert_queue.get()
                    
                    if points == "end":
                        break
                    elif points == "error":
                        raise Exception("GPU processor error")
                    
                    # Upsert to Qdrant
                    await asyncio.to_thread(
                        qdrant_client.upsert,
                        collection_name=collection_name,
                        points=points
                    )
                    
                    # Update counters
                    async with stats_lock:
                        stats["processed"] += len(points)
                        job_status[job_id]["processed_files"] = stats["processed"]
                        job_status[job_id]["cached_files"] = stats["cached"]
                        
                        total_done = stats["processed"] + stats["cached"]
                        progress = (total_done / total_files) * 100
                        job_status[job_id]["progress"] = progress
                        job_status[job_id]["logs"].append(
                            f"Upserted {len(points)} embeddings (total {total_done})"
                        )
                
                logger.info(f"Job {job_id}: Database upserter finished")
                
            except Exception as e:
                logger.error(f"Job {job_id}: Database upserter failed: {e}", exc_info=True)
                job_status[job_id]["errors"].append(f"Database upsert failed: {e}")

        # ------------------ RUN CONCURRENT PIPELINE ------------------
        logger.info(f"Job {job_id}: Starting 3-stage concurrent pipeline...")
        
        # Start all stages concurrently
        pipeline_tasks = [
            asyncio.create_task(io_producer()),
            asyncio.create_task(gpu_processor()),
        ]
        
        # Wait for pipeline completion
        await asyncio.gather(*pipeline_tasks, return_exceptions=True)
        
        # Final status update
        total_processed = stats["processed"] + stats["cached"]
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = 100.0
        job_status[job_id]["processed_files"] = stats["processed"]
        job_status[job_id]["cached_files"] = stats["cached"]
        job_status[job_id]["scanned_files"] = stats["scanned"]
        
        success_msg = f"Completed processing {total_processed}/{total_files} files"
        if stats["cached"] > 0:
            success_msg += f" ({stats['cached']} from cache)"
        if stats["errors"] > 0:
            success_msg += f" with {stats['errors']} errors"
        if stats["duplicates"] > 0:
            success_msg += f" - {stats['duplicates']} duplicates skipped"
        
        job_status[job_id]["message"] = success_msg
        job_status[job_id]["logs"].append(f"✅ {success_msg}")
        
        # Cooldown ML service
        try:
            async with httpx.AsyncClient(timeout=30.0) as cooldown_client:
                cooldown_response = await cooldown_client.post(f"{ML_SERVICE_URL}/api/v1/cooldown")
                cooldown_response.raise_for_status()
                logger.info(f"Job {job_id}: ML service cooled down")
        except Exception as cooldown_error:
            logger.warning(f"Job {job_id}: ML cooldown failed: {cooldown_error}")
        
        logger.info(f"Job {job_id} completed: {success_msg}")
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["message"] = f"Pipeline failed: {str(e)}"
        job_status[job_id]["logs"].append(f"❌ Pipeline failed: {str(e)}")
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)

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
