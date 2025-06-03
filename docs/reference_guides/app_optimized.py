# 🚀 Optimized Pixel Detective Application
# 📌 Purpose: Lightning-fast startup with background model loading
# 🎯 Mission: Sub-second UI rendering, models load in background
# 💡 Based on: Streamlit Background tasks.md research

"""
Pixel Detective: Optimized High-Performance Image Search Application

Key Performance Optimizations:
- Instant UI rendering (< 1 second)
- Background model preloading
- True non-blocking operations
- Smart memory management
- Task queue-based architecture
"""

import streamlit as st
import time
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Set page config as the absolute first command
st.set_page_config(
    page_title="Pixel Detective - Optimized",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """
    Optimized main application with instant startup.
    
    Performance targets:
    - UI renders in < 1 second
    - Models load in background
    - User can interact immediately
    """
    try:
        # Start performance timer
        app_start_time = time.time()
        
        # Phase 1: Instant UI rendering
        render_instant_ui()
        ui_render_time = time.time() - app_start_time
        
        logger.info(f"UI rendered in {ui_render_time:.3f}s")
        
        # Phase 2: Background model preloading (non-blocking)
        start_background_loading()
        
        # Phase 3: Main application logic
        render_main_application()
        
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        render_error_recovery(e)


def render_instant_ui():
    """
    Render the instant UI components.
    This must be extremely fast (< 1 second).
    """
    # Header
    st.title("🚀 Pixel Detective - Optimized")
    st.markdown("**Lightning-fast image search with AI-powered analysis**")
    
    # Performance indicator
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info("⚡ **Ultra-fast startup mode** - UI ready instantly!")
        
        with col2:
            if 'models_ready' in st.session_state and st.session_state.models_ready:
                st.success("🤖 AI Ready")
            else:
                st.warning("🔄 AI Loading")
        
        with col3:
            if 'startup_time' in st.session_state:
                st.metric("Startup", f"{st.session_state.startup_time:.2f}s")


def start_background_loading():
    """
    Start background model loading without blocking the UI.
    This is the key optimization from the research document.
    """
    if 'background_loading_started' not in st.session_state:
        st.session_state.background_loading_started = True
        
        # Import and start the fast startup manager
        from core.fast_startup_manager import start_fast_app
        
        try:
            manager, progress = start_fast_app()
            st.session_state.startup_manager = manager
            st.session_state.startup_progress = progress
            
            logger.info("Background model loading started")
            
        except Exception as e:
            logger.error(f"Failed to start background loading: {e}")
            st.session_state.background_loading_error = str(e)


def render_main_application():
    """
    Render the main application interface.
    This adapts based on whether models are ready.
    """
    # Check model readiness
    models_ready = check_models_ready()
    
    if models_ready:
        render_full_application()
    else:
        render_loading_interface()


def check_models_ready() -> bool:
    """Check if AI models are ready for use"""
    if 'startup_manager' in st.session_state:
        manager = st.session_state.startup_manager
        ready = manager.is_ready()
        st.session_state.models_ready = ready
        return ready
    
    return False


def render_loading_interface():
    """
    Render the interface while models are loading.
    Users can still interact with basic features.
    """
    st.markdown("---")
    st.markdown("### 🚀 AI Models Loading in Background")
    
    # Progress tracking
    if 'startup_manager' in st.session_state:
        manager = st.session_state.startup_manager
        progress = manager.get_progress()
        
        # Progress bar
        if progress.models_preloading:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Estimate progress
            if progress.start_time > 0:
                elapsed = time.time() - progress.start_time
                estimated_progress = min(0.9, elapsed / 30.0)  # Assume 30s max
                progress_bar.progress(estimated_progress)
                status_text.info(f"Loading AI models... ({elapsed:.1f}s elapsed)")
        
        # Show what users can do while waiting
        st.markdown("### 📋 Available While Loading")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **✅ Ready Now:**
            - Browse file system
            - View image metadata
            - Check system status
            - Configure settings
            """)
        
        with col2:
            st.markdown("""
            **🔄 Coming Soon:**
            - AI-powered search
            - Image similarity
            - Auto-captioning
            - Duplicate detection
            """)
        
        # Basic file browser (works without AI)
        render_basic_file_browser()
    
    else:
        st.error("Failed to initialize startup manager")


def render_full_application():
    """
    Render the full application when models are ready.
    This is the complete Pixel Detective experience.
    """
    st.markdown("---")
    st.success("🎉 **All systems ready!** Full AI capabilities available.")
    
    # Main navigation
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Search", "📁 Browse", "🤖 AI Analysis", "⚙️ Settings"])
    
    with tab1:
        render_search_interface()
    
    with tab2:
        render_browse_interface()
    
    with tab3:
        render_ai_analysis_interface()
    
    with tab4:
        render_settings_interface()


def render_basic_file_browser():
    """
    Basic file browser that works without AI models.
    Provides immediate value while models load.
    """
    st.markdown("### 📁 File Browser (No AI Required)")
    
    # Simple folder selection
    folder_path = st.text_input(
        "Enter folder path:",
        value=st.session_state.get('folder_path', ''),
        key="basic_folder_input"
    )
    
    if folder_path:
        st.session_state.folder_path = folder_path
        
        try:
            import os
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                # List image files
                image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                image_files = []
                
                for file in os.listdir(folder_path):
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        image_files.append(file)
                
                if image_files:
                    st.success(f"Found {len(image_files)} image files")
                    
                    # Show first few files
                    st.markdown("**Sample files:**")
                    for file in image_files[:10]:
                        st.text(f"📷 {file}")
                    
                    if len(image_files) > 10:
                        st.text(f"... and {len(image_files) - 10} more")
                else:
                    st.warning("No image files found in this folder")
            else:
                st.error("Invalid folder path")
                
        except Exception as e:
            st.error(f"Error accessing folder: {e}")


def render_search_interface():
    """Render the AI-powered search interface"""
    st.markdown("### 🔍 AI-Powered Image Search")
    
    search_query = st.text_input("Search for images:", key="search_query")
    
    if search_query:
        st.info(f"Searching for: '{search_query}'")
        # TODO: Implement actual search using optimized model manager
        st.success("Search functionality will be implemented here")


def render_browse_interface():
    """Render the enhanced browse interface"""
    st.markdown("### 📁 Enhanced Image Browser")
    
    # TODO: Implement enhanced browsing with AI features
    st.info("Enhanced browsing with AI-powered features")


def render_ai_analysis_interface():
    """Render the AI analysis interface"""
    st.markdown("### 🤖 AI Image Analysis")
    
    # TODO: Implement AI analysis features
    st.info("AI analysis features will be implemented here")


def render_settings_interface():
    """Render the settings interface"""
    st.markdown("### ⚙️ Application Settings")
    
    # Performance settings
    st.subheader("Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.checkbox("Keep models in memory", value=True, key="keep_models_loaded")
        st.checkbox("Enable GPU acceleration", value=True, key="use_gpu")
    
    with col2:
        st.slider("Memory threshold (%)", 50, 95, 80, key="memory_threshold")
        st.slider("Background workers", 1, 4, 2, key="worker_count")
    
    # Model settings
    st.subheader("AI Models")
    
    if 'startup_manager' in st.session_state:
        manager = st.session_state.startup_manager
        
        # Show model status
        try:
            from core.optimized_model_manager import get_optimized_model_manager
            model_manager = get_optimized_model_manager()
            status = model_manager.get_loading_status()
            
            for model_name, model_status in status.items():
                if isinstance(model_status, dict):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.text(f"Model: {model_name}")
                    
                    with col2:
                        if model_status.get('loaded', False):
                            st.success("✅ Loaded")
                        elif model_status.get('loading', False):
                            st.warning("🔄 Loading")
                        else:
                            st.error("❌ Not loaded")
                    
                    with col3:
                        if model_status.get('load_time', 0) > 0:
                            st.text(f"{model_status['load_time']:.1f}s")
        
        except Exception as e:
            st.error(f"Error getting model status: {e}")


def render_error_recovery(error: Exception):
    """Render error recovery interface"""
    st.error("🚨 Application Error")
    st.exception(error)
    
    st.markdown("### 🔧 Recovery Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Restart App"):
            # Clear session state and restart
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col2:
        if st.button("🧹 Clear Cache"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache cleared")
    
    with col3:
        if st.button("📊 Show Debug Info"):
            st.json({
                "session_state_keys": list(st.session_state.keys()),
                "error_type": type(error).__name__,
                "error_message": str(error)
            })


# Auto-refresh for loading progress
if 'models_ready' not in st.session_state or not st.session_state.models_ready:
    # Auto-refresh every 2 seconds while models are loading
    time.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main() 