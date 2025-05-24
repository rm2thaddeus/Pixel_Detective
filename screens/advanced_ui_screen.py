# 🎛️ Screen 3: Advanced UI Screen - SOPHISTICATED VERSION
# 📌 Purpose: Full-featured interface with integrated sophisticated components
# 🎯 Mission: Use ALL the advanced features from ui/ folder in 3-screen architecture

import os
import streamlit as st
from core.app_state import AppStateManager, AppState


class AdvancedUIScreen:
    """Screen 3: Full featured interface with sophisticated components"""
    
    @staticmethod
    def render():
        """Render the advanced UI screen with real components"""
        AdvancedUIScreen._render_header()
        AdvancedUIScreen._render_sophisticated_tabs()
        AdvancedUIScreen._render_contextual_sidebar()
    
    @staticmethod
    def _render_header():
        """Render the advanced UI header"""
        folder_path = st.session_state.get('folder_path', 'Unknown')
        image_count = len(st.session_state.get('image_files', []))
        
        st.title(f"🕵️‍♂️ Pixel Detective - Collection: {os.path.basename(folder_path)}")
        st.markdown(f"**Path:** `{folder_path}` • **Images:** {image_count:,} items")
        st.markdown("---")
    
    @staticmethod
    def _render_sophisticated_tabs():
        """Render tabs with real sophisticated components"""
        # Create tabs
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
        """Use the real search components from ui/tabs.py"""
        try:
            # Import and use the sophisticated search components
            from components.search.search_tabs import render_text_search_tab, render_image_upload_tab
            
        st.markdown("## 🔍 Search Your Collection")
        
        # Search mode selection
        search_mode = st.radio(
            "Search Mode:",
            ["📝 Text Search", "🖼️ Image Search"],
            horizontal=True
        )
        
        if search_mode == "📝 Text Search":
                # Use the sophisticated text search component
                render_text_search_tab()
        else:
                # Use the sophisticated image search component  
                render_image_upload_tab()
                
        except ImportError as e:
            st.error(f"🚧 Search components not yet integrated: {e}")
            st.info("Using fallback search interface...")
            AdvancedUIScreen._render_fallback_search()
    
    @staticmethod
    def _render_fallback_search():
        """Fallback search interface if components aren't available"""
        st.markdown("### 🔍 Simple Search")
        
            search_query = st.text_input(
            "Search your photos:",
            placeholder="e.g., 'sunset', 'family', 'vacation'"
        )
        
        if st.button("🔍 Search", type="primary") and search_query:
            st.info(f"🔍 Searching for: {search_query}")
            st.info("🚧 Full search functionality coming soon!")
    
    @staticmethod
    def _render_latent_space():
        """Use the sophisticated UMAP visualization from latent_space.py"""
        try:
            # Import and use the sophisticated latent space component
            from components.visualization.latent_space import render_latent_space_tab
            
            st.markdown("## 🌐 Visual Exploration")
            st.markdown("Explore your images in a visual similarity space using advanced AI visualization.")
            
            # Use the sophisticated UMAP visualization with all features:
            # - UMAP dimensionality reduction with caching
            # - DBSCAN clustering with interactive tuning  
            # - Plotly scatter plot with click/lasso selection
            # - Dynamic sampling for large datasets
            render_latent_space_tab()
            
        except ImportError as e:
            st.error(f"🚧 Latent space component not yet integrated: {e}")
            st.info("🌐 Advanced visual exploration coming soon!")
            st.markdown("""
            **Coming Features:**
            - **UMAP 2D projection** of image embeddings
            - **Interactive clustering** with DBSCAN
            - **Click and drag selection** of image groups
            - **Visual similarity exploration** 
            - **Pattern discovery** in your collection
            """)
    
    @staticmethod
    def _render_ai_game():
        """Use the AI guessing game from tabs.py"""
        try:
            # Import and use the AI guessing game component
            from components.search.search_tabs import render_guessing_game_tab
            
            st.markdown("## 🎮 AI Guessing Game")
            st.markdown("Play interactive games with AI using your photo collection!")
            
            # Use the sophisticated AI game component
            render_guessing_game_tab()
            
        except ImportError as e:
            st.error(f"🚧 AI Game component not yet integrated: {e}")
            st.info("🎮 AI games coming soon!")
        st.markdown("""
            **Coming Games:**
            - **AI Photo Guesser**: AI tries to guess your photos
            - **Theme Detective**: Find photos matching a theme
            - **Memory Challenge**: Test your photo memory
            - **Visual Trivia**: Answer questions about your photos
            """)
    
    @staticmethod
    def _render_duplicates():
        """Use the duplicate detection from tabs.py"""
        try:
            # Import and use the duplicate detection component
            from components.search.search_tabs import render_duplicates_tab
            
        st.markdown("## 👥 Duplicate Detection")
            st.markdown("Find and manage duplicate or very similar images in your collection.")
        
            # Use the sophisticated duplicate detection
            render_duplicates_tab()
        
        except ImportError as e:
            st.error(f"🚧 Duplicate detection not yet integrated: {e}")
            st.info("👥 Smart duplicate detection coming soon!")
            st.markdown("""
            **Coming Features:**
            - **Visual similarity detection** using AI
            - **Exact duplicate finder** for identical files
            - **Smart grouping** of similar photos
            - **Batch deletion tools** for cleanup
            - **Preview before delete** for safety
            """)
    
    @staticmethod
    def _render_contextual_sidebar():
        """Context-aware sidebar for advanced features"""
        try:
            # Try to use the sophisticated sidebar
            from components.sidebar.context_sidebar import render_sidebar
            
            # Use the rich sidebar with:
            # - GPU status with fun names
            # - Database stats and info
            # - Memory usage monitoring  
            # - Advanced controls
            render_sidebar()
            
        except ImportError:
            # Fallback to simple sidebar
            AdvancedUIScreen._render_simple_sidebar()
    
    @staticmethod
    def _render_simple_sidebar():
        """Simple fallback sidebar"""
        with st.sidebar:
            st.markdown("### 📊 Collection Info")
            
            # Basic collection stats
            folder_path = st.session_state.get('folder_path', 'Unknown')
            image_count = len(st.session_state.get('image_files', []))
            
            st.markdown(f"**📁 Folder:** {os.path.basename(folder_path)}")
            st.metric("🖼️ Total Images", f"{image_count:,}")
            st.metric("💾 Database", "Ready" if st.session_state.get('database_ready') else "Loading")
            
            st.markdown("---")
            st.markdown("### 🎯 Quick Actions")
            
            if st.button("🔄 Refresh Collection"):
                st.info("🔄 Refresh functionality coming soon!")
            
            if st.button("📊 View Statistics"):
                AdvancedUIScreen._show_collection_stats()
            
            if st.button("⚙️ Settings"):
                AdvancedUIScreen._show_settings()
            
            if st.button("🏠 Back to Start"):
                if st.button("✅ Confirm", key="confirm_home"):
                AppStateManager.reset_to_fast_ui()
                st.rerun()
    
    @staticmethod
    def _show_collection_stats():
        """Show detailed collection statistics"""
        with st.expander("📊 Collection Statistics", expanded=True):
            folder_path = st.session_state.get('folder_path', '')
            image_files = st.session_state.get('image_files', [])
            
            st.markdown(f"**📁 Collection Path:** `{folder_path}`")
            st.markdown(f"**🖼️ Total Images:** {len(image_files):,}")
            
            if image_files:
                # File type breakdown
            extensions = {}
                total_size = 0
                
                for img_path in image_files[:100]:  # Sample first 100 for performance
                    try:
                        ext = os.path.splitext(img_path)[1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1
            
                        if os.path.exists(img_path):
                            total_size += os.path.getsize(img_path)
                    except Exception:
                        continue
                
                st.markdown("**📈 File Types:**")
            for ext, count in sorted(extensions.items()):
                    st.markdown(f"- `{ext}`: {count} files")
                
                if total_size > 0:
                    size_mb = total_size / (1024 * 1024)
                    st.markdown(f"**💾 Sample Size:** {size_mb:.1f} MB (from first 100 files)")
            
            st.markdown("**🤖 AI Status:**")
            st.markdown(f"- Models loaded: {'✅' if st.session_state.get('models_loaded') else '❌'}")
            st.markdown(f"- Database ready: {'✅' if st.session_state.get('database_ready') else '❌'}")
    
    @staticmethod
    def _show_settings():
        """Show application settings"""
        with st.expander("⚙️ Settings", expanded=True):
            st.markdown("**🎨 Display Options:**")
            
            # Search results per page
            results_per_page = st.slider("Search results per page", 6, 24, 12)
            st.session_state.results_per_page = results_per_page
            
            # Image preview size
            preview_size = st.select_slider(
                "Image preview size", 
                options=["Small", "Medium", "Large"], 
                value="Medium"
            )
            st.session_state.preview_size = preview_size
            
            st.markdown("**🔍 Search Options:**")
            
            # Search similarity threshold
            similarity_threshold = st.slider("Search similarity threshold", 0.1, 1.0, 0.7, 0.1)
            st.session_state.similarity_threshold = similarity_threshold
            
            # Enable advanced features
            enable_clustering = st.checkbox("Enable clustering in latent space", value=True)
            st.session_state.enable_clustering = enable_clustering
            
            st.markdown("**💾 Data Options:**")
            
            if st.button("📤 Export Search Results"):
                st.info("📤 Export functionality coming soon!")
            
            if st.button("🗑️ Clear Cache"):
                st.info("🗑️ Cache clearing coming soon!")
            
            if st.button("🔄 Rebuild Database"):
                st.warning("⚠️ This will rebuild the entire database. Are you sure?")
                if st.button("✅ Yes, Rebuild", key="confirm_rebuild"):
                    st.info("🔄 Database rebuild functionality coming soon!")


# Global function for easy import
def render_advanced_ui_screen():
    """Main entry point for Screen 3"""
    AdvancedUIScreen.render() 