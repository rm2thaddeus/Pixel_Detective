import streamlit as st
import os
import random
from utils.logger import logger
from components.task_orchestrator import submit, is_running
from core import service_api
import asyncio
from frontend.config import DEFAULT_IMAGES_PATH

def render_sidebar():
    """
    Render the sidebar components.
    
    Returns:
        str: The selected image folder path.
    """
    st.sidebar.header("🔧 Folder Processor")
    
    try:
        if not hasattr(st, 'session_state'):
            st.sidebar.warning("Sidebar not available yet.")
            return DEFAULT_IMAGES_PATH
            
        if 'image_folder' not in st.session_state:
            st.session_state.image_folder = DEFAULT_IMAGES_PATH

        current_folder = st.sidebar.text_input("📁 Folder to process", value=st.session_state.image_folder, key="db_folder").strip().strip('"')
        st.session_state.image_folder = current_folder
        
        if os.path.exists(current_folder):
            # This section needs an API call to check backend status for current_folder
            # For now, let's just show a button to trigger processing
            pass # Remove old db_manager checks here
        else:
            st.sidebar.error("Selected folder path does not exist locally!")
            # Do not proceed if folder doesn't exist.

    except Exception as e:
        logger.error(f"Error in sidebar rendering: {e}")
        st.sidebar.warning("Sidebar temporarily unavailable. Please refresh the page.")
        return DEFAULT_IMAGES_PATH

    # Button to trigger backend processing for the selected folder
    if st.sidebar.button("🚀 Process Folder with Backend") and os.path.exists(current_folder):
        # TempUiStateManager.init_search_state() # If purely UI state
        
        # Ensure _background_build_or_load_db calls service_api.ingest_directory
        scheduled = submit("process_folder_task", _background_process_folder, current_folder)
        if scheduled:
            st.sidebar.info(f"🚀 Backend processing started for: {current_folder}")
            st.session_state.folder_processing_started = True # UI state flag
        else:
            st.sidebar.warning("⚠️ Folder processing already in progress or failed to start.")

    # Poll folder processing status
    if st.session_state.get('folder_processing_started'):
        if is_running("process_folder_task"):
            st.sidebar.info("🔄 Backend processing in progress...")
        else:
            # This assumes the task sets 'database_built' or a similar flag upon completion.
            # Ideally, the task itself would update a more specific status via st.session_state
            # or we'd have an API to poll for job status from the ingestion service.
            if st.session_state.get('database_built', False): # 'database_built' is a bit of a misnomer now
                st.sidebar.success(f"✅ Backend processing complete for {current_folder}!")
            else:
                st.sidebar.error("Backend processing finished, but outcome unknown or failed. Check logs.")
            st.session_state.folder_processing_started = False
            # Removed direct QdrantDB instantiation from here

    # New folder merge - this logic seems okay as it uses _background_merge_folder
    # which should also be calling the backend ingestion service.
    new_folder_to_merge = st.sidebar.text_input("📁 New folder to merge with backend data", value="", key="new_folder").strip().strip('"')
    if st.sidebar.button("🔗 Merge New Folder with Backend") and new_folder_to_merge and os.path.exists(new_folder_to_merge):
        scheduled = submit("merge_folder_task", _background_merge_folder_with_backend, new_folder_to_merge) # current_folder here might be context for the backend.
        if scheduled:
            st.sidebar.info(f"🔗 Merge task for `{new_folder_to_merge}` started in background.")
            st.session_state.merge_folder_started = True
        else:
            st.sidebar.warning("⚠️ Merge task already running or failed to start.")

    if st.session_state.get('merge_folder_started'):
        if is_running("merge_folder_task"):
            st.sidebar.info("🔄 Folder merge in progress...")
        else:
            st.sidebar.success("✅ Folder merge task complete!") # Again, ideally poll backend for actual status
            st.session_state.merge_folder_started = False
            st.sidebar.info("Backend data potentially updated.")

    st.sidebar.info("✨ ML models and data are managed by backend services.")
    # Removed direct model_manager and device display.
    # Removed incremental indexing UI elements.

    return current_folder

# Helper background functions
# Ensure these use service_api.py for actual backend calls

def _background_process_folder(folder_path_to_process):
    """Triggers backend ingestion for a folder and updates session state."""
    logger.info(f"Task 'process_folder_task': Requesting ingestion for {folder_path_to_process} via service_api")
    st.session_state.folder_processing_status = "pending"
    try:
        # Ensure service_api.ingest_directory is an async function
        # The task_orchestrator.submit needs to handle running async functions.
        # If it doesn't, this needs a sync wrapper in service_api or asyncio.run here.
        # For this example, assuming task_orchestrator can run an async target or it's handled.
        
        # Correct approach: Call service_api, which contains the httpx logic
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response_data = loop.run_until_complete(service_api.ingest_directory(folder_path_to_process))
        loop.close()

        if response_data and not response_data.get("error"):
            job_id = response_data.get("job_id", "N/A")
            logger.info(f"Task 'process_folder_task': Backend ingestion started for {folder_path_to_process}. Job ID: {job_id}")
            st.session_state.folder_processing_status = "success" # Or "submitted_successfully"
            st.session_state.current_ingestion_job_id = job_id
            # UI should then poll get_ingestion_status(job_id)
        else:
            error_msg = response_data.get("detail", response_data.get("error", "Unknown error from backend"))
            logger.error(f"Task 'process_folder_task': Failed for {folder_path_to_process}. Error: {error_msg}")
            st.session_state.folder_processing_status = f"error: {error_msg}"
            # st.error(f"Folder processing error: {error_msg}") # Task orchestrator doesn't show st.error directly
    except Exception as e:
        logger.error(f"Task 'process_folder_task': Exception for {folder_path_to_process}: {e}", exc_info=True)
        st.session_state.folder_processing_status = f"exception: {str(e)}"

def _background_merge_folder_with_backend(new_folder_to_ingest):
    """Triggers backend ingestion for an additional folder."""
    logger.info(f"Task 'merge_folder_task': Requesting ingestion for {new_folder_to_ingest} via service_api")
    st.session_state.merge_folder_status = "pending"
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response_data = loop.run_until_complete(service_api.ingest_directory(new_folder_to_ingest)) # Assuming same endpoint
        loop.close()

        if response_data and not response_data.get("error"):
            job_id = response_data.get("job_id", "N/A")
            logger.info(f"Task 'merge_folder_task': Backend ingestion started for {new_folder_to_ingest}. Job ID: {job_id}")
            st.session_state.merge_folder_status = "success"
            st.session_state.current_merge_job_id = job_id
        else:
            error_msg = response_data.get("detail", response_data.get("error", "Unknown error from backend"))
            logger.error(f"Task 'merge_folder_task': Failed for {new_folder_to_ingest}. Error: {error_msg}")
            st.session_state.merge_folder_status = f"error: {error_msg}"
    except Exception as e:
        logger.error(f"Task 'merge_folder_task': Exception for {new_folder_to_ingest}: {e}", exc_info=True)
        st.session_state.merge_folder_status = f"exception: {str(e)}"

def _background_build_or_load_db(folder_path_to_process):
    # This function should primarily call service_api.ingest_directory
    logger.info(f"Task 'process_folder_task': Requesting ingestion for {folder_path_to_process}")
    st.session_state.database_built = False # Reset status
    try:
        # response = asyncio.run(service_api.ingest_directory(folder_path_to_process)) # If service_api is async
        # For synchronous task orchestrator, service_api might need sync wrappers or task orchestrator handles async.
        # Assuming service_api.ingest_directory is a blocking call or the task orchestrator handles async:
        
        # This httpx call should be inside service_api.py
        import httpx # Temporary direct use for illustration - MOVE TO service_api.py
        INGESTION_SERVICE_URL = f"{os.getenv('INGESTION_ORCHESTRATION_SERVICE_URL', 'http://localhost:8002/api/v1')}/ingest/"
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(INGESTION_SERVICE_URL, json={"directory_path": folder_path_to_process})
            response.raise_for_status()
            logger.info(f"Task 'process_folder_task': Ingestion request for {folder_path_to_process} successful. Response: {response.json()}")
            st.session_state.database_built = True # Signifies request was made and successful
            # The backend should return a job_id for proper status polling
            # st.session_state.ingestion_job_id = response.json().get("job_id")
    except Exception as e: # More specific exceptions for httpx.RequestError, httpx.HTTPStatusError
        logger.error(f"Task 'process_folder_task': Error for {folder_path_to_process}: {e}")
        st.error(f"Error submitting folder for ingestion: {e}") # Show error on UI
        # st.session_state.database_built remains False or set explicitly

def _background_merge_folder(main_context_folder, new_folder_to_ingest):
    # Similar to above, this should call a backend endpoint via service_api.py
    # The backend would handle how "merging" works (e.g., ingesting the new_folder)
    logger.info(f"Task 'merge_folder_task': Requesting ingestion for {new_folder_to_ingest}")
    try:
        import httpx # Temporary direct use for illustration - MOVE TO service_api.py
        INGESTION_SERVICE_URL = f"{os.getenv('INGESTION_ORCHESTRATION_SERVICE_URL', 'http://localhost:8002/api/v1')}/ingest/"
        with httpx.Client(timeout=60.0) as client:
            response = client.post(INGESTION_SERVICE_URL, json={"directory_path": new_folder_to_ingest})
            response.raise_for_status()
            logger.info(f"Task 'merge_folder_task': Ingestion request for {new_folder_to_ingest} successful. Response: {response.json()}")
            # No specific session state for merge completion here, UI relies on is_running for now.
            # Ideally, poll a job status from backend.
    except Exception as e:
        logger.error(f"Task 'merge_folder_task': Error for {new_folder_to_ingest}: {e}")
        st.error(f"Error submitting folder for merging: {e}") 
