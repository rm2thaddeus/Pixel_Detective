# 📊 Screen 2: Loading Screen - ENGAGING VERSION
# 📌 Purpose: Keep user engaged during background processing with excitement  
# 🎯 Mission: Build anticipation and show progress in user-friendly terms

import os
import time
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader, LoadingPhase


class LoadingScreen:
    """Screen 2: Engaging progress tracking that builds excitement"""
    
    @staticmethod
    def render():
        """Render the engaging loading screen"""
        # Get current progress from background loader
        progress_data = background_loader.get_progress()
        
        LoadingScreen._render_exciting_header()
        LoadingScreen._render_engaging_progress(progress_data)
        LoadingScreen._render_coming_features()
        LoadingScreen._render_simple_controls()
        LoadingScreen._render_encouraging_sidebar(progress_data)
        
        # Handle completion or errors
        LoadingScreen._handle_completion_or_errors(progress_data)
        
        # Auto-refresh every 3 seconds (reduced frequency for better UX)
        if progress_data.is_loading:
            time.sleep(2)  # Less frequent polling for smoother experience
            st.rerun()
    
    @staticmethod
    def _handle_completion_or_errors(progress_data):
        """Handle completion or error states"""
        if progress_data.error_occurred:
            # Transition to error state
            AppStateManager.transition_to_error(progress_data.error_message, can_retry=True)
            st.rerun()
        elif not progress_data.is_loading and progress_data.progress_percentage >= 100:
            # Update session state with results and transition to advanced UI
            st.session_state.ui_deps_loaded = progress_data.ui_deps_loaded
            st.session_state.models_loaded = progress_data.models_loaded
            st.session_state.database_ready = progress_data.database_ready
            st.session_state.image_files = progress_data.image_files
            
            AppStateManager.transition_to_advanced()
            st.rerun()
    
    @staticmethod
    def _render_exciting_header():
        """Render exciting header that builds anticipation"""
        st.title("🔄 Building Your Personal Image Assistant")
        
        folder_path = st.session_state.get('folder_path', 'Unknown')
        folder_name = os.path.basename(folder_path)
        st.markdown(f"### Creating magic for your **{folder_name}** collection ✨")
        st.markdown("---")
    
    @staticmethod
    def _render_engaging_progress(progress_data):
        """Build excitement, not just show technical progress"""
        # Excitement-building messages based on phase
        excitement_phases = {
            LoadingPhase.UI_DEPS: {
                "title": "🎨 Preparing Your Interface",
                "message": "Setting up your personalized workspace...",
                "action": "Getting everything ready for you",
                "next": "Next: Discovering your amazing photo collection"
            },
            LoadingPhase.FOLDER_SCAN: {
                "title": "🔍 Discovering Your Photos",
                "message": "Wow! Exploring your incredible image collection...",
                "action": "Finding all your precious memories",
                "next": "Next: Teaching AI to understand your style"
            },
            LoadingPhase.MODEL_INIT: {
                "title": "🤖 AI Learning Phase", 
                "message": "Our AI is learning to see the world through your lens...",
                "action": "Loading super-smart vision capabilities",
                "next": "Next: Building your intelligent search engine"
            },
            LoadingPhase.DB_BUILD: {
                "title": "🧠 Creating Your Search Engine",
                "message": "Building magical connections between your images and ideas...",
                "action": "Making every photo instantly searchable",
                "next": "Almost ready for the magic to begin!"
            },
            LoadingPhase.READY: {
                "title": "🎉 Your Image Assistant is Ready!",
                "message": "Everything is set up perfectly for you!",
                "action": "Preparing to amaze you",
                "next": "Let's explore your photos together!"
            }
        }
        
        current = excitement_phases.get(progress_data.current_phase, {
            "title": "⚡ Working Magic...",
            "message": "Something amazing is happening with your photos...",
            "action": "Processing your collection",
            "next": "Great things coming soon!"
        })
        
        # Main progress section with excitement
        st.markdown(f"## {current['title']}")
        st.markdown(f"**{current['message']}**")
        
        # Visual progress bar with excitement
        progress_bar = st.progress(progress_data.progress_percentage / 100)
        
        # Progress percentage with encouraging message
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric("Progress", f"{progress_data.progress_percentage}%", "🚀 Moving fast!")
        with col2:
            st.info(f"🔄 {current['action']}")
        
        # Build anticipation for what's next
        if current.get('next') and progress_data.progress_percentage < 100:
            st.markdown(f"*{current['next']}*")
        
        # Show image count when available (exciting milestone)
        if hasattr(progress_data, 'image_files') and len(progress_data.image_files) > 0:
            image_count = len(progress_data.image_files)
            st.success(f"🎉 **Discovered {image_count:,} images** in your collection!")
    
    @staticmethod
    def _render_coming_features():
        """Preview what's coming to build excitement"""
        st.markdown("---")
        
        with st.expander("🎯 The Amazing Features You'll Get", expanded=True):
            st.markdown("""
            ### 🔍 **Smart Search Magic**
            - Type **"sunset over lake"** → AI finds them instantly ✨
            - Upload **any image** → Find all similar ones automatically 🔮
            - Search by **colors, objects, moods** → AI understands everything 🎨
            
            ### 🎮 **AI Guessing Games**  
            - AI tries to **guess your photos** → Fun challenges await! 🎪
            - Discover **hidden gems** in your collection 💎
            - Interactive way to **explore memories** 🌟
            
            ### 🌐 **Visual Universe Explorer**
            - See your photos **arranged by visual similarity** 🌌
            - Discover **patterns and themes** you never noticed 🎭
            - **Travel through your memories** visually 🚀
            
            ### 👥 **Smart Organization**
            - Find **duplicate photos** automatically 🔄
            - **Clean up your collection** effortlessly 🧹
            - **Group similar memories** together 📚
            """)
    
    @staticmethod
    def _render_simple_controls():
        """Simple, user-friendly controls"""
        st.markdown("---")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("**🚀 Hang tight - amazing things are happening!**")
        
        with col2:
            if st.button("⏸️ Take a Break", help="Pause the magic for now"):
                st.info("⏸️ Pause feature coming soon!")
        
        with col3:
            if st.button("❌ Start Over", help="Go back and choose different folder"):
                LoadingScreen._go_back_to_start()
    
    @staticmethod
    def _go_back_to_start():
        """User-friendly way to return to folder selection"""
        if st.button("🔄 Yes, Start Over", key="confirm_restart"):
            background_loader.cancel_loading()
            st.warning("🔄 Going back to folder selection...")
            AppStateManager.reset_to_fast_ui()
            st.rerun()
        else:
            st.warning("Click 'Yes, Start Over' to confirm")
    
    @staticmethod
    def _render_encouraging_sidebar(progress_data):
        """Encouraging sidebar that builds excitement"""
        with st.sidebar:
            st.markdown("### 🌟 Your Collection Stats")
            
            # Show collection info in exciting way
            folder_path = st.session_state.get('folder_path', 'Unknown')
            folder_name = os.path.basename(folder_path)
            st.markdown(f"**📁 Collection:** {folder_name}")
            
            # Image count with celebration
            if hasattr(progress_data, 'image_files') and len(progress_data.image_files) > 0:
            image_count = len(progress_data.image_files)
                if image_count > 1000:
                    celebration = "🤩 Massive collection!"
                elif image_count > 500:
                    celebration = "😍 Huge collection!"
                elif image_count > 100:
                    celebration = "🎉 Great collection!"
                else:
                    celebration = "✨ Nice collection!"
                    
                st.metric("🖼️ Photos Found", f"{image_count:,}", celebration)
            else:
                st.info("🔍 Discovering photos...")
            
            # Progress in encouraging terms
            progress_percent = progress_data.progress_percentage
            if progress_percent > 80:
                encouragement = "🎉 Almost there!"
            elif progress_percent > 50:
                encouragement = "🚀 Halfway done!"
            elif progress_percent > 20:
                encouragement = "⚡ Making progress!"
            else:
                encouragement = "🌟 Just started!"
                
            st.metric("📊 Progress", f"{progress_percent}%", encouragement)
            
            st.markdown("---")
            
            # What's happening now (user-friendly)
            st.markdown("### 🔄 What's Happening")
            
            current_phase = progress_data.current_phase
            if current_phase == LoadingPhase.FOLDER_SCAN:
                st.info("🔍 **Exploring** your photo collection")
                st.markdown("Finding all your amazing images...")
            elif current_phase == LoadingPhase.MODEL_INIT:
                st.info("🤖 **Teaching AI** about images")
                st.markdown("Loading super-smart vision...")
            elif current_phase == LoadingPhase.DB_BUILD:
                st.info("🧠 **Building** your search engine")
                st.markdown("Making magic connections...")
            elif current_phase == LoadingPhase.READY:
                st.success("🎉 **Ready** for exploration!")
                st.markdown("Everything is perfect!")
            else:
                st.info("⚡ **Preparing** your workspace")
                st.markdown("Getting everything ready...")
            
            st.markdown("---")
            
            # Time estimation in friendly terms
            eta = getattr(progress_data, 'estimated_time_remaining', 'Soon')
            st.markdown("### ⏰ Time Estimate")
            if isinstance(eta, str) and 'minute' in eta:
                st.info(f"🕐 About {eta}")
                st.markdown("Perfect time for a coffee! ☕")
            elif isinstance(eta, str) and 'second' in eta:
                st.info(f"⚡ Just {eta}")  
                st.markdown("Almost instant! 🚀")
            else:
                st.info("⚡ Very soon!")
                st.markdown("We're working at light speed! 💫")
            
            st.markdown("---")
            
            # Excitement builder
            st.markdown("### 🎊 Fun Fact")
            
            # Random encouraging facts based on progress
            import random
            fun_facts = [
                "🎨 Your photos contain thousands of colors and patterns!",
                "🧠 AI will learn to see your unique photography style!",
                "🔍 Soon you'll search photos faster than ever before!",
                "✨ Every image will become instantly discoverable!",
                "🎮 Fun games await in your photo collection!",
                "🌟 Hidden connections between photos will be revealed!",
                "🚀 You're about to experience the future of photo search!"
            ]
            
            st.info(random.choice(fun_facts))


# Global function for easy import
def render_loading_screen():
    """Main entry point for Screen 2"""
    LoadingScreen.render() 