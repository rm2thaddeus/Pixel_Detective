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
from typing import Dict, Any, Tuple, List, Optional

# Configure basic logging
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

app = FastAPI(title="ML Inference Service")
v1_router = APIRouter(prefix="/api/v1") # Define v1 router

# --- Configuration ---
CLIP_MODEL_NAME_CONFIG = os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")
BLIP_MODEL_NAME_CONFIG = os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")
DEVICE_PREFERENCE = os.environ.get("DEVICE_PREFERENCE", "cuda")

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
        
        # Handle DNG separately if needed, though PIL might handle some via libraries
        # For simplicity, assuming PIL can handle common formats from bytes.
        # If specific DNG handling from clip_model.py (rawpy) is strictly needed for all DNGs:
        # if request.filename.lower().endswith('.dng'):
        #     with rawpy.imread(io.BytesIO(image_bytes)) as raw:
        #         rgb = raw.postprocess()
        #     image = Image.fromarray(rgb).convert("RGB")
        # else:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        image_input = clip_preprocess_instance(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = clip_model_instance.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        
        embedding = image_features.cpu().numpy().squeeze().tolist() # tolist for JSON
        
        logger.info(f"Successfully embedded image: {request.filename or 'untitled'}")
        return {
            "filename": request.filename,
            "embedding": embedding,
            "embedding_shape": list(np.array(embedding).shape),
            "model_name": CLIP_MODEL_NAME_CONFIG,
            "device_used": str(device)
        }
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
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # BLIP doesn't typically use a conditional prompt string unless you want to guide it.
        # For general captioning, an empty prompt or task-specific default is fine.
        # inputs = blip_processor_instance(image, return_tensors="pt").to(device) # Simple case
        inputs = blip_processor_instance(images=image, text=None, return_tensors="pt").to(device)


        with torch.no_grad():
            output_ids = blip_model_instance.generate(**inputs, max_length=75) # Added max_length
        
        caption = blip_processor_instance.decode(output_ids[0], skip_special_tokens=True)
        
        logger.info(f"Successfully captioned image: {request.filename or 'untitled'}")
        return {
            "filename": request.filename,
            "caption": caption.strip(),
            "model_name": BLIP_MODEL_NAME_CONFIG,
            "device_used": str(device)
        }
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

# --- Batch Processing Endpoint ---
@v1_router.post("/batch_embed_and_caption", response_model=BatchEmbedAndCaptionResponse)
async def batch_embed_and_caption_endpoint_v1(request: BatchEmbedAndCaptionRequest = Body(...)):
    if not clip_model_instance or not clip_preprocess_instance or not blip_model_instance or not blip_processor_instance:
        logger.error("/batch_embed_and_caption call failed: One or more models not loaded.")
        raise HTTPException(status_code=503, detail="One or more models are not available. Please check service logs.")

    batch_results: List[BatchResultItem] = []
    if not request.images:
        return BatchEmbedAndCaptionResponse(results=[])

    logger.info(f"Received batch request for {len(request.images)} images.")

    pil_images = []
    processed_indices = [] # Keep track of indices of successfully preprocessed images
    request_items_for_processing = [] # Store corresponding request items

    for i, item in enumerate(request.images):
        try:
            image_bytes = base64.b64decode(item.image_base64)
            # DNG handling - simplified, assuming PIL can handle it from bytes or we rely on general format support
            # For more robust DNG, rawpy logic would be here as in single endpoints.
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            pil_images.append(pil_img)
            processed_indices.append(i) # Store original index
            request_items_for_processing.append(item) # Store corresponding request item
        except Exception as e:
            logger.error(f"Error decoding/preprocessing image {item.filename} (ID: {item.unique_id}) for batch: {e}")
            batch_results.append(BatchResultItem(
                unique_id=item.unique_id,
                filename=item.filename,
                error=f"Failed to decode or preprocess image: {str(e)}"
            ))
    
    # Filter out items that failed preprocessing for model inference
    if not pil_images: # All images failed preprocessing
        logger.warning("All images in batch failed preprocessing. Returning empty results for model inference part.")
        # Errors for failed preprocessing items are already in batch_results
        return BatchEmbedAndCaptionResponse(results=batch_results)

    # Get CLIP embeddings for successfully preprocessed images
    clip_embeddings = []
    if clip_model_instance and clip_preprocess_instance:
        # Preprocess all images for CLIP together if possible (check clip_preprocess_instance type)
        # Assuming clip_preprocess_instance can take a list of PIL images or individual application
        try:
            # This part needs to be careful with how clip_preprocess_instance handles a list
            # If it expects individual images, loop here. If it can batch, then batch.
            # For simplicity, let's assume individual preprocessing for now, then stack.
            image_inputs_clip = torch.stack([clip_preprocess_instance(img) for img in pil_images]).to(device)
            with torch.no_grad():
                image_features = clip_model_instance.encode_image(image_inputs_clip)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            clip_embeddings = image_features.cpu().numpy()
        except Exception as e:
            logger.error(f"Error during CLIP batch embedding: {e}")
            # Mark all items in this batch as errored for CLIP part
            for idx, original_batch_idx in enumerate(processed_indices):
                req_item = request_items_for_processing[idx]
                # Find if this item already has an error, if so, append. If not, create.
                found_result = next((r for r in batch_results if r.unique_id == req_item.unique_id), None)
                if found_result:
                    found_result.error = (found_result.error + "; CLIP embedding failed: " + str(e)) if found_result.error else "CLIP embedding failed: " + str(e)
                else: # Should not happen if preprocessing errors are handled by adding to batch_results first
                    batch_results.append(BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error="CLIP embedding failed: " + str(e)))
    else:
        logger.warning("CLIP model not available for batch processing.")
        # Add error to all items that were successfully preprocessed but can't get embedding
        for idx, original_batch_idx in enumerate(processed_indices):
            req_item = request_items_for_processing[idx]
            found_result = next((r for r in batch_results if r.unique_id == req_item.unique_id), None)
            if found_result:
                 found_result.error = (found_result.error + "; CLIP model unavailable") if found_result.error else "CLIP model unavailable"
            else:
                 batch_results.append(BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error="CLIP model unavailable"))

    # Get BLIP captions for successfully preprocessed images
    blip_captions = [None] * len(pil_images)
    if blip_model_instance and blip_processor_instance:
        try:
            # BLIP usually processes one by one for captioning in a loop or small batches
            for i, img in enumerate(pil_images):
                inputs = blip_processor_instance(images=img, text=None, return_tensors="pt").to(device)
                with torch.no_grad():
                    output_ids = blip_model_instance.generate(**inputs, max_length=75)
                blip_captions[i] = blip_processor_instance.decode(output_ids[0], skip_special_tokens=True).strip()
        except Exception as e:
            logger.error(f"Error during BLIP batch captioning: {e}")
            # Mark all items as errored for BLIP part
            for idx, original_batch_idx in enumerate(processed_indices):
                req_item = request_items_for_processing[idx]
                found_result = next((r for r in batch_results if r.unique_id == req_item.unique_id), None)
                if found_result:
                    found_result.error = (found_result.error + "; BLIP captioning failed: " + str(e)) if found_result.error else "BLIP captioning failed: " + str(e)
                else:
                    batch_results.append(BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error="BLIP captioning failed: " + str(e)))
    else:
        logger.warning("BLIP model not available for batch processing.")
        for idx, original_batch_idx in enumerate(processed_indices):
            req_item = request_items_for_processing[idx]
            found_result = next((r for r in batch_results if r.unique_id == req_item.unique_id), None)
            if found_result:
                 found_result.error = (found_result.error + "; BLIP model unavailable") if found_result.error else "BLIP model unavailable"
            else:
                 batch_results.append(BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error="BLIP model unavailable"))

    # Combine results
    # Iterate through the successfully preprocessed items and update/add to batch_results
    for idx, original_batch_idx in enumerate(processed_indices):
        item = request_items_for_processing[idx] # The original request item for this successfully preprocessed image
        
        # Check if this item already exists in batch_results (e.g. due to a preprocessing error being logged)
        # This logic can be complex if an item fails one model but not another.
        # The current structure adds errors to existing entries or creates new ones.
        # We need to ensure we are updating the correct BatchResultItem or creating it if it was fully successful up to this point.

        existing_result_index = -1
        for i, res in enumerate(batch_results):
            if res.unique_id == item.unique_id:
                existing_result_index = i
                break
        
        current_result = None
        if existing_result_index != -1:
            current_result = batch_results[existing_result_index]
        else:
            current_result = BatchResultItem(unique_id=item.unique_id, filename=item.filename)
            # This new item needs to be appended later if it wasn't found
            # However, items that passed preprocessing should not need this unless errors are cleared.
            # Let's assume items that passed preprocessing don't have an error entry yet, or their error entry is what we update.
            # This means the `batch_results.append` in the error handling above for CLIP/BLIP already created the necessary entries.

        # Update with embedding if available and no critical error for this item already
        if idx < len(clip_embeddings) and clip_embeddings[idx] is not None and (not current_result.error or "CLIP" not in current_result.error):
            current_result.embedding = clip_embeddings[idx].squeeze().tolist()
            current_result.embedding_shape = list(np.array(clip_embeddings[idx].squeeze()).shape)
        elif not current_result.error or "CLIP" not in current_result.error: # If embedding is None but no specific CLIP error logged for this item yet
            current_result.error = (current_result.error + "; Embedding not generated") if current_result.error else "Embedding not generated"

        # Update with caption if available and no critical error for this item already
        if idx < len(blip_captions) and blip_captions[idx] is not None and (not current_result.error or "BLIP" not in current_result.error):
            current_result.caption = blip_captions[idx]
        elif not current_result.error or "BLIP" not in current_result.error: # If caption is None but no specific BLIP error logged for this item yet
            current_result.error = (current_result.error + "; Caption not generated") if current_result.error else "Caption not generated"
        
        # Update model names and device (these are constant for the batch)
        current_result.model_name_clip = CLIP_MODEL_NAME_CONFIG
        current_result.model_name_blip = BLIP_MODEL_NAME_CONFIG
        current_result.device_used = str(device) # Actual device used

        if existing_result_index == -1 and not current_result.error: # Only append if it's a new, error-free result
            # This case should ideally not be hit often if error handling above creates the items.
            # This ensures items that passed everything are added if they somehow weren't.
             batch_results.append(current_result)
        elif existing_result_index != -1: # If it existed, update it in place
            batch_results[existing_result_index] = current_result
        elif current_result.error and existing_result_index == -1: # It has an error and wasn't in batch_results (e.g. only preproc error)
             batch_results.append(current_result) # This was missing, ensure errored items from preproc are kept


    logger.info(f"Batch processing completed. Returning {len(batch_results)} results.")
    return BatchEmbedAndCaptionResponse(results=batch_results)

app.include_router(v1_router) # Add the v1 router to the main app

if __name__ == "__main__":
    import uvicorn
    # Note: For production, consider more robust runner like Gunicorn with Uvicorn workers
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001))) 