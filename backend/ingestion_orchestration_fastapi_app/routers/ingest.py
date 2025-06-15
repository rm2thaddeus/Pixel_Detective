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

from ..dependencies import get_qdrant_client, get_active_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])

# In-memory job tracking (in production, use Redis or database)
job_status = {}

# Configuration
ML_SERVICE_URL = os.getenv("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
ML_BATCH_SIZE = int(os.getenv("ML_INFERENCE_BATCH_SIZE", "25"))
QDRANT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "32"))

# Initialize disk cache for deduplication
cache = diskcache.Cache('.diskcache')

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
        "logs": []  # Add logs array for frontend
    }
    
    # Start background processing
    background_tasks.add_task(process_directory, job_id, request.directory_path, collection_name)
    
    logger.info(f"Started ingestion job {job_id} for directory: {request.directory_path}")
    
    return JobResponse(
        job_id=job_id,
        status="started",
        message=f"Ingestion job started for directory: {request.directory_path}"
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
        "directory_path": temp_dir, # The temp dir is the source
        "collection_name": collection_name,
        "processed_files": 0,
        "total_files": len(files),
        "errors": [],
        "cached_files": 0,
        "progress": 0.0,
        "logs": ["Starting ingestion from uploaded files..."]
    }
    
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

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """Extract metadata from image file."""
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            metadata = {
                "width": width,
                "height": height,
                "format": img.format,
                "mode": img.mode
            }
            
            # Extract EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        metadata[f"exif_{tag}"] = str(value)
            
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
    """Send a batch of images to the ML service for processing."""
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
