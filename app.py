# 📂 File Path: /project_root/app.py
# 📌 Purpose: Main entry point for the Pixel Detective image search application.
# 🔄 Latest Changes: 
#   - Refactored code into smaller modules for better maintainability
#   - Optimized model loading strategy to load models once at startup
#   - Fixed asyncio and Streamlit context issues
#   - Improved error handling and logging
#   - Added tab state persistence to fix metadata tab issue
#   - Reverted to minimal CSS for dark mode with extendable sidebar
# ⚙️ Key Logic: Initializes the application, loads models, and sets up the Streamlit interface.
# 🧠 Reasoning: Streamlit provides an easy-to-use interface for deploying machine learning models.

"""
Pixel Detective: Image Search Application.
"""
import os
import asyncio
import streamlit as st
import torch
import gc

# Set environment variables before importing other modules
# Fix Streamlit file watcher issue with torch
os.environ['STREAMLIT_WATCH_EXCLUDE_MODULES'] = 'torch,torch._classes'
os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'

# Set CUDA environment variables for better compatibility
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'  # More synchronous CUDA calls for better error detection
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'  # Help with memory fragmentation
os.environ['PYTORCH_NO_CUDA_MEMORY_CACHING'] = '0'  # Enable memory caching for better performance

# Set page config as the first Streamlit command (must be before any other st commands)
st.set_page_config(
    page_title="Pixel Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load minimal CSS for dark mode
def load_custom_css():
    """Load minimal CSS for dark mode styling and extendable sidebar."""
    try:
        css_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "custom.css")
        if os.path.exists(css_file):
            with open(css_file, "r") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            print(f"Custom CSS file not found at {css_file}")
    except Exception as e:
        print(f"Error loading custom CSS: {e}")

# Load custom CSS
load_custom_css()

# Initialize asyncio event loop to avoid "no running event loop" error in Streamlit
try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Now import the rest of our modules
from utils.logger import logger
from utils.cuda_utils import check_cuda_availability, check_gpu_memory, log_cuda_memory_usage
from models.model_manager import ModelManager
from ui.main_interface import render_main_interface
from database.db_manager import DatabaseManager
from config import GPU_MEMORY_EFFICIENT, KEEP_MODELS_LOADED

# Global model manager to maintain loaded models throughout the app lifecycle
model_manager = None

def initialize_app():
    """Initialize the application, load models, and set up session state."""
    global model_manager
    
    # Display CUDA availability information
    cuda_available, cuda_message = check_cuda_availability()
    st.sidebar.write(cuda_message)
    
    if not cuda_available:
        st.sidebar.error("CUDA is not available. The application will run on the CPU, which may be significantly slower.")
        device = torch.device("cpu")
    else:
        st.sidebar.success("CUDA is available. The application will utilize the GPU for faster processing.")
        device = torch.device("cuda")
        
        # Display GPU memory information
        memory_info = check_gpu_memory()
        if memory_info["available"]:
            st.sidebar.info(memory_info["message"])
    
    # Initialize or retrieve model manager from session state
    if 'model_manager' not in st.session_state:
        logger.info("Creating new model manager instance")
        model_manager = ModelManager(device)
        st.session_state.model_manager = model_manager
    else:
        logger.info("Using existing model manager from session state")
        model_manager = st.session_state.model_manager
    
    # Log CUDA memory usage after model loading
    log_cuda_memory_usage("After model manager initialization")
    
    # Initialize or retrieve database manager from session state
    if 'db_manager' not in st.session_state:
        logger.info("Creating new database manager instance")
        db_manager = DatabaseManager(model_manager)
        st.session_state.db_manager = db_manager
    else:
        logger.info("Using existing database manager from session state")
        db_manager = st.session_state.db_manager
    
    # Initialize other session state variables
    if 'database_built' not in st.session_state:
        st.session_state.database_built = False
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    if 'total_images' not in st.session_state:
        st.session_state.total_images = 0
    if 'images_data' not in st.session_state:
        st.session_state.images_data = None
    if 'embeddings' not in st.session_state:
        st.session_state.embeddings = None
    if 'image_files' not in st.session_state:
        st.session_state.image_files = None
    if 'game_image_shown' not in st.session_state:
        st.session_state.game_image_shown = False
    if 'image_understanding' not in st.session_state:
        st.session_state.image_understanding = None
    # Initialize tab state variables
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    if 'text_metadata_expanded' not in st.session_state:
        st.session_state.text_metadata_expanded = {}
    if 'image_metadata_expanded' not in st.session_state:
        st.session_state.image_metadata_expanded = {}

def on_shutdown():
    """Clean up resources when the app is shutting down."""
    logger.info("Application shutting down, cleaning up resources...")
    
    # Unload models if they were loaded and we don't want to keep them loaded
    if 'model_manager' in st.session_state:
        model_manager = st.session_state.model_manager
        if not KEEP_MODELS_LOADED:
            logger.info("Unloading models as KEEP_MODELS_LOADED is False")
            model_manager.unload_all_models()
        else:
            logger.info("Keeping models loaded as KEEP_MODELS_LOADED is True")
    
    # Force garbage collection
    gc.collect()
    
    # Clear CUDA cache
    if torch.cuda.is_available():
        try:
            # Empty CUDA cache
            torch.cuda.empty_cache()
            
            # Reset peak memory stats
            torch.cuda.reset_peak_memory_stats()
            
            # Log final GPU memory state
            allocated = torch.cuda.memory_allocated(0) / 1024**2
            reserved = torch.cuda.memory_reserved(0) / 1024**2
            logger.info(f"Final GPU memory state - Allocated: {allocated:.2f} MB, Reserved: {reserved:.2f} MB")
            
            logger.info("CUDA resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up CUDA resources: {e}")
    
    logger.info("Application shutdown complete")
    
def main():
    """Main function to run the Streamlit app."""
    try:
        # Initialize the application
        initialize_app()
        
        # Log memory usage before rendering the interface
        log_cuda_memory_usage("Before rendering UI")
        
        # Render the main interface
        render_main_interface()
        
        # Log memory usage after rendering the interface
        log_cuda_memory_usage("After rendering UI")
        
    except Exception as e:
        st.error(f"An error occurred: {e}")
        logger.error(f"Application error: {e}", exc_info=True)

# Register shutdown function
import atexit
atexit.register(on_shutdown)

# Start the app
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # We don't call on_shutdown() here anymore since atexit will handle it
        # and we don't want to clean up resources if they'll be reused
        pass 