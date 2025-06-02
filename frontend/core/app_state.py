# 🔄 Core State Management for Pixel Detective
# 📌 Purpose: Centralized state management for the 3-screen UX flow
# 🎯 Mission: Clear state transitions and session management

from enum import Enum
from typing import List, Optional
import streamlit as st
import time
from utils.logger import logger
from frontend.config import AppConfig, DEFAULT_IMAGES_PATH, DEFAULT_COLLECTION_NAME


class AppState(Enum):
    """Core application states for the 3-screen flow"""
    FAST_UI = "fast_ui"           # Screen 1: Instant UI, folder selection
    LOADING = "loading"           # Screen 2: Background processing
    ADVANCED_UI = "advanced_ui"   # Screen 3: Full featured interface
    ERROR = "error"              # Error recovery state


class AppStateManager:
    """
    Manages the global application state stored in Streamlit's session_state.
    This includes initialization of necessary keys and providing helper methods
    to access or modify state in a structured way.
    """

    @staticmethod
    def init_session_state():
        """
        Initializes the core session state variables if they don't exist.
        This should be called once at the beginning of the app.
        """
        logger.debug("Initializing AppStateManager session state...")

        # Core application state keys
        if 'app_config' not in st.session_state:
            st.session_state.app_config = AppConfig()
            logger.debug("Initialized 'app_config' in session state.")

        if 'current_screen' not in st.session_state:
            st.session_state.current_screen = "loading"  # Default to loading screen
            logger.debug("Initialized 'current_screen' to 'loading'.")
        
        if 'folder_path' not in st.session_state: # Previously managed by LazySessionManager.init_folder_state()
            st.session_state.folder_path = None # Or some default like DEFAULT_IMAGES_PATH if appropriate
            logger.debug(f"Initialized 'folder_path' to None (was {DEFAULT_IMAGES_PATH}).")

        if 'collection_name' not in st.session_state: # Previously LazySessionManager.init_folder_state()
            st.session_state.collection_name = DEFAULT_COLLECTION_NAME
            logger.debug(f"Initialized 'collection_name' to {DEFAULT_COLLECTION_NAME}.")
        
        # States related to backend API calls and data loading (managed by service_api and components)
        # No direct LazySessionManager calls needed here anymore.
        # Components should initialize their specific states as needed.

        # Example: Search related states (if previously in LazySessionManager.init_search_state())
        # These might be better initialized within the search components themselves or not at all globally
        # if they are transient.
        if 'search_query' not in st.session_state: # If this was part of init_search_state
            st.session_state.search_query = ""
        if 'search_results' not in st.session_state: # If this was part of init_search_state
            st.session_state.search_results = []
        
        # UI Interaction states (e.g., expanded sections, modal visibility)
        # These are typically managed by the components that use them.

        logger.info("Core session state initialization check complete via AppStateManager.")

    @staticmethod
    def update_app_config(new_config_values: dict):
        """Update the app configuration with new values"""
        current_config = st.session_state.get('app_config', AppConfig())
        updated_config = current_config.update(**new_config_values)
        st.session_state.app_config = updated_config

    @staticmethod
    def transition_to_loading(folder_path: str):
        """Transition from FAST_UI to LOADING"""
        st.session_state.app_state = AppState.LOADING
        st.session_state.folder_path = folder_path
        st.session_state.folder_selected = True
        
    @staticmethod
    def transition_to_advanced():
        """Transition from LOADING to ADVANCED_UI"""
        st.session_state.app_state = AppState.ADVANCED_UI
        
    @staticmethod
    def transition_to_error(error_message: str, can_retry: bool = True):
        """Transition to ERROR state"""
        st.session_state.app_state = AppState.ERROR
        st.session_state.error_message = error_message
        st.session_state.can_retry = can_retry
        
    @staticmethod
    def reset_to_fast_ui():
        """Reset app to initial state"""
        st.session_state.app_state = AppState.FAST_UI
        st.session_state.folder_selected = False
        st.session_state.ui_deps_loaded = False
        # st.session_state.models_loaded = False # Re-evaluate
        # st.session_state.database_ready = False # Re-evaluate
        st.session_state.error_message = ""
        st.session_state.image_files = []
    
    @staticmethod
    def get_current_state() -> AppState:
        """Get current app state"""
        return st.session_state.get('app_state', AppState.FAST_UI)
    
    @staticmethod
    def is_ready_for_advanced() -> bool:
        """Check if app is ready for advanced interface"""
        # This condition needs to be re-evaluated based on service availability
        # For now, let's assume UI dependencies are the main check.
        # Actual readiness might involve checking if backend services are responsive.
        return st.session_state.get('ui_deps_loaded', False)
                # and st.session_state.get('models_loaded', False) 
                # and st.session_state.get('database_ready', False) 