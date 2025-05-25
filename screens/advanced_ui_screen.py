# 🎨 Advanced UI Screen for Pixel Detective
# 📌 Purpose: Full featured interface with sophisticated components + Design System
# 🚀 PERFORMANCE REVOLUTION: Lazy loading + beautiful UX
# ⚡ Key Innovation: Progressive enhancement with fallbacks
# 🧠 Philosophy: Beautiful, functional, and fast

import streamlit as st
from utils.logger import logger


class AdvancedUIScreen:
    """Screen 3: Full featured interface with sophisticated components + Design System"""

    
    @staticmethod
    def render():
        """Render the advanced UI with full features and beautiful design"""
        # Apply the design system
        AdvancedUIScreen._apply_design_system()
        
        # Enhanced header
        AdvancedUIScreen._render_enhanced_header()
        
        # Main content with sophisticated tabs
        AdvancedUIScreen._render_sophisticated_tabs()
        
        # Enhanced sidebar
        AdvancedUIScreen._render_contextual_sidebar()
    
    @staticmethod
    def _apply_design_system():
        """Apply the comprehensive design system"""
        st.markdown(
            '''
            <style>
            /* Pixel Detective Design System */
            :root {
                --pd-primary: #667eea;
                --pd-secondary: #764ba2;
                --pd-accent: #f093fb;
                --pd-success: #4ecdc4;
                --pd-warning: #ffe66d;
                --pd-error: #ff6b6b;
                --pd-text-primary: #2c3e50;
                --pd-text-secondary: #7f8c8d;
                --pd-surface: #ffffff;
                --pd-background: #f8f9fa;
                --pd-border: #e9ecef;
                --pd-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                --pd-radius: 8px;
                --pd-transition: all 0.3s ease;
            }
            
            /* Enhanced animations */
            @keyframes pd-fade-in {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes pd-slide-in {
                from { opacity: 0; transform: translateX(-30px); }
                to { opacity: 1; transform: translateX(0); }
            }
            
            .pd-fade-in { animation: pd-fade-in 0.6s ease-out; }
            .pd-slide-in { animation: pd-slide-in 0.5s ease-out; }
            
            /* Staggered animations */
            .pd-stagger-item:nth-child(1) { animation-delay: 0.1s; }
            .pd-stagger-item:nth-child(2) { animation-delay: 0.2s; }
            .pd-stagger-item:nth-child(3) { animation-delay: 0.3s; }
            .pd-stagger-item:nth-child(4) { animation-delay: 0.4s; }
            </style>
            ''',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def _render_enhanced_header():
        """Enhanced header with gradient and animations"""
        st.markdown(
            '''
            <div class="pd-hero pd-fade-in" style="
                background: linear-gradient(135deg, var(--pd-primary), var(--pd-secondary));
                padding: 3rem 2rem;
                border-radius: 20px;
                margin-bottom: 2rem;
                text-align: center;
                color: white;
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            ">
                <h1 style="font-size: 3rem; margin: 0; font-weight: 700;">🕵️‍♂️ Pixel Detective</h1>
                <p style="font-size: 1.3rem; margin: 1rem 0 0 0; opacity: 0.9;">Advanced AI-Powered Image Search & Analysis</p>
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
        """Enhanced search with beautiful nested tabs instead of ugly radio buttons"""
        # Beautiful header with gradient background
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
                    Find images using natural language or upload a photo to find similar ones
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Custom CSS for beautiful nested tabs
        st.markdown(
            '''
            <style>
            /* Beautiful nested tabs styling */
            .search-tabs .stTabs [data-baseweb="tab-list"] {
                gap: 0;
                background: linear-gradient(90deg, #f8f9fa, #e9ecef);
                border-radius: 12px;
                padding: 4px;
                margin-bottom: 2rem;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .search-tabs .stTabs [data-baseweb="tab"] {
                background: transparent;
                border: none;
                border-radius: 8px;
                padding: 1rem 2rem;
                font-weight: 600;
                font-size: 1.1rem;
                transition: all 0.3s ease;
                color: #6c757d;
            }
            
            .search-tabs .stTabs [aria-selected="true"] {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                transform: translateY(-2px);
            }
            
            .search-tabs .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
                background: rgba(102, 126, 234, 0.1);
                color: #495057;
            }
            
            /* Search content area styling */
            .search-content {
                background: white;
                border-radius: 15px;
                padding: 2rem;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                border: 1px solid #e9ecef;
            }
            </style>
            ''',
            unsafe_allow_html=True
        )
        
        # Create beautiful nested tabs for search types
        st.markdown('<div class="search-tabs">', unsafe_allow_html=True)
        
        text_tab, image_tab = st.tabs([
            "📝 Text Search", 
            "🖼️ Image Search"
        ])
        
        with text_tab:
            st.markdown('<div class="search-content">', unsafe_allow_html=True)
            try:
                from components.search.search_tabs import render_text_search_tab
                render_text_search_tab()
            except Exception as e:
                AdvancedUIScreen._render_beautiful_text_search_fallback()
            st.markdown('</div>', unsafe_allow_html=True)
        
        with image_tab:
            st.markdown('<div class="search-content">', unsafe_allow_html=True)
            try:
                from components.search.search_tabs import render_image_upload_tab
                render_image_upload_tab()
            except Exception as e:
                AdvancedUIScreen._render_beautiful_image_search_fallback()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def _render_beautiful_text_search_fallback():
        """Beautiful text search interface with working functionality"""
        st.markdown("### 📝 Search by Description")
        st.markdown("*Describe what you're looking for in natural language*")
        
        # Beautiful search input
        search_query = st.text_input(
            "",
            placeholder="e.g., 'sunset over mountains', 'cute dog playing', 'family vacation photos'",
            key="text_search_input",
            label_visibility="collapsed"
        )
        
        # Search options in columns
        col1, col2 = st.columns([3, 1])
        with col1:
            num_results = st.slider("Number of results:", 1, 20, 5, key="text_results_slider")
        with col2:
            search_button = st.button("🔍 Search Images", type="primary", use_container_width=True)
        
        if search_button and search_query:
            with st.spinner("🔍 Searching your collection..."):
                try:
                    # Try to use the actual search functionality
                    from utils.lazy_session_state import LazySessionManager
                    
                    # Check if database is ready - flexible check
                    database_indicators = [
                        st.session_state.get('database_ready', False),
                        st.session_state.get('database_built', False),
                        st.session_state.get('images_data') is not None,
                        hasattr(st.session_state, 'database_manager')
                    ]
                    
                    if not any(database_indicators):
                        st.warning("🔄 Database not ready yet. Please complete the image processing first.")
                        return
                    
                    # Get database manager and search
                    db_manager = LazySessionManager.ensure_database_manager()
                    results = db_manager.search_similar_images(search_query, top_k=num_results)
                    
                    if results:
                        st.success(f"✨ Found {len(results)} matching images!")
                        AdvancedUIScreen._render_beautiful_search_results(results)
                    else:
                        st.warning("No results found. Try different search terms or check if your database is built.")
                        
                except Exception as e:
                    st.error(f"Search error: {str(e)}")
                    st.info("💡 Make sure your database is built and ready before searching.")
        elif search_button:
            st.warning("Please enter a search query first!")
    
    @staticmethod
    def _render_beautiful_image_search_fallback():
        """Beautiful image search interface with working functionality"""
        st.markdown("### 🖼️ Search by Image")
        st.markdown("*Upload an image to find similar ones in your collection*")
        
        # Beautiful file uploader
        uploaded_file = st.file_uploader(
            "Choose an image...", 
            type=['jpg', 'jpeg', 'png', 'bmp', 'gif'],
            key="image_search_uploader"
        )
        
        if uploaded_file is not None:
            # Display uploaded image in a nice layout
            col1, col2 = st.columns([2, 3])
            
            with col1:
                st.image(uploaded_file, caption="📤 Uploaded Image", use_container_width=True)
                
            with col2:
                st.markdown("#### Search Settings")
                num_results = st.slider("Number of similar images:", 1, 20, 5, key="image_results_slider")
                
                search_button = st.button("🔍 Find Similar Images", type="primary", use_container_width=True)
                
                if search_button:
                    with st.spinner("🔍 Finding similar images..."):
                        try:
                            import tempfile
                            import os
                            from utils.lazy_session_state import LazySessionManager
                            
                            # Check if database is ready - flexible check
                            database_indicators = [
                                st.session_state.get('database_ready', False),
                                st.session_state.get('database_built', False),
                                st.session_state.get('images_data') is not None,
                                hasattr(st.session_state, 'database_manager')
                            ]
                            
                            if not any(database_indicators):
                                st.warning("🔄 Database not ready yet. Please complete the image processing first.")
                                return
                            
                            # Save uploaded file temporarily
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name
                            
                            # Get database manager and search
                            db_manager = LazySessionManager.ensure_database_manager()
                            results = db_manager.search_by_image(tmp_path, top_k=num_results)
                            
                            # Clean up temporary file
                            try:
                                os.unlink(tmp_path)
                            except:
                                pass
                            
                            if results:
                                st.success(f"✨ Found {len(results)} similar images!")
                                AdvancedUIScreen._render_beautiful_search_results(results)
                            else:
                                st.warning("No similar images found. Try a different image or check if your database is built.")
                                
                        except Exception as e:
                            st.error(f"Search error: {str(e)}")
                            st.info("💡 Make sure your database is built and ready before searching.")
    
    @staticmethod
    def _render_beautiful_search_results(results):
        """Render search results in a beautiful grid layout"""
        import os
        
        st.markdown("---")
        st.markdown("### 🎯 Search Results")
        
        # Create a responsive grid
        cols_per_row = 3
        for i in range(0, len(results), cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j, result in enumerate(results[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        # Beautiful result card
                        score_percentage = result['score'] * 100
                        filename = os.path.basename(result['path'])
                        
                        # Image with overlay
                        st.image(result['path'], use_container_width=True)
                        
                        # Info card
                        st.markdown(
                            f'''
                            <div style="
                                background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                                padding: 1rem;
                                border-radius: 10px;
                                margin-top: 0.5rem;
                                border-left: 4px solid #667eea;
                            ">
                                <div style="font-weight: 600; color: #495057; margin-bottom: 0.5rem;">
                                    📁 {filename[:30]}{'...' if len(filename) > 30 else ''}
                                </div>
                                <div style="color: #667eea; font-weight: 700; font-size: 1.1rem;">
                                    🎯 {score_percentage:.1f}% match
                                </div>
                            </div>
                            ''',
                            unsafe_allow_html=True
                        )
                        
                        # Additional metadata if available
                        if 'caption' in result and result['caption']:
                            st.markdown(f"**💬 Caption:** {result['caption']}")
                        
                        if 'tags' in result and result['tags']:
                            tags_str = ', '.join(result['tags']) if isinstance(result['tags'], list) else result['tags']
                            st.markdown(f"**🏷️ Tags:** {tags_str}")
                            
                    except Exception as e:
                        st.error(f"Error loading result: {e}")
                        st.write(f"Path: {result.get('path', 'Unknown')}")
    
    @staticmethod
    def _render_fallback_search():
        """Legacy fallback - keeping for compatibility"""
        AdvancedUIScreen._render_beautiful_text_search_fallback()
    
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
                        <strong>AI game component not yet integrated</strong>
                        <div style="margin-top: 0.5rem; font-size: 0.875rem; opacity: 0.8;">
                            {e}
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            # Enhanced coming features preview
            games = [
                "🎯 Guess what the AI sees in your photos",
                "🏆 Score points for accurate descriptions",
                "🎲 Random image challenges",
                "🤖 Compare your perception vs AI analysis",
                "📊 Track your guessing accuracy over time"
            ]
            
            st.markdown(
                '''
                <div class="pd-card" style="margin: 1rem 0;">
                    <h4 style="color: var(--pd-secondary); margin-bottom: 1rem;">🎮 Coming Games:</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            for game in games:
                st.markdown(
                    f'''
                    <div class="pd-stagger-item" style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(31, 119, 180, 0.05); border-left: 3px solid var(--pd-primary); border-radius: var(--pd-radius);">
                        {game}
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
                        <strong>Duplicate detection component not yet integrated</strong>
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
                "🔍 AI-powered similarity detection",
                "📊 Configurable similarity thresholds",
                "🗂️ Batch duplicate management",
                "💾 Smart storage optimization",
                "📈 Duplicate statistics and insights"
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
                    <div class="pd-stagger-item" style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(31, 119, 180, 0.05); border-left: 3px solid var(--pd-primary); border-radius: var(--pd-radius);">
                        {feature}
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
    
    @staticmethod
    def _render_contextual_sidebar():
        """Enhanced contextual sidebar with smart features"""
        try:
            # Import and use the enhanced sidebar component
            from components.sidebar.context_sidebar import render_sidebar
            
            # Use the sophisticated sidebar with all features
            render_sidebar()
            
        except ImportError as e:
            logger.warning(f"Sidebar component not available: {e}")
            # Fallback to simple sidebar
            AdvancedUIScreen._render_enhanced_simple_sidebar()
    
    @staticmethod
    def _render_enhanced_simple_sidebar():
        """Enhanced simple sidebar as fallback"""
        st.sidebar.markdown(
            '''
            <div style="
                background: linear-gradient(135deg, var(--pd-primary), var(--pd-secondary));
                padding: 1.5rem;
                border-radius: 15px;
                margin-bottom: 2rem;
                text-align: center;
                color: white;
            ">
                <h2 style="margin: 0; font-size: 1.5rem;">🎛️ Control Center</h2>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Advanced features coming soon!</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        # Enhanced status indicators
        status_items = [
            ("🔧 System Status", "All systems operational", "success"),
            ("🧠 AI Models", "Ready for lazy loading", "info"),
            ("💾 Database", "Awaiting configuration", "warning"),
            ("🔍 Search Engine", "Standby mode", "info")
        ]
        
        for title, status, status_type in status_items:
            color_map = {
                "success": "#4ecdc4",
                "warning": "#ffe66d", 
                "info": "#667eea",
                "error": "#ff6b6b"
            }
            
            st.sidebar.markdown(
                f'''
                <div style="
                    background: white;
                    padding: 1rem;
                    border-radius: 10px;
                    margin-bottom: 1rem;
                    border-left: 4px solid {color_map[status_type]};
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <div style="font-weight: 600; color: #2c3e50; margin-bottom: 0.5rem;">{title}</div>
                    <div style="color: #7f8c8d; font-size: 0.9rem;">{status}</div>
                </div>
                ''',
                unsafe_allow_html=True
            )


def render_advanced_ui_screen():
    """Main function to render the advanced UI screen"""
    AdvancedUIScreen.render()
