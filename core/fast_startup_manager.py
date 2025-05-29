# ⚡ Fast Startup Manager for Pixel Detective
# 📌 Purpose: Instant UI startup with background model preloading
# 🎯 Mission: Sub-second UI rendering while models load in background
# 💡 Based on: Streamlit Background tasks.md research

import streamlit as st
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class StartupPhase(Enum):
    """Phases of the fast startup process"""
    INSTANT_UI = "instant_ui"
    BACKGROUND_PREP = "background_prep"
    SERVICE_CHECK = "service_check"
    READY = "ready"


@dataclass
class StartupProgress:
    """Thread-safe startup progress tracking"""
    phase: StartupPhase = StartupPhase.INSTANT_UI
    ui_ready: bool = False
    services_ready: bool = False
    error: Optional[str] = None
    start_time: float = 0.0
    ui_render_time: float = 0.0


class FastStartupManager:
    """
    Manages ultra-fast application startup with background model preloading.
    
    Key principles:
    1. UI renders instantly (< 1 second)
    2. Models preload in background while user interacts with UI
    3. Seamless transition when models are ready
    4. No blocking operations in main thread
    """
    
    def __init__(self):
        self._progress = StartupProgress()
        self._lock = threading.RLock()
        self._preload_thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable] = {}
        
        logger.info("FastStartupManager initialized")
    
    def start_fast_startup(self) -> StartupProgress:
        """
        Start the fast startup process.
        Returns immediately with UI-ready status.
        """
        with self._lock:
            if self._progress.start_time > 0:
                return self._progress  # Already started
            
            self._progress.start_time = time.time()
            self._progress.phase = StartupPhase.INSTANT_UI
        
        # Phase 1: Instant UI (this should be < 1 second)
        ui_start = time.time()
        self._render_instant_ui()
        ui_time = time.time() - ui_start
        
        with self._lock:
            self._progress.ui_ready = True
            self._progress.ui_render_time = ui_time
            self._progress.phase = StartupPhase.BACKGROUND_PREP
        
        logger.info(f"Instant UI rendered in {ui_time:.3f}s")
        
        # Phase 2: Start background service checks (non-blocking placeholder)
        self._start_background_service_check()
        
        return self._progress
    
    def _render_instant_ui(self):
        """
        Render the instant UI components.
        This must be extremely fast (< 1 second).
        """
        # Only import lightweight UI components
        try:
            # Set basic page config if not already set
            if not hasattr(st, '_config_set'):
                st.set_page_config(
                    page_title="Pixel Detective",
                    page_icon="🕵️‍♂️",
                    layout="wide",
                    initial_sidebar_state="expanded"
                )
                st._config_set = True
            
            # Render minimal UI structure
            self._render_header()
            self._render_quick_actions()
            self._render_status_area()
            
        except Exception as e:
            logger.error(f"Error in instant UI rendering: {e}")
            with self._lock:
                self._progress.error = f"UI render error: {str(e)}"
    
    def _render_header(self):
        """Render the application header instantly"""
        st.title("🕵️‍♂️ Pixel Detective")
        st.markdown("**Lightning-fast image search and analysis**")
        
        # Show startup status
        with self._lock:
            if self._progress.services_ready:
                st.success("✅ Services Connected. Ready for image analysis")
            elif self._progress.phase == StartupPhase.SERVICE_CHECK:
                st.info("🔄 Checking backend services...")
            else:
                st.info("⚡ Starting up...")
    
    def _render_quick_actions(self):
        """Render quick action buttons that work immediately"""
        st.markdown("### Quick Start")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📁 Select Folder", type="primary", key="quick_folder"):
                self._handle_folder_selection()
        
        with col2:
            if st.button("🔍 Search Images", key="quick_search"):
                self._handle_quick_search()
        
        with col3:
            if st.button("📊 View Stats", key="quick_stats"):
                self._handle_quick_stats()
    
    def _render_status_area(self):
        """Render the status area with loading progress"""
        with st.container():
            st.markdown("### System Status")
            
            # Model loading status
            with self._lock:
                progress = self._progress
            
            if progress.services_ready:
                st.success("🔗 Backend Services: Connected")
            elif progress.phase == StartupPhase.SERVICE_CHECK:
                # Placeholder for service check progress
                st.info("Attempting to connect to backend services...")
            else:
                st.warning("🔗 Backend Services: Initializing...")
            
            # Performance metrics
            if progress.ui_render_time > 0:
                st.metric("UI Startup Time", f"{progress.ui_render_time:.3f}s")
    
    def _start_background_service_check(self):
        """Start background service checking"""
        # This is a placeholder. Actual service checking logic will be added later.
        # For now, simulate a quick check and set services to ready.
        if self._preload_thread and self._preload_thread.is_alive():
            return  # Already running (though name is now _preload_thread)
        
        with self._lock:
            self._progress.phase = StartupPhase.SERVICE_CHECK
        
        self._preload_thread = threading.Thread(
            target=self._background_service_check_worker,
            daemon=True,
            name="ServiceChecker"
        )
        self._preload_thread.start()
        
        logger.info("Started background service checking (placeholder)")

    def _background_service_check_worker(self):
        """Background worker that checks service availability (placeholder)"""
        try:
            service_check_start = time.time()
            
            # Simulate service check
            logger.info("Simulating service checks...")
            time.sleep(2) # Simulate network delay
            services_are_actually_ready = True # Placeholder
            
            service_check_time = time.time() - service_check_start
            
            with self._lock:
                self._progress.services_ready = services_are_actually_ready
                self._progress.phase = StartupPhase.READY if self._progress.services_ready else StartupPhase.SERVICE_CHECK
            
            if self._progress.services_ready:
                logger.info(f"All services checked and ready in {service_check_time:.1f}s (simulated)")
            else:
                logger.warning(f"Service check failed or timed out (simulated)")
            
            # Trigger UI update
            self._trigger_ui_update()
            
        except Exception as e:
            logger.error(f"Error in background service check: {e}")
            with self._lock:
                self._progress.error = f"Service check error: {str(e)}"
    
    def _setup_progress_callback(self, progress_bar, status_text):
        """Setup progress callback for UI updates"""
        self._callbacks['progress_bar'] = progress_bar
        self._callbacks['status_text'] = status_text
    
    def _trigger_ui_update(self):
        """Trigger UI update (Streamlit-safe)"""
        # In a real implementation, you might use st.rerun() or similar
        # For now, we'll just update the callbacks if they exist
        try:
            if 'progress_bar' in self._callbacks and 'status_text' in self._callbacks:
                with self._lock:
                    progress = self._progress
                
                if progress.services_ready:
                    self._callbacks['progress_bar'].progress(1.0)
                    self._callbacks['status_text'].success("✅ Services connected!")
                elif progress.phase == StartupPhase.SERVICE_CHECK:
                    # Placeholder for service check progress
                    st.info("Attempting to connect to backend services...")
        except Exception as e:
            logger.debug(f"UI update callback error: {e}")
    
    def _handle_folder_selection(self):
        """Handle folder selection (works even if models aren't ready)"""
        st.info("📁 Folder selection will be available once services are connected")
        
        # You could implement a basic folder browser here that doesn't require models
        # For now, just show a message
        if not self._progress.services_ready:
            st.warning("Please wait for backend services to finish connecting...")
    
    def _handle_quick_search(self):
        """Handle quick search (works even if models aren't ready)"""
        st.info("🔍 Search will be available once services are connected")
        
        # You could implement a basic file browser here
        if not self._progress.services_ready:
            st.warning("Please wait for backend services to finish connecting...")
    
    def _handle_quick_stats(self):
        """Handle quick stats (works immediately)"""
        st.info("📊 System Statistics")
        
        with self._lock:
            progress = self._progress
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Startup Phase", progress.phase.value.replace('_', ' ').title())
            st.metric("UI Ready", "✅ Yes" if progress.ui_ready else "❌ No")
        
        with col2:
            st.metric("Services Ready", "✅ Yes" if progress.services_ready else "🔄 Loading")
            if progress.ui_render_time > 0:
                st.metric("UI Render Time", f"{progress.ui_render_time:.3f}s")
    
    def get_progress(self) -> StartupProgress:
        """Get current startup progress"""
        with self._lock:
            return self._progress
    
    def is_ready(self) -> bool:
        """Check if the system is fully ready"""
        with self._lock:
            return self._progress.services_ready and self._progress.ui_ready
    
    def wait_for_ready(self, timeout: float = 60.0) -> bool:
        """Wait for the system to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_ready():
                return True
            time.sleep(0.1)
        
        return False


# Streamlit cache integration
@st.cache_resource
def get_fast_startup_manager() -> FastStartupManager:
    """Get cached fast startup manager instance"""
    return FastStartupManager()


def start_fast_app():
    """
    Start the fast application.
    This is the main entry point for ultra-fast startup.
    """
    manager = get_fast_startup_manager()
    progress = manager.start_fast_startup()
    
    # The UI is now rendered and services are loading in background
    return manager, progress 