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

# --- Concurrency Control ---
# Global lock to ensure only one batch is processed on the GPU at a time
gpu_lock = asyncio.Lock()
# Lock to prevent race conditions when lazy-loading the BLIP model
blip_load_lock = asyncio.Lock()


# --- Global Variables for Models and Processors ---
device: torch.device = None
clip_model_instance: Any = None
clip_preprocess_instance: Any = None
blip_model_instance: Any = None
blip_processor_instance: Any = None
SAFE_BATCH_SIZE: int = 1 # Default, will be probed on startup if using CUDA

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
        # Ensure model is on the target device and in half-precision if using CUDA
        if target_device.type == "cuda":
            model = model.to(target_device).half()
        else:
            model = model.to(target_device)
        logger.info(f"CLIP model ({model_name}) loaded in {time.time() - start_time:.2f}s. Device: {next(model.parameters()).device}, Precision: {next(model.parameters()).dtype}")
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
        # Ensure model is on the target device and in half-precision if using CUDA
        if target_device.type == "cuda":
            model = model.to(target_device).half()
        else:
            model = model.to(target_device)
        logger.info(f"BLIP model ({model_name}) loaded in {time.time() - start_time:.2f}s. Device: {next(model.parameters()).device}, Precision: {next(model.parameters()).dtype}")
        return model, processor
    except Exception as e:
        logger.error(f"Error loading BLIP model ({model_name}): {e}", exc_info=True)
        raise # Re-raise to be caught by startup event

# --- New Function for GPU Probing ---
def _probe_safe_batch_size():
    """
    Probes the GPU to determine a safe batch size for CLIP inference.
    This helps prevent out-of-memory errors.
    """
    global SAFE_BATCH_SIZE
    if device.type != "cuda" or not clip_model_instance:
        logger.info("Skipping batch size probing (not using CUDA or CLIP model not loaded). Defaulting to 1.")
        SAFE_BATCH_SIZE = 1
        return

    logger.info("Probing for safe GPU batch size...")
    try:
        # 1. Create a dummy input tensor
        # Use the preprocessor to get the correct dimensions
        dummy_pil = Image.new('RGB', (224, 224))
        dummy_input = clip_preprocess_instance(dummy_pil).unsqueeze(0).to(device)
        
        # 2. Measure memory usage for a single item
        torch.cuda.empty_cache()
        mem_before = torch.cuda.memory_allocated()
        
        # Run inference on the single item
        with torch.inference_mode():
            with torch.amp.autocast("cuda"):
                clip_model_instance.encode_image(dummy_input)

        mem_after = torch.cuda.memory_allocated()
        torch.cuda.empty_cache()

        per_input_mem = mem_after - mem_before
        if per_input_mem <= 0:
            # This can happen if the model is very small or memory allocation is unusual
            logger.warning("Could not determine memory per input (per_input_mem <= 0). Defaulting batch size to 1.")
            SAFE_BATCH_SIZE = 1
            return
            
        # 3. Get free memory and calculate a safe batch size
        free_mem, _ = torch.cuda.mem_get_info()
        # Use 80% of free memory as a safety margin
        safe_free_mem = free_mem * 0.8
        
        calculated_size = int(safe_free_mem // per_input_mem)
        
        # Ensure batch size is at least 1
        SAFE_BATCH_SIZE = max(1, calculated_size)
        logger.info(f"Memory per input: {per_input_mem / 1024**2:.2f} MB. Free memory: {free_mem / 1024**2:.2f} MB.")
        logger.info(f"Determined safe batch size: {SAFE_BATCH_SIZE}")

    except Exception as e:
        logger.error(f"Failed to probe for safe batch size: {e}. Defaulting to 1.", exc_info=True)
        SAFE_BATCH_SIZE = 1

# --- Dependency for Lazy-Loading BLIP Model ---
async def get_blip_model():
    """
    Dependency to lazy-load the BLIP model.
    This ensures the model is only loaded into memory when a captioning endpoint is called.
    Uses a lock to prevent race conditions on first load.
    """
    global blip_model_instance, blip_processor_instance
    if blip_model_instance is None:
        async with blip_load_lock:
            # Check again inside the lock in case it was loaded while waiting
            if blip_model_instance is None:
                logger.info("BLIP model not loaded. Loading now...")
                try:
                    blip_model_instance, blip_processor_instance = await _load_blip_model_internal(BLIP_MODEL_NAME_CONFIG, device)
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to lazy-load BLIP model: {e}")
                    # Set to dummy values to prevent repeated load attempts
                    blip_model_instance, blip_processor_instance = "failed", "failed" 
            
    if blip_model_instance == "failed":
        raise HTTPException(status_code=503, detail="BLIP model failed to load and is unavailable.")
        
    return blip_model_instance, blip_processor_instance

# --- Heavy compute helper functions to allow asyncio offloading ---
def _encode_clip(tensor: torch.Tensor) -> torch.Tensor:
    with torch.inference_mode():
        with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
            feats = clip_model_instance.encode_image(tensor)
            feats /= feats.norm(dim=-1, keepdim=True)
    return feats

def _generate_blip(inputs: Dict[str, torch.Tensor]) -> torch.Tensor:
    with torch.inference_mode():
        with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
            return blip_model_instance.generate(**inputs, max_length=75)

# --- FastAPI Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    global device, clip_model_instance, clip_preprocess_instance, blip_model_instance, blip_processor_instance
    
    logger.info("ML Inference Service starting up...")
    device = _setup_device(DEVICE_PREFERENCE)
    logger.info(f"Selected device: {device}")

    # Eagerly load the CLIP model as it's the primary model
    try:
        clip_model_instance, clip_preprocess_instance = await _load_clip_model_internal(CLIP_MODEL_NAME_CONFIG, device)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to load CLIP model during startup: {e}")
        # Service will start degraded, endpoint checks will fail.

    # BLIP model is now lazy-loaded and will not be loaded here.
    logger.info("BLIP model will be lazy-loaded on first use.")

    # After loading models, probe for a safe batch size
    _probe_safe_batch_size()

    logger.info("ML Inference Service startup complete.")
    if clip_model_instance:
        logger.info(f"CLIP model ({CLIP_MODEL_NAME_CONFIG}) ready.")
    else:
        logger.warning(f"CLIP model ({CLIP_MODEL_NAME_CONFIG}) FAILED TO LOAD.")


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

@app.get("/health")
async def health():
    """Health check endpoint for the ML Inference Service."""
    return {"service": "ML Inference Service", "status": "ok", "device": str(device)}

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

class TextEmbedRequest(BaseModel):
    text: str
    description: str = "Text query for embedding"  # Optional, for logging/context

class TextEmbedResponse(BaseModel):
    embedding: List[float]
    embedding_shape: List[int]
    text: str
    model_name: str
    device_used: str

@v1_router.post("/embed_text", response_model=TextEmbedResponse)
async def embed_text_endpoint_v1(request: TextEmbedRequest = Body(...)):
    """
    Generate CLIP text embeddings for semantic search.
    
    Args:
        request: TextEmbedRequest containing the text to embed
        
    Returns:
        TextEmbedResponse containing the normalized embedding vector
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    if not clip_model_instance:
        raise HTTPException(status_code=503, detail="CLIP model not loaded")
    
    logger.info(f"Generating text embedding for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    try:
        # Tokenize and encode text
        text_tokens = clip.tokenize([text]).to(device)
        
        # Generate embeddings with GPU lock
        async with gpu_lock:
            with torch.inference_mode():
                with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                    text_features = clip_model_instance.encode_text(text_tokens)
                    # Normalize the features
                    text_features /= text_features.norm(dim=-1, keepdim=True)
        
        # Convert to CPU and list format
        embedding = text_features.cpu().numpy().flatten().tolist()
        embedding_shape = list(text_features.shape)
        
        logger.info(f"Generated text embedding: shape={embedding_shape}, first_few_values={embedding[:3]}")
        
        return TextEmbedResponse(
            embedding=embedding,
            embedding_shape=embedding_shape,
            text=text,
            model_name=CLIP_MODEL_NAME_CONFIG,
            device_used=str(device)
        )
        
    except Exception as e:
        logger.error(f"Error generating text embedding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate text embedding: {str(e)}")

@v1_router.post("/caption", response_model=Dict[str, Any])
async def caption_image_endpoint_v1(request: CaptionRequest = Body(...)):
    try:
        # Lazy load the BLIP model using the dependency
        blip_model, blip_processor = await get_blip_model()
    except HTTPException as e:
        raise e # Propagate the 503 error if the model failed to load

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
        inputs = blip_processor.to(device)

        async with gpu_lock:
            output_ids = await asyncio.to_thread(_generate_blip, inputs)
        
        caption = blip_processor.decode(output_ids[0], skip_special_tokens=True)
        
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
    """
    Handles batch processing for embedding (CLIP) and captioning (BLIP).
    - Image decoding is done in parallel on a CPU thread pool.
    - GPU-bound inference is protected by a lock to ensure sequential access.
    - BLIP model is lazy-loaded on demand.
    """
    start_time = time.time()
    
    # --- Check for model availability ---
    if not clip_model_instance:
        raise HTTPException(status_code=503, detail="CLIP model is not available.")
    
    # Lazy load the BLIP model if needed for this request
    try:
        blip_model, blip_processor = await get_blip_model()
    except HTTPException as e:
        raise e # Propagate the 503 error if model loading fails

    # --- 1. Parallel Image Preprocessing on CPU threads ---
    prepped_images: Dict[str, Image.Image] = {}
    future_to_id = {cpu_executor.submit(_decode_and_prep_image, item): item.unique_id for item in request.images}
    
    processing_results: Dict[str, Dict] = {item.unique_id: {
        "unique_id": item.unique_id,
        "filename": item.filename,
        "error": None
    } for item in request.images}

    for future in as_completed(future_to_id):
        unique_id = future_to_id[future]
        try:
            _id, pil_image, error_msg = future.result()
            if error_msg:
                processing_results[unique_id]["error"] = error_msg
            else:
                prepped_images[unique_id] = pil_image
        except Exception as e:
            logger.error(f"Error decoding image {unique_id} in thread: {e}", exc_info=True)
            processing_results[unique_id]["error"] = f"Failed during decoding: {e}"

    # Filter out images that failed decoding
    valid_ids = [uid for uid, img in prepped_images.items() if img is not None]
    
    if not valid_ids:
        logger.warning("No valid images to process after decoding step.")
        return BatchEmbedAndCaptionResponse(results=list(processing_results.values()))

    logger.info(f"Decoded {len(valid_ids)} images in {time.time() - start_time:.2f}s")
    log_cuda_memory("After Image Decoding")

    # --- 2. Locked, Sequential GPU Inference in Chunks ---
    async with gpu_lock:
        inference_start_time = time.time()
        logger.info(f"Acquired GPU lock. Starting inference for {len(valid_ids)} images in chunks of {SAFE_BATCH_SIZE}.")

        # Process valid_ids in chunks of SAFE_BATCH_SIZE
        for i in range(0, len(valid_ids), SAFE_BATCH_SIZE):
            chunk_ids = valid_ids[i:i + SAFE_BATCH_SIZE]
            if not chunk_ids:
                continue
            
            logger.info(f"Processing chunk {i//SAFE_BATCH_SIZE + 1}/{(len(valid_ids) + SAFE_BATCH_SIZE - 1)//SAFE_BATCH_SIZE} with {len(chunk_ids)} images.")

            # --- CLIP Embeddings for the chunk ---
            try:
                pil_images_clip = [prepped_images[uid] for uid in chunk_ids]
                clip_input_tensors = torch.stack([clip_preprocess_instance(img) for img in pil_images_clip]).to(device)

                # For half-precision, ensure input tensor is also .half()
                if device.type == "cuda":
                    clip_input_tensors = clip_input_tensors.half()

                clip_features = await asyncio.to_thread(_encode_clip, clip_input_tensors)
                clip_embeddings = clip_features.cpu().numpy()
                
                for j, unique_id in enumerate(chunk_ids):
                    processing_results[unique_id]["embedding"] = clip_embeddings[j].tolist()
                    processing_results[unique_id]["embedding_shape"] = list(clip_embeddings[j].shape)
            except Exception as e:
                logger.error(f"Error during CLIP batch inference on chunk: {e}", exc_info=True)
                for uid in chunk_ids:
                    if not processing_results[uid]["error"]: # Avoid overwriting decode error
                        processing_results[uid]["error"] = f"CLIP inference failed: {e}"
            
            # --- BLIP Captions for the chunk ---
            try:
                pil_images_blip = [prepped_images[uid] for uid in chunk_ids]
                # Use the lazy-loaded processor
                blip_inputs = blip_processor(images=pil_images_blip, return_tensors="pt").to(device)

                # For half-precision, ensure input tensor is also .half()
                if device.type == "cuda":
                    blip_inputs = {k: v.to(device).half() for k, v in blip_inputs.items()}
                else:
                    blip_inputs = {k: v.to(device) for k, v in blip_inputs.items()}

                
                logger.info(f"Running BLIP inference for batch of size {len(pil_images_blip)}...")
                blip_output_ids = await asyncio.to_thread(_generate_blip, blip_inputs)
                captions = blip_processor.batch_decode(blip_output_ids, skip_special_tokens=True)

                for j, unique_id in enumerate(chunk_ids):
                    processing_results[unique_id]["caption"] = captions[j].strip()
            except Exception as e:
                logger.error(f"Error during BLIP batch inference on chunk: {e}", exc_info=True)
                for uid in chunk_ids:
                    if not processing_results[uid]["error"]: # Avoid overwriting previous errors
                        processing_results[uid]["error"] = f"BLIP inference failed: {e}"
        
        log_cuda_memory("After all inference chunks")
        logger.info(f"GPU inference finished in {time.time() - inference_start_time:.2f}s. Releasing lock.")

    # --- 3. Consolidate and Respond ---
    final_results = [BatchResultItem(**res) for res in processing_results.values()]

    logger.info(f"Batch processing complete for {len(request.images)} items in {time.time() - start_time:.2f}s")
    if device.type == "cuda":
        torch.cuda.empty_cache() # Clear cache after a large batch operation
        
    return BatchEmbedAndCaptionResponse(results=final_results)

# --- New Capabilities Endpoint to Expose Service Limits ---
class CapabilitiesResponse(BaseModel):
    """Response model for service capability information."""
    safe_clip_batch: int

@v1_router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities_v1():
    """Return runtime capability information so clients can adapt dynamically."""
    return CapabilitiesResponse(safe_clip_batch=SAFE_BATCH_SIZE)

app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    # Note: For production, consider more robust runner like Gunicorn with Uvicorn workers
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001))) 