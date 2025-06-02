# 📊 Screen 2: Loading Screen - PERFORMANCE OPTIMIZED
# 📌 Purpose: Keep user engaged during background processing with excitement  
# 🎯 Mission: Build anticipation and show progress in user-friendly terms
# 🎨 Sprint 02: Now with beautiful design system integration
# 🚀 FIXED: Removed blocking operations and optimized refresh mechanism

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader, BackgroundLoaderProgress
from styles.style_injector import (
    inject_pixel_detective_styles,
    create_hero_section,
    create_progress_bar,
    create_status_indicator,
    create_loading_spinner,
    create_styled_container
)
from components.skeleton_screens import SkeletonScreens
import logging
import asyncio
from core import service_api

logger = logging.getLogger(__name__)


class LoadingScreen:
    """Screen 2: Engaging progress tracking that builds excitement + Design System"""
    
    @staticmethod
    async def render():
        """Render the enhanced loading screen with design system - PERFORMANCE OPTIMIZED"""
        # Only inject styles once per session to avoid performance issues
        if not st.session_state.get('loading_styles_injected', False):
            inject_pixel_detective_styles()
            SkeletonScreens.inject_skeleton_styles()
            st.session_state.loading_styles_injected = True
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        # Get current progress from background_loader.progress
        current_progress_percent = background_loader.progress.percent_complete
        current_progress_detail = background_loader.progress.current_detail

        # Display native progress bar for smoother UX and accessibility
        st.progress(current_progress_percent / 100.0) # progress expects 0.0 to 1.0
        
        # Show progress message
        st.text(f"{current_progress_percent:.0f}% - {current_progress_detail}")
        
        # DEBUG: Show loader status and detail
        # with st.expander("Loading Debug Info", expanded=False):
        #    st.text(f"Status: {background_loader.progress.status}")
        #    st.text(f"Detail: {background_loader.progress.current_detail}")
        #    st.text(f"Error: {background_loader.progress.error_message}")
        #    st.text(f"Job ID: {st.session_state.get('bg_loader_job_id')}")

        # Pass background_loader.progress to sub-render methods that might need it
        LoadingScreen._render_enhanced_header(background_loader.progress)
        LoadingScreen._render_enhanced_progress(background_loader.progress)
        LoadingScreen._render_skeleton_preview(background_loader.progress)
        LoadingScreen._render_enhanced_features_preview()
        LoadingScreen._render_enhanced_controls()
        LoadingScreen._render_enhanced_sidebar(background_loader.progress)
        
        # Close animation wrapper
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle completion or errors by checking background_loader.progress.status
        await LoadingScreen._handle_completion_or_errors()
        
        # OPTIMIZED: Use smart refresh mechanism
        if background_loader.progress.is_loading:
            # Now that background_loader.check_ingestion_status is async, await it.
            await background_loader.check_ingestion_status() # Correctly await the async method
            
            # If after checking, the status is no longer loading (e.g., completed or error), 
            # re-evaluate completion/error to transition if needed.
            if not background_loader.progress.is_loading:
                await LoadingScreen._handle_completion_or_errors()
                st.rerun() # Ensure transition if state changed to completed/error
                return # Stop further processing in this render cycle
            
            # Rerun logic (throttled) if still loading
            import time
            if not hasattr(st.session_state, 'last_loading_rerun_time'):
                st.session_state.last_loading_rerun_time = 0
            
            current_time = time.time()
            if current_time - st.session_state.last_loading_rerun_time > 1.0: 
                st.session_state.last_loading_rerun_time = current_time
                st.rerun()
        elif background_loader.progress.status == "completed":
            # Completion state is handled by _handle_completion_or_errors which should have triggered a rerun to advanced UI
            pass # Or call _handle_completion_or_errors one last time to be sure
            await LoadingScreen._handle_completion_or_errors() 
            # No st.rerun() here if _handle_completion_or_errors already does it for completed state.
            # _handle_completion_or_errors already calls st.rerun() when transitioning.
    
    @staticmethod
    async def _handle_completion_or_errors():
        """Handle completion or error states based on background_loader.progress"""
        loader_status = background_loader.progress.status
        
        if loader_status == "error":
            error_msg = background_loader.progress.error_message or "An unknown error occurred during loading."
            AppStateManager.transition_to_error(error_msg, can_retry=True)
            st.rerun()
        elif loader_status == "completed":
            # Minimal state setting here. Advanced UI will fetch necessary data via service_api.
            st.session_state.database_built = True # Indicate that ingestion process finished
            
            # Clear loader-specific session state if desired, or leave for debugging
            # background_loader.reset_loading_state() # Optional: reset if not needed anymore

            st.markdown(
                '''
                <div class="pd-alert pd-alert-success pd-fade-in" style="text-align: center; margin: 2rem 0;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">🎉</div>
                    <div>
                        <strong>Loading Complete!</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Transitioning to your advanced image search interface...
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Transition to advanced UI
            AppStateManager.transition_to_advanced()
            st.rerun()
    
    @staticmethod
    def _render_enhanced_header(progress_data): # progress_data is now background_loader.progress
        """Enhanced header with styled components and progress visualization"""
        folder_path = st.session_state.get('folder_path', 'Unknown')
        folder_name = os.path.basename(folder_path)
        
        # Enhanced hero section for loading state
        st.markdown(
            f'''
            <div class="pd-hero pd-fade-in" style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">🔄</div>
                <h1 class="pd-title" style="color: white; margin-bottom: 0.5rem;">Building Your Personal Image Assistant</h1>
                <p class="pd-subheading" style="color: rgba(255, 255, 255, 0.9); margin-bottom: 1rem;">
                    Creating magic for your <strong>{folder_name}</strong> collection ✨
                </p>
                
                <!-- Main Progress Bar -->
                <div style="max-width: 600px; margin: 0 auto;">
                    <div class="pd-progress pd-wave" style="height: 12px; margin-bottom: 1rem;">
                        <div class="pd-progress-bar" style="width: {progress_data.percent_complete}%;"></div>
                    </div>
                    <div style="color: rgba(255, 255, 255, 0.8); font-size: 1.1rem;">
                        {progress_data.percent_complete}% Complete
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def _render_enhanced_progress(progress_data): # progress_data is now background_loader.progress
        """Enhanced progress display with styled phase indicators"""
        # Enhanced excitement-building messages based on phase
        # This section needs significant rework as LoadingPhase is gone
        # We'll use current_detail and status for a simpler message for now
        
        current_detail = progress_data.current_detail
        status = progress_data.status

        # Simplified message based on current detail
        display_title = "⚙️ Processing Your Collection"
        display_message = current_detail
        display_icon = "⚙️"
        display_color = "info"

        if status == "completed":
            display_title = "🎉 Your Image Assistant is Ready!"
            display_message = "Everything is set up perfectly for you!"
            display_icon = "🎉"
            display_color = "success"
        elif status == "error":
            display_title = "⚠️ Error Occurred"
            display_message = progress_data.error_message or "An error occurred during processing."
            display_icon = "⚠️"
            display_color = "danger"
        elif status == "pending":
            display_title = "⏳ Preparing to Load"
            display_message = "Initiating the loading process..."
            display_icon = "⏳"
            display_color = "info"


        # Main progress section with enhanced styling
        st.markdown(
            f'''
            <div class="pd-card pd-fade-in" style="margin: 2rem 0; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">{display_icon}</div>
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">{display_title}</h2>
                <p style="font-size: 1.2rem; color: var(--pd-text-primary); margin-bottom: 2rem;">
                    <strong>{display_message}</strong>
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Progress metrics with enhanced styling
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(
                f'''
                <div class="pd-card pd-stagger-item" style="text-align: center;">
                    <div style="font-size: 2rem; color: var(--pd-primary); margin-bottom: 0.5rem;">📊</div>
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">{progress_data.percent_complete}%</h3>
                    <p style="color: var(--pd-text-secondary); margin: 0;">Progress</p>
                    <div style="margin-top: 0.5rem;">
                        <span class="pd-status pd-status-{display_color}">
                            <span>🚀 Moving fast!</span>
                        </span>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f'''
                <div class="pd-card pd-stagger-item" style="text-align: center;">
                    <div style="font-size: 2rem; color: var(--pd-secondary); margin-bottom: 0.5rem;">🔄</div>
                    <h4 style="color: var(--pd-text-primary); margin-bottom: 0.5rem;">Current Task</h4>
                    <p style="color: var(--pd-text-secondary); margin: 0; font-size: 0.9rem;">{current_detail}</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        with col3:
            # Show image count when available with celebration
            if hasattr(progress_data, 'image_files') and len(progress_data.image_files) > 0:
                image_count = len(progress_data.image_files)
                st.markdown(
                    f'''
                    <div class="pd-card pd-stagger-item pd-celebrate" style="text-align: center;">
                        <div style="font-size: 2rem; color: var(--pd-success); margin-bottom: 0.5rem;">🖼️</div>
                        <h3 style="color: var(--pd-success); margin-bottom: 0.5rem;">{image_count:,}</h3>
                        <p style="color: var(--pd-text-secondary); margin: 0;">Images Found</p>
                        <div style="margin-top: 0.5rem;">
                            <span class="pd-status pd-status-success">
                                <span>🎉 Discovered!</span>
                            </span>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '''
                    <div class="pd-card pd-stagger-item" style="text-align: center;">
                        <div class="pd-loading-dots" style="justify-content: center; margin-bottom: 1rem;">
                            <div class="pd-loading-dot"></div>
                            <div class="pd-loading-dot"></div>
                            <div class="pd-loading-dot"></div>
                        </div>
                        <h4 style="color: var(--pd-text-primary); margin-bottom: 0.5rem;">Scanning...</h4>
                        <p style="color: var(--pd-text-secondary); margin: 0; font-size: 0.9rem;">Finding images</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        
        # Build anticipation for what's next with enhanced styling
        if progress_data.status == "completed":
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-info pd-fade-in" style="margin-top: 2rem;">
                    <div style="font-size: 1.2rem;">✨</div>
                    <div>
                        <strong>Coming Next:</strong> {display_title}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    @staticmethod
    def _render_skeleton_preview(progress_data: BackgroundLoaderProgress):
        """Render the skeleton preview area with dynamic messages."""
        
        # Phase messages (Consider if these are still needed if backend provides good detail)
        # phase_messages = {
        #     "initializing": "✨ Initializing the magic...",
        #     "scanning_files": "📂 Scanning your image collection...",
        #     "generating_embeddings": "🧠 Creating image understanding (embeddings)...",
        #     "building_index": "🏗️ Building the search index...",
        #     "finalizing": "🏁 Finalizing the process...",
        #     "completed": "✅ All done! Ready for the advanced UI.",
        #     "error": "⚠️ An error occurred during processing."
        # }

        # Use current_detail from progress_data, which comes from the backend's message
        # If current_detail is empty or generic, provide a fallback.
        current_message = progress_data.current_detail
        if not current_message or current_message == "Initializing...": # Default from BackgroundLoaderProgress
             if progress_data.status == "pending":
                 current_message = "🚀 Preparing to launch processing..."
             elif progress_data.status == "processing":
                 current_message = "⚙️ Working on it..."
             elif progress_data.status == "completed":
                 current_message = "✅ Processing complete!"
             elif progress_data.status == "error":
                 current_message = f"⚠️ Error: {progress_data.error_message or 'An issue occurred.'}"
             else: # idle or unknown
                 current_message = "✨ Stand by, magic in progress..."


        # Preview section
        st.markdown("### 👀 Preview: What's Being Built")
        
        # Simulate task update
        tasks_container = st.empty()
        with tasks_container.container():
            st.markdown(f"""
            <div class="pd-task-item">
                <div class="pd-task-icon">🔄</div>
                <div>
                    <div class="pd-task-name">Current Task</div>
                    <div class="pd-task-detail">{current_message}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Simulate image processing (could show some generic images or placeholders)
        # ... existing code ...
    
    @staticmethod
    def _render_enhanced_features_preview():
        """Enhanced preview of features with styled cards"""
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("🎯 The Amazing Features You'll Get", expanded=False):
            # Create feature preview cards
            features = [
                {
                    "icon": "🔍",
                    "title": "Smart Search Magic",
                    "description": "Type 'sunset over lake' → AI finds them instantly ✨\nUpload any image → Find all similar ones automatically 🔮"
                },
                {
                    "icon": "🎮", 
                    "title": "AI Guessing Games",
                    "description": "AI tries to guess your photos → Fun challenges await! 🎪\nDiscover hidden gems in your collection 💎"
                },
                {
                    "icon": "🌐",
                    "title": "Visual Universe Explorer", 
                    "description": "See photos arranged by visual similarity 🌌\nTravel through your memories visually 🚀"
                }
            ]
            
            cols = st.columns(len(features))
            for i, feature in enumerate(features):
                with cols[i]:
                    st.markdown(
                        f'''
                        <div class="pd-feature-card pd-stagger-item pd-hover-lift" style="margin: 1rem 0;">
                            <div class="pd-feature-card-icon">{feature['icon']}</div>
                            <div class="pd-feature-card-title">{feature['title']}</div>
                            <div class="pd-feature-card-description" style="line-height: 1.6; white-space: pre-line;">
                                {feature['description']}
                            </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
    
    @staticmethod
    def _render_enhanced_controls():
        """Enhanced controls with styled buttons"""
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(
                '''
                <div class="pd-alert pd-alert-info pd-pulse">
                    <div style="font-size: 1.2rem;">🚀</div>
                    <div>
                        <strong>Hang tight - amazing things are happening!</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            Your intelligent image assistant is almost ready
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        with col2:
            if st.button("⏸️ Take a Break", help="Pause the magic for now", key="pause_btn"):
                st.markdown(
                    '''
                    <div class="pd-alert pd-alert-info pd-fade-in">
                        <div style="font-size: 1.2rem;">⏸️</div>
                        <div>
                            <strong>Pause feature coming soon!</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                For now, feel free to minimize the browser
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        
        with col3:
            if st.button("❌ Start Over", help="Go back and choose different folder", key="restart_btn"):
                LoadingScreen._go_back_to_start()
    
    @staticmethod
    def _go_back_to_start():
        """Enhanced restart confirmation with styled components"""
        st.markdown(
            '''
            <div class="pd-alert pd-alert-warning pd-fade-in">
                <div style="font-size: 1.2rem;">⚠️</div>
                <div>
                    <strong>Are you sure you want to start over?</strong>
                    <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                        This will cancel the current processing and return to folder selection
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Yes, Start Over", key="confirm_restart", type="primary"):
                background_loader.cancel_loading()
                
                st.markdown(
                    '''
                    <div class="pd-alert pd-alert-info pd-fade-in">
                        <div style="font-size: 1.2rem;">🔄</div>
                        <div>
                            <strong>Going back to folder selection...</strong>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                
                AppStateManager.reset_to_fast_ui()
                st.rerun()
        
        with col2:
            if st.button("❌ Cancel", key="cancel_restart"):
                st.rerun()
    
    @staticmethod
    def _render_enhanced_sidebar(progress_data): # progress_data is now background_loader.progress
        """Render enhanced sidebar for loading screen"""
        with st.sidebar:
            # Enhanced sidebar header
            st.markdown(
                '''
                <div class="pd-card" style="text-align: center; margin-bottom: 1.5rem;">
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">🌟 Collection Stats</h3>
                    <div style="font-size: 0.875rem; color: var(--pd-text-secondary);">
                        Real-time processing updates
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Collection info with enhanced styling
            folder_path = st.session_state.get('folder_path', 'Unknown')
            folder_name = os.path.basename(folder_path)
            
            st.markdown(
                f'''
                <div class="pd-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem;">📁</span>
                        <strong style="color: var(--pd-text-primary);">Collection</strong>
                    </div>
                    <div style="color: var(--pd-text-secondary); font-size: 0.9rem;">
                        {folder_name}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced image count with celebration
            if hasattr(progress_data, 'image_files') and len(progress_data.image_files) > 0:
                image_count = len(progress_data.image_files)
                if image_count > 1000:
                    celebration = "🤩 Massive collection!"
                    color = "success"
                elif image_count > 500:
                    celebration = "😍 Huge collection!"
                    color = "success" 
                elif image_count > 100:
                    celebration = "🎉 Great collection!"
                    color = "info"
                else:
                    celebration = "✨ Nice collection!"
                    color = "info"
                
                st.markdown(
                    f'''
                    <div class="pd-card pd-celebrate" style="margin-bottom: 1rem; text-align: center;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🖼️</div>
                        <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">{image_count:,}</h3>
                        <div style="color: var(--pd-text-secondary); margin-bottom: 0.5rem;">Photos Found</div>
                        <div class="pd-status pd-status-{color}">
                            <span>{celebration}</span>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            else:
                create_loading_spinner("Discovering photos...", "dots")
            
            # Enhanced progress display
            progress_percent = progress_data.percent_complete
            if progress_percent > 80:
                encouragement = "🎉 Almost there!"
                color = "success"
            elif progress_percent > 50:
                encouragement = "🚀 Halfway done!"
                color = "info"
            elif progress_percent > 20:
                encouragement = "⚡ Making progress!"
                color = "info"
            else:
                encouragement = "🌟 Just started!"
                color = "info"
            
            st.markdown(
                f'''
                <div class="pd-card" style="margin-bottom: 1rem; text-align: center;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">📊</div>
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">{progress_percent}%</h3>
                    <div style="color: var(--pd-text-secondary); margin-bottom: 1rem;">Progress</div>
                    <div class="pd-progress pd-wave" style="margin-bottom: 0.5rem;">
                        <div class="pd-progress-bar" style="width: {progress_percent}%;"></div>
                    </div>
                    <div class="pd-status pd-status-{color}">
                        <span>{encouragement}</span>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            
            # Enhanced current phase display
            st.markdown("### 🔄 What's Happening")
            
            current_phase = progress_data.current_phase
            if current_phase == "FOLDER_SCAN":
                create_status_indicator("info", "Exploring your photo collection", True)
                st.markdown("Finding all your amazing images...")
            elif current_phase == "MODEL_INIT":
                create_status_indicator("info", "Teaching AI about images", True)
                st.markdown("Loading super-smart vision...")
            elif current_phase == "DB_BUILD":
                create_status_indicator("info", "Building your search engine", True)
                st.markdown("Making magic connections...")
            elif current_phase == "READY":
                create_status_indicator("success", "Ready for exploration!", True)
                st.markdown("Everything is perfect!")
            else:
                create_status_indicator("info", "Preparing your workspace", True)
                st.markdown("Getting everything ready...")
            
            st.markdown("---")
            
            # Enhanced time estimation
            eta = getattr(progress_data, 'estimated_time_remaining', 'Soon')
            st.markdown(
                '''
                <div class="pd-card" style="text-align: center; margin-bottom: 1rem;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">⏰</div>
                    <h4 style="color: var(--pd-text-primary); margin-bottom: 0.5rem;">Time Estimate</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            if isinstance(eta, str) and 'minute' in eta:
                st.markdown(
                    f'''
                    <div class="pd-alert pd-alert-info">
                        <div style="font-size: 1.2rem;">🕐</div>
                        <div>
                            <strong>About {eta}</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                Perfect time for a coffee! ☕
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            elif isinstance(eta, str) and 'second' in eta:
                st.markdown(
                    f'''
                    <div class="pd-alert pd-alert-success">
                        <div style="font-size: 1.2rem;">⚡</div>
                        <div>
                            <strong>Just {eta}</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                Almost instant! 🚀
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '''
                    <div class="pd-alert pd-alert-info">
                        <div style="font-size: 1.2rem;">⚡</div>
                        <div>
                            <strong>Very soon!</strong>
                            <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                                We're working at light speed! 💫
                            </div>
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            
            st.markdown("---")
            
            # Enhanced fun fact section
            st.markdown(
                '''
                <div class="pd-card" style="text-align: center; margin-bottom: 1rem;">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎊</div>
                    <h4 style="color: var(--pd-secondary); margin-bottom: 1rem;">Fun Fact</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
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
            
            selected_fact = random.choice(fun_facts)
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-info pd-pulse">
                    <div style="font-size: 1.2rem;">💡</div>
                    <div>
                        {selected_fact}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

            # Status Section (using the new progress object)
            st.markdown("### 📊 Status")
            if progress_data.is_loading:
                create_status_indicator(f"Processing: {progress_data.current_detail}", "processing")
                st.markdown(f"**Progress:** {progress_data.percent_complete:.0f}%")
            elif progress_data.status == "completed":
                create_status_indicator("Load Complete!", "success")
            elif progress_data.status == "error":
                create_status_indicator(f"Error: {progress_data.error_message}", "error")
            else:
                create_status_indicator("Status: Idle", "idle")
            
            # Debug Info (Optional)
            if st.checkbox("Show Loading Debug Info"):
                st.markdown("**Debug Details:**")
                st.text(f"Job ID: {st.session_state.get('bg_loader_job_id')}")
                st.text(f"Raw Status: {progress_data.status}")
                st.text(f"Detail: {progress_data.current_detail}")
                st.text(f"Percent: {progress_data.percent_complete}")
                st.text(f"Error Msg: {progress_data.error_message}")


# Global function for easy import
async def render_loading_screen():
    """Main entry point for Screen 2 with enhanced design system"""
    await LoadingScreen.render() 