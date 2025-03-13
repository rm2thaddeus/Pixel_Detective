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
from utils.logger import logger
from config import (
    BLIP_MODEL_NAME, 
    BLIP_PROCESSOR_NAME, 
    BLIP_DEVICE, 
    BLIP_LOAD_8BIT,
    GPU_MEMORY_EFFICIENT
)

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

def generate_caption(image_path, metadata=None):
    """
    Generate a caption for an image using BLIP.

    Args:
        image_path: Path to the image file.
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
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        logger.error(f"Error opening image {image_path}: {e}")
        return "Error opening image"

    # Process the image with the processor
    inputs = _blip_processor(image, prompt, return_tensors="pt").to(_blip_model.device)

    # Generate caption
    output = _blip_model.generate(**inputs, max_length=75)
    caption = _blip_processor.decode(output[0], skip_special_tokens=True)

    # Clean up the caption if needed
    caption = caption.strip()
    return caption

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
    Sets up the device for BLIP model (CPU or GPU).
    Checks CUDA availability and initializes it if present.
    Handles potential CUDA initialization errors gracefully.
    
    Returns:
        torch.device: The selected device (CPU or GPU).
    """
    # Check CUDA availability
    if torch.cuda.is_available():
        try:
            # Get CUDA device count and properties before attempting to use it
            cuda_device_count = torch.cuda.device_count()
            cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Unknown"
            logger.info(f"BLIP: CUDA reports {cuda_device_count} available device(s): {cuda_device_name}")
            
            # Create a small tensor on CUDA to force initialization
            test_tensor = torch.zeros(1).cuda()
            
            # Verify the tensor is actually on CUDA
            if test_tensor.device.type != "cuda":
                raise RuntimeError("Test tensor not on CUDA despite cuda() call")
            
            # Do a small computation to fully initialize CUDA
            _ = test_tensor + 1
            
            logger.info("BLIP: CUDA initialized successfully")
            
            # Clean up test tensor
            del test_tensor
            torch.cuda.empty_cache()
            
            # Create a proper device object
            device = torch.device("cuda")
            
            # Log GPU memory
            if hasattr(torch.cuda, 'memory_allocated'):
                logger.info(f"BLIP: GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
                logger.info(f"BLIP: GPU memory reserved: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
            
            logger.info(f"BLIP: CUDA is available! Using device: {cuda_device_name}")
            
        except Exception as e:
            logger.error(f"BLIP: CUDA initialization error: {e}")
            logger.warning("BLIP: Falling back to CPU due to CUDA initialization error")
            device = torch.device("cpu")
    else:
        logger.info("CUDA not available for BLIP, using CPU")
        device = torch.device("cpu")
    
    # Store in session state if available
    if hasattr(st, 'session_state'):
        st.session_state.blip_device = device
    
    return device 