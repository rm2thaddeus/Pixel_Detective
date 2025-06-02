# 📂 File Path: /project_root/config.py
# 📌 Purpose: Centralizes configuration settings for the application.
# 🔄 Latest Changes: Created configuration file with application settings.
# ⚙️ Key Logic: Defines constants and settings used throughout the application.
# 🧠 Reasoning: Centralizes configuration for easier maintenance and updates.

"""
Configuration settings for the Pixel Detective app.
"""
import os
# import torch # REMOVED: Torch should not be imported directly in frontend config
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any

# Database file names
DB_EMBEDDINGS_FILE = "embeddings.npy"
DB_METADATA_FILE = "metadata.csv"

# Model settings
# CLIP_MODEL_NAME = "ViT-B/32" # Moved to backend service
# BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base" # Moved to backend service

# Memory management settings
GPU_MEMORY_EFFICIENT = True  # Keep this true for safety

# UI settings
DEFAULT_NUM_RESULTS = 5
MAX_NUM_RESULTS = 20

# Paths
DEFAULT_IMAGES_PATH = "data/default_images"  # Example path
DEFAULT_COLLECTION_NAME = "pixel_detective_collection" # Example name
API_BASE_URL_ML = "http://localhost:8001/ml/api/v1" # Example ML backend URL
API_BASE_URL_INGESTION = "http://localhost:8002/ingestion/api/v1" # Example Ingestion backend URL

# === PATHS ===
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "cache"
LOGS_DIR = PROJECT_ROOT / "logs"

# BLIP model settings
# BLIP_PROCESSOR_NAME = "Salesforce/blip-image-captioning-large" # Moved to backend service
# Set device based on availability - no longer hardcoded to "cuda"
# BLIP_DEVICE = "cuda" if torch.cuda.is_available() else "cpu" # Moved to backend service
# BLIP_LOAD_8BIT = False  # Regular precision for this model # Moved to backend service

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

@dataclass
class AppConfig:
    """
    Holds application configuration settings.
    These can be loaded from a file, environment variables, or defaults.
    """
    app_name: str = "Pixel Detective"
    default_image_folder: str = DEFAULT_IMAGES_PATH
    default_qdrant_collection_name: str = DEFAULT_COLLECTION_NAME
    
    # API Endpoints (examples, adjust as per your actual backend setup)
    api_ml_base_url: str = API_BASE_URL_ML
    api_ingestion_base_url: str = API_BASE_URL_INGESTION

    # Example of how you might structure specific endpoint paths
    # These would ideally be used by service_api.py
    endpoints: Dict[str, str] = field(default_factory=lambda: {
        "search_text": "/search/text",
        "search_image": "/search/image",
        "get_caption": "/image/caption",
        "list_images_qdrant": "/images/list", # For listing images from vector DB
        "get_all_vectors": "/vectors/all", # For latent space visualization
        "start_ingestion": "/ingest/start",
        "ingestion_status": "/ingest/status",
        "get_folder_stats": "/fs/stats", # Example for getting folder stats
        "list_folders": "/fs/list-dirs" # Example for listing directories
        # Add other endpoints as needed
    })

    # UI settings
    results_per_page: int = 20
    max_upload_size_mb: int = 50

    def update(self, **kwargs):
        """Update config attributes with provided keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                # Optionally log a warning for unknown config keys
                print(f"Warning: Unknown config key '{key}'")
        return self

    def get_ml_api_url(self, endpoint_key: str) -> str:
        """Constructs a full URL for a given ML API endpoint key."""
        if endpoint_key not in self.endpoints:
            raise ValueError(f"Unknown ML endpoint key: {endpoint_key}")
        return f"{self.api_ml_base_url}{self.endpoints[endpoint_key]}"

    def get_ingestion_api_url(self, endpoint_key: str) -> str:
        """Constructs a full URL for a given Ingestion API endpoint key."""
        if endpoint_key not in self.endpoints:
            raise ValueError(f"Unknown Ingestion endpoint key: {endpoint_key}")
        return f"{self.api_ingestion_base_url}{self.endpoints[endpoint_key]}"


# To make it accessible for AppStateManager
# Ensure this file defines what app_state.py is trying to import.
# If AppConfig, DEFAULT_IMAGES_PATH, DEFAULT_COLLECTION_NAME are already defined,
# then the issue might be a circular import or an error within this config.py file itself. 