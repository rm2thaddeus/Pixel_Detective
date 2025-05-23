# 📂 File Path: /project_root/utils/lazy_session_state.py  
# 📌 Purpose: Progressive session state initialization to reduce startup overhead
# 🔄 Latest Changes: Created to implement lazy session state from next_sprint.md
# ⚙️ Key Logic: Initialize variables only when accessed, tab-specific state management
# 🧠 Reasoning: Reduces session state bloat from 10+ variables to only needed ones

import streamlit as st
from typing import Any, Callable, Optional

def get_or_init_session_var(key: str, default_factory: Callable[[], Any]) -> Any:
    """
    Get or initialize a session state variable on demand.
    
    Args:
        key: Session state key
        default_factory: Function that returns the default value
        
    Returns:
        The session state value
    """
    if key not in st.session_state:
        st.session_state[key] = default_factory()
    return st.session_state[key]

def get_or_init_simple(key: str, default_value: Any) -> Any:
    """
    Get or initialize a session state variable with a simple default value.
    
    Args:
        key: Session state key
        default_value: Default value to use
        
    Returns:
        The session state value
    """
    if key not in st.session_state:
        st.session_state[key] = default_value
    return st.session_state[key]

class LazySessionManager:
    """
    Manager for lazy session state initialization.
    Groups related state variables and initializes them only when the feature is accessed.
    """
    
    @staticmethod
    def init_search_state():
        """Initialize search-related state variables only when search tab is accessed."""
        get_or_init_simple('database_built', False)
        get_or_init_simple('images_data', None)
        get_or_init_simple('embeddings', None)
        get_or_init_simple('image_files', None)
        
    @staticmethod
    def init_game_state():
        """Initialize game-related state variables only when game tab is accessed."""
        get_or_init_simple('current_image_index', 0)
        get_or_init_simple('total_images', 0)
        get_or_init_simple('game_image_shown', False)
        get_or_init_simple('image_understanding', None)
        
    @staticmethod
    def init_metadata_state():
        """Initialize metadata-related state variables only when metadata is accessed."""
        get_or_init_session_var('text_metadata_expanded', dict)
        get_or_init_session_var('image_metadata_expanded', dict)
        
    @staticmethod
    def init_core_state():
        """Initialize only the most essential state variables at startup."""
        # Only initialize truly essential variables
        get_or_init_simple('active_tab', 0)
        
        # Model manager will be lazy-loaded when needed
        # Database manager will be lazy-loaded when needed
        
    @staticmethod
    def ensure_model_manager():
        """Ensure model manager exists (lazy initialization)."""
        if 'model_manager' not in st.session_state:
            # Import here to avoid circular imports
            from models.lazy_model_manager import LazyModelManager
            from utils.cuda_utils import log_cuda_memory_usage
            import torch
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            st.session_state.model_manager = LazyModelManager(device)
            log_cuda_memory_usage("After lazy model manager initialization")
            
        return st.session_state.model_manager
    
    @staticmethod
    def ensure_database_manager():
        """Ensure database manager exists (lazy initialization)."""
        if 'db_manager' not in st.session_state:
            # Import here to avoid circular imports
            from database.db_manager import DatabaseManager
            from utils.logger import logger
            
            model_manager = LazySessionManager.ensure_model_manager()
            logger.info("Creating database manager with lazy model manager")
            st.session_state.db_manager = DatabaseManager(model_manager)
            
        return st.session_state.db_manager

def clear_unused_session_state():
    """Clear session state variables that are no longer needed."""
    # Define variables that can be safely cleared when not in use
    clearable_vars = [
        'image_understanding',  # Clear after game session
        'embeddings',          # Clear when switching datasets
        'images_data'          # Clear when switching datasets
    ]
    
    cleared_count = 0
    for var in clearable_vars:
        if var in st.session_state:
            del st.session_state[var]
            cleared_count += 1
    
    if cleared_count > 0:
        st.info(f"Cleared {cleared_count} unused session variables to free memory")

def get_session_memory_usage():
    """Get an estimate of session state memory usage for debugging."""
    import sys
    
    total_size = 0
    large_objects = []
    
    for key, value in st.session_state.items():
        size = sys.getsizeof(value)
        total_size += size
        
        if size > 1024 * 1024:  # Objects larger than 1MB
            large_objects.append((key, size / 1024 / 1024))  # Convert to MB
    
    return {
        "total_mb": total_size / 1024 / 1024,
        "variable_count": len(st.session_state),
        "large_objects": large_objects
    } 