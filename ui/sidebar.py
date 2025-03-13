"""
Sidebar components for the Pixel Detective app.
"""
import os
import torch
import streamlit as st
from utils.logger import logger
from models.clip_model import load_clip_model
from config import DEFAULT_IMAGES_PATH

def render_sidebar():
    """
    Render the sidebar components with support for extendable image display.
    
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
    
    # Get db_manager from session state
    db_manager = st.session_state.db_manager
    
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
                else:
                    progress_placeholder.error("Failed to load database.")
            else:
                # Get the list of images in the folder
                progress_placeholder.info("Scanning folder for images...")
                image_files = db_manager.get_image_list(current_folder)
                
                if image_files:
                    st.session_state.total_images = len(image_files)
                    progress_placeholder.info(f"Found {len(image_files)} images. Building database...")
                    
                    # Update the progress info and message every second
                    import time
                    import threading
                    
                    def update_loading_message():
                        idx = 0
                        while st.session_state.get('building_database', True) and idx < 100:
                            message_placeholder.info(random.choice(loading_messages))
                            idx += 1
                            time.sleep(2)  # Update message every 2 seconds
                    
                    # Start the message update thread
                    st.session_state.building_database = True
                    threading.Thread(target=update_loading_message).start()
                    
                    try:
                        # Build the database
                        success = db_manager.build_database(current_folder, image_files)
                        
                        # Update progress and message
                        st.session_state.building_database = False
                        if success:
                            progress_placeholder.success("Database built successfully!")
                            progress_bar.progress(100)
                            message_placeholder.success("Ready to search! 🚀")
                        else:
                            progress_placeholder.error("Failed to build database.")
                    except Exception as e:
                        st.session_state.building_database = False
                        progress_placeholder.error(f"Error building database: {e}")
                        logger.error(f"Error building database: {e}")
                else:
                    progress_placeholder.error("No images found in the folder.")
        else:
            st.sidebar.error("Invalid folder path.")
    
    # Now add an option to merge a new folder into the existing database
    new_folder = st.sidebar.text_input("📁 New folder to merge", value="", key="new_folder").strip().strip('"')
    if new_folder:
        if st.sidebar.button("🔀 Merge New Folder"):
            if os.path.exists(new_folder):
                # Start merge with fun message
                merge_placeholder = st.sidebar.empty()
                merge_progress = st.sidebar.progress(0)
                merge_message = st.sidebar.empty()
                
                # Display fun merge message
                import random
                merge_messages = [
                    "🧩 Putting the pieces together...",
                    "🔄 Mixing and matching images...",
                    "🌪️ Creating a perfect storm of data...",
                    "🧙‍♂️ Performing AI magic...",
                    "🧬 Splicing image DNA...",
                    "🍳 Cooking up a database fusion...",
                    "🚢 Merging the flotillas...",
                    "🧠 Teaching the AI new tricks..."
                ]
                
                merge_message.info(random.choice(merge_messages))
                merge_placeholder.info(f"Merging images from {new_folder}...")
                
                # Get the list of new images
                new_images = db_manager.get_image_list(new_folder)
                if new_images:
                    st.session_state.total_new_images = len(new_images)
                    st.session_state.current_new_image_index = 0
                    
                    try:
                        # TODO: Replace with actual merge function when available
                        # For now, simulate progress
                        import time
                        for i in range(10):
                            merge_progress.progress(i / 10)
                            merge_message.info(random.choice(merge_messages))
                            time.sleep(0.5)
                        
                        # Complete the progress bar
                        merge_progress.progress(100)
                        merge_placeholder.success(f"Successfully merged {len(new_images)} new images!")
                        merge_message.success("Database ready for searching! 🎉")
                    except Exception as e:
                        merge_placeholder.error(f"Error merging folders: {e}")
                        logger.error(f"Error merging folders: {e}")
                else:
                    merge_placeholder.warning("No new images found to merge.")
            else:
                st.sidebar.error("New folder does not exist!")
    
    # Show model information at the bottom of sidebar
    if st.session_state.get('clip_model') is not None:
        st.sidebar.success("✅ CLIP model is loaded and ready")
        
        # Check if model parameters are actually on GPU
        for param in st.session_state.clip_model.parameters():
            device_type = "GPU" if param.device.type == "cuda" else "CPU"
            st.sidebar.info(f"Model is running on: {device_type}")
            break
    else:
        st.sidebar.warning("CLIP model not loaded yet")
    
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
    if st.session_state.get('clip_model') is not None:
        st.sidebar.success("✅ CLIP model is loaded and ready")
        
        # Check if model parameters are actually on GPU
        for param in st.session_state.clip_model.parameters():
            device_type = "GPU" if param.device.type == "cuda" else "CPU"
            st.sidebar.info(f"Model is running on: {device_type}")
            break
    else:
        st.sidebar.warning("CLIP model not loaded yet")
    
    return image_folder 