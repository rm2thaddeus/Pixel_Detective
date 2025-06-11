from fastapi import FastAPI, HTTPException, Body, APIRouter
from pydantic import BaseModel
import torch
import clip # openai-clip
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import os
import rawpy # Added for DNG support, ensure it's in requirements if not already
import time
import logging
import numpy as np
import io # For handling bytes as files for PIL
import base64
import tempfile  # Added for DNG temp file handling
from typing import Dict, Any, Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

# Configure basic logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Inference Service")
v1_router = APIRouter(prefix="/api/v1") # Define v1 router

# --- Configuration ---
CLIP_MODEL_NAME_CONFIG = os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")
BLIP_MODEL_NAME_CONFIG = os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")
DEVICE_PREFERENCE = os.environ.get("DEVICE_PREFERENCE", "cuda")

# --- Global Thread Pool Executor ---
# Use a thread pool for CPU-bound tasks like image decoding to avoid blocking the asyncio event loop
cpu_executor = ThreadPoolExecutor(max_workers=os.cpu_count())

# --- Global Variables for Models and Processors ---
device: torch.device = None
clip_model_instance: Any = None
clip_preprocess_instance: Any = None
blip_model_instance: Any = None
blip_processor_instance: Any = None

# --- Helper Functions from clip_model.py and blip_model.py (adapted) ---

def _setup_device(preferred_device: str) -> torch.device:
    if preferred_device == "cuda" and torch.cuda.is_available():
        try:
            # Force CUDA initialization with a dummy tensor
            torch.zeros(1).cuda()
            logger.info(f"CUDA available. Using device: cuda:{torch.cuda.current_device()}")
            return torch.device("cuda")
        except Exception as e:
            logger.error(f"Error initializing CUDA: {e}. Falling back to CPU.")
            return torch.device("cpu")
    logger.info(f"Using device: cpu (CUDA not available or not preferred)")
    return torch.device("cpu")

async def _load_clip_model_internal(model_name: str, target_device: torch.device) -> Tuple[Any, Any]:
    logger.info(f"Loading CLIP model ({model_name}) on {target_device}...")
    start_time = time.time()
    try:
        model, preprocess = clip.load(model_name, device=target_device)
        # Ensure model is on the target device, clip.load might handle this but an explicit .to() is safer.
        model = model.to(target_device) 
        logger.info(f"CLIP model ({model_name}) loaded in {time.time() - start_time:.2f}s. Device: {next(model.parameters()).device}")
        return model, preprocess
    except Exception as e:
        logger.error(f"Error loading CLIP model ({model_name}): {e}", exc_info=True)
        raise # Re-raise to be caught by startup event

async def _load_blip_model_internal(model_name: str, target_device: torch.device) -> Tuple[Any, Any]:
    logger.info(f"Loading BLIP model ({model_name}) on {target_device}...")
    start_time = time.time()
    try:
        processor = BlipProcessor.from_pretrained(model_name)
        model = BlipForConditionalGeneration.from_pretrained(model_name)
        model = model.to(target_device)
        logger.info(f"BLIP model ({model_name}) loaded in {time.time() - start_time:.2f}s. Device: {next(model.parameters()).device}")
        return model, processor
    except Exception as e:
        logger.error(f"Error loading BLIP model ({model_name}): {e}", exc_info=True)
        raise # Re-raise to be caught by startup event

# --- Heavy compute helper functions to allow asyncio offloading ---
def _encode_clip(tensor: torch.Tensor) -> torch.Tensor:
    with torch.inference_mode():
        with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
            feats = clip_model_instance.encode_image(tensor)
            feats /= feats.norm(dim=-1, keepdim=True)
    return feats

def _generate_blip(inputs: Dict[str, torch.Tensor]) -> torch.Tensor:
    with torch.inference_mode():
        with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
            return blip_model_instance.generate(**inputs, max_length=75)

# --- FastAPI Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    global device, clip_model_instance, clip_preprocess_instance, blip_model_instance, blip_processor_instance
    
    logger.info("ML Inference Service starting up...")
    device = _setup_device(DEVICE_PREFERENCE)
    logger.info(f"Selected device: {device}")

    try:
        clip_model_instance, clip_preprocess_instance = await _load_clip_model_internal(CLIP_MODEL_NAME_CONFIG, device)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load CLIP model during startup: {e}")
        # Decide if service should fail to start or run degraded
        # For now, it will continue, but endpoints using CLIP will fail.

    try:
        blip_model_instance, blip_processor_instance = await _load_blip_model_internal(BLIP_MODEL_NAME_CONFIG, device)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load BLIP model during startup: {e}")
        # Decide if service should fail to start or run degraded

    logger.info("ML Inference Service startup complete.")
    if clip_model_instance:
        logger.info(f"CLIP model ({CLIP_MODEL_NAME_CONFIG}) ready.")
    else:
        logger.warning(f"CLIP model ({CLIP_MODEL_NAME_CONFIG}) FAILED TO LOAD.")
    
    if blip_model_instance:
        logger.info(f"BLIP model ({BLIP_MODEL_NAME_CONFIG}) ready.")
    else:
        logger.warning(f"BLIP model ({BLIP_MODEL_NAME_CONFIG}) FAILED TO LOAD.")


@app.on_event("shutdown")
async def shutdown_event():
    global clip_model_instance, clip_preprocess_instance, blip_model_instance, blip_processor_instance
    logger.info("ML Inference Service shutting down...")
    clip_model_instance = None
    clip_preprocess_instance = None
    blip_model_instance = None
    blip_processor_instance = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Models and preprocessors cleared.")

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "ML Inference Service is running", "device": str(device)}

class EmbedRequest(BaseModel):
    image_base64: str
    filename: str # Optional, for logging/context

@v1_router.post("/embed", response_model=Dict[str, Any])
async def embed_image_endpoint_v1(request: EmbedRequest = Body(...)):
    if not clip_model_instance or not clip_preprocess_instance:
        logger.error("/embed call failed: CLIP model not loaded.")
        raise HTTPException(status_code=503, detail="CLIP model is not available. Please check service logs.")

    try:
        image_bytes = base64.b64decode(request.image_base64)
        
        # Handle DNG separately using rawpy on a temporary file
        if request.filename.lower().endswith('.dng'):
            with tempfile.NamedTemporaryFile(suffix='.dng', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp.flush()
                tmp_path = tmp.name
            try:
                with rawpy.imread(tmp_path) as raw:
                    rgb = raw.postprocess()
                image = Image.fromarray(rgb).convert("RGB")
            finally:
                os.remove(tmp_path)
        else:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        image_input = clip_preprocess_instance(image).unsqueeze(0).to(device)

        image_features = await asyncio.to_thread(_encode_clip, image_input)
        
        embedding = image_features.cpu().numpy().squeeze().tolist() # tolist for JSON

        logger.info(f"Successfully embedded image: {request.filename or 'untitled'}")
        response = {
            "filename": request.filename,
            "embedding": embedding,
            "embedding_shape": list(np.array(embedding).shape),
            "model_name": CLIP_MODEL_NAME_CONFIG,
            "device_used": str(device)
        }
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return response
    except Exception as e:
        logger.error(f"Error processing image for embedding ({request.filename or 'untitled'}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to embed image: {str(e)}")

class CaptionRequest(BaseModel):
    image_base64: str
    filename: str # Optional, for logging/context

@v1_router.post("/caption", response_model=Dict[str, Any])
async def caption_image_endpoint_v1(request: CaptionRequest = Body(...)):
    if not blip_model_instance or not blip_processor_instance:
        logger.error("/caption call failed: BLIP model not loaded.")
        raise HTTPException(status_code=503, detail="BLIP model is not available. Please check service logs.")

    try:
        image_bytes = base64.b64decode(request.image_base64)
        # Handle DNG in caption endpoint using rawpy on a temp file
        if request.filename.lower().endswith('.dng'):
            with tempfile.NamedTemporaryFile(suffix='.dng', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp.flush()
                tmp_path = tmp.name
            try:
                with rawpy.imread(tmp_path) as raw:
                    rgb = raw.postprocess()
                image = Image.fromarray(rgb).convert("RGB")
            finally:
                os.remove(tmp_path)
        else:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # BLIP doesn't typically use a conditional prompt string unless you want to guide it.
        # For general captioning, an empty prompt or task-specific default is fine.
        # inputs = blip_processor_instance(image, return_tensors="pt").to(device) # Simple case
        inputs = blip_processor_instance(images=image, text=None, return_tensors="pt").to(device)

        output_ids = await asyncio.to_thread(_generate_blip, inputs)
        
        caption = blip_processor_instance.decode(output_ids[0], skip_special_tokens=True)
        
        logger.info(f"Successfully captioned image: {request.filename or 'untitled'}")
        response = {
            "filename": request.filename,
            "caption": caption.strip(),
            "model_name": BLIP_MODEL_NAME_CONFIG,
            "device_used": str(device)
        }
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return response
    except Exception as e:
        logger.error(f"Error processing image for captioning ({request.filename or 'untitled'}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to caption image: {str(e)}")

# --- Batch Processing Pydantic Models ---
class BatchImageRequestItem(BaseModel):
    unique_id: str # A unique identifier for the image, like its original path or a hash
    image_base64: str
    filename: str # For logging/context, can be part of unique_id

class BatchEmbedAndCaptionRequest(BaseModel):
    images: List[BatchImageRequestItem]

class BatchResultItem(BaseModel):
    unique_id: str
    filename: str
    embedding: List[float] = None
    embedding_shape: List[int] = None
    caption: str = None
    error: Optional[str] = None
    model_name_clip: str = CLIP_MODEL_NAME_CONFIG
    model_name_blip: str = BLIP_MODEL_NAME_CONFIG
    device_used: str = str(DEVICE_PREFERENCE) # Reflects config, actual device in global var

class BatchEmbedAndCaptionResponse(BaseModel):
    results: List[BatchResultItem]

def log_cuda_memory(stage: str):
    """Log current CUDA memory usage."""
    if torch.cuda.is_available():
        alloc = torch.cuda.memory_allocated() / 1024**2
        res = torch.cuda.memory_reserved() / 1024**2
        logging.getLogger(__name__).info(f"{stage} - GPU allocated: {alloc:.2f} MB, reserved: {res:.2f} MB")

# --- Helper function for parallel preprocessing ---
def _decode_and_prep_image(item: BatchImageRequestItem) -> Tuple[str, Optional[Image.Image], Optional[str]]:
    """
    Decodes a base64 image string and prepares it as a PIL image.
    Handles DNG and common image formats. Runs in a thread pool.
    Returns a tuple of (unique_id, PIL.Image or None, error_message or None).
    """
    try:
        image_bytes = base64.b64decode(item.image_base64)
        if item.filename.lower().endswith('.dng'):
            # DNG handling requires reading from a file path
            with tempfile.NamedTemporaryFile(suffix='.dng', delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                with rawpy.imread(tmp_path) as raw:
                    rgb = raw.postprocess()
                pil_img = Image.fromarray(rgb).convert("RGB")
            finally:
                os.remove(tmp_path)
        else:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return item.unique_id, pil_img, None
    except Exception as e:
        logger.error(f"Error decoding/preprocessing image {item.filename} (ID: {item.unique_id}): {e}")
        return item.unique_id, None, f"Failed to decode or preprocess image: {str(e)}"

# --- Batch Processing Endpoint ---
@v1_router.post("/batch_embed_and_caption", response_model=BatchEmbedAndCaptionResponse)
async def batch_embed_and_caption_endpoint_v1(request: BatchEmbedAndCaptionRequest = Body(...)):
    if not clip_model_instance or not clip_preprocess_instance or not blip_model_instance or not blip_processor_instance:
        logger.error("/batch_embed_and_caption call failed: One or more models not loaded.")
        raise HTTPException(status_code=503, detail="One or more models are not available. Please check service logs.")

    batch_results_map: Dict[str, BatchResultItem] = {
        item.unique_id: BatchResultItem(unique_id=item.unique_id, filename=item.filename)
        for item in request.images
    }

    if not request.images:
        return BatchEmbedAndCaptionResponse(results=[])

    logger.info(f"Received batch request for {len(request.images)} images. Starting parallel preprocessing.")
    log_cuda_memory("Before batch processing")

    # --- Parallel Preprocessing ---
    loop = asyncio.get_running_loop()
    preprocessing_tasks = [loop.run_in_executor(cpu_executor, _decode_and_prep_image, item) for item in request.images]
    
    pil_images = []
    request_items_for_processing = []

    preprocessing_results = await asyncio.gather(*preprocessing_tasks)

    for i, (unique_id, pil_img, error) in enumerate(preprocessing_results):
        if error:
            batch_results_map[unique_id].error = error
        else:
            pil_images.append(pil_img)
            # Find the original request item to maintain order and context
            original_item = next((item for item in request.images if item.unique_id == unique_id), None)
            if original_item:
                request_items_for_processing.append(original_item)

    if not pil_images:
        logger.warning("All images in batch failed preprocessing. Returning results.")
        return BatchEmbedAndCaptionResponse(results=list(batch_results_map.values()))

    # --- CLIP Embeddings ---
    clip_embeddings = []
    try:
        if clip_model_instance:
            # Note: The original OOM handling logic is complex and might be better handled by setting a reasonable max batch size.
            # For this refactoring, we'll simplify but retain the concept. A more robust solution might use a job queue.
            inputs_clip = torch.stack([clip_preprocess_instance(img) for img in pil_images]).to(device)
            feats = await asyncio.to_thread(_encode_clip, inputs_clip)
            clip_embeddings.extend(feats.cpu().numpy())
            log_cuda_memory("After CLIP embedding batch")
    except Exception as e:
        logger.error(f"Critical error during CLIP batch processing: {e}", exc_info=True)
        # Mark all items in this batch as failed for CLIP
        for item in request_items_for_processing:
            err_msg = f"CLIP processing failed: {e}"
            if batch_results_map[item.unique_id].error:
                batch_results_map[item.unique_id].error += f"; {err_msg}"
            else:
                batch_results_map[item.unique_id].error = err_msg

    # --- BLIP Captions ---
    blip_captions = []
    try:
        if blip_model_instance:
            inputs_blip = blip_processor_instance(images=pil_images, text=None, return_tensors="pt").to(device)
            output_ids_batch = await asyncio.to_thread(_generate_blip, inputs_blip)
            blip_captions.extend([blip_processor_instance.decode(ids, skip_special_tokens=True).strip() for ids in output_ids_batch])
            log_cuda_memory("After BLIP captioning batch")
    except Exception as e:
        logger.error(f"Critical error during BLIP batch processing: {e}", exc_info=True)
        # Mark all items in this batch as failed for BLIP
        for item in request_items_for_processing:
            err_msg = f"BLIP processing failed: {e}"
            if batch_results_map[item.unique_id].error:
                batch_results_map[item.unique_id].error += f"; {err_msg}"
            else:
                batch_results_map[item.unique_id].error = err_msg

    # --- Combine Results ---
    for idx, item in enumerate(request_items_for_processing):
        result = batch_results_map[item.unique_id]
        if not result.error:
            if idx < len(clip_embeddings):
                result.embedding = clip_embeddings[idx].squeeze().tolist()
                result.embedding_shape = list(np.array(clip_embeddings[idx].squeeze()).shape)
            else:
                result.error = (result.error or "") + " ;Failed to get CLIP embedding"

            if idx < len(blip_captions):
                result.caption = blip_captions[idx]
            else:
                result.error = (result.error or "") + " ;Failed to get BLIP caption"

    final_results = list(batch_results_map.values())
    logger.info(f"Batch processing completed. Returning {len(final_results)} results.")
    log_cuda_memory("End of batch processing")
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return BatchEmbedAndCaptionResponse(results=final_results)

app.include_router(v1_router) # Add the v1 router to the main app

if __name__ == "__main__":
    import uvicorn
    # Note: For production, consider more robust runner like Gunicorn with Uvicorn workers
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001))) 