from fastapi import FastAPI, HTTPException, Body, APIRouter, UploadFile, File
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
import gc
import math

# Configure basic logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Inference Service")
v1_router = APIRouter(prefix="/api/v1") # Define v1 router

# --- Configuration ---
CLIP_MODEL_NAME_CONFIG = os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")
BLIP_MODEL_NAME_CONFIG = os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")
DEVICE_PREFERENCE = os.environ.get("DEVICE_PREFERENCE", "cuda")
# Optional runtime flag – when set to 1/true the service will embed images but
# **skip all BLIP caption generation**.  This is useful during large ingest
# runs where captions are not immediately required and we want to halve GPU
# utilisation.
DISABLE_CAPTIONS = os.getenv("DISABLE_CAPTIONS", "0").lower() in {"1", "true", "yes"}

if DISABLE_CAPTIONS:
    logging.getLogger(__name__).info("[config] Captions DISABLED via env flag – BLIP model will not be loaded")

# --------------------------------------
# Performance-tuning knobs (env-override)
# --------------------------------------
# • BLIP_BATCH_OPT – cap runtime batch so autoregressive generation stays fast.
#   Default 32 (good for 6–8 GB GPUs).
# • CAPTION_MAX_LEN – maximum tokens to generate (default 40).
# • CAPTION_NUM_BEAMS – beam width (1 ⇒ greedy, fastest).
#   All values are overridable via environment variables for quick benchmarking.

# Operators can override the caption batch size with BLIP_BATCH_OPT.  In the
# absence of an override we default to a high ceiling (512) so that the
# SAFE_BATCH_SIZE computed at runtime is the primary limiting factor.
BLIP_BATCH_OPT = int(os.getenv("BLIP_BATCH_OPT", "512"))
CAPTION_MAX_LEN = int(os.getenv("CAPTION_MAX_LEN", "40"))
CAPTION_NUM_BEAMS = int(os.getenv("CAPTION_NUM_BEAMS", "1"))

# --- Global Thread Pool Executor ---
# Use a thread pool for CPU-bound tasks like image decoding to avoid blocking the asyncio event loop
# Oversubscribe the thread-pool for CPU-bound image decoding.
# Default: 2× logical cores (can be overridden via ML_CPU_WORKERS).
_cpu_workers_default = os.cpu_count() * 2 if os.cpu_count() else 4
cpu_executor = ThreadPoolExecutor(
    max_workers=int(os.getenv("ML_CPU_WORKERS", str(_cpu_workers_default)))
)

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

# One-time flag to run a real-image memory calibration only once
real_probe_done: bool = False

# ---------------------------------------------------------------------------
# Dual-model memory probing variables (CLIP + BLIP)
# ---------------------------------------------------------------------------
# We measure memory cost per image for both models and derive the safe batch
# size as the amount of free VRAM divided by the WORST-CASE cost.
# ---------------------------------------------------------------------------

clip_mem_per_img: int = 0  # bytes
blip_mem_per_img: int = 0  # bytes

# ---------------------------------------------------------------------------
# Memory-probe helpers (generic, CLIP, BLIP) and batch-size recalculator
# ---------------------------------------------------------------------------

def _probe_model_memory(run_one_image_fn) -> int:
    """Return VRAM used (bytes) for *one* image through the given callable."""
    try:
        if device.type != "cuda":
            # On CPU we cannot measure per-image VRAM, return 0 (ignored by caller)
            run_one_image_fn()
            return 0

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        mem_before = torch.cuda.memory_allocated(device)
        run_one_image_fn()
        torch.cuda.synchronize()
        peak_alloc = torch.cuda.max_memory_allocated(device)
        delta = peak_alloc - mem_before
        torch.cuda.empty_cache()
        return max(delta, 1)
    except Exception as exc:
        logger.error(f"Memory probe failed: {exc}")
        return 1


def _recalculate_safe_batch() -> None:
    """Re-compute SAFE_BATCH_SIZE using both CLIP & BLIP per-image costs."""
    global SAFE_BATCH_SIZE
    if device.type != "cuda":
        SAFE_BATCH_SIZE = 1
        return

    worst_case = max(clip_mem_per_img or 1, blip_mem_per_img or 1)
    free_mem, _ = torch.cuda.mem_get_info()
    safe_free = free_mem * 0.8  # 20 % head-room
    calc_size = max(1, int(safe_free // worst_case))
    # Clamp to avoid pathological values on probe failures
    SAFE_BATCH_SIZE = min(
        calc_size,
        int(os.getenv("SAFE_BATCH_SIZE_MAX", "512"))
    )
    logger.info(
        f"[Batch-Probe] clip={clip_mem_per_img/1e6:.1f} MB  "
        f"blip={blip_mem_per_img/1e6:.1f} MB  free={free_mem/1e6:.1f} MB  "
        f"→ SAFE_BATCH_SIZE={SAFE_BATCH_SIZE}"
    )

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
                    # Load BLIP model & processor
                    blip_model_instance, blip_processor_instance = await _load_blip_model_internal(
                        BLIP_MODEL_NAME_CONFIG, device
                    )

                    # ------------------  Probe BLIP memory cost ------------------
                    if device.type == "cuda":
                        def _one_blip():
                            # Use batch of 2 to capture kv-cache scaling more reliably
                            pil_batch = [Image.new("RGB", (224, 224)) for _ in range(2)]
                            inputs = blip_processor_instance(images=pil_batch, return_tensors="pt")
                            if device.type == "cuda":
                                inputs = {k: v.to(device).half() for k, v in inputs.items()}
                            else:
                                inputs = {k: v.to(device) for k, v in inputs.items()}
                            with torch.inference_mode(), torch.amp.autocast(
                                "cuda", enabled=(device.type == "cuda")
                            ):
                                blip_model_instance.generate(**inputs, max_length=75)

                        global blip_mem_per_img
                        delta_total = _probe_model_memory(_one_blip)
                        blip_mem_per_img = delta_total // 2 if delta_total > 0 else 0
                        if blip_mem_per_img < 10 * 1024:
                            logger.warning(
                                "[Batch-Probe] BLIP memory delta %.0f bytes is implausibly low – using conservative 20 MB fallback",
                                blip_mem_per_img,
                            )
                            blip_mem_per_img = 20_000_000

                        _recalculate_safe_batch()
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
    """Generate captions with globally tuned parameters (AMP + greedy/beam search)."""
    with torch.inference_mode():
        with torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
            return blip_model_instance.generate(
                **inputs,
                max_length=CAPTION_MAX_LEN,
                num_beams=CAPTION_NUM_BEAMS,
            )

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

    # ------------------  Probe CLIP memory cost  ------------------
    if device.type == "cuda":
        def _one_clip():
            # Create dummy tensor matching model precision to avoid dtype mismatch
            dummy = clip_preprocess_instance(Image.new("RGB", (224, 224))).unsqueeze(0).to(device)
            if next(clip_model_instance.parameters()).dtype == torch.float16:
                dummy = dummy.half()
            else:
                dummy = dummy.float()
            # Inference under autocast to mimic real forward pass
            with torch.inference_mode(), torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                clip_model_instance.encode_image(dummy)

        global clip_mem_per_img
        clip_mem_per_img = _probe_model_memory(_one_clip)
        # Fallback guard – if probe returns implausibly low value (<10 kB) assume 20 MB
        if clip_mem_per_img < 10 * 1024:
            logger.warning(
                "[Batch-Probe] CLIP memory delta %.0f bytes is implausibly low – using conservative 20 MB fallback",
                clip_mem_per_img,
            )
            clip_mem_per_img = 20_000_000  # 20 MB safety floor

    # After loading CLIP probe initial safe batch size (BLIP may adjust later)
    _recalculate_safe_batch()

    # BLIP model is now lazy-loaded and will not be loaded here.
    logger.info("BLIP model will be lazy-loaded on first use.")

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
    if DISABLE_CAPTIONS:
        raise HTTPException(status_code=503, detail="Captioning disabled by configuration")

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
    
    # Lazy load the BLIP model if needed for this request and captions enabled
    if not DISABLE_CAPTIONS:
        try:
            blip_model, blip_processor = await get_blip_model()
        except HTTPException as e:
            raise e  # Propagate the 503 error if model loading fails

    # --- 1. Parallel Image Preprocessing on CPU threads ---
    global real_probe_done, clip_mem_per_img, blip_mem_per_img
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

    # ------------------------------------------------------------------
    # One-time real-image GPU memory probe (better than 224×224 dummy)
    # ------------------------------------------------------------------
    if device.type == "cuda" and not real_probe_done and valid_ids:
        sample_uid = valid_ids[0]
        try:
            # ---- CLIP real probe ----
            tensor_clip = clip_preprocess_instance(prepped_images[sample_uid]).unsqueeze(0).to(device)
            tensor_clip = tensor_clip.half() if device.type == "cuda" else tensor_clip
            def _one_clip_real():
                with torch.inference_mode(), torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                    clip_model_instance.encode_image(tensor_clip)

            delta_clip = _probe_model_memory(_one_clip_real)
            if delta_clip > 0:
                clip_mem_per_img = max(clip_mem_per_img, delta_clip)

            # ---- BLIP real probe (only if blip already loaded) ----
            if blip_model_instance not in (None, "failed"):
                inputs_blip = blip_processor_instance(images=[prepped_images[sample_uid]], return_tensors="pt")
                inputs_blip = {k: v.to(device).half() for k, v in inputs_blip.items()} if device.type == "cuda" else inputs_blip
                def _one_blip_real():
                    with torch.inference_mode(), torch.amp.autocast("cuda", enabled=(device.type == "cuda")):
                        blip_model_instance.generate(**inputs_blip, max_length=75)

                delta_blip = _probe_model_memory(_one_blip_real)
                if delta_blip > 0:
                    blip_mem_per_img = max(blip_mem_per_img, delta_blip)

            _recalculate_safe_batch()
            real_probe_done = True
            logger.info("[Batch-Probe] Real-image calibration complete. New SAFE_BATCH_SIZE=%s", SAFE_BATCH_SIZE)
        except Exception as p_exc:
            logger.warning("Real-image probe failed: %s", p_exc)

    # --- 2. Locked, Sequential GPU Inference in Chunks ---
    async with gpu_lock:
        inference_start_time = time.time()
        logger.info(f"Acquired GPU lock. Starting inference for {len(valid_ids)} images in chunks of {SAFE_BATCH_SIZE}.")

        # --- Decide per-iteration chunk size (same logic as JSON endpoint) ---
        chunk_lim = SAFE_BATCH_SIZE
        if BLIP_BATCH_OPT and BLIP_BATCH_OPT > SAFE_BATCH_SIZE:
            chunk_lim = BLIP_BATCH_OPT

        num_chunks_total = math.ceil(len(valid_ids) / chunk_lim)

        for chunk_idx, i in enumerate(range(0, len(valid_ids), chunk_lim), start=1):
            chunk_ids = valid_ids[i:i + chunk_lim]
            logger.info(
                "[multipart] Processing chunk %s/%s with %s images.",
                chunk_idx,
                num_chunks_total,
                len(chunk_ids),
            )

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
            
            # --- BLIP Captions for the chunk (optional) ---
            if not DISABLE_CAPTIONS:
                try:
                    pil_images_blip = [prepped_images[uid] for uid in chunk_ids]
                    blip_inputs = blip_processor(images=pil_images_blip, return_tensors="pt").to(device)

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
                        if not processing_results[uid]["error"]:
                            processing_results[uid]["error"] = f"BLIP inference failed: {e}"
            else:
                for uid in chunk_ids:
                    processing_results[uid]["caption"] = ""
            
            # ------------------  Clean up CPU & GPU memory for next chunk  ----------
            # Drop PIL images & tensors belonging to the processed chunk so the
            # host RAM stays constant across thousands-image jobs.
            for _uid in chunk_ids:
                prepped_images.pop(_uid, None)

            if device.type == "cuda":
                del clip_input_tensors, blip_inputs, clip_features, blip_output_ids  # type: ignore
                torch.cuda.empty_cache()
            gc.collect()

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

# === NEW MULTIPART BATCH ENDPOINT ===
# This endpoint accepts `multipart/form-data` uploads where each part is an image file.
# The filename MUST be encoded as "<unique_id>__<original_filename>.png" so we can
# retrieve the caller-supplied identifier.  The business logic is identical to the
# JSON variant, but skips the expensive base64 decode and can overlap CPU decode
# on the ingestion host.


@v1_router.post("/batch_embed_and_caption_multipart", response_model=BatchEmbedAndCaptionResponse)
async def batch_embed_and_caption_multipart_endpoint_v1(
    files: List[UploadFile] = File(..., description="Upload list of PNG-encoded RGB images")
):
    """High-throughput batch embedding & captioning via multipart upload.

    Ingestion service pre-decodes original images → PNG and streams binary data.
    This saves ~33 % payload bloat from base64 and shifts CPU decode cost off the
    GPU host.
    """

    start_time = time.time()

    if not clip_model_instance:
        raise HTTPException(status_code=503, detail="CLIP model is not available.")

    # Lazy load BLIP (caption) model if required
    if not DISABLE_CAPTIONS:
        try:
            blip_model, blip_processor = await get_blip_model()
        except HTTPException as e:
            raise e

    # --- 1. Decode uploaded PNG buffers on a CPU thread pool --------------
    prepped_images: Dict[str, Image.Image] = {}
    processing_results: Dict[str, Dict] = {}

    def _decode_single_upload(upload: UploadFile):
        """Helper to decode one UploadFile → (unique_id, PIL.Image) or raise."""
        file_bytes = upload.file.read()  # synchronous read inside thread
        fname = upload.filename or "unknown.png"
        if "__" in fname:
            unique_id, original_name = fname.split("__", 1)
        else:
            unique_id, original_name = os.path.splitext(fname)[0], fname

        try:
            pil_img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            return unique_id, original_name, pil_img, None
        except Exception as exc:
            return unique_id, original_name, None, f"Failed to decode PNG: {exc}"

    decode_futures = [cpu_executor.submit(_decode_single_upload, uf) for uf in files]

    for fut in as_completed(decode_futures):
        uid, orig_name, pil_img, err = fut.result()
        processing_results[uid] = {
            "unique_id": uid,
            "filename": orig_name,
            "error": err,
        }
        if err is None and pil_img is not None:
            prepped_images[uid] = pil_img

    valid_ids = list(prepped_images.keys())
    if not valid_ids:
        return BatchEmbedAndCaptionResponse(results=[BatchResultItem(**res) for res in processing_results.values()])

    log_cuda_memory("After PNG Decode (multipart)")

    # --- 2. GPU inference in SAFE_BATCH_SIZE chunks -----------------------
    async with gpu_lock:
        inference_start = time.time()
        chunk_lim = SAFE_BATCH_SIZE
        if BLIP_BATCH_OPT and BLIP_BATCH_OPT > SAFE_BATCH_SIZE:
            chunk_lim = BLIP_BATCH_OPT

        num_chunks_total = math.ceil(len(valid_ids) / chunk_lim)

        for chunk_idx, i in enumerate(range(0, len(valid_ids), chunk_lim), start=1):
            chunk_ids = valid_ids[i:i + chunk_lim]
            logger.info(
                "[multipart] Processing chunk %s/%s with %s images.",
                chunk_idx,
                num_chunks_total,
                len(chunk_ids),
            )

            # CLIP
            try:
                pil_imgs_clip = [prepped_images[uid] for uid in chunk_ids]
                clip_inputs = torch.stack([clip_preprocess_instance(img) for img in pil_imgs_clip]).to(device)
                if device.type == "cuda":
                    clip_inputs = clip_inputs.half()
                clip_features = await asyncio.to_thread(_encode_clip, clip_inputs)
                clip_np = clip_features.cpu().numpy()
                for j, uid in enumerate(chunk_ids):
                    processing_results[uid]["embedding"] = clip_np[j].tolist()
                    processing_results[uid]["embedding_shape"] = list(clip_np[j].shape)
            except Exception as e:
                logger.error(f"CLIP inference failed on multipart chunk: {e}", exc_info=True)
                for uid in chunk_ids:
                    if not processing_results[uid]["error"]:
                        processing_results[uid]["error"] = f"CLIP error: {e}"
            
            # BLIP captions (optional)
            if not DISABLE_CAPTIONS:
                try:
                    pil_imgs_blip = [prepped_images[uid] for uid in chunk_ids]
                    blip_inputs = blip_processor(images=pil_imgs_blip, return_tensors="pt").to(device)
                    if device.type == "cuda":
                        blip_inputs = {k: v.to(device).half() for k, v in blip_inputs.items()}
                    else:
                        blip_inputs = {k: v.to(device) for k, v in blip_inputs.items()}

                    blip_ids = await asyncio.to_thread(_generate_blip, blip_inputs)
                    captions = blip_processor.batch_decode(blip_ids, skip_special_tokens=True)
                    for j, uid in enumerate(chunk_ids):
                        processing_results[uid]["caption"] = captions[j].strip()
                except Exception as e:
                    logger.error(f"BLIP inference failed on multipart chunk: {e}", exc_info=True)
                    for uid in chunk_ids:
                        if not processing_results[uid]["error"]:
                            processing_results[uid]["error"] = f"BLIP error: {e}"
            else:
                for uid in chunk_ids:
                    processing_results[uid]["caption"] = ""
            
            # ------------------  Clean up CPU & GPU memory for next chunk  ----------
            # Drop PIL images & tensors belonging to the processed chunk so the
            # host RAM stays constant across thousands-image jobs.
            for _uid in chunk_ids:
                prepped_images.pop(_uid, None)

            if device.type == "cuda":
                del clip_inputs, blip_inputs, clip_features, blip_ids  # type: ignore
                torch.cuda.empty_cache()
            gc.collect()

        logger.info(f"Multipart GPU inference completed in {time.time() - inference_start:.2f}s")

    if device.type == "cuda":
        torch.cuda.empty_cache()

    return BatchEmbedAndCaptionResponse(results=[BatchResultItem(**res) for res in processing_results.values()])

app.include_router(v1_router)

if __name__ == "__main__":
    import uvicorn
    # Note: For production, consider more robust runner like Gunicorn with Uvicorn workers
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001))) 