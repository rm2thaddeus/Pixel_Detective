# 🎛️ Screen 3: Advanced UI Screen - ENHANCED WITH DESIGN SYSTEM
# 📌 Purpose: Full-featured interface with integrated sophisticated components
# 🎯 Mission: Use ALL the advanced features from ui/ folder in 3-screen architecture
# 🎨 Sprint 02: Now with beautiful design system integration

import streamlit as st
import os
from frontend.core import service_api
from styles.style_injector import inject_pixel_detective_styles
from utils.logger import logger
import asyncio


class AdvancedUIScreen:
    """Screen 3: Full featured interface with sophisticated components + Design System"""
    
    @staticmethod
    async def render():
        """Render the enhanced advanced UI screen with design system"""
        # Inject our custom styles
        inject_pixel_detective_styles()
        
        # Add screen entrance animation
        st.markdown('<div class="pd-screen-enter">', unsafe_allow_html=True)
        
        await AdvancedUIScreen._render_enhanced_header()
        await AdvancedUIScreen._render_sophisticated_tabs()
        AdvancedUIScreen._render_contextual_sidebar()
        
        # Close animation wrapper
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    async def _render_enhanced_header():
        """Enhanced header with styled components"""
        folder_path = st.session_state.get('folder_path', 'Unknown')
        folder_name = os.path.basename(folder_path)
        image_count = 0
        try:
            # API call is now async
            response = await service_api.get_processed_images(page=1, limit=1) # Get 1 just for count, or modify API
            if response and not response.get("error") and "total" in response:
                image_count = response["total"]
            elif response and response.get("error"):
                logger.error(f"Error fetching image count for header: {response.get('error')}")
        except Exception as e:
            logger.error(f"Exception fetching image count for header: {e}")
        
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
    async def _render_sophisticated_tabs():
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
            await AdvancedUIScreen._render_sophisticated_search()
        
        with ai_game_tab:
            await AdvancedUIScreen._render_ai_game()
        
        with latent_space_tab:
            await AdvancedUIScreen._render_latent_space()
        
        with duplicates_tab:
            await AdvancedUIScreen._render_duplicates()
    
    @staticmethod
    async def _render_sophisticated_search():
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
                    Find images using text or upload a sample image
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
            await AdvancedUIScreen._render_text_search()
            st.markdown('</div>', unsafe_allow_html=True)
        
        with image_tab:
            st.markdown('<div class="search-content">', unsafe_allow_html=True)
            await AdvancedUIScreen._render_image_search()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    async def _render_text_search():
        st.markdown("### 📝 Search by Description")
        search_query = st.text_input(
            "",
            placeholder="e.g., 'sunset over mountains', 'cute dog playing', 'family vacation photos'",
            key="text_search_input",
            label_visibility="collapsed"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            num_results = st.slider("Number of results:", 1, 20, 5, key="text_results_slider")
        with col2:
            search_button = st.button("🔍 Search Images", type="primary", use_container_width=True)
        if search_button and search_query:
            with st.spinner("🔍 Searching your collection..."):
                try:
                    # API call is now async
                    results = await service_api.search_images_by_text(query=search_query, top_k=num_results)
                    if results and not results.get("error"):
                        st.success(f"✨ Found {len(results)} matching images!")
                        AdvancedUIScreen._render_search_results(results)
                    elif results and results.get("error"):
                        st.error(f"Search error: {results.get('error')}")
                    else:
                        st.warning("No results found. Try different search terms.")
                except Exception as e:
                    st.error(f"Search error: {str(e)}")
    
    @staticmethod
    async def _render_image_search():
        st.markdown("### 🖼️ Search by Image")
        uploaded_file = st.file_uploader(
            "Choose an image...", 
            type=['jpg', 'jpeg', 'png', 'bmp', 'gif'],
            key="image_search_uploader"
        )
        if uploaded_file is not None:
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
                            # API call is now async
                            image_bytes = uploaded_file.getvalue()
                            results = await service_api.search_images_by_image(image_bytes=image_bytes, top_k=num_results)
                            if results and not results.get("error"):
                                st.success(f"✨ Found {len(results)} similar images!")
                                AdvancedUIScreen._render_search_results(results)
                            elif results and results.get("error"):
                                st.error(f"Search error: {results.get('error')}")
                            else:
                                st.warning("No similar images found.")
                        except Exception as e:
                            st.error(f"Image search error: {str(e)}")
    
    @staticmethod
    def _render_search_results(results):
        import os
        st.markdown("---")
        st.markdown("### 🎯 Search Results")
        cols_per_row = 3
        for i in range(0, len(results), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, result in enumerate(results[i:i+cols_per_row]):
                with cols[j]:
                    try:
                        st.image(result['path'], use_container_width=True)
                        score_percentage = result.get('score', 0) * 100
                        filename = os.path.basename(result['path'])
                        st.markdown(f"**{filename[:25]}{'...' if len(filename) > 25 else ''}**")
                        st.markdown(f"🎯 **{score_percentage:.1f}% match**")
                        if 'caption' in result and result['caption']:
                            st.caption(f"💬 {result['caption'][:50]}{'...' if len(result['caption']) > 50 else ''}")
                    except Exception as e:
                        st.error(f"Error loading result: {e}")
                        st.write(f"Path: {result.get('path', 'Unknown')}")
    
    @staticmethod
    async def _render_latent_space():
        """Enhanced latent space visualization"""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">�� Visual Exploration</h2>
                <p style="color: var(--pd-text-secondary);">
                    Explore your images in a visual similarity space using advanced AI visualization
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        try:
            # Import and use the sophisticated latent space component
            from frontend.components.visualization.latent_space import render_latent_space_tab
            
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
    async def _render_ai_game():
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
            from frontend.components.search.search_tabs import render_guessing_game_tab
            
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
    async def _render_duplicates():
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
        
        # TODO: When backend endpoint is available, use service_api.find_duplicates()
        st.info("Duplicate detection coming soon! Backend support required.")
    
    @staticmethod
    def _render_contextual_sidebar():
        """Enhanced contextual sidebar with smart features"""
        try:
            # Import and use the enhanced sidebar component
            from frontend.components.sidebar.context_sidebar import render_sidebar
            
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


async def render_advanced_ui_screen():
    """Main function to render the advanced UI screen"""
    await AdvancedUIScreen.render()
