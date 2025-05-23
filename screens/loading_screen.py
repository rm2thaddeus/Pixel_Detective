# 📊 Screen 2: Loading Screen
# 📌 Purpose: Keep user engaged during background processing
# 🎯 Mission: Show detailed progress and build excitement

import os
import time
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader, LoadingPhase


class LoadingScreen:
    """Screen 2: Progress tracking and live logs"""
    
    @staticmethod
    def render():
        """Render the loading screen"""
        # Get current progress from background loader
        progress_data = background_loader.get_progress()
        
        LoadingScreen._render_header()
        LoadingScreen._render_progress_section(progress_data)
        LoadingScreen._render_live_logs(progress_data)
        LoadingScreen._render_controls()
        LoadingScreen._render_footer(progress_data)
        LoadingScreen._render_sidebar(progress_data)
        
        # Handle completion or errors
        LoadingScreen._handle_completion_or_errors(progress_data)
        
        # Auto-refresh every 2 seconds during loading
        if progress_data.is_loading:
            time.sleep(1)  # Small delay to prevent excessive polling
            st.rerun()
    
    @staticmethod
    def _handle_completion_or_errors(progress_data):
        """Handle completion or error states"""
        if progress_data.error_occurred:
            # Transition to error state
            AppStateManager.transition_to_error(progress_data.error_message, can_retry=True)
            st.rerun()
        elif not progress_data.is_loading and progress_data.progress_percentage >= 100:
            # Update session state with results and transition to advanced UI
            st.session_state.ui_deps_loaded = progress_data.ui_deps_loaded
            st.session_state.models_loaded = progress_data.models_loaded
            st.session_state.database_ready = progress_data.database_ready
            st.session_state.image_files = progress_data.image_files
            
            AppStateManager.transition_to_advanced()
            st.rerun()
    
    @staticmethod
    def _render_header():
        """Render the loading screen header"""
        st.title("🔄 Building Your Image Database")
        
        folder_path = st.session_state.get('folder_path', 'Unknown')
        st.markdown(f"**Processing:** `{folder_path}`")
        st.markdown("---")
    
    @staticmethod
    def _render_progress_section(progress_data):
        """Render the main progress section"""
        st.markdown("### 📊 Overall Progress")
        
        # Progress bar with percentage
        progress_bar = st.progress(progress_data.progress_percentage / 100)
        st.markdown(f"**{progress_data.progress_percentage}%** - {progress_data.progress_message}")
        
        # Current phase indicator
        LoadingScreen._render_phase_indicator(progress_data.current_phase)
        
        st.markdown("---")
    
    @staticmethod
    def _render_phase_indicator(current_phase):
        """Show current loading phase with visual indicators"""
        # Phase mapping with icons and descriptions
        phases = {
            LoadingPhase.UI_DEPS: ("🎨", "Loading UI Components", "Preparing interface modules"),
            LoadingPhase.FOLDER_SCAN: ("📁", "Scanning Image Folder", "Finding and cataloging images"),
            LoadingPhase.MODEL_INIT: ("🤖", "Initializing AI Models", "Loading CLIP and text encoders"),
            LoadingPhase.DB_BUILD: ("💾", "Building Database", "Processing images for search"),
            LoadingPhase.READY: ("✅", "System Ready", "All systems operational")
        }
        
        st.markdown("#### 🔄 Current Phase")
        
        # Create phase progress indicators
        cols = st.columns(5)
        
        for i, (phase, (icon, title, desc)) in enumerate(phases.items()):
            with cols[i]:
                if phase == current_phase:
                    # Current phase - highlighted
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background-color: #1f77b4; border-radius: 10px; color: white;">
                        <div style="font-size: 24px;">{icon}</div>
                        <div style="font-size: 12px; font-weight: bold;">{title}</div>
                    </div>
                    """, unsafe_allow_html=True)
                elif list(phases.keys()).index(phase) < list(phases.keys()).index(current_phase):
                    # Completed phase
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background-color: #28a745; border-radius: 10px; color: white;">
                        <div style="font-size: 24px;">✅</div>
                        <div style="font-size: 12px;">{title}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Future phase
                    st.markdown(f"""
                    <div style="text-align: center; padding: 10px; background-color: #6c757d; border-radius: 10px; color: white;">
                        <div style="font-size: 24px;">{icon}</div>
                        <div style="font-size: 12px;">{title}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Show current phase description
        if current_phase in phases:
            icon, title, desc = phases[current_phase]
            st.info(f"**{icon} {title}**: {desc}")
    
    @staticmethod
    def _render_live_logs(progress_data):
        """Render the live progress logs"""
        st.markdown("### 📋 Live Progress Log")
        
        if not progress_data.logs:
            st.info("No logs yet...")
            return
        
        # Create scrollable log container
        log_container = st.container()
        
        with log_container:
            # Show logs in reverse order (newest first)
            for log in reversed(progress_data.logs[-20:]):  # Show last 20 logs
                if "✅" in log:
                    st.success(log)
                elif "❌" in log or "Error" in log:
                    st.error(log)
                elif "⚠️" in log or "Warning" in log:
                    st.warning(log)
                elif "🔄" in log or "⏳" in log:
                    st.info(log)
                else:
                    st.text(log)
    
    @staticmethod
    def _render_controls():
        """Render user controls for the loading process"""
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("⏸️ Pause", help="Pause the loading process"):
                st.warning("⏸️ Pause functionality coming soon!")
        
        with col2:
            if st.button("❌ Cancel", help="Cancel and return to folder selection"):
                LoadingScreen._cancel_loading()
        
        with col3:
            if st.button("📊 Details", help="Show detailed system information"):
                LoadingScreen._show_details()
        
        with col4:
            if st.button("🔄 Refresh", help="Refresh the progress display"):
                st.rerun()
    
    @staticmethod
    def _cancel_loading():
        """Cancel the loading process"""
        background_loader.cancel_loading()
        st.warning("🛑 Cancelling loading process...")
        
        # Brief delay to let cancellation process, then return to fast UI
        import time
        time.sleep(1)
        AppStateManager.reset_to_fast_ui()
        st.rerun()
    
    @staticmethod
    def _show_details():
        """Show detailed loading information"""
        progress_data = background_loader.get_progress()
        
        with st.expander("📊 Detailed Loading Information", expanded=True):
            # System info
            st.markdown("**System Status:**")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("UI Dependencies", "✅ Loaded" if progress_data.ui_deps_loaded else "⏳ Loading")
                st.metric("Models", "✅ Loaded" if progress_data.models_loaded else "⏳ Loading")
            
            with col2:
                st.metric("Database", "✅ Ready" if progress_data.database_ready else "⏳ Building")
                st.metric("Images Found", f"{len(progress_data.image_files):,}")
            
            # Timing info
            if progress_data.start_time:
                import time
                elapsed = time.time() - progress_data.start_time
                st.markdown(f"**Elapsed Time:** {elapsed:.1f} seconds")
                
                eta = progress_data.get_estimated_time_remaining()
                st.markdown(f"**Estimated Remaining:** {eta}")
    
    @staticmethod
    def _render_footer(progress_data):
        """Render the loading screen footer"""
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            eta = progress_data.get_estimated_time_remaining()
            st.info(f"⏱️ **Estimated time remaining:** {eta}")
        
        with col2:
            st.success("🎯 **After completion:** Advanced search, AI game, and more!")
    
    @staticmethod
    def _render_sidebar(progress_data):
        """Render contextual sidebar for Loading screen"""
        with st.sidebar:
            st.markdown("### 🔄 Processing Status")
            
            # Folder info
            folder_path = st.session_state.get('folder_path', 'Unknown')
            st.markdown(f"**📁 Folder:** `{folder_path}`")
            
            # Image count
            image_count = len(progress_data.image_files)
            if image_count > 0:
                st.metric("🖼️ Images Found", f"{image_count:,}")
            else:
                st.info("🔍 Scanning for images...")
            
            # Progress summary
            st.metric("📊 Progress", f"{progress_data.progress_percentage}%")
            
            # ETA
            eta = progress_data.get_estimated_time_remaining()
            st.metric("⏱️ ETA", eta)
            
            st.markdown("---")
            
            # Current phase details
            st.markdown("### 📊 Current Phase")
            
            phase_details = {
                LoadingPhase.UI_DEPS: {
                    "title": "🎨 Loading UI Components",
                    "tasks": ["Interface modules", "Layout components", "Style systems"]
                },
                LoadingPhase.FOLDER_SCAN: {
                    "title": "📁 Scanning Folder",
                    "tasks": ["Finding images", "Checking formats", "Building file list"]
                },
                LoadingPhase.MODEL_INIT: {
                    "title": "🤖 Loading AI Models",
                    "tasks": ["CLIP Vision Model", "Text Encoder", "Feature Extractor"]
                },
                LoadingPhase.DB_BUILD: {
                    "title": "💾 Building Database",
                    "tasks": ["Processing images", "Extracting features", "Creating indices"]
                },
                LoadingPhase.READY: {
                    "title": "✅ System Ready",
                    "tasks": ["All systems operational"]
                }
            }
            
            if progress_data.current_phase in phase_details:
                details = phase_details[progress_data.current_phase]
                st.markdown(f"**{details['title']}**")
                for task in details['tasks']:
                    st.markdown(f"• {task}")
            
            st.markdown("---")
            
            # Coming features
            st.markdown("### 🎯 Coming Next")
            st.markdown("""
            **🔍 Text-based search**  
            Find images using natural language
            
            **🖼️ Image similarity**  
            Find similar images visually
            
            **🎮 AI guessing game**  
            Interactive image challenges
            
            **🔗 Duplicate detection**  
            Find and manage duplicates
            """)
            
            # System resources
            st.markdown("---")
            if st.button("💻 System Resources"):
                LoadingScreen._show_system_resources()
    
    @staticmethod
    def _show_system_resources():
        """Show system resource usage"""
        with st.expander("💻 System Resources", expanded=True):
            try:
                import psutil
                
                # Memory usage
                memory = psutil.virtual_memory()
                st.metric("Memory Usage", f"{memory.percent}%")
                
                # CPU usage
                cpu = psutil.cpu_percent(interval=1)
                st.metric("CPU Usage", f"{cpu}%")
                
                # Disk usage for current folder
                folder_path = st.session_state.get('folder_path', '/')
                if folder_path and os.path.exists(folder_path):
                    disk = psutil.disk_usage(folder_path)
                    st.metric("Disk Usage", f"{disk.percent}%")
                
            except Exception:
                st.info("System resource monitoring not available")


# Easy import for main app
def render_loading_screen():
    """Main entry point for loading screen"""
    LoadingScreen.render() 