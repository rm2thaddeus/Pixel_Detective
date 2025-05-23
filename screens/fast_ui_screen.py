# 🚀 Screen 1: Fast UI Screen
# 📌 Purpose: Instant launch with folder selection and smart triggers
# 🎯 Mission: Get user started immediately with minimal loading

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader


class FastUIScreen:
    """Screen 1: Instant UI with folder selection"""
    
    @staticmethod
    def render():
        """Render the fast UI screen"""
        FastUIScreen._render_header()
        FastUIScreen._render_system_metrics()
        FastUIScreen._render_folder_selection()
        FastUIScreen._render_welcome_info()
        FastUIScreen._render_sidebar()
    
    @staticmethod
    def _render_header():
        """Render the main header"""
        st.title("🕵️‍♂️ Pixel Detective")
        st.markdown("### Lightning-fast AI image search")
        st.markdown("---")
    
    @staticmethod
    def _render_system_metrics():
        """Show instant system status metrics"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Startup Time", "< 1 second", "⚡ Instant")
        
        with col2:
            ui_status = "Ready" if st.session_state.get('ui_deps_loaded', False) else "Standby"
            ui_delta = "🎨 Smart Loading"
            st.metric("UI System", ui_status, ui_delta)
        
        with col3:
            st.metric("AI Models", "On-demand", "🤖 Efficient")
    
    @staticmethod
    def _render_folder_selection():
        """Render folder selection interface"""
        st.markdown("### 📁 Select Your Image Collection")
        
        # Get current folder path
        current_path = st.session_state.get('folder_path', '')
        
        # Folder input with smart triggers
        folder_path = st.text_input(
            "Enter your image folder path:",
            value=current_path,
            placeholder="C:\\Users\\YourName\\Pictures",
            help="Enter the path to your image collection",
            key="folder_input"
        )
        
        # Update session state when path changes
        if folder_path != current_path:
            st.session_state.folder_path = folder_path
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("📂 Browse Folder", help="Browse for your image folder"):
                st.info("💡 **Tip:** Type or paste your folder path above and click Start Processing")
        
        with col2:
            # Main action button
            can_start = folder_path and os.path.exists(folder_path)
            button_text = "🚀 Start Processing" if can_start else "🚀 Start Processing"
            
            if st.button(button_text, type="primary", disabled=not can_start):
                if folder_path and os.path.exists(folder_path):
                    FastUIScreen._start_processing(folder_path)
                elif folder_path:
                    st.error("❌ Folder not found. Please check the path.")
                else:
                    st.error("❌ Please enter a folder path.")
        
        with col3:
            if st.button("ℹ️ Help", help="Get help with folder selection"):
                FastUIScreen._show_help()
        
        # Show validation feedback
        if folder_path:
            FastUIScreen._show_path_validation(folder_path)
    
    @staticmethod
    def _show_path_validation(folder_path: str):
        """Show real-time validation of folder path"""
        if os.path.exists(folder_path):
            if os.path.isdir(folder_path):
                # Quick preview of folder contents
                try:
                    files = os.listdir(folder_path)
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                    image_count = sum(1 for f in files[:100] if any(f.lower().endswith(ext) for ext in image_extensions))
                    
                    if image_count > 0:
                        st.success(f"✅ Valid folder! Found {image_count}+ images")
                    else:
                        st.warning("⚠️ Folder exists but no images found in first 100 files")
                except Exception:
                    st.info("📁 Folder exists and is readable")
            else:
                st.error("❌ Path exists but is not a folder")
        else:
            st.error("❌ Folder not found")
    
    @staticmethod
    def _start_processing(folder_path: str):
        """Start the processing pipeline"""
        # Transition to loading state
        AppStateManager.transition_to_loading(folder_path)
        
        # Start background loading
        if background_loader.start_loading_pipeline(folder_path):
            st.success("🚀 Processing started! Switching to progress view...")
            st.rerun()
        else:
            st.error("❌ Could not start processing. Please try again.")
    
    @staticmethod
    def _show_help():
        """Show help information"""
        with st.expander("💡 Help: Selecting Your Image Folder", expanded=True):
            st.markdown("""
            **How to find your image folder path:**
            
            **Windows:**
            - Open File Explorer
            - Navigate to your pictures folder
            - Click on the address bar and copy the path
            - Example: `C:\\Users\\YourName\\Pictures`
            
            **Mac:**
            - Open Finder
            - Navigate to your pictures folder
            - Right-click and select "Get Info"
            - Copy the path from "Where"
            - Example: `/Users/YourName/Pictures`
            
            **Tips:**
            - The app will scan all subfolders automatically
            - Supported formats: JPG, PNG, GIF, BMP, TIFF, WebP
            - Larger collections take longer to process
            """)
    
    @staticmethod
    def _render_welcome_info():
        """Show welcome information and smart loading explanation"""
        st.markdown("---")
        st.markdown("### ✨ Smart Loading System")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🚀 How it works:**
            - ✅ App loads instantly (<1s)
            - 📁 Select your image folder above
            - 🎨 UI loads automatically when needed
            - 🤖 AI loads only when processing
            """)
        
        with col2:
            st.markdown("""
            **🧠 Smart & Efficient:**
            - No waiting for unused features
            - Load the right thing at the right time
            - Fast response when you need it
            - Zero bloat, maximum speed
            """)
        
        # Dynamic status based on current state
        if st.session_state.get('folder_path', ''):
            if os.path.exists(st.session_state.folder_path):
                st.info("🎯 **Ready to process!** Click 'Start Processing' to begin.")
            else:
                st.warning("⚠️ **Please check your folder path** - we couldn't find that location.")
        else:
            st.info("💡 **Start by entering your image folder path above** - the system will prepare as you work!")
    
    @staticmethod
    def _render_sidebar():
        """Render contextual sidebar for Fast UI screen"""
        with st.sidebar:
            st.markdown("### 🔧 System Status")
            
            # UI System status
            if st.session_state.get('ui_deps_loaded', False):
                st.success("✅ UI system ready!")
            else:
                st.info("⏸️ UI system on standby")
            
            # AI Models status
            st.info("🤖 AI models: Load on demand")
            
            # Database status
            st.info("💾 Database: Not connected")
            
            # Current status
            if st.session_state.get('folder_path', '') and os.path.exists(st.session_state.folder_path):
                st.metric("Status", "Ready to Process", "🚀 Click Start Processing")
            else:
                st.metric("Status", "Waiting", "📁 Select folder above")
            
            st.markdown("---")
            st.markdown("### 💡 Next Steps")
            st.markdown("""
            1. **Enter folder path** above
            2. **System prepares** automatically  
            3. **Click Start Processing**
            4. **Enjoy advanced features!**
            """)
            
            # Quick tips
            st.markdown("---")
            st.markdown("### 🎯 Quick Tips")
            st.markdown("""
            - **Large collections?** Processing takes longer but works better
            - **Subfolders included** automatically
            - **All formats supported** (JPG, PNG, etc.)
            - **Cancel anytime** during processing
            """)
            
            # System info
            if st.button("🔍 System Info"):
                FastUIScreen._show_system_info()
    
    @staticmethod
    def _show_system_info():
        """Show system information modal"""
        with st.expander("🖥️ System Information", expanded=True):
            import platform
            import psutil
            
            st.markdown(f"""
            **System:**
            - OS: {platform.system()} {platform.release()}
            - Python: {platform.python_version()}
            - Memory: {psutil.virtual_memory().total // (1024**3)} GB
            
            **Pixel Detective:**
            - Version: 1.0.0
            - Mode: Smart Progressive Loading
            - State: Fast UI Ready
            """)


# Easy import for main app
def render_fast_ui_screen():
    """Main entry point for fast UI screen"""
    FastUIScreen.render() 