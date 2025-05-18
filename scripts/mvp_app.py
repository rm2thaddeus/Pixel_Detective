# -*- coding: utf-8 -*-

'''
📂 File Path: /project_root/mvp_app.py
📌 Purpose: MVP application that processes a folder of images in two stages: first computing CLIP embeddings in batches, then generating BLIP captions in parallel, and finally storing results in a Qdrant vector database.
🔄 Latest Changes: Added proper logging infrastructure from main app.py, and CUDA memory tracking.
⚙️ Key Logic: Uses batch processing for CLIP and parallel caption generation for BLIP.
🧠 Reasoning: Optimizes GPU memory usage by not loading both models simultaneously and speeds up processing.
'''

import os
import sys
import time
import glob
import torch
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import atexit
import argparse

# Add the parent directory to sys.path so Python can find the project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project utils
from utils.logger import logger
from utils.cuda_utils import check_gpu_memory, log_cuda_memory_usage

# Import models from the project
from models.clip_model import load_clip_model, unload_clip_model, setup_device
from models.blip_model import load_blip_model, unload_blip_model, generate_caption, setup_blip_device
from vector_db import QdrantDB


def get_image_list(folder: str):
    """Return a sorted list of image file paths in the folder."""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder, ext)))
    unique_files = sorted(list(set(image_files)))
    return unique_files


def process_clip_embeddings(image_paths, batch_size=16, device=None):
    """
    Process images in batches using the CLIP model to compute embeddings.
    Returns a dictionary mapping each image path to its embedding (numpy array).
    """
    logger.info("Loading CLIP model...")
    log_cuda_memory_usage("Before CLIP model loading")
    if device is None:
        device = setup_device()
    model, preprocess = load_clip_model(device=device)
    logger.info(f"CLIP model loaded on device: {device}")
    log_cuda_memory_usage("After CLIP model loading")

    embeddings_dict = {}
    num_images = len(image_paths)
    logger.info(f"Starting CLIP embedding generation for {num_images} images with batch size {batch_size}")
    
    for start in range(0, num_images, batch_size):
        batch_paths = image_paths[start:start+batch_size]
        batch_images = []
        
        for path in batch_paths:
            try:
                image = Image.open(path).convert("RGB")
                image_tensor = preprocess(image)
                batch_images.append(image_tensor)
            except Exception as e:
                logger.error(f"Error processing image {path}: {e}", exc_info=True)
        
        if not batch_images:
            logger.warning(f"Batch starting at index {start} had no valid images, skipping")
            continue
            
        try:
            batch_tensor = torch.stack(batch_images).to(device)
            with torch.no_grad():
                image_features = model.encode_image(batch_tensor)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            embeddings = image_features.cpu().numpy()
            for i, path in enumerate(batch_paths):
                embeddings_dict[path] = embeddings[i]
                
            logger.info(f"Processed {min(start+batch_size, num_images)} / {num_images} images with CLIP")
            
            # Periodically log memory usage
            if start % (batch_size * 10) == 0:
                log_cuda_memory_usage(f"CLIP processing progress: {min(start+batch_size, num_images)}/{num_images}")
                
        except Exception as e:
            logger.error(f"Error during batch processing at index {start}: {e}", exc_info=True)
    
    logger.info("Unloading CLIP model...")
    unload_clip_model()
    torch.cuda.empty_cache()
    log_cuda_memory_usage("After CLIP model unloading")
    return embeddings_dict


def process_blip_captions(image_paths, max_workers=4, device=None):
    """
    Process images in parallel using the BLIP model to generate captions.
    Returns a dictionary mapping each image path to its generated caption.
    """
    logger.info(f"Loading BLIP model with {max_workers} parallel workers...")
    log_cuda_memory_usage("Before BLIP model loading")
    if device is None:
        device = setup_blip_device()
    model, processor = load_blip_model(device=device)
    logger.info(f"BLIP model loaded on device: {device}")
    log_cuda_memory_usage("After BLIP model loading")

    results = {}

    def get_caption(path):
        try:
            caption = generate_caption(path)
            return path, caption
        except Exception as e:
            logger.error(f"Error generating caption for {path}: {e}", exc_info=True)
            return path, ""
    
    logger.info(f"Starting parallel caption generation for {len(image_paths)} images")        
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(get_caption, path): path for path in image_paths}
        completed = 0
        
        for future in as_completed(future_to_path):
            try:
                path, caption = future.result()
                results[path] = caption
                completed += 1
                
                if completed % 25 == 0:
                    logger.info(f"Generated captions for {completed}/{len(image_paths)} images")
                    log_cuda_memory_usage(f"BLIP processing progress: {completed}/{len(image_paths)}")
            except Exception as e:
                logger.error(f"Error retrieving caption result: {e}", exc_info=True)
    
    logger.info("Unloading BLIP model...")
    unload_blip_model()
    torch.cuda.empty_cache()
    log_cuda_memory_usage("After BLIP model unloading")
    return results


def on_shutdown():
    """Clean up resources when the script is shutting down."""
    logger.info("Script shutting down, cleaning up resources...")
    
    # Force garbage collection
    gc.collect()
    
    # Clear CUDA cache
    if torch.cuda.is_available():
        try:
            # Empty CUDA cache
            torch.cuda.empty_cache()
            
            # Reset peak memory stats
            torch.cuda.reset_peak_memory_stats()
            
            # Log final GPU memory state
            allocated = torch.cuda.memory_allocated(0) / 1024**2
            reserved = torch.cuda.memory_reserved(0) / 1024**2
            logger.info(f"Final GPU memory state - Allocated: {allocated:.2f} MB, Reserved: {reserved:.2f} MB")
            
            logger.info("CUDA resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up CUDA resources: {e}", exc_info=True)
    
    logger.info("Script shutdown complete")


def main():
    parser = argparse.ArgumentParser(description="Pixel Detective MVP: Batch image processing and search")
    parser.add_argument('--folder', type=str, required=True, help='Path to the image folder')
    parser.add_argument('--batch-size', type=int, default=16, help='Batch size for CLIP embeddings')
    parser.add_argument('--max-workers', type=int, default=4, help='Number of parallel workers for BLIP captions')
    parser.add_argument('--query', type=str, default=None, help='Text query for image search (optional)')
    args = parser.parse_args()

    clip_device = setup_device()
    blip_device = setup_blip_device()
    logger.info(f"CLIP device: {clip_device}, BLIP device: {blip_device}")
    memory_info = check_gpu_memory()
    if memory_info["available"]:
        logger.info(memory_info["message"])

    folder = args.folder
    batch_size = args.batch_size
    max_workers = args.max_workers
    query = args.query

    if not os.path.isdir(folder):
        logger.error(f"Provided folder does not exist: {folder}")
        return
    image_paths = get_image_list(folder)
    if not image_paths:
        logger.warning(f"No images found in the specified folder: {folder}")
        return
    logger.info(f"Found {len(image_paths)} images. Starting processing...")

    start_time = time.time()
    logger.info("=== Starting Stage 1: CLIP Embedding Generation ===")
    embeddings_dict = process_clip_embeddings(image_paths, batch_size=batch_size, device=clip_device)
    clip_time = time.time()
    clip_duration = clip_time - start_time
    logger.info(f"CLIP processing completed in {clip_duration:.2f} seconds.")

    logger.info("=== Starting Stage 2: BLIP Caption Generation ===")
    captions_dict = process_blip_captions(image_paths, max_workers=max_workers, device=blip_device)
    blip_time = time.time()
    blip_duration = blip_time - clip_time
    logger.info(f"BLIP caption generation completed in {blip_duration:.2f} seconds.")

    logger.info("=== Starting Stage 3: Vector Database Updates ===")
    db = QdrantDB(collection_name="image_collection")
    logger.info(f"Adding {len(image_paths)} images to vector database...")
    added_count = 0
    for path in image_paths:
        try:
            metadata = {
                "caption": captions_dict.get(path, ""),
                "keywords": [captions_dict.get(path, "")]
            }
            db.add_image(path, embeddings_dict.get(path), metadata)
            added_count += 1
            if added_count % 100 == 0:
                logger.info(f"Added {added_count}/{len(image_paths)} images to database")
        except Exception as e:
            logger.error(f"Error adding image {path} to database: {e}", exc_info=True)
    db_time = time.time()
    db_duration = db_time - blip_time
    logger.info(f"Database updated in {db_duration:.2f} seconds.")
    total_time = time.time() - start_time
    logger.info(f"Processing complete in {total_time:.2f} seconds.")
    logger.info(f"Summary: CLIP: {clip_duration:.2f}s, BLIP: {blip_duration:.2f}s, DB: {db_duration:.2f}s")

    # Optional: Demonstrate a text search using CLIP for query encoding
    if query:
        logger.info(f"Performing text search with query: '{query}'")
        log_cuda_memory_usage("Before search query processing")
        try:
            logger.info("Loading CLIP model for text encoding...")
            model, preprocess = load_clip_model(device=clip_device)
            device = next(model.parameters()).device
            import clip
            with torch.no_grad():
                text = clip.tokenize([query]).to(device)
                text_features = model.encode_text(text)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            query_vector = text_features.cpu().numpy().flatten()
            unload_clip_model()
            logger.info("Searching vector database...")
            results = db.search_by_vector(query_vector, limit=5)
            if results:
                logger.info(f"Found {len(results)} matching images:")
                for image_path, score in results:
                    logger.info(f"Image: {image_path}, Score: {score:.4f}")
            else:
                logger.info("No matching images found.")
        except Exception as e:
            logger.error(f"Error during text search: {e}", exc_info=True)
    else:
        logger.info("No search query provided, skipping search")


# Register shutdown function
atexit.register(on_shutdown)

if __name__ == "__main__":
    try:
        logger.info("=== Starting Pixel Detective MVP Script ===")
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # We don't call on_shutdown() here since atexit will handle it
        pass 