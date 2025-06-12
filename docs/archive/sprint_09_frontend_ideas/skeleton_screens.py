# 💀 Skeleton Screens Component for Enhanced Loading States
# 📌 Purpose: Provide visual feedback during loading processes with skeleton UI
# 🎯 Sprint 02 Final 25%: Enhanced loading state with skeleton screens
# 🎨 Design System: Consistent with Pixel Detective gradient theme

import streamlit as st


class SkeletonScreens:
    """Skeleton screen components for enhanced loading states"""
    
    @staticmethod
    def inject_skeleton_styles():
        """Inject CSS for skeleton animations and components"""
        st.markdown("""
        <style>
        /* Skeleton Animation */
        @keyframes skeleton-loading {
            0% {
                background-position: -200px 0;
            }
            100% {
                background-position: calc(200px + 100%) 0;
            }
        }
        
        .skeleton {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200px 100%;
            animation: skeleton-loading 1.5s infinite;
            border-radius: 8px;
        }
        
        .skeleton-dark {
            background: linear-gradient(90deg, rgba(255,255,255,0.1) 25%, rgba(255,255,255,0.2) 50%, rgba(255,255,255,0.1) 75%);
            background-size: 200px 100%;
            animation: skeleton-loading 1.5s infinite;
            border-radius: 8px;
        }
        
        .skeleton-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .skeleton-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        
        .skeleton-item {
            height: 120px;
            border-radius: 8px;
        }
        
        .skeleton-text {
            height: 1rem;
            margin: 0.5rem 0;
            border-radius: 4px;
        }
        
        .skeleton-text-lg {
            height: 1.5rem;
            margin: 0.75rem 0;
            border-radius: 6px;
        }
        
        .skeleton-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            margin: 0 auto 1rem;
        }
        
        .skeleton-progress {
            height: 8px;
            border-radius: 4px;
            margin: 1rem 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_folder_scan_skeleton():
        """Skeleton screen for folder scanning phase"""
        st.markdown("""
        <div class="skeleton-card">
            <div class="skeleton-avatar skeleton-dark"></div>
            <div class="skeleton-text-lg skeleton-dark" style="width: 60%; margin: 0 auto;"></div>
            <div class="skeleton-text skeleton-dark" style="width: 80%; margin: 0.5rem auto;"></div>
            
            <div class="skeleton-grid">
                <div class="skeleton-item skeleton-dark"></div>
                <div class="skeleton-item skeleton-dark"></div>
                <div class="skeleton-item skeleton-dark"></div>
                <div class="skeleton-item skeleton-dark"></div>
                <div class="skeleton-item skeleton-dark"></div>
                <div class="skeleton-item skeleton-dark"></div>
            </div>
            
            <div class="skeleton-progress skeleton-dark"></div>
            <div class="skeleton-text skeleton-dark" style="width: 40%; margin: 0.5rem auto;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_model_loading_skeleton():
        """Skeleton screen for AI model loading phase"""
        st.markdown("""
        <div class="skeleton-card">
            <div class="skeleton-avatar skeleton-dark"></div>
            <div class="skeleton-text-lg skeleton-dark" style="width: 70%; margin: 0 auto;"></div>
            <div class="skeleton-text skeleton-dark" style="width: 90%; margin: 0.5rem auto;"></div>
            
            <div style="display: flex; gap: 1rem; margin: 2rem 0;">
                <div style="flex: 1;">
                    <div class="skeleton-text skeleton-dark" style="width: 80%;"></div>
                    <div class="skeleton-progress skeleton-dark"></div>
                    <div class="skeleton-text skeleton-dark" style="width: 60%;"></div>
                </div>
                <div style="flex: 1;">
                    <div class="skeleton-text skeleton-dark" style="width: 75%;"></div>
                    <div class="skeleton-progress skeleton-dark"></div>
                    <div class="skeleton-text skeleton-dark" style="width: 55%;"></div>
                </div>
            </div>
            
            <div class="skeleton-text skeleton-dark" style="width: 50%; margin: 1rem auto;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_database_building_skeleton():
        """Skeleton screen for database building phase"""
        st.markdown("""
        <div class="skeleton-card">
            <div class="skeleton-avatar skeleton-dark"></div>
            <div class="skeleton-text-lg skeleton-dark" style="width: 75%; margin: 0 auto;"></div>
            <div class="skeleton-text skeleton-dark" style="width: 85%; margin: 0.5rem auto;"></div>
            
            <div style="margin: 2rem 0;">
                <div class="skeleton-text skeleton-dark" style="width: 30%; margin-bottom: 0.5rem;"></div>
                <div class="skeleton-progress skeleton-dark"></div>
                
                <div class="skeleton-text skeleton-dark" style="width: 40%; margin: 1rem 0 0.5rem;"></div>
                <div class="skeleton-progress skeleton-dark"></div>
                
                <div class="skeleton-text skeleton-dark" style="width: 35%; margin: 1rem 0 0.5rem;"></div>
                <div class="skeleton-progress skeleton-dark"></div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin: 2rem 0;">
                <div>
                    <div class="skeleton-text skeleton-dark" style="width: 80%;"></div>
                    <div class="skeleton-text-lg skeleton-dark" style="width: 60%;"></div>
                </div>
                <div>
                    <div class="skeleton-text skeleton-dark" style="width: 75%;"></div>
                    <div class="skeleton-text-lg skeleton-dark" style="width: 65%;"></div>
                </div>
                <div>
                    <div class="skeleton-text skeleton-dark" style="width: 85%;"></div>
                    <div class="skeleton-text-lg skeleton-dark" style="width: 55%;"></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_search_interface_skeleton():
        """Skeleton screen for search interface preparation"""
        st.markdown("""
        <div class="skeleton-card">
            <div class="skeleton-text-lg skeleton-dark" style="width: 60%; margin: 0 auto 2rem;"></div>
            
            <!-- Search bar skeleton -->
            <div style="margin: 2rem 0;">
                <div class="skeleton-text-lg skeleton-dark" style="height: 3rem; border-radius: 25px;"></div>
            </div>
            
            <!-- Filter options skeleton -->
            <div style="display: flex; gap: 1rem; margin: 1rem 0;">
                <div class="skeleton-text skeleton-dark" style="width: 100px; height: 2rem;"></div>
                <div class="skeleton-text skeleton-dark" style="width: 120px; height: 2rem;"></div>
                <div class="skeleton-text skeleton-dark" style="width: 80px; height: 2rem;"></div>
                <div class="skeleton-text skeleton-dark" style="width: 90px; height: 2rem;"></div>
            </div>
            
            <!-- Results grid skeleton -->
            <div class="skeleton-grid">
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
                <div class="skeleton-item skeleton-dark" style="height: 150px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def render_contextual_skeleton(phase_name, description):
        """Render a contextual skeleton based on the current loading phase"""
        if "folder" in phase_name.lower() or "scan" in phase_name.lower():
            SkeletonScreens.render_folder_scan_skeleton()
        elif "model" in phase_name.lower() or "ai" in phase_name.lower():
            SkeletonScreens.render_model_loading_skeleton()
        elif "database" in phase_name.lower() or "build" in phase_name.lower():
            SkeletonScreens.render_database_building_skeleton()
        elif "search" in phase_name.lower() or "interface" in phase_name.lower():
            SkeletonScreens.render_search_interface_skeleton()
        else:
            # Default skeleton
            SkeletonScreens.render_database_building_skeleton() 