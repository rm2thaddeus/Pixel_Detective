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

# Callbacks to toggle metadata expansion without resetting tabs
def _toggle_text_metadata(metadata_key):
    st.session_state.text_metadata_expanded[metadata_key] = not st.session_state.text_metadata_expanded.get(metadata_key, False)

def _toggle_image_metadata(metadata_key):
    st.session_state.image_metadata_expanded[metadata_key] = not st.session_state.image_metadata_expanded.get(metadata_key, False)

def render_text_search_tab():
    """
    Renders the text search tab UI.
    """
    st.header("🔍 Text Search")
    st.write("Search for images using text descriptions.")
    
    # Text search input
    query = st.text_input("Enter your search terms:", placeholder="e.g., sunset over mountains, cute dog, family picnic")
    
    # Number of results selector
    num_results = st.slider("Number of results:", min_value=1, max_value=20, value=5)
    
    # Initialize metadata_expanded in session state if it doesn't exist
    if 'text_metadata_expanded' not in st.session_state:
        st.session_state.text_metadata_expanded = {}
    
    # Search button
    if st.button("🔍 Search Images"):
        if query:
            with st.spinner("Searching..."):
                # Get database manager from session state
                db_manager = st.session_state.db_manager
                
                # Search for images similar to the query text
                results = db_manager.search_similar_images(query, top_k=num_results)
                
                if results:
                    st.success(f"Found {len(results)} images matching your query!")
                    
                    # Display results
                    for i, result in enumerate(results):
                        score_percentage = result['score'] * 100
                        
                        # Create a container for each result
                        result_container = st.container()
                        with result_container:
                            # Create columns for each result
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                try:
                                    st.image(result['path'], use_container_width=True)
                                except Exception as e:
                                    st.error(f"Could not load image: {e}")
                            
                            with col2:
                                st.markdown(f"**Match score:** {score_percentage:.1f}%")
                                
                                # Display AI-generated description if available
                                if 'ai_description' in result:
                                    st.markdown(f"**AI Description:** {result['ai_description']}")
                                elif 'caption' in result:
                                    st.markdown(f"**Caption:** {result['caption']}")
                                
                                # Display original caption if available
                                if 'original_caption' in result:
                                    st.markdown(f"**Original Caption:** {result['original_caption']}")
                                    
                                # Display keywords/tags
                                if 'Keywords' in result:
                                    if isinstance(result['Keywords'], list):
                                        keywords = ", ".join(result['Keywords'])
                                    else:
                                        keywords = result['Keywords']
                                    st.markdown(f"**Keywords:** {keywords}")
                                
                                st.markdown(f"**Path:** `{result['path']}`")
                                
                                # Create a unique key for this result
                                metadata_key = f"text_metadata_{i}_{result.get('index', i)}"
                                
                                # Add a "Show Metadata" button with a unique key
                                st.button(
                                    "🔍 Show Metadata",
                                    key=f"metadata_btn_{i}",
                                    help="Display all metadata for this image",
                                    on_click=_toggle_text_metadata,
                                    args=(metadata_key,)
                                )
                            
                            # Check if metadata should be displayed for this result
                            if st.session_state.text_metadata_expanded.get(metadata_key, False):
                                # Get all metadata for the image from the database
                                if 'index' in result:
                                    metadata = st.session_state.images_data.iloc[result['index']].to_dict()
                                    
                                    # Display metadata in a clean format below the image and basic info
                                    st.write("---")
                                    st.write("### Complete Metadata")
                                    
                                    # Filter out very large fields and non-informative ones
                                    exclude_keys = ['embeddings', 'path', 'filename']
                                    filtered_metadata = {k: v for k, v in metadata.items() 
                                                      if k not in exclude_keys and v is not None and str(v) != 'nan'}
                                    
                                    # Create a clean display
                                    # Use 3 columns for better space utilization
                                    metadata_cols = st.columns(3)
                                    
                                    # Sort metadata keys for consistent display
                                    sorted_keys = sorted(filtered_metadata.keys())
                                    
                                    # Distribute metadata across columns
                                    items_per_column = len(sorted_keys) // 3 + (1 if len(sorted_keys) % 3 > 0 else 0)
                                    
                                    for col_idx, col in enumerate(metadata_cols):
                                        with col:
                                            start_idx = col_idx * items_per_column
                                            end_idx = min((col_idx + 1) * items_per_column, len(sorted_keys))
                                            
                                            for key in sorted_keys[start_idx:end_idx]:
                                                value = filtered_metadata[key]
                                                
                                                # Handle different types of values
                                                if isinstance(value, list):
                                                    value_str = ", ".join(str(v) for v in value)
                                                else:
                                                    value_str = str(value)
                                                
                                                # Make the display more readable
                                                if len(value_str) > 100:
                                                    value_str = value_str[:100] + "..."
                                                
                                                # Display the key-value pair
                                                st.markdown(f"**{key}:** {value_str}")
                        
                        st.divider()
                else:
                    st.warning("No images found matching your query. Try different search terms.")
        else:
            st.warning("Please enter a search query.")

def render_image_upload_tab():
    """
    Renders the image upload tab UI for searching by image.
    """
    st.header("🖼️ Image Search")
    st.write("Upload an image to find similar images in your collection.")
    
    # Image upload
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    
    # Number of results selector
    num_results = st.slider("Number of results:", min_value=1, max_value=20, value=5, key="image_search_slider")
    
    # Initialize metadata_expanded in session state if it doesn't exist
    if 'image_metadata_expanded' not in st.session_state:
        st.session_state.image_metadata_expanded = {}
    
    if uploaded_file is not None:
        # Display the uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Search button
        if st.button("🔍 Find Similar Images"):
            with st.spinner("Searching for similar images..."):
                # Get database manager from session state
                db_manager = st.session_state.db_manager
                
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
                            # Create columns for each result
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                try:
                                    st.image(result['path'], use_container_width=True)
                                except Exception as e:
                                    st.error(f"Could not load image: {e}")
                            
                            with col2:
                                st.markdown(f"**Match score:** {score_percentage:.1f}%")
                                
                                # Display AI-generated description if available
                                if 'ai_description' in result:
                                    st.markdown(f"**AI Description:** {result['ai_description']}")
                                elif 'caption' in result:
                                    st.markdown(f"**Caption:** {result['caption']}")
                                
                                # Display original caption if available
                                if 'original_caption' in result:
                                    st.markdown(f"**Original Caption:** {result['original_caption']}")
                                    
                                # Display keywords/tags
                                if 'Keywords' in result:
                                    if isinstance(result['Keywords'], list):
                                        keywords = ", ".join(result['Keywords'])
                                    else:
                                        keywords = result['Keywords']
                                    st.markdown(f"**Keywords:** {keywords}")
                                
                                st.markdown(f"**Path:** `{result['path']}`")
                                
                                # Create a unique key for this result
                                metadata_key = f"image_metadata_{i}_{result.get('index', i)}"
                                
                                # Add a "Show Metadata" button with a unique key
                                st.button(
                                    "🔍 Show Metadata",
                                    key=f"img_metadata_btn_{i}",
                                    help="Display all metadata for this image",
                                    on_click=_toggle_image_metadata,
                                    args=(metadata_key,)
                                )
                            
                            # Check if metadata should be displayed for this result
                            if st.session_state.image_metadata_expanded.get(metadata_key, False):
                                # Get all metadata for the image from the database
                                if 'index' in result:
                                    metadata = st.session_state.images_data.iloc[result['index']].to_dict()
                                    
                                    # Display metadata in a clean format below the image and basic info
                                    st.write("---")
                                    st.write("### Complete Metadata")
                                    
                                    # Filter out very large fields and non-informative ones
                                    exclude_keys = ['embeddings', 'path', 'filename']
                                    filtered_metadata = {k: v for k, v in metadata.items() 
                                                      if k not in exclude_keys and v is not None and str(v) != 'nan'}
                                    
                                    # Create a clean display
                                    # Use 3 columns for better space utilization
                                    metadata_cols = st.columns(3)
                                    
                                    # Sort metadata keys for consistent display
                                    sorted_keys = sorted(filtered_metadata.keys())
                                    
                                    # Distribute metadata across columns
                                    items_per_column = len(sorted_keys) // 3 + (1 if len(sorted_keys) % 3 > 0 else 0)
                                    
                                    for col_idx, col in enumerate(metadata_cols):
                                        with col:
                                            start_idx = col_idx * items_per_column
                                            end_idx = min((col_idx + 1) * items_per_column, len(sorted_keys))
                                            
                                            for key in sorted_keys[start_idx:end_idx]:
                                                value = filtered_metadata[key]
                                                
                                                # Handle different types of values
                                                if isinstance(value, list):
                                                    value_str = ", ".join(str(v) for v in value)
                                                else:
                                                    value_str = str(value)
                                                
                                                # Make the display more readable
                                                if len(value_str) > 100:
                                                    value_str = value_str[:100] + "..."
                                                
                                                # Display the key-value pair
                                                st.markdown(f"**{key}:** {value_str}")
                        
                        st.divider()
                else:
                    st.warning("No similar images found in your collection.")
        
        # Clean up the temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass

def render_guessing_game_tab():
    """
    Renders the AI guessing game tab UI.
    """
    st.header("🎮 AI Guessing Game")
    st.write("Test how well you can guess what the AI sees in your images!")
    
    # Only show the game if a database is loaded
    if not st.session_state.get("database_built", False):
        st.warning("Please build or load a database first to play the guessing game.")
        return
    
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
            st.experimental_rerun()
    
    # Show the selected image and game interface
    if st.session_state.get("game_image_shown", False):
        # Create a container for the game content
        game_container = st.container()
        with game_container:
            # Display the random image
            random_image = st.session_state.game_image
            image_path = random_image['path']
            
            try:
                st.image(image_path, caption="What do you think the AI sees in this image?", use_container_width=True)
            except Exception as e:
                st.error(f"Could not load image: {e}")
                st.session_state.game_image_shown = False
                return
            
            # Input for user's guess
            user_guess = st.text_input("What do you think this image contains? Be specific:", key="game_guess")
            
            # Button to reveal what the AI sees
            if st.button("👁️ Reveal What AI Sees"):
                with st.spinner("Analyzing the image..."):
                    # Get the model manager from session state
                    model_manager = st.session_state.model_manager
                    
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
                    
                    for col_idx, col in enumerate(concept_cols):
                        with col:
                            start_idx = col_idx * items_per_column
                            end_idx = min((col_idx + 1) * items_per_column, len(concepts))
                            
                            for concept, score in concepts[start_idx:end_idx]:
                                score_percentage = score * 100 if isinstance(score, float) else 0
                                st.markdown(f"- **{concept}:** {score_percentage:.1f}%")
            
            # Button to start a new game
            if st.button("🔄 New Image"):
                st.session_state.game_image_shown = False
                st.session_state.game_understanding = None
                st.experimental_rerun()

def search_similar_images(query_text, top_k=5):
    """
    Search for images similar to the query text.
    
    Args:
        query_text (str): The query text.
        top_k (int): Number of results to return.
        
    Returns:
        list: List of dictionaries containing the results.
    """
    try:
        if not st.session_state.database_built:
            st.error("Database not built yet. Please build the database first.")
            return None
        
        model = st.session_state.clip_model
        device = st.session_state.device
        
        # Encode the query text
        with torch.no_grad():
            text_features = model.encode_text(clip.tokenize(query_text).to(device))
            text_features /= text_features.norm(dim=-1, keepdim=True)
        
        # Compute similarity scores
        text_features_np = text_features.cpu().numpy()
        similarities = np.dot(st.session_state.embeddings, text_features_np.T).squeeze()
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        top_scores = similarities[top_indices]
        
        results = []
        for idx, score in zip(top_indices, top_scores):
            img_path = st.session_state.images_data.iloc[idx]['path']
            result = {
                'path': img_path,
                'score': float(score),
                'index': int(idx)
            }
            
            # Add additional metadata from the database if available
            metadata = st.session_state.images_data.iloc[idx].to_dict()
            
            # Add caption if available
            if 'caption' in metadata and metadata['caption'] is not None and str(metadata['caption']) != 'nan':
                result['caption'] = metadata['caption']
            
            # Add keywords if available
            if 'Keywords' in metadata and metadata['Keywords'] is not None and str(metadata['Keywords']) != 'nan':
                result['Keywords'] = metadata['Keywords']
            
            # Add original caption if available
            if 'original_caption' in metadata and metadata['original_caption'] is not None and str(metadata['original_caption']) != 'nan':
                result['original_caption'] = metadata['original_caption']
                
            # Add AI description if available
            if 'ai_description' in metadata and metadata['ai_description'] is not None and str(metadata['ai_description']) != 'nan':
                result['ai_description'] = metadata['ai_description']
            
            results.append(result)
        
        return results
    except Exception as e:
        st.error(f"Error searching images: {e}")
        return None

def search_similar_images_by_image(uploaded_image, top_k=5):
    """
    Search for images similar to the uploaded image.
    
    Args:
        uploaded_image (PIL.Image): The uploaded image.
        top_k (int): Number of results to return.
        
    Returns:
        list: List of dictionaries containing the results.
    """
    if not st.session_state.database_built:
        st.error("Database not built yet. Please build the database first.")
        return None
    
    model = st.session_state.clip_model
    preprocess = st.session_state.clip_preprocess
    device = st.session_state.device
    
    # Preprocess and encode the uploaded image
    try:
        image = preprocess(uploaded_image).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = model.encode_image(image)
        
        image_features /= image_features.norm(dim=-1, keepdim=True)
        image_features_np = image_features.cpu().numpy()
        
        # Compute similarity scores
        similarities = np.dot(st.session_state.embeddings, image_features_np.T).squeeze()
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        top_scores = similarities[top_indices]
        
        results = []
        for idx, score in zip(top_indices, top_scores):
            img_path = st.session_state.images_data.iloc[idx]['path']
            result = {
                'path': img_path,
                'score': float(score),
                'index': int(idx)
            }
            
            # Add additional metadata from the database if available
            metadata = st.session_state.images_data.iloc[idx].to_dict()
            
            # Add caption if available
            if 'caption' in metadata and metadata['caption'] is not None and str(metadata['caption']) != 'nan':
                result['caption'] = metadata['caption']
            
            # Add keywords if available
            if 'Keywords' in metadata and metadata['Keywords'] is not None and str(metadata['Keywords']) != 'nan':
                result['Keywords'] = metadata['Keywords']
            
            # Add original caption if available
            if 'original_caption' in metadata and metadata['original_caption'] is not None and str(metadata['original_caption']) != 'nan':
                result['original_caption'] = metadata['original_caption']
                
            # Add AI description if available
            if 'ai_description' in metadata and metadata['ai_description'] is not None and str(metadata['ai_description']) != 'nan':
                result['ai_description'] = metadata['ai_description']
            
            results.append(result)
        
        return results
    except Exception as e:
        st.error(f"Error processing uploaded image: {e}")
        return None 