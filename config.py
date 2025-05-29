# 📂 File Path: /project_root/config.py
# 📌 Purpose: Centralizes configuration settings for the application.
# 🔄 Latest Changes: Created configuration file with application settings.
# ⚙️ Key Logic: Defines constants and settings used throughout the application.
# 🧠 Reasoning: Centralizes configuration for easier maintenance and updates.

"""
Configuration settings for the Pixel Detective app.
"""
import os
import torch
from pathlib import Path

# Database file names
DB_EMBEDDINGS_FILE = "embeddings.npy"
DB_METADATA_FILE = "metadata.csv"

# Model settings
CLIP_MODEL_NAME = "ViT-B/32"
BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base"

# Memory management settings
GPU_MEMORY_EFFICIENT = True  # Keep this true for safety

# UI settings
DEFAULT_NUM_RESULTS = 5
MAX_NUM_RESULTS = 20

# Paths
DEFAULT_IMAGES_PATH = os.path.expanduser("~/Pictures")

# === PATHS ===
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "cache"
LOGS_DIR = PROJECT_ROOT / "logs"

# BLIP model settings
BLIP_PROCESSOR_NAME = "Salesforce/blip-image-captioning-large"
# Set device based on availability - no longer hardcoded to "cuda"
BLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BLIP_LOAD_8BIT = False  # Regular precision for this model

# Update batch size to process more images at once
BATCH_SIZE = 50  # Process images in batches

# Add a setting to control whether to keep models loaded
KEEP_MODELS_LOADED = False  # Changed from True - prevents GPU memory issues

# Supported image extensions
IMAGE_EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.dng']

# === PERFORMANCE SETTINGS ===
# CRITICAL FIX: Set to False to prevent GPU memory overload
# This enables proper sequential loading (CLIP -> process -> unload -> BLIP -> process)

# === DEVICE SETTINGS ===
# Auto-detect CUDA availability
# DEVICE = "cuda" if torch.cuda.is_available() else "cpu" # OLD WAY
# print(f"🎯 Using device: {DEVICE}") # OLD WAY

def get_device():
    """Determine and return the appropriate torch device, printing the choice."""
    # This function should only be called AFTER torch has been safely imported
    # by the FastStartupManager or equivalent controlled loading mechanism.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🎯 Using device: {device}")
    return device

# === DATABASE SETTINGS ===
DATABASE_NAME = "pixel_detective.db"

# === UI SETTINGS ===
MAX_DISPLAY_IMAGES = 20
THUMBNAIL_SIZE = (150, 150)

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# === LOGGING ===
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# === STREAMLIT SETTINGS ===
STREAMLIT_CONFIG = {
    "page_title": "🕵️‍♂️ Pixel Detective",
    "page_icon": "🕵️‍♂️",
    "layout": "wide",
    "initial_sidebar_state": "collapsed"
} 