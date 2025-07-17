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
from ..services import redis_scheduler as scheduler

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

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[BatchEmbedAndCaptionResponse] = None
    error: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    status: str

class CapabilitiesResponse(BaseModel):
    safe_clip_batch: int
    safe_blip_batch: int
    clip_model_loaded: bool
    blip_model_loaded: bool
    device_type: str
    cuda_available: bool

class TextEmbedRequest(BaseModel):
    text: str
    description: Optional[str] = None

class TextEmbedResponse(BaseModel):
    embedding: List[float]
    embedding_shape: List[int]

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

    if valid_images:
        image_list = list(valid_images.values())
        embeddings = clip_service.encode_image_batch(image_list)
        captions = blip_service.generate_captions(image_list)

        for i, uid in enumerate(valid_images.keys()):
            original_item = next((item for item in request.images if item.unique_id == uid), None)
            results[uid] = BatchResultItem(
                unique_id=uid,
                filename=original_item.filename if original_item else "",
                embedding=embeddings[i].tolist(),
                embedding_shape=list(embeddings[i].shape),
                caption=captions[i]
            )

    # Add filenames for decode errors
    for item in request.images:
        if item.unique_id in results and not results[item.unique_id].filename:
            results[item.unique_id].filename = item.filename

    final_results = [results[item.unique_id] for item in request.images]
    return BatchEmbedAndCaptionResponse(results=final_results)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    status = await scheduler.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    if status.get("status") in {"completed", "failed"}:
        result = status.get("result")
        error = status.get("error")
        result_model = None
        if result:
            result_model = BatchEmbedAndCaptionResponse(**result)
        return JobStatusResponse(job_id=job_id, status=status["status"], result=result_model, error=error)
    return JobStatusResponse(job_id=job_id, status=status["status"])


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

@router.post("/embed_text", response_model=TextEmbedResponse)
async def embed_text_endpoint(request: TextEmbedRequest):
    """Embed a text string using the CLIP model and return the embedding."""
    if not clip_service.get_clip_model_status():
        raise HTTPException(status_code=503, detail="CLIP model is not available.")
    try:
        features = clip_service.encode_text_batch([request.text])
        embedding = features[0].detach().cpu().numpy().tolist()
        embedding_shape = list(features[0].shape)
        return TextEmbedResponse(embedding=embedding, embedding_shape=embedding_shape)
    except Exception as e:
        logger.error(f"Failed to embed text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to embed text: {e}") 