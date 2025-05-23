"""
Sidebar components for the Pixel Detective app with lazy loading optimizations.
"""
import os
import torch
import streamlit as st
from utils.logger import logger
from utils.lazy_session_state import LazySessionManager
from config import DEFAULT_IMAGES_PATH
from database.qdrant_connector import QdrantDB

def render_sidebar():
    """
    Render the sidebar components with lazy loading and performance optimizations.
    
    Returns:
        dict: A dictionary with keys for 'image_folder' (current DB folder) and 'new_folder' (to be merged), if any.
    """
    st.sidebar.header("✨ Command Center ✨")
    
    # Display colored device status with fun names
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        st.sidebar.markdown(f"<h3 style='color: green;'> Super Graphix Cardz Activated! 🔥</h3>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p>Your trusty sidekick today: <b>{gpu_name}</b> - ready to crunch pixels!</p>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h3 style='color: orange;'>🐢 CPU Mode (Slow & Steady) 🐢</h3>", unsafe_allow_html=True)
        st.sidebar.markdown("<p>No Graphix Cardz detected. We'll do our best with brain power alone!</p>", unsafe_allow_html=True)
    
    # Current folder for the existing database
    if 'image_folder' not in st.session_state:
        st.session_state.image_folder = DEFAULT_IMAGES_PATH

    current_folder = st.sidebar.text_input("📁 Database folder", value=st.session_state.image_folder, key="db_folder").strip().strip('"')
    st.session_state.image_folder = current_folder
    
    # 🚀 LAZY LOADING: Get db_manager only when needed
    db_manager = LazySessionManager.ensure_database_manager()
    
    # Check and indicate if a database exists here
    if os.path.exists(current_folder):
        if db_manager.database_exists(current_folder):
            st.sidebar.success("🧠 Database exists in this folder!")
        else:
            st.sidebar.info("No database found in this folder.")
    else:
        st.sidebar.error("Folder does not exist!")
    
    # Button to Build/Load the database if it doesn't exist
    if st.sidebar.button("🚀 Build/Load Database"):
        if os.path.exists(current_folder):
            # 🚀 LAZY LOADING: Initialize search state only when building database
            LazySessionManager.init_search_state()
            
            # Fun loading messages
            loading_messages = [
                "🕵️‍♂️ Deploying pixel detectives...",
                "🧠 Training the AI to recognize your cat photos...",
                "🔍 Examining each pixel with a magnifying glass...",
                "🤖 Teaching robots to appreciate your photography skills...",
                "🎨 Extracting colors, shapes, and secret messages...",
                "📊 Converting visual beauty into boring numbers...",
                "🧩 Solving the puzzle of image understanding...",
                "🏃‍♂️ Making electrons run really fast...",
                "🌈 Finding rainbows in your image collection...",
                "🚀 Preparing for lightspeed image searching..."
            ]
            
            # Create a progress placeholder in the sidebar
            progress_placeholder = st.sidebar.empty()
            progress_bar = st.sidebar.progress(0)
            message_placeholder = st.sidebar.empty()
            
            # Display fun loading message
            import random
            message_placeholder.info(random.choice(loading_messages))
            
            # Update session state to track progress
            if 'total_images' not in st.session_state:
                st.session_state.total_images = 0
            if 'current_image_index' not in st.session_state:
                st.session_state.current_image_index = 0
            
            # Load the database if it exists, or build it if it doesn't
            if db_manager.database_exists(current_folder):
                progress_placeholder.info("Loading existing database...")
                if db_manager.load_database(current_folder):
                    progress_placeholder.success("Database loaded successfully!")
                    progress_bar.progress(100)
                    message_placeholder.success("Ready to search! 🚀")
                    # Initialize QdrantDB after loading DB
                    st.session_state.qdrant_db = QdrantDB(collection_name="image_collection")
                else:
                    progress_placeholder.error("Failed to load database.")
            else:
                # Get the list of images in the folder
                progress_placeholder.info("Scanning folder for images...")
                image_files = db_manager.get_image_list(current_folder)
                
                if image_files:
                    st.session_state.total_images = len(image_files)
                    progress_placeholder.info(f"Found {len(image_files)} images. Building database...")
                    try:
                        with st.spinner("Building database..."):
                            success = db_manager.build_database(current_folder, image_files)
                        if success:
                            progress_placeholder.success("Database built successfully!")
                            progress_bar.progress(100)
                            message_placeholder.success("Ready to search! 🚀")
                            # Initialize QdrantDB after building DB
                            st.session_state.qdrant_db = QdrantDB(collection_name="image_collection")
                        else:
                            progress_placeholder.error("Failed to build database.")
                    except Exception as e:
                        progress_placeholder.error(f"Error building database: {e}")
                        logger.error(f"Error building database: {e}")
                else:
                    progress_placeholder.error("No images found in the folder.")
        else:
            st.sidebar.error("Invalid folder path.")
    
    # Now add an option to merge a new folder into the existing database
    new_folder = st.sidebar.text_input("📁 New folder to merge", value="", key="new_folder").strip().strip('"')
    
    if st.sidebar.button("🔗 Merge New Folder") and new_folder:
        if os.path.exists(new_folder):
            # Create progress placeholders for merge operation
            merge_placeholder = st.sidebar.empty()
            merge_progress = st.sidebar.progress(0)
            merge_message = st.sidebar.empty()
            
            merge_placeholder.info("Scanning new folder for images...")
            
            # Get new images that aren't already in the current database
            existing_images = set(db_manager.get_image_list(current_folder))
            new_images = [img for img in db_manager.get_image_list(new_folder) if img not in existing_images]
            
            if new_images:
                st.session_state.total_new_images = len(new_images)
                st.session_state.current_new_image_index = 0

                try:
                    # Merge new images using existing build_database (caching will skip already processed images)
                    merge_placeholder.info(f"Merging {len(new_images)} new images into database...")
                    with st.spinner(f"Merging {len(new_images)} images..."):
                        combined_images = db_manager.get_image_list(current_folder) + new_images
                        success = db_manager.build_database(current_folder, combined_images)
                    if success:
                        merge_progress.progress(100)
                        merge_placeholder.success(f"Successfully merged {len(new_images)} new images!")
                        merge_message.success("Database ready for searching! 🎉")
                    else:
                        merge_placeholder.error("Error merging new images.")
                except Exception as e:
                    merge_placeholder.error(f"Error merging folders: {e}")
                    logger.error(f"Error merging folders: {e}")
            else:
                merge_placeholder.warning("No new images found to merge.")
        else:
            st.sidebar.error("New folder does not exist!")
    
    # 🚀 PERFORMANCE OPTIMIZATION: Show model status with lazy loading awareness
    model_manager = st.session_state.get('model_manager')
    if model_manager:
        # Show which model is currently loaded (if any)
        if hasattr(model_manager, '_current_model') and model_manager._current_model:
            current_model = model_manager._current_model
            st.sidebar.success(f"✅ {current_model.upper()} model is loaded and ready")
            
            # Show memory status if available
            if hasattr(model_manager, 'get_memory_status'):
                try:
                    memory_status = model_manager.get_memory_status()
                    if memory_status["available"]:
                        usage_percent = memory_status.get('usage_percent', 0)
                        if usage_percent > 80:
                            st.sidebar.warning(f"⚠️ High GPU memory usage: {usage_percent:.1f}%")
                        else:
                            st.sidebar.info(f"💾 GPU memory usage: {usage_percent:.1f}%")
                except Exception as e:
                    logger.error(f"Error getting memory status: {e}")
        else:
            st.sidebar.info("⚡ Models ready for lazy loading (0 MB baseline)")
            
        device = model_manager.device
        device_type = "GPU" if device.type == "cuda" else "CPU"
        st.sidebar.info(f"Models will run on: {device_type}")
    else:
        st.sidebar.info("⚡ Models will load when first needed")

    # Enable incremental indexing
    watch_enabled = st.sidebar.checkbox("📡 Enable Incremental Indexing", value=False, key="enable_watch")
    if watch_enabled:
        if 'indexer_observer' not in st.session_state:
            from utils.embedding_cache import get_cache
            from utils.incremental_indexer import start_incremental_indexer

            cache = get_cache()
            folder = current_folder
            model_mgr = LazySessionManager.ensure_model_manager()
            observer = start_incremental_indexer(folder, db_manager, cache, model_mgr)
            st.session_state.indexer_observer = observer
            st.sidebar.success("Incremental indexer started.")
    else:
        if 'indexer_observer' in st.session_state:
            st.session_state.indexer_observer.stop()
            del st.session_state.indexer_observer
            st.sidebar.info("Incremental indexer stopped.")

    return current_folder

def render_sidebar_old():
    """
    Render the sidebar components.
    
    Returns:
        str: The selected image folder path.
    """
    st.sidebar.header("✨ Command Center ✨")
    
    # Display colored device status with fun names
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        st.sidebar.markdown(f"<h3 style='color: green;'> Super Graphix Cardz Activated! 🔥</h3>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p>Your trusty sidekick today: <b>{gpu_name}</b> - ready to crunch pixels!</p>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h3 style='color: orange;'>🐢 CPU Mode (Slow & Steady) 🐢</h3>", unsafe_allow_html=True)
        st.sidebar.markdown("<p>No Graphix Cardz detected. We'll do our best with brain power alone!</p>", unsafe_allow_html=True)
    
    # Image folder input with fun label
    if 'image_folder' not in st.session_state:
        st.session_state.image_folder = DEFAULT_IMAGES_PATH

    # Strip quotes and whitespace from the input path
    folder_input = st.sidebar.text_input(
        "📁 Where are your amazing pics hiding?", 
        value=st.session_state.image_folder, 
        key="folder_path"
    ).strip().strip('"')

    # Update the folder path when the text input changes
    if folder_input != st.session_state.image_folder:
        st.session_state.image_folder = folder_input

    image_folder = st.session_state.image_folder
    
    # Check if database exists with fun message
    if os.path.exists(image_folder):
        if database_exists(image_folder):
            st.sidebar.success("🧠 Brain cells found! This folder already has a database!")
        else:
            st.sidebar.info("🔍 No database here yet. Let's make some magic happen!")
    
    # Button to build/load database with fun text
    if st.sidebar.button("🚀 Launch the Brain Builder!"):
        if os.path.exists(image_folder):
            # Load CLIP model first
            load_clip_model()
            
            # Check if database exists and load it, or build new one
            if database_exists(image_folder):
                st.sidebar.info("📚 Loading existing brain cells... stand by!")
                load_database(image_folder)
            else:
                st.sidebar.info("🏗️ Building new neural pathways... this might take a bit!")
                st.session_state.database_built = False
                st.session_state.db_building_complete = False
                st.session_state.current_image_index = 0
                
                # Get the list of images and build the database
                image_list = get_image_list(image_folder)
                if image_list:
                    build_database(image_folder, image_list)
                else:
                    st.sidebar.error("No images found in the specified folder.")
        else:
            st.sidebar.error(f"🤔 Hmm, can't find that folder. Did the computer gremlins take it?")
    
    # Show model information at the bottom of sidebar
    if 'model_manager' in st.session_state and st.session_state.model_manager.clip_model is not None:
        st.sidebar.success("✅ CLIP model is loaded and ready")
        device = st.session_state.model_manager.device
        device_type = "GPU" if device.type == "cuda" else "CPU"
        st.sidebar.info(f"Model is running on: {device_type}")
    else:
        st.sidebar.warning("CLIP model is not loaded yet")
    
    return image_folder 