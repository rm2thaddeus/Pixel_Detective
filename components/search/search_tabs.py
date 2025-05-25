"""
Tab components for the Pixel Detective app.

This module contains the UI components for the different tabs in the application.
Fixed issues:
- Replaced deprecated 'use_column_width' with 'use_container_width'
- Restored metadata sidecar in search results
- Enhanced display of captions and tags
- Fixed metadata button causing tab reset
- Changed metadata display to show below images instead of in an expander
"""
import streamlit as st
import torch
import clip
import pandas as pd
import numpy as np
from PIL import Image
import os
import random
from models.clip_model import load_clip_model, get_image_understanding
import tempfile
from utils.logger import logger
from utils.metadata_extractor import extract_metadata
from utils.lazy_session_state import LazySessionManager

# Callbacks to toggle metadata expansion without resetting tabs
def _toggle_text_metadata(metadata_key):
    st.session_state.text_metadata_expanded[metadata_key] = not st.session_state.text_metadata_expanded.get(metadata_key, False)

def _toggle_image_metadata(metadata_key):
    st.session_state.image_metadata_expanded[metadata_key] = not st.session_state.image_metadata_expanded.get(metadata_key, False)

def render_text_search_tab():
    """
    Renders the text search tab UI with lazy loading optimizations.
    """
    st.header("🔍 Text Search")
    st.write("Search for images using text descriptions.")
    
    # FIXED: Check if we're in a proper Streamlit context before accessing session state
    try:
        # Only access session state if we're in the main UI thread
        if not hasattr(st, 'session_state'):
            st.warning("Text search not available yet. Please complete the initial setup first.")
            return
            
        # Check if database is ready before trying to access it
        # More flexible check - look for any sign that database might be available
        database_indicators = [
            st.session_state.get('database_ready', False),
            st.session_state.get('database_built', False),
            st.session_state.get('images_data') is not None,
            hasattr(st.session_state, 'database_manager')
        ]
        
        if not any(database_indicators):
            st.info("🔄 Database not ready yet. Please complete the image processing first.")
            return
            
        # 🚀 LAZY LOADING: Initialize search state only when tab is accessed
        LazySessionManager.init_search_state()
        
        # Text search input
        query = st.text_input("Enter your search terms:", placeholder="e.g., sunset over mountains, cute dog, family picnic")
        
        # Number of results selector
        num_results = st.slider("Number of results:", min_value=1, max_value=20, value=5)
        
        # 🚀 LAZY LOADING: Initialize metadata state only when needed
        LazySessionManager.init_metadata_state()
    except Exception as e:
        from utils.logger import logger
        logger.error(f"Error in text search tab: {e}")
        st.warning("Text search temporarily unavailable. Please refresh the page.")
        return
    
    # Search button
    if st.button("🔍 Search Images"):
        if query:
            with st.spinner("Searching..."):
                # 🚀 LAZY LOADING: Get database manager only when searching
                db_manager = LazySessionManager.ensure_database_manager()
                
                # Search for images similar to the query text
                results = db_manager.search_similar_images(query, top_k=num_results)
                
                if results:
                    st.success(f"Found {len(results)} results!")
                    
                    # Display results
                    for i, result in enumerate(results):
                        score_percentage = result['score'] * 100
                        
                        # Create a container for each result
                        result_container = st.container()
                        
                        with result_container:
                            # Create columns for image and info
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                try:
                                    st.image(result['path'], caption=f"Score: {score_percentage:.1f}%", use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error loading image: {e}")
                                    st.write(f"Path: {result['path']}")
                            
                            with col2:
                                # File info
                                filename = os.path.basename(result['path'])
                                st.write(f"**Filename:** {filename}")
                                st.write(f"**Similarity:** {score_percentage:.1f}%")
                                
                                # Caption if available
                                if 'caption' in result and result['caption']:
                                    st.write(f"**Caption:** {result['caption']}")
                                
                                # Tags if available
                                if 'tags' in result and result['tags']:
                                    tags_str = ', '.join(result['tags']) if isinstance(result['tags'], list) else result['tags']
                                    st.write(f"**Tags:** {tags_str}")
                        
                        # Add a separator between results
                        st.divider()
                else:
                    st.warning("No results found. Try different search terms.")
        else:
            st.warning("Please enter a search query.")

def render_image_upload_tab():
    """
    Renders the image upload tab UI with lazy loading optimizations.
    """
    st.header("📸 Image Search")
    st.write("Upload an image to find similar images in your collection.")
    
    # FIXED: Check if we're in a proper Streamlit context before accessing session state
    try:
        # Only access session state if we're in the main UI thread
        if not hasattr(st, 'session_state'):
            st.warning("Image search not available yet. Please complete the initial setup first.")
            return
            
        # Check if database is ready before trying to access it
        # More flexible check - look for any sign that database might be available
        database_indicators = [
            st.session_state.get('database_ready', False),
            st.session_state.get('database_built', False),
            st.session_state.get('images_data') is not None,
            hasattr(st.session_state, 'database_manager')
        ]
        
        if not any(database_indicators):
            st.info("🔄 Database not ready yet. Please complete the image processing first.")
            return
            
        # 🚀 LAZY LOADING: Initialize search state only when tab is accessed
        LazySessionManager.init_search_state()
        
        # File uploader
        uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png', 'bmp', 'gif'])
    except Exception as e:
        from utils.logger import logger
        logger.error(f"Error in image upload tab: {e}")
        st.warning("Image search temporarily unavailable. Please refresh the page.")
        return
    
    if uploaded_file is not None:
        # Display the uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        # Number of results selector
        num_results = st.slider("Number of similar images:", min_value=1, max_value=20, value=5)
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Search button
        if st.button("🔍 Find Similar Images"):
            with st.spinner("Searching for similar images..."):
                # 🚀 LAZY LOADING: Get database manager only when searching
                db_manager = LazySessionManager.ensure_database_manager()
                
                # Search for images similar to the uploaded image
                results = db_manager.search_by_image(tmp_path, top_k=num_results)
                
                if results:
                    st.success(f"Found {len(results)} similar images!")
                    
                    # Display results
                    for i, result in enumerate(results):
                        score_percentage = result['score'] * 100
                        
                        # Create a container for each result
                        result_container = st.container()
                        
                        with result_container:
                            # Create columns for image and info
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                try:
                                    st.image(result['path'], caption=f"Score: {score_percentage:.1f}%", use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error loading image: {e}")
                                    st.write(f"Path: {result['path']}")
                            
                            with col2:
                                # File info
                                filename = os.path.basename(result['path'])
                                st.write(f"**Filename:** {filename}")
                                st.write(f"**Similarity:** {score_percentage:.1f}%")
                                
                                # Caption if available
                                if 'caption' in result and result['caption']:
                                    st.write(f"**Caption:** {result['caption']}")
                                
                                # Tags if available
                                if 'tags' in result and result['tags']:
                                    tags_str = ', '.join(result['tags']) if isinstance(result['tags'], list) else result['tags']
                                    st.write(f"**Tags:** {tags_str}")
                        
                        # Add a separator between results
                        st.divider()
                else:
                    st.warning("No similar images found.")
        
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass

def render_guessing_game_tab():
    """
    Renders the AI guessing game tab UI with lazy loading optimizations.
    """
    st.header("🎮 AI Guessing Game")
    st.write("Test how well you can guess what the AI sees in your images!")
    
    # Only show the game if a database is loaded
    if not st.session_state.get("database_built", False):
        st.warning("Please build or load a database first to play the guessing game.")
        return
    
    # 🚀 LAZY LOADING: Initialize game state only when tab is accessed
    LazySessionManager.init_game_state()
    
    # Get a random image if not already selected
    if not st.session_state.get("game_image_shown", False):
        if st.button("🎲 Select Random Image"):
            # Get a random image from the database
            num_images = len(st.session_state.images_data)
            random_idx = random.randint(0, num_images - 1)
            random_image = st.session_state.images_data.iloc[random_idx]
            
            # Store the selected image in session state
            st.session_state.game_image = random_image
            st.session_state.game_image_shown = True
            st.session_state.game_understanding = None
            
            # Force a rerun to update the UI
            st.rerun()
    
    # Show the game if an image is selected
    if st.session_state.get("game_image_shown", False):
        game_image = st.session_state.game_image
        image_path = game_image['path']
        
        # Display the image
        col1, col2 = st.columns([2, 1])
        
        with col1:
            try:
                st.image(image_path, caption="What do you think the AI sees in this image?", use_container_width=True)
            except Exception as e:
                st.error(f"Error loading image: {e}")
                st.write(f"Path: {image_path}")
        
        with col2:
            # User guess input
            user_guess = st.text_area("Your guess:", placeholder="What do you think this image contains?")
            
            # Button to reveal what the AI sees
            if st.button("👁️ Reveal What AI Sees"):
                with st.spinner("Analyzing the image..."):
                    # 🚀 LAZY LOADING: Get the model manager only when needed for AI analysis
                    model_manager = LazySessionManager.ensure_model_manager()
                    
                    # Get image understanding if not already cached
                    if st.session_state.get("game_understanding") is None:
                        understanding = model_manager.get_image_understanding(image_path)
                        st.session_state.game_understanding = understanding
                    else:
                        understanding = st.session_state.game_understanding
                    
                    # Display the AI's understanding
                    st.subheader("🤖 AI's Understanding:")
                    
                    # First show the BLIP caption if available
                    for concept, score in understanding:
                        if concept == "BLIP Caption":
                            st.markdown(f"**{concept}:** {score}")
                            break
                    
                    # Then show the top concepts in a more visually organized way
                    st.markdown("**Top concepts identified:**")
                    
                    # Create 3 columns for better organization of concepts
                    concept_cols = st.columns(3)
                    
                    # Filter out BLIP Caption which we've already displayed
                    concepts = [item for item in understanding if item[0] != "BLIP Caption"]
                    
                    # Distribute concepts across columns
                    items_per_column = len(concepts) // 3 + (1 if len(concepts) % 3 > 0 else 0)
                    
                    for i, (concept, score) in enumerate(concepts):
                        col_idx = i // items_per_column
                        if col_idx < 3:  # Safety check
                            with concept_cols[col_idx]:
                                confidence = score * 100 if isinstance(score, (int, float)) else "N/A"
                                if isinstance(confidence, (int, float)):
                                    st.write(f"• {concept} ({confidence:.1f}%)")
                                else:
                                    st.write(f"• {concept}")
            
            # Show a button to try another image
            if st.button("🔄 Try Another Image"):
                st.session_state.game_image_shown = False
                st.session_state.game_understanding = None
                st.rerun()

def render_duplicates_tab():
    """
    Renders the Duplicate Detection tab UI with lazy loading optimizations.
    """
    st.header("🧑‍🤝‍🧑 Duplicate Detection (Post-Embedding)")
    st.write("Find near-duplicate images using vector similarity in the embedding space.")

    if not st.session_state.get("database_built", False):
        st.warning("Please build or load a database first.")
        return

    # 🚀 LAZY LOADING: Initialize search state only when tab is accessed
    LazySessionManager.init_search_state()

    if st.button("🔍 Find Duplicates"):  # Button to trigger detection
        with st.spinner("Searching for duplicate images..."):
            # 🚀 LAZY LOADING: Get managers only when needed for duplicate detection
            db_manager = LazySessionManager.ensure_database_manager()
            qdrant_db = st.session_state.qdrant_db
            duplicates = db_manager.find_duplicate_images(qdrant_db)
            # Store results using session state (this is legitimate for storing results)
            st.session_state.duplicate_results = duplicates
            st.success(f"Found {len(duplicates)} duplicate pairs above similarity 0.98.")

    duplicates = st.session_state.get('duplicate_results', [])
    if duplicates:
        st.write(f"### Duplicate Pairs (showing up to 100):")
        for i, dup in enumerate(duplicates[:100]):
            col1, col2 = st.columns([1, 1])
            with col1:
                st.image(dup['image'], caption=f"Image 1", use_container_width=True)
                st.caption(dup['image'])
            with col2:
                st.image(dup['duplicate'], caption=f"Image 2", use_container_width=True)
                st.caption(dup['duplicate'])
            st.markdown(f"**Cosine Similarity:** {dup['score']:.4f}")
            st.divider()
    elif 'duplicate_results' in st.session_state:
        st.info("No duplicate pairs found above the threshold.")
