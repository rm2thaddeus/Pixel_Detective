# 📊 Screen 2: Loading Screen - PERFORMANCE OPTIMIZED
# 📌 Purpose: Keep user engaged during background processing with excitement  
# 🎯 Mission: Build anticipation and show progress in user-friendly terms
# 🎨 Sprint 02: Now with beautiful design system integration
# 🚀 FIXED: Removed blocking operations and optimized refresh mechanism

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from core.background_loader import background_loader, LoadingPhase
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

logger = logging.getLogger(__name__)


class LoadingScreen:
    """Screen 2: Engaging progress tracking that builds excitement + Design System"""
    
    @staticmethod
    def render():
        """Render the enhanced loading screen with design system - PERFORMANCE OPTIMIZED"""
        # Only inject styles once per session to avoid performance issues
        if not st.session_state.get('loading_styles_injected', False):
            inject_pixel_detective_styles()
            SkeletonScreens.inject_skeleton_styles()
            st.session_state.loading_styles_injected = True
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        # Get current progress from background loader
        progress_data = background_loader.get_progress()
        # Display native progress bar for smoother UX and accessibility
        st.progress(progress_data.progress_percentage)
        # Show progress message and estimated time remaining
        eta = progress_data.get_estimated_time_remaining()
        st.text(f"{progress_data.progress_percentage}% - {progress_data.progress_message} | ETA: {eta}")
        
        # DEBUG: Show loader logs to diagnose stalling
        with st.expander("Loading Debug Logs", expanded=False):
            for log in progress_data.logs:
                st.text(log)
        
        LoadingScreen._render_enhanced_header(progress_data)
        LoadingScreen._render_enhanced_progress(progress_data)
        LoadingScreen._render_skeleton_preview(progress_data)
        LoadingScreen._render_enhanced_features_preview()
        LoadingScreen._render_enhanced_controls()
        LoadingScreen._render_enhanced_sidebar(progress_data)
        
        # Close animation wrapper
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Handle completion or errors
        LoadingScreen._handle_completion_or_errors(progress_data)
        
        # OPTIMIZED: Use smart refresh mechanism - avoid infinite rerun loops
        if progress_data.is_loading and progress_data.progress_percentage < 100:
            # Only rerun if actually loading and not complete
            # FIXED: Add throttling to prevent excessive reruns
            import time
            if not hasattr(st.session_state, 'last_rerun_time'):
                st.session_state.last_rerun_time = 0
            
            current_time = time.time()
            if current_time - st.session_state.last_rerun_time > 2.0:  # Throttle to every 2 seconds
                st.session_state.last_rerun_time = current_time
                st.rerun()
        elif progress_data.progress_percentage >= 100 and not progress_data.error_occurred:
            # Completion state - let the handle_completion method manage transition
            pass
    
    @staticmethod
    def _handle_completion_or_errors(progress_data):
        """Handle completion or error states"""
        if progress_data.error_occurred:
            AppStateManager.transition_to_error(progress_data.error_message, can_retry=True)
            st.rerun()
        elif not progress_data.is_loading and progress_data.progress_percentage >= 100:
            # Update session state with results from BackgroundLoader's progress object
            st.session_state.ui_deps_loaded = progress_data.ui_deps_loaded
            st.session_state.models_loaded = progress_data.models_loaded
            st.session_state.database_ready = progress_data.database_ready # This should be true here
            st.session_state.image_files = progress_data.image_files
            
            # NEW: Transfer results from background loader to session state
            if hasattr(progress_data, 'result_embeddings') and progress_data.result_embeddings is not None:
                st.session_state.embeddings = progress_data.result_embeddings
            else:
                # This case should ideally be an error caught by BackgroundLoader
                st.session_state.embeddings = np.array([], dtype=np.float32).reshape(0,0)
                logger.warning("Loading complete but no embeddings found in progress_data.")

            if hasattr(progress_data, 'result_metadata_df') and progress_data.result_metadata_df is not None:
                st.session_state.images_data = progress_data.result_metadata_df
            else:
                st.session_state.images_data = pd.DataFrame()
                logger.warning("Loading complete but no metadata dataframe found in progress_data.")
            
            # Ensure database_built is also set if database_ready is true
            if progress_data.database_ready:
                st.session_state.database_built = True

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
    def _render_enhanced_header(progress_data):
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
                        <div class="pd-progress-bar" style="width: {progress_data.progress_percentage}%;"></div>
                    </div>
                    <div style="color: rgba(255, 255, 255, 0.8); font-size: 1.1rem;">
                        {progress_data.progress_percentage}% Complete
                    </div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def _render_enhanced_progress(progress_data):
        """Enhanced progress display with styled phase indicators"""
        # Enhanced excitement-building messages based on phase
        excitement_phases = {
            LoadingPhase.UI_DEPS: {
                "title": "🎨 Preparing Your Interface",
                "message": "Setting up your personalized workspace...",
                "action": "Getting everything ready for you",
                "next": "Next: Discovering your amazing photo collection",
                "icon": "🎨",
                "color": "info"
            },
            LoadingPhase.FOLDER_SCAN: {
                "title": "🔍 Discovering Your Photos",
                "message": "Wow! Exploring your incredible image collection...",
                "action": "Finding all your precious memories",
                "next": "Next: Teaching AI to understand your style",
                "icon": "🔍",
                "color": "info"
            },
            LoadingPhase.MODEL_INIT: {
                "title": "🤖 AI Learning Phase", 
                "message": "Our AI is learning to see the world through your lens...",
                "action": "Loading super-smart vision capabilities",
                "next": "Next: Building your intelligent search engine",
                "icon": "🤖",
                "color": "info"
            },
            LoadingPhase.DB_BUILD: {
                "title": "🧠 Creating Your Search Engine",
                "message": "Building magical connections between your images and ideas...",
                "action": "Making every photo instantly searchable",
                "next": "Almost ready for the magic to begin!",
                "icon": "🧠",
                "color": "info"
            },
            LoadingPhase.READY: {
                "title": "🎉 Your Image Assistant is Ready!",
                "message": "Everything is set up perfectly for you!",
                "action": "Preparing to amaze you",
                "next": "Let's explore your photos together!",
                "icon": "🎉",
                "color": "success"
            }
        }
        
        current = excitement_phases.get(progress_data.current_phase, {
            "title": "⚡ Working Magic...",
            "message": "Something amazing is happening with your photos...",
            "action": "Processing your collection",
            "next": "Great things coming soon!",
            "icon": "⚡",
            "color": "info"
        })
        
        # Main progress section with enhanced styling
        st.markdown(
            f'''
            <div class="pd-card pd-fade-in" style="margin: 2rem 0; text-align: center;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">{current['icon']}</div>
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">{current['title']}</h2>
                <p style="font-size: 1.2rem; color: var(--pd-text-primary); margin-bottom: 2rem;">
                    <strong>{current['message']}</strong>
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
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">{progress_data.progress_percentage}%</h3>
                    <p style="color: var(--pd-text-secondary); margin: 0;">Progress</p>
                    <div style="margin-top: 0.5rem;">
                        <span class="pd-status pd-status-{current['color']}">
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
                    <p style="color: var(--pd-text-secondary); margin: 0; font-size: 0.9rem;">{current['action']}</p>
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
        if current.get('next') and progress_data.progress_percentage < 100:
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-info pd-fade-in" style="margin-top: 2rem;">
                    <div style="font-size: 1.2rem;">✨</div>
                    <div>
                        <strong>Coming Next:</strong> {current['next']}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
                            )
    
    @staticmethod
    def _render_skeleton_preview(progress_data):
        """Render contextual skeleton screens based on current loading phase"""
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Show skeleton preview with contextual information
        with st.expander("👀 Preview: What's Being Built", expanded=False):
            st.markdown(
                '''
                <div style="text-align: center; margin-bottom: 1rem;">
                    <h4 style="color: var(--pd-text-primary); margin-bottom: 0.5rem;">
                        🔮 Sneak Peek at Your Future Interface
                    </h4>
                    <p style="color: var(--pd-text-secondary); font-size: 0.9rem;">
                        This is what we're preparing for you right now...
                    </p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Render contextual skeleton based on current phase
            phase_name = str(progress_data.current_phase).split('.')[-1] if hasattr(progress_data, 'current_phase') else "loading"
            # phase_description = getattr(progress_data, 'current_message', 'Preparing your interface...')
            
            # TEMP: Test simple HTML rendering
            st.markdown("SIMPLE SKELETON TEST", unsafe_allow_html=True) # Simplified further
            # SkeletonScreens.render_contextual_skeleton(phase_name, phase_description)
            
            # Add contextual message
            phase_messages = {
                'UI_DEPS': "🎨 Setting up your beautiful interface components...",
                'FOLDER_SCAN': "🔍 This is how your photo gallery will look once we find all your images!",
                'MODEL_INIT': "🤖 Preparing AI-powered search capabilities for you...",
                'DB_BUILD': "🧠 Building the intelligent database that will power instant search...",
                'READY': "🎉 Your complete image search interface is ready!"
            }
            
            current_message = phase_messages.get(phase_name, "✨ Creating something amazing for your photos...")
            
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-info pd-fade-in" style="margin-top: 1rem; text-align: center;">
                    <div style="font-size: 1rem; color: var(--pd-text-primary);">
                        {current_message}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
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
    def _render_enhanced_sidebar(progress_data):
        """Enhanced sidebar with styled components and animated elements"""
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
            progress_percent = progress_data.progress_percentage
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
            if current_phase == LoadingPhase.FOLDER_SCAN:
                create_status_indicator("info", "Exploring your photo collection", True)
                st.markdown("Finding all your amazing images...")
            elif current_phase == LoadingPhase.MODEL_INIT:
                create_status_indicator("info", "Teaching AI about images", True)
                st.markdown("Loading super-smart vision...")
            elif current_phase == LoadingPhase.DB_BUILD:
                create_status_indicator("info", "Building your search engine", True)
                st.markdown("Making magic connections...")
            elif current_phase == LoadingPhase.READY:
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


# Global function for easy import
def render_loading_screen():
    """Main entry point for Screen 2 with enhanced design system"""
    LoadingScreen.render() 