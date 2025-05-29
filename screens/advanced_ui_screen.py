# 🎛️ Screen 3: Advanced UI Screen - ENHANCED WITH DESIGN SYSTEM
# 📌 Purpose: Full-featured interface with integrated sophisticated components
# 🎯 Mission: Use ALL the advanced features from ui/ folder in 3-screen architecture
# 🎨 Sprint 02: Now with beautiful design system integration

import os
import streamlit as st
from core.app_state import AppStateManager, AppState
from styles.style_injector import inject_pixel_detective_styles


class AdvancedUIScreen:
    """Screen 3: Full featured interface with sophisticated components + Design System"""
    
    @staticmethod
    def render():
        """Render the enhanced advanced UI screen with design system"""
        # Inject our custom styles
        inject_pixel_detective_styles()
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        AdvancedUIScreen._render_enhanced_header()
        AdvancedUIScreen._render_sophisticated_tabs()
        AdvancedUIScreen._render_contextual_sidebar()
        
        # Close animation wrapper
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def _render_enhanced_header():
        """Enhanced header with styled components"""
        folder_path = st.session_state.get('folder_path', 'Unknown')
        image_count = len(st.session_state.get('image_files', []))
        folder_name = os.path.basename(folder_path)
        
        # Enhanced hero section for advanced UI
        st.markdown(
            f'''
            <div class="pd-hero pd-fade-in" style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🕵️‍♂️</div>
                <h1 class="pd-title" style="color: white; margin-bottom: 0.5rem;">Pixel Detective</h1>
                <p class="pd-subheading" style="color: rgba(255, 255, 255, 0.9); margin-bottom: 1rem;">
                    Collection: <strong>{folder_name}</strong>
                </p>
                <div style="display: flex; justify-content: center; gap: 2rem; color: rgba(255, 255, 255, 0.8);">
                    <div>📁 <strong>{folder_path}</strong></div>
                    <div>🖼️ <strong>{image_count:,}</strong> images</div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def _render_sophisticated_tabs():
        """Enhanced tabs with styled components"""
        # Create tabs with enhanced styling
        st.markdown(
            '''
            <div class="pd-fade-in">
                <style>
                .stTabs [data-baseweb="tab-list"] {
                    gap: 8px;
                }
                .stTabs [data-baseweb="tab"] {
                    background-color: var(--pd-surface);
                    border: 1px solid var(--pd-border);
                    border-radius: var(--pd-radius);
                    padding: 0.75rem 1.5rem;
                    font-weight: 500;
                    transition: all var(--pd-transition);
                }
                .stTabs [aria-selected="true"] {
                    background-color: var(--pd-primary);
                    color: white;
                    border-color: var(--pd-primary);
                }
                </style>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        search_tab, ai_game_tab, latent_space_tab, duplicates_tab = st.tabs([
            "🔍 Search", 
            "🎮 AI Game", 
            "🌐 Latent Space", 
            "👥 Duplicates"
        ])
        
        with search_tab:
            AdvancedUIScreen._render_sophisticated_search()
        
        with ai_game_tab:
            AdvancedUIScreen._render_ai_game()
        
        with latent_space_tab:
            AdvancedUIScreen._render_latent_space()
        
        with duplicates_tab:
            AdvancedUIScreen._render_duplicates()
    
    @staticmethod
    def _render_sophisticated_search():
        """Simple, clean search interface - search bar, image upload, sliders, gallery"""
        # Clean header
        st.markdown(
            '''
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 2rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                color: white;
                text-align: center;
                box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            ">
                <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700;">🔍 Search Your Collection</h1>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
                    Find images using text or upload a sample image
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Check if database is ready
        database_indicators = [
            st.session_state.get('database_ready', False),
            st.session_state.get('database_built', False),
            st.session_state.get('images_data') is not None,
            hasattr(st.session_state, 'database_manager')
        ]
        
        if not any(database_indicators):
            st.warning("🔄 Database not ready yet. Please complete the image processing first.")
            return
        
        # Simple search interface - stacked vertically
        # Text search bar (full width)
        search_query = st.text_input(
            "🔍 Search by description:",
            placeholder="e.g., 'sunset over mountains', 'cute dog playing', 'family vacation photos'",
            key="simple_search_input"
        )
        
        # Image upload (full width)
        uploaded_file = st.file_uploader(
            "📤 Or upload sample image:", 
            type=['jpg', 'jpeg', 'png', 'bmp', 'gif'],
            key="simple_image_uploader"
        )
        
        # Show uploaded image preview if available
        if uploaded_file:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(uploaded_file, caption="Sample Image", use_container_width=True)
        
        # Controls row
        col1, col2 = st.columns([2, 1])
        with col1:
            num_results = st.slider("Number of results:", 1, 20, 5, key="simple_results_slider")
        with col2:
            # Search button
            search_button = st.button("🔍 Search", type="primary", use_container_width=True)
        
        # Handle search - both button click and Enter key
        search_triggered = search_button or (search_query and st.session_state.get('simple_search_input') != st.session_state.get('last_search_query', ''))
        
        if search_triggered:
            # Update last search query to prevent repeated searches
            st.session_state.last_search_query = search_query
            
            if search_query or uploaded_file:
                with st.spinner("🔍 Searching your collection..."):
                    try:
                        # Direct search without complex component calls
                        from utils.lazy_session_state import LazySessionManager
                        try:
                            db_manager = LazySessionManager.ensure_database_manager()
                        except Exception as e:
                            st.error(f"❌ Database manager not available: {e}")
                            st.info("💡 Please build the database first using the sidebar.")
                            return
                        
                        if uploaded_file:
                            # Image search
                            import tempfile
                            import os
                            
                            # Save uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            results = db_manager.search_by_image(tmp_path, top_k=num_results)
                            
                            # Clean up temporary file
                            try:
                                os.unlink(tmp_path)
                            except:
                                pass
                        else:
                            # Text search
                            results = db_manager.search_similar_images(search_query, top_k=num_results)
                        
                        if results:
                            st.success(f"✨ Found {len(results)} matching images!")
                            AdvancedUIScreen._render_simple_gallery(results)
                        else:
                            st.warning("No results found. Try different search terms or check if your database is built.")
                            
                    except Exception as e:
                        st.error(f"Search error: {str(e)}")
                        st.info("💡 Make sure your database is built and ready before searching.")
                        # Debug info
                        st.write(f"Debug: {type(e).__name__}: {e}")
            else:
                st.warning("Please enter a search query or upload an image!")
    
    @staticmethod
    def _render_simple_gallery(results):
        """Simple, clean gallery display"""
        import os
        
        st.markdown("---")
        st.markdown("### 🎯 Search Results")
        
        # Simple responsive grid
        cols_per_row = 3
        for i in range(0, len(results), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, result in enumerate(results[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        # Simple image display
                        st.image(result['path'], use_container_width=True)
                        
                        # Simple info below
                        score_percentage = result['score'] * 100
                        filename = os.path.basename(result['path'])
                        
                        st.markdown(f"**{filename[:25]}{'...' if len(filename) > 25 else ''}**")
                        st.markdown(f"🎯 **{score_percentage:.1f}% match**")
                        
                        # Show caption if available
                        if 'caption' in result and result['caption']:
                            st.caption(f"💬 {result['caption'][:50]}{'...' if len(result['caption']) > 50 else ''}")
                            
                    except Exception as e:
                        st.error(f"Error loading result: {e}")
                        st.write(f"Path: {result.get('path', 'Unknown')}")
    
    @staticmethod
    def _render_latent_space():
        """Enhanced latent space visualization"""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">🌐 Visual Exploration</h2>
                <p style="color: var(--pd-text-secondary);">
                    Explore your images in a visual similarity space using advanced AI visualization
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        try:
            # Import and use the sophisticated latent space component
            from components.visualization.latent_space import render_latent_space_tab
            
            # Use the sophisticated UMAP visualization with all features
            render_latent_space_tab()
            
        except ImportError as e:
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-warning pd-fade-in">
                    <div style="font-size: 1.2rem;">🚧</div>
                    <div>
                        <strong>Latent space component not yet integrated</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            {e}
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced coming features preview
            features = [
                "🎯 UMAP 2D projection of image embeddings",
                "🔍 Interactive clustering with DBSCAN", 
                "🖱️ Click and drag selection of image groups",
                "🌟 Visual similarity exploration",
                "🔮 Pattern discovery in your collection"
            ]
            
            st.markdown(
                '''
                <div class="pd-card" style="margin: 1rem 0;">
                    <h4 style="color: var(--pd-secondary); margin-bottom: 1rem;">🌐 Coming Features:</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            for feature in features:
                st.markdown(
                    f'''
                    <div class="pd-stagger-item" style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(31, 119, 180, 0.05); border-left: 3px solid var(--pd-primary); border-radius: var(--pd-radius);">
                        {feature}
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
    
    @staticmethod
    def _render_ai_game():
        """Enhanced AI game interface"""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">🎮 AI Guessing Game</h2>
                <p style="color: var(--pd-text-secondary);">
                    Play interactive games with AI using your photo collection!
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        try:
            # Import and use the AI guessing game component
            from components.search.search_tabs import render_guessing_game_tab
            
            # Use the sophisticated AI game component
            render_guessing_game_tab()
            
        except ImportError as e:
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-warning pd-fade-in">
                    <div style="font-size: 1.2rem;">🚧</div>
                    <div>
                        <strong>AI Game component not yet integrated</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            {e}
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced games preview
            games = [
                {
                    "icon": "🔮",
                    "title": "AI Photo Guesser",
                    "description": "AI tries to guess your photos"
                },
                {
                    "icon": "🕵️",
                    "title": "Theme Detective", 
                    "description": "Find photos matching a theme"
                },
                {
                    "icon": "🧠",
                    "title": "Memory Challenge",
                    "description": "Test your photo memory"
                }
            ]
            
            cols = st.columns(len(games))
            for i, game in enumerate(games):
                with cols[i]:
                    st.markdown(
                        f'''
                        <div class="pd-feature-card pd-stagger-item pd-hover-lift" style="margin: 1rem 0;">
                            <div class="pd-feature-card-icon">{game['icon']}</div>
                            <div class="pd-feature-card-title">{game['title']}</div>
                            <div class="pd-feature-card-description">{game['description']}</div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )
    
    @staticmethod
    def _render_duplicates():
        """Enhanced duplicate detection interface"""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">👥 Duplicate Detection</h2>
                <p style="color: var(--pd-text-secondary);">
                    Find and manage duplicate or very similar images in your collection
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        try:
            # Import and use the duplicate detection component
            from components.search.search_tabs import render_duplicates_tab
            
            # Use the sophisticated duplicate detection
            render_duplicates_tab()
        
        except ImportError as e:
            st.markdown(
                f'''
                <div class="pd-alert pd-alert-warning pd-fade-in">
                    <div style="font-size: 1.2rem;">🚧</div>
                    <div>
                        <strong>Duplicate detection not yet integrated</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            {e}
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced features preview
            features = [
                "🔍 Visual similarity detection using AI",
                "📸 Exact duplicate finder for identical files", 
                "🗂️ Smart grouping of similar photos",
                "🗑️ Batch deletion tools for cleanup",
                "👀 Preview before delete for safety"
            ]
            
            st.markdown(
                '''
                <div class="pd-card" style="margin: 1rem 0;">
                    <h4 style="color: var(--pd-secondary); margin-bottom: 1rem;">👥 Coming Features:</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            for feature in features:
                st.markdown(
                    f'''
                    <div class="pd-stagger-item" style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(44, 160, 44, 0.05); border-left: 3px solid var(--pd-success); border-radius: var(--pd-radius);">
                        {feature}
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
    
    @staticmethod
    def _render_contextual_sidebar():
        """Enhanced contextual sidebar"""
        try:
            # Try to use the sophisticated sidebar
            from components.sidebar.context_sidebar import render_sidebar
            
            # Use the rich sidebar with enhanced styling
            with st.sidebar:
                st.markdown(
                    '''
                    <div class="pd-card" style="text-align: center; margin-bottom: 1.5rem;">
                        <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">🎛️ Advanced Controls</h3>
                        <div style="font-size: 0.875rem; color: var(--pd-text-secondary);">
                            Sophisticated features & monitoring
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            
            render_sidebar()
            
        except ImportError:
            # Fallback to enhanced simple sidebar
            AdvancedUIScreen._render_enhanced_simple_sidebar()
    
    @staticmethod
    def _render_enhanced_simple_sidebar():
        """Enhanced simple fallback sidebar"""
        with st.sidebar:
            st.markdown(
                '''
                <div class="pd-card" style="text-align: center; margin-bottom: 1.5rem;">
                    <h3 style="color: var(--pd-primary); margin-bottom: 0.5rem;">📊 Collection Info</h3>
                    <div style="font-size: 0.875rem; color: var(--pd-text-secondary);">
                        Basic collection statistics
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced collection stats
            folder_path = st.session_state.get('folder_path', 'Unknown')
            image_count = len(st.session_state.get('image_files', []))
            folder_name = os.path.basename(folder_path)
            
            st.markdown(
                f'''
                <div class="pd-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem;">📁</span>
                        <strong style="color: var(--pd-text-primary);">Folder</strong>
                    </div>
                    <div style="color: var(--pd-text-secondary); font-size: 0.9rem;">
                        {folder_name}
                    </div>
                </div>
                
                <div class="pd-card" style="margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem;">🖼️</span>
                        <strong style="color: var(--pd-text-primary);">Images</strong>
                    </div>
                    <div style="color: var(--pd-text-secondary); font-size: 0.9rem;">
                        {image_count:,} files discovered
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            st.markdown("---")
            
            # Quick actions
            st.markdown("### ⚡ Quick Actions")
            
            if st.button("🔄 Refresh Collection", use_container_width=True):
                st.info("🔄 Refresh functionality coming soon!")
            
            if st.button("⚙️ Settings", use_container_width=True):
                st.info("⚙️ Settings panel coming soon!")
            
            if st.button("📊 Statistics", use_container_width=True):
                st.info("📊 Detailed statistics coming soon!")


# Global function for easy import
def render_advanced_ui_screen():
    """Main entry point for Screen 3 with enhanced design system"""
    AdvancedUIScreen.render() 