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
import rawpy
import csv

# Add the parent directory to sys.path so Python can find the project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import project utils
from utils.logger import logger
from utils.cuda_utils import check_gpu_memory, log_cuda_memory_usage
from utils.embedding_cache import EmbeddingCache
from utils.duplicate_detector import compute_sha256

# Import models from the project
from models.clip_model import load_clip_model, unload_clip_model, setup_device
from models.blip_model import load_blip_model, unload_blip_model, generate_caption, setup_blip_device
from database.qdrant_connector import QdrantDB
from metadata_extractor import extract_metadata
from utils.incremental_indexer import start_incremental_indexer
from models.model_manager import ModelManager


def get_image_list(folder: str):
    """Return a sorted list of image file paths in the folder."""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.dng']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder, ext)))
    unique_files = sorted(list(set(image_files)))
    return unique_files


def load_image_with_rawpy_or_pil(path):
    """Load an image using rawpy for DNG/RAW files, or PIL for others. Returns a PIL.Image in RGB mode."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.dng':
        try:
            with rawpy.imread(path) as raw:
                rgb = raw.postprocess()
            return Image.fromarray(rgb)
        except Exception as e:
            logger.error(f"Error loading DNG file {path} with rawpy: {e}", exc_info=True)
            raise
    else:
        return Image.open(path).convert("RGB")


def process_clip_embeddings(image_paths, batch_size=16, device=None, embedding_cache=None):
    """
    Process images in batches using the CLIP model to compute embeddings.
    Returns a dictionary mapping each image path to its embedding (numpy array).
    Uses embedding_cache if provided.
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
        batch_indices = []
        batch_hashes = []
        # Check cache for each image
        for i, path in enumerate(batch_paths):
            file_hash = compute_sha256(path)
            cached = embedding_cache.get(file_hash) if embedding_cache else None
            if cached is not None:
                embeddings_dict[path] = cached
            else:
                try:
                    image = load_image_with_rawpy_or_pil(path)
                    image_tensor = preprocess(image)
                    batch_images.append(image_tensor)
                    batch_indices.append(i)
                    batch_hashes.append(file_hash)
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
            for idx, emb, file_hash in zip(batch_indices, embeddings, batch_hashes):
                path = batch_paths[idx]
                embeddings_dict[path] = emb
                if embedding_cache:
                    embedding_cache.set(file_hash, emb)
            logger.info(f"Processed {min(start+batch_size, num_images)} / {num_images} images with CLIP")
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
            ext = os.path.splitext(path)[1].lower()
            if ext == '.dng':
                image = load_image_with_rawpy_or_pil(path)
                caption = generate_caption(image)
            else:
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
    parser.add_argument('--save-summary', action='store_true', help='If set, print and save a summary of results to results_summary.txt')
    parser.add_argument('--clear-embedding-cache', action='store_true', help='Clear the embedding cache before running')
    parser.add_argument('--inspect-embedding-cache', action='store_true', help='Inspect the embedding cache and exit')
    parser.add_argument('--watch', action='store_true', help='Watch folder for changes and incrementally index')
    args = parser.parse_args()

    embedding_cache = EmbeddingCache()
    if args.clear_embedding_cache:
        embedding_cache.clear()
        print("Embedding cache cleared.")
    if args.inspect_embedding_cache:
        hashes = embedding_cache.inspect(20)
        if hashes:
            print(f"First {len(hashes)} hashes in embedding cache:")
            for h in hashes:
                print(h)
        else:
            print("Embedding cache is empty.")
        return

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
    save_summary = args.save_summary

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
    embeddings_dict = process_clip_embeddings(image_paths, batch_size=batch_size, device=clip_device, embedding_cache=embedding_cache)
    clip_time = time.time()
    clip_duration = clip_time - start_time
    logger.info(f"CLIP processing completed in {clip_duration:.2f} seconds.")

    logger.info("=== Starting Stage 2: BLIP Caption Generation ===")
    captions_dict = process_blip_captions(image_paths, max_workers=max_workers, device=blip_device)
    blip_time = time.time()
    blip_duration = blip_time - clip_time
    logger.info(f"BLIP caption generation completed in {blip_duration:.2f} seconds.")

    logger.info("=== Starting Stage 3: Vector Database Updates ===")
    # Initialize QdrantDB with in_memory=False by default, or add CLI arg to control this
    db = QdrantDB(collection_name="pixel_detective_mvp") # Using a distinct collection name
    logger.info(f"Adding {len(image_paths)} images to vector database '{db.collection_name}'...")
    
    points_to_add_paths = []
    points_to_add_embeddings = []
    points_to_add_metadata = []

    for path in image_paths:
        embedding = embeddings_dict.get(path)
        if embedding is None:
            logger.warning(f"Skipping image {path} for database addition due to missing embedding.")
            continue

        metadata = extract_metadata(path) # Extract fresh metadata
        caption = captions_dict.get(path, "")
        metadata["caption"] = caption
        
        # Ensure Keywords field exists and includes the caption
        if "Keywords" not in metadata or not metadata["Keywords"]:
            metadata["Keywords"] = [caption] if caption else []
        elif isinstance(metadata["Keywords"], str):
            metadata["Keywords"] = [metadata["Keywords"]]
        if caption and caption not in metadata["Keywords"]:
            metadata["Keywords"].append(caption)
        
        # Ensure tags field exists and is a list (prefer tags, fallback to Keywords)
        if "tags" not in metadata or not metadata["tags"]:
            metadata["tags"] = metadata.get("Keywords", [])
        elif isinstance(metadata["tags"], str):
            metadata["tags"] = [metadata["tags"]]
        
        # Remove duplicates in tags and Keywords
        if isinstance(metadata.get("Keywords"), list):
             metadata["Keywords"] = list(dict.fromkeys(metadata["Keywords"]))
        if isinstance(metadata.get("tags"), list):
            metadata["tags"] = list(dict.fromkeys(metadata["tags"]))

        points_to_add_paths.append(path)
        points_to_add_embeddings.append(embedding)
        points_to_add_metadata.append(metadata)

    if points_to_add_paths:
        success_count, failure_count = db.add_images_batch(
            image_paths=points_to_add_paths, 
            embeddings=points_to_add_embeddings, 
            metadata_list=points_to_add_metadata,
            batch_size=args.batch_size # Reuse CLI batch_size for Qdrant batching
        )
        logger.info(f"Database batch addition: {success_count} succeeded, {failure_count} failed.")
    else:
        logger.info("No valid images with embeddings to add to the database.")

    db_time = time.time()
    db_duration = db_time - blip_time
    logger.info(f"Database updated in {db_duration:.2f} seconds.")
    total_time = time.time() - start_time
    logger.info(f"Processing complete in {total_time:.2f} seconds.")
    logger.info(f"Summary: CLIP: {clip_duration:.2f}s, BLIP: {blip_duration:.2f}s, DB: {db_duration:.2f}s")

    # --- SUMMARY OUTPUT ---
    if save_summary:
        summary_lines = []
        summary_lines.append(f"Processed {len(image_paths)} images in {total_time:.2f} seconds.")
        summary_lines.append(f"CLIP: {clip_duration:.2f}s, BLIP: {blip_duration:.2f}s, DB: {db_duration:.2f}s\n")
        summary_lines.append("Image Results:")
        for path in image_paths:
            caption = captions_dict.get(path, "<NO CAPTION>")
            emb = embeddings_dict.get(path)
            emb_status = "OK" if emb is not None else "FAILED"
            summary_lines.append(f"- {os.path.basename(path)}: Caption: {caption[:60]}... | Embedding: {emb_status}")
        summary = "\n".join(summary_lines)
        print("\n=== SUMMARY ===\n" + summary)
        with open("results_summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info("Results summary written to results_summary.txt")
        print("\n===== results_summary.txt =====\n")
        with open('results_summary.txt', 'r', encoding='utf-8') as f:
            print(f.read())

        # --- DETAILED CSV OUTPUT ---
        detailed_csv = 'results_detailed_summary.csv'
        all_fields = set()
        metadata_list = []
        for path in image_paths:
            metadata = extract_metadata(path)
            caption = captions_dict.get(path, "<NO CAPTION>")
            emb = embeddings_dict.get(path)
            emb_status = "OK" if emb is not None else "FAILED"
            metadata = metadata.copy() if metadata else {}
            metadata['filename'] = os.path.basename(path)
            metadata['caption'] = caption
            metadata['embedding_status'] = emb_status
            metadata_list.append(metadata)
            all_fields.update(metadata.keys())
        all_fields = list(all_fields)
        # Write CSV
        with open(detailed_csv, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_fields)
            writer.writeheader()
            for row in metadata_list:
                writer.writerow(row)
        print(f"\n===== {detailed_csv} =====\n")
        with open(detailed_csv, 'r', encoding='utf-8') as f:
            print(f.read())

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

    # Start incremental indexing if requested
    if args.watch:
        # Initialize a model manager for incremental processing
        model_mgr = ModelManager(device=clip_device)
        observer = start_incremental_indexer(
            folder=folder,
            db=db,
            cache=embedding_cache,
            model_mgr=model_mgr
        )
        print(f"Watching {folder} for changes. Press Ctrl+C to exit.")
        try:
            observer.join()
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
            print("Incremental indexer stopped.")


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