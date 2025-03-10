# 📂 File Path: /project_root/app.py
# 📌 Purpose: This file serves as the main application script for the Pixel Detective image search application.
# 🔄 Latest Changes: 
#   - Optimized GPU memory usage for BLIP-2 and CLIP models
#   - Implemented proper model loading and unloading to share GPU resources
#   - Enhanced caption generation with BLIP-2
#   - Added memory-efficient processing for large image collections
# ⚙️ Key Logic: Utilizes Streamlit for the web interface and CLIP for image processing and search capabilities.
# 🧠 Reasoning: Streamlit provides an easy-to-use interface for deploying machine learning models, while CLIP offers robust image-text matching.

"""
Pixel Detective: Image Search Application.
"""
import os
os.environ['STREAMLIT_WATCH_EXCLUDE_MODULES'] = 'torch'
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

import streamlit as st
import os
import time
import gc
from PIL import Image
import torch
import clip
from pathlib import Path
import numpy as np
import pandas as pd
import logging
from datetime import datetime
import pickle
import json
import random
import glob
import re

import tkinter as tk
from tkinter import filedialog
from metadata_extractor import extract_metadata

from utils.logger import logger
from models.clip_model import setup_device, load_clip_model, process_image, unload_clip_model
from models.blip_model import generate_caption, unload_blip_model
from ui.tabs import render_text_search_tab, render_image_upload_tab, render_guessing_game_tab
from config import DB_EMBEDDINGS_FILE, DB_METADATA_FILE, GPU_MEMORY_EFFICIENT

# 2. FUNCTION DEFINITIONS - Define ALL functions before using them
def get_image_list(folder: str):
    """
    Returns a list of image file paths in the given folder.
    Looks for common image file extensions.
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

def initialize_session_state():
    if 'database_built' not in st.session_state:
        st.session_state.database_built = False
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    if 'total_images' not in st.session_state:
        st.session_state.total_images = 0
    if 'db_building_complete' not in st.session_state:
        st.session_state.db_building_complete = False
    if 'images_data' not in st.session_state:
        st.session_state.images_data = None
    if 'embeddings' not in st.session_state:
        st.session_state.embeddings = None
    if 'image_files' not in st.session_state:
        st.session_state.image_files = None
    if 'clip_model' not in st.session_state:
        st.session_state.clip_model = None
    if 'clip_preprocess' not in st.session_state:
        st.session_state.clip_preprocess = None
    if 'blip_model' not in st.session_state:
        st.session_state.blip_model = None
    if 'blip_processor' not in st.session_state:
        st.session_state.blip_processor = None
    if 'device' not in st.session_state:
        st.session_state.device = setup_device()
    if 'game_image_shown' not in st.session_state:
        st.session_state.game_image_shown = False
    if 'image_understanding' not in st.session_state:
        st.session_state.image_understanding = None
    if 'models_loaded' not in st.session_state:
        st.session_state.models_loaded = False

# Function to build database
def build_database(db_folder, image_list):
    """
    Build a new database from a list of images.
    This extracts each image's metadata including the Keywords, and then saves embeddings and metadata.
    """
    embeddings = []        # To store image embeddings
    metadata_records = []  # To store metadata dictionaries
    
    # Load CLIP model for embeddings
    load_clip_model()
    
    for i, image_path in enumerate(image_list):
        # Update progress
        if hasattr(st.session_state, 'current_image_index'):
            st.session_state.current_image_index = i + 1
        
        # Process the image and compute its embedding
        embedding = process_image(image_path)
        embeddings.append(embedding)
        
        # Extract metadata for the image
        metadata = extract_metadata(image_path)
        
        # Generate BLIP caption for the image
        caption = generate_caption(image_path, metadata)
        
        # Add the caption to metadata
        metadata["caption"] = caption
        
        # Always include the caption in Keywords
        if "Keywords" not in metadata or not metadata["Keywords"]:
            metadata["Keywords"] = [caption]
        else:
            # If Keywords exists but doesn't contain the caption, add it
            if isinstance(metadata["Keywords"], list):
                if caption not in metadata["Keywords"]:
                    metadata["Keywords"].append(caption)
            else:
                # If Keywords is not a list, convert it to a list and add the caption
                metadata["Keywords"] = [metadata["Keywords"], caption]
                
        metadata["path"] = image_path  # Record the image path
        metadata_records.append(metadata)
        
        # Periodically clean up GPU memory if processing many images
        if GPU_MEMORY_EFFICIENT and i > 0 and i % 50 == 0:
            torch.cuda.empty_cache()
            gc.collect()
    
    # Save embeddings as a numpy array
    embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
    np.save(embeddings_path, np.array(embeddings))
    
    # Convert metadata records to a DataFrame and save as CSV
    metadata_df = pd.DataFrame(metadata_records)
    metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
    metadata_df.to_csv(metadata_path, index=False)
    
    # Update session state with loaded data
    st.session_state.embeddings = np.array(embeddings)
    st.session_state.images_data = metadata_df
    st.session_state.database_built = True
    
    # Unload models to free up GPU memory
    if GPU_MEMORY_EFFICIENT:
        unload_clip_model()
        unload_blip_model()
    
    st.success("Database built and saved successfully!")
    return True

# Function to check if database exists
def database_exists(folder_path):
    db_embeddings_path = os.path.join(folder_path, DB_EMBEDDINGS_FILE)
    db_metadata_path = os.path.join(folder_path, DB_METADATA_FILE)
    return os.path.exists(db_embeddings_path) and os.path.exists(db_metadata_path)

# Function to load database
def load_database(db_folder):
    """
    Check if database files exist, and if so, load them.
    """
    embeddings_path = os.path.join(db_folder, DB_EMBEDDINGS_FILE)
    metadata_path = os.path.join(db_folder, DB_METADATA_FILE)
    if os.path.exists(embeddings_path) and os.path.exists(metadata_path):
        st.session_state.embeddings = np.load(embeddings_path)
        st.session_state.images_data = pd.read_csv(metadata_path)
        st.session_state.database_built = True
        st.success("Database loaded successfully!")
        return True
    return False

# Function to search for similar images
def search_similar_images(query_text, top_k=5):
    """
    Search for images similar to the query text.
    
    Args:
        query_text (str): The text query to search for.
        top_k (int): Number of top results to return.
        
    Returns:
        list: List of dictionaries containing search results.
    """
    try:
        # Load CLIP model if not already loaded
        if not hasattr(st, 'session_state') or 'clip_model' not in st.session_state or st.session_state.clip_model is None:
            model, preprocess = load_clip_model()
        else:
            model = st.session_state.clip_model
            preprocess = st.session_state.clip_preprocess
        
        device = st.session_state.device if hasattr(st, 'session_state') and 'device' in st.session_state else setup_device()
        
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
        st.error(f"Error searching by text: {e}")
        return []

def search_by_image(image_path, top_k=5):
    """
    Search for images similar to the query image.
    
    Args:
        image_path (str): Path to the query image.
        top_k (int): Number of top results to return.
        
    Returns:
        list: List of dictionaries containing search results.
    """
    try:
        # Load CLIP model if not already loaded
        if not hasattr(st, 'session_state') or 'clip_model' not in st.session_state or st.session_state.clip_model is None:
            model, preprocess = load_clip_model()
        else:
            model = st.session_state.clip_model
            preprocess = st.session_state.clip_preprocess
        
        device = st.session_state.device if hasattr(st, 'session_state') and 'device' in st.session_state else setup_device()
        
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
        st.error(f"Error searching by image: {e}")
        return []

# Function to get what the AI understands about an image
def get_image_understanding(image_path, top_k=10):
    """
    Get a textual understanding of an image by finding the most similar concepts.
    
    Args:
        image_path (str): Path to the image file.
        top_k (int): Number of top concepts to return.
        
    Returns:
        list: List of (concept, score) tuples.
    """
    from models.clip_model import get_image_understanding as clip_image_understanding
    
    # Get image understanding using CLIP
    understanding = clip_image_understanding(image_path, top_k)
    
    # Also get a caption using BLIP-2
    try:
        caption = generate_caption(image_path)
        understanding.insert(0, ("BLIP-2 Caption", caption))
    except Exception as e:
        logger.error(f"Error generating BLIP-2 caption: {e}")
    
    return understanding

# Dummy function for building the main database.
def build_main_database(image_folder):
    # Your actual logic to scan the folder, compute embeddings, extract metadata, and save the database goes here.
    # For the sake of demonstration, we just simulate success.
    st.write(f"Scanning for images in: {image_folder}")
    # Simulated processing… (in your actual code, load your CLIP model and scan/process images)
    st.success("Main database built successfully!")
    # You might store that database is built in session_state:
    st.session_state.database_built = True

# Dummy function for merging additional folder images.
def merge_additional_folder(primary_folder, new_folder):
    # Your logic to load the existing database, scan the new folder, process only new images,
    # and then merge them into the existing database should be placed here.
    st.write(f"Merging images from: {new_folder} into the database at: {primary_folder}")
    # Simulated processing…
    st.success("Additional images merged successfully!")

# 3. MAIN APP CODE - Only after all functions are defined
def main():
    """
    Main function to run the Streamlit app.
    """
    # Set page config
    st.set_page_config(
        page_title="Pixel Detective",
        page_icon="🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # === SIDEBAR ===
    with st.sidebar:
        st.title("🕵️‍♂️ Command Center")
        
        # Input for image folder
        primary_folder = st.text_input("📁 Image Folder Path", value=os.path.expanduser("~/Pictures"))
        
        # Button to build database
        if st.button("🧠 Launch the Brain Builder!"):
            if os.path.exists(primary_folder):
                with st.spinner("🔍 Scanning for images..."):
                    image_files = get_image_list(primary_folder)
                    if image_files:
                        st.session_state.image_files = image_files
                        st.session_state.total_images = len(image_files)
                        st.info(f"Found {len(image_files)} images. Building database...")
                        
                        # Load models for processing
                        if GPU_MEMORY_EFFICIENT and not st.session_state.models_loaded:
                            load_clip_model()
                            st.session_state.models_loaded = True
                        
                        # Build the database
                        build_database(primary_folder, image_files)
                        
                        # Unload models to free up memory if needed
                        if GPU_MEMORY_EFFICIENT:
                            unload_clip_model()
                            unload_blip_model()
                            st.session_state.models_loaded = False
                    else:
                        st.error("No images found in the specified folder.")
            else:
                st.error("Folder does not exist!")
        
        # Option to load existing database
        if st.button("📂 Load Existing Database"):
            if os.path.exists(primary_folder):
                with st.spinner("🔍 Loading database..."):
                    if database_exists(primary_folder):
                        load_database(primary_folder)
                    else:
                        st.error("No database found in the specified folder.")
            else:
                st.error("Folder does not exist!")
        
        # Add a section for merging additional folders
        if st.session_state.get("database_built", False):
            st.subheader("📊 Add More Images")
            new_folder = st.text_input("📁 Additional Image Folder", value="")
            
            if st.button("🔀 Merge New Images"):
                if os.path.exists(new_folder):
                    with st.spinner("🕵️‍♂️ Processing new images..."):
                        # Load models if needed
                        if GPU_MEMORY_EFFICIENT and not st.session_state.models_loaded:
                            load_clip_model()
                            st.session_state.models_loaded = True
                        
                        # Merge the new folder
                        from database.vector_db import append_images_to_database
                        append_images_to_database(primary_folder, new_folder)
                        
                        # Unload models to free up memory if needed
                        if GPU_MEMORY_EFFICIENT:
                            unload_clip_model()
                            unload_blip_model()
                            st.session_state.models_loaded = False
                else:
                    st.error("New folder does not exist!")
    
    # === MAIN CONTENT AREA ===
    if not st.session_state.get("database_built", False):
        # Show welcome message when no database is loaded yet
        st.markdown("""
        ## Welcome to Pixel Detective! 🕵️‍♂️
        
        The ultimate tool for searching through your image collection using AI.
        
        **To get started:**
        1. Enter your image folder path in the Command Center sidebar
        2. Click "Launch the Brain Builder!" to scan and index your images
        3. Once complete, you can search by text, upload similar images, or play the guessing game!
        
        *Your images will be analyzed by our AI assistant to create a searchable database.*
        """)
        
        # Maybe show a cool detective image
        st.image("https://i.imgur.com/3vvZbSh.png", caption="Ready to investigate your images!")
    else:
        # Database is built, show the three tabs for searching
        tab1, tab2, tab3 = st.tabs(["Text Search", "Image Search", "AI Guessing Game"])
        
        # Load models if needed for search operations
        if GPU_MEMORY_EFFICIENT and not st.session_state.models_loaded:
            with st.spinner("Loading AI models for search..."):
                load_clip_model()
                st.session_state.models_loaded = True
        
        with tab1:
            # Text search tab
            render_text_search_tab()
            
        with tab2:
            # Image upload tab
            render_image_upload_tab()
            
        with tab3:
            # Guessing game tab
            render_guessing_game_tab()

# Clean up function to be called when the app is closed
def on_shutdown():
    """Clean up resources when the app is closed."""
    if hasattr(st, 'session_state'):
        if 'clip_model' in st.session_state:
            unload_clip_model()
        if 'blip_model' in st.session_state:
            unload_blip_model()
    
    # Force garbage collection
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

# 4. START THE APP
if __name__ == "__main__":
    try:
        main()
    finally:
        on_shutdown() 