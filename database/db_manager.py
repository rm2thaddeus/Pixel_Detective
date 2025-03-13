# 📂 File Path: /project_root/database/db_manager.py
# 📌 Purpose: Manages database operations for the image search application.
# 🔄 Latest Changes: Created module to centralize database operations.
# ⚙️ Key Logic: Provides functions to build, load, and search the image database.
# 🧠 Reasoning: Centralizes database operations for better code organization.

import os
import numpy as np
import pandas as pd
import logging
import glob
import torch
import gc
from metadata_extractor import extract_metadata
from models.blip_model import generate_caption
from config import DB_EMBEDDINGS_FILE, DB_METADATA_FILE, GPU_MEMORY_EFFICIENT

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database operations for the image search application.
    """
    
    def __init__(self, model_manager):
        """
        Initialize the database manager.
        
        Args:
            model_manager: The model manager to use for processing images
        """
        self.model_manager = model_manager
    
    def get_image_list(self, folder):
        """
        Returns a list of image file paths in the given folder.
        Looks for common image file extensions.
        
        Args:
            folder: Path to the folder containing images
            
        Returns:
            list: List of image file paths
        """
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif']
        image_files = set()
        
        logger.info(f"Scanning folder: {folder}")
        for ext in image_extensions:
            found = glob.glob(os.path.join(folder, ext))
            logger.info(f"Found {len(found)} files with extension {ext}")
            image_files.update(found)
        
        unique_files = sorted(list(image_files))
        logger.info(f"Total unique images found: {len(unique_files)}")
        return unique_files
    
    def build_database(self, db_folder, image_list):
        """
        Builds a vector database from a list of images.

        Args:
            db_folder (str): The folder where the database files will be stored.
            image_list (list): A list of paths to the image files.

        Returns:
            bool: True if the database was built successfully, False otherwise.
        """
        embeddings = []
        metadata_records = []

        for i, image_path in enumerate(image_list):
            # Process image and compute embedding
            embedding = self.model_manager.process_image(image_path)
            embeddings.append(embedding)

            # Extract metadata for the image
            metadata = extract_metadata(image_path)

            # Generate BLIP caption
            caption = generate_caption(image_path)
            metadata["caption"] = caption

            # Use Keywords from XMP if available, otherwise use the caption.
            if "Keywords" not in metadata or not metadata["Keywords"]:
                metadata["Keywords"] = [caption]
            elif isinstance(metadata["Keywords"], str):
                metadata["Keywords"] = [metadata["Keywords"]] # Ensure it is a list

            # Prioritize 'tags' from XMP, fallback to 'Keywords'
            if "tags" not in metadata or not metadata["tags"]:
                metadata["tags"] = metadata.get("Keywords", [])
            elif isinstance(metadata["tags"], str):
                metadata["tags"] = [metadata["tags"]]

            metadata["path"] = image_path  # Record the image path
            metadata_records.append(metadata)

        # Save embeddings as a numpy array
        embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
        np.save(embeddings_path, np.array(embeddings))
        
        # Convert metadata records to a DataFrame and save as CSV
        metadata_df = pd.DataFrame(metadata_records)
        metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
        metadata_df.to_csv(metadata_path, index=False)
        
        # Update session state with loaded data
        import streamlit as st
        st.session_state.embeddings = np.array(embeddings)
        st.session_state.images_data = metadata_df
        st.session_state.database_built = True
        
        return True
    
    def database_exists(self, folder_path):
        """
        Check if a database exists in the given folder.
        
        Args:
            folder_path: Path to the folder to check
            
        Returns:
            bool: True if the database exists
        """
        db_embeddings_path = os.path.join(folder_path, DB_EMBEDDINGS_FILE)
        db_metadata_path = os.path.join(folder_path, DB_METADATA_FILE)
        return os.path.exists(db_embeddings_path) and os.path.exists(db_metadata_path)
    
    def load_database(self, db_folder):
        """
        Load a database from the given folder.
        
        Args:
            db_folder: Path to the folder containing the database
            
        Returns:
            bool: True if the database was loaded successfully
        """
        embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
        metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
        
        if os.path.exists(embeddings_path) and os.path.exists(metadata_path):
            import streamlit as st
            st.session_state.embeddings = np.load(embeddings_path)
            st.session_state.images_data = pd.read_csv(metadata_path)
            st.session_state.database_built = True
            return True
        
        return False
    
    def search_similar_images(self, query_text, top_k=5):
        """
        Search for images similar to the query text.
        
        Args:
            query_text: The text query to search for
            top_k: Number of top results to return
            
        Returns:
            list: List of dictionaries containing search results
        """
        import streamlit as st
        import clip
        
        try:
            # Get CLIP model
            model, preprocess = self.model_manager.load_clip_model()
            device = self.model_manager.device
            
            # Tokenize and encode the text query
            with torch.no_grad():
                text = clip.tokenize([query_text]).to(device)
                text_features = model.encode_text(text)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            
            # Convert to numpy array
            text_features_np = text_features.cpu().numpy()
            
            # Compute similarity scores
            similarities = np.dot(st.session_state.embeddings, text_features_np.T).squeeze()
            
            # Create a list of (index, score) tuples for all images
            scored_indices = [(i, float(score)) for i, score in enumerate(similarities)]
            
            # Sort by score and get top-k
            scored_indices.sort(key=lambda x: x[1], reverse=True)
            top_scored_indices = scored_indices[:top_k]
            
            results = []
            for idx, score in top_scored_indices:
                img_path = st.session_state.images_data.iloc[idx]['path']
                result = {
                    'path': img_path,
                    'score': score,
                    'index': int(idx)
                }
                
                # Add metadata fields to results
                metadata = st.session_state.images_data.iloc[idx]
                if 'caption' in metadata:
                    result['caption'] = metadata['caption']
                if 'tags' in metadata:
                    result['tags'] = metadata['tags']
                if 'Keywords' in metadata:
                    result['keywords'] = metadata['Keywords']
                    
                results.append(result)
            
            # Clean up GPU memory if needed
            if GPU_MEMORY_EFFICIENT:
                del text, text_features
                torch.cuda.empty_cache()
                gc.collect()
            
            return results
        except Exception as e:
            logger.error(f"Error searching by text: {e}")
            return []
    
    def search_by_image(self, image_path, top_k=5):
        """
        Search for images similar to the query image.
        
        Args:
            image_path: Path to the query image
            top_k: Number of top results to return
            
        Returns:
            list: List of dictionaries containing search results
        """
        import streamlit as st
        from PIL import Image
        
        try:
            # Get CLIP model
            model, preprocess = self.model_manager.load_clip_model()
            device = self.model_manager.device
            
            # Open and preprocess the image
            image = Image.open(image_path).convert('RGB')
            image_input = preprocess(image).unsqueeze(0).to(device)
            
            # Generate the image embedding
            with torch.no_grad():
                image_features = model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # Convert to numpy array
            image_features_np = image_features.cpu().numpy()
            
            # Compute similarity scores
            similarities = np.dot(st.session_state.embeddings, image_features_np.T).squeeze()
            
            # Create a list of (index, score) tuples for all images
            scored_indices = [(i, float(score)) for i, score in enumerate(similarities)]
            
            # Sort by score and get top-k
            scored_indices.sort(key=lambda x: x[1], reverse=True)
            top_scored_indices = scored_indices[:top_k]
            
            results = []
            for idx, score in top_scored_indices:
                img_path = st.session_state.images_data.iloc[idx]['path']
                result = {
                    'path': img_path,
                    'score': score,
                    'index': int(idx)
                }
                
                # Add metadata fields to results
                metadata = st.session_state.images_data.iloc[idx]
                if 'caption' in metadata:
                    result['caption'] = metadata['caption']
                if 'tags' in metadata:
                    result['tags'] = metadata['tags']
                if 'Keywords' in metadata:
                    result['keywords'] = metadata['Keywords']
                    
                results.append(result)
            
            # Clean up GPU memory if needed
            if GPU_MEMORY_EFFICIENT:
                del image_input, image_features
                torch.cuda.empty_cache()
                gc.collect()
            
            return results
        except Exception as e:
            logger.error(f"Error searching by image: {e}")
            return [] 