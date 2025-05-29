# 🚀 Screen 1: Fast UI Screen - MINIMAL & FUNCTIONAL
# 📌 Purpose: Simple folder selection that actually works
# 🎯 Mission: Get user started immediately with working buttons
# 🎨 Sprint 02: Minimal UI focused on functionality

import os
import streamlit as st
import sys
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader
from styles.style_injector import (
    inject_pixel_detective_styles,
    create_status_indicator
)

# Import tkinter for file dialog
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
<<<<<<< HEAD

# Import for background model preloading
# from core.optimized_model_manager import get_optimized_model_manager, ModelType
=======
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb


class FastUIScreen:
    """Screen 1: Minimal UI with working folder selection"""
    
    @staticmethod
    def render():
        """Render the minimal fast UI screen"""
        # Inject our custom styles
        inject_pixel_detective_styles()
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        FastUIScreen._render_welcome_header()
        FastUIScreen._render_simple_folder_selection()
        FastUIScreen._render_minimal_sidebar()
        
        # Close animation wrapper
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Start background preparation when appropriate
        FastUIScreen._start_background_preparation()
    
    @staticmethod
    def _render_welcome_header():
        """Simple welcome header focused on the task"""
        st.markdown(
            '''
            <div class="pd-hero pd-fade-in" style="text-align: center; margin-bottom: 2rem; padding: 2rem 0;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🕵️‍♂️</div>
                <h1 class="pd-title" style="color: white; margin-bottom: 0.5rem;">Pixel Detective</h1>
                <p class="pd-subheading" style="color: rgba(255, 255, 255, 0.9); margin-bottom: 0;">
                    Point me to your photos and I'll make them searchable ✨
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def _render_simple_folder_selection():
        """Simple folder selection with working file dialog"""
        # Get current folder path
        current_path = st.session_state.get('folder_path', '')
        
        # Simple input row
        st.markdown("**📂 Select your image folder:**")
        col1, col2 = st.columns([7, 3])
        
        with col1:
            folder_path = st.text_input(
                "folder_path",
                value=current_path,
                placeholder="Click 'Browse' to select folder or type path here...",
                help="Path to your image collection",
                key="folder_input",
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("📁 Browse", help="Open folder selection dialog", key="browse_btn", use_container_width=True):
                if TKINTER_AVAILABLE:
                    try:
                        # Create a root window and hide it
                        root = tk.Tk()
                        root.withdraw()
                        root.wm_attributes('-topmost', 1)
                        
                        # Open folder dialog
                        selected_folder = filedialog.askdirectory(
                            title="Select Image Folder",
                            initialdir=os.path.expanduser("~/Pictures") if os.path.exists(os.path.expanduser("~/Pictures")) else os.path.expanduser("~")
                        )
                        
                        # Clean up
                        root.destroy()
                        
                        if selected_folder:
                            st.session_state.folder_path = selected_folder
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"Could not open file dialog: {e}")
                        st.info("Please type the folder path manually in the text box above.")
                else:
                    st.error("File dialog not available. Please type the folder path manually.")
        
        # Update session state when path changes
        if folder_path != current_path:
            st.session_state.folder_path = folder_path
        
        # Show validation and start button
        if folder_path:
            FastUIScreen._show_validation_and_start(folder_path)
        else:
            st.markdown(
                '''
                <div class="pd-alert pd-alert-info" style="margin: 2rem 0; text-align: center; padding: 2rem;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">📁</div>
                    <div>
                        <strong>Ready to get started!</strong>
                        <div style="margin-top: 1rem; font-size: 1rem;">
                            Click "Browse" to select your image folder<br>
                            or type the path in the box above
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _show_validation_and_start(folder_path: str):
        """Show validation and start button"""
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            # Quick image count
            try:
                files = os.listdir(folder_path)[:50]  # Check first 50 files
                image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                image_count = sum(1 for f in files if any(f.lower().endswith(ext) for ext in image_extensions))
                
                if image_count > 0:
                    # Success - ready to start
                    st.markdown("---")
                    st.markdown(
                        f'''
                        <div class="pd-alert pd-alert-success pd-fade-in" style="margin: 1rem 0;">
                            <div style="font-size: 1.2rem;">✅</div>
                            <div>
                                <strong>Perfect!</strong> Found {image_count}+ images in selected folder
                                <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                    Ready to build your searchable image database
                                </div>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                    
                    # Big start button
                    if st.button("🚀 Start Building Your Image Search Engine", type="primary", key="start_btn", use_container_width=True):
                        FastUIScreen._start_processing(folder_path)
                
                else:
                    # No images found
                    st.markdown("---")
                    st.markdown(
                        '''
                        <div class="pd-alert pd-alert-warning">
                            <div style="font-size: 1.2rem;">⚠️</div>
                            <div>
                                <strong>No images found</strong> in this folder
                                <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                    Try selecting a folder with .jpg, .png, or other image files
                                </div>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
            
            except Exception:
                # Can't read folder
                st.markdown("---")
                st.markdown(
                    '''
                    <div class="pd-alert pd-alert-warning">
                        <div style="font-size: 1.2rem;">❌</div>
                        <div>
                            <strong>Cannot access this folder</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                Check permissions and try a different folder
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        
        else:
            # Folder doesn't exist
            st.markdown("---")
            st.markdown(
                '''
                <div class="pd-alert pd-alert-warning">
                    <div style="font-size: 1.2rem;">❌</div>
                    <div>
                        <strong>Folder not found</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Please check the path or use the Browse button
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _start_processing(folder_path: str):
<<<<<<< HEAD
        """Signal ScreenRenderer to start the processing pipeline"""
        st.session_state.folder_path = folder_path
        st.session_state.trigger_loading = True
        
        # Show a message indicating that loading will start
        st.markdown(
            '''
            <div class="pd-alert pd-alert-success pd-fade-in" style="margin: 1rem 0; text-align: center;">
                <div style="font-size: 1.2rem;">🚀</div>
                <div>
                    <strong>Preparing to process your images...</strong>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                        The application will now proceed to the loading screen.
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        # Add a small delay for the user to see the message before rerun
        import time
        time.sleep(0.5) 
        st.rerun()
    
    @staticmethod
    def _start_background_preparation():
        """
        Start background preparation (import heavy libraries) if not already done.
        Models are preloaded by FastStartupManager.
        """
        if not background_loader.progress.heavy_modules_imported and \
           not background_loader.progress.heavy_import_started:
            background_loader.start_background_preparation()
    
    @staticmethod
    @st.cache_resource # Cache the lazy_import function itself if needed, or apply to its result per module
    def lazy_import(module_name):
        """Helper to lazy import modules within this class, reducing startup impact."""
        try:
            if module_name in sys.modules:
                return sys.modules[module_name]
            
            # Ensure 'importlib.util' is imported if not already
            if 'importlib' not in sys.modules or 'importlib.util' not in sys.modules:
                 import importlib.util # Direct import ok here as it's for the utility itself

            spec = importlib.util.find_spec(module_name)
            if spec is None:
                # Fallback for streamlit logger if logging module itself fails
                if module_name == 'logging' and hasattr(st, 'warning'):
                    st.warning(f"Could not find spec for module: {module_name}")
                return None 
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        except ImportError as e:
            # Fallback for streamlit logger
            if module_name == 'logging' and hasattr(st, 'error'):
                 st.error(f"Failed to lazy import {module_name}: {e}")
            return None
    
    @staticmethod
    def _render_minimal_sidebar():
        """Minimal sidebar with only essential information"""
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🕵️‍♂️ Pixel Detective")
            st.caption("Fast, Smart Image Search")
            st.markdown("---")
            
            # App State Indicator (visual cue)
            current_app_state = st.session_state.get('app_state', AppState.FAST_UI)
            if current_app_state == AppState.FAST_UI:
                create_status_indicator("⚡ Ready for Action", "success")
            elif current_app_state == AppState.LOADING:
                create_status_indicator("⏳ Processing Images...", "progress")
            elif current_app_state == AppState.ADVANCED_UI:
                create_status_indicator("🎉 Database Ready", "success")

            st.markdown("---")
            st.markdown("📄 **Sprint 05 Goals**")
            st.markdown("- FAST_UI (<1s)")
            st.markdown("- LOADING screen")
            st.markdown("- ADVANCED_UI tabs")
            st.markdown("- Startup Optimization")
            st.markdown("---")
            
            # Debug info toggle (optional)
            if st.checkbox("Show Debug Info", key="fast_ui_debug_checkbox", value=False):
                with st.expander("FastUI Debug", expanded=False):
                    st.write(f"Current App State: {current_app_state.value}")
                    st.write(f"Folder Path: {st.session_state.get('folder_path', 'Not set')}")
                    st.write(f"Trigger Loading: {st.session_state.get('trigger_loading', False)}")
                    st.write(f"Background Prep Started: {st.session_state.get('background_prep_started', False)}")
                    st.write(f"Tkinter Available: {TKINTER_AVAILABLE}")
                    if st.button("Test Background Prep Manually"):
                        FastUIScreen._start_background_preparation()
                        st.success("Manually triggered background prep.")
=======
        """Start the processing pipeline"""
        # Show starting message
        st.markdown(
            '''
            <div class="pd-alert pd-alert-success pd-celebrate">
                <div style="font-size: 1.2rem;">🚀</div>
                <div>
                    <strong>Starting your image search engine...</strong>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                        This will take a moment - please keep this tab open
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Transition to loading
        AppStateManager.transition_to_loading(folder_path)
        
        # Start background loading
        if background_loader.start_loading_pipeline(folder_path):
            import time
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("❌ Could not start processing. Please try again.")
    
    @staticmethod
    def _start_background_preparation():
        """Start loading heavy modules in background"""
        if (not st.session_state.get('background_prep_started', False) and 
            st.session_state.get('app_state', AppState.FAST_UI) == AppState.FAST_UI):
            
            st.session_state.background_prep_started = True
            background_loader.start_background_preparation()
    
    @staticmethod
    def _render_minimal_sidebar():
        """Minimal sidebar with only essential information"""
        with st.sidebar:
            # Simple status
            st.markdown(
                '''
                <div class="pd-card" style="text-align: center; margin-bottom: 1.5rem;">
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">🎯 Getting Started</h3>
                    <div style="font-size: 0.875rem; color: var(--pd-text-secondary);">
                        Select your image folder to begin
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # System status
            if st.session_state.get('background_prep_started', False):
                create_status_indicator("success", "System ready", True)
            else:
                create_status_indicator("info", "Preparing...", True)
            
            st.markdown("---")
            
            # Current selection info
            current_path = st.session_state.get('folder_path', '')
            if current_path:
                st.markdown("**📁 Selected folder:**")
                st.code(current_path)
                
                # Quick folder info
                if os.path.exists(current_path):
                    try:
                        files = os.listdir(current_path)[:20]
                        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                        image_count = sum(1 for f in files if any(f.lower().endswith(ext) for ext in image_extensions))
                        st.success(f"🖼️ {image_count}+ images found")
                    except:
                        st.warning("⚠️ Cannot read folder")
            
            st.markdown("---")
            
            # Simple help
            with st.expander("💡 Need Help?"):
                st.markdown(
                    '''
                    **How to use:**
                    1. Click "Browse" to select your image folder
                    2. Or type the folder path manually
                    3. Click "Start Building" when ready
                    
                    **Tips:**
                    - The app works with .jpg, .png, .gif, and other image formats
                    - It will search all subfolders automatically
                    - Make sure you have read access to the folder
                    '''
                )
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb


# Global function for easy import
def render_fast_ui_screen():
    """Main entry point for minimal Screen 1"""
<<<<<<< HEAD
    # Ensure sys is imported for lazy_import helper
    FastUIScreen.render() 
=======
    FastUIScreen.render()
>>>>>>> e999a0dbfc5b1dedbbf2bc17b574607da607c9fb
