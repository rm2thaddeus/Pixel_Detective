from fastapi import FastAPI, HTTPException, Body
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

@app.post("/embed", response_model=Dict[str, Any])
async def embed_image_endpoint(request: EmbedRequest = Body(...)):
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

@app.post("/caption", response_model=Dict[str, Any])
async def caption_image_endpoint(request: CaptionRequest = Body(...)):
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
@app.post("/batch_embed_and_caption", response_model=BatchEmbedAndCaptionResponse)
async def batch_embed_and_caption_endpoint(request: BatchEmbedAndCaptionRequest = Body(...)):
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
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            pil_images.append(pil_image)
            processed_indices.append(i)
            request_items_for_processing.append(item)
        except Exception as e:
            logger.error(f"Error decoding/opening image {item.filename} (ID: {item.unique_id}) in batch: {e}")
            batch_results.append(BatchResultItem(
                unique_id=item.unique_id, 
                filename=item.filename, 
                error=f"Failed to decode or open image: {str(e)}"
            ))
    
    # Initialize full results list with potential errors for images that failed preprocessing
    # This ensures the response has an entry for every requested image, in order.
    full_results_list = [None] * len(request.images)
    for br_item in batch_results: # Place already errored items
        original_index = next((i for i, req_item in enumerate(request.images) if req_item.unique_id == br_item.unique_id), -1)
        if original_index != -1:
            full_results_list[original_index] = br_item

    if not pil_images: # All images failed decoding
        return BatchEmbedAndCaptionResponse(results=[r for r in full_results_list if r is not None])

    # --- CLIP Batch Embedding ---
    clip_embeddings_list = [None] * len(pil_images)
    try:
        logger.info(f"Processing {len(pil_images)} images for CLIP batch embedding...")
        # Preprocess all images for CLIP
        clip_image_inputs = torch.stack([clip_preprocess_instance(img) for img in pil_images]).to(device)

        with torch.no_grad():
            batch_image_features = clip_model_instance.encode_image(clip_image_inputs)
            batch_image_features /= batch_image_features.norm(dim=-1, keepdim=True)
        
        clip_embeddings_list = [features.cpu().numpy().squeeze().tolist() for features in batch_image_features]
        logger.info(f"Successfully embedded {len(pil_images)} images with CLIP.")
    except Exception as e:
        logger.error(f"Error during CLIP batch embedding: {e}", exc_info=True)
        # Mark all images in this batch as failed for CLIP if batch fails
        for i, req_item in enumerate(request_items_for_processing):
            error_msg = f"CLIP batch processing error: {str(e)}"
            # Find original index to update the correct item in full_results_list
            original_idx = next((j for j, r_item in enumerate(request.images) if r_item.unique_id == req_item.unique_id), -1)
            if original_idx != -1:
                if full_results_list[original_idx] is None:
                    full_results_list[original_idx] = BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error=error_msg)
                elif full_results_list[original_idx].error is None: # Only update if no prior decoding error
                    full_results_list[original_idx].error = error_msg
            # Skip BLIP if CLIP failed catastrophically for the batch
            # Ensure all items in full_results_list that weren't decoding errors get this new error
            for i_orig, orig_req_item in enumerate(request.images):
                if full_results_list[i_orig] is None:
                    full_results_list[i_orig] = BatchResultItem(unique_id=orig_req_item.unique_id, filename=orig_req_item.filename, error=error_msg)
                elif full_results_list[i_orig].error is None: # If it was a successfully decoded image, add this error
                    full_results_list[i_orig].error = error_msg
        return BatchEmbedAndCaptionResponse(results=[r for r in full_results_list if r is not None])

    # --- BLIP Iterative Captioning (on preprocessed batch where possible) ---
    blip_captions_list = [None] * len(pil_images)
    try:
        logger.info(f"Processing {len(pil_images)} images for BLIP captioning...")
        # BLIP processing is often image by image for generation, but we use the same PIL images
        for i, pil_img in enumerate(pil_images):
            try:
                # Reuse the PIL image, BLIP processor handles its own specific preprocessing
                blip_inputs = blip_processor_instance(images=pil_img, text=None, return_tensors="pt").to(device)
                with torch.no_grad():
                    output_ids = blip_model_instance.generate(**blip_inputs, max_length=75)
                caption = blip_processor_instance.decode(output_ids[0], skip_special_tokens=True).strip()
                blip_captions_list[i] = caption
            except Exception as caption_e:
                req_item = request_items_for_processing[i]
                logger.error(f"Error during BLIP captioning for {req_item.filename} (ID: {req_item.unique_id}): {caption_e}")
                blip_captions_list[i] = f"BLIP captioning error: {str(caption_e)}" # Store error as caption for now or mark error
                # Also mark this error in the main results structure
                original_idx = next((j for j, r_item in enumerate(request.images) if r_item.unique_id == req_item.unique_id), -1)
                if original_idx != -1:
                    err_msg = f"BLIP captioning error: {str(caption_e)}"
                    if full_results_list[original_idx] is None: # Should not happen if CLIP was successful
                        full_results_list[original_idx] = BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error=err_msg)
                    elif full_results_list[original_idx].error is None:
                        full_results_list[original_idx].error = err_msg # Add error if no previous one
                    else: # Append to existing error
                        full_results_list[original_idx].error += f"; {err_msg}"

        logger.info(f"Successfully processed {len(pil_images)} images with BLIP.")
    except Exception as e:
        logger.error(f"Error during BLIP batch captioning (outer loop): {e}", exc_info=True)
        # Mark all images as failed for BLIP if outer loop fails
        for i, req_item in enumerate(request_items_for_processing):
            error_msg = f"BLIP batch processing error (outer): {str(e)}"
            original_idx = next((j for j, r_item in enumerate(request.images) if r_item.unique_id == req_item.unique_id), -1)
            if original_idx != -1:
                if full_results_list[original_idx] is None:
                    full_results_list[original_idx] = BatchResultItem(unique_id=req_item.unique_id, filename=req_item.filename, error=error_msg)
                elif full_results_list[original_idx].error is None:
                    full_results_list[original_idx].error = error_msg
                else:
                    full_results_list[original_idx].error += f"; {error_msg}"

    # --- Assemble Results ---
    final_batch_results = []
    for i, req_item in enumerate(request_items_for_processing): # Iterate through successfully preprocessed items
        original_idx = next((j for j, r_item in enumerate(request.images) if r_item.unique_id == req_item.unique_id), -1)
        if original_idx == -1: continue # Should not happen

        current_error = full_results_list[original_idx].error if full_results_list[original_idx] and full_results_list[original_idx].error else None
        embedding_val = clip_embeddings_list[i] if i < len(clip_embeddings_list) and clip_embeddings_list[i] is not None and current_error is None else None
        caption_val = blip_captions_list[i] if i < len(blip_captions_list) and blip_captions_list[i] is not None and not (isinstance(blip_captions_list[i], str) and "error:" in blip_captions_list[i].lower()) and current_error is None else None
        
        # If BLIP captioning stored an error message in caption_val, parse it
        if isinstance(caption_val, str) and "error:" in caption_val.lower() and current_error is None:
            current_error = caption_val # Use BLIP's error string
            caption_val = None # Clear caption if it was an error message
        elif isinstance(caption_val, str) and "error:" in caption_val.lower() and current_error is not None:
            current_error += f"; {caption_val}" # Append BLIP error to existing error
            caption_val = None

        result_item = BatchResultItem(
            unique_id=req_item.unique_id,
            filename=req_item.filename,
            embedding=embedding_val,
            embedding_shape=list(np.array(embedding_val).shape) if embedding_val else None,
            caption=caption_val,
            error=current_error,
            device_used=str(device) # Actual device from global var
        )
        full_results_list[original_idx] = result_item # Update the placeholder in the full list
    
    # Filter out any Nones that might have remained if something went wrong with indexing
    final_clean_results = [r for r in full_results_list if r is not None]
    logger.info(f"Batch processing complete. Returning {len(final_clean_results)} results.")
    return BatchEmbedAndCaptionResponse(results=final_clean_results)

if __name__ == "__main__":
    import uvicorn
    # Note: For production, consider more robust runner like Gunicorn with Uvicorn workers
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8001))) 