# 📂 File Path: /project_root/config.py
# 📌 Purpose: This file contains configuration settings for the Pixel Detective application.
# 🔄 Latest Changes: Updated BLIP model to use a compatible version with transformers 4.38.0.
# ⚙️ Key Logic: Defines constants for database file names, default image folder, CLIP model settings, and supported image extensions.
# 🧠 Reasoning: Centralizes configuration to facilitate easy updates and maintenance of application settings.

"""
Configuration settings for the Pixel Detective app.
"""
import os

# Database file names
DB_EMBEDDINGS_FILE = "embeddings.npy"
DB_METADATA_FILE = "metadata.csv"

# Default folder for images
DEFAULT_IMAGE_FOLDER = os.path.expanduser("~/Pictures")

# CLIP model settings
CLIP_MODEL_NAME = "ViT-B/32"

# BLIP model settings
BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-large"  # More compatible model
BLIP_PROCESSOR_NAME = "Salesforce/blip-image-captioning-large"
BLIP_DEVICE = "cuda"  # Use GPU for BLIP
BLIP_LOAD_8BIT = False  # Regular precision for this model

# GPU memory optimization
GPU_MEMORY_EFFICIENT = True  # Enable memory-efficient operations
BATCH_SIZE = 1  # Process one image at a time to save memory

# Supported image extensions
IMAGE_EXTENSIONS = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif'] 