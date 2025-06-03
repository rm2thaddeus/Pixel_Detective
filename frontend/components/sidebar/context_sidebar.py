import streamlit as st
import os
# import random # random was not used
from utils.logger import logger
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
    if 'folder_processing_status' not in st.session_state:
        st.session_state.folder_processing_status = "idle"
    if 'merge_folder_status' not in st.session_state:
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
            key="db_folder_main_processing"
        ).strip().strip('"')
        st.session_state.image_folder = current_folder
        
        if not os.path.exists(current_folder) and current_folder:
            st.sidebar.error("Selected folder path does not exist locally!")
        
        # Button to trigger backend processing for the selected folder
        if st.sidebar.button("🚀 Process Selected Folder via Backend") and os.path.exists(current_folder):
            st.session_state.folder_processing_status = "pending"
            st.session_state.current_ingestion_job_id = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response_data = loop.run_until_complete(service_api.ingest_directory(current_folder))
                loop.close()
                if response_data and not response_data.get("error"):
                    job_id = response_data.get("job_id")
                    st.session_state.current_ingestion_job_id = job_id
                    msg = response_data.get("message", "Ingestion process started.")
                    logger.info(f"Backend ingestion successfully initiated for {current_folder}. Job ID: {job_id}. Message: {msg}")
                    st.session_state.folder_processing_status = f"success: {msg}"
                else:
                    error_msg = response_data.get("detail", response_data.get("error", "Unknown error from backend during ingestion initiation."))
                    logger.error(f"Failed for {current_folder}. Error: {error_msg}")
                    st.session_state.folder_processing_status = f"error: {error_msg}"
                    st.session_state.current_ingestion_job_id = None
            except Exception as e:
                logger.error(f"Exception during ingestion initiation for {current_folder}: {e}", exc_info=True)
                st.session_state.folder_processing_status = f"error: Exception - {str(e)}"
                st.session_state.current_ingestion_job_id = None

        # Display status for the main folder processing
        if st.session_state.folder_processing_status.startswith("pending"):
            st.sidebar.info(f"🔄 Backend processing in progress for: {current_folder}...")
        elif st.session_state.folder_processing_status.startswith("success"):
            job_id_info = f"(Job ID: {st.session_state.current_ingestion_job_id})" if st.session_state.current_ingestion_job_id else ""
            st.sidebar.success(f"✅ Backend processing initiated for {current_folder}. {job_id_info}. Check main screen or logs for completion status.")
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
            st.session_state.merge_folder_status = "pending"
            st.session_state.current_merge_job_id = None
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response_data = loop.run_until_complete(service_api.ingest_directory(new_folder_to_merge))
                loop.close()
                if response_data and not response_data.get("error"):
                    job_id = response_data.get("job_id")
                    st.session_state.current_merge_job_id = job_id
                    msg = response_data.get("message", "Merge process started.")
                    logger.info(f"Backend merge successfully initiated for {new_folder_to_merge}. Job ID: {job_id}. Message: {msg}")
                    st.session_state.merge_folder_status = f"success: {msg}"
                else:
                    error_msg = response_data.get("detail", response_data.get("error", "Unknown error from backend during merge initiation."))
                    logger.error(f"Failed for {new_folder_to_merge}. Error: {error_msg}")
                    st.session_state.merge_folder_status = f"error: {error_msg}"
                    st.session_state.current_merge_job_id = None
            except Exception as e:
                logger.error(f"Exception during merge initiation for {new_folder_to_merge}: {e}", exc_info=True)
                st.session_state.merge_folder_status = f"error: Exception - {str(e)}"
                st.session_state.current_merge_job_id = None

        # Display status for the merge folder processing
        if st.session_state.merge_folder_status.startswith("pending"):
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
        current_folder = st.session_state.get('image_folder', DEFAULT_IMAGES_PATH)

    return current_folder

# Removed _background_process_folder, _background_merge_folder_with_backend,
# _background_build_or_load_db, and _background_merge_folder as they are
# replaced by _background_initiate_ingestion or were redundant/using direct httpx.
