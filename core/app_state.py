# 🔄 Core State Management for Pixel Detective
# 📌 Purpose: Centralized state management for the 3-screen UX flow
# 🎯 Mission: Clear state transitions and session management

from enum import Enum
from typing import List, Optional
import streamlit as st
import time


class AppState(Enum):
    """Core application states for the 3-screen flow"""
    FAST_UI = "fast_ui"           # Screen 1: Instant UI, folder selection
    LOADING = "loading"           # Screen 2: Background processing
    ADVANCED_UI = "advanced_ui"   # Screen 3: Full featured interface
    ERROR = "error"              # Error recovery state


class AppStateManager:
    """Centralized state management for the 3-screen flow"""
    
    @staticmethod
    def init_session_state():
        """Initialize all session state variables with proper defaults"""
        # CRITICAL: Initialize lazy session manager first
        from utils.lazy_session_state import LazySessionManager
        LazySessionManager.init_core_state()
        
        # Core app state
        if 'app_state' not in st.session_state:
            st.session_state.app_state = AppState.FAST_UI
        
        # User inputs
        if 'folder_path' not in st.session_state:
            st.session_state.folder_path = ""
        if 'folder_selected' not in st.session_state:
            st.session_state.folder_selected = False
        
        # Background loading tracking (these are updated from background loader results)
        if 'ui_deps_loaded' not in st.session_state:
            st.session_state.ui_deps_loaded = False
        if 'models_loaded' not in st.session_state:
            st.session_state.models_loaded = False
        if 'database_ready' not in st.session_state:
            st.session_state.database_ready = False
        
        # Core objects (loaded when needed)
        if 'model_manager' not in st.session_state:
            st.session_state.model_manager = None
        if 'db_manager' not in st.session_state:
            st.session_state.db_manager = None
        if 'image_files' not in st.session_state:
            st.session_state.image_files = []
        
        # Error handling
        if 'error_message' not in st.session_state:
            st.session_state.error_message = ""
        if 'can_retry' not in st.session_state:
            st.session_state.can_retry = True
    
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
        st.session_state.models_loaded = False
        st.session_state.database_ready = False
        st.session_state.error_message = ""
        st.session_state.image_files = []
    
    @staticmethod
    def get_current_state() -> AppState:
        """Get current app state"""
        return st.session_state.get('app_state', AppState.FAST_UI)
    
    @staticmethod
    def is_ready_for_advanced() -> bool:
        """Check if app is ready for advanced interface"""
        return (st.session_state.get('ui_deps_loaded', False) and
                st.session_state.get('models_loaded', False) and 
                st.session_state.get('database_ready', False)) 