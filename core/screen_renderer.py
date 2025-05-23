# 🎛️ Main Screen Renderer for Pixel Detective
# 📌 Purpose: Route between the 3 screens based on app state
# 🎯 Mission: Seamless navigation with proper state management

import streamlit as st
from core.app_state import AppState, AppStateManager
from screens.fast_ui_screen import render_fast_ui_screen
from screens.loading_screen import render_loading_screen
from screens.advanced_ui_screen import render_advanced_ui_screen


class ScreenRenderer:
    """Central renderer that manages the 3-screen flow"""
    
    @staticmethod
    def render():
        """Render the appropriate screen based on current app state"""
        # Initialize session state if needed
        AppStateManager.init_session_state()
        
        # Get current state
        current_state = AppStateManager.get_current_state()
        
        # Route to appropriate screen
        if current_state == AppState.FAST_UI:
            ScreenRenderer._render_fast_ui()
        elif current_state == AppState.LOADING:
            ScreenRenderer._render_loading()
        elif current_state == AppState.ADVANCED_UI:
            ScreenRenderer._render_advanced_ui()
        elif current_state == AppState.ERROR:
            ScreenRenderer._render_error()
        else:
            # Fallback to fast UI
            st.session_state.app_state = AppState.FAST_UI
            ScreenRenderer._render_fast_ui()
    
    @staticmethod
    def _render_fast_ui():
        """Render Screen 1: Fast UI"""
        try:
            render_fast_ui_screen()
        except Exception as e:
            st.error(f"Error in Fast UI: {str(e)}")
            st.exception(e)
    
    @staticmethod
    def _render_loading():
        """Render Screen 2: Loading"""
        try:
            render_loading_screen()
        except Exception as e:
            st.error(f"Error in Loading screen: {str(e)}")
            st.exception(e)
            # Fallback to fast UI on error
            AppStateManager.reset_to_fast_ui()
    
    @staticmethod
    def _render_advanced_ui():
        """Render Screen 3: Advanced UI"""
        try:
            render_advanced_ui_screen()
        except Exception as e:
            st.error(f"Error in Advanced UI: {str(e)}")
            st.exception(e)
            # Show error but don't reset state - user can try to continue
    
    @staticmethod
    def _render_error():
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
                    # Reset to loading state and retry
                    folder_path = st.session_state.get('folder_path', '')
                    if folder_path:
                        AppStateManager.transition_to_loading(folder_path)
                        from core.background_loader import background_loader
                        background_loader.start_loading_pipeline(folder_path)
                        st.rerun()
                    else:
                        AppStateManager.reset_to_fast_ui()
                        st.rerun()
            
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
    def show_debug_info():
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


# Global function for easy import
def render_app():
    """Main entry point for the entire application"""
    try:
        # Load minimal CSS
        st.markdown("""
        <style>
        .main { padding-top: 1rem; }
        .stAlert { margin: 1rem 0; }
        .loading-spinner { 
            text-align: center; 
            font-size: 2rem; 
            animation: spin 2s linear infinite; 
        }
        @keyframes spin { 
            0% { transform: rotate(0deg); } 
            100% { transform: rotate(360deg); } 
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Render the appropriate screen
        ScreenRenderer.render()
        
        # Show debug info in development
        # ScreenRenderer.show_debug_info()  # Uncomment for debugging
        
    except Exception as e:
        st.error("Critical application error occurred")
        st.exception(e)
        
        if st.button("🔄 Force Reset"):
            # Emergency reset
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun() 