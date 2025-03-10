"""
Tab components for the Pixel Detective app.

This module contains the UI components for the different tabs in the application.
Fixed issues:
- Replaced deprecated 'use_column_width' with 'use_container_width'
- Restored metadata sidecar in search results
- Enhanced display of captions and tags
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

def render_text_search_tab():
    """
    Render the Text Search tab.
    """
    st.header("🔍 Find Images by Text")
    query = st.text_input("💭 What kind of image are you dreaming of?", key="search_query")
    num_results = st.slider("How many treasures to dig up?", min_value=1, max_value=20, value=5, key="num_results")
    
    date_filter = None
    if st.session_state.images_data is not None and 'DateTime' in st.session_state.images_data.columns:
        try:
            # Try to parse dates with a specific format first
            date_format = '%Y:%m:%d %H:%M:%S'  # Common EXIF date format
            dates = pd.to_datetime(st.session_state.images_data['DateTime'], 
                                  format=date_format, 
                                  errors='coerce').dropna()
            
            if dates.empty:
                # If that fails, try a more flexible approach
                dates = pd.to_datetime(st.session_state.images_data['DateTime'], 
                                      errors='coerce').dropna()
            
            if not dates.empty:
                min_date, max_date = dates.min(), dates.max()
                date_filter = st.slider("Filter by Date Taken", 
                                       min_value=min_date.date(), 
                                       max_value=max_date.date(),
                                       value=(min_date.date(), max_date.date()), 
                                       format="YYYY-MM-DD")
        except Exception as e:
            st.warning(f"Date filter not available: {e}")
    
    if query:
        results = search_similar_images(query, top_k=num_results)
        if results and date_filter is not None:
            try:
                date_format = '%Y:%m:%d %H:%M:%S'  # Common EXIF date format
                # Filter by date if date_filter is set
                filtered_results = []
                for result in results:
                    idx = result['index']
                    if 'DateTime' in st.session_state.images_data.columns:
                        date_str = st.session_state.images_data.iloc[idx]['DateTime']
                        if date_str and pd.notna(date_str):
                            try:
                                # Try the specific format first
                                date = pd.to_datetime(date_str, format=date_format, errors='coerce')
                                if pd.isna(date):
                                    # If that fails, try a more flexible approach
                                    date = pd.to_datetime(date_str, errors='coerce')
                                
                                if not pd.isna(date) and date_filter[0] <= date.date() <= date_filter[1]:
                                    filtered_results.append(result)
                            except:
                                # If date parsing fails, include the result anyway
                                filtered_results.append(result)
                        else:
                            # If no date, include the result
                            filtered_results.append(result)
                    else:
                        # If no DateTime column, include all results
                        filtered_results.append(result)
                results = filtered_results
            except Exception as e:
                st.warning(f"Error filtering by date: {e}")
        
        if results:
            st.subheader(f"Found {len(results)} treasures:")
            
            # Display results in a grid
            cols = st.columns(3)
            for i, result in enumerate(results):
                col_idx = i % 3
                with cols[col_idx]:
                    try:
                        img = Image.open(result['path'])
                        st.image(img, caption=f"Score: {result['score']:.2f}", use_container_width=True)
                        
                        # Display caption if available
                        if 'caption' in result:
                            st.markdown(f"**Caption:** {result['caption']}")
                        
                        # Display tags if available
                        if 'tags' in result and result['tags']:
                            if isinstance(result['tags'], list):
                                tags_str = ", ".join([str(tag) for tag in result['tags'] if tag]) if result['tags'] else "None"
                            else:
                                tags_str = str(result['tags'])
                            st.markdown(f"**Tags:** {tags_str}")
                        
                        # Display path (shortened)
                        path = result['path']
                        if len(path) > 30:
                            path = "..." + path[-30:]
                        st.markdown(f"**Path:** {path}")
                        
                        # Add metadata sidecar
                        with st.expander("View All Metadata"):
                            idx = result['index']
                            row = st.session_state.images_data.iloc[idx]
                            for key, value in row.items():
                                st.markdown(f"**{key}:** {value}")
                    except Exception as e:
                        st.error(f"Error displaying image: {e}")
        else:
            st.info("No treasures found matching your criteria.")
    else:
        st.info("Enter a search query to begin your treasure hunt!")

def render_image_upload_tab():
    """
    Render the Image Upload tab.
    """
    st.header("🖼️ Find Similar Images")
    uploaded_file = st.file_uploader("Upload an image to find its twins:", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption="Your Image", use_container_width=True)
            
            num_results = st.slider("How many similar images to find?", min_value=1, max_value=20, value=5)
            
            if st.button("Find Similar Images"):
                with st.spinner("Searching for twins..."):
                    results = search_similar_images_by_image(image, top_k=num_results)
                
                if results:
                    st.subheader(f"Found {len(results)} similar images:")
                    
                    # Display results in a grid
                    cols = st.columns(3)
                    for i, result in enumerate(results):
                        col_idx = i % 3
                        with cols[col_idx]:
                            try:
                                img = Image.open(result['path'])
                                st.image(img, caption=f"Score: {result['score']:.2f}", use_container_width=True)
                                
                                # Display caption if available
                                if 'caption' in result:
                                    st.markdown(f"**Caption:** {result['caption']}")
                                
                                # Display tags if available
                                if 'tags' in result and result['tags']:
                                    if isinstance(result['tags'], list):
                                        tags_str = ", ".join([str(tag) for tag in result['tags'] if tag]) if result['tags'] else "None"
                                    else:
                                        tags_str = str(result['tags'])
                                    st.markdown(f"**Tags:** {tags_str}")
                                
                                # Display path (shortened)
                                path = result['path']
                                if len(path) > 30:
                                    path = "..." + path[-30:]
                                st.markdown(f"**Path:** {path}")
                                
                                # Add metadata sidecar
                                with st.expander("View All Metadata"):
                                    idx = result['index']
                                    row = st.session_state.images_data.iloc[idx]
                                    for key, value in row.items():
                                        st.markdown(f"**{key}:** {value}")
                            except Exception as e:
                                st.error(f"Error displaying image: {e}")
                else:
                    st.info("No similar images found.")
        except Exception as e:
            st.error(f"Error processing uploaded image: {e}")

def render_guessing_game_tab():
    """
    Render the Guessing Game tab.
    """
    st.header("🎮 Guessing Game")
    st.write("Try to guess what the AI thinks this image represents!")
    game_image_container = st.empty()
    
    if st.button("Start New Game"):
        if st.session_state.get('image_files'):
            import random
            random_idx = random.randint(0, len(st.session_state.image_files) - 1)
            random_img_path = st.session_state.image_files[random_idx]
            st.session_state.game_img_path = str(random_img_path)
            st.session_state.game_img_idx = random_idx
            st.session_state.game_image_shown = True
            st.session_state.image_understanding = None
            try:
                img = Image.open(random_img_path)
                game_image_container.image(img, caption="What does this image represent?", use_container_width=True)
            except Exception as e:
                st.error(f"Error displaying game image: {e}")
        else:
            st.error("No images available. Please build the database first.")
    
    if 'game_img_path' in st.session_state and st.session_state.game_image_shown:
        try:
            img = Image.open(st.session_state.game_img_path)
            game_image_container.image(img, caption="What does this image represent?", use_container_width=True)
        except Exception as e:
            pass
        
        user_guess = st.text_input("Enter your guess:")
        if st.button("Check Guess") and user_guess:
            img_embedding = st.session_state.embeddings[st.session_state.game_img_idx]
            model = st.session_state.clip_model
            device = st.session_state.device
            with torch.no_grad():
                text_features = model.encode_text(clip.tokenize(user_guess).to(device))
                text_features /= text_features.norm(dim=-1, keepdim=True)
            similarity = np.dot(img_embedding, text_features.cpu().numpy().T).item()
            score = similarity * 100
            
            if score > 80:
                st.success(f"Wow, are you psychic? You nailed it with {score:.1f}% similarity!")
            elif score > 60:
                st.info(f"Not bad – {score:.1f}% similarity. Your guess is warming up, keep it quirky!")
            else:
                st.warning(f"Ouch, only {score:.1f}% similarity. Even a cat nap might yield better results!")
            
            if st.session_state.image_understanding is None:
                st.session_state.image_understanding = get_image_understanding(st.session_state.game_img_path)
            
            st.subheader("What the AI understands about this image:")
            for concept, score in st.session_state.image_understanding:
                st.write(f"- {concept}: {score*100:.1f}%")

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
            results.append({
                'path': img_path,
                'score': float(score),
                'index': int(idx)
            })
        
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
            results.append({
                'path': img_path,
                'score': float(score),
                'index': int(idx)
            })
        
        return results
    except Exception as e:
        st.error(f"Error processing uploaded image: {e}")
        return None 