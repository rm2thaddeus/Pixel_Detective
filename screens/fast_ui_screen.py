# 🚀 Screen 1: Fast UI Screen - REDESIGNED FOR BETTER BALANCE
# 📌 Purpose: Simple, welcoming folder selection focused on user task
# 🎯 Mission: Get user started immediately - just point to images and go!
# 🎨 Sprint 02: Balanced layout with prominent folder browser

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
    """Screen 1: Redesigned UI with balanced folder selection"""
    
    @staticmethod
    def render():
        """Render the redesigned fast UI screen"""
        # Inject our custom styles
        inject_pixel_detective_styles()
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        FastUIScreen._render_welcome_header()
        FastUIScreen._render_balanced_folder_selection()
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
    def _render_balanced_folder_selection():
        """Redesigned folder selection with better balance and prominent browser"""
        # Get current folder path
        current_path = st.session_state.get('folder_path', '')
        
        # Compact input row - much smaller
        st.markdown("**📂 Image folder path:**")
        col1, col2, col3 = st.columns([6, 2, 2])
        
        with col1:
            folder_path = st.text_input(
                "folder_path",
                value=current_path,
                placeholder="Type path or use browser below...",
                help="Path to your image collection",
                key="folder_input",
                label_visibility="collapsed"
            )
        
        with col2:
            if st.button("🔍 Browse", help="Open folder browser", key="browse_btn", use_container_width=True):
                st.session_state.show_folder_browser = True
                st.rerun()
        
        with col3:
            if st.button("🏠 Pictures", help="Use Pictures folder", key="quick_pictures", use_container_width=True):
                pictures_path = os.path.expanduser("~/Pictures")
                if os.path.exists(pictures_path):
                    st.session_state.folder_path = pictures_path
                    st.rerun()
                else:
                    st.warning("Pictures folder not found")
        
        # Update session state when path changes
        if folder_path != current_path:
            st.session_state.folder_path = folder_path
        
        # Prominent folder browser - takes up most of the space
        FastUIScreen._render_prominent_folder_browser()
        
        # Show validation and start button
        if folder_path:
            FastUIScreen._show_validation_and_start(folder_path)
        else:
            st.markdown(
                '''
                <div class="pd-alert pd-alert-info" style="margin: 1rem 0; text-align: center;">
                    <div style="font-size: 1.2rem;">👆</div>
                    <div>
                        <strong>Browse folders below or type a path above</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Click any folder to explore or select it
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _render_prominent_folder_browser():
        """Prominent folder browser that takes up most of the space"""
        # Always show the folder browser - it's the main feature now
        st.markdown("---")
        st.markdown("### 📁 Folder Browser")
        
        # Get current browse path
        if 'browse_path' not in st.session_state:
            # Start with Pictures folder if it exists, otherwise home
            pictures_path = os.path.expanduser("~/Pictures")
            if os.path.exists(pictures_path):
                st.session_state.browse_path = pictures_path
            else:
                st.session_state.browse_path = os.path.expanduser("~")
        
        current_path = st.session_state.browse_path
        
        # Navigation bar
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**📍 Current location:** `{current_path}`")
        
        with col2:
            parent = os.path.dirname(current_path)
            if parent != current_path:
                if st.button("⬆️ Up", key="nav_up", use_container_width=True):
                    st.session_state.browse_path = parent
                    st.rerun()
            else:
                st.button("⬆️ Up", key="nav_up", disabled=True, use_container_width=True)
        
        with col3:
            if st.button("🏠 Home", key="nav_home", use_container_width=True):
                st.session_state.browse_path = os.path.expanduser("~")
                st.rerun()
        
        with col4:
            if st.button("✅ Use Current", key="use_current", type="primary", use_container_width=True):
                st.session_state.folder_path = current_path
                st.rerun()
        
        # Quick shortcuts row
        st.markdown("**🚀 Quick locations:**")
        shortcuts = FastUIScreen._get_folder_shortcuts()
        
        if shortcuts:
            # Display shortcuts in rows of 4
            for i in range(0, len(shortcuts), 4):
                cols = st.columns(4)
                for j, col in enumerate(cols):
                    if i + j < len(shortcuts):
                        name, path = shortcuts[i + j]
                        with col:
                            if st.button(name, key=f"shortcut_{i+j}", use_container_width=True):
                                if os.path.exists(path):
                                    st.session_state.browse_path = path
                                    st.rerun()
                                else:
                                    st.warning(f"{name} not found")
        
        # Main folder listing - Windows Explorer style
        st.markdown("**📂 Folders in this location:**")
        
        try:
            if os.path.exists(current_path):
                folders = []
                for item in sorted(os.listdir(current_path)):
                    item_path = os.path.join(current_path, item)
                    if os.path.isdir(item_path):
                        # Quick image count
                        try:
                            files = os.listdir(item_path)[:30]  # Check first 30 files
                            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
                            image_count = sum(1 for f in files if any(f.lower().endswith(ext) for ext in image_extensions))
                            folders.append((item, item_path, image_count))
                        except:
                            folders.append((item, item_path, 0))
                
                # Show folders in a grid - Windows Explorer style
                if folders:
                    # Show folders in rows of 2 for better visibility
                    for i in range(0, len(folders), 2):
                        cols = st.columns(2)
                        
                        for j, col in enumerate(cols):
                            if i + j < len(folders):
                                name, path, count = folders[i + j]
                                
                                with col:
                                    # Create folder card with image count
                                    if count > 0:
                                        folder_info = f"📁 **{name}**\n🖼️ {count} images found"
                                        button_type = "primary" if count > 5 else "secondary"
                                    else:
                                        folder_info = f"📁 **{name}**\n📄 No images detected"
                                        button_type = "secondary"
                                    
                                    # Two buttons per folder: Browse and Select
                                    subcol1, subcol2 = st.columns([3, 1])
                                    
                                    with subcol1:
                                        if st.button(folder_info, key=f"browse_folder_{i+j}", use_container_width=True):
                                            st.session_state.browse_path = path
                                            st.rerun()
                                    
                                    with subcol2:
                                        if st.button("✅", key=f"select_folder_{i+j}", help=f"Select {name}", use_container_width=True):
                                            st.session_state.folder_path = path
                                            st.rerun()
                    
                    # Show count info
                    if len(folders) > 10:
                        st.info(f"📁 Showing first 10 of {len(folders)} folders. Navigate to see more.")
                
                else:
                    st.info("📁 No folders found in this location")
            
            else:
                st.error("❌ Cannot access this location")
        
        except PermissionError:
            st.error("❌ Permission denied - cannot access this folder")
        except Exception as e:
            st.error(f"❌ Error browsing folder: {str(e)}")
    
    @staticmethod
    def _get_folder_shortcuts():
        """Get list of useful folder shortcuts"""
        shortcuts = []
        home = os.path.expanduser("~")
        
        # Common folders that usually exist
        common_folders = [
            ("📸 Pictures", os.path.join(home, "Pictures")),
            ("📥 Downloads", os.path.join(home, "Downloads")),
            ("🖥️ Desktop", os.path.join(home, "Desktop")),
            ("📁 Documents", os.path.join(home, "Documents")),
        ]
        
        # Only add folders that exist
        for name, path in common_folders:
            if os.path.exists(path):
                shortcuts.append((name, path))
        
        # Add OneDrive if it exists
        onedrive_paths = [
            ("☁️ OneDrive Pictures", os.path.join(home, "OneDrive", "Pictures")),
            ("☁️ OneDrive Photos", os.path.join(home, "OneDrive", "Photos")),
        ]
        for name, path in onedrive_paths:
            if os.path.exists(path):
                shortcuts.append((name, path))
                break  # Only add one OneDrive option
        
        # Add common photo locations
        photo_locations = [
            ("📷 Camera Roll", os.path.join(home, "Pictures", "Camera Roll")),
            ("📱 Phone Photos", os.path.join(home, "Pictures", "Phone")),
        ]
        for name, path in photo_locations:
            if os.path.exists(path):
                shortcuts.append((name, path))
        
        return shortcuts
    
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
                                    Try browsing to a folder with .jpg, .png, or other image files
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
                            Please check the path or browse to a valid folder
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
                        Browse and select your image folder
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
                    1. Browse folders using the main interface
                    2. Click folders to explore them
                    3. Click ✅ to select a folder
                    4. Click "Start Building" when ready
                    
                    **Tips:**
                    - Look for folders with image counts
                    - Use quick shortcuts for common locations
                    - The app searches all subfolders automatically
                    '''
                )


# Global function for easy import
def render_fast_ui_screen():
    """Main entry point for redesigned Screen 1"""
    FastUIScreen.render()