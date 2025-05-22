# 📂 File Path: /project_root/ui/main_interface.py
# 📌 Purpose: Renders the main user interface for the Pixel Detective application.
# 🔄 Latest Changes: 
#   - Created module to centralize UI rendering.
#   - Added tab state persistence to fix tab reset issue.
#   - Enhanced image loading with multiple fallback methods.
#   - Added HTML fallback for image display.
#   - Added minigame fallback when image cannot be displayed.
#   - Reverted to default dark mode with extendable sidebar for images.
# ⚙️ Key Logic: Provides functions to render the main interface and sidebar.
# 🧠 Reasoning: Centralizes UI code for better organization and maintainability.

import streamlit as st
import os
import base64
from pathlib import Path
from ui.tabs import render_text_search_tab, render_image_upload_tab, render_guessing_game_tab
from ui.latent_space import render_latent_space_tab
import sys

# Add the root directory to the path to import minigame
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.minigame import BreakoutGame

# Function to load image from various locations with fallbacks
def get_image_path(image_name):
    """
    Try multiple methods to locate and load an image file.
    Returns the path if found, None otherwise.
    """
    # Method 1: Check in assets directory (relative to this file)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_path = os.path.join(base_dir, "assets", image_name)
    if os.path.exists(assets_path):
        return assets_path
    
    # Method 2: Check in .streamlit/static directory
    streamlit_static = os.path.join(base_dir, ".streamlit", "static", image_name)
    if os.path.exists(streamlit_static):
        return streamlit_static
    
    # Method 3: Check in current working directory
    cwd_path = os.path.join(os.getcwd(), image_name)
    if os.path.exists(cwd_path):
        return cwd_path
    
    # Method 4: Check in current working directory's assets folder
    cwd_assets = os.path.join(os.getcwd(), "assets", image_name)
    if os.path.exists(cwd_assets):
        return cwd_assets
    
    return None

# Function to display an image using HTML as a fallback
def display_image_html():
    """Display a detective image using HTML directly."""
    # Direct URL to the image
    image_url = "https://i.imgur.com/3vvZbSh.png"
    
    # HTML to display the image with dark mode compatibility
    html = f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <img src="{image_url}" alt="Detective" style="max-width: 400px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
        <p style="font-style: italic; margin-top: 10px; color: var(--text-color, #FAFAFA);">Ready to investigate your images!</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# Function to display a base64 encoded image
def display_base64_image():
    """Display a detective image using base64 encoding."""
    try:
        # Check if we have a base64 encoded image in a file
        base64_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "detective_base64.txt")
        if os.path.exists(base64_file) and os.path.getsize(base64_file) > 0:
            with open(base64_file, "r") as f:
                base64_data = f.read().strip()
                if base64_data:
                    st.markdown(f"""
                    <div style="text-align: center; margin-bottom: 20px;">
                        <img src="data:image/png;base64,{base64_data}" alt="Detective" style="max-width: 400px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
                        <p style="font-style: italic; margin-top: 10px; color: var(--text-color, #FAFAFA);">Ready to investigate your images!</p>
                    </div>
                    """, unsafe_allow_html=True)
                    return True
        return False
    except Exception as e:
        st.warning(f"Could not display base64 image: {e}")
        return False

# Function to display a waiting message
def display_waiting_message():
    """Display an animated waiting message."""
    st.markdown("""
    <div style="text-align: center; margin: 50px 0;">
        <h2 style="color: var(--primary-color, #4F8BF9);">Building your image database...</h2>
        <div style="font-size: 72px; margin: 30px 0;">🔍</div>
        <p style="font-style: italic; color: var(--text-color, #FAFAFA);">
            Our AI detective is analyzing your images.<br>
            This might take a few moments.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_main_interface():
    """
    Render the complete application interface, including extendable sidebar and main content.
    This is the main entry point for the UI rendering.
    """
    # Render the sidebar
    from ui.sidebar import render_sidebar
    sidebar_config = render_sidebar()
    
    # Render the main content
    render_main_content()
    
    return sidebar_config

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
        
        # Try multiple methods to display the detective image
        image_displayed = False
        
        # Method 1: Try to load the detective image using our helper function
        detective_image_path = get_image_path("detective.png")
        
        if detective_image_path:
            try:
                st.image(detective_image_path, caption="Ready to investigate your images!")
                image_displayed = True
            except Exception as e:
                st.session_state.image_displayed = False
                st.warning(f"Could not display detective image from file: {e}")
        
        # Method 2: Try using base64 encoded image
        if not image_displayed:
            image_displayed = display_base64_image()
        
        # Method 3: If the previous methods failed, try using HTML
        if not image_displayed:
            try:
                display_image_html()
                image_displayed = True
            except Exception as e:
                st.warning(f"Could not display detective image using HTML: {e}")
                # Fallback to a simple emoji
                st.markdown("# 🕵️‍♂️")
                st.caption("Ready to investigate your images!")
                image_displayed = False
        
        # Method 4: If all image display methods failed, show the minigame or waiting message
        if not image_displayed:
            st.markdown("### While we prepare your database, enjoy this mini-game!")
            
            # Create a container for the game
            game_container = st.container()
            
            # Initialize the game if it doesn't exist in session state
            if 'breakout_game' not in st.session_state:
                st.session_state.breakout_game = BreakoutGame(game_container)
            
            # Render the game
            st.session_state.breakout_game.render()
            
            # Alternative: Show a waiting message
            if st.button("Show Waiting Message Instead"):
                display_waiting_message()
    else:
        # Define tab names and render content directly via st.tabs
        tab_names = ["Text Search", "Image Search", "AI Guessing Game", "Latent Space"]
        tabs = st.tabs(tab_names)
        with tabs[0]:
            render_text_search_tab()
        with tabs[1]:
            render_image_upload_tab()
        with tabs[2]:
            render_guessing_game_tab()
        with tabs[3]:
            render_latent_space_tab() 