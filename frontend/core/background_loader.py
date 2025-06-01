# frontend/core/background_loader.py
import streamlit as st
import time
import logging
from typing import Optional
import asyncio # New import

# Assuming service_api.py is in frontend.core
from core import service_api
# Assuming app_state.py is in frontend.core (AppStateManager might be used later for transitions)
# from frontend.core.app_state import AppStateManager 

logger = logging.getLogger(__name__)

# Keys for session state, centralized here for clarity
LOADING_JOB_ID_KEY = "bg_loader_job_id"
LOADING_STATUS_KEY = "bg_loader_status"  # e.g., "idle", "pending", "processing", "completed", "error"
LOADING_PERCENT_KEY = "bg_loader_percent"
LOADING_DETAIL_KEY = "bg_loader_detail"
LOADING_ERROR_MSG_KEY = "bg_loader_error_message"


class BackgroundLoaderProgress:
    """Provides properties to access loading progress from session state."""

    @property
    def is_loading(self) -> bool:
        """True if an ingestion job is actively pending or processing."""
        status = st.session_state.get(LOADING_STATUS_KEY, "idle")
        return status in ["pending", "processing"]

    @property
    def percent_complete(self) -> float:
        """Current progress percentage (0.0 to 100.0)."""
        return float(st.session_state.get(LOADING_PERCENT_KEY, 0.0))

    @property
    def current_detail(self) -> str:
        """Current detailed status message."""
        return str(st.session_state.get(LOADING_DETAIL_KEY, "Initializing..."))
    
    @property
    def error_message(self) -> Optional[str]:
        """Error message if the loading status is 'error'."""
        if st.session_state.get(LOADING_STATUS_KEY) == "error":
            return st.session_state.get(LOADING_ERROR_MSG_KEY)
        return None
    
    @property
    def status(self) -> str:
        """Returns the raw status string (idle, pending, processing, completed, error)."""
        return str(st.session_state.get(LOADING_STATUS_KEY, "idle"))


class BackgroundLoader:
    """
    Manages the background ingestion process by interacting with backend services
    via service_api.py. Updates Streamlit session state with progress.
    """
    def __init__(self):
        self.progress = BackgroundLoaderProgress()
        self._initialize_session_state_keys()

    def _initialize_session_state_keys(self):
        """Ensure all necessary session state keys are initialized."""
        default_states = {
            LOADING_JOB_ID_KEY: None,
            LOADING_STATUS_KEY: "idle",
            LOADING_PERCENT_KEY: 0.0,
            LOADING_DETAIL_KEY: "",
            LOADING_ERROR_MSG_KEY: None,
        }
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    # This method is called from synchronous Streamlit interactions (button clicks in loading_screen.py)
    # So, it needs to bridge the sync-async gap if it calls async service_api functions.
    # Option 1: Make it async and have callers use asyncio.run() or st.experimental_rerun().
    # Option 2: Run the async parts in a separate thread or use asyncio.gather() if possible.
    # For Streamlit, often the simplest is to make the calling chain async if possible.
    # Since loading_screen.render() is now async, this can be async too.
    async def start_loading_pipeline(self, folder_path: str): # Changed to async def
        """Initiates the ingestion pipeline for the given folder path."""
        if self.progress.is_loading and st.session_state.get(LOADING_JOB_ID_KEY):
            logger.info(f"Ingestion job {st.session_state[LOADING_JOB_ID_KEY]} already in progress. Not starting new one.")
            return

        logger.info(f"Requesting to start ingestion pipeline for folder: {folder_path}")
        self.reset_loading_state()
        st.session_state[LOADING_STATUS_KEY] = "pending"
        st.session_state[LOADING_DETAIL_KEY] = f"Sending request to ingest {folder_path}..."
        
        # API call is now async
        api_response = await service_api.ingest_directory(path=folder_path) # await

        if isinstance(api_response, dict) and api_response.get("error"):
            error_msg = f"Failed to start ingestion: {api_response['error']}"
            logger.error(error_msg)
            st.session_state[LOADING_STATUS_KEY] = "error"
            st.session_state[LOADING_ERROR_MSG_KEY] = error_msg
            st.session_state[LOADING_DETAIL_KEY] = "Error: Unexpected server response."
            return # Return early on error

        # Perform an immediate status check to get initial progress if job_id was received
        if st.session_state.get(LOADING_JOB_ID_KEY):
            await self.check_ingestion_status() # await

    # This method is also called from async loading_screen.render()
    async def check_ingestion_status(self): # Changed to async def
        """Checks the status of the current ingestion job and updates session state."""
        job_id = st.session_state.get(LOADING_JOB_ID_KEY)
        
        if not job_id or st.session_state.get(LOADING_STATUS_KEY) not in ["pending", "processing"]:
            return

        logger.debug(f"Checking status for ingestion job_id: {job_id}")
        # API call is now async
        api_response = await service_api.get_ingestion_status(job_id=job_id) # await

        if isinstance(api_response, dict) and api_response.get("error"):
            status_code = api_response.get('status_code')
            error_detail = api_response['error']
            logger.error(f"Error checking ingestion status for job {job_id} (HTTP {status_code}): {error_detail}")
            # If job not found, it's a definitive error for this job ID.
            if status_code == 404:
                 st.session_state[LOADING_STATUS_KEY] = "error"
                 st.session_state[LOADING_ERROR_MSG_KEY] = f"Ingestion job {job_id} not found on server."
                 st.session_state[LOADING_DETAIL_KEY] = "Error: Job not found."
            else:
                # For other errors, keep current status but update detail to show transient issue
                st.session_state[LOADING_DETAIL_KEY] = f"Error fetching status: {error_detail} (HTTP {status_code})"

        elif isinstance(api_response, dict):
            status = api_response.get("status", "unknown").lower()
            progress_percent = api_response.get("progress", st.session_state.get(LOADING_PERCENT_KEY, 0.0))
            detail_message = api_response.get("message", api_response.get("details", "")) # Use message or details
            
            st.session_state[LOADING_PERCENT_KEY] = float(progress_percent) if progress_percent is not None else st.session_state[LOADING_PERCENT_KEY]
            st.session_state[LOADING_DETAIL_KEY] = detail_message if detail_message else f"Job status: {status}"

            if status == "completed":
                logger.info(f"Ingestion job {job_id} reported as COMPLETED.")
                st.session_state[LOADING_STATUS_KEY] = "completed"
                st.session_state[LOADING_DETAIL_KEY] = detail_message or "Processing complete!"
                st.session_state[LOADING_PERCENT_KEY] = 100.0
            elif status in ["failed", "error"]:
                logger.error(f"Ingestion job {job_id} reported as FAILED/ERROR. API Response: {api_response}")
                st.session_state[LOADING_STATUS_KEY] = "error"
                st.session_state[LOADING_ERROR_MSG_KEY] = detail_message or "Ingestion failed due to an unspecified server error."
                st.session_state[LOADING_DETAIL_KEY] = f"Error: {st.session_state[LOADING_ERROR_MSG_KEY]}"
            elif status in ["pending", "processing", "running"]: # "running" or other active states
                st.session_state[LOADING_STATUS_KEY] = "processing" # Normalize to "processing" for UI
                logger.debug(f"Job {job_id} is {status}. Progress: {st.session_state[LOADING_PERCENT_KEY]}%. Detail: {st.session_state[LOADING_DETAIL_KEY]}")
            else: 
                logger.warning(f"Job {job_id} has UNKNOWN status '{status}'. API Response: {api_response}")
                st.session_state[LOADING_DETAIL_KEY] = f"Current status: {status} (Waiting for update)"
                # Keep current "processing" status unless explicitly failed/completed
                if st.session_state[LOADING_STATUS_KEY] not in ["error", "completed"]:
                     st.session_state[LOADING_STATUS_KEY] = "processing" 
        else:
            logger.error(f"Unexpected API response type when checking status for job {job_id}: {type(api_response)}. Response: {api_response}")
            # Keep current status, but indicate an issue with status retrieval in details.
            st.session_state[LOADING_DETAIL_KEY] = "Error: Could not retrieve valid status from server."


    def reset_loading_state(self):
        """Resets all loading-related session state variables to their defaults."""
        logger.info("Resetting background_loader session state.")
        st.session_state[LOADING_JOB_ID_KEY] = None
        st.session_state[LOADING_STATUS_KEY] = "idle"
        st.session_state[LOADING_PERCENT_KEY] = 0.0
        st.session_state[LOADING_DETAIL_KEY] = ""
        st.session_state[LOADING_ERROR_MSG_KEY] = None

# Global instance to be imported by other modules like screen_renderer
background_loader = BackgroundLoader() 