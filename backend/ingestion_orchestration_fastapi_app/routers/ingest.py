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
from qdrant_client.http.models import PointStruct
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

async def send_batch_to_ml_service(batch_images: List[Dict]) -> List[Dict]:
    """Send a batch of images to the ML service for processing.

    This helper automatically chooses the optimal transport:
    • JSON + Base64 (legacy)
    • multipart/form-data with loss-less PNG buffers (when USE_MULTIPART_UPLOAD=1)
    """
    if USE_MULTIPART_UPLOAD:
        # --- Multipart implementation -------------------------------------
        files_payload = []
        for item in batch_images:
            try:
                img_path = item["file_path"] if "file_path" in item else item["full_path"]
                unique_id = item["unique_id"]
                filename_original = item.get("filename") or os.path.basename(img_path)

                # Decode → RGB and re-encode as PNG (loss-less, reasonably small)
                if filename_original.lower().endswith(".dng"):
                    try:
                        with rawpy.imread(img_path) as raw:
                            rgb = raw.postprocess(use_camera_wb=True)
                        pil_img = Image.fromarray(rgb).convert("RGB")
                    except Exception as e:
                        logger.error(f"rawpy failed for {img_path}: {e}")
                        raise
                else:
                    pil_img = Image.open(img_path).convert("RGB")

                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                buf.seek(0)
                combined_name = f"{unique_id}__{filename_original}.png"
                files_payload.append(("files", (combined_name, buf.read(), "image/png")))
            except Exception as e:
                logger.error(f"Failed to prepare image {img_path} for multipart upload: {e}")

        async with httpx.AsyncClient(timeout=300.0) as client:  # 5-minute timeout
            try:
                response = await client.post(
                    f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption_multipart",
                    files=files_payload,
                )
                response.raise_for_status()
                return response.json().get("results", [])
            except Exception as e:
                logger.error(f"Error calling ML service (multipart): {e}")
                raise

    # --- Legacy JSON path --------------------------------------------------
    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
                json={"images": batch_images}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Error calling ML service: {e}")
            raise

async def process_directory(job_id: str, directory_path: str, collection_name: str):
    """Background task to process all images in a directory."""
    try:
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
        
        processed = 0
        cached_files = 0
        batch_for_ml = []
        points_for_qdrant = []
        
        for i, image_path in enumerate(image_files):
            try:
                # Compute file hash for deduplication
                file_hash = await asyncio.to_thread(compute_sha256, image_path)
                cache_key = f"sha256:{file_hash}"

                # Check if file already exists in the collection
                duplicate_check = qdrant_client.scroll(
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
                
                # Process ML batch when it's full or we're at the end
                if len(batch_for_ml) >= ML_BATCH_SIZE or i == len(image_files) - 1:
                    if batch_for_ml:
                        job_status[job_id]["message"] = f"Processing ML batch of {len(batch_for_ml)} images"
                        job_status[job_id]["logs"].append(f"Processing ML batch of {len(batch_for_ml)} images")
                        
                        # Send batch to ML service
                        ml_results = await send_batch_to_ml_service(batch_for_ml)
                        
                        # Process ML results
                        for ml_result, batch_item in zip(ml_results, batch_for_ml):
                            if ml_result.get("error"):
                                error_msg = f"ML processing error for {batch_item['filename']}: {ml_result['error']}"
                                job_status[job_id]["errors"].append(error_msg)
                                job_status[job_id]["logs"].append(f"ERROR: {error_msg}")
                                logger.error(error_msg)
                                continue
                            
                            # Cache the ML result
                            cache_data = {
                                "embedding": ml_result["embedding"],
                                "caption": ml_result.get("caption", "")
                            }
                            cache.set(f"sha256:{ml_result['unique_id']}", cache_data)
                            
                            # Extract metadata and create Qdrant point
                            metadata = await asyncio.to_thread(extract_image_metadata, batch_item["full_path"])
                            
                            # Create thumbnail for fast display
                            thumbnail_base64 = await asyncio.to_thread(create_thumbnail_base64, batch_item["full_path"])
                            
                            # FIX: Generate UUID for point ID instead of using SHA256 hash
                            point_id = str(uuid.uuid4())
                            
                            point = PointStruct(
                                id=point_id,  # Use UUID instead of file_hash
                                vector=ml_result["embedding"],
                                payload={
                                    "filename": batch_item["filename"],
                                    "full_path": batch_item["full_path"],
                                    "file_hash": ml_result["unique_id"],
                                    "caption": ml_result.get("caption", ""),
                                    "thumbnail_base64": thumbnail_base64,
                                    **metadata
                                }
                            )
                            points_for_qdrant.append(point)
                        
                        batch_for_ml = []
                
                # Upsert to Qdrant when batch is full
                if len(points_for_qdrant) >= QDRANT_BATCH_SIZE:
                    job_status[job_id]["message"] = f"Storing {len(points_for_qdrant)} points to Qdrant"
                    job_status[job_id]["logs"].append(f"Storing {len(points_for_qdrant)} points to database")
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=points_for_qdrant
                    )
                    processed += len(points_for_qdrant)
                    points_for_qdrant = []
                
                # Update progress
                progress = ((i + 1) / total_files) * 100
                job_status[job_id]["progress"] = progress
                job_status[job_id]["processed_files"] = processed
                job_status[job_id]["cached_files"] = cached_files
                job_status[job_id]["message"] = f"Progress: {progress:.1f}% ({processed + cached_files}/{total_files} files)"
                
                # Add periodic log updates
                if (i + 1) % 10 == 0 or i == len(image_files) - 1:
                    job_status[job_id]["logs"].append(f"Processed {i + 1}/{total_files} files ({progress:.1f}%)")
                
            except Exception as e:
                error_msg = f"Error processing {image_path}: {str(e)}"
                job_status[job_id]["errors"].append(error_msg)
                job_status[job_id]["logs"].append(f"ERROR: {error_msg}")
                logger.error(f"Job {job_id}: {error_msg}")
        
        # Upsert any remaining points
        if points_for_qdrant:
            job_status[job_id]["message"] = f"Storing final {len(points_for_qdrant)} points to Qdrant"
            job_status[job_id]["logs"].append(f"Storing final {len(points_for_qdrant)} points to database")
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points_for_qdrant
            )
            processed += len(points_for_qdrant)
        
        # Complete the job
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["processed_files"] = processed
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
        logger.info(f"Job {job_id} completed successfully: {success_msg}")
        
    except Exception as e:
        job_status[job_id]["status"] = "failed"
        job_status[job_id]["message"] = f"Job failed: {str(e)}"
        job_status[job_id]["logs"].append(f"❌ Job failed: {str(e)}")
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
