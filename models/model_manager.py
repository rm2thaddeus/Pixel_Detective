# 📂 File Path: /project_root/models/model_manager.py
# 📌 Purpose: Manages the loading, unloading, and access to AI models.
# 🔄 Latest Changes: Created module to centralize model management.
# ⚙️ Key Logic: Provides a single interface for working with CLIP and BLIP models.
# 🧠 Reasoning: Centralizes model management to avoid repeated loading/unloading.

import torch
import time
import logging
from models.clip_model import load_clip_model, unload_clip_model, process_image
from models.blip_model import load_blip_model, unload_blip_model, generate_caption
from config import KEEP_MODELS_LOADED
from utils.embedding_cache import get_cache
from utils.duplicate_detector import compute_sha256

logger = logging.getLogger(__name__)

class ModelManager:
    """
    Manages the loading, unloading, and access to AI models.
    Provides a centralized interface for working with models.
    """
    
    def __init__(self, device=None):
        """
        Initialize the model manager.
        
        Args:
            device: The device to load models on (cuda or cpu)
        """
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.clip_model = None
        self.clip_preprocess = None
        self.blip_model = None
        self.blip_processor = None
        self.models_loaded = False
        
        # Load CLIP immediately; attempt BLIP but don't crash on OOM
        if torch.cuda.is_available():
            # Load CLIP model up front
            self.load_clip_model()
            # Try to load BLIP model, but defer failure to runtime
            try:
                self.load_blip_model()
            except Exception as init_ex:
                logger.error(f"Error loading BLIP model at init: {init_ex}. It will be loaded on demand.")
            self.models_loaded = True
    
    def load_all_models(self):
        """
        Load all models (CLIP and BLIP) into memory.
        """
        self.load_clip_model()
        self.load_blip_model()
    
    def unload_all_models(self):
        """
        Unload all models from memory if they should not be kept loaded.
        """
        if not KEEP_MODELS_LOADED:
            self.unload_clip_model()
            self.unload_blip_model()
            self.models_loaded = False
        else:
            # Just clean up any unused memory but keep models loaded
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def load_clip_model(self):
        """
        Load the CLIP model if not already loaded.
        
        Returns:
            tuple: (model, preprocess) - The CLIP model and preprocessing function
        """
        if self.clip_model is None:
            start_time = time.time()
            logger.info(f"Loading CLIP model on {self.device}...")
            self.clip_model, self.clip_preprocess = load_clip_model(device=self.device)
            logger.info(f"CLIP model loaded in {time.time() - start_time:.2f} seconds")
        
        return self.clip_model, self.clip_preprocess
    
    def load_blip_model(self):
        """
        Load the BLIP model if not already loaded.
        
        Returns:
            tuple: (model, processor) - The BLIP model and processor
        """
        if self.blip_model is None:
            start_time = time.time()
            logger.info(f"Loading BLIP model on {self.device}...")
            self.blip_model, self.blip_processor = load_blip_model(device=self.device)
            logger.info(f"BLIP model loaded in {time.time() - start_time:.2f} seconds")
        
        return self.blip_model, self.blip_processor
    
    def unload_clip_model(self):
        """
        Unload the CLIP model from memory.
        """
        if self.clip_model is not None:
            unload_clip_model()
            self.clip_model = None
            self.clip_preprocess = None
    
    def unload_blip_model(self):
        """
        Unload the BLIP model from memory.
        """
        if self.blip_model is not None:
            unload_blip_model()
            self.blip_model = None
            self.blip_processor = None
    
    def process_image(self, image_path):
        """
        Process an image to generate its embedding using CLIP.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            numpy.ndarray: The image embedding
        """
        # Ensure CLIP model is loaded
        self.load_clip_model()
        # Use cache
        cache = get_cache()
        file_hash = compute_sha256(image_path)
        cached = cache.get(file_hash)
        if cached is not None:
            return cached
        # Process the image
        embedding = process_image(image_path)
        cache.set(file_hash, embedding)
        return embedding
    
    def generate_caption(self, image_path, metadata=None):
        """
        Generate a caption for an image using BLIP.
        
        Args:
            image_path: Path to the image file
            metadata: Optional metadata about the image
            
        Returns:
            dict: A dictionary containing the generated caption and original tags
        """
        # Ensure BLIP model is loaded
        self.load_blip_model()
        
        # Generate caption
        return generate_caption(image_path, metadata)
    
    def get_image_understanding(self, image_path, top_k=10):
        """
        Get a textual understanding of an image by finding the most similar concepts.
        
        Args:
            image_path: Path to the image file
            top_k: Number of top concepts to return
            
        Returns:
            list: List of (concept, score) tuples
        """
        from models.clip_model import get_image_understanding as clip_image_understanding
        
        # Ensure both models are loaded
        self.load_clip_model()
        self.load_blip_model()
        
        # Get image understanding using CLIP
        understanding = clip_image_understanding(image_path, top_k)
        
        # Also get a caption using BLIP
        try:
            caption_result = self.generate_caption(image_path)
            if isinstance(caption_result, dict) and 'caption' in caption_result:
                caption = caption_result['caption']
            else:
                caption = str(caption_result)
            understanding.insert(0, ("BLIP Caption", caption))
        except Exception as e:
            logger.error(f"Error generating BLIP caption: {e}")
        
        return understanding 

    def embed_image(self, image_path: str):
        """
        Compute or retrieve from cache the embedding for an image.
        """
        return self.process_image(image_path)

    def caption_image(self, image_path: str):
        """
        Generate a caption for an image.
        """
        return self.generate_caption(image_path) 