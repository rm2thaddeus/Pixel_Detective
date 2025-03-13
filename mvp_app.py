# -*- coding: utf-8 -*-

'''
📂 File Path: /project_root/mvp_app.py
📌 Purpose: MVP application that processes a folder of images in two stages: first computing CLIP embeddings in batches, then generating BLIP captions in parallel, and finally storing results in a Qdrant vector database.
🔄 Latest Changes: Refactored to load one model at a time on GPU, process images in parallel/batch mode, and integrate with the vector DB.
⚙️ Key Logic: Uses batch processing for CLIP and parallel caption generation for BLIP.
🧠 Reasoning: Optimizes GPU memory usage by not loading both models simultaneously and speeds up processing.
'''

import os
import time
import glob
import torch
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import models from the project
from models.clip_model import load_clip_model, unload_clip_model
from models.blip_model import load_blip_model, unload_blip_model, generate_caption
from vector_db import QdrantDB


def get_image_list(folder: str):
    """Return a sorted list of image file paths in the folder."""
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder, ext)))
    unique_files = sorted(list(set(image_files)))
    return unique_files


def process_clip_embeddings(image_paths, batch_size=16):
    """
    Process images in batches using the CLIP model to compute embeddings.
    Returns a dictionary mapping each image path to its embedding (numpy array).
    """
    print("Loading CLIP model...")
    model, preprocess = load_clip_model()
    device = next(model.parameters()).device  

    embeddings_dict = {}
    num_images = len(image_paths)
    for start in range(0, num_images, batch_size):
        batch_paths = image_paths[start:start+batch_size]
        batch_images = []
        for path in batch_paths:
            try:
                image = Image.open(path).convert("RGB")
                image_tensor = preprocess(image)
                batch_images.append(image_tensor)
            except Exception as e:
                print(f"Error processing image {path}: {e}")
        if not batch_images:
            continue
        batch_tensor = torch.stack(batch_images).to(device)
        with torch.no_grad():
            image_features = model.encode_image(batch_tensor)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        embeddings = image_features.cpu().numpy()
        for i, path in enumerate(batch_paths):
            embeddings_dict[path] = embeddings[i]
        print(f"Processed {min(start+batch_size, num_images)} / {num_images} images with CLIP")
    unload_clip_model()
    torch.cuda.empty_cache()
    return embeddings_dict


def process_blip_captions(image_paths, max_workers=4):
    """
    Process images in parallel using the BLIP model to generate captions.
    Returns a dictionary mapping each image path to its generated caption.
    """
    print("Loading BLIP model...")
    processor, model = load_blip_model()
    device = next(model.parameters()).device

    results = {}

    def get_caption(path):
        try:
            caption = generate_caption(path)
            return path, caption
        except Exception as e:
            print(f"Error generating caption for {path}: {e}")
            return path, ""
            
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(get_caption, path): path for path in image_paths}
        for future in as_completed(future_to_path):
            path, caption = future.result()
            results[path] = caption
    unload_blip_model()
    torch.cuda.empty_cache()
    return results


def main():
    folder = input("Enter the path to the image folder: ").strip()
    if not os.path.isdir(folder):
        print("Provided folder does not exist.")
        return
    image_paths = get_image_list(folder)
    if not image_paths:
        print("No images found in the specified folder.")
        return
    print(f"Found {len(image_paths)} images. Starting processing...")

    start_time = time.time()
    # Stage 1: Compute CLIP embeddings in batches
    embeddings_dict = process_clip_embeddings(image_paths)
    clip_time = time.time()
    print(f"CLIP processing completed in {clip_time - start_time:.2f} seconds.")

    # Stage 2: Generate BLIP captions in parallel
    captions_dict = process_blip_captions(image_paths)
    blip_time = time.time()
    print(f"BLIP caption generation completed in {blip_time - clip_time:.2f} seconds.")

    # Stage 3: Insert results into the Qdrant vector database
    print("Storing results in vector database...")
    db = QdrantDB(collection_name="image_collection")
    for path in image_paths:
        metadata = {
            "caption": captions_dict.get(path, ""),
            "Keywords": [captions_dict.get(path, "")]
        }
        db.add_image(path, embeddings_dict.get(path), metadata)
    db_time = time.time()
    print(f"Database updated in {db_time - blip_time:.2f} seconds.")
    total_time = time.time() - start_time
    print(f"Processing complete in {total_time:.2f} seconds.")

    # Optional: Demonstrate a text search using CLIP for query encoding
    query = input("Enter a text query to search for similar images (or leave empty): ").strip()
    if query:
        # Load CLIP model again for text encoding
        model, preprocess = load_clip_model()
        device = next(model.parameters()).device
        import clip
        with torch.no_grad():
            text = clip.tokenize([query]).to(device)
            text_features = model.encode_text(text)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        query_vector = text_features.cpu().numpy().flatten()
        unload_clip_model()
        results = db.search_by_vector(query_vector, limit=5)
        if results:
            print("Search results:")
            for image_path, score in results:
                print(f"Image: {image_path}, Score: {score:.4f}")
        else:
            print("No matching images found.")


if __name__ == "__main__":
    main() 