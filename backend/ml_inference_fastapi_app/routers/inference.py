import asyncio
import logging
import base64
import io
from typing import List, Dict, Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from PIL import Image
import torch

from ..services import clip_service, blip_service

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models ---

class BatchImageRequestItem(BaseModel):
    unique_id: str
    image_base64: str
    filename: str

class BatchEmbedAndCaptionRequest(BaseModel):
    images: List[BatchImageRequestItem]

class BatchResultItem(BaseModel):
    unique_id: str
    filename: str
    embedding: Optional[List[float]] = None
    embedding_shape: Optional[List[int]] = None
    caption: Optional[str] = None
    error: Optional[str] = None
    model_name_clip: str = clip_service.CLIP_MODEL_NAME_CONFIG
    model_name_blip: str = blip_service.BLIP_MODEL_NAME_CONFIG
    device_used: str = str(clip_service.DEVICE)

class BatchEmbedAndCaptionResponse(BaseModel):
    results: List[BatchResultItem]

class CapabilitiesResponse(BaseModel):
    safe_clip_batch: int
    safe_blip_batch: int
    clip_model_loaded: bool
    blip_model_loaded: bool
    device_type: str
    cuda_available: bool

# --- Endpoints ---

@router.post("/batch_embed_and_caption", response_model=BatchEmbedAndCaptionResponse)
async def batch_embed_and_caption_endpoint(request: BatchEmbedAndCaptionRequest = Body(...)):
    logger.info(f"[ML Service] Received batch_embed_and_caption request with {len(request.images)} images. Example filenames: {[item.filename for item in request.images[:3]]}{'...' if len(request.images) > 3 else ''}")
    batch_start_time = asyncio.get_event_loop().time()
    if not clip_service.get_clip_model_status() or not blip_service.get_blip_model_status():
        logger.error("[ML Service] Models are not ready. Rejecting batch.")
        raise HTTPException(status_code=503, detail="Models are not ready. Please use /warmup first.")

    valid_images: Dict[str, Image.Image] = {}
    failed_decodes: Dict[str, str] = {}
    for item in request.images:
        try:
            image_data = base64.b64decode(item.image_base64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            valid_images[item.unique_id] = image
        except Exception as e:
            logger.error(f"[ML Service] Failed to decode base64 for {item.unique_id} ({item.filename}): {e}", exc_info=True)
            failed_decodes[item.unique_id] = f"Failed to decode image: {e}"

    results: Dict[str, BatchResultItem] = {
        uid: BatchResultItem(unique_id=uid, filename="", error=err)
        for uid, err in failed_decodes.items()
    }

    if not valid_images:
        for item in request.images:
            if item.unique_id in results:
                results[item.unique_id].filename = item.filename
        logger.info("[ML Service] All images in batch failed to decode. Returning error results.")
        return BatchEmbedAndCaptionResponse(results=list(results.values()))

    # Batch process embeddings and captions under a single GPU lock
    async with clip_service.gpu_lock:
        logger.info(f"[ML Service] Starting embedding for {len(valid_images)} images...")
        embed_start = asyncio.get_event_loop().time()
        image_list = list(valid_images.values())
        embeddings = clip_service.encode_image_batch(image_list)
        embed_elapsed = asyncio.get_event_loop().time() - embed_start
        logger.info(f"[ML Service] Embedding completed in {embed_elapsed:.2f}s.")

        logger.info(f"[ML Service] Starting captioning for {len(valid_images)} images...")
        caption_start = asyncio.get_event_loop().time()
        captions = blip_service.generate_captions(image_list)
        caption_elapsed = asyncio.get_event_loop().time() - caption_start
        logger.info(f"[ML Service] Captioning completed in {caption_elapsed:.2f}s.")

    for i, (uid, image) in enumerate(valid_images.items()):
        original_item = next((item for item in request.images if item.unique_id == uid), None)
        results[uid] = BatchResultItem(
            unique_id=uid,
            filename=original_item.filename if original_item else "",
            embedding=embeddings[i].tolist(),
            embedding_shape=list(embeddings[i].shape),
            caption=captions[i]
        )

    final_results = [results[item.unique_id] for item in request.images]
    total_elapsed = asyncio.get_event_loop().time() - batch_start_time
    logger.info(f"[ML Service] Finished batch_embed_and_caption for {len(request.images)} images in {total_elapsed:.2f}s.")
    return BatchEmbedAndCaptionResponse(results=final_results)


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Return service capability information."""
    return CapabilitiesResponse(
        safe_clip_batch=clip_service.SAFE_CLIP_BATCH_SIZE,
        safe_blip_batch=blip_service.SAFE_BLIP_BATCH_SIZE,
        clip_model_loaded=clip_service.get_clip_model_status(),
        blip_model_loaded=blip_service.get_blip_model_status(),
        device_type=str(clip_service.DEVICE),
        cuda_available=torch.cuda.is_available(),
    )

@router.post("/warmup")
async def warmup_models():
    """Load both CLIP and BLIP models into memory."""
    async with clip_service.gpu_lock:
        await clip_service.load_clip_model()
        clip_service.recalculate_safe_batch_size()
    
    async with clip_service.gpu_lock:
        await blip_service.load_blip_model()
        blip_service.recalculate_safe_batch_size()
        
    return {"message": "Models warmed up and ready."}


@router.post("/cooldown")
async def cooldown_models():
    """Unload both CLIP and BLIP models from memory."""
    async with clip_service.gpu_lock:
        await clip_service.cooldown_clip_model()
        await blip_service.cooldown_blip_model()
        
    return {"message": "Models cooled down and unloaded."} 