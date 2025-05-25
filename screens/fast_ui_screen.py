# 🚀 Screen 1: Fast UI Screen - SIMPLIFIED & FOCUSED
# 📌 Purpose: Simple, welcoming folder selection focused on user task
# 🎯 Mission: Get user started immediately - just point to images and go!
# 🎨 Sprint 02: Clean, minimal design focused on the essential task

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader
from styles.style_injector import (
    inject_pixel_detective_styles,
    create_hero_section,
    create_styled_container,
    create_progress_bar,
    create_status_indicator
)


class FastUIScreen:
    """Screen 1: Simplified UI focused purely on folder selection"""
    
    @staticmethod
    def render():
        """Render the simplified fast UI screen"""
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
        # Compact hero section
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
        """Simplified folder selection focused on the essential task"""
        # Main task section
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin: 2rem 0; text-align: center;">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">📁 Select Your Image Folder</h2>
                <p style="color: var(--pd-text-secondary); margin-bottom: 2rem;">
                    Choose the folder containing your photos. I'll search all subfolders automatically.
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Get current folder path
        current_path = st.session_state.get('folder_path', '')
        
        # Simplified folder input - more compact
        col1, col2 = st.columns([4, 1])
        
        with col1:
            folder_path = st.text_input(
                "📂 Image folder path:",
                value=current_path,
                placeholder="Select your Pictures folder or browse...",
                help="Path to your image collection",
                key="folder_input",
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("📂 Browse", help="Browse for folder", key="browse_btn", use_container_width=True):
                FastUIScreen._open_system_file_dialog()
        
        # Update session state when path changes
        if folder_path != current_path:
            st.session_state.folder_path = folder_path
        
        # Quick shortcuts row
        st.markdown("**Quick shortcuts:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🏠 Pictures", key="quick_pictures", use_container_width=True):
                pictures_path = os.path.expanduser("~/Pictures")
                if os.path.exists(pictures_path):
                    st.session_state.folder_path = pictures_path
                    st.rerun()
                else:
                    st.warning("Pictures folder not found")
        
        with col2:
            if st.button("📥 Downloads", key="quick_downloads", use_container_width=True):
                downloads_path = os.path.expanduser("~/Downloads")
                if os.path.exists(downloads_path):
                    st.session_state.folder_path = downloads_path
                    st.rerun()
                else:
                    st.warning("Downloads folder not found")
        
        with col3:
            if st.button("🖥️ Desktop", key="quick_desktop", use_container_width=True):
                desktop_path = os.path.expanduser("~/Desktop")
                if os.path.exists(desktop_path):
                    st.session_state.folder_path = desktop_path
                    st.rerun()
                else:
                    st.warning("Desktop folder not found")
        
        with col4:
            if st.button("☁️ OneDrive", key="quick_onedrive", use_container_width=True):
                onedrive_path = os.path.expanduser("~/OneDrive/Pictures")
                if os.path.exists(onedrive_path):
                    st.session_state.folder_path = onedrive_path
                    st.rerun()
                else:
                    st.warning("OneDrive Pictures not found")
        
        # Show validation and start button
        if folder_path:
            FastUIScreen._show_validation_and_start(folder_path)
        else:
            st.markdown(
                '''
                <div class="pd-alert pd-alert-info" style="margin: 2rem 0; text-align: center;">
                    <div style="font-size: 1.2rem;">👆</div>
                    <div>
                        <strong>Choose a folder above to get started</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Use the browse button or quick shortcuts
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _open_system_file_dialog():
        """Open system file dialog for folder selection"""
        st.markdown(
            '''
            <div class="pd-alert pd-alert-info">
                <div style="font-size: 1.2rem;">💡</div>
                <div>
                    <strong>File Dialog Tip:</strong> Use the quick shortcuts above or type your folder path
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                        Common locations: Pictures, Downloads, Desktop, or OneDrive
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Show simple folder browser
        if st.button("🔍 Show Folder Browser", key="show_browser"):
            st.session_state.show_folder_browser = True
            st.rerun()
        
        # Simple folder browser if requested
        if st.session_state.get('show_folder_browser', False):
            FastUIScreen._show_simple_folder_browser()
    
    @staticmethod
    def _show_simple_folder_browser():
        """Show a simplified folder browser"""
        st.markdown("### 📂 Simple Folder Browser")
        
        # Get current path
        if 'browse_path' not in st.session_state:
            st.session_state.browse_path = os.path.expanduser("~/Pictures")
        
        current_path = st.session_state.browse_path
        
        # Navigation
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            st.markdown(f"**Current:** `{os.path.basename(current_path) or current_path}`")
        
        with col2:
            parent = os.path.dirname(current_path)
            if parent != current_path:
                if st.button("⬆️ Go Up", key="nav_up"):
                    st.session_state.browse_path = parent
                    st.rerun()
        
        with col3:
            if st.button("✅ Use", key="use_current", type="primary"):
                st.session_state.folder_path = current_path
                st.session_state.show_folder_browser = False
                st.rerun()
        
        # Show folders only
        try:
            if os.path.exists(current_path):
                folders = []
                for item in sorted(os.listdir(current_path)):
                    item_path = os.path.join(current_path, item)
                    if os.path.isdir(item_path):
                        # Quick image count
                        try:
                            files = os.listdir(item_path)[:20]  # Check first 20 files
                            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                            image_count = sum(1 for f in files if any(f.lower().endswith(ext) for ext in image_extensions))
                            folders.append((item, item_path, image_count))
                        except:
                            folders.append((item, item_path, 0))
                
                # Show folders in a simple list
                if folders:
                    for name, path, count in folders[:8]:  # Show max 8 folders
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            display_name = f"📁 {name}"
                            if count > 0:
                                display_name += f" ({count} images)"
                            
                            if st.button(display_name, key=f"folder_{name}", use_container_width=True):
                                st.session_state.browse_path = path
                                st.rerun()
                        
                        with col2:
                            if st.button("✅", key=f"select_{name}", help=f"Select {name}"):
                                st.session_state.folder_path = path
                                st.session_state.show_folder_browser = False
                                st.rerun()
                
                if st.button("❌ Close Browser", key="close_browser"):
                    st.session_state.show_folder_browser = False
                    st.rerun()
        
        except Exception as e:
            st.error(f"Cannot access folder: {str(e)}")
    
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
                    st.markdown(
                        f'''
                        <div class="pd-alert pd-alert-success pd-fade-in" style="margin: 2rem 0;">
                            <div style="font-size: 1.2rem;">✅</div>
                            <div>
                                <strong>Perfect!</strong> Found {image_count}+ images
                                <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                    Ready to make them searchable
                                </div>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
                    
                    # Big start button
                    if st.button("🚀 Start Building Your Image Search", type="primary", key="start_btn", use_container_width=True):
                        FastUIScreen._start_processing(folder_path)
                
                else:
                    # No images found
                    st.markdown(
                        '''
                        <div class="pd-alert pd-alert-warning">
                            <div style="font-size: 1.2rem;">⚠️</div>
                            <div>
                                <strong>No images found</strong> in this folder
                                <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                    Try a different folder with .jpg, .png, or other image files
                                </div>
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
            
            except Exception:
                # Can't read folder
                st.markdown(
                    '''
                    <div class="pd-alert pd-alert-warning">
                        <div style="font-size: 1.2rem;">❌</div>
                        <div>
                            <strong>Cannot access this folder</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                Check permissions and try again
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        
        else:
            # Folder doesn't exist
            st.markdown(
                '''
                <div class="pd-alert pd-alert-warning">
                    <div style="font-size: 1.2rem;">❌</div>
                    <div>
                        <strong>Folder not found</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Please check the path and try again
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _start_processing(folder_path: str):
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
            
            # Simple help
            with st.expander("💡 Need Help?"):
                st.markdown(
                    '''
                    **Quick steps:**
                    1. Click "Browse" or use quick shortcuts
                    2. Select your Photos/Pictures folder
                    3. Click "Start Building"
                    
                    **Common locations:**
                    - Pictures folder (recommended)
                    - Downloads folder
                    - Desktop folder
                    - OneDrive Photos
                    
                    The app will search all subfolders automatically!
                    '''
                )


# Global function for easy import
def render_fast_ui_screen():
    """Main entry point for simplified Screen 1"""
    FastUIScreen.render()