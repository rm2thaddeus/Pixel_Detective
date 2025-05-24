# 🚀 Screen 1: Fast UI Screen - SIMPLIFIED VERSION
# 📌 Purpose: Simple, welcoming folder selection focused on user task
# 🎯 Mission: Get user started immediately without technical jargon

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader


class FastUIScreen:
    """Screen 1: Simplified UI with user-focused folder selection"""
    
    @staticmethod
    def render():
        """Render the simplified fast UI screen"""
        FastUIScreen._render_simple_header()
        FastUIScreen._render_folder_selection()
        FastUIScreen._render_simple_sidebar()
        
        # Start background preparation when appropriate
        FastUIScreen._start_background_preparation()
    
    @staticmethod
    def _render_simple_header():
        """Clean, welcoming header per UX design"""
        st.title("🕵️‍♂️ Pixel Detective")
        st.markdown("### Lightning-fast AI image search")
        
        # Welcoming message instead of technical metrics
        st.markdown("""
        Ready to search through your photos with AI? Just tell us where they are!
        
        🔍 **Search by description**: "sunset over lake"  
        🖼️ **Find similar images**: Upload any photo  
        🎮 **Play AI games**: Let AI guess your photos
        """)
        st.markdown("---")
    
    @staticmethod
    def _render_folder_selection():
        """Simple folder selection focused on user task"""
        st.markdown("### 📁 Select Your Image Collection")
        
        # Get current folder path
        current_path = st.session_state.get('folder_path', '')
        
        # Simple folder input
        folder_path = st.text_input(
            "Enter your image folder path:",
            value=current_path,
            placeholder="C:\\Users\\YourName\\Pictures",
            help="Path to your image collection",
            key="folder_input"
        )
        
        # Update session state when path changes
        if folder_path != current_path:
            st.session_state.folder_path = folder_path
        
        # Simplified action buttons
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Main action button
            can_start = folder_path and os.path.exists(folder_path)
            
            if st.button("🚀 Start Processing", type="primary", disabled=not can_start):
                if folder_path and os.path.exists(folder_path):
                    FastUIScreen._start_processing(folder_path)
                elif folder_path:
                    st.error("❌ Folder not found. Please check the path.")
                else:
                    st.error("❌ Please enter a folder path.")
        
        with col2:
            if st.button("💡 Help"):
                FastUIScreen._show_simple_help()
        
        # Show friendly validation feedback
        if folder_path:
            FastUIScreen._show_simple_validation(folder_path)
    
    @staticmethod
    def _show_simple_validation(folder_path: str):
        """Show user-friendly validation of folder path"""
        if os.path.exists(folder_path):
            if os.path.isdir(folder_path):
                # Quick preview of folder contents
                try:
                    files = os.listdir(folder_path)
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                    image_count = sum(1 for f in files[:100] if any(f.lower().endswith(ext) for ext in image_extensions))
                    
                    if image_count > 0:
                        st.success(f"✅ Great! Found {image_count}+ images in your collection")
                    else:
                        st.warning("⚠️ This folder doesn't seem to have images")
                except Exception:
                    st.info("📁 Folder found and accessible")
            else:
                st.error("❌ Please enter a folder path, not a file")
        else:
            st.error("❌ Folder not found - please check the path")
    
    @staticmethod
    def _show_simple_help():
        """Show simple, user-friendly help"""
        with st.expander("💡 How to find your image folder", expanded=True):
            st.markdown("""
            **Quick steps:**
            
            1. **Open File Explorer** (Windows) or **Finder** (Mac)
            2. **Go to your Pictures folder** or wherever you keep photos
            3. **Copy the path** from the address bar
            4. **Paste it above** and click "Start Processing"
            
            **Common locations:**
            - `C:\\Users\\YourName\\Pictures`
            - `C:\\Users\\YourName\\OneDrive\\Photos`
            - `D:\\Photos`
            
            **Tip:** The app will search all subfolders automatically!
            """)
    
    @staticmethod
    def _start_processing(folder_path: str):
        """Start the processing pipeline"""
        # Transition to loading state
        AppStateManager.transition_to_loading(folder_path)
        
        # Start background loading
        if background_loader.start_loading_pipeline(folder_path):
            st.success("🚀 Starting your personal image assistant...")
            st.rerun()
        else:
            st.error("❌ Could not start processing. Please try again.")
    
    @staticmethod
    def _start_background_preparation():
        """Start loading heavy modules in background (minimal UI impact)"""
        # Only start if not already started and no folder is being processed
        if (not st.session_state.get('background_prep_started', False) and 
            st.session_state.get('app_state', AppState.FAST_UI) == AppState.FAST_UI):
            
            st.session_state.background_prep_started = True
            
            # Start the actual background preparation (silent)
            background_loader.start_background_preparation()
    
    @staticmethod
    def _render_simple_sidebar():
        """Simple, context-aware sidebar for Screen 1"""
        with st.sidebar:
            st.markdown("### 🎯 Quick Start")
            
            # Show system status in simple terms
            if st.session_state.get('background_prep_started', False):
                st.success("✅ System ready for processing")
            else:
                st.info("⚡ Getting ready...")
            
            st.markdown("---")
            st.markdown("### 📂 Common Folders")
            
            # Quick folder suggestions
            common_paths = [
                ("📸 Pictures", os.path.expanduser("~/Pictures")),
                ("📥 Downloads", os.path.expanduser("~/Downloads")),
                ("🖥️ Desktop", os.path.expanduser("~/Desktop")),
            ]
            
            for name, path in common_paths:
                if st.button(f"{name}", key=f"quick_{name}"):
                    if os.path.exists(path):
                        st.session_state.folder_path = path
                        st.success(f"✅ Selected {name}")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {name} folder not found")
            
            st.markdown("---")
            st.markdown("### ✨ What's Coming")
            st.markdown("""
            After processing starts, you'll get:
            - 🔍 Smart photo search
            - 🎮 AI guessing games  
            - 🌐 Visual exploration
            - 👥 Duplicate detection
            """)


# Global function for easy import
def render_fast_ui_screen():
    """Main entry point for Screen 1"""
    FastUIScreen.render() 