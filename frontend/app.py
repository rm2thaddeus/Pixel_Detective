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
import streamlit as st
import asyncio 
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
from frontend.core.screen_renderer import ScreenRenderer 

# ===== MAIN APPLICATION =====
async def main_async(): 
    """Main application with smart 3-screen UX flow"""
    try:
        # ScreenRenderer handles all UI rendering and state transitions
        await ScreenRenderer.render() 
        
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
    asyncio.run(main_async()) 