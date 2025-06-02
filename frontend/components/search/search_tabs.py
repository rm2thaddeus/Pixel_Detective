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
# import torch # REMOVED: No direct torch usage
# import clip # REMOVED: No direct clip usage
# import pandas as pd # pandas might be used by individual tabs if they process API results into DataFrames
# import numpy as np # numpy might be used by individual tabs
from PIL import Image # Keep PIL if displaying/manipulating images locally, but not for core model tasks
import os
import random
# from models.clip_model import load_clip_model, get_image_understanding # REMOVED
# import tempfile # REMOVED: Tempfile for image upload no longer needed for API calls
from utils.logger import logger
# from utils.metadata_extractor import extract_metadata # REMOVED: If not used directly by UI after LazySessionManager removal
# from utils.lazy_session_state import LazySessionManager # REMOVED
from components.task_orchestrator import submit as submit_task, is_running as is_task_running
# from core.optimized_model_manager import OptimizedModelManager # REMOVED
from streamlit_extras.switch_page_button import switch_page # Keep if used
from core import service_api

# Callbacks for metadata expansion (These are fine as local UI helpers)
def _toggle_text_metadata(metadata_key):
    if 'text_metadata_expanded' not in st.session_state:
        st.session_state.text_metadata_expanded = {}
    st.session_state.text_metadata_expanded[metadata_key] = not st.session_state.text_metadata_expanded.get(metadata_key, False)

def _toggle_image_metadata(metadata_key):
    if 'image_metadata_expanded' not in st.session_state:
        st.session_state.image_metadata_expanded = {}
    st.session_state.image_metadata_expanded[metadata_key] = not st.session_state.image_metadata_expanded.get(metadata_key, False)

def render_text_search_tab():
    """
    Renders the text search tab UI. Backend services handle search logic.
    """
    st.header("🔍 Text Search")
    st.write("Search for images using text descriptions.")
    
    try:
        if not hasattr(st, 'session_state'):
            st.warning("Text search not available yet.")
            return
        
        # Simplified check: Does a folder_path exist? If not, probably nothing to search.
        if not st.session_state.get('folder_path'):
            st.info("🔄 Please select and process a folder first (using the sidebar) to enable search.")
            return
            
        # REMOVED: LazySessionManager.init_search_state()
        # REMOVED: LazySessionManager.init_metadata_state()
        # Component-specific UI state for metadata expansion will be initialized by callbacks if needed.

        query = st.text_input("Enter your search terms:", placeholder="e.g., sunset over mountains, cute dog, family picnic", key="text_search_query_input")
        num_results = st.slider("Number of results:", min_value=1, max_value=50, value=10, key="text_search_num_results") # Increased max

    except Exception as e: # Broad exception for UI setup
        logger.error(f"Error setting up text search tab: {e}", exc_info=True)
        st.error("Text search temporarily unavailable. Please try refreshing.")
        return # Stop rendering if basic setup fails
    
    if st.button("🔍 Search Images", key="text_search_button"):
        if query:
            with st.spinner("Searching..."):
                # API call to backend search service
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                api_response = loop.run_until_complete(service_api.search_images_by_text(query=query, top_k=num_results))
                loop.close()
                
                results = []
                if isinstance(api_response, dict) and api_response.get("error"):
                    st.error(f"Search failed: {api_response.get('detail', api_response['error'])}")
                elif isinstance(api_response, list):
                    results = api_response
                else:
                    st.error(f"Search returned an unexpected response format: {type(api_response)}")
                
                if results:
                    st.success(f"Found {len(results)} results!")
                    # Display results
                    for i, result in enumerate(results):
                        # Ensure score is a float before formatting
                        score = result.get('score', 0.0)
                        try:
                            score_percentage = float(score) * 100
                        except (ValueError, TypeError):
                            score_percentage = 0.0 
                            logger.warning(f"Could not convert score '{score}' to float for result: {result.get('path')}")

                        result_container = st.container()
                        with result_container:
                            col1, col2 = st.columns([1, 2])
                            img_path = result.get('path', '')
                            with col1:
                                if img_path:
                                    try:
                                        st.image(img_path, caption=f"Score: {score_percentage:.1f}%", use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Error loading image: {os.path.basename(img_path)}")
                                        logger.debug(f"Image load error for {img_path}: {e}")
                                else:
                                    st.caption("Image path not available.")
                            
                            with col2:
                                filename = os.path.basename(img_path) if img_path else "N/A"
                                st.write(f"**Filename:** {filename}")
                                st.write(f"**Similarity:** {score_percentage:.1f}%")
                                
                                # Display caption and tags if present in payload
                                payload = result.get('payload', {})
                                caption = payload.get('caption', result.get('caption')) # Check payload first
                                tags = payload.get('tags', result.get('tags'))

                                if caption:
                                    st.write(f"**Caption:** {caption}")
                                if tags:
                                    tags_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
                                    st.write(f"**Tags:** {tags_str}")
                        st.divider()
                elif not (isinstance(api_response, dict) and api_response.get("error")): # Avoid double message if error already shown
                    st.info("No results found. Try different search terms.")
        else:
            st.warning("Please enter a search query.")

def render_image_upload_tab():
    """
    Renders the image upload tab UI. Backend services handle search logic.
    """
    st.header("📸 Image Search")
    st.write("Upload an image to find similar images in your collection.")
    
    try:
        if not hasattr(st, 'session_state'):
            st.warning("Image search not available yet.")
            return
            
        if not st.session_state.get('folder_path'):
            st.info("🔄 Please select and process a folder first (using the sidebar) to enable search.")
            return
            
        # REMOVED: LazySessionManager.init_search_state()

        uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png', 'bmp', 'gif'], key="image_search_uploader")
        num_results = st.slider("Number of similar images:", min_value=1, max_value=50, value=10, key="image_search_num_results") # Increased max

    except Exception as e:
        logger.error(f"Error setting up image search tab: {e}", exc_info=True)
        st.error("Image search temporarily unavailable. Please try refreshing.")
        return
    
    if uploaded_file is not None:
        try:
            # Display the uploaded image
            st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        except Exception as e:
            st.error(f"Could not display uploaded image: {e}")
            return # Don't proceed if image can't be displayed
        
        if st.button("🔍 Find Similar Images", key="image_search_button"):
            with st.spinner("Searching for similar images..."):
                image_bytes = uploaded_file.getvalue()
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                api_response = loop.run_until_complete(
                    service_api.search_images_by_image(image_bytes=image_bytes, top_k=num_results)
                )
                loop.close()

                results = []
                if isinstance(api_response, dict) and api_response.get("error"):
                    st.error(f"Search failed: {api_response.get('detail', api_response['error'])}")
                elif isinstance(api_response, list):
                    results = api_response
                else:
                    st.error(f"Search returned an unexpected response format: {type(api_response)}")

                if results:
                    st.success(f"Found {len(results)} similar images!")
                    for i, result in enumerate(results):
                        score = result.get('score', 0.0)
                        try:
                            score_percentage = float(score) * 100
                        except (ValueError, TypeError):
                            score_percentage = 0.0
                            logger.warning(f"Could not convert score '{score}' to float for result: {result.get('path')}")

                        result_container = st.container()
                        with result_container:
                            col1, col2 = st.columns([1, 2])
                            img_path = result.get('path', '')
                            with col1:
                                if img_path:
                                    try:
                                        st.image(img_path, caption=f"Score: {score_percentage:.1f}%", use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Error loading image: {os.path.basename(img_path)}")
                                        logger.debug(f"Image load error for {img_path}: {e}")
                                else:
                                    st.caption("Image path not available.")
                            
                            with col2:
                                filename = os.path.basename(img_path) if img_path else "N/A"
                                st.write(f"**Filename:** {filename}")
                                st.write(f"**Similarity:** {score_percentage:.1f}%")

                                payload = result.get('payload', {})
                                caption = payload.get('caption', result.get('caption'))
                                tags = payload.get('tags', result.get('tags'))
                                if caption:
                                    st.write(f"**Caption:** {caption}")
                                if tags:
                                    tags_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
                                    st.write(f"**Tags:** {tags_str}")
                        st.divider()
                elif not (isinstance(api_response, dict) and api_response.get("error")):
                    st.info("No similar images found.")
        
        # REMOVED: tempfile creation and os.unlink as image_bytes are used directly

# --- AI Guessing Game ---
AI_GUESS_TASK_KEY = "ai_guess_task_status" # Changed key to be more specific about what it stores
AI_GUESS_IMAGE_PATH_KEY = "ai_guess_image_path"
AI_GUESS_RESULT_KEY = "ai_guess_result"

def _run_ai_guess_task(image_path_for_guess: str):
    """Runs the AI image captioning task via service_api and stores the result."""
    st.session_state[AI_GUESS_RESULT_KEY] = None # Clear previous results
    try:
        logger.info(f"AI Guess Task: Reading image {image_path_for_guess}")
        image_bytes = None
        try:
            with open(image_path_for_guess, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            err_msg = f"Error reading image file for AI guess: {e}"
            logger.error(err_msg, exc_info=True)
            st.session_state[AI_GUESS_RESULT_KEY] = {"error": err_msg}
            return

        if image_bytes:
            logger.info(f"AI Guess Task: Calling service_api.get_caption for {image_path_for_guess}")
            # Run async function in a new event loop for threaded context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            api_response = loop.run_until_complete(service_api.get_caption(image_bytes=image_bytes))
            loop.close()
            
            if isinstance(api_response, dict) and api_response.get("error"):
                err_msg = f"Error from AI caption service: {api_response.get('detail', api_response['error'])}"
                logger.error(err_msg)
                st.session_state[AI_GUESS_RESULT_KEY] = {"error": err_msg}
            elif isinstance(api_response, dict) and "caption" in api_response:
                st.session_state[AI_GUESS_RESULT_KEY] = api_response 
                logger.info(f"AI guess (caption) task completed for: {image_path_for_guess}")
            else:
                err_msg = f"Unexpected response from AI caption service: {api_response}"
                logger.error(err_msg)
                st.session_state[AI_GUESS_RESULT_KEY] = {"error": err_msg}
        else:
            st.session_state[AI_GUESS_RESULT_KEY] = {"error": "Image data was not available for AI guess."}
    except Exception as e:
        err_msg = f"General error during AI guess task for {image_path_for_guess}: {e}"
        logger.error(err_msg, exc_info=True)
        st.session_state[AI_GUESS_RESULT_KEY] = {"error": err_msg}

def render_guessing_game_tab():
    """
    Renders the AI guessing game tab UI.
    """
    st.header("🤖 AI Guessing Game")
    st.write("Let the AI try to guess what's in a randomly selected image!")

    if not hasattr(st, 'session_state'):
        st.warning("Guessing game not available yet.")
        return

    # REMOVED: LazySessionManager.init_guessing_game_state()
    # Initialize necessary session state keys directly if not present
    if AI_GUESS_TASK_KEY not in st.session_state:
        st.session_state[AI_GUESS_TASK_KEY] = "idle" # idle, running, completed, error
    if AI_GUESS_IMAGE_PATH_KEY not in st.session_state:
        st.session_state[AI_GUESS_IMAGE_PATH_KEY] = None
    if AI_GUESS_RESULT_KEY not in st.session_state:
        st.session_state[AI_GUESS_RESULT_KEY] = None
    if 'all_image_paths_for_game' not in st.session_state:
        st.session_state.all_image_paths_for_game = []
        
    # Load image paths for the game if not already loaded
    if not st.session_state.all_image_paths_for_game and st.session_state.get('folder_path'):
        with st.spinner("Loading image list for the game..."):
            # Run async function in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Fetch a reasonable number of images. Max 1000 to prevent overload.
            response = loop.run_until_complete(service_api.list_images_qdrant(page=1, per_page=1000))
            loop.close()

            if isinstance(response, dict) and response.get("error"):
                st.error(f"Could not load image list for game: {response.get('detail', response['error'])}")
            elif isinstance(response, dict) and "images" in response:
                st.session_state.all_image_paths_for_game = [
                    img_data.get('path') for img_data in response["images"] 
                    if img_data.get('path') and os.path.exists(img_data.get('path')) # Ensure path exists locally for display
                ]
                if not st.session_state.all_image_paths_for_game:
                    st.warning("No valid local image paths found via API for the game. Ensure backend returns accessible paths.")
            else:
                st.error("Failed to load image list for game: Unexpected API response.")
    
    all_images_for_game = st.session_state.all_image_paths_for_game

    col1, col2 = st.columns(2)
    with col1:
        show_random_image_disabled = not bool(all_images_for_game) or st.session_state[AI_GUESS_TASK_KEY] == "running"
        if st.button("🎲 Show Random Image", key="new_random_image_guess_game_btn", disabled=show_random_image_disabled):
            if all_images_for_game:
                st.session_state[AI_GUESS_IMAGE_PATH_KEY] = random.choice(all_images_for_game)
                st.session_state[AI_GUESS_RESULT_KEY] = None 
                st.session_state[AI_GUESS_TASK_KEY] = "idle"
                st.rerun() # Rerun to update image and button states
            else:
                st.warning("No images available to choose from. Ensure a folder is processed.")

    current_image_path = st.session_state.get(AI_GUESS_IMAGE_PATH_KEY)

    if current_image_path:
        try:
            st.image(current_image_path, caption="What does the AI see?", use_container_width=True)
        except Exception as e:
            st.error(f"Error displaying image: {current_image_path}. Error: {e}")
            st.session_state[AI_GUESS_IMAGE_PATH_KEY] = None # Clear problematic path
    
    with col2:
        if current_image_path and st.session_state[AI_GUESS_TASK_KEY] == "idle":
            if st.button("🧠 AI, what do you see?", key="ai_guess_trigger_btn"):
                st.session_state[AI_GUESS_TASK_KEY] = "running"
                logger.info(f"Submitting AI guess task for: {current_image_path}")
                # Task orchestrator runs the function in a separate thread
                submit_task(
                    name="ai_guess_processing_task", # Use a more descriptive name for orchestrator
                    fn=_run_ai_guess_task,
                    image_path_for_guess=current_image_path
                )
                st.rerun() 

        if st.session_state[AI_GUESS_TASK_KEY] == "running" or is_task_running("ai_guess_processing_task"):
            st.spinner("🤔 AI is thinking...")
            # If task orchestrator says it's done, but our local status is still running, update.
            if not is_task_running("ai_guess_processing_task") and st.session_state[AI_GUESS_TASK_KEY] == "running":
                st.session_state[AI_GUESS_TASK_KEY] = "completed" # Or "idle" if result implies immediate readiness for next
                st.rerun() # Rerun to display result or clear spinner

        ai_guess_result_data = st.session_state.get(AI_GUESS_RESULT_KEY)
        if ai_guess_result_data: # Check if there's any result (could be data or error dict)
            if isinstance(ai_guess_result_data, dict) and ai_guess_result_data.get("error"):
                st.error(ai_guess_result_data["error"])
            elif isinstance(ai_guess_result_data, dict) and "caption" in ai_guess_result_data:
                st.subheader("🤖 AI's Thoughts:")
                st.markdown(f"> {ai_guess_result_data['caption']}")
                # Optionally display other details from ai_guess_result_data if any
            else: # Fallback for unexpected structure, though _run_ai_guess_task tries to make it an error dict
                st.info("AI's thoughts are being processed or in an unexpected format.")
            
            # Once result is shown (or error), reset task state to idle for next action
            if st.session_state[AI_GUESS_TASK_KEY] != "idle":
                st.session_state[AI_GUESS_TASK_KEY] = "idle"
                # Consider if a rerun is needed here or if UI updates naturally
    
    if not current_image_path and st.session_state.get('folder_path'):
        st.info("Click 'Show Random Image' to start the game.")
    elif not st.session_state.get('folder_path'):
        st.info("Please select and process a folder first to enable the guessing game.")


def render_duplicates_tab(): # Renamed from commented out section
    """
    Renders the duplicates tab UI. Currently a placeholder as backend service is required.
    """
    st.header("🧑‍🤝‍🧑 Duplicate Detection")
    st.write("Find near-duplicate images using vector similarity in the embedding space.")

    # REMOVED: LazySessionManager.init_search_state()

    # This feature explicitly requires a backend service endpoint for duplicate detection.
    # The old logic using db_manager.find_duplicate_images is removed.
    
    st.warning("⚠️ The Duplicate Detection feature is currently under development and requires a dedicated backend service. This tab will be fully functional once the backend endpoint is available and integrated via `service_api.py`.")
    st.info("Planned functionality: Trigger backend duplicate detection, view groups of similar images.")

    # Example structure for when backend is ready:
    # if 'duplicate_detection_job_id' not in st.session_state:
    #     st.session_state.duplicate_detection_job_id = None
    # if 'duplicate_results_data' not in st.session_state:
    #     st.session_state.duplicate_results_data = None
    # if 'duplicate_detection_status' not in st.session_state: # e.g., idle, pending, processing, completed, error
    #     st.session_state.duplicate_detection_status = "idle"

    # if st.button("🔍 Find Duplicates (via Backend Service)"):
    #     if st.session_state.duplicate_detection_status not in ["pending", "processing"]:
    #         st.session_state.duplicate_detection_status = "pending"
    #         st.session_state.duplicate_results_data = None # Clear previous
    #         # Placeholder for API call:
    #         # async def call_backend_duplicates():
    #         #     response = await service_api.trigger_duplicate_detection_job() # New function in service_api
    #         #     if response and response.get("job_id"):
    #         #         st.session_state.duplicate_detection_job_id = response["job_id"]
    #         #         st.session_state.duplicate_detection_status = "processing"
    #         #     else:
    #         #         st.session_state.duplicate_detection_status = "error"
    #         #         st.error(f"Failed to start duplicate detection: {response.get('error', 'Unknown')}")
    #         # asyncio.run(call_backend_duplicates())
    #         st.info("Placeholder: This would call a backend duplicate detection service.")
    #     else:
    #         st.info("Duplicate detection is already in progress or pending.")

    # # Polling and displaying results would go here, similar to loading_screen.py for ingestion jobs.
