# 📂 File Path: /project_root/ui/main_interface.py
# 📌 Purpose: Renders the main user interface for the Pixel Detective application.
# 🔄 Latest Changes: Created module to centralize UI rendering.
# ⚙️ Key Logic: Provides functions to render the main interface and sidebar.
# 🧠 Reasoning: Centralizes UI code for better organization and maintainability.

import streamlit as st
import os
from ui.tabs import render_text_search_tab, render_image_upload_tab, render_guessing_game_tab

def render_main_interface():
    """
    Render the complete application interface, including sidebar and main content.
    This is the main entry point for the UI rendering.
    """
    # Render the sidebar
    with st.sidebar:
        render_sidebar()
    
    # Render the main content
    render_main_content()

def render_sidebar():
    """
    Render the sidebar with controls for building and loading the database.
    """
    st.title("🕵️‍♂️ Command Center")
    
    # Input for image folder
    primary_folder = st.text_input("📁 Image Folder Path", value=os.path.expanduser("~/Pictures"))
    
    # Button to build database
    if st.button("🧠 Launch the Brain Builder!"):
        if os.path.exists(primary_folder):
            with st.spinner("🔍 Scanning for images..."):
                db_manager = st.session_state.db_manager
                image_files = db_manager.get_image_list(primary_folder)
                
                if image_files:
                    st.session_state.image_files = image_files
                    st.session_state.total_images = len(image_files)
                    st.info(f"Found {len(image_files)} images. Building database...")
                    
                    # Build the database
                    db_manager.build_database(primary_folder, image_files)
                    st.success("Database built and saved successfully!")
                else:
                    st.error("No images found in the specified folder.")
        else:
            st.error("Folder does not exist!")
    
    # Option to load existing database
    if st.button("📂 Load Existing Database"):
        if os.path.exists(primary_folder):
            with st.spinner("🔍 Loading database..."):
                db_manager = st.session_state.db_manager
                if db_manager.database_exists(primary_folder):
                    db_manager.load_database(primary_folder)
                    st.success("Database loaded successfully!")
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
                    # Merge the new folder
                    from database.vector_db import append_images_to_database
                    append_images_to_database(primary_folder, new_folder)
            else:
                st.error("New folder does not exist!")

def render_main_content():
    """
    Render the main content area with tabs for searching and playing the guessing game.
    """
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
        
        # Show a detective image
        st.image("https://i.imgur.com/3vvZbSh.png", caption="Ready to investigate your images!")
    else:
        # Database is built, show the tabs for searching
        tab1, tab2, tab3 = st.tabs(["Text Search", "Image Search", "AI Guessing Game"])
        
        with tab1:
            # Text search tab
            render_text_search_tab()
            
        with tab2:
            # Image upload tab
            render_image_upload_tab()
            
        with tab3:
            # Guessing game tab
            render_guessing_game_tab() 