# 📂 File Path: /project_root/models/blip_model.py
# 📌 Purpose: Handles loading and using the BLIP model for image captioning.
# 🔄 Latest Changes: Created module for BLIP model interactions.
# ⚙️ Key Logic: Provides functions to load, unload, and use the BLIP model.
# 🧠 Reasoning: Separates BLIP-specific code for better organization.

"""
BLIP model for image captioning.
"""
import os
import torch
import time
import gc
from PIL import Image
import streamlit as st
from transformers import BlipProcessor, BlipForConditionalGeneration
from utils.logger import logger # This will be a broken import in archive
from config import (
    BLIP_MODEL_NAME, 
    BLIP_PROCESSOR_NAME, 
    BLIP_DEVICE, 
    BLIP_LOAD_8BIT,
    GPU_MEMORY_EFFICIENT
) # This will be a broken import in archive

# Templates for caption prompts based on image type
STREET_PROMPT = "a street photography image of"
PEOPLE_PROMPT = "a candid photograph of people"
ARCHITECTURE_PROMPT = "an architectural photograph of"
LANDSCAPE_PROMPT = "a landscape photograph of"
DEFAULT_PROMPT = "a photograph of"

# Global variables to store model and processor
_blip_model = None
_blip_processor = None

def load_blip_model(model_name=BLIP_MODEL_NAME, device=None):
    """
    Load the BLIP model for image captioning.
    
    Args:
        model_name (str): The name of the BLIP model to load
        device (torch.device): The device to load the model on
        
    Returns:
        tuple: (model, processor) - The BLIP model and processor
    """
    global _blip_model, _blip_processor
    
    if _blip_model is not None:
        return _blip_model, _blip_processor
    
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    logger.info(f"Starting to load BLIP model on {device}...")
    
    try:
        start_time = time.time()
        
        if isinstance(device, str):
            device = torch.device(device)
        
        # Load processor first
        logger.info(f"Loading BLIP processor from {model_name}...")
        processor = BlipProcessor.from_pretrained(model_name)
        
        # Load model with specific device
        logger.info(f"Loading BLIP model from {model_name}...")
        
        # Log current CUDA device information if using CUDA
        if device.type == "cuda":
            logger.info(f"CUDA device count: {torch.cuda.device_count()}")
            logger.info(f"Current CUDA device: {torch.cuda.current_device()}")
        
        # Attempt to load model on desired device, fallback to CPU on OOM
        try:
            logger.info(f"Loading BLIP model on {device}...")
            model = BlipForConditionalGeneration.from_pretrained(model_name).to(device)
        except RuntimeError as oom_error:
            logger.error(f"CUDA out of memory when loading BLIP on {device}: {oom_error}")
            logger.warning("Falling back to CPU for BLIP model.")
            device = torch.device("cpu")
            model = BlipForConditionalGeneration.from_pretrained(model_name).to(device)
        
        # Verify model is on the correct device
        model_device = next(model.parameters()).device
        logger.info(f"BLIP model is loaded on: {model_device}")
        
        # Store model and processor in global variables
        _blip_model = model
        _blip_processor = processor
        
        logger.info(f"BLIP model loaded successfully on {device}")
        
        return model, processor
    except Exception as e:
        logger.error(f"Error loading BLIP model: {e}")
        raise

def _get_caption_prompt(metadata):
    """
    Determine the appropriate caption prompt based on metadata.
    
    Args:
        metadata (dict): Image metadata.
        
    Returns:
        str: A prompt for the BLIP model.
    """
    # Check for tags or keywords that indicate image type
    tags = []
    
    # Try to get tags from metadata
    if metadata and 'tags' in metadata and metadata['tags']:
        if isinstance(metadata['tags'], list):
            tags = metadata['tags']
        elif isinstance(metadata['tags'], str):
            tags = [metadata['tags']]
    
    # Try to get keywords from metadata if tags are empty
    if not tags and metadata and 'Keywords' in metadata and metadata['Keywords']:
        if isinstance(metadata['Keywords'], list):
            tags = metadata['Keywords']
        elif isinstance(metadata['Keywords'], str):
            tags = [metadata['Keywords']]
    
    # Convert tags to lowercase for easier matching
    tags_lower = [tag.lower() if isinstance(tag, str) else "" for tag in tags]
    
    # Determine prompt based on tags
    if any(keyword in " ".join(tags_lower) for keyword in ['street', 'urban', 'city']):
        return STREET_PROMPT
    elif any(keyword in " ".join(tags_lower) for keyword in ['people', 'person', 'portrait', 'candid']):
        return PEOPLE_PROMPT
    elif any(keyword in " ".join(tags_lower) for keyword in ['architecture', 'building', 'structure']):
        return ARCHITECTURE_PROMPT
    elif any(keyword in " ".join(tags_lower) for keyword in ['landscape', 'nature', 'outdoor']):
        return LANDSCAPE_PROMPT
    else:
        return DEFAULT_PROMPT

def generate_caption(image_or_path, metadata=None):
    """
    Generate a caption for an image using BLIP.

    Args:
        image_or_path: Path to the image file or a PIL.Image.Image object.
        metadata: Optional metadata (not used for caption generation).

    Returns:
        str: The generated caption.
    """
    # Ensure BLIP model is loaded
    global _blip_model, _blip_processor
    if _blip_model is None or _blip_processor is None:
        load_blip_model()

    prompt = ""  # No prompt engineering based on metadata
    try:
        if isinstance(image_or_path, Image.Image):
            image = image_or_path.convert("RGB")
        else:
            image = Image.open(image_or_path).convert("RGB")
    except Exception as e:
        logger.error(f"Error opening image {image_or_path}: {e}")
        return "Error opening image"

    # Process the image with the processor
    inputs = _blip_processor(image, prompt, return_tensors="pt").to(_blip_model.device)

    # Generate caption
    output = _blip_model.generate(**inputs, max_length=75)
    caption = _blip_processor.decode(output[0], skip_special_tokens=True)

    # Clean up the caption if needed
    caption = caption.strip()
    return caption

def generate_caption_from_model(model, processor, image_or_path, device, metadata=None):
    """
    Generate a caption for an image using a provided BLIP model and processor.

    Args:
        model: The pre-loaded BLIP model.
        processor: The pre-loaded BLIP processor.
        image_or_path: Path to the image file or a PIL.Image.Image object.
        device: The torch device the model is on.
        metadata: Optional metadata (currently not used for caption generation here).

    Returns:
        str: The generated caption.
    """
    if model is None or processor is None:
        logger.error("BLIP model or processor not provided to generate_caption_from_model.")
        return "Error: Model or processor not provided."

    prompt = ""  # No prompt engineering based on metadata in this version
    try:
        if isinstance(image_or_path, Image.Image):
            image = image_or_path.convert("RGB")
        else:
            image = Image.open(image_or_path).convert("RGB")
    except Exception as e:
        logger.error(f"Error opening image {image_or_path}: {e}")
        return "Error opening image"

    try:
        # Ensure inputs are on the same device as the model
        inputs = processor(image, prompt, return_tensors="pt").to(device)

        # Generate caption
        output = model.generate(**inputs, max_length=75)
        caption = processor.decode(output[0], skip_special_tokens=True)
        caption = caption.strip()
        return caption
    except Exception as e:
        logger.error(f"Error during caption generation with provided model: {e}", exc_info=True)
        return f"Error generating caption: {e}"

def unload_blip_model():
    """
    Unload the BLIP model from memory.
    
    Returns:
        bool: True if the model was unloaded, False otherwise
    """
    global _blip_model, _blip_processor
    
    if _blip_model is None:
        return False
    
    try:
        # Record GPU memory before unloading if using CUDA
        if torch.cuda.is_available():
            before_mem = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
        
        # Set model and processor to None
        _blip_model = None
        _blip_processor = None
        
        # Clean up CUDA cache if using CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            after_mem = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
            logger.info(f"GPU memory still allocated after BLIP unload: {after_mem:.2f} MB")
        
        logger.info("BLIP model unloaded from memory")
        return True
    except Exception as e:
        logger.error(f"Error unloading BLIP model: {e}")
        return False

def setup_blip_device():
    """
    Set up the device for the BLIP model based on config.
    Returns:
        torch.device: The device to use for BLIP model.
    """
    # Use BLIP_DEVICE from config if specified and valid
    if BLIP_DEVICE and BLIP_DEVICE.lower() in ["cuda", "cpu"]:
        if BLIP_DEVICE.lower() == "cuda" and torch.cuda.is_available():
            logger.info(f"Using configured BLIP_DEVICE: cuda")
            return torch.device("cuda")
        elif BLIP_DEVICE.lower() == "cpu":
            logger.info(f"Using configured BLIP_DEVICE: cpu")
            return torch.device("cpu")
        else:
            logger.warning(f"Configured BLIP_DEVICE='{BLIP_DEVICE}' but CUDA not available or invalid. Auto-detecting.")
    
    # Auto-detect if no valid BLIP_DEVICE config
    if torch.cuda.is_available():
        logger.info("CUDA available. Using CUDA for BLIP model.")
        return torch.device("cuda")
    else:
        logger.info("CUDA not available. Using CPU for BLIP model.")
        return torch.device("cpu")


# For testing purposes
if __name__ == '__main__':
    # Example usage (requires images in a ./test_images folder)
    # Ensure you have BLIP_MODEL_NAME defined in config.py or set it directly
    # And utils.logger configured
    logging.basicConfig(level=logging.INFO)
    # BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-large" # Example

    # Create dummy config and logger if not present
    class DummyConfig:
        BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base"
        BLIP_PROCESSOR_NAME = "Salesforce/blip-image-captioning-base"
        BLIP_DEVICE = "cpu" # Force CPU for simpler testing if no GPU
        BLIP_LOAD_8BIT = False
        GPU_MEMORY_EFFICIENT = False

    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    if 'config' not in globals() or not hasattr(config, 'BLIP_MODEL_NAME'):
        config = DummyConfig()
        BLIP_MODEL_NAME = config.BLIP_MODEL_NAME
        BLIP_PROCESSOR_NAME = config.BLIP_PROCESSOR_NAME
        BLIP_DEVICE = config.BLIP_DEVICE
        BLIP_LOAD_8BIT = config.BLIP_LOAD_8BIT

    if 'logger' not in globals() or isinstance(logger, logging.RootLogger):
        logger = DummyLogger()

    try:
        # Test model loading
        logger.info("Testing BLIP model loading...")
        # Force CPU for this test to avoid GPU issues in CI/CD or diverse environments
        model, processor = load_blip_model(device=torch.device("cpu")) 
        logger.info("BLIP model loaded successfully.")
        
        # Create a dummy image file for testing if it doesn't exist
        test_image_dir = "test_images"
        if not os.path.exists(test_image_dir):
            os.makedirs(test_image_dir)
        dummy_image_path = os.path.join(test_image_dir, "dummy_blip_test.png")
        if not os.path.exists(dummy_image_path):
            try:
                dummy_img = Image.new('RGB', (60, 30), color = 'blue')
                dummy_img.save(dummy_image_path)
                logger.info(f"Created dummy image: {dummy_image_path}")
            except Exception as e_img:
                logger.error(f"Could not create dummy image: {e_img}")

        if os.path.exists(dummy_image_path):
            # Test caption generation
            logger.info(f"Testing caption generation with {dummy_image_path}...")
            caption = generate_caption(dummy_image_path)
            logger.info(f"Generated caption: {caption}")
            assert isinstance(caption, str) and len(caption) > 0, "Caption generation failed or returned empty."
            logger.info("Caption generation test successful.")
        else:
            logger.warning("Skipping caption generation test as dummy image could not be created/found.")

        # Test model unloading
        logger.info("Testing BLIP model unloading...")
        unloaded = unload_blip_model()
        logger.info(f"BLIP model unloaded: {unloaded}")
        assert unloaded, "BLIP model unload failed"

    except Exception as e:
        logger.error(f"An error occurred during BLIP model testing: {e}", exc_info=True)

    finally:
        # Clean up dummy image
        if os.path.exists(dummy_image_path):
            try:
                os.remove(dummy_image_path)
                # os.rmdir(test_image_dir) # Only if dir is empty and you want to remove it
                logger.info(f"Cleaned up dummy image: {dummy_image_path}")
            except Exception as e_clean:
                logger.error(f"Error cleaning up dummy image: {e_clean}") 