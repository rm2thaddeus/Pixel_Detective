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
import numpy as np
import rawpy
import os

# Global variables to store model and preprocessor
_clip_model = None
_clip_preprocess = None

def setup_device(force_cpu=False):
    """
    Set up the device for the model.
    
    Args:
        force_cpu (bool): If True, force CPU usage even if CUDA is available
        
    Returns:
        torch.device: The device to use
    """
    if force_cpu:
        return torch.device("cpu")
    
    if torch.cuda.is_available():
        # Initialize CUDA
        try:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            logger.info(f"CUDA reports {device_count} available device(s): {device_name}")
            
            # Force CUDA initialization with a dummy tensor
            torch.zeros(1).cuda()
            
            # Log GPU memory usage at initialization
            allocated = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
            reserved = torch.cuda.memory_reserved(0) / (1024 * 1024)  # MB
            logger.info(f"CUDA initialized successfully")
            logger.info(f"GPU memory allocated: {allocated:.2f} MB")
            logger.info(f"GPU memory reserved: {reserved:.2f} MB")
            
            return torch.device("cuda")
        except Exception as e:
            logger.error(f"Error initializing CUDA: {e}")
            logger.warning("Falling back to CPU")
            return torch.device("cpu")
    else:
        logger.info("CUDA is not available, using CPU")
        return torch.device("cpu")

def load_clip_model(device=None):
    """
    Load the CLIP model.
    
    Args:
        device (torch.device): The device to load the model on
        
    Returns:
        tuple: (model, preprocess) - The CLIP model and preprocessing function
    """
    global _clip_model, _clip_preprocess
    
    if _clip_model is not None:
        return _clip_model, _clip_preprocess
    
    if device is None:
        device = setup_device()
    
    logger.info(f"Starting to load CLIP model on {device}...")
    
    try:
        start_time = time.time()
        
        if isinstance(device, str):
            device = torch.device(device)
        
        # Log current CUDA device information
        if device.type == "cuda":
            logger.info(f"CUDA device count: {torch.cuda.device_count()}")
            logger.info(f"Current CUDA device: {torch.cuda.current_device()}")
        
        # Load the model
        logger.info(f"Loading CLIP model with device={device}...")
        model, preprocess = clip.load(CLIP_MODEL_NAME, device=device)
        model = model.to(device)
        
        # Log device the model is on
        model_device = next(model.parameters()).device
        logger.info(f"Model is loaded on: {model_device}")
        
        _clip_model = model
        _clip_preprocess = preprocess
        
        end_time = time.time()
        logger.info(f"CLIP model loaded in {end_time - start_time:.2f} seconds on {device}")
        
        return model, preprocess
    except Exception as e:
        logger.error(f"Error loading CLIP model: {e}")
        raise

def unload_clip_model():
    """
    Unload the CLIP model from memory.
    
    Returns:
        bool: True if the model was unloaded, False otherwise
    """
    global _clip_model, _clip_preprocess
    
    if _clip_model is None:
        return False
    
    try:
        # Record GPU memory before unloading
        if torch.cuda.is_available():
            before_mem = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
        
        # Set model and preprocess to None
        _clip_model = None
        _clip_preprocess = None
        
        # Clean up CUDA cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            after_mem = torch.cuda.memory_allocated(0) / (1024 * 1024)  # MB
            logger.info(f"GPU memory still allocated after CLIP unload: {after_mem:.2f} MB")
        
        logger.info("CLIP model unloaded from memory")
        return True
    except Exception as e:
        logger.error(f"Error unloading CLIP model: {e}")
        return False

def process_image(image_path):
    """
    Process an image to generate its embedding using CLIP.
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        numpy.ndarray: The image embedding
    """
    global _clip_model, _clip_preprocess
    
    if _clip_model is None or _clip_preprocess is None:
        model, preprocess = load_clip_model()
    else:
        model, preprocess = _clip_model, _clip_preprocess
    
    device = next(model.parameters()).device
    
    try:
        start_time = time.time()
        
        # Open and preprocess the image
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.dng':
            try:
                with rawpy.imread(image_path) as raw:
                    rgb = raw.postprocess()
                image = Image.fromarray(rgb).convert("RGB")
            except Exception as raw_e:
                logger.error(f"Error loading DNG file {image_path} with rawpy: {raw_e}", exc_info=True)
                raise
        else:
            image = Image.open(image_path).convert("RGB")

        image_input = preprocess(image).unsqueeze(0).to(device)
        
        # Generate the embedding
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        
        # Convert to numpy array
        embedding = image_features.cpu().numpy().squeeze()
        
        end_time = time.time()
        logger.info(f"Image processed in {end_time - start_time:.2f} seconds")
        
        return embedding
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise

def get_image_understanding(image_path, top_k=10):
    """
    Get a textual understanding of an image by finding the most similar concepts.
    
    Args:
        image_path (str): Path to the image file
        top_k (int): Number of top concepts to return
        
    Returns:
        list: List of (concept, score) tuples
    """
    global _clip_model, _clip_preprocess
    
    if _clip_model is None or _clip_preprocess is None:
        model, preprocess = load_clip_model()
    else:
        model, preprocess = _clip_model, _clip_preprocess
    
    device = next(model.parameters()).device
    
    try:
        # List of common concepts to check against
        concepts = [
            "person", "people", "man", "woman", "child", "baby",
            "dog", "cat", "animal", "bird", "fish",
            "car", "vehicle", "bike", "motorcycle", "boat",
            "building", "house", "city", "landscape", "beach", "mountain", "forest", "sunset",
            "food", "fruit", "vegetable", "drink",
            "computer", "phone", "technology",
            "art", "painting", "music", "sport",
            "happy", "sad", "angry", "celebration",
            "indoor", "outdoor", "daytime", "nighttime"
        ]
        
        # Open and preprocess the image
        image = Image.open(image_path).convert("RGB")
        image_input = preprocess(image).unsqueeze(0).to(device)
        
        # Tokenize concepts
        text_inputs = clip.tokenize(concepts).to(device)
        
        # Get image and text features
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_inputs)
            
            # Normalize features
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Calculate similarities
            similarities = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
        # Convert to list of (concept, score) tuples
        scores = similarities[0].cpu().numpy()
        results = [(concepts[i], float(scores[i])) for i in range(len(concepts))]
        
        # Sort by score and get top-k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    except Exception as e:
        logger.error(f"Error getting image understanding: {e}")
        return []

def process_batch(image_paths, batch_size_override=None):
    """
    Process a batch of images to generate embeddings using CLIP.
    
    Args:
        image_paths (list): List of paths to image files.
        batch_size_override (int, optional): Override the default batch size from config. 
                                        Set to 1 for single image processing if needed by caller.

    Returns:
        list: List of image embeddings (numpy.ndarray).
              Returns an empty list if an error occurs or no images are processed.
    """
    global _clip_model, _clip_preprocess

    if not image_paths:
        return []

    if _clip_model is None or _clip_preprocess is None:
        model, preprocess = load_clip_model()
    else:
        model, preprocess = _clip_model, _clip_preprocess
    
    device = next(model.parameters()).device
    
    # Determine batch size (from config or override)
    # Assuming BATCH_SIZE is available in config, otherwise use a default or pass explicitly
    # For this example, let's use a default if not found in config, or use override.
    try:
        from config import BATCH_SIZE as DEFAULT_BATCH_SIZE
    except ImportError:
        DEFAULT_BATCH_SIZE = 16 # Fallback default

    batch_size = batch_size_override if batch_size_override is not None else DEFAULT_BATCH_SIZE

    all_embeddings = []
    num_images = len(image_paths)
    
    logger.info(f"Starting CLIP batch embedding generation for {num_images} images with batch size {batch_size}")

    for i in range(0, num_images, batch_size):
        current_batch_paths = image_paths[i:i+batch_size]
        batch_images_tensors = []
        processed_paths_in_batch = [] # Keep track of successfully processed images for this batch

        for path in current_batch_paths:
            try:
                ext = os.path.splitext(path)[1].lower()
                if ext == '.dng':
                    try:
                        with rawpy.imread(path) as raw:
                            rgb = raw.postprocess()
                        image = Image.fromarray(rgb).convert("RGB")
                    except Exception as raw_e:
                        logger.error(f"Error loading DNG file {path} with rawpy for batch: {raw_e}")
                        continue # Skip this image
                else:
                    image = Image.open(path).convert("RGB")
                
                image_tensor = preprocess(image)
                batch_images_tensors.append(image_tensor)
                processed_paths_in_batch.append(path)
            except Exception as e:
                logger.error(f"Error processing image {path} for batch: {e}")
        
        if not batch_images_tensors:
            logger.warning(f"Batch starting at index {i} had no valid images to tensorize, skipping")
            continue
            
        try:
            batch_tensor_stacked = torch.stack(batch_images_tensors).to(device)
            with torch.no_grad():
                image_features = model.encode_image(batch_tensor_stacked)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            batch_embeddings = image_features.cpu().numpy()
            all_embeddings.extend(batch_embeddings) # Appends each row of batch_embeddings as a separate item
            
            logger.info(f"Processed batch {i//batch_size + 1}/{(num_images-1)//batch_size + 1} ({len(batch_embeddings)} images)")

            if GPU_MEMORY_EFFICIENT and torch.cuda.is_available():
                # Minimal cleanup for batch processing, full unload is separate
                del batch_tensor_stacked, image_features, batch_embeddings
                torch.cuda.empty_cache()

        except Exception as e:
            logger.error(f"Error during CLIP model batch inference at index {i}: {e}")
            # Add None or zero vectors for failed images in this batch if count needs to match input
            # For simplicity here, we just log and continue. `all_embeddings` will have fewer items.

    logger.info(f"Finished CLIP batch processing. Generated {len(all_embeddings)} embeddings for {num_images} requested images.")
    return all_embeddings 