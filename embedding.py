# 📂 File Path: /project_root/embedding.py
# 📌 Purpose: This file provides functionality for generating embeddings using the CLIP model.
# 🔄 Latest Changes: Added detailed comments to improve code readability and maintainability.
# ⚙️ Key Logic: Utilizes PyTorch and CLIP to generate image and text embeddings for similarity search.
# 🧠 Reasoning: CLIP's ability to handle both image and text inputs makes it ideal for cross-modal retrieval tasks.

import torch
import clip
from PIL import Image
import io
import numpy as np
import os
import time
import traceback
import streamlit as st

class CLIPEmbedder:
    def __init__(self, model_name="ViT-B/32"):
        """
        Initialize the CLIP model for embedding generation.
        
        Args:
            model_name (str): CLIP model variant to use
        """
        try:
            # Display loading status
            print("Loading CLIP model...")
            start_time = time.time()
            
            # Load the CLIP model
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.device = device
            self.model, self.preprocess = clip.load(model_name, device=device)
            
            # Set model to evaluation mode
            self.model.eval()
            
            load_time = time.time() - start_time
            print(f"CLIP model loaded on {device} in {load_time:.2f} seconds")
        except Exception as e:
            print(f"Error loading CLIP model: {e}")
            print(traceback.format_exc())
            raise Exception(f"Failed to load CLIP model: {str(e)}")
    
    @torch.no_grad()
    def get_embedding(self, image_path):
        """
        Generate an embedding for an image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            np.ndarray: Image embedding
        """
        try:
            # Check if file exists
            if not os.path.exists(image_path):
                print(f"File not found: {image_path}")
                return np.zeros(512, dtype=np.float32)
                
            # Load and preprocess the image
            if image_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                image = Image.open(image_path).convert("RGB")
                processed_image = self.preprocess(image).unsqueeze(0).to(self.device)
                
                # Generate embedding
                image_features = self.model.encode_image(processed_image)
                
                # Convert to numpy array and return
                return image_features.cpu().numpy().flatten()
            else:
                # For RAW and DNG files, we need to convert them to RGB first
                try:
                    from rawpy import imread
                    
                    # Read the raw image and convert to RGB
                    with imread(image_path) as raw:
                        rgb = raw.postprocess()
                    
                    # Convert numpy array to PIL image and preprocess
                    image = Image.fromarray(rgb)
                    processed_image = self.preprocess(image).unsqueeze(0).to(self.device)
                    
                    # Generate embedding
                    image_features = self.model.encode_image(processed_image)
                    
                    # Convert to numpy array and return
                    return image_features.cpu().numpy().flatten()
                except Exception as raw_error:
                    print(f"Error processing RAW file {image_path}: {raw_error}")
                    print(traceback.format_exc())
                    return np.zeros(512, dtype=np.float32)
        
        except Exception as e:
            print(f"Error generating embedding for {image_path}: {e}")
            print(traceback.format_exc())
            # Return a zero vector in case of error
            return np.zeros(512, dtype=np.float32)
    
    @torch.no_grad()
    def get_embedding_from_bytes(self, image_bytes):
        """
        Generate an embedding from image bytes.
        
        Args:
            image_bytes (bytes): Raw image bytes
            
        Returns:
            np.ndarray: Image embedding
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            processed_image = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate embedding
            image_features = self.model.encode_image(processed_image)
            
            # Convert to numpy array and return
            return image_features.cpu().numpy().flatten()
            
        except Exception as e:
            print(f"Error generating embedding from bytes: {e}")
            print(traceback.format_exc())
            # Return a zero vector in case of error
            return np.zeros(512, dtype=np.float32)
    
    @torch.no_grad()
    def get_text_embedding(self, text):
        """
        Generate an embedding for a text description.
        
        Args:
            text (str): Text to embed
            
        Returns:
            np.ndarray: Text embedding
        """
        try:
            # Tokenize and encode the text
            text_inputs = clip.tokenize([text]).to(self.device)
            text_features = self.model.encode_text(text_inputs)
            
            # Convert to numpy array and return
            return text_features.cpu().numpy().flatten()
            
        except Exception as e:
            print(f"Error generating text embedding: {e}")
            print(traceback.format_exc())
            # Return a zero vector in case of error
            return np.zeros(512, dtype=np.float32) 