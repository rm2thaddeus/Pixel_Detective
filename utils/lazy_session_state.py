# 📂 File Path: /project_root/utils/lazy_session_state.py  
# 📌 Purpose: TRUE lazy session state management - models load ONLY when explicitly needed
# 🚀 PERFORMANCE REVOLUTION: Zero model loading until user requests processing
# ⚡ Key Innovation: Session state without any model initialization
# 🧠 Philosophy: Session management ≠ Model loading

import streamlit as st
import sys
import gc
from typing import Dict, Any, Optional, Callable

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

def get_session_memory_usage():
    """
    Calculate memory usage of session state variables.
    
    Returns:
        dict: Memory usage information
    """
    total_size = 0
    variable_count = 0
    large_objects = []
    
    try:
        for key, value in st.session_state.items():
            variable_count += 1
            try:
                size = sys.getsizeof(value)
                total_size += size
                
                # Track large objects (>1MB)
                if size > 1024 * 1024:
                    large_objects.append((key, size / 1024 / 1024))
                    
            except (TypeError, AttributeError):
                # Some objects don't support getsizeof
                pass
    except Exception:
        pass
    
    return {
        'total_mb': total_size / 1024 / 1024,
        'variable_count': variable_count,
        'large_objects': large_objects
    }

def clear_unused_session_state():
    """Clear session state variables that are safe to remove."""
    safe_to_remove = []
    
    for key in st.session_state.keys():
        # Don't remove core app state
        if key not in ['app_initialized', 'folder_path', 'database_built', 
                      'start_processing', 'show_advanced', 'processing_config']:
            # Check if it's a large object we can safely remove
            try:
                size = sys.getsizeof(st.session_state[key])
                if size > 10 * 1024 * 1024:  # >10MB objects
                    safe_to_remove.append(key)
            except (TypeError, AttributeError):
                pass
    
    # Remove large objects
    for key in safe_to_remove:
        del st.session_state[key]
    
    # Force garbage collection
    gc.collect()

class LazySessionManager:
    """
    TRUE lazy session state manager - models load ONLY when explicitly requested.
    
    Key principles:
    - init_core_state() does NOT load any models
    - Models load only when user clicks "Start Processing"
    - Session state tracks UI state, not model state
    - Zero heavy imports during initialization
    """
    
    @staticmethod
    def init_core_state():
        """
        Initialize ONLY core UI session state - NO MODEL LOADING.
        
        This function is called at app startup and must be lightning fast.
        It sets up session state for UI tracking only.
        """
        # Initialize minimal UI state tracking
        if 'lazy_session_initialized' not in st.session_state:
            st.session_state.lazy_session_initialized = True
            
            # UI state only - no models!
            st.session_state.models_loaded = False
            st.session_state.database_connected = False
            st.session_state.processing_active = False
            
            # Folder and processing state
            if 'folder_path' not in st.session_state:
                st.session_state.folder_path = ""
            if 'database_built' not in st.session_state:
                st.session_state.database_built = False
        
        # Important: Do NOT load any models here!
        # Models will be loaded only when user explicitly starts processing
    
    @staticmethod
    def init_search_state():
        """Initialize search-related state variables (lightweight, no models)."""
        get_or_init_simple('database_built', False)
        get_or_init_simple('images_data', None)
        get_or_init_simple('embeddings', None)
        get_or_init_simple('image_files', None)
        
    @staticmethod
    def init_game_state():
        """Initialize game-related state variables (lightweight, no models)."""
        get_or_init_simple('current_image_index', 0)
        get_or_init_simple('total_images', 0)
        get_or_init_simple('game_image_shown', False)
        get_or_init_simple('image_understanding', None)
        
    @staticmethod
    def init_metadata_state():
        """Initialize metadata-related state variables (lightweight, no models)."""
        get_or_init_session_var('text_metadata_expanded', dict)
        get_or_init_session_var('image_metadata_expanded', dict)
        
    @staticmethod
    def ensure_model_manager():
        """
        Load model manager ONLY when explicitly called.
        This should only happen when user clicks 'Start Processing'.
        """
        if 'model_manager' not in st.session_state:
            # Show clear feedback that models are loading NOW
            with st.spinner("🤖 Loading AI models for the first time..."):
                progress = st.progress(0)
                
                # Import heavy modules
                progress.progress(20)
                from models.lazy_model_manager import LazyModelManager
                
                progress.progress(40)
                # Only import torch when actually needed
                import torch
                
                progress.progress(60)
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                
                progress.progress(80)
                # Create model manager (but models still load on demand)
                st.session_state.model_manager = LazyModelManager(device)
                
                progress.progress(100)
                progress.empty()
                
            st.session_state.models_loaded = True
            st.success("✅ AI models ready for processing!")
            
        return st.session_state.model_manager
    
    @staticmethod
    def ensure_database_manager():
        """
        Load database manager ONLY when explicitly called.
        This should only happen after model manager is loaded.
        """
        if 'db_manager' not in st.session_state:
            with st.spinner("💾 Connecting to database..."):
                # Import database modules only when needed
                from database.db_manager import DatabaseManager
                from utils.logger import logger
                
                # Ensure model manager exists first
                model_manager = LazySessionManager.ensure_model_manager()
                
                logger.info("Creating database manager with lazy model manager")
                st.session_state.db_manager = DatabaseManager(model_manager)
                st.session_state.database_connected = True
                
            st.success("✅ Database connection established!")
            
        return st.session_state.db_manager
    
    @staticmethod
    def get_processing_status():
        """Get current processing status without triggering any loads."""
        return {
            'models_loaded': st.session_state.get('models_loaded', False),
            'database_connected': st.session_state.get('database_connected', False),
            'processing_active': st.session_state.get('processing_active', False),
            'database_built': st.session_state.get('database_built', False)
        }
    
    @staticmethod
    def cleanup_heavy_objects():
        """Clean up heavy objects while preserving essential state."""
        cleanup_keys = []
        
        # Identify heavy objects
        for key in st.session_state.keys():
            if key.startswith('temp_') or key.endswith('_cache'):
                cleanup_keys.append(key)
        
        # Remove them
        for key in cleanup_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        # Force garbage collection
        gc.collect()
        
        return len(cleanup_keys)

# ===== PERFORMANCE UTILITIES =====

def is_heavy_module_loaded() -> bool:
    """Check if heavy modules (torch, models) have been loaded."""
    return 'model_manager' in st.session_state or 'torch' in sys.modules

def get_startup_metrics() -> Dict[str, Any]:
    """Get metrics about app startup performance."""
    import time
    
    return {
        'session_variables': len(st.session_state.keys()),
        'heavy_modules_loaded': is_heavy_module_loaded(),
        'memory_usage_mb': get_session_memory_usage()['total_mb'],
        'torch_available': 'torch' in sys.modules,
        'models_loaded': st.session_state.get('models_loaded', False)
    }

def log_performance_metrics():
    """Log current performance metrics."""
    metrics = get_startup_metrics()
    
    if 'logger' in globals():
        logger.info(f"Performance metrics: {metrics}")
    else:
        print(f"Performance metrics: {metrics}")

# ===== MIGRATION UTILITIES =====

def migrate_from_old_session():
    """Migrate from old session state structure if needed."""
    # Remove old heavy objects if they exist
    old_keys = ['old_model_manager', 'clip_model', 'blip_model', 'embedding_cache']
    
    for key in old_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Ensure new lazy structure
    LazySessionManager.init_core_state() 