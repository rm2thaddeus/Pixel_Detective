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

# Database file names
DB_EMBEDDINGS_FILE = "embeddings.npy"
DB_METADATA_FILE = "metadata.csv"

# Model settings
CLIP_MODEL_NAME = "ViT-B/32"  # Options: "ViT-B/32", "ViT-B/16", "RN50", etc.
BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-large"

# Memory management settings
GPU_MEMORY_EFFICIENT = True  # Keep this true for safety

# UI settings
DEFAULT_NUM_RESULTS = 5
MAX_NUM_RESULTS = 20

# Paths
DEFAULT_IMAGES_PATH = os.path.expanduser("~/Pictures")

# Cache settings
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# BLIP model settings
BLIP_PROCESSOR_NAME = "Salesforce/blip-image-captioning-large"
# Set device based on availability - no longer hardcoded to "cuda"
BLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BLIP_LOAD_8BIT = False  # Regular precision for this model

# Update batch size to process more images at once
BATCH_SIZE = 16  # Increased from 1 to process more images in parallel

# Add a setting to control whether to keep models loaded
KEEP_MODELS_LOADED = True  # New setting to maintain models in memory

# Supported image extensions
IMAGE_EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.dng'] 