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
                "unique_id": item["file_path"],
                "image_base64": item["image_base64"],
                "filename": item["filename"]
            }
            for item in batch_items
        ]
    }
    # Dynamic timeout based on batch size: 30s base + 2s per image
    timeout_seconds = max(30.0, 30.0 + (len(batch_items) * 2.0))
    
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(
            f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
            json=batch_data
        )
        response.raise_for_status()
        return response.json()["results"]

async def process_directory(job_id: str, directory_path: str, collection_name: str):
    """Background task to process all images in a directory."""
    try:
        # ---------- BLIP Model Warmup ----------
        logger.info(f"Job {job_id}: Warming up ML service for ingestion...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as warmup_client:
                warmup_response = await warmup_client.post(f"{ML_SERVICE_URL}/api/v1/warmup")
                warmup_response.raise_for_status()
                warmup_result = warmup_response.json()
                logger.info(f"Job {job_id}: ML warmup result: {warmup_result}")
        except Exception as warmup_error:
            logger.warning(f"Job {job_id}: ML warmup failed (continuing anyway): {warmup_error}")
        
        # Update job status
        job_status[job_id]["status"] = "processing"
        job_status[job_id]["message"] = "Scanning directory for images"
        job_status[job_id]["logs"] = ["Starting directory scan..."]
        
        # Get list of image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.dng'}
        image_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    image_files.append(os.path.join(root, file))
        
        total_files = len(image_files)
        job_status[job_id]["total_files"] = total_files
        job_status[job_id]["message"] = f"Found {total_files} image files to process"
        job_status[job_id]["logs"].append(f"Found {total_files} image files")
        
        if total_files == 0:
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["message"] = "No image files found in directory"
            job_status[job_id]["logs"].append("No image files found - job completed")
            return

        # Get Qdrant client
        from ..dependencies import app_state
        qdrant_client = app_state.qdrant_client
        if not qdrant_client:
            raise RuntimeError("Qdrant client not initialized")
        
        # ------------------------------------------------------------------
        # Dynamic ML batch sizing – re-query ML service capabilities to guard
        # against mis-reported values and operator mis-configuration.
        # We clamp to a hard maximum of 512 so a single bad response cannot
        # overwhelm GPU memory.
        # ------------------------------------------------------------------
        effective_ml_batch = ML_BATCH_SIZE  # fallback
        try:
            async with httpx.AsyncClient(timeout=5.0) as _client:
                _resp = await _client.get(f"{ML_SERVICE_URL}/api/v1/capabilities")
                _resp.raise_for_status()
                service_safe_batch = int(_resp.json().get("safe_clip_batch", 1))
                effective_ml_batch = max(1, min(service_safe_batch, ML_BATCH_SIZE, 512))
                logger.info(
                    "[ingest] Using effective ML batch size %s (service_safe=%s, env=%s)",
                    effective_ml_batch, service_safe_batch, ML_BATCH_SIZE,
                )
        except Exception as exc:
            logger.warning("[ingest] Could not fetch ML capabilities – defaulting to env batch size (%s): %s", ML_BATCH_SIZE, exc)

        # If operators want to limit the ingestion batch for any reason (e.g. to
        # avoid saturating the ML service while benchmarking), they can set
        # INGEST_BLIP_CAP.  When the variable is *not* set we will honour the
        # full safe batch size reported by the ML service instead of falling
        # back to an arbitrary default of 32.

        _ingest_blip_cap_env = os.getenv("INGEST_BLIP_CAP")
        if _ingest_blip_cap_env is not None and _ingest_blip_cap_env.strip():
            try:
                INGEST_BLIP_CAP = int(_ingest_blip_cap_env)
                effective_ml_opt = max(1, min(effective_ml_batch, INGEST_BLIP_CAP))
            except ValueError:
                logger.warning("Invalid INGEST_BLIP_CAP value '%s' – ignoring", _ingest_blip_cap_env)
                INGEST_BLIP_CAP = None
                effective_ml_opt = effective_ml_batch
        else:
            # No cap requested – use the effective batch reported by the ML service
            INGEST_BLIP_CAP = None
            effective_ml_opt = effective_ml_batch

        logger.info("[ingest] Final ML batch size per request: %s (cap=%s)", effective_ml_opt, INGEST_BLIP_CAP or "none")

        processed = 0  # Embeddings actually stored
        scanned = 0    # Files that have been discovered & analysed (hash, cache, etc.)
        cached_files = 0
        batch_for_ml: list[dict] = []
        points_for_qdrant = []  # Cached-image points (producer handles) 

        tasks: list[asyncio.Task] = []  # ML worker tasks

        # ---------------------------------------------------------------------------
        # Concurrency controls -------------------------------------------------------
        # ---------------------------------------------------------------------------
        # Ingestion can overlap disk IO (producer) with GPU inference (consumer)
        # by firing several ML requests in parallel.  We expose a simple knob so
        # operators can tune the number of in-flight requests without changing code.
        #
        #   INGEST_ML_MAX_INFLIGHT   – Maximum parallel batches hitting the ML
        #                               inference service.  Defaults to 2 which
        #                               gives good utilisation on a single-GPU host
        #                               without overwhelming VRAM.
        # ---------------------------------------------------------------------------

        MAX_INFLIGHT_ML_REQUESTS: int = int(os.getenv("INGEST_ML_MAX_INFLIGHT", "2"))

        # Global semaphore limiting concurrent ML batch workers.
        ml_semaphore: asyncio.Semaphore = asyncio.Semaphore(MAX_INFLIGHT_ML_REQUESTS)

        # Async lock used by background workers to serialise updates to the shared
        # ``job_status`` structure so progress counters and logs do not clobber each
        # other.
        status_lock: asyncio.Lock = asyncio.Lock()

        # -------------------------------------------------------------
        # Internal async worker – posts one batch to the ML service and
        # upserts the resulting points.  Runs under a semaphore so only
        # MAX_INFLIGHT_ML_REQUESTS batches hit the GPU host at once.
        # -------------------------------------------------------------
        async def ml_batch_worker(batch_items: list[dict]):
            """Worker that sends one image batch to the ML service and then stores
            the resulting vectors in Qdrant.

            The semaphore only wraps the **GPU/HTTP** phase so that PNG upload
            and inference are limited to *MAX_INFLIGHT_ML_REQUESTS* concurrent
            batches, while the (much slower) Qdrant upsert runs outside the
            semaphore – allowing the next batch to start uploading as soon as
            the previous one leaves the GPU.
            """

            nonlocal processed, cached_files, scanned

            # ---------------- GPU / HTTP phase ----------------
            try:
                async with ml_semaphore:
                    ml_results = await send_batch_to_ml_service(batch_items)
            except Exception as exc:
                error_msg = f"ML batch failed – size={len(batch_items)} images – {exc}"
                async with status_lock:
                    job_status[job_id]["errors"].append(error_msg)
                    job_status[job_id]["logs"].append(f"ERROR: {error_msg}")
                logger.error(error_msg, exc_info=True)
                return

            # ---------------- Build Qdrant points --------------
            points: list[PointStruct] = []
            for ml_result, src in zip(ml_results, batch_items):
                if ml_result.get("error"):
                    err = f"ML error for {src['filename']}: {ml_result['error']}"
                    async with status_lock:
                        job_status[job_id]["errors"].append(err)
                        job_status[job_id]["logs"].append(f"ERROR: {err}")
                    continue

                # Cache embedding to skip future GPU work on identical file
                cache.set(
                    f"sha256:{ml_result['unique_id']}",
                    {"embedding": ml_result["embedding"], "caption": ml_result.get("caption", "")},
                )

                metadata = await asyncio.to_thread(extract_image_metadata, src["full_path"])
                thumb_b64 = await asyncio.to_thread(create_thumbnail_base64, src["full_path"])

                point_id = str(uuid.uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=ml_result["embedding"],
                        payload={
                            "filename": src["filename"],
                            "full_path": src["full_path"],
                            "file_hash": ml_result["unique_id"],
                            "caption": ml_result.get("caption", ""),
                            "thumbnail_base64": thumb_b64,
                            **metadata,
                        },
                    )
                )

            if not points:
                return

            # ---------------- Qdrant upsert (CPU / network) ----
            await asyncio.to_thread(
                qdrant_client.upsert,
                collection_name=collection_name,
                points=points,
            )

            # Update global counters / logs
            async with status_lock:
                nonlocal processed
                processed += len(points)
                job_status[job_id]["processed_files"] = processed
                job_status[job_id]["logs"].append(
                    f"Upserted {len(points)} embeddings (total {processed})"
                )

        for i, image_path in enumerate(image_files):
            try:
                # Compute file hash for deduplication
                file_hash = await asyncio.to_thread(compute_sha256, image_path)
                cache_key = f"sha256:{file_hash}"

                # Check if file already exists in the collection
                duplicate_check = await asyncio.to_thread(
                    qdrant_client.scroll,
                    collection_name=collection_name,
                    scroll_filter=Filter(must=[FieldCondition(key="file_hash", match={"value": file_hash})]),
                    limit=1,
                    with_payload=True,
                    with_vectors=False,
                )
                if duplicate_check[0]:
                    existing_point = duplicate_check[0][0]
                    job_status[job_id]["exact_duplicates"].append({
                        "file_path": image_path,
                        "existing_id": existing_point.id,
                        "existing_payload": existing_point.payload
                    })
                    continue

                # Check if we've already processed this image
                cached_result = cache.get(cache_key)
                if cached_result:
                    # Use cached result
                    cached_files += 1
                    
                    # Create Qdrant point from cached data
                    metadata = await asyncio.to_thread(extract_image_metadata, image_path)
                    
                    # Create thumbnail for fast display
                    thumbnail_base64 = await asyncio.to_thread(create_thumbnail_base64, image_path)
                    
                    # FIX: Generate UUID for point ID instead of using SHA256 hash
                    point_id = str(uuid.uuid4())
                    
                    point = PointStruct(
                        id=point_id,  # Use UUID instead of file_hash
                        vector=cached_result["embedding"],
                        payload={
                            "filename": os.path.basename(image_path),
                            "full_path": image_path,
                            "file_hash": file_hash,
                            "caption": cached_result.get("caption", ""),
                            "thumbnail_base64": thumbnail_base64,
                            **metadata
                        }
                    )
                    points_for_qdrant.append(point)
                    
                else:
                    # Add to ML processing batch
                    if USE_MULTIPART_UPLOAD:
                        batch_for_ml.append({
                            "unique_id": file_hash,
                            "file_path": image_path,
                            "filename": os.path.basename(image_path),
                            "full_path": image_path
                        })
                    else:
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        batch_for_ml.append({
                            "unique_id": file_hash,
                            "image_base64": base64.b64encode(image_data).decode('utf-8'),
                            "filename": os.path.basename(image_path),
                            "full_path": image_path
                        })
                
                # Increment scanned counter and expose via status
                scanned += 1

                # Process ML batch when it's full or we're at the end
                if len(batch_for_ml) >= effective_ml_opt or i == len(image_files) - 1:
                    if batch_for_ml:
                        # Schedule worker and go on scanning immediately
                        tasks.append(asyncio.create_task(ml_batch_worker(batch_for_ml.copy())))
                        batch_for_ml = []
                
                # Update progress (based on *scanned* files so UI moves steadily)
                done = processed + cached_files
                progress = (done / total_files) * 100
                job_status[job_id]["progress"] = progress
                job_status[job_id]["scanned_files"] = scanned
                job_status[job_id]["processed_files"] = processed
                job_status[job_id]["cached_files"] = cached_files
                job_status[job_id]["message"] = (
                    f"Progress: {progress:.1f}% (scanned {scanned}/{total_files}, "
                    f"stored {processed + cached_files})"
                )
                
                # Add periodic log updates
                if (i + 1) % 10 == 0 or i == len(image_files) - 1:
                    job_status[job_id]["logs"].append(
                        f"Scanned {scanned}/{total_files} files ({progress:.1f}%)"
                    )
                
            except Exception as e:
                error_msg = f"Error processing {image_path}: {str(e)}"
                job_status[job_id]["errors"].append(error_msg)
                job_status[job_id]["logs"].append(f"ERROR: {error_msg}")
                logger.error(f"Job {job_id}: {error_msg}")
        
        # Await outstanding ML workers
        if tasks:
            await asyncio.gather(*tasks)

        # Upsert any remaining points from cached-image path
        if points_for_qdrant:
            job_status[job_id]["message"] = f"Storing final {len(points_for_qdrant)} points to Qdrant"
            job_status[job_id]["logs"].append(f"Storing final {len(points_for_qdrant)} points to database")
            await asyncio.to_thread(
                qdrant_client.upsert,
                collection_name=collection_name,
                points=points_for_qdrant,
            )
            processed += len(points_for_qdrant)
        
        # Complete the job
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["processed_files"] = processed
        job_status[job_id]["scanned_files"] = scanned
        job_status[job_id]["cached_files"] = cached_files
        job_status[job_id]["progress"] = 100.0
        
        success_msg = f"Completed processing {processed + cached_files}/{total_files} files"
        if cached_files > 0:
            success_msg += f" ({cached_files} from cache)"
        if job_status[job_id]["errors"]:
            success_msg += f" with {len(job_status[job_id]['errors'])} errors"
        if job_status[job_id]["exact_duplicates"]:
            success_msg += f" - {len(job_status[job_id]['exact_duplicates'])} duplicates skipped"
        
        job_status[job_id]["message"] = success_msg
        job_status[job_id]["logs"].append(f"✅ {success_msg}")
        
        # ---------- BLIP Model Cooldown ----------
        logger.info(f"Job {job_id}: Cooling down ML service after ingestion...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as cooldown_client:
                cooldown_response = await cooldown_client.post(f"{ML_SERVICE_URL}/api/v1/cooldown")
                cooldown_response.raise_for_status()
                cooldown_result = cooldown_response.json()
                logger.info(f"Job {job_id}: ML cooldown result: {cooldown_result}")
        except Exception as cooldown_error:
            logger.warning(f"Job {job_id}: ML cooldown failed: {cooldown_error}")
        
        logger.info(f"Job {job_id} completed successfully: {success_msg}")
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["message"] = f"Job failed: {str(e)}"
        job_status[job_id]["logs"].append(f"❌ Job failed: {str(e)}")
        
        # Cool down even on failure to free GPU memory
        try:
            async with httpx.AsyncClient(timeout=30.0) as cooldown_client:
                await cooldown_client.post(f"{ML_SERVICE_URL}/api/v1/cooldown")
        except Exception:
            pass  # Ignore cooldown errors during failure cleanup
        
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
