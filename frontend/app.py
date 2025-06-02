# 📂 File Path: /project_root/app.py
# 📌 Purpose: Main entry point with SMART 3-screen progressive UX
# 🚀 PERFORMANCE REVOLUTION: Instant startup + perfect user flow
# ⚡ Key Innovation: Respect user flow - clear 3-screen progression
# 🧠 Philosophy: Load what you need, when you need it, with seamless UX

"""
Pixel Detective: Lightning-Fast Image Search Application
Smart 3-screen progressive UX - FAST_UI → LOADING → ADVANCED_UI
"""

# ===== MINIMAL STARTUP IMPORTS ONLY =====
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import asyncio 

# Set page config as the absolute first command (before ANY other Streamlit calls)
# This should only be called once per app.
if not hasattr(st, '_page_config_set'):
    st.set_page_config(
        page_title="Pixel Detective",
        page_icon="🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="expanded" # Keep expanded for easy access to folder processing
    )
    st._page_config_set = True


# ===== IMPORT THE NEW ARCHITECTURE =====
from core.screen_renderer import render_app 
from core.fast_startup_manager import get_fast_startup_manager 
# from core.app_state import AppStateManager # AppStateManager is used by ScreenRenderer

# ===== MAIN APPLICATION =====
async def main_async(): 
    """Main application with smart 3-screen UX flow"""
    try:
        # Initialize FastStartupManager to start any background tasks it's designed for (e.g., service checks)
        # Assuming get_fast_startup_manager() or a method it calls internally starts its non-UI work.
        # If FSM needs an explicit start for its background tasks without rendering UI:
        fsm = get_fast_startup_manager()
        # fsm.start_background_tasks_only() # Hypothetical method if FSM is refactored

        # ScreenRenderer handles all UI rendering and state transitions
        await render_app() 
        
    except Exception as e:
        # Emergency fallback
        st.error("🚨 Critical application startup error!")
        st.exception(e)
        st.markdown("---")
        st.markdown("### 🆘 Emergency Recovery Options")
        st.markdown("An unexpected error has occurred. You can try the following:")
        
        if st.button("🔄 Force Application Reset & Clear Cache"):
            # Clear everything and restart
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
        
        st.markdown("If the problem persists, please close this browser tab, ensure your backend services are running correctly, and then try reopening the application. Consult the application logs for more details.")

# Start the smart 3-screen UX app!
if __name__ == "__main__":
    # Initialize core app state here if not handled by ScreenRenderer's first call
    # AppStateManager.init_session_state() # Ensure this is called once. ScreenRenderer also calls it.
                                        # It's idempotent, so calling it here is safe too.
    asyncio.run(main_async()) 