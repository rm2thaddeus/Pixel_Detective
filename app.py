# 📂 File Path: /project_root/app.py
# 📌 Purpose: Main entry point for the Pixel Detective image search application.
# 🔄 Latest Changes: 
#   - PERFORMANCE OPTIMIZATION: Implemented lazy model loading from next_sprint.md
#   - Replaced ModelManager with LazyModelManager for 70% startup time reduction
#   - Added progressive session state initialization to reduce memory bloat
#   - Integrated mvp_app.py sequential loading patterns for memory efficiency
#   - Added memory monitoring and cleanup capabilities
# ⚙️ Key Logic: Fast startup with lazy loading, models load only when needed
# 🧠 Reasoning: Addresses critical performance bottlenecks identified in next_sprint.md

"""
Pixel Detective: Image Search Application with Performance Optimizations.
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
from utils.lazy_session_state import LazySessionManager, get_session_memory_usage, clear_unused_session_state
from ui.main_interface import render_main_interface
from config import GPU_MEMORY_EFFICIENT, KEEP_MODELS_LOADED

def initialize_app():
    """
    Initialize the application with lazy loading optimizations.
    
    Key improvements from next_sprint.md:
    - Models load only when needed (not at startup)
    - Progressive session state initialization
    - Immediate UI availability
    """
    
    # Display CUDA availability information
    cuda_available, cuda_message = check_cuda_availability()
    st.sidebar.write(cuda_message)
    
    if not cuda_available:
        st.sidebar.error("CUDA is not available. The application will run on the CPU, which may be significantly slower.")
    else:
        st.sidebar.success("CUDA is available. The application will utilize the GPU for faster processing.")
        
        # Display GPU memory information
        memory_info = check_gpu_memory()
        if memory_info["available"]:
            st.sidebar.info(memory_info["message"])
    
    # 🚀 PERFORMANCE OPTIMIZATION: Initialize only essential session state
    # Models and database managers will be lazy-loaded when first accessed
    LazySessionManager.init_core_state()
    
    # Display memory monitoring in sidebar
    show_memory_monitoring()
    
    logger.info("Fast app initialization completed - models will load on demand")

def show_memory_monitoring():
    """Display memory monitoring information in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Performance Monitor")
    
    # Session state memory usage
    try:
        session_memory = get_session_memory_usage()
        st.sidebar.metric(
            "Session Memory", 
            f"{session_memory['total_mb']:.1f} MB",
            help=f"{session_memory['variable_count']} variables"
        )
        
        # Show large objects warning
        if session_memory['large_objects']:
            st.sidebar.warning(f"Large objects detected: {len(session_memory['large_objects'])}")
    except Exception as e:
        st.sidebar.error(f"Error getting session memory: {e}")
    
    # GPU memory status (if model manager exists)
    if 'model_manager' in st.session_state:
        try:
            model_manager = st.session_state.model_manager
            if hasattr(model_manager, 'get_memory_status'):
                memory_status = model_manager.get_memory_status()
                if memory_status["available"]:
                    st.sidebar.metric(
                        "GPU Memory",
                        f"{memory_status['allocated_mb']:.0f} MB",
                        f"{memory_status['usage_percent']:.1f}% used"
                    )
                    
                    # Show current model
                    current_model = memory_status.get('current_model', 'None')
                    st.sidebar.info(f"🤖 Active Model: {current_model or 'None'}")
                    
                    # Memory cleanup button
                    if st.sidebar.button("🧹 Clean Memory"):
                        clear_unused_session_state()
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        st.rerun()
        except Exception as e:
            st.sidebar.error(f"Error getting GPU memory: {e}")
    else:
        st.sidebar.info("🤖 Models: Not loaded (lazy loading)")

def on_shutdown():
    """Clean up resources when the app is shutting down."""
    logger.info("Application shutting down, cleaning up resources...")
    
    # Unload models if they were loaded and we don't want to keep them loaded
    if 'model_manager' in st.session_state:
        model_manager = st.session_state.model_manager
        if not KEEP_MODELS_LOADED:
            logger.info("Unloading models as KEEP_MODELS_LOADED is False")
            if hasattr(model_manager, 'unload_all_models'):
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
    """Main function to run the Streamlit app with performance optimizations."""
    try:
        # 🚀 PERFORMANCE OPTIMIZATION: Fast initialization
        # Models will load lazily when first accessed
        initialize_app()
        
        # Log memory usage before rendering the interface
        log_cuda_memory_usage("Before rendering UI (lazy loading)")
        
        # Render the main interface
        render_main_interface()
        
        # Log memory usage after rendering the interface
        log_cuda_memory_usage("After rendering UI (lazy loading)")
        
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