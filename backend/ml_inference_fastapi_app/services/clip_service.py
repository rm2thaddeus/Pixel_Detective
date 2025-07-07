import asyncio
import logging
import os
from typing import Tuple, Any

import torch
from transformers import AutoProcessor, AutoModel

logger = logging.getLogger(__name__)

# --- Globals for CLIP Service ---
CLIP_MODEL: Any = None
CLIP_PROCESSOR: Any = None
SAFE_CLIP_BATCH_SIZE = 1  # Default, will be probed
CLIP_MODEL_NAME_CONFIG = os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32")
DEVICE_PREFERENCE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
DEVICE = torch.device(DEVICE_PREFERENCE)

# GPU lock for exclusive access
gpu_lock = asyncio.Lock()

# --- Model Loading and Management ---

async def load_clip_model() -> Tuple[Any, Any]:
    """Loads the CLIP model and processor into memory."""
    global CLIP_MODEL, CLIP_PROCESSOR
    if CLIP_MODEL is not None:
        return CLIP_MODEL, CLIP_PROCESSOR

    logger.info(f"Loading CLIP model: {CLIP_MODEL_NAME_CONFIG} on device: {DEVICE}")
    try:
        processor = AutoProcessor.from_pretrained(CLIP_MODEL_NAME_CONFIG)
        model = AutoModel.from_pretrained(CLIP_MODEL_NAME_CONFIG).to(DEVICE)
        model.eval()
        CLIP_MODEL = model
        CLIP_PROCESSOR = processor
        logger.info("CLIP model loaded successfully.")
        return model, processor
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}", exc_info=True)
        CLIP_MODEL = "failed" # Mark as failed to prevent retries
        return None, None

def get_clip_model_status() -> bool:
    """Returns True if the CLIP model is loaded, False otherwise."""
    return CLIP_MODEL is not None and CLIP_MODEL != "failed"

def encode_text_batch(texts: list[str]) -> torch.Tensor:
    """Encodes a batch of text queries using the loaded CLIP model."""
    if not get_clip_model_status():
        raise RuntimeError("CLIP model is not available.")
        
    inputs = CLIP_PROCESSOR(text=texts, return_tensors="pt", padding=True, truncation=True).to(DEVICE)
    with torch.no_grad():
        text_features = CLIP_MODEL.get_text_features(**inputs)
    return text_features

def encode_image_batch(images: list[Any]) -> torch.Tensor:
    """Encodes a batch of pre-processed images using the loaded CLIP model."""
    if not get_clip_model_status():
        raise RuntimeError("CLIP model is not available.")

    inputs = CLIP_PROCESSOR(images=images, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        image_features = CLIP_MODEL.get_image_features(**inputs)
    return image_features

# --- Performance & Memory Probing ---

def _probe_model_memory(run_one_image_fn) -> int:
    """Helper to probe GPU memory for a single inference call."""
    if DEVICE.type != "cuda":
        return 1

    # Clear cache and reset peak memory statistics
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(DEVICE)
    # Record baseline memory usage
    baseline = torch.cuda.memory_allocated(DEVICE)
    try:
        run_one_image_fn()
    except Exception as e:
        logger.error(f"Probing function failed: {e}", exc_info=True)
        torch.cuda.empty_cache()
        return 1
    # Get peak memory usage during inference
    peak = torch.cuda.max_memory_allocated(DEVICE)
    torch.cuda.empty_cache()
    # Calculate memory used by one inference
    mem_used = peak - baseline
    return mem_used if mem_used > 0 else 1


def recalculate_safe_batch_size():
    """Calculates and sets the safe batch size for the CLIP model."""
    global SAFE_CLIP_BATCH_SIZE
    if not get_clip_model_status() or DEVICE.type != "cuda":
        SAFE_CLIP_BATCH_SIZE = 1
        return

    def _one_clip_real():
        dummy_image = torch.zeros((3, 224, 224), device=DEVICE)
        encode_image_batch([dummy_image])

    free_mem, _ = torch.cuda.mem_get_info(DEVICE)
    mem_per_item = _probe_model_memory(_one_clip_real)
    
    # Calculate batch size with a 20% safety margin
    safe_size = int((free_mem * 0.8) / mem_per_item)
    SAFE_CLIP_BATCH_SIZE = max(1, safe_size)
    logger.info(f"Recalculated SAFE_CLIP_BATCH_SIZE: {SAFE_CLIP_BATCH_SIZE}")


async def cooldown_clip_model():
    """Unloads the CLIP model from memory."""
    global CLIP_MODEL, CLIP_PROCESSOR
    if CLIP_MODEL is not None and CLIP_MODEL != "failed":
        logger.info("Unloading CLIP model from memory.")
        del CLIP_MODEL
        del CLIP_PROCESSOR
        CLIP_MODEL = None
        CLIP_PROCESSOR = None
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()
        logger.info("CLIP model unloaded.") 