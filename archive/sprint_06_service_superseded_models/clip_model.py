"""
CLIP model loading and image processing.
"""
import time
import torch
import clip
import gc
from PIL import Image
import streamlit as st
from utils.logger import logger # This will be a broken import in archive
from config import CLIP_MODEL_NAME, GPU_MEMORY_EFFICIENT # This will be a broken import in archive
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

def get_image_embedding_from_model_instance(model, preprocess, image_path, device):
    """
    Process an image to generate its embedding using a provided CLIP model instance.

    Args:
        model: The pre-loaded CLIP model instance.
        preprocess: The pre-loaded CLIP preprocessor.
        image_path (str): Path to the image file.
        device (torch.device): The device the model is on.
        
    Returns:
        numpy.ndarray: The image embedding, or None on error.
    """
    if model is None or preprocess is None:
        logger.error("CLIP model or preprocess not provided to get_image_embedding_from_model_instance.")
        return None
    
    try:
        start_time = time.time()
        
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.dng':
            try:
                with rawpy.imread(image_path) as raw:
                    rgb = raw.postprocess()
                image = Image.fromarray(rgb).convert("RGB")
            except Exception as raw_e:
                logger.error(f"Error loading DNG file {image_path} with rawpy: {raw_e}", exc_info=True)
                return None # Return None on DNG processing error
        else:
            image = Image.open(image_path).convert("RGB")

        image_input = preprocess(image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            image_features = model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
        
        embedding = image_features.cpu().numpy().squeeze()
        
        end_time = time.time()
        logger.debug(f"Image {os.path.basename(image_path)} processed for embedding in {end_time - start_time:.2f} seconds using provided model instance.")
        
        return embedding
    except Exception as e:
        logger.error(f"Error processing image {image_path} with provided model instance: {e}", exc_info=True)
        return None

def get_image_understanding_from_model(model, preprocess, image_path, device, top_k=10):
    """
    Get a textual understanding of an image using a provided CLIP model and processor.

    Args:
        model: The pre-loaded CLIP model.
        preprocess: The pre-loaded CLIP preprocessor.
        image_path (str): Path to the image file.
        device (torch.device): The device the model is on.
        top_k (int): Number of top classes for classification (default is 10).

    Returns:
        str: A textual description of the image, or an error message.
    """
    # This function assumes clip_text_model.py structure for text prompts if that's intended.
    # For simplicity, let's assume it returns a generic message or uses predefined classes.
    # For a true text understanding, you might load a text dataset or use zero-shot classification.
    
    if model is None or preprocess is None:
        logger.error("CLIP model/preprocess not provided for get_image_understanding_from_model.")
        return "Error: CLIP model not available."

    try:
        ext = os.path.splitext(image_path)[1].lower()
        if ext == '.dng':
            with rawpy.imread(image_path) as raw:
                rgb = raw.postprocess()
            image = Image.fromarray(rgb).convert("RGB")
        else:
            image = Image.open(image_path).convert("RGB")
        
        image_input = preprocess(image).unsqueeze(0).to(device)

        # Example: Using predefined text prompts for zero-shot classification
        # This is a very basic example. A real implementation would use more sophisticated text prompts.
        text_prompts = [
            "a photo of a cat", "a photo of a dog", "a photo of a landscape", 
            "a portrait of a person", "an abstract image", "a technical drawing",
            "a city scene", "a nature scene", "a food item", "a vehicle"
        ]
        text_inputs = clip.tokenize(text_prompts).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_inputs)
            
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            
            similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            values, indices = similarity[0].topk(min(top_k, len(text_prompts)))

        description_parts = []
        for value, index in zip(values, indices):
            description_parts.append(f"{text_prompts[index]}: {value.item()*100:.1f}%")
        
        understanding = f"Image classified as: {', '.join(description_parts)}"
        logger.debug(f"Generated understanding for {os.path.basename(image_path)}: {understanding}")
        return understanding

    except Exception as e:
        logger.error(f"Error getting image understanding for {image_path} with provided model: {e}", exc_info=True)
        return f"Error processing image for understanding: {str(e)}"

# Original get_image_understanding, kept for compatibility if used elsewhere directly
def get_image_understanding(image_path, top_k=10):
    """
    Get a textual understanding of an image using CLIP.
    Loads the model if not already loaded.
    
    Args:
        image_path (str): Path to the image file
        top_k (int): Number of top classes for classification
        
    Returns:
        str: A textual description of the image
    """
    global _clip_model, _clip_preprocess
    
    if _clip_model is None or _clip_preprocess is None:
        model, preprocess = load_clip_model()
    else:
        model, preprocess = _clip_model, _clip_preprocess
    
    device = next(model.parameters()).device
    return get_image_understanding_from_model(model, preprocess, image_path, device, top_k)

def process_batch(image_paths, batch_size_override=None):
    """
    Process a batch of images to generate their embeddings using CLIP.
    
    Args:
        image_paths (list of str): List of paths to image files.
        batch_size_override (int, optional): Override the default batch size.
        
    Returns:
        list of numpy.ndarray: A list of image embeddings.
                               Returns empty list or partial results on errors.
    """
    global _clip_model, _clip_preprocess
    
    if not image_paths:
        return []

    if _clip_model is None or _clip_preprocess is None:
        model, preprocess = load_clip_model()
    else:
        model, preprocess = _clip_model, _clip_preprocess
    
    device = next(model.parameters()).device
    batch_size = batch_size_override if batch_size_override else (32 if device.type == 'cuda' else 4) # Smaller batch for CPU
    all_embeddings = []
    processed_count = 0

    logger.info(f"Processing batch of {len(image_paths)} images with batch size {batch_size} on {device}.")

    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i:i+batch_size]
        batch_images_pil = []
        valid_indices_in_batch = [] # To track which images in sub-batch were successfully loaded

        for idx, image_path in enumerate(batch_paths):
            try:
                ext = os.path.splitext(image_path)[1].lower()
                if ext == '.dng':
                    with rawpy.imread(image_path) as raw:
                        rgb = raw.postprocess()
                    image = Image.fromarray(rgb).convert("RGB")
                else:
                    image = Image.open(image_path).convert("RGB")
                batch_images_pil.append(image)
                valid_indices_in_batch.append(idx) # Original index within this mini-batch
            except Exception as e:
                logger.error(f"Error loading image {image_path} in batch: {e}", exc_info=True)
                # We will skip this image and the final embeddings list will be shorter
                # or one could insert a None placeholder if the caller expects full length.

        if not batch_images_pil:
            logger.warning(f"No valid images loaded for batch starting at index {i}. Skipping.")
            continue

        try:
            # Preprocess all valid images in the batch
            image_inputs = torch.stack([preprocess(img) for img in batch_images_pil]).to(device)
            
            with torch.no_grad():
                image_features = model.encode_image(image_inputs)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # Convert to numpy array and add to results
            embeddings_np = image_features.cpu().numpy()
            all_embeddings.extend([emb.squeeze() for emb in embeddings_np])
            processed_count += len(batch_images_pil)
            logger.debug(f"Processed sub-batch {i//batch_size + 1}, {len(batch_images_pil)} images.")

        except Exception as e:
            logger.error(f"Error processing image batch starting at {batch_paths[0] if batch_paths else 'N/A'}: {e}", exc_info=True)
            # Depending on desired behavior, one might add None for each failed image in this batch
            # For now, we just log and the output list will be shorter if a whole sub-batch fails.

    logger.info(f"Finished processing batch. Total images processed: {processed_count}/{len(image_paths)}.")
    return all_embeddings

# For testing purposes
if __name__ == '__main__':
    # Example usage (requires images in a ./test_images folder)
    # Ensure you have CLIP_MODEL_NAME defined in config.py or set it directly
    # And utils.logger configured
    logging.basicConfig(level=logging.INFO)
    # CLIP_MODEL_NAME = "ViT-B/32" # Example if not in config
    
    # Create dummy config and logger if not present
    class DummyConfig:
        CLIP_MODEL_NAME = "ViT-B/32"
        GPU_MEMORY_EFFICIENT = False

    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    if 'config' not in globals():
        config = DummyConfig()
        CLIP_MODEL_NAME = config.CLIP_MODEL_NAME
    if 'logger' not in globals() or isinstance(logger, logging.RootLogger): # if not a custom logger
        logger = DummyLogger()

    try:
        # Test model loading
        logger.info("Testing CLIP model loading...")
        model, preprocess = load_clip_model()
        logger.info("CLIP model loaded successfully.")
        
        # Create a dummy image file for testing if it doesn't exist
        test_image_dir = "test_images"
        if not os.path.exists(test_image_dir):
            os.makedirs(test_image_dir)
        dummy_image_path = os.path.join(test_image_dir, "dummy_clip_test.png")
        if not os.path.exists(dummy_image_path):
            try:
                dummy_img = Image.new('RGB', (60, 30), color = 'red')
                dummy_img.save(dummy_image_path)
                logger.info(f"Created dummy image: {dummy_image_path}")
            except Exception as e_img:
                logger.error(f"Could not create dummy image: {e_img}")

        if os.path.exists(dummy_image_path):
            # Test image processing
            logger.info(f"Testing image processing with {dummy_image_path}...")
            embedding = process_image(dummy_image_path)
            logger.info(f"Image embedding shape: {embedding.shape}")
            assert embedding.shape == (512,), "Embedding shape is not (512,)"
            logger.info("Image processing test successful.")

            # Test batch processing
            logger.info("Testing batch processing...")
            batch_embeddings = process_batch([dummy_image_path, dummy_image_path])
            logger.info(f"Batch embeddings count: {len(batch_embeddings)}")
            assert len(batch_embeddings) == 2, "Batch processing did not return 2 embeddings"
            assert batch_embeddings[0].shape == (512,), "Batch embedding shape is not (512,)"
            logger.info("Batch processing test successful.")

        else:
            logger.warning("Skipping image processing tests as dummy image could not be created/found.")

        # Test model unloading
        logger.info("Testing CLIP model unloading...")
        unloaded = unload_clip_model()
        logger.info(f"CLIP model unloaded: {unloaded}")
        assert unloaded, "Model unload failed"

    except Exception as e:
        logger.error(f"An error occurred during testing: {e}", exc_info=True)

    finally:
        # Clean up dummy image
        if os.path.exists(dummy_image_path):
            try:
                os.remove(dummy_image_path)
                # os.rmdir(test_image_dir) # Only if dir is empty and you want to remove it
                logger.info(f"Cleaned up dummy image: {dummy_image_path}")
            except Exception as e_clean:
                logger.error(f"Error cleaning up dummy image: {e_clean}") 