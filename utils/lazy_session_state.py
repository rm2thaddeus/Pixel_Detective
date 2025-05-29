# 📂 File Path: /project_root/utils/lazy_session_state.py  
# 📌 Purpose: TRUE lazy session state management - models load ONLY when explicitly needed
# 🚀 PERFORMANCE REVOLUTION: Zero model loading until user requests processing
# ⚡ Key Innovation: Session state without any model initialization
# 🧠 Philosophy: Session management ≠ Model loading

import streamlit as st
import sys
import gc
from typing import Dict, Any, Optional, Callable

# Import logger for error handling
try:
    from utils.logger import logger
except ImportError:
    # Fallback if logger is not available
    import logging
    logger = logging.getLogger(__name__)

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
        Get the OptimizedModelManager instance.
        This relies on OptimizedModelManager being a cached resource.
        
        Returns:
            OptimizedModelManager: A valid model manager instance
            
        Raises:
            RuntimeError: If model manager cannot be created
        """
        try:
            from core.optimized_model_manager import get_optimized_model_manager
            model_manager = get_optimized_model_manager()
            
            if model_manager is None:
                raise RuntimeError("get_optimized_model_manager() returned None")
            
            # OptimizedModelManager has its own checks. 'device' is a basic attribute.
            if not hasattr(model_manager, 'device'): 
                 logger.warning("OptimizedModelManager instance seems basic or not fully initialized.")

            # OptimizedModelManager manages its own loading state. 
            # We can check if it's ready or if models are preloading.
            if hasattr(model_manager, 'are_all_models_ready') and model_manager.are_all_models_ready():
                st.session_state.models_loaded = True
            elif hasattr(model_manager, 'get_loading_status'):
                status = model_manager.get_loading_status()
                st.session_state.models_loaded = status.get('all_ready', False)
            else:
                 st.session_state.models_loaded = False # Fallback

            logger.info("OptimizedModelManager instance obtained via get_optimized_model_manager.")
            return model_manager
            
        except Exception as e:
            error_msg = f"Failed to get OptimizedModelManager: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)
    
    @staticmethod
    def ensure_database_manager():
        """
        Load database manager ONLY when explicitly called.
        This should only happen after model manager is loaded.
        
        Returns:
            DatabaseManager: A valid database manager instance
            
        Raises:
            RuntimeError: If database manager cannot be created after all attempts
        """
        if st.session_state.get('db_manager') is None:
            try:
                # Import database modules only when needed
                from database.db_manager import DatabaseManager
                
                logger.info("Creating database manager...")
                
                # Ensure model manager exists first
                model_manager = LazySessionManager.ensure_model_manager()
                
                if model_manager is None:
                    raise RuntimeError("Model manager is None - cannot create database manager")
                
                logger.info("Creating database manager with lazy model manager")
                db_manager = DatabaseManager(model_manager)
                
                if db_manager is None:
                    raise RuntimeError("DatabaseManager constructor returned None")
                
                # Test the database manager to ensure it's working
                try:
                    # Simple test to verify the database manager is functional
                    test_result = db_manager.database_exists(".")
                    logger.info(f"Database manager test successful: database_exists('.') = {test_result}")
                except Exception as test_error:
                    logger.error(f"Database manager test failed: {test_error}")
                    raise RuntimeError(f"Database manager is not functional: {test_error}")
                
                st.session_state.db_manager = db_manager
                st.session_state.database_connected = True
                logger.info("Database manager created and stored in session state")
                
            except Exception as e:
                error_msg = f"Failed to create database manager: {e}"
                logger.error(error_msg)
                
                # Try to create a fallback database manager without Streamlit UI
                try:
                    logger.info("Attempting to create fallback database manager...")
                    from database.db_manager import DatabaseManager
                    from models.lazy_model_manager import LazyModelManager
                    import torch
                    
                    # Create minimal components without Streamlit UI
                    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                    fallback_model_manager = LazyModelManager(device)
                    fallback_db_manager = DatabaseManager(fallback_model_manager)
                    
                    # Test the fallback
                    fallback_db_manager.database_exists(".")
                    
                    st.session_state.db_manager = fallback_db_manager
                    st.session_state.database_connected = True
                    logger.info("Fallback database manager created successfully")
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback database manager creation failed: {fallback_error}")
                    raise RuntimeError(f"Cannot create database manager: {e}. Fallback also failed: {fallback_error}")
            
        # Verify we have a valid database manager
        db_manager = st.session_state.get('db_manager')
        if db_manager is None:
            raise RuntimeError("Database manager is None in session state")
            
        return db_manager
    
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

# ===== STREAMLIT CACHING HELPERS =====

@st.cache_resource(show_spinner=False)
def get_cached_model_manager():
    """
    Get a cached instance of the OptimizedModelManager.
    This now directly calls the cached function from core.optimized_model_manager.
    """
    logger.info("Attempting to get cached OptimizedModelManager instance via core module...")
    try:
        from core.optimized_model_manager import get_optimized_model_manager
        model_manager = get_optimized_model_manager()

        if model_manager is None:
            error_msg = "get_optimized_model_manager() from core module returned None."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Basic check (OptimizedModelManager has methods like is_model_ready)
        if not hasattr(model_manager, 'is_model_ready'): 
             logger.warning("OptimizedModelManager instance obtained, but appears to be missing 'is_model_ready' method. Ensure it's the correct class.")
        
        logger.info("Successfully obtained OptimizedModelManager instance from core module.")
        return model_manager
    except ImportError as ie:
        error_msg = f"ImportError while trying to get OptimizedModelManager from core: {str(ie)}. Check module paths."
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from ie
    except Exception as e:
        error_msg = f"Unexpected error while trying to get OptimizedModelManager from core: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

@st.cache_resource(show_spinner=False)
def get_cached_db_manager():
    """Return a cached DatabaseManager instance."""
    return LazySessionManager.ensure_database_manager() 