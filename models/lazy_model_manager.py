# 📂 File Path: /project_root/models/lazy_model_manager.py
# 📌 Purpose: Lazy loading model manager implementing next_sprint.md performance improvements
# 🔄 Latest Changes: Created to implement lazy loading pattern from mvp_app.py
# ⚙️ Key Logic: Load models only when needed, sequential loading pattern, explicit cleanup
# 🧠 Reasoning: Reduces startup time from 10s to <3s, memory from 2.2GB to <500MB baseline

import torch
import time
import logging
import gc
from models.clip_model import load_clip_model, unload_clip_model, process_image
from models.blip_model import load_blip_model, unload_blip_model, generate_caption
from config import KEEP_MODELS_LOADED
from utils.embedding_cache import get_cache
from utils.duplicate_detector import compute_sha256
from utils.cuda_utils import log_cuda_memory_usage

logger = logging.getLogger(__name__)

class LazyModelManager:
    """
    Lazy loading model manager implementing performance optimizations from next_sprint.md.
    
    Key improvements:
    - Models load only when needed (not at startup)
    - Sequential loading pattern from mvp_app.py 
    - Explicit memory cleanup between model swaps
    - Memory threshold monitoring
    """
    
    def __init__(self, device=None):
        """
        Initialize the lazy model manager.
        
        Args:
            device: The device to load models on (cuda or cpu)
        """
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        
        # Model state - None means not loaded (lazy loading)
        self.clip_model = None
        self.clip_preprocess = None
        self.blip_model = None
        self.blip_processor = None
        
        # Track which model is currently loaded for smart swapping
        self._current_model = None  # 'clip', 'blip', or None
        
        # Memory threshold for automatic cleanup (80% of available VRAM)
        self._memory_threshold = 0.8
        
        logger.info(f"LazyModelManager initialized on {self.device} - models will load on demand")
    
    def _check_memory_pressure(self):
        """Check if we're approaching memory limits and need cleanup."""
        if not torch.cuda.is_available():
            return False
            
        try:
            allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            usage_ratio = allocated / total_memory
            
            if usage_ratio > self._memory_threshold:
                logger.warning(f"Memory pressure detected: {usage_ratio:.1%} usage ({allocated:.1f}GB/{total_memory:.1f}GB)")
                return True
        except Exception as e:
            logger.error(f"Error checking memory pressure: {e}")
        
        return False
    
    def _cleanup_for_model_swap(self, target_model):
        """Clean up memory before loading a different model (mvp_app.py pattern)."""
        if self._current_model == target_model:
            return  # No swap needed
            
        if self._current_model == 'clip' and target_model == 'blip':
            logger.info("Swapping CLIP → BLIP: cleaning up CLIP model")
            self.unload_clip_model()
        elif self._current_model == 'blip' and target_model == 'clip':
            logger.info("Swapping BLIP → CLIP: cleaning up BLIP model")
            self.unload_blip_model()
    
    def _after_model_cleanup(self, model_name):
        """Explicit memory cleanup after model unloading (mvp_app.py pattern)."""
        try:
            # Force garbage collection
            gc.collect()
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
            log_cuda_memory_usage(f"After {model_name} cleanup")
            logger.info(f"{model_name} model cleanup completed")
        except Exception as e:
            logger.error(f"Error in {model_name} cleanup: {e}")
    
    def get_clip_model_for_search(self):
        """
        Get CLIP model for search operations (lazy loading).
        
        Returns:
            tuple: (model, preprocess) - The CLIP model and preprocessing function
        """
        # Check for memory pressure and clean up if needed
        if self._check_memory_pressure():
            self._cleanup_for_model_swap('clip')
        
        if self.clip_model is None:
            # Smart cleanup: unload BLIP if loaded to make room
            if self._current_model == 'blip':
                self._cleanup_for_model_swap('clip')
                
            start_time = time.time()
            logger.info(f"Lazy loading CLIP model on {self.device}...")
            log_cuda_memory_usage("Before CLIP lazy load")
            
            self.clip_model, self.clip_preprocess = load_clip_model(device=self.device)
            self._current_model = 'clip'
            
            load_time = time.time() - start_time
            logger.info(f"CLIP model lazy loaded in {load_time:.2f} seconds")
            log_cuda_memory_usage("After CLIP lazy load")
        
        return self.clip_model, self.clip_preprocess
    
    def get_blip_model_for_caption(self):
        """
        Get BLIP model for caption generation (lazy loading).
        
        Returns:
            tuple: (model, processor) - The BLIP model and processor
        """
        # Check for memory pressure and clean up if needed
        if self._check_memory_pressure():
            self._cleanup_for_model_swap('blip')
        
        if self.blip_model is None:
            # Smart cleanup: unload CLIP if loaded to make room
            if self._current_model == 'clip':
                self._cleanup_for_model_swap('blip')
                
            start_time = time.time()
            logger.info(f"Lazy loading BLIP model on {self.device}...")
            log_cuda_memory_usage("Before BLIP lazy load")
            
            self.blip_model, self.blip_processor = load_blip_model(device=self.device)
            self._current_model = 'blip'
            
            load_time = time.time() - start_time
            logger.info(f"BLIP model lazy loaded in {load_time:.2f} seconds")
            log_cuda_memory_usage("After BLIP lazy load")
        
        return self.blip_model, self.blip_processor
    
    def unload_clip_model(self):
        """Unload the CLIP model from memory with explicit cleanup."""
        if self.clip_model is not None:
            logger.info("Unloading CLIP model...")
            unload_clip_model()
            self.clip_model = None
            self.clip_preprocess = None
            
            if self._current_model == 'clip':
                self._current_model = None
                
            self._after_model_cleanup('CLIP')
    
    def unload_blip_model(self):
        """Unload the BLIP model from memory with explicit cleanup."""
        if self.blip_model is not None:
            logger.info("Unloading BLIP model...")
            unload_blip_model()
            self.blip_model = None
            self.blip_processor = None
            
            if self._current_model == 'blip':
                self._current_model = None
                
            self._after_model_cleanup('BLIP')
    
    def unload_all_models(self):
        """Unload all models from memory if they should not be kept loaded."""
        if not KEEP_MODELS_LOADED:
            logger.info("Unloading all models as KEEP_MODELS_LOADED is False")
            self.unload_clip_model()
            self.unload_blip_model()
        else:
            # Just clean up any unused memory but keep models loaded
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("Cleaned CUDA cache but kept models loaded")
    
    def process_image(self, image_path):
        """
        Process an image to generate its embedding using CLIP (with lazy loading).
        
        Args:
            image_path: Path to the image file
            
        Returns:
            numpy.ndarray: The image embedding
        """
        # Use cache first
        cache = get_cache()
        file_hash = compute_sha256(image_path)
        cached = cache.get(file_hash)
        if cached is not None:
            logger.debug(f"Using cached embedding for {image_path}")
            return cached
        
        # Ensure CLIP model is loaded (lazy loading)
        self.get_clip_model_for_search()
        
        # Process the image
        embedding = process_image(image_path)
        cache.set(file_hash, embedding)
        return embedding
    
    def generate_caption(self, image_path, metadata=None):
        """
        Generate a caption for an image using BLIP (with lazy loading).
        
        Args:
            image_path: Path to the image file
            metadata: Optional metadata about the image
            
        Returns:
            dict: A dictionary containing the generated caption and original tags
        """
        # Ensure BLIP model is loaded (lazy loading)
        self.get_blip_model_for_caption()
        
        # Generate caption
        return generate_caption(image_path, metadata)
    
    def get_image_understanding(self, image_path, top_k=10):
        """
        Get a textual understanding of an image by finding the most similar concepts.
        Uses sequential model loading to avoid memory issues.
        
        Args:
            image_path: Path to the image file
            top_k: Number of top concepts to return
            
        Returns:
            list: List of (concept, score) tuples
        """
        from models.clip_model import get_image_understanding as clip_image_understanding
        
        results = []
        
        # Step 1: Get BLIP caption first (typically less memory intensive)
        try:
            caption_result = self.generate_caption(image_path)
            if isinstance(caption_result, dict) and 'caption' in caption_result:
                caption = caption_result['caption']
            else:
                caption = str(caption_result)
            results.append(("BLIP Caption", caption))
        except Exception as e:
            logger.error(f"Error generating BLIP caption: {e}")
        
        # Step 2: Sequential swap to CLIP for image understanding
        # This follows mvp_app.py pattern: BLIP → cleanup → CLIP
        if self._current_model == 'blip':
            self._cleanup_for_model_swap('clip')
        
        # Get CLIP understanding
        self.get_clip_model_for_search()
        understanding = clip_image_understanding(image_path, top_k)
        results.extend(understanding)
        
        return results
    
    def embed_image(self, image_path: str):
        """Compute or retrieve from cache the embedding for an image."""
        return self.process_image(image_path)

    def caption_image(self, image_path: str):
        """Generate a caption for an image."""
        return self.generate_caption(image_path)
    
    def get_memory_status(self):
        """Get current memory usage status for UI display."""
        if not torch.cuda.is_available():
            return {"available": False, "message": "CUDA not available"}
        
        try:
            allocated = torch.cuda.memory_allocated(0) / 1024**2  # MB
            reserved = torch.cuda.memory_reserved(0) / 1024**2   # MB
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**2  # MB
            
            usage_percent = (allocated / total_memory) * 100
            
            status = {
                "available": True,
                "allocated_mb": allocated,
                "reserved_mb": reserved, 
                "total_mb": total_memory,
                "usage_percent": usage_percent,
                "current_model": self._current_model,
                "message": f"GPU Memory: {allocated:.0f}MB allocated ({usage_percent:.1f}%), Model: {self._current_model or 'None'}"
            }
            
            return status
        except Exception as e:
            return {"available": False, "message": f"Error getting memory status: {e}"} 