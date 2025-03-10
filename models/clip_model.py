"""
CLIP model loading and image processing.
"""
import time
import torch
import clip
import gc
from PIL import Image
import streamlit as st
from utils.logger import logger
from config import CLIP_MODEL_NAME, GPU_MEMORY_EFFICIENT

def setup_device():
    """
    Set up the device for the CLIP model.
    
    Returns:
        torch.device: The device to use (CUDA or CPU).
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        logger.info(f"CUDA is available for CLIP! Found device: {device_name}")
        
        # Empty cache first
        torch.cuda.empty_cache()
        
        # Check CUDA version
        logger.info(f"CUDA version: {torch.version.cuda}")
        
        # Create a proper device object and make it the default
        device = torch.device("cuda:0")
        
        # Log GPU memory
        if hasattr(torch.cuda, 'memory_allocated'):
            logger.info(f"GPU memory allocated: {torch.cuda.memory_allocated(0) / 1024**2:.2f} MB")
            logger.info(f"GPU memory reserved: {torch.cuda.memory_reserved(0) / 1024**2:.2f} MB")
    else:
        logger.info("CUDA not available for CLIP, using CPU")
        device = torch.device("cpu")
    
    return device

def load_clip_model():
    """
    Load the CLIP model and return it.
    
    Returns:
        tuple: (model, preprocess) - The CLIP model and preprocessing function.
    """
    if hasattr(st, 'session_state') and 'clip_model' in st.session_state and st.session_state.clip_model is not None:
        return st.session_state.clip_model, st.session_state.clip_preprocess
    
    with st.spinner("🧠 Waking up the AI brain cells..."):
        start_time = time.time()
        device = setup_device()
        logger.info(f"Starting to load CLIP model on {device}...")
        
        # First check if CUDA is available
        if torch.cuda.is_available():
            cuda_device_count = torch.cuda.device_count()
            cuda_device_name = torch.cuda.get_device_name(0)
            logger.info(f"Found {cuda_device_count} CUDA device(s): {cuda_device_name}")
            
            # Clear GPU memory before loading model
            torch.cuda.empty_cache()
            gc.collect()
        
        # Load CLIP model with explicit device
        logger.info(f"Loading CLIP model with device={device}...")
        model, preprocess = clip.load(CLIP_MODEL_NAME, device=device)
        
        # Explicitly move model to device and set to evaluation mode
        model = model.to(device)
        model.eval()
        
        # Test if model is actually on GPU
        test_param = next(model.parameters())
        
        if str(test_param.device) == "cpu" and device.type == "cuda":
            logger.warning("⚠️ Model is still on CPU despite CUDA being available!")
            logger.info("Attempting to force model to GPU...")
            for param in model.parameters():
                param.data = param.data.to(device)
        
        # Store in session state
        if hasattr(st, 'session_state'):
            st.session_state.clip_model = model
            st.session_state.clip_preprocess = preprocess
            st.session_state.device = device
        
        load_time = time.time() - start_time
        logger.info(f"CLIP model loaded in {load_time:.2f} seconds")
        
        return model, preprocess

def process_image(image_path):
    """
    Processes an image and returns its embedding using the CLIP model.
    
    Args:
        image_path (str): Path to the image file.
        
    Returns:
        numpy.ndarray: The image embedding.
    """
    # Load CLIP model if not already loaded
    if not hasattr(st, 'session_state') or 'clip_model' not in st.session_state or st.session_state.clip_model is None:
        model, preprocess = load_clip_model()
    else:
        model = st.session_state.clip_model
        preprocess = st.session_state.clip_preprocess
    
    device = st.session_state.device if hasattr(st, 'session_state') and 'device' in st.session_state else setup_device()
    
    start_time = time.time()
    
    try:
        # Open and preprocess the image
        image = Image.open(image_path).convert('RGB')
        image_input = preprocess(image).unsqueeze(0).to(device)
        
        # Generate the image embedding with memory optimization
        with torch.no_grad():
            if GPU_MEMORY_EFFICIENT:
                # Process in smaller chunks if needed
                image_features = model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            else:
                image_features = model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy array
        embedding = image_features.cpu().numpy().flatten()
        
        # Clean up GPU memory
        if device.type == "cuda" and GPU_MEMORY_EFFICIENT:
            del image_input, image_features
            torch.cuda.empty_cache()
            gc.collect()
        
        process_time = time.time() - start_time
        logger.info(f"Image processed in {process_time:.2f} seconds")
        
        return embedding
    
    except Exception as e:
        logger.error(f"Error processing image {image_path}: {e}")
        raise

def get_image_understanding(image_path, top_k=10):
    """
    Get a textual understanding of an image by finding the most similar concepts.
    
    Args:
        image_path (str): Path to the image file.
        top_k (int): Number of top concepts to return.
        
    Returns:
        list: List of (concept, score) tuples.
    """
    # Load CLIP model if not already loaded
    if not hasattr(st, 'session_state') or 'clip_model' not in st.session_state or st.session_state.clip_model is None:
        model, preprocess = load_clip_model()
    else:
        model = st.session_state.clip_model
        preprocess = st.session_state.clip_preprocess
    
    device = st.session_state.device if hasattr(st, 'session_state') and 'device' in st.session_state else setup_device()
    
    # List of concepts to check against
    concepts = [
        "street photography", "urban scene", "cityscape", "architecture", 
        "building", "people", "crowd", "portrait", "candid", "landscape", 
        "nature", "outdoor", "night", "day", "sunset", "sunrise", 
        "black and white", "color", "vintage", "modern", "abstract", 
        "minimalist", "detailed", "close-up", "wide angle", "telephoto"
    ]
    
    try:
        # Open and preprocess the image
        image = Image.open(image_path).convert('RGB')
        image_input = preprocess(image).unsqueeze(0).to(device)
        
        # Tokenize the concepts
        text_inputs = torch.cat([clip.tokenize(c) for c in concepts]).to(device)
        
        # Generate embeddings
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_inputs)
            
            # Normalize features
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarity
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            # Get top k concepts
            values, indices = similarity[0].topk(top_k)
            
        # Create list of (concept, score) tuples
        results = [(concepts[idx], val.item()) for val, idx in zip(values, indices)]
        
        # Clean up GPU memory
        if device.type == "cuda" and GPU_MEMORY_EFFICIENT:
            del image_input, text_inputs, image_features, text_features, similarity
            torch.cuda.empty_cache()
            gc.collect()
        
        return results
    
    except Exception as e:
        logger.error(f"Error getting image understanding for {image_path}: {e}")
        return []

def unload_clip_model():
    """
    Unload the CLIP model to free up GPU memory.
    """
    if hasattr(st, 'session_state'):
        if 'clip_model' in st.session_state:
            del st.session_state.clip_model
        if 'clip_preprocess' in st.session_state:
            del st.session_state.clip_preprocess
        if 'device' in st.session_state:
            del st.session_state.device
    
    # Force garbage collection and clear CUDA cache
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    logger.info("CLIP model unloaded from memory") 