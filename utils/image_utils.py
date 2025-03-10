"""
Utility functions for image handling.
"""
import os
import glob
from utils.logger import logger
from config import IMAGE_EXTENSIONS

def get_image_list(folder: str):
    """
    Returns a list of image file paths in the given folder and its subfolders.
    Looks for common image file extensions.
    
    Args:
        folder (str): Path to the folder containing images.
        
    Returns:
        list: List of image file paths.
    """
    image_files = []
    
    # Verify the folder exists
    if not os.path.exists(folder):
        logger.error(f"Folder does not exist: {folder}")
        return image_files
    
    # Log that we're starting to scan for images
    logger.info(f"Scanning for images in: {folder}")
    
    # Use recursive lookup with glob
    for ext in IMAGE_EXTENSIONS:
        pattern = os.path.join(folder, '**', ext)
        # Enable recursive search
        matches = glob.glob(pattern, recursive=True)
        image_files.extend(matches)
    
    logger.info(f"Found {len(image_files)} images in {folder}")
    
    # Debug: print the first few images found (if any)
    if image_files:
        logger.info(f"First few images: {image_files[:3]}")
    
    return image_files 