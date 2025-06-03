# 🎛️ Screen 3: Advanced UI Screen - ENHANCED WITH DESIGN SYSTEM
# 📌 Purpose: Full-featured interface with integrated sophisticated components
# 🎯 Mission: Use ALL the advanced features from ui/ folder in 3-screen architecture
# 🎨 Sprint 02: Now with beautiful design system integration

import streamlit as st
import os
from core import service_api
from styles.style_injector import inject_pixel_detective_styles, create_styled_button, create_loading_spinner
from utils.logger import logger
import asyncio
import json
from datetime import datetime
from components.visualization.latent_space import render_latent_space_tab
from components.search.search_tabs import render_guessing_game_tab
from components.sidebar.context_sidebar import render_sidebar
from frontend.components.accessibility import AccessibilityEnhancer


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
            response = await service_api.get_processed_images(page=1, limit=1)
            if response and not response.get("error") and "total" in response:
                image_count = response["total"]
            elif response and response.get("error"):
                st.error(f"Error fetching image count: {response.get('error')}")
        except Exception as e:
            st.error(f"Exception fetching image count: {e}")
        AccessibilityEnhancer.add_skip_navigation()
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
        
        search_tab, ai_game_tab, latent_space_tab, duplicates_tab, random_tab = st.tabs([
            "🔍 Search", 
            "🎮 AI Game", 
            "🌐 Latent Space", 
            "👥 Duplicates",
            "🎲 Random Image"
        ])
        
        with search_tab:
            await AdvancedUIScreen._render_sophisticated_search()
        
        with ai_game_tab:
            await AdvancedUIScreen._render_ai_game()
        
        with latent_space_tab:
            await AdvancedUIScreen._render_latent_space()
        
        with duplicates_tab:
            await AdvancedUIScreen._render_duplicates()
        
        with random_tab:
            await AdvancedUIScreen._render_random_image()
    
    @staticmethod
    async def _render_sophisticated_search():
        """Enhanced search with sidebar filtering, sorting, pagination, and vector search integration."""
        import json
        from datetime import datetime

        # Sidebar for filters and sorting
        with st.sidebar:
            st.markdown("## 🔍 Search Filters")
            @st.cache_data
            def get_tag_options():
                return ["nature", "people", "city", "animals", "vacation", "family", "work"]
            tag_options = get_tag_options()
            selected_tags = st.multiselect("Tags", tag_options, key="search_tags")
            date_range = st.date_input("Date range", [], key="search_date_range")
            st.markdown("## 🔃 Sorting")
            sort_field = st.selectbox("Sort by", ["created_at", "name"], key="search_sort_field")
            sort_order = st.radio("Order", ["desc", "asc"], key="search_sort_order")

        # Pagination state
        if 'search_page' not in st.session_state:
            st.session_state['search_page'] = 1
        if 'search_per_page' not in st.session_state:
            st.session_state['search_per_page'] = 9

        # Build filters for API
        filters = {}
        if selected_tags:
            filters['tags'] = selected_tags
        if date_range and len(date_range) == 2:
            filters['date_from'] = date_range[0].isoformat()
            filters['date_to'] = date_range[1].isoformat()
        filters_json_str = json.dumps(filters) if filters else None

        # Main area: nested tabs for standard and vector search
        st.markdown('<div class="search-tabs">', unsafe_allow_html=True)
        standard_tab, vector_tab = st.tabs(["🖼️ Standard Search", "🧬 Vector Search"])
        with standard_tab:
            st.markdown("### 🖼️ Image Results")
            placeholder = st.empty()
            with placeholder.container():
                with st.spinner("Loading images..."):
                    try:
                        result = await service_api.list_images_qdrant(
                            page=st.session_state['search_page'],
                            per_page=st.session_state['search_per_page'],
                            filters_json_str=filters_json_str,
                            sort_by=sort_field,
                            sort_order=sort_order
                        )
                        if result and not result.get('error'):
                            images = result.get('images', [])
                            total = result.get('total', 0)
                            page = result.get('page', 1)
                            per_page = result.get('per_page', st.session_state['search_per_page'])
                            if images:
                                cols_per_row = 3
                                for i in range(0, len(images), cols_per_row):
                                    cols = st.columns(cols_per_row)
                                    for j, img in enumerate(images[i:i+cols_per_row]):
                                        with cols[j]:
                                            st.image(img.get('url', img.get('path', '')), use_container_width=True)
                                            st.markdown(f"**{img.get('filename', 'Image')}**")
                                            st.caption(f"Tags: {', '.join(img.get('tags', []))}")
                                            st.caption(f"Date: {img.get('created_at', 'N/A')}")
                            else:
                                st.info("No images found for the selected filters.")
                            total_pages = max(1, (total + per_page - 1) // per_page)
                            col1, col2, col3 = st.columns([1,2,1])
                            with col1:
                                if st.button("⬅️ Prev", disabled=page <= 1, key="search_prev_page"):
                                    st.session_state['search_page'] = max(1, page - 1)
                                    st.experimental_rerun()
                            with col2:
                                st.markdown(f"Page **{page}** of **{total_pages}**")
                            with col3:
                                if st.button("Next ➡️", disabled=page >= total_pages, key="search_next_page"):
                                    st.session_state['search_page'] = min(total_pages, page + 1)
                                    st.experimental_rerun()
                        else:
                            st.error(f"Search error: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Search error: {str(e)}")
        with vector_tab:
            st.markdown("### 🧬 Vector Search (Text or Image)")
            vector_mode = st.radio("Search by", ["Text", "Image"], key="vector_mode")
            embedding = None
            if vector_mode == "Text":
                text_query = st.text_input("Enter a description for semantic search", key="vector_text_query")
                if st.button("Get Embedding & Search", key="vector_text_search_btn") and text_query:
                    with st.spinner("Getting embedding and searching..."):
                        try:
                            emb_result = await service_api.get_embedding(text_query.encode("utf-8"), model_name="clip")
                            embedding = emb_result.get("embedding")
                            if embedding:
                                search_result = await service_api.search_images_vector(embedding=embedding, filters=filters, limit=st.session_state['search_per_page'])
                                if search_result and not search_result.get('error'):
                                    AdvancedUIScreen._render_search_results(search_result)
                                else:
                                    st.error(f"Vector search error: {search_result.get('error', 'Unknown error')}")
                            else:
                                st.error("Failed to get embedding from text.")
                        except Exception as e:
                            st.error(f"Embedding/search error: {str(e)}")
            else:
                uploaded_file = st.file_uploader("Upload an image for semantic search", type=['jpg', 'jpeg', 'png', 'bmp', 'gif'], key="vector_image_uploader")
                if st.button("Get Embedding & Search", key="vector_image_search_btn") and uploaded_file:
                    with st.spinner("Getting embedding and searching..."):
                        try:
                            image_bytes = uploaded_file.getvalue()
                            emb_result = await service_api.get_embedding(image_bytes, model_name="clip")
                            embedding = emb_result.get("embedding")
                            if embedding:
                                search_result = await service_api.search_images_vector(embedding=embedding, filters=filters, limit=st.session_state['search_per_page'])
                                if search_result and not search_result.get('error'):
                                    AdvancedUIScreen._render_search_results(search_result)
                                else:
                                    st.error(f"Vector search error: {search_result.get('error', 'Unknown error')}")
                            else:
                                st.error("Failed to get embedding from image.")
                        except Exception as e:
                            st.error(f"Embedding/search error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def _render_search_results(search_result_data):
        """Helper to render search results from vector search."""
        # Accommodate common keys for results like 'results' or 'hits'
        images = search_result_data.get('results', search_result_data.get('hits', []))
        
        if images:
            st.success(f"Found {len(images)} similar images.")
            cols_per_row = 3  # Or make this configurable
            for i in range(0, len(images), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, img_data in enumerate(images[i:i+cols_per_row]):
                    with cols[j]:
                        payload = img_data.get('payload', {}) # Qdrant often stores metadata in payload
                        img_path_or_url = payload.get('path', img_data.get('path', img_data.get('url'))) # Check multiple possible keys
                        
                        filename = payload.get('filename', os.path.basename(img_path_or_url) if img_path_or_url else 'Image')
                        caption_text = payload.get('caption', img_data.get('caption', filename)) # Prefer specific caption, fallback to filename
                        
                        if img_path_or_url:
                            try:
                                st.image(img_path_or_url, use_container_width=True, caption=f"Score: {img_data.get('score', 'N/A'):.4f}")
                            except Exception as e:
                                st.caption(f"Cannot load: {filename} ({e})")
                        else:
                            st.caption(f"No image path/URL for: {filename}")

                        st.markdown(f"**{filename}**")
                        # Display other relevant metadata from payload if needed
                        # For example, if 'tags' or 'created_at' are in payload:
                        tags = payload.get('tags', [])
                        if tags:
                            st.caption(f"Tags: {', '.join(tags)}")
                        created_at = payload.get('created_at')
                        if created_at:
                            st.caption(f"Date: {created_at}")
        else:
            st.info("No similar images found for this query.")
    
    @staticmethod
    async def _render_latent_space():
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
        """Enhanced duplicate detection interface with error handling, retry, and accessibility."""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;" role="region" aria-label="Duplicate Detection">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">👥 Duplicate Detection</h2>
                <p style="color: var(--pd-text-secondary);">
                    Find and manage duplicate or very similar images in your collection
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        if 'duplicates_result' not in st.session_state:
            st.session_state['duplicates_result'] = None
        if 'duplicates_error' not in st.session_state:
            st.session_state['duplicates_error'] = None
        if 'duplicates_loading' not in st.session_state:
            st.session_state['duplicates_loading'] = False

        placeholder = st.empty()
        if st.button('🔍 Run Duplicate Detection', disabled=st.session_state['duplicates_loading'], key='run_duplicates_btn'):
            st.session_state['duplicates_loading'] = True
            st.session_state['duplicates_result'] = None
            st.session_state['duplicates_error'] = None

        if st.session_state['duplicates_loading']:
            with placeholder.container():
                with st.spinner('Detecting duplicates...'):
                    try:
                        result = await service_api.get_duplicates_qdrant()
                        if result and not result.get('error'):
                            st.session_state['duplicates_result'] = result
                            st.session_state['duplicates_error'] = None
                        else:
                            st.session_state['duplicates_result'] = None
                            st.session_state['duplicates_error'] = result.get('error', 'Unknown error')
                    except Exception as e:
                        st.session_state['duplicates_result'] = None
                        st.session_state['duplicates_error'] = str(e)
                    st.session_state['duplicates_loading'] = False

        if st.session_state['duplicates_result']:
            with placeholder.container():
                st.success('Duplicate detection complete!')
                groups = st.session_state['duplicates_result'].get('groups', [])
                if groups:
                    for idx, group in enumerate(groups, 1):
                        st.markdown(f"**Group {idx}** ({len(group)} images):")
                        cols = st.columns(len(group))
                        for col, img in zip(cols, group):
                            with col:
                                st.image(img.get('url', ''), caption=img.get('filename', ''))
                else:
                    st.info('No duplicates found!')
        elif st.session_state['duplicates_error']:
            with placeholder.container():
                st.error(f"Duplicate detection failed: {st.session_state['duplicates_error']}")
                if st.button('Retry Duplicate Detection', key='retry_duplicates_btn'):
                    st.session_state['duplicates_loading'] = True
                    st.session_state['duplicates_result'] = None
                    st.session_state['duplicates_error'] = None
        elif not st.session_state['duplicates_loading']:
            with placeholder.container():
                st.info('Click the button above to start duplicate detection.')
    
    @staticmethod
    def _render_contextual_sidebar():
        """Enhanced contextual sidebar with smart features"""
        try:
            # Import and use the enhanced sidebar component
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

    @staticmethod
    async def _render_random_image():
        """Random Image UI: Button, spinner, image display, error handling, retry, accessibility."""
        st.markdown(
            '''
            <div class="pd-card pd-fade-in" style="margin-bottom: 2rem;" role="region" aria-label="Random Image">
                <h2 style="color: var(--pd-primary); margin-bottom: 1rem;">🎲 Random Image</h2>
                <p style="color: var(--pd-text-secondary);">
                    Fetch and display a random image from your collection.
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        if 'random_image_result' not in st.session_state:
            st.session_state['random_image_result'] = None
        if 'random_image_error' not in st.session_state:
            st.session_state['random_image_error'] = None
        if 'random_image_loading' not in st.session_state:
            st.session_state['random_image_loading'] = False

        placeholder = st.empty()
        if st.button('🎲 Show Random Image', disabled=st.session_state['random_image_loading'], key='show_random_btn'):
            st.session_state['random_image_loading'] = True
            st.session_state['random_image_result'] = None
            st.session_state['random_image_error'] = None

        if st.session_state['random_image_loading']:
            with placeholder.container():
                with st.spinner('Fetching a random image...'):
                    try:
                        result = await service_api.get_random_image_qdrant()
                        if result and not result.get('error'):
                            st.session_state['random_image_result'] = result
                            st.session_state['random_image_error'] = None
                        else:
                            st.session_state['random_image_result'] = None
                            st.session_state['random_image_error'] = result.get('error', 'Unknown error')
                    except Exception as e:
                        st.session_state['random_image_result'] = None
                        st.session_state['random_image_error'] = str(e)
                    st.session_state['random_image_loading'] = False

        if st.session_state['random_image_result']:
            with placeholder.container():
                img_url = st.session_state['random_image_result'].get('url') or st.session_state['random_image_result'].get('path')
                meta = st.session_state['random_image_result']
                if img_url:
                    st.image(img_url, caption=meta.get('filename', 'Random Image'), use_container_width=True)
                st.markdown('---')
                st.markdown('**Metadata:**')
                for k, v in meta.items():
                    if k not in ('url', 'path', 'image_bytes'):
                        st.markdown(f"- **{k}**: {v}")
        elif st.session_state['random_image_error']:
            with placeholder.container():
                st.error(f"Failed to fetch random image: {st.session_state['random_image_error']}")
                if st.button('Retry Random Image', key='retry_random_btn'):
                    st.session_state['random_image_loading'] = True
                    st.session_state['random_image_result'] = None
                    st.session_state['random_image_error'] = None
        elif not st.session_state['random_image_loading']:
            with placeholder.container():
                st.info('Click the button above to fetch a random image.')


async def render_advanced_ui_screen():
    """Main function to render the advanced UI screen"""
    await AdvancedUIScreen.render()
