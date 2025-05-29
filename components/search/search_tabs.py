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
from components.task_orchestrator import submit as submit_task, is_running as is_task_running
from core.optimized_model_manager import OptimizedModelManager

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
                try:
                    db_manager = LazySessionManager.ensure_database_manager()
                except Exception as e:
                    st.error(f"❌ Database manager not available: {e}")
                    st.info("💡 Please build the database first using the sidebar.")
                    return
                
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
                try:
                    db_manager = LazySessionManager.ensure_database_manager()
                except Exception as e:
                    st.error(f"❌ Database manager not available: {e}")
                    st.info("💡 Please build the database first using the sidebar.")
                    return
                
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

# Unique key for the AI Guessing Game task in session state
AI_GUESS_TASK_KEY = "ai_guess_task"
AI_GUESS_IMAGE_PATH_KEY = "ai_guess_image_path"
AI_GUESS_RESULT_KEY = "ai_guess_result"

def _run_ai_guess_task(image_path_for_guess):
    """Runs the AI image understanding task and stores the result in session state."""
    try:
        logger.info(f"Starting AI guess task for image: {image_path_for_guess}")
        # 🚀 LAZY LOADING: Get model manager only when needed (OptimizedModelManager is cached)
        # from utils.lazy_session_state import LazySessionManager # Not needed for this call anymore
        # ai_insights = model_manager.get_image_understanding(image_path_for_guess) # OLD CALL
        ai_insights = OptimizedModelManager.get_image_understanding_orchestrated(image_path_for_guess)
        
        st.session_state[AI_GUESS_RESULT_KEY] = ai_insights
        logger.info(f"AI guess task completed for image: {image_path_for_guess}")
    except Exception as e:
        logger.error(f"Error during AI guess task for {image_path_for_guess}: {e}")
        st.session_state[AI_GUESS_RESULT_KEY] = f"Error: Could not get AI insights. {e}"
    finally:
        # Ensure the task is marked as not running even if there's an error
        # TaskOrchestrator might have its own status, but this helps clear our specific UI state
        if AI_GUESS_TASK_KEY in st.session_state and st.session_state[AI_GUESS_TASK_KEY].get("status") == "running":
             st.session_state[AI_GUESS_TASK_KEY]["status"] = "completed"

def render_guessing_game_tab():
    """
    Renders the AI guessing game tab UI with lazy loading and TaskOrchestrator for background processing.
    """
    st.header("🤖 AI Guessing Game")
    st.write("Let the AI try to guess what's in a randomly selected image!")

    try:
        if not hasattr(st, 'session_state'):
            st.warning("Guessing game not available yet. Please complete initial setup.")
        return
    
    # 🚀 LAZY LOADING: Initialize game state only when tab is accessed
        LazySessionManager.init_guessing_game_state()
        # Ensure task orchestrator keys are initialized
        if AI_GUESS_TASK_KEY not in st.session_state:
            st.session_state[AI_GUESS_TASK_KEY] = {"status": "idle"} # idle, running, completed, error
        if AI_GUESS_IMAGE_PATH_KEY not in st.session_state:
            st.session_state[AI_GUESS_IMAGE_PATH_KEY] = None
        if AI_GUESS_RESULT_KEY not in st.session_state:
            st.session_state[AI_GUESS_RESULT_KEY] = None

        # 🚀 LAZY LOADING: Get database manager only when needed
        db_manager = LazySessionManager.ensure_database_manager()
        if not db_manager or not db_manager.is_db_ready():
            st.info("🔄 Database not ready. Please build the database first.")
            return
        
        all_images = db_manager.get_all_image_paths()
        if not all_images:
            st.warning("No images found in the database. Please add images first.")
            return

        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎲 Show Random Image", key="new_random_image_guess_game"):
                st.session_state[AI_GUESS_IMAGE_PATH_KEY] = random.choice(all_images)
                st.session_state[AI_GUESS_RESULT_KEY] = None # Clear previous results
                st.session_state[AI_GUESS_TASK_KEY]["status"] = "idle" # Reset task status

        current_image_path = st.session_state.get(AI_GUESS_IMAGE_PATH_KEY)

        if current_image_path:
            st.image(current_image_path, caption="What does the AI see?", use_container_width=True)
        
        with col2:
                if st.session_state[AI_GUESS_TASK_KEY]["status"] == "idle" and st.button("🧠 AI, what do you see?"):
                    if current_image_path:
                        st.session_state[AI_GUESS_RESULT_KEY] = None # Clear previous result before new task
                        logger.info(f"Submitting AI guess task for: {current_image_path}")
                        # Use the imported submit_task and is_task_running
                        submit_task(
                            name=AI_GUESS_TASK_KEY,
                            fn=_run_ai_guess_task,
                            image_path_for_guess=current_image_path
                        )
                        st.session_state[AI_GUESS_TASK_KEY]["status"] = "running" # Manually update our status tracker
                        st.rerun() # Rerun to show spinner

                if st.session_state[AI_GUESS_TASK_KEY]["status"] == "running" or is_task_running(AI_GUESS_TASK_KEY):
                    st.spinner("🤔 AI is thinking...")
                    # If is_task_running shows it's done but our status hasn't updated, sync it.
                    if not is_task_running(AI_GUESS_TASK_KEY) and st.session_state[AI_GUESS_TASK_KEY]["status"] == "running":
                        st.session_state[AI_GUESS_TASK_KEY]["status"] = "completed"
                        st.rerun()

            ai_result = st.session_state.get(AI_GUESS_RESULT_KEY)
            if ai_result:
                if isinstance(ai_result, str) and ai_result.startswith("Error:"):
                    st.error(ai_result)
                else:
                    st.subheader("🤖 AI's Thoughts:")
                    if isinstance(ai_result, dict):
                        for key, value in ai_result.items():
                            st.markdown(f"**{key.replace('_', ' ').title()}:**")
                            if isinstance(value, list):
                                for item in value:
                                    st.markdown(f"- {item}")
                    else:
                                st.markdown(str(value))
                    else: # Should be the detailed string from get_image_understanding
                        st.markdown(ai_result)
                 # Reset task status to allow new guess on the same image or new image
                if st.session_state[AI_GUESS_TASK_KEY]["status"] != "idle": # Check to prevent multiple resets
                    st.session_state[AI_GUESS_TASK_KEY]["status"] = "idle"

                                else:
            st.info("Click 'Show Random Image' to start the game.")

    except Exception as e:
        logger.error(f"Error in AI Guessing Game tab: {e}")
        st.error("An error occurred in the Guessing Game. Please try again or check the logs.")

def render_duplicates_tab():
    """
    Renders the duplicates tab UI using TaskOrchestrator for background processing.
    """
    st.header("🧑‍🤝‍🧑 Duplicate Detection (Post-Embedding)")
    st.write("Find near-duplicate images using vector similarity in the embedding space.")

    if not st.session_state.get("database_built", False):
        st.warning("Please build or load a database first.")
        return

    # LAZY LOADING: Initialize search state only when tab is accessed
    LazySessionManager.init_search_state()

    # Task function for duplicate detection
    def _run_duplicate_detection_task():
            try:
            st.session_state.duplicate_results = [] # Clear previous results
                db_manager = LazySessionManager.ensure_database_manager()
            qdrant_db = st.session_state.qdrant_db # Assuming qdrant_db is in session_state
            
            duplicates = db_manager.find_duplicate_images(qdrant_db)
            st.session_state.duplicate_results = duplicates
            st.session_state.duplicates_status = "completed"
            # No st.rerun() here; UI will update based on session state changes
        except Exception as e:
            st.session_state.duplicates_status = "error"
            st.session_state.duplicates_error_message = str(e)
            # Log the error if a logger is available/configured
            logger = LazySessionManager.lazy_import('logging').getLogger(__name__)
            logger.error(f"Error during duplicate detection task: {e}", exc_info=True)

    if st.button("🔍 Find Duplicates"): 
        if not is_task_running("duplicate_detection_task"):
            st.session_state.duplicates_status = "running"
            st.session_state.duplicate_results = None # Clear previous results display
            submit_task("duplicate_detection_task", _run_duplicate_detection_task)
            # No st.rerun() here immediately, let the spinner show and periodic checks update UI
        else:
            st.info("Duplicate detection is already in progress.")

    # Display status and results
    task_status = st.session_state.get("duplicates_status")
    
    if task_status == "running" or is_task_running("duplicate_detection_task"):
        st.spinner("Searching for duplicate images...")
        # Add a timed rerun to refresh the spinner and check task status if needed
        # This can be a simple time.sleep() + st.rerun() or a more sophisticated callback
        # For now, relying on user interaction or other timed refreshes on the page.
        # Consider adding a specific rerun logic if the spinner feels stuck.

    elif task_status == "completed":
        duplicates = st.session_state.get('duplicate_results', [])
        if duplicates:
            st.success(f"Found {len(duplicates)} duplicate pairs above similarity 0.98.")
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
        else:
        st.info("No duplicate pairs found above the threshold.") 
    elif task_status == "error":
        st.error(f"Error during duplicate detection: {st.session_state.get('duplicates_error_message', 'Unknown error')}")
    
    # If no button clicked yet, and no status, it's the initial state
    elif task_status is None and 'duplicate_results' not in st.session_state:
        st.info("Click 'Find Duplicates' to start the detection process.") 