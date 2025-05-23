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

# Set page config as the absolute first command (before ANY other Streamlit calls)
st.set_page_config(
    page_title="Pixel Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== IMPORT THE NEW ARCHITECTURE =====
from core.screen_renderer import render_app

# ===== MAIN APPLICATION =====
def main():
    """Main application with smart 3-screen UX flow"""
    try:
        # Everything is handled by the screen renderer
        render_app()
        
    except Exception as e:
        # Emergency fallback
        st.error("Critical application startup error")
        st.exception(e)
        st.markdown("---")
        st.markdown("### 🆘 Emergency Recovery")
        
        if st.button("🔄 Force Application Reset"):
            # Clear everything and restart
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("If the problem persists, please restart your browser or contact support.")

# Start the smart 3-screen UX app!
if __name__ == "__main__":
    main() 