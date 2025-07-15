import asyncio
import logging
import os
from typing import Tuple, Any

import torch
from transformers import AutoProcessor, BlipForConditionalGeneration

# Import the shared GPU lock to ensure exclusive access
from .clip_service import gpu_lock, DEVICE

logger = logging.getLogger(__name__)

# --- Globals for BLIP Service ---
BLIP_MODEL: Any = None
BLIP_PROCESSOR: Any = None
SAFE_BLIP_BATCH_SIZE = 1  # Default, will be probed
BLIP_MODEL_NAME_CONFIG = os.environ.get("BLIP_MODEL", "Salesforce/blip-image-captioning-base")

# --- Model Loading and Management ---

async def load_blip_model() -> Tuple[Any, Any]:
    """Loads the BLIP model and processor into memory."""
    global BLIP_MODEL, BLIP_PROCESSOR
    if BLIP_MODEL is not None:
        return BLIP_MODEL, BLIP_PROCESSOR

    logger.info(f"Loading BLIP model: {BLIP_MODEL_NAME_CONFIG} on device: {DEVICE}")
    try:
        blip_processor = AutoProcessor.from_pretrained(BLIP_MODEL_NAME_CONFIG)
        blip_model = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL_NAME_CONFIG)

        if DEVICE.type == 'cuda':
            # Move model to GPU with FP16 for memory efficiency
            blip_model.to(torch.float16)
            
            # Apply torch.compile for performance (PyTorch 2.0+)
            try:
                blip_model = torch.compile(blip_model, mode="reduce-overhead")
                logger.info("✅ Applied torch.compile optimization to BLIP model")
            except Exception as e:
                logger.warning("torch.compile for BLIP failed, continuing without it: %s", e)

        blip_model = blip_model.to(DEVICE)
        blip_model.eval()
        BLIP_MODEL = blip_model
        BLIP_PROCESSOR = blip_processor
        logger.info("BLIP model loaded successfully.")
        return blip_model, blip_processor
    except Exception as e:
        logger.error(f"Failed to load BLIP model: {e}", exc_info=True)
        BLIP_MODEL = "failed"
        return None, None

def get_blip_model_status() -> bool:
    """Returns True if the BLIP model is loaded, False otherwise."""
    return BLIP_MODEL is not None and BLIP_MODEL != "failed"

def generate_captions(images: list[Any], text: str = None, do_rescale: bool = True) -> list[str]:
    """Generates captions for a batch of pre-processed images.
    If an OOM error occurs, splits the batch and retries recursively.
    """
    if not get_blip_model_status():
        raise RuntimeError("BLIP model is not available.")

    try:
        inputs = BLIP_PROCESSOR(images=images, text=text, return_tensors="pt", do_rescale=do_rescale).to(DEVICE)
        with torch.no_grad():
            outputs = BLIP_MODEL.generate(**inputs)
        captions = [BLIP_PROCESSOR.decode(out, skip_special_tokens=True) for out in outputs]
        return captions
    except RuntimeError as e:
        # WARNING: This function previously caused CUDA OOM errors when batch size was too large.
        # If you see 'CUDA out of memory', this block will split the batch and retry.
        if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
            logger.warning(f"[BLIP] OOM detected for batch of size {len(images)}. Splitting and retrying.")
            torch.cuda.empty_cache()
            if len(images) == 1:
                logger.error(f"[BLIP] OOM on single image. Cannot split further.")
                raise
            mid = len(images) // 2
            left = generate_captions(images[:mid], text=text, do_rescale=do_rescale)
            right = generate_captions(images[mid:], text=text, do_rescale=do_rescale)
            return left + right
        else:
            raise

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
    """Calculates and sets the safe batch size for the BLIP model."""
    global SAFE_BLIP_BATCH_SIZE
    if not get_blip_model_status() or DEVICE.type != "cuda":
        SAFE_BLIP_BATCH_SIZE = 1
        return

    def _one_blip_real():
        dummy_image = torch.zeros((3, 224, 224))
        generate_captions([dummy_image], do_rescale=False)

    free_mem, _ = torch.cuda.mem_get_info(DEVICE)
    mem_per_item = _probe_model_memory(_one_blip_real)
    
    safe_size = int((free_mem * 0.8) / mem_per_item)
    SAFE_BLIP_BATCH_SIZE = max(1, safe_size)
    logger.info(f"Recalculated SAFE_BLIP_BATCH_SIZE: {SAFE_BLIP_BATCH_SIZE}")


async def cooldown_blip_model():
    """Unloads the BLIP model from memory."""
    global BLIP_MODEL, BLIP_PROCESSOR
    if BLIP_MODEL is not None and BLIP_MODEL != "failed":
        logger.info("Unloading BLIP model from memory.")
        del BLIP_MODEL
        del BLIP_PROCESSOR
        BLIP_MODEL = None
        BLIP_PROCESSOR = None
        if DEVICE.type == "cuda":
            torch.cuda.empty_cache()
        logger.info("BLIP model unloaded.") 