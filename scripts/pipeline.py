"""
Purpose: Implements a sequential pipeline for processing images using the CLIP model.
Latest Changes: Refactored to load the CLIP model, process images, and then unload the model to free GPU memory.
Key Logic: Loads the model, processes all images (outputs embedding and textual understanding), then unloads the model, ensuring that only one model instance uses GPU at a time.
File Path: pipeline.py
Reasoning: This sequential approach prevents the simultaneous loading of multiple models.
"""

import glob
import os
from models.clip_model import load_clip_model, process_image, get_image_understanding, unload_clip_model


def process_images_with_clip(image_dir):
    """
    Load the CLIP model, process each image in a sequential manner, then unload the model.
    This ensures that GPU memory is only used by one model at a time.

    Args:
        image_dir (str): Directory containing the image files.

    Returns:
        dict: A dictionary mapping image filenames to their processing results.
    """
    # Load CLIP model and get preprocessing function
    model, preprocess = load_clip_model()
    results = {}
    image_pattern = os.path.join(image_dir, "*")
    image_paths = glob.glob(image_pattern)

    for image_path in image_paths:
        try:
            # Process the image to get both embedding and textual understanding
            embedding = process_image(image_path)
            understanding = get_image_understanding(image_path)
            results[os.path.basename(image_path)] = {
                "embedding": embedding,
                "understanding": understanding
            }
        except Exception as e:
            print(f"Error processing {image_path}: {e}")

    # Unload the CLIP model to free up GPU memory before proceeding
    unload_clip_model()
    print("Finished processing images with CLIP model.")
    return results


if __name__ == '__main__':
    # Example usage: process images in the './images' directory
    image_dir = './images'
    results = process_images_with_clip(image_dir)
    # Further sequential processing (e.g., loading a different model) can be done here
    print("Results:", results) 