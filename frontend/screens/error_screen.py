# frontend/screens/error_screen.py
import streamlit as st
from frontend.core.app_state import AppStateManager

def render_error_screen():
    """
    Renders the error recovery screen for the application.
    
    Presents the user with the error message and provides options to recover,
    such as trying the operation again or returning to the home screen.
    """
    st.title("❌ Something Went Wrong")
    
    error_message = st.session_state.get('error_message', 'An unknown error occurred. Please restart the application.')
    can_retry = st.session_state.get('can_retry', True)
    
    st.error(f"**An error occurred:**\n\n{error_message}")
    
    st.markdown("---")
    
    if can_retry:
        st.markdown("### 🔄 Recovery Options")
        col1, col2 = st.columns([1, 4])
        
        with col1:
            if st.button("🔄 Try Again", type="primary", use_container_width=True):
                folder_path_retry = st.session_state.get('folder_path', '')
                if folder_path_retry:
                    logger.info(f"Retrying ingestion for {folder_path_retry}")
                    AppStateManager.transition_to_loading(folder_path_retry)
                    st.rerun()
                else:
                    logger.warning("No folder path found to retry, returning to Fast UI.")
                    AppStateManager.reset_to_fast_ui()
                    st.rerun()
        
        with col2:
            if st.button("📁 Choose Different Folder", use_container_width=True):
                logger.info("User chose to select a different folder.")
                AppStateManager.reset_to_fast_ui()
                st.rerun()

    else:
        st.markdown("### 🆘 Manual Recovery Required")
        st.warning("This error cannot be automatically recovered. Please restart the application.")
        if st.button("🔄 Restart Application", use_container_width=True):
            # Clear all session state to ensure a clean restart
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with st.expander("🔍 Show Error Details"):
        st.code(error_message) 