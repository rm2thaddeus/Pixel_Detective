import streamlit as st
import os
# import random # random was not used
from utils.logger import logger
from components.task_orchestrator import submit, is_running
from core import service_api # Ensure this is imported
import asyncio
from frontend.config import DEFAULT_IMAGES_PATH # Keep this for default folder

def render_sidebar():
    """
    Render the sidebar components.
    All backend operations are now routed through service_api.py.
    """
    st.sidebar.header("🔧 Folder Processor")
    
    # Initialize session state keys if they don't exist
    if 'image_folder' not in st.session_state:
        st.session_state.image_folder = DEFAULT_IMAGES_PATH
    if 'folder_processing_status' not in st.session_state: # tracks status of current_folder processing
        st.session_state.folder_processing_status = "idle" # idle, pending, success, error: <msg>
    if 'merge_folder_status' not in st.session_state: # tracks status of new_folder_to_merge processing
        st.session_state.merge_folder_status = "idle"
    if 'current_ingestion_job_id' not in st.session_state:
        st.session_state.current_ingestion_job_id = None
    if 'current_merge_job_id' not in st.session_state:
        st.session_state.current_merge_job_id = None

    try:
        # Folder selection for processing
        current_folder = st.sidebar.text_input(
            "📁 Folder to process", 
            value=st.session_state.image_folder, 
            key="db_folder_main_processing" # Changed key to avoid conflict if old one lingered
        ).strip().strip('"')
        st.session_state.image_folder = current_folder

        if not os.path.exists(current_folder) and current_folder: # Only show error if path is non-empty and invalid
            st.sidebar.error("Selected folder path does not exist locally!")
        
        # Button to trigger backend processing for the selected folder
        if st.sidebar.button("🚀 Process Selected Folder via Backend") and os.path.exists(current_folder):
            if not is_running("process_folder_task"):
                logger.info(f"UI: Submitting 'process_folder_task' for {current_folder}")
                # Reset status before starting
                st.session_state.folder_processing_status = "pending"
                st.session_state.current_ingestion_job_id = None 
                submit("process_folder_task", _background_initiate_ingestion, current_folder, "main_folder")
                # UI will update based on is_running and folder_processing_status
            else:
                st.sidebar.warning("⚠️ Folder processing task already in progress.")

        # Display status for the main folder processing
        if is_running("process_folder_task"):
            st.sidebar.info(f"🔄 Backend processing in progress for: {current_folder}...")
        elif st.session_state.folder_processing_status.startswith("success"):
            job_id_info = f"(Job ID: {st.session_state.current_ingestion_job_id})" if st.session_state.current_ingestion_job_id else ""
            st.sidebar.success(f"✅ Backend processing initiated for {current_folder}. {job_id_info}. Check main screen or logs for completion status.")
            # Consider resetting status to idle after showing success message once, or add a "clear status" button
            # st.session_state.folder_processing_status = "idle" # Or keep success until next action
        elif st.session_state.folder_processing_status.startswith("error"):
            st.sidebar.error(f"❌ Error processing {current_folder}: {st.session_state.folder_processing_status.split(': ', 1)[-1]}")
        
        # --- New folder merge ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("➕ Merge Another Folder")
        new_folder_to_merge = st.sidebar.text_input(
            "📁 New folder to merge with backend data", 
            value="", 
            key="new_folder_to_merge_input"
        ).strip().strip('"')

        if not os.path.exists(new_folder_to_merge) and new_folder_to_merge:
             st.sidebar.error("Merge folder path does not exist locally!")

        if st.sidebar.button("🔗 Merge New Folder via Backend") and new_folder_to_merge and os.path.exists(new_folder_to_merge):
            if not is_running("merge_folder_task"):
                logger.info(f"UI: Submitting 'merge_folder_task' for {new_folder_to_merge}")
                st.session_state.merge_folder_status = "pending"
                st.session_state.current_merge_job_id = None
                submit("merge_folder_task", _background_initiate_ingestion, new_folder_to_merge, "merge_folder")
            else:
                st.sidebar.warning("⚠️ Merge folder task already in progress.")

        # Display status for the merge folder processing
        if is_running("merge_folder_task"):
            st.sidebar.info(f"🔄 Merging {new_folder_to_merge} in progress...")
        elif st.session_state.merge_folder_status.startswith("success"):
            job_id_info = f"(Job ID: {st.session_state.current_merge_job_id})" if st.session_state.current_merge_job_id else ""
            st.sidebar.success(f"✅ Merge initiated for {new_folder_to_merge}. {job_id_info}. Check main screen or logs for completion.")
        elif st.session_state.merge_folder_status.startswith("error"):
            st.sidebar.error(f"❌ Error merging {new_folder_to_merge}: {st.session_state.merge_folder_status.split(': ', 1)[-1]}")

        st.sidebar.markdown("---")
        st.sidebar.info("✨ ML models and data are managed by backend services. All operations here trigger backend tasks.")
        
    except Exception as e:
        logger.error(f"Error in sidebar rendering: {e}", exc_info=True)
        st.sidebar.error("Sidebar rendering error. Please check logs.")
        # Fallback or ensure current_folder is defined for return
        current_folder = st.session_state.get('image_folder', DEFAULT_IMAGES_PATH)

    return current_folder


def _background_initiate_ingestion(folder_path_to_process: str, task_type: str):
    """
    Background task to call service_api.ingest_directory and update session state.
    Args:
        folder_path_to_process: The path to the folder to ingest.
        task_type: "main_folder" or "merge_folder" to update correct session state status.
    """
    status_key = "folder_processing_status" if task_type == "main_folder" else "merge_folder_status"
    job_id_key = "current_ingestion_job_id" if task_type == "main_folder" else "current_merge_job_id"

    logger.info(f"Task '{task_type}': Requesting ingestion for {folder_path_to_process} via service_api")
    st.session_state[status_key] = "pending" # Should be set by caller, but good to ensure
    
    try:
        # service_api.ingest_directory is async, run it in an event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response_data = loop.run_until_complete(service_api.ingest_directory(folder_path_to_process))
        loop.close()

        if response_data and not response_data.get("error"):
            job_id = response_data.get("job_id") # Get job_id if available
            st.session_state[job_id_key] = job_id
            msg = response_data.get("message", "Ingestion process started.")
            logger.info(f"Task '{task_type}': Backend ingestion successfully initiated for {folder_path_to_process}. Job ID: {job_id}. Message: {msg}")
            st.session_state[status_key] = f"success: {msg}"
            # The UI can then use background_loader.check_ingestion_status(job_id) if needed on the main screen
        else:
            error_msg = response_data.get("detail", response_data.get("error", "Unknown error from backend during ingestion initiation."))
            logger.error(f"Task '{task_type}': Failed for {folder_path_to_process}. Error: {error_msg}")
            st.session_state[status_key] = f"error: {error_msg}"
            st.session_state[job_id_key] = None
            
    except Exception as e:
        logger.error(f"Task '{task_type}': Exception during ingestion initiation for {folder_path_to_process}: {e}", exc_info=True)
        st.session_state[status_key] = f"error: Exception - {str(e)}"
        st.session_state[job_id_key] = None

# Removed _background_process_folder, _background_merge_folder_with_backend,
# _background_build_or_load_db, and _background_merge_folder as they are
# replaced by _background_initiate_ingestion or were redundant/using direct httpx.
