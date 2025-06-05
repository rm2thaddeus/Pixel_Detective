import streamlit as st
import os
# import random # random was not used
from utils.logger import logger
from frontend.core.background_loader import background_loader # Use the global instance
from frontend.config import DEFAULT_IMAGES_PATH # Keep this for default folder
# from frontend.styles.style_injector import create_styled_button # Not used in this refactor
from frontend.components.accessibility import AccessibilityEnhancer

async def render_sidebar():
    """
    Render the sidebar components.
    All backend operations are now routed through background_loader, which uses service_api.py.
    """
    st.sidebar.header("🔧 Folder Processor")
    AccessibilityEnhancer.add_skip_navigation()
    
    # Initialize session state for image_folder if it doesn't exist (used by text_input)
    if 'image_folder' not in st.session_state:
        st.session_state.image_folder = DEFAULT_IMAGES_PATH

    # Main folder processing section
    try:
        current_folder = st.sidebar.text_input(
            "📁 Folder to process/load", 
            value=st.session_state.image_folder, 
            key="db_folder_main_processing" 
        ).strip().strip('"')
        st.session_state.image_folder = current_folder # Keep updating this for the text input

        if not os.path.exists(current_folder) and current_folder:
            st.sidebar.error("Selected folder path does not exist locally!")
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🚀 Process/Load Folder", key="process_folder_button"):
                if os.path.exists(current_folder):
                    logger.info(f"Process/Load Folder button clicked for: {current_folder}")
                    # asyncio.create_task(background_loader.start_loading_pipeline(current_folder)) # Non-blocking
                    await background_loader.start_loading_pipeline(current_folder) # Blocking for this sidebar render pass
                    # st.experimental_rerun() # Rerun to reflect immediate pending state
                else:
                    st.sidebar.error("Cannot process. Folder path is invalid.")
        with col2:
            if st.button("🔄 Reset Job", key="reset_job_button"):
                logger.info("Reset Job button clicked.")
                background_loader.reset_loading_state()
                # st.experimental_rerun()


        # Display status and logs using background_loader's properties
        loader_status = background_loader.progress.status
        loader_detail = background_loader.progress.current_detail
        loader_error = background_loader.progress.error_message
        loader_percent = background_loader.progress.percent_complete

        if background_loader.progress.is_loading:
            # If loading, try to update status. 
            # This call should be quick and update session state for the next rerun.
            try:
                await background_loader.check_ingestion_status()
                # Update local vars after check_ingestion_status, as it modifies session state
                loader_status = background_loader.progress.status
                loader_detail = background_loader.progress.current_detail
                loader_error = background_loader.progress.error_message
                loader_percent = background_loader.progress.percent_complete
            except Exception as e:
                logger.error(f"Error calling check_ingestion_status in sidebar: {e}", exc_info=True)
                st.sidebar.warning("Could not refresh job status.")


        if loader_status == "pending" or loader_status == "processing":
            st.sidebar.info(f"🔄 Status: {loader_status.capitalize()} ({loader_percent:.0f}%)")
            if loader_detail and loader_status == "processing": # Only show detail expander if there's something to show during processing
                 with st.sidebar.expander("Show Details/Logs", expanded=True):
                    st.text_area("Progress Details", value=loader_detail, height=200, disabled=True, key="bg_loader_detail_display")
            elif loader_status == "pending" and loader_detail:
                 st.sidebar.caption(loader_detail) # Show initial message if pending
        elif loader_status == "completed":
            st.sidebar.success(f"✅ Status: {loader_status.capitalize()} ({loader_percent:.0f}%)")
            if loader_detail:
                with st.sidebar.expander("Final Details/Summary", expanded=False):
                    st.text_area("Completion Details", value=loader_detail, height=100, disabled=True, key="bg_loader_complete_display")
        elif loader_status == "error":
            st.sidebar.error(f"❌ Status: {loader_status.capitalize()}")
            full_error_message = loader_error or loader_detail # Prioritize specific error_message
            if full_error_message:
                 with st.sidebar.expander("Error Details", expanded=True):
                    st.error(full_error_message)
        elif loader_status == "idle" and st.session_state.get("bg_loader_job_id") is None: # LOADING_JOB_ID_KEY from background_loader
            st.sidebar.caption("Status: Idle. Select a folder and click 'Process/Load Folder'.")
        
        # Merge folder functionality can be re-evaluated or simplified.
        # For now, focusing on the primary folder processing and log display.
        # The current background_loader handles one job at a time.
        # If merge is to be a separate concurrent job, background_loader would need changes
        # or a second instance/mechanism.
        # For simplicity, let's remove the merge UI for now to focus on the primary task.
        # If merge is essentially "ingest another directory to the same collection",
        # then the same "Process/Load Folder" button can be used with a different folder path.

        st.sidebar.markdown("---")
        st.sidebar.info("✨ All data operations are managed by backend services.")
        
    except Exception as e:
        logger.error(f"Error in sidebar rendering: {e}", exc_info=True)
        st.sidebar.error("Sidebar rendering error. Please check logs.")
        current_folder = st.session_state.get('image_folder', DEFAULT_IMAGES_PATH)

    AccessibilityEnhancer.inject_accessibility_styles()

    # The sidebar doesn't strictly need to return current_folder anymore unless app.py uses it directly from here.
    # app.py might get the folder from st.session_state.image_folder directly if needed.
    return st.session_state.get('image_folder', DEFAULT_IMAGES_PATH)

# Note: The direct asyncio.run() calls previously in this file for service_api were problematic
# in Streamlit's typical execution model. Using an async render_sidebar and relying on 
# background_loader's async methods (which manage their own session state updates) is a cleaner approach,
# assuming the calling context (e.g., in app.py) can await render_sidebar or manage an event loop.
# If app.py is purely synchronous, further adjustments for running these async tasks might be needed,
# potentially involving st.experimental_rerun() more strategically after task submissions.
# The `asyncio.create_task` approach for `start_loading_pipeline` could make it non-blocking,
# but then immediate feedback might require a quick `st.experimental_rerun()`.
# For now, `await background_loader.start_loading_pipeline()` makes it blocking for the current
# sidebar render pass, ensuring status is updated before the next element is drawn.
# `await background_loader.check_ingestion_status()` also updates state for the current render.

# Removed _background_process_folder, _background_merge_folder_with_backend,
# _background_build_or_load_db, and _background_merge_folder as they are
# replaced by _background_initiate_ingestion or were redundant/using direct httpx.
