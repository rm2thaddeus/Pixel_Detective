# 📂 File Path: /project_root/models/blip_model.py
# 📌 Purpose: Provides functionality for generating image captions using the BLIP model.
# 🔄 Latest Changes: Updated to use regular BLIP model instead of BLIP-2 for better compatibility.
# ⚙️ Key Logic: Contains functions to load the BLIP model and generate captions for images.
# 🧠 Reasoning: BLIP provides high-quality image captions that can enhance metadata and search capabilities.

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

def setup_blip_device():
    """
    Set up the device for the BLIP model.
    
    Returns:
        torch.device: The device to use (CUDA or CPU).
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA is available for BLIP! Found device: {device_name}")
        
        # Empty cache first
        torch.cuda.empty_cache()
        
        # Check CUDA version
        logger.info(f"CUDA version: {torch.version.cuda}")
        
        # Create a proper device object
        device = torch.device(BLIP_DEVICE)
        
        # Log GPU memory
        if hasattr(torch.cuda, 'memory_allocated'):
            logger.info(f"GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
            logger.info(f"GPU memory reserved: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
    else:
        logger.info("CUDA not available for BLIP, using CPU")
        device = torch.device("cpu")
    
    return device

def load_blip_model():
    """
    Load the BLIP model and processor.
    
    Returns:
        tuple: (processor, model) - The BLIP processor and model.
    """
    # Check if model is already loaded in session state
    if hasattr(st, 'session_state') and 'blip_model' in st.session_state and st.session_state.blip_model is not None:
        return st.session_state.blip_processor, st.session_state.blip_model
    
    device = setup_blip_device()
    
    try:
        logger.info(f"Loading BLIP processor from {BLIP_PROCESSOR_NAME}...")
        processor = BlipProcessor.from_pretrained(BLIP_PROCESSOR_NAME)
        
        logger.info(f"Loading BLIP model from {BLIP_MODEL_NAME}...")
        # Load model with memory optimizations for 6GB GPU
        model = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL_NAME)
        
        # Move model to device
        if device.type == "cuda":
            model = model.to(device)
        
        model.eval()  # Set to evaluation mode
        
        # Store in session state if available
        if hasattr(st, 'session_state'):
            st.session_state.blip_processor = processor
            st.session_state.blip_model = model
            st.session_state.blip_device = device
        
        logger.info("BLIP model loaded successfully")
        return processor, model
    
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
    Generate a caption for the given image using the BLIP model.
    
    Args:
        image_path (str): The path to the image file.
        metadata (dict, optional): Metadata for the image to help with prompt selection.
        
    Returns:
        str: A generated caption for the image.
    """
    try:
        # Try to extract metadata if not provided
        if metadata is None:
            try:
                from metadata_extractor import extract_metadata
                metadata = extract_metadata(image_path)
            except Exception as e:
                logger.warning(f"Could not extract metadata for prompt selection: {e}")
                metadata = {}
        
        # Get appropriate prompt based on metadata
        prompt = _get_caption_prompt(metadata)
        
        # Load BLIP model and processor
        processor, model = load_blip_model()
        device = st.session_state.blip_device if hasattr(st, 'session_state') and 'blip_device' in st.session_state else setup_blip_device()
        
        # Open and preprocess the image
        start_time = time.time()
        image = Image.open(image_path).convert('RGB')
        
        # Process the image with the prompt
        inputs = processor(image, text=prompt, return_tensors="pt").to(device)
        
        # Generate caption
        with torch.no_grad():
            # Use memory-efficient generation if enabled
            if GPU_MEMORY_EFFICIENT:
                # Set a reasonable max length to avoid excessive memory usage
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=75,
                    min_length=10,
                    num_beams=5,
                    length_penalty=1.0,
                    repetition_penalty=1.5
                )
            else:
                outputs = model.generate(**inputs)
        
        # Decode the generated caption
        caption = processor.decode(outputs[0], skip_special_tokens=True)
        
        # Clean up the caption
        caption = caption.strip()
        if prompt in caption:
            # Remove the prompt from the beginning of the caption
            caption = caption.replace(prompt, "", 1).strip()
        
        # Log generation time
        generation_time = time.time() - start_time
        logger.info(f"Caption generated in {generation_time:.2f} seconds: {caption}")
        
        # Clean up GPU memory
        if device.type == "cuda" and GPU_MEMORY_EFFICIENT:
            del inputs, outputs
            torch.cuda.empty_cache()
            gc.collect()
        
        return caption
    
    except Exception as e:
        logger.error(f"Error generating caption for {image_path}: {e}")
        # Fallback to a simple caption if anything goes wrong
        filename = os.path.basename(image_path)
        return f"Image file {filename}"

def unload_blip_model():
    """
    Unload the BLIP model to free up GPU memory.
    """
    if hasattr(st, 'session_state') and 'blip_model' in st.session_state:
        del st.session_state.blip_model
        del st.session_state.blip_processor
        if 'blip_device' in st.session_state:
            del st.session_state.blip_device
    
    # Force garbage collection and clear CUDA cache
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    logger.info("BLIP model unloaded from memory") 