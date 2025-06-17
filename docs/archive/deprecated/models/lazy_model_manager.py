import torch
import clip
from transformers import BlipProcessor, BlipForConditionalGeneration
import os
import time
import logging
from config import KEEP_MODELS_LOADED

logger = logging.getLogger(__name__)

class LazyModelManager:
    def __init__(self, device):
        self.device = device
        self.clip_model = None
        self.clip_preprocess = None
        self.blip_model = None
        self.blip_processor = None
        self.CLIP_MODEL_NAME = os.environ.get("CLIP_MODEL_NAME", "ViT-B/32")
        self.BLIP_MODEL_NAME = os.environ.get("BLIP_MODEL_NAME", "Salesforce/blip-image-captioning-large")

    def _load_clip_model(self):
        if self.clip_model is None:
            logger.info(f"Loading CLIP model ({self.CLIP_MODEL_NAME}) on {self.device}...")
            start_time = time.time()
            try:
                self.clip_model, self.clip_preprocess = clip.load(self.CLIP_MODEL_NAME, device=self.device)
                self.clip_model = self.clip_model.to(self.device)
                logger.info(f"CLIP model loaded in {time.time() - start_time:.2f}s.")
            except Exception as e:
                logger.error(f"Error loading CLIP model: {e}", exc_info=True)
                raise

    def _load_blip_model(self):
        if self.blip_model is None:
            logger.info(f"Loading BLIP model ({self.BLIP_MODEL_NAME}) on {self.device}...")
            start_time = time.time()
            try:
                self.blip_processor = BlipProcessor.from_pretrained(self.BLIP_MODEL_NAME)
                self.blip_model = BlipForConditionalGeneration.from_pretrained(self.BLIP_MODEL_NAME)
                self.blip_model = self.blip_model.to(self.device)
                logger.info(f"BLIP model loaded in {time.time() - start_time:.2f}s.")
            except Exception as e:
                logger.error(f"Error loading BLIP model: {e}", exc_info=True)
                raise

    def get_clip_model_for_search(self):
        self._load_clip_model()
        if not KEEP_MODELS_LOADED:
            self.blip_model = None
            self.blip_processor = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return self.clip_model, self.clip_preprocess

    def get_blip_model_for_caption(self):
        self._load_blip_model()
        if not KEEP_MODELS_LOADED:
            self.clip_model = None
            self.clip_preprocess = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        return self.blip_model, self.blip_processor 