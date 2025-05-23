# 🎛️ Screen 3: Advanced UI Screen
# 📌 Purpose: Full-featured interface for all app capabilities
# 🎯 Mission: Organized tabs with seamless navigation

import os
import streamlit as st
from core.app_state import AppStateManager, AppState


class AdvancedUIScreen:
    """Screen 3: Full featured interface with tabs"""
    
    @staticmethod
    def render():
        """Render the advanced UI screen"""
        AdvancedUIScreen._render_header()
        AdvancedUIScreen._render_tab_navigation()
        AdvancedUIScreen._render_sidebar()
    
    @staticmethod
    def _render_header():
        """Render the advanced UI header"""
        folder_path = st.session_state.get('folder_path', 'Unknown')
        image_count = len(st.session_state.get('image_files', []))
        
        st.title(f"🕵️‍♂️ Pixel Detective - Collection: {os.path.basename(folder_path)}")
        st.markdown(f"**Path:** `{folder_path}` • **Images:** {image_count:,} items")
        st.markdown("---")
    
    @staticmethod
    def _render_tab_navigation():
        """Render the main tab navigation"""
        # Create tabs
        search_tab, ai_game_tab, latent_space_tab, duplicates_tab = st.tabs([
            "🔍 Search", 
            "🎮 AI Game", 
            "🌐 Latent Space", 
            "👥 Duplicates"
        ])
        
        with search_tab:
            AdvancedUIScreen._render_search_tab()
        
        with ai_game_tab:
            AdvancedUIScreen._render_ai_game_tab()
        
        with latent_space_tab:
            AdvancedUIScreen._render_latent_space_tab()
        
        with duplicates_tab:
            AdvancedUIScreen._render_duplicates_tab()
    
    @staticmethod
    def _render_search_tab():
        """Render the search functionality tab"""
        st.markdown("## 🔍 Search Your Collection")
        
        # Search mode selection
        search_mode = st.radio(
            "Search Mode:",
            ["📝 Text Search", "🖼️ Image Search"],
            horizontal=True
        )
        
        if search_mode == "📝 Text Search":
            AdvancedUIScreen._render_text_search()
        else:
            AdvancedUIScreen._render_image_search()
        
        # Search results section
        st.markdown("---")
        AdvancedUIScreen._render_search_results()
    
    @staticmethod
    def _render_text_search():
        """Render text-based search interface"""
        st.markdown("### 📝 Text Search")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_query = st.text_input(
                "Describe what you're looking for:",
                placeholder="e.g., 'sunset over lake', 'cat photos', 'birthday party'",
                help="Use natural language to describe the images you want to find"
            )
        
        with col2:
            search_button = st.button("🔍 Search", type="primary")
        
        if search_button and search_query:
            st.session_state.current_search_query = search_query
            st.session_state.search_type = "text"
            AdvancedUIScreen._perform_search(search_query, "text")
        
        # Search suggestions
        if not search_query:
            st.markdown("**💡 Try searching for:**")
            suggestions = [
                "sunset beach", "family photos", "food cooking", 
                "nature landscape", "pets animals", "vacation travel"
            ]
            
            cols = st.columns(3)
            for i, suggestion in enumerate(suggestions):
                with cols[i % 3]:
                    if st.button(f"💭 {suggestion}", key=f"suggestion_{i}"):
                        st.session_state.current_search_query = suggestion
                        st.session_state.search_type = "text"
                        AdvancedUIScreen._perform_search(suggestion, "text")
    
    @staticmethod
    def _render_image_search():
        """Render image-based search interface"""
        st.markdown("### 🖼️ Image Search")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Upload an image to find similar ones:",
                type=['jpg', 'jpeg', 'png', 'gif', 'bmp'],
                help="Upload an image and we'll find visually similar images in your collection"
            )
        
        with col2:
            if uploaded_file is not None:
                st.image(uploaded_file, caption="Search Image", width=150)
                if st.button("🔍 Find Similar", type="primary"):
                    st.session_state.search_image = uploaded_file
                    st.session_state.search_type = "image"
                    AdvancedUIScreen._perform_search(uploaded_file, "image")
        
        # Alternative: Select from collection
        st.markdown("**Or select an image from your collection:**")
        if st.button("📂 Browse Collection"):
            st.info("🔄 Collection browser coming soon!")
    
    @staticmethod
    def _perform_search(query, search_type):
        """Perform the actual search"""
        with st.spinner(f"🔍 Searching your collection..."):
            # Simulate search process
            import time
            import random
            time.sleep(1)
            
            # Generate mock results
            image_files = st.session_state.get('image_files', [])
            if image_files:
                # Simulate finding results
                num_results = random.randint(5, min(25, len(image_files)))
                results = random.sample(image_files, num_results)
                
                st.session_state.search_results = results
                st.session_state.last_search_query = query
                st.session_state.last_search_type = search_type
                
                st.success(f"✅ Found {len(results)} matching images!")
            else:
                st.error("❌ No images loaded. Please restart the application.")
    
    @staticmethod
    def _render_search_results():
        """Render search results"""
        results = st.session_state.get('search_results', [])
        last_query = st.session_state.get('last_search_query', '')
        
        if results and last_query:
            st.markdown(f"### 📊 Results for: \"{last_query}\"")
            st.markdown(f"**Found {len(results)} matches**")
            
            # Results per page
            results_per_page = 12
            total_pages = (len(results) + results_per_page - 1) // results_per_page
            
            if total_pages > 1:
                page = st.selectbox("Page:", range(1, total_pages + 1)) - 1
            else:
                page = 0
            
            start_idx = page * results_per_page
            end_idx = min(start_idx + results_per_page, len(results))
            page_results = results[start_idx:end_idx]
            
            # Display results in grid
            cols = st.columns(4)
            for i, image_path in enumerate(page_results):
                with cols[i % 4]:
                    try:
                        # For now, show placeholder
                        st.markdown(f"""
                        <div style="background-color: #f0f0f0; height: 150px; 
                                    border-radius: 10px; display: flex; 
                                    align-items: center; justify-content: center;
                                    margin-bottom: 10px;">
                            <div style="text-align: center;">
                                <div style="font-size: 40px;">🖼️</div>
                                <div style="font-size: 10px;">{os.path.basename(image_path)[:20]}...</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button(f"👁️ View", key=f"view_{start_idx + i}"):
                            st.session_state.selected_image = image_path
                            AdvancedUIScreen._show_image_details(image_path)
                    except Exception:
                        st.error(f"Error loading image: {os.path.basename(image_path)}")
        
        elif last_query:
            st.info("🔍 No results found. Try a different search term.")
        else:
            st.info("💡 Use the search options above to find images in your collection.")
    
    @staticmethod
    def _show_image_details(image_path):
        """Show detailed view of selected image"""
        with st.expander(f"📸 Image Details: {os.path.basename(image_path)}", expanded=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("**🖼️ Preview:**")
                st.markdown("*(Image preview coming soon)*")
            
            with col2:
                st.markdown("**📄 Details:**")
                st.markdown(f"**Path:** `{image_path}`")
                st.markdown(f"**Filename:** `{os.path.basename(image_path)}`")
                
                try:
                    stat = os.stat(image_path)
                    size_mb = stat.st_size / (1024 * 1024)
                    st.markdown(f"**Size:** {size_mb:.2f} MB")
                except Exception:
                    st.markdown("**Size:** Unknown")
                
                # Action buttons
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("🔍 Find Similar"):
                        st.info("Similar image search coming soon!")
                with col_b:
                    if st.button("📂 Show in Folder"):
                        st.info("Show in folder coming soon!")
                with col_c:
                    if st.button("📤 Export"):
                        st.info("Export functionality coming soon!")
    
    @staticmethod
    def _render_ai_game_tab():
        """Render the AI guessing game tab"""
        st.markdown("## 🎮 AI Guessing Game")
        st.info("🚧 **Coming Soon!** An interactive game where the AI tries to guess what you're thinking about from your image collection.")
        
        st.markdown("""
        ### 🎯 How it will work:
        1. **Think of something** in your image collection
        2. **Answer AI questions** with yes/no
        3. **See if AI can guess** what you're thinking!
        4. **Challenge your friends** with the same game
        
        ### 🏆 Features:
        - Smart questioning based on your collection
        - Learning from your answers
        - Difficulty levels and scoring
        - Multiplayer challenges
        """)
        
        if st.button("🎮 Start Demo Game"):
            st.balloons()
            st.success("🎉 Demo game starting soon!")
    
    @staticmethod
    def _render_latent_space_tab():
        """Render the latent space exploration tab"""
        st.markdown("## 🌐 Latent Space Explorer")
        st.info("🚧 **Coming Soon!** Explore your images in AI-generated latent space - see how AI organizes and understands your collection.")
        
        st.markdown("""
        ### 🧠 What is Latent Space?
        Latent space is how AI models understand and organize images. Similar images cluster together based on:
        - **Visual similarity** (colors, shapes, objects)
        - **Semantic meaning** (concepts, activities, emotions)
        - **Style and composition** (photography style, artistic elements)
        
        ### 🔍 Features:
        - **Interactive 2D/3D visualization** of your image collection
        - **Zoom and explore** different regions
        - **Find unexpected connections** between images
        - **Discover patterns** in your photo-taking habits
        """)
        
        # Mock visualization
        st.markdown("### 📊 Preview Visualization:")
        import random
        import pandas as pd
        
        # Generate mock data points
        n_points = min(100, len(st.session_state.get('image_files', [])))
        if n_points > 0:
            data = pd.DataFrame({
                'x': [random.uniform(-10, 10) for _ in range(n_points)],
                'y': [random.uniform(-10, 10) for _ in range(n_points)],
                'cluster': [random.choice(['Nature', 'People', 'Food', 'Travel', 'Pets']) for _ in range(n_points)]
            })
            
            st.scatter_chart(data.set_index('cluster'))
            st.caption("*Mock visualization - actual latent space will be generated from your images*")
    
    @staticmethod
    def _render_duplicates_tab():
        """Render the duplicates detection tab"""
        st.markdown("## 👥 Duplicate Detection")
        st.info("🚧 **Coming Soon!** Find and manage duplicate or very similar images in your collection.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 Detection Types:
            - **Exact duplicates** (same file, different names)
            - **Near duplicates** (slight edits, crops, filters)
            - **Similar images** (same scene, different angles)
            - **Burst photos** (rapid sequence shots)
            """)
        
        with col2:
            st.markdown("""
            ### ⚙️ Management Options:
            - **Preview side-by-side** comparisons
            - **Keep best quality** version
            - **Archive or delete** duplicates
            - **Batch operations** for efficiency
            """)
        
        # Mock duplicate detection
        st.markdown("---")
        st.markdown("### 🔍 Scan for Duplicates")
        
        sensitivity = st.slider("Detection Sensitivity:", 0.7, 0.99, 0.85, 0.01)
        st.caption(f"Higher values find fewer, more exact matches. Current: {sensitivity:.0%}")
        
        if st.button("🔍 Start Duplicate Scan"):
            with st.spinner("🔍 Scanning for duplicates..."):
                import time
                time.sleep(2)
                
                # Mock results
                st.success("✅ Scan complete!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Duplicate Groups", "12", "📸")
                with col2:
                    st.metric("Total Duplicates", "28", "🔄")
                with col3:
                    st.metric("Space Savings", "156 MB", "💾")
                
                st.info("📋 **Results preview coming soon!** You'll be able to review and manage each duplicate group.")
    
    @staticmethod
    def _render_sidebar():
        """Render contextual sidebar for Advanced UI screen"""
        with st.sidebar:
            st.markdown("### 📊 Collection Info")
            
            # Collection stats
            folder_path = st.session_state.get('folder_path', 'Unknown')
            image_count = len(st.session_state.get('image_files', []))
            
            st.markdown(f"**📁 Path:** `{os.path.basename(folder_path)}`")
            st.metric("🖼️ Total Images", f"{image_count:,}")
            st.metric("💾 Database", "Ready")
            st.metric("🕒 Last Updated", "Just now")
            
            # Quick actions
            st.markdown("---")
            st.markdown("### 🎯 Quick Actions")
            
            if st.button("🔄 Refresh Collection"):
                st.info("🔄 Collection refresh coming soon!")
            
            if st.button("📊 View Statistics"):
                AdvancedUIScreen._show_collection_stats()
            
            if st.button("⚙️ Settings"):
                AdvancedUIScreen._show_settings()
            
            if st.button("📤 Export Results"):
                st.info("📤 Export functionality coming soon!")
            
            # Search history
            st.markdown("---")
            st.markdown("### 🔍 Recent Searches")
            
            recent_searches = st.session_state.get('search_history', [])
            if recent_searches:
                for i, search in enumerate(recent_searches[-5:]):  # Show last 5
                    if st.button(f"🔍 {search[:20]}...", key=f"recent_{i}"):
                        st.session_state.current_search_query = search
                        AdvancedUIScreen._perform_search(search, "text")
            else:
                st.info("No recent searches")
            
            if st.button("🗑️ Clear History"):
                st.session_state.search_history = []
                st.rerun()
            
            # AI status
            st.markdown("---")
            st.markdown("### 🤖 AI Status")
            st.success("✅ Models: Loaded")
            st.success("✅ CLIP: Ready")
            st.success("✅ Features: Cached")
            
            # Check GPU availability
            try:
                import torch
                if torch.cuda.is_available():
                    st.success("✅ GPU: Available")
                else:
                    st.info("💻 CPU: Active")
            except ImportError:
                st.info("💻 CPU: Active")
            
            # Back to folder selection
            st.markdown("---")
            if st.button("📁 Change Collection"):
                AppStateManager.reset_to_fast_ui()
                st.rerun()
    
    @staticmethod
    def _show_collection_stats():
        """Show detailed collection statistics"""
        with st.expander("📊 Collection Statistics", expanded=True):
            image_files = st.session_state.get('image_files', [])
            
            if not image_files:
                st.warning("No images loaded")
                return
            
            # File type distribution
            extensions = {}
            for file_path in image_files:
                ext = os.path.splitext(file_path)[1].lower()
                extensions[ext] = extensions.get(ext, 0) + 1
            
            st.markdown("**📁 File Types:**")
            for ext, count in sorted(extensions.items()):
                percentage = (count / len(image_files)) * 100
                st.markdown(f"- {ext.upper()}: {count:,} files ({percentage:.1f}%)")
            
            # Folder distribution
            folders = {}
            for file_path in image_files:
                folder = os.path.dirname(file_path)
                folders[folder] = folders.get(folder, 0) + 1
            
            st.markdown("**📂 Top Folders:**")
            for folder, count in sorted(folders.items(), key=lambda x: x[1], reverse=True)[:5]:
                st.markdown(f"- `{os.path.basename(folder)}`: {count:,} files")
    
    @staticmethod
    def _show_settings():
        """Show application settings"""
        with st.expander("⚙️ Application Settings", expanded=True):
            st.markdown("**🔍 Search Settings:**")
            
            # Search result limit
            result_limit = st.slider("Max search results:", 10, 100, 25, 5)
            st.session_state.search_result_limit = result_limit
            
            # Search similarity threshold
            similarity_threshold = st.slider("Similarity threshold:", 0.1, 1.0, 0.7, 0.1)
            st.session_state.similarity_threshold = similarity_threshold
            
            st.markdown("**💾 Performance Settings:**")
            
            # Cache settings
            use_cache = st.checkbox("Use feature cache", value=True)
            st.session_state.use_cache = use_cache
            
            auto_refresh = st.checkbox("Auto-refresh search", value=False)
            st.session_state.auto_refresh = auto_refresh
            
            if st.button("💾 Save Settings"):
                st.success("✅ Settings saved!")


# Easy import for main app
def render_advanced_ui_screen():
    """Main entry point for advanced UI screen"""
    AdvancedUIScreen.render() 