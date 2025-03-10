"""
Sidebar components for the Pixel Detective app.
"""
import os
import torch
import streamlit as st
from utils.logger import logger
from utils.image_utils import get_image_list
from models.clip_model import load_clip_model
from database.vector_db import database_exists, load_database, build_database, append_images_to_database
from config import DEFAULT_IMAGE_FOLDER

def render_sidebar():
    """
    Render the sidebar components.
    
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
        st.session_state.image_folder = DEFAULT_IMAGE_FOLDER

    current_folder = st.sidebar.text_input("📁 Database folder", value=st.session_state.image_folder, key="db_folder").strip().strip('"')
    st.session_state.image_folder = current_folder
    
    # Check and indicate if a database exists here
    if os.path.exists(current_folder):
        if database_exists(current_folder):
            st.sidebar.success("🧠 Database exists in this folder!")
        else:
            st.sidebar.info("No database found in this folder.")
    else:
        st.sidebar.error("Folder does not exist!")
    
    # Button to Build/Load the database if it doesn't exist
    if st.sidebar.button("🚀 Build/Load Database"):
        if os.path.exists(current_folder):
            load_clip_model()  # Load the CLIP model if not already loaded
            # Call your build_database function here...
            # (Assuming your build_database function is already handling scanning and building.)
        else:
            st.sidebar.error("Invalid folder path.")
    
    # Now add an option to merge a new folder into the existing database
    new_folder = st.sidebar.text_input("📁 New folder to merge", value="", key="new_folder").strip().strip('"')
    if new_folder:
        if st.sidebar.button("🔀 Merge New Folder"):
            if os.path.exists(new_folder):
                append_images_to_database(current_folder, new_folder)
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
        st.session_state.image_folder = DEFAULT_IMAGE_FOLDER

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