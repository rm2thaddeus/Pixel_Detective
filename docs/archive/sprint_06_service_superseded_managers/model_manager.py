# 📂 File Path: /project_root/models/model_manager.py
# 📌 Purpose: Manages the loading, unloading, and access to AI models.
# 🔄 Latest Changes: Created module to centralize model management.
# ⚙️ Key Logic: Provides a single interface for working with CLIP and BLIP models.
# 🧠 Reasoning: Centralizes model management to avoid repeated loading/unloading.

import torch
import time
import logging
import threading
from enum import Enum
from models.clip_model import load_clip_model, unload_clip_model, process_image # These imports will fail after move
from models.blip_model import load_blip_model, unload_blip_model, generate_caption # These imports will fail after move
from config import KEEP_MODELS_LOADED
from utils.embedding_cache import get_cache
from utils.duplicate_detector import compute_sha256

logger = logging.getLogger(__name__)

# Added for async loading status
class ModelLoadStatus(Enum):
    NOT_LOADED = 0
    LOADING = 1
    LOADED = 2
    FAILED = 3

class ModelManager:
    """
    Manages the loading, unloading, and access to AI models.
    Provides a centralized interface for working with models.
    Now supports asynchronous preloading.
    """
    
    def __init__(self, device=None, load_on_init=False):
        """
        Initialize the model manager.
        
        Args:
            device: The device to load models on (cuda or cpu)
            load_on_init: If True, loads models synchronously during initialization (old behavior).
                          Defaults to False for asynchronous loading.
        """
        self.device = device or (torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu"))
        self.clip_model = None
        self.clip_preprocess = None
        self.blip_model = None
        self.blip_processor = None
        
        # For async loading
        self._clip_status = ModelLoadStatus.NOT_LOADED
        self._blip_status = ModelLoadStatus.NOT_LOADED
        self._clip_load_thread = None
        self._blip_load_thread = None
        self._load_lock = threading.RLock() # Use RLock for re-entrant lock if methods call each other

        self._preload_callback = None # Store callback for async preloading

        if load_on_init:
            logger.info("Synchronous model loading on init requested.")
        # Load CLIP immediately; attempt BLIP but don't crash on OOM
            # This part remains for explicit synchronous loading if needed by other parts of app,
            # but FastStartupManager will use preload_models_async.
            if torch.cuda.is_available() or not self.device.type == 'cuda': # Allow CPU loading too
                self.load_clip_model(is_sync_call=True) # Pass a flag if needed to differentiate behavior
                try:
                    self.load_blip_model(is_sync_call=True)
                except Exception as init_ex:
                    logger.error(f"Error loading BLIP model at init (if load_on_init=True): {init_ex}. It will be loaded on demand.")
    
    def _execute_load(self, model_type_str: str, load_function: callable, status_attr: str, model_attr: str, processor_attr: str = None):
        """Helper function to execute model loading and manage status."""
        actual_model_attr_name = model_attr
        actual_processor_attr_name = processor_attr

        with self._load_lock:
            if getattr(self, actual_model_attr_name) is not None:
                # logger.debug(f"{model_type_str} model already loaded.")
                return getattr(self, actual_model_attr_name), getattr(self, actual_processor_attr_name) if actual_processor_attr_name else None
            
            current_status = getattr(self, status_attr)
            if current_status == ModelLoadStatus.LOADING:
                logger.info(f"{model_type_str} model is already loading in another thread. Call will not block.")
                # This should ideally not happen if preload_async is managed well.
                # If it does, the caller needs to be aware it might get None if it can't wait.
                return None, None 

            setattr(self, status_attr, ModelLoadStatus.LOADING)
        
        model = None
        processor_or_preprocess = None
        success = False
        error_str = None

        try:
            logger.info(f"Loading {model_type_str} model on {self.device}...")
            start_time = time.time()
            
            # The actual model loading call
            model, processor_or_preprocess = load_function(device=self.device)
            
            with self._load_lock:
                setattr(self, actual_model_attr_name, model)
                if actual_processor_attr_name:
                    setattr(self, actual_processor_attr_name, processor_or_preprocess)
                setattr(self, status_attr, ModelLoadStatus.LOADED)
                logger.info(f"{model_type_str} model loaded in {time.time() - start_time:.2f} seconds")
            success = True
        except Exception as e:
            with self._load_lock:
                setattr(self, status_attr, ModelLoadStatus.FAILED)
            error_str = str(e)
            logger.error(f"Failed to load {model_type_str} model: {e}", exc_info=True)
        
        if self._preload_callback:
            self._preload_callback(model_type_str.lower(), success, error_str)
        
        if success:
            return model, processor_or_preprocess
        else:
            # raise RuntimeError(f"Failed to load {model_type_str}: {error_str}") from e if success is False else None
            return None, None


    def load_clip_model(self, is_sync_call=False):
        model, preprocess = self._execute_load("CLIP", load_clip_model, "_clip_status", "clip_model", "clip_preprocess")
        if model: # Only assign if successfully loaded
             self.clip_model, self.clip_preprocess = model, preprocess
        return self.clip_model, self.clip_preprocess

    def load_blip_model(self, is_sync_call=False):
        model, processor = self._execute_load("BLIP", load_blip_model, "_blip_status", "blip_model", "blip_processor")
        if model: # Only assign if successfully loaded
            self.blip_model, self.blip_processor = model, processor
        return self.blip_model, self.blip_processor

    def preload_models_async(self, callback=None):
        logger.info("Starting asynchronous model preloading...")
        self._preload_callback = callback

        with self._load_lock:
            can_load_clip = self._clip_status == ModelLoadStatus.NOT_LOADED and \
                            (self._clip_load_thread is None or not self._clip_load_thread.is_alive())
            can_load_blip = self._blip_status == ModelLoadStatus.NOT_LOADED and \
                            (self._blip_load_thread is None or not self._blip_load_thread.is_alive())

        if can_load_clip:
            logger.info("Queueing CLIP model for async loading.")
            self._clip_load_thread = threading.Thread(target=self.load_clip_model, daemon=True, name="CLIPLoader")
            self._clip_load_thread.start()
        else:
            logger.info(f"CLIP model not queued for async loading. Status: {self._clip_status}, Thread alive: {self._clip_load_thread.is_alive() if self._clip_load_thread else 'N/A'}")
            # If already loaded or failed, and callback exists, notify immediately
            if self._preload_callback and (self._clip_status == ModelLoadStatus.LOADED or self._clip_status == ModelLoadStatus.FAILED):
                 self._preload_callback("clip", self._clip_status == ModelLoadStatus.LOADED, "Already loaded" if self._clip_status == ModelLoadStatus.LOADED else "Previously failed")


        if can_load_blip:
            logger.info("Queueing BLIP model for async loading.")
            self._blip_load_thread = threading.Thread(target=self.load_blip_model, daemon=True, name="BLIPLoader")
            self._blip_load_thread.start()
        else:
            logger.info(f"BLIP model not queued for async loading. Status: {self._blip_status}, Thread alive: {self._blip_load_thread.is_alive() if self._blip_load_thread else 'N/A'}")
            if self._preload_callback and (self._blip_status == ModelLoadStatus.LOADED or self._blip_status == ModelLoadStatus.FAILED):
                 self._preload_callback("blip", self._blip_status == ModelLoadStatus.LOADED, "Already loaded" if self._blip_status == ModelLoadStatus.LOADED else "Previously failed")


    def are_all_models_ready(self):
        with self._load_lock:
            clip_done = self._clip_status in [ModelLoadStatus.LOADED, ModelLoadStatus.FAILED]
            blip_done = self._blip_status in [ModelLoadStatus.LOADED, ModelLoadStatus.FAILED]
            # logger.debug(f"are_all_models_ready: CLIP status {self._clip_status}, BLIP status {self._blip_status}")
            return clip_done and blip_done

    # Generic load_model for the check in get_cached_model_manager
    def load_model(self, model_type: str): # This is what get_cached_model_manager checks
        if model_type.lower() == "clip":
            return self.load_clip_model()
        elif model_type.lower() == "blip":
            return self.load_blip_model()
        else:
            logger.warning(f"Unknown model type for load_model: {model_type}")
            return None, None

    
    def unload_all_models(self):
        """
        Unload all models from memory if they should not be kept loaded.
        """
        if not KEEP_MODELS_LOADED:
            self.unload_clip_model()
            self.unload_blip_model()
            # Reset statuses
            with self._load_lock:
                self._clip_status = ModelLoadStatus.NOT_LOADED
                self._blip_status = ModelLoadStatus.NOT_LOADED
        else:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def unload_clip_model(self):
        """
        Unload the CLIP model from memory.
        """
        with self._load_lock:
            if self.clip_model is not None:
                unload_clip_model() # Assuming this is the actual unload call
                self.clip_model = None
                self.clip_preprocess = None
                self._clip_status = ModelLoadStatus.NOT_LOADED
                logger.info("CLIP model unloaded.")
    
    def unload_blip_model(self):
        """
        Unload the BLIP model from memory.
        """
        with self._load_lock:
            if self.blip_model is not None:
                unload_blip_model() # Assuming this is the actual unload call
                self.blip_model = None
                self.blip_processor = None
                self._blip_status = ModelLoadStatus.NOT_LOADED
                logger.info("BLIP model unloaded.")
    
    def process_image(self, image_path):
        """
        Process an image to generate its embedding using CLIP.
        Ensures CLIP model is loaded before processing.
        """
        if self._clip_status != ModelLoadStatus.LOADED:
            logger.info("CLIP model not loaded, attempting to load for process_image...")
            self.load_clip_model() # This will block if called directly and model not loaded
            if self._clip_status != ModelLoadStatus.LOADED:
                raise RuntimeError("CLIP model failed to load, cannot process image.")

        cache = get_cache()
        file_hash = compute_sha256(image_path)
        cached = cache.get(file_hash)
        if cached is not None:
            return cached
        
        embedding = process_image(self.clip_model, self.clip_preprocess, image_path) # Assuming process_image takes model&preprocess
        cache.set(file_hash, embedding)
        return embedding
    
    def generate_caption(self, image_path, metadata=None):
        """
        Generate a caption for an image using BLIP.
        Ensures BLIP model is loaded.
        """
        if self._blip_status != ModelLoadStatus.LOADED:
            logger.info("BLIP model not loaded, attempting to load for generate_caption...")
            self.load_blip_model()
            if self._blip_status != ModelLoadStatus.LOADED:
                raise RuntimeError("BLIP model failed to load, cannot generate caption.")

        # BLIP processing here
        # This is simplified; actual processing involves PIL, transforms, etc.
        # Placeholder until full integration. Ensure model and processor are available.
        if self.blip_model and self.blip_processor:
            caption_text = generate_caption(self.blip_model, self.blip_processor, image_path, metadata=metadata)
            return caption_text
        else:
            logger.error("BLIP model or processor not available for captioning.")
            return "Error: BLIP model not available."

    # Placeholder for comprehensive image understanding
    def get_image_understanding(self, image_path, top_k=10):
        """
        Orchestrates getting embeddings, captions, and potentially other insights.
        This is a high-level method that utilizes other specific model methods.
        This method's logic will eventually be more sophisticated, handling errors,
        and possibly integrating other AI models or data sources in the future.
        
        Args:
            image_path (str): Path to the image file.
            top_k (int): Number of top similar images (for future search features).

        Returns:
            dict: A dictionary containing embeddings, caption, and other metadata.
                  Returns None if essential components (like CLIP model) fail to load.
        """
        logger.info(f"Getting image understanding for: {image_path}")
        understanding = {
            "image_path": image_path,
            "embedding": None,
            "caption": None,
            "errors": []
        }

        try:
            embedding = self.process_image(image_path)
            understanding["embedding"] = embedding
        except RuntimeError as e:
            logger.error(f"RuntimeError processing image for embedding: {e}")
            understanding["errors"].append(str(e))
        except Exception as e:
            logger.error(f"Unexpected error processing image for embedding: {e}", exc_info=True)
            understanding["errors"].append(f"Unexpected embedding error: {str(e)}")

        try:
            # Assuming metadata is extracted elsewhere or not needed for basic captioning here
            caption = self.generate_caption(image_path)
            understanding["caption"] = caption
        except RuntimeError as e:
            logger.error(f"RuntimeError generating caption: {e}")
            understanding["errors"].append(str(e))
        except Exception as e:
            logger.error(f"Unexpected error generating caption: {e}", exc_info=True)
            understanding["errors"].append(f"Unexpected caption error: {str(e)}")
        
        # Clean up errors if empty
        if not understanding["errors"]:
            del understanding["errors"]
            
        return understanding

    # --- Added for Sprint 05 --- 
    def embed_image(self, image_path: str):
        # Alias for process_image for clarity if used by external components
        return self.process_image(image_path)

    def caption_image(self, image_path: str):
        # Alias for generate_caption
        return self.generate_caption(image_path) 