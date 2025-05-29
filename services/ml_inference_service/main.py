from fastapi import FastAPI, HTTPException
import torch
import clip # from openai
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import os
import rawpy
import time # For logging model load times
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import clip
    logger.info(f"Successfully imported 'clip'. Path: {clip.__file__}")
except ImportError as e:
    logger.error(f"Failed to import 'clip': {e}")
    clip = None # Ensure clip is None if import fails, to be caught later

app = FastAPI()

# --- Configuration (Could be moved to environment variables or a config file) ---
CLIP_MODEL_NAME = os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")
BLIP_MODEL_NAME = os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")
# Forcing CPU for now for broader compatibility in a mixed environment, can be parameterized
DEVICE_PREFERENCE = os.environ.get("DEVICE_PREFERENCE", "cuda") # "cuda" or "cpu"

# --- Global Variables for Models and Processors ---
clip_model = None
clip_preprocess = None
blip_model = None
blip_processor = None
device = None

# --- Device Setup ---
def setup_device():
    global device
    # Forcing CPU for initial service implementation to avoid CUDA complexities in Docker setup for all users.
    # This can be enhanced later with env variables to choose \'cuda\' if available.
    if DEVICE_PREFERENCE == "cuda" and torch.cuda.is_available():
        try:
            torch.zeros(1).cuda() # Test CUDA
            device = torch.device("cuda")
            logger.info("CUDA is available. Using CUDA.")
        except Exception as e:
            logger.error(f"CUDA selected but initialization failed: {e}. Falling back to CPU.")
            device = torch.device("cpu")
    else:
        if DEVICE_PREFERENCE == "cuda":
            logger.warning("CUDA was preferred but is not available. Using CPU.")
        else:
            logger.info("CPU is preferred. Using CPU.")
        device = torch.device("cpu")
    logger.info(f"Using device: {device}")

# --- Model Loading --- 
async def load_models_on_startup():
    global clip_model, clip_preprocess, blip_model, blip_processor, device
    
    setup_device() # Determine device first

    # Load CLIP
    try:
        logger.info(f"Loading CLIP model ({CLIP_MODEL_NAME}) on {device}...")
        start_time = time.time()

        # Diagnostic prints for clip module
        logger.info(f"Attempting to load CLIP. Imported 'clip' module: {clip}")
        logger.info(f"Attributes of imported 'clip' module: {dir(clip)}")
        logger.info(f"Path of imported 'clip' module: {hasattr(clip, '__file__') and clip.__file__ or 'Unknown'}")

        clip_model_instance, clip_preprocess_instance = clip.load(CLIP_MODEL_NAME, device=device)
        clip_model = clip_model_instance.to(device)
        clip_preprocess = clip_preprocess_instance
        end_time = time.time()
        logger.info(f"CLIP model loaded in {end_time - start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Error loading CLIP model: {e}", exc_info=True)
        # Decide if service should fail to start or run degraded

    # Load BLIP
    try:
        logger.info(f"Loading BLIP model ({BLIP_MODEL_NAME}) on {device}...")
        start_time = time.time()
        blip_processor_instance = BlipProcessor.from_pretrained(BLIP_MODEL_NAME)
        blip_model_instance = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL_NAME)
        blip_model = blip_model_instance.to(device)
        blip_processor = blip_processor_instance
        end_time = time.time()
        logger.info(f"BLIP model loaded in {end_time - start_time:.2f} seconds.")
    except Exception as e:
        logger.error(f"Error loading BLIP model: {e}", exc_info=True)
        # Decide if service should fail to start or run degraded

@app.on_event("startup")
async def startup_event():
    logger.info("ML Inference Service starting up. Loading models...")
    await load_models_on_startup()
    logger.info("Models loaded (or attempted). Service ready.")

# --- Image Processing Utilities (Adapted from clip_model.py and blip_model.py) ---
def _open_image(image_path: str) -> Image.Image:
    try:
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.dng':
            try:
                with rawpy.imread(image_path) as raw:
                    rgb = raw.postprocess()
                return Image.fromarray(rgb).convert("RGB")
            except Exception as raw_e:
                logger.error(f"Error loading DNG file {image_path} with rawpy: {raw_e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error processing DNG image: {raw_e}")
        else:
            return Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        logger.error(f"Image file not found: {image_path}")
        raise HTTPException(status_code=404, detail=f"Image file not found: {image_path}")
    except Exception as e:
        logger.error(f"Error opening image {image_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error opening image: {e}")

# --- API Endpoints ---
@app.post("/embed")
async def embed_image(image_data: dict):
    global clip_model, clip_preprocess, device
    if not clip_model or not clip_preprocess:
        logger.error("CLIP model not loaded. Embedding not possible.")
        raise HTTPException(status_code=503, detail="CLIP model is not available.")

    image_path = image_data.get("image_path")
    if not image_path:
        raise HTTPException(status_code=400, detail="'image_path' not provided.")

    logger.info(f"Received request to embed image: {image_path}")
    try:
        image = _open_image(image_path)
        image_input = clip_preprocess(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = clip_model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        
        embedding = image_features.cpu().numpy().squeeze().tolist()
        logger.info(f"Successfully embedded image: {image_path}")
        return {"embedding": embedding, "image_path": image_path}
    except HTTPException: # Re-raise HTTP exceptions from _open_image
        raise
    except Exception as e:
        logger.error(f"Error generating CLIP embedding for {image_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate CLIP embedding: {e}")

@app.post("/caption")
async def caption_image(image_data: dict):
    global blip_model, blip_processor, device
    if not blip_model or not blip_processor:
        logger.error("BLIP model not loaded. Captioning not possible.")
        raise HTTPException(status_code=503, detail="BLIP model is not available.")

    image_path = image_data.get("image_path")
    if not image_path:
        raise HTTPException(status_code=400, detail="'image_path' not provided.")
    
    logger.info(f"Received request to caption image: {image_path}")
    try:
        image = _open_image(image_path)
        # For BLIP, the prompt is optional for basic captioning.
        # The original blip_model.py had prompt engineering logic (_get_caption_prompt)
        # which could be re-integrated here if metadata is passed or a default is desired.
        prompt = "" 
        inputs = blip_processor(image, text=prompt, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = blip_model.generate(**inputs, max_length=75)
        
        caption = blip_processor.decode(outputs[0], skip_special_tokens=True).strip()
        logger.info(f"Successfully captioned image: {image_path}")
        return {"caption": caption, "image_path": image_path}
    except HTTPException: # Re-raise HTTP exceptions from _open_image
        raise
    except Exception as e:
        logger.error(f"Error generating BLIP caption for {image_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate BLIP caption: {e}")

if __name__ == "__main__":
    # This part is for local debugging of this script, not for when run by uvicorn in Docker
    import uvicorn
    logger.info("Starting ML Inference Service for local debugging...")
    # Note: For local debugging, models will load upon running this script directly.
    # Ensure your environment has the necessary model files accessible or they will be downloaded.
    uvicorn.run(app, host="0.0.0.0", port=8001) 