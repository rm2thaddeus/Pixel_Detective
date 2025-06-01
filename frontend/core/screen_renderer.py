# 🎛️ Main Screen Renderer for Pixel Detective
# 📌 Purpose: Route between the 3 screens based on app state
# 🎯 Mission: Seamless navigation with proper state management

import streamlit as st
from core.app_state import AppState, AppStateManager
from screens.fast_ui_screen import render_fast_ui_screen
from screens.loading_screen import render_loading_screen
from screens.advanced_ui_screen import render_advanced_ui_screen
from core.background_loader import background_loader
from styles.style_injector import inject_pixel_detective_styles
from components.accessibility import AccessibilityEnhancer

# Helper to run async code in Streamlit. Required if calling async functions from sync Streamlit callbacks.
# However, if the entire chain from main() is async, this might not be strictly needed everywhere,
# but good to have for isolated async calls within sync contexts if they arise.
# For now, we assume the main path will be async.

class ScreenRenderer:
    """Central renderer that manages the 3-screen flow"""
    
    @staticmethod
    async def render():
        """Render the appropriate screen based on current app state"""
        
        AppStateManager.init_session_state()
        
        current_state = AppStateManager.get_current_state()
        folder_path = st.session_state.get('folder_path')

        # Check if FAST_UI has signaled to start loading
        if current_state == AppState.FAST_UI and st.session_state.get('trigger_loading', False):
            if folder_path:
                AppStateManager.transition_to_loading(folder_path)
                st.session_state.trigger_loading = False # Consume the trigger
                
                # 🚀 PERFORMANCE FIX: Don't create managers here - let background loader handle it
                # This was causing 68+ second startup times by loading models immediately
                
                # --- BEGIN CRITICAL LOGGING ---
                st.session_state.renderer_log = st.session_state.get('renderer_log', [])
                st.session_state.renderer_log.append(f"RENDERER: Transitioning to loading for {folder_path}")
                # --- END CRITICAL LOGGING ---

                # Start the background loading pipeline - it will create managers when needed
                if not background_loader.progress.is_loading: # Avoid starting if already in progress (e.g. from error retry)
                    background_loader.start_loading_pipeline(folder_path)
                    # --- BEGIN CRITICAL LOGGING ---
                    st.session_state.renderer_log.append(f"RENDERER: Called start_loading_pipeline for {folder_path}.")
                    # --- END CRITICAL LOGGING ---
                else:
                    # --- BEGIN CRITICAL LOGGING ---
                    st.session_state.renderer_log.append("RENDERER: Loading already in progress, not restarting.")
                    # --- END CRITICAL LOGGING ---
                
                current_state = AppState.LOADING # Update current_state for the next block
                st.rerun() # Rerun to immediately go to loading screen render path
            else:
                st.warning("Folder path not set, cannot trigger loading.")
                st.session_state.trigger_loading = False # Consume trigger

        if current_state == AppState.FAST_UI:
            await ScreenRenderer._render_fast_ui()
        elif current_state == AppState.LOADING:
            # Ensure the loader is started if we directly land in LOADING state (e.g. after app restart with state preserved)
            # This is a safeguard, primary start is above.
            if folder_path and not background_loader.progress.is_loading and not AppStateManager.is_ready_for_advanced():
                # --- BEGIN CRITICAL LOGGING ---
                st.session_state.renderer_log = st.session_state.get('renderer_log', [])
                st.session_state.renderer_log.append(f"RENDERER (SAFEGUARD): Starting loading pipeline for {folder_path}")
                # --- END CRITICAL LOGGING ---
                background_loader.start_loading_pipeline(folder_path)
                # --- BEGIN CRITICAL LOGGING ---
                st.session_state.renderer_log.append(f"RENDERER (SAFEGUARD): Called start_loading_pipeline for {folder_path}.")
                # --- END CRITICAL LOGGING ---

                # No rerun here, loading screen will handle it.
            await ScreenRenderer._render_loading()
        elif current_state == AppState.ADVANCED_UI:
            await ScreenRenderer._render_advanced_ui()
        elif current_state == AppState.ERROR:
            await ScreenRenderer._render_error()
        else:
            # Fallback to fast UI
            st.session_state.app_state = AppState.FAST_UI
            await ScreenRenderer._render_fast_ui()
    
    @staticmethod
    async def _render_fast_ui():
        """Render Screen 1: Fast UI"""
        try:
            await render_fast_ui_screen()
        except Exception as e:
            st.error(f"Error in Fast UI: {str(e)}")
            st.exception(e)
    
    @staticmethod
    async def _render_loading():
        """Render Screen 2: Loading"""
        try:
            await render_loading_screen()
        except Exception as e:
            st.error(f"Error in Loading screen: {str(e)}")
            st.exception(e)
            # Fallback to fast UI on error
            AppStateManager.reset_to_fast_ui()
    
    @staticmethod
    async def _render_advanced_ui():
        """Render Screen 3: Advanced UI"""
        try:
            await render_advanced_ui_screen()
        except Exception as e:
            st.error(f"Error in Advanced UI: {str(e)}")
            st.exception(e)
            # Show error but don't reset state - user can try to continue
    
    @staticmethod
    async def _render_error():
        """Render error recovery screen"""
        st.title("❌ Something Went Wrong")
        
        error_message = st.session_state.get('error_message', 'Unknown error occurred')
        can_retry = st.session_state.get('can_retry', True)
        
        st.error(f"**Error:** {error_message}")
        
        if can_retry:
            st.markdown("### 🔄 Recovery Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Try Again", type="primary"):
                    folder_path_retry = st.session_state.get('folder_path', '')
                    if folder_path_retry:
                        AppStateManager.transition_to_loading(folder_path_retry)
                        # 🚀 PERFORMANCE FIX: Let background loader create managers when needed
                        # Start the background loading pipeline - it will create managers when needed
                        if not background_loader.progress.is_loading:
                             background_loader.start_loading_pipeline(folder_path_retry)
                        st.rerun()
                    else:
                        AppStateManager.reset_to_fast_ui()
            
            with col2:
                if st.button("📁 Choose Different Folder"):
                    AppStateManager.reset_to_fast_ui()
                    st.rerun()
            
            with col3:
                if st.button("ℹ️ Report Issue"):
                    ScreenRenderer._show_error_report()
        else:
            st.markdown("### 🆘 Manual Recovery Required")
            st.warning("This error requires manual intervention. Please restart the application.")
            
            if st.button("🔄 Restart Application"):
                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # Show error details
        with st.expander("🔍 Error Details", expanded=False):
            st.markdown("**Error Message:**")
            st.code(error_message)
            
            st.markdown("**Session State:**")
            state_info = {
                'app_state': str(st.session_state.get('app_state', 'Unknown')),
                'loading_phase': str(st.session_state.get('loading_phase', 'None')),
                'folder_path': st.session_state.get('folder_path', 'None'),
                'ui_deps_loaded': st.session_state.get('ui_deps_loaded', False),
                'models_loaded': st.session_state.get('models_loaded', False),
                'database_ready': st.session_state.get('database_ready', False)
            }
            
            for key, value in state_info.items():
                st.text(f"{key}: {value}")
    
    @staticmethod
    def _show_error_report():
        """Show error reporting interface"""
        with st.expander("📧 Error Report", expanded=True):
            st.markdown("""
            **To report this issue:**
            
            1. **Take a screenshot** of this error page
            2. **Copy the error details** from the section above
            3. **Describe what you were doing** when the error occurred
            4. **Send to support** with your system information
            
            **System Information:**
            """)
            
            try:
                import platform
                import sys
                
                st.code(f"""
Operating System: {platform.system()} {platform.release()}
Python Version: {sys.version}
Streamlit Version: {st.__version__}
Error Time: {st.session_state.get('error_time', 'Unknown')}
Folder Path: {st.session_state.get('folder_path', 'None')}
Image Count: {len(st.session_state.get('image_files', []))}
                """)
            except Exception:
                st.text("System information unavailable")
    
    @staticmethod
    async def show_debug_info():
        """Show debug information (for development)"""
        if st.checkbox("🔧 Show Debug Info"):
            with st.expander("🛠️ Debug Information", expanded=True):
                st.markdown("**Current State:**")
                st.json({
                    'app_state': str(st.session_state.get('app_state', 'Unknown')),
                    'loading_phase': str(st.session_state.get('loading_phase', 'None')),
                    'progress': st.session_state.get('current_progress', 0),
                    'folder_selected': st.session_state.get('folder_selected', False),
                    'ui_deps_loaded': st.session_state.get('ui_deps_loaded', False),
                    'models_loaded': st.session_state.get('models_loaded', False),
                    'database_ready': st.session_state.get('database_ready', False),
                    'image_count': len(st.session_state.get('image_files', [])),
                    'log_count': len(st.session_state.get('loading_logs', []))
                })
                
                st.markdown("**Recent Logs:**")
                logs = st.session_state.get('loading_logs', [])
                if logs:
                    for log in logs[-5:]:
                        st.text(log)
                else:
                    st.text("No logs available")
                
                # Manual state controls
                st.markdown("**Manual Controls:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("→ Fast UI"):
                        AppStateManager.reset_to_fast_ui()
                        st.rerun()
                
                with col2:
                    if st.button("→ Loading"):
                        folder_path = st.session_state.get('folder_path', '')
                        if folder_path:
                            AppStateManager.transition_to_loading(folder_path)
                            st.rerun()
                
                with col3:
                    if st.button("→ Advanced"):
                        AppStateManager.transition_to_advanced()
                        st.rerun()

# This is the function imported by app.py
async def render_app():
    AccessibilityEnhancer.add_skip_navigation()

    renderer = ScreenRenderer()
    await renderer.render()

    # Apply custom visual styles globally after rendering main content
    inject_pixel_detective_styles() # This should handle main visual styles

    # Explicitly inject accessibility-specific CSS.
    # If inject_pixel_detective_styles already includes these, this might be redundant
    # but it's safer to call it to ensure accessibility styles are applied.
    AccessibilityEnhancer.inject_accessibility_styles()

    # Optionally, show debug info
    if st.session_state.get("show_debug_info", False):
        await ScreenRenderer.show_debug_info() 