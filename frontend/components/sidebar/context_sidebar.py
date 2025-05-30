import streamlit as st
import os
import torch
import random
from utils.logger import logger
from utils.lazy_session_state import LazySessionManager
<<<<<<< HEAD
from config import DEFAULT_IMAGES_PATH
from database.qdrant_connector import QdrantDB
from components.task_orchestrator import submit, is_running
=======
from utils.qdrant_db import QdrantDB

# Default path for images
DEFAULT_IMAGES_PATH = os.path.expanduser("~/Pictures")
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb

def render_sidebar():
    """
    Render the sidebar components.
    
    Returns:
        str: The selected image folder path.
    """
    st.sidebar.header("🔧 Database Manager")
    
    # Display colored device status with fun names
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        st.sidebar.markdown(f"<h3 style='color: green;'> Super Graphix Cardz Activated! 🔥</h3>", unsafe_allow_html=True)
        st.sidebar.markdown(f"<p>Your trusty sidekick today: <b>{gpu_name}</b> - ready to crunch pixels!</p>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h3 style='color: orange;'>🐢 CPU Mode (Slow & Steady) 🐢</h3>", unsafe_allow_html=True)
        st.sidebar.markdown("<p>No Graphix Cardz detected. We'll do our best with brain power alone!</p>", unsafe_allow_html=True)
    
    # FIXED: Check if we're in a proper Streamlit context before accessing session state
    try:
        # Only access session state if we're in the main UI thread
        if not hasattr(st, 'session_state'):
            st.sidebar.warning("Sidebar not available yet. Please complete the initial setup first.")
            return DEFAULT_IMAGES_PATH
            
        # Current folder for the existing database
        if 'image_folder' not in st.session_state:
            st.session_state.image_folder = DEFAULT_IMAGES_PATH

        current_folder = st.sidebar.text_input("📁 Database folder", value=st.session_state.image_folder, key="db_folder").strip().strip('"')
        st.session_state.image_folder = current_folder
        
<<<<<<< HEAD
        # Note: Removed the database_ready check as it was preventing database creation
        
        # 🚀 LAZY LOADING: Get db_manager only when needed and safe
        # Don't try to create database manager on every page load - only when user needs it
        db_manager = st.session_state.get('db_manager', None)
        if db_manager is None:
            st.sidebar.info("🔄 Database manager will initialize when you build/load a database.")
        
        # Check and indicate if a database exists here
=======
        # Check if database is ready before trying to access it
        if not st.session_state.get('database_ready', False):
            st.sidebar.info("🔄 Database not ready yet. Please complete the image processing first.")
            return current_folder
        
        # 🚀 LAZY LOADING: Get db_manager only when needed and safe
        db_manager = LazySessionManager.ensure_database_manager()
        
        # Check and indicate if a database exists here
        if os.path.exists(current_folder):
            if db_manager.database_exists(current_folder):
                st.sidebar.success("🧠 Database exists in this folder!")
            else:
                st.sidebar.info("No database found in this folder.")
        else:
            st.sidebar.error("Folder does not exist!")
    except Exception as e:
        logger.error(f"Error in sidebar rendering: {e}")
        st.sidebar.warning("Sidebar temporarily unavailable. Please refresh the page.")
        return DEFAULT_IMAGES_PATH
    
    # Button to Build/Load the database if it doesn't exist
    if st.sidebar.button("🚀 Build/Load Database"):
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb
        if os.path.exists(current_folder):
            if db_manager:
                try:
                    if db_manager.database_exists(current_folder):
                        st.sidebar.success("🧠 Database exists in this folder!")
                    else:
                        st.sidebar.info("No database found in this folder.")
                except Exception as e:
                    st.sidebar.error(f"❌ Error checking database: {e}")
                    logger.error(f"Error checking database existence: {e}")
            else:
                st.sidebar.info("🔄 Database manager loading... Click 'Build/Load Database' to initialize.")
        else:
            st.sidebar.error("Folder does not exist!")
    except Exception as e:
        logger.error(f"Error in sidebar rendering: {e}")
        st.sidebar.warning("Sidebar temporarily unavailable. Please refresh the page.")
        return DEFAULT_IMAGES_PATH
    
    # Handle Build/Load in background using TaskOrchestrator
    if st.sidebar.button("🚀 Build/Load Database") and os.path.exists(current_folder):
        LazySessionManager.init_search_state()
        # Schedule the build/load task
        scheduled = submit("build_db", _background_build_or_load_db, current_folder)
        if scheduled:
            st.sidebar.info("🕵️‍♂️ Database build/load started in background.")
            st.session_state.build_db_started = True
        else:
            st.sidebar.warning("⚠️ Database build already running.")

    # Poll build status
    if st.session_state.get('build_db_started'):
        if is_running("build_db"):
            st.sidebar.info("🔄 Database build in progress...")
        else:
            st.sidebar.success("✅ Database build/load complete!")
            st.session_state.build_db_started = False
            st.session_state.database_built = True
            # Initialize QdrantDB after completion
            try:
                st.session_state.qdrant_db = QdrantDB(collection_name="image_collection")
            except:
                pass

    # Now add an option to merge a new folder into the existing database
    new_folder = st.sidebar.text_input("📁 New folder to merge", value="", key="new_folder").strip().strip('"')
    
    # Handle Merge New Folder in background using TaskOrchestrator
    if st.sidebar.button("🔗 Merge New Folder") and new_folder and os.path.exists(new_folder):
        scheduled = submit("merge_db", _background_merge_folder, current_folder, new_folder)
        if scheduled:
            st.sidebar.info(f"🔗 Merge `{new_folder}` started in background.")
            st.session_state.merge_db_started = True
        else:
            st.sidebar.warning("⚠️ Merge already running.")

    # Poll merge status
    if st.session_state.get('merge_db_started'):
        if is_running("merge_db"):
            st.sidebar.info("🔄 Folder merge in progress...")
        else:
            st.sidebar.success("✅ Folder merge complete!")
            st.session_state.merge_db_started = False
            st.sidebar.info("Database updated. Ready to search! 🎉")

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
    # watch_enabled = st.sidebar.checkbox("📡 Enable Incremental Indexing", value=False, key="enable_watch")
    # if watch_enabled:
    #     if 'indexer_observer' not in st.session_state:
    #         from utils.embedding_cache import get_cache
    #         from utils.incremental_indexer import start_incremental_indexer
    #
    #         cache = get_cache()
    #         folder = current_folder
    #         # model_mgr = LazySessionManager.ensure_model_manager() # This would fail
    #         # db_manager = LazySessionManager.ensure_database_manager() # This would fail
    #         st.sidebar.warning("Incremental indexer needs refactoring for new service architecture.")
    #         # observer = start_incremental_indexer(folder, db_manager, cache, model_mgr)
    #         # st.session_state.indexer_observer = observer
    #         # st.sidebar.success("Incremental indexer started.")
    # else:
    #     if 'indexer_observer' in st.session_state:
    #         st.session_state.indexer_observer.stop()
    #         del st.session_state.indexer_observer
    #         st.sidebar.info("Incremental indexer stopped.")

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
    
<<<<<<< HEAD
    return image_folder 

# Helper background functions
def _background_build_or_load_db(current_folder):
    import streamlit as st
    import httpx
    import time
    from utils.logger import logger # Assuming logger is available

    INGESTION_SERVICE_URL = "http://localhost:8002/ingest_directory" 
    logger.info(f"Task 'build_db': Requesting ingestion for {current_folder} via {INGESTION_SERVICE_URL}")
    
    try:
        with httpx.Client(timeout=30.0) as client: # Added timeout
            response = client.post(INGESTION_SERVICE_URL, json={"directory_path": current_folder})
            response.raise_for_status() # Raise an exception for bad status codes
            logger.info(f"Task 'build_db': Ingestion request for {current_folder} successful. Response: {response.json()}")
            st.session_state.database_built = True # Signifies request was made
    except httpx.RequestError as e:
        logger.error(f"Task 'build_db': HTTP RequestError for {current_folder}: {e}")
        st.error(f"Error submitting folder for ingestion: {e}") # Show error on UI
        st.session_state.database_built = False
    except Exception as e:
        logger.error(f"Task 'build_db': Unexpected error for {current_folder}: {e}")
        st.error(f"Unexpected error: {e}")
        st.session_state.database_built = False

def _background_merge_folder(current_folder, new_folder):
    import streamlit as st
    import httpx
    import time
    from utils.logger import logger # Assuming logger is available

    INGESTION_SERVICE_URL = "http://localhost:8002/ingest_directory"
    logger.info(f"Task 'merge_db': Requesting ingestion for {new_folder} (to merge with {current_folder}) via {INGESTION_SERVICE_URL}")
    
    try:
        with httpx.Client(timeout=30.0) as client: # Added timeout
            # The service will handle deduplication or merging based on its Qdrant data
            response = client.post(INGESTION_SERVICE_URL, json={"directory_path": new_folder})
            response.raise_for_status()
            logger.info(f"Task 'merge_db': Ingestion request for {new_folder} successful. Response: {response.json()}")
            # No specific session state for merge completion, UI relies on is_running for now
    except httpx.RequestError as e:
        logger.error(f"Task 'merge_db': HTTP RequestError for {new_folder}: {e}")
        st.error(f"Error submitting folder for merging: {e}")
    except Exception as e:
        logger.error(f"Task 'merge_db': Unexpected error for {new_folder}: {e}")
        st.error(f"Unexpected error: {e}") 
=======
    return current_folder
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb
