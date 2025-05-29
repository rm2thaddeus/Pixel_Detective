# 🎨 Pixel Detective - Style Injector
# Sprint 02: Visual Design System Implementation
# Purpose: Helper to inject custom CSS into Streamlit apps

import streamlit as st
from pathlib import Path
import os


class StyleInjector:
    """Handles injection of custom CSS into Streamlit apps"""
    
    def __init__(self):
        # Get the styles directory path
        self.styles_dir = Path(__file__).parent
        
    def inject_styles(self, files=None):
        """
        Inject CSS files into the Streamlit app
        
        Args:
            files (list): List of CSS files to inject. If None, injects all core files.
        """
        if files is None:
            # Default CSS files in order of dependency
            files = [
                'main.css',          # Core design system first
                'components.css',    # Component styles
                'animations.css'     # Animations last
            ]
        
        combined_css = ""
        
        for css_file in files:
            css_path = self.styles_dir / css_file
            if css_path.exists():
                try:
                    with open(css_path, 'r', encoding='utf-8') as f:
                        css_content = f.read()
                        combined_css += f"\n/* ===== {css_file.upper()} ===== */\n"
                        combined_css += css_content + "\n"
                except Exception as e:
                    st.error(f"Error loading CSS file {css_file}: {e}")
            else:
                st.warning(f"CSS file not found: {css_file}")
        
        if combined_css:
            # Inject the combined CSS into the Streamlit app
            st.markdown(
                f"""
                <style>
                {combined_css}
                </style>
                """,
                unsafe_allow_html=True
            )
    
    def inject_single_file(self, filename):
        """Inject a single CSS file"""
        self.inject_styles([filename])
    
    def apply_theme_class(self, class_name="pd-app"):
        """Apply theme class to the main app container"""
        st.markdown(
            f"""
            <script>
            // Apply theme class to main container
            document.addEventListener('DOMContentLoaded', function() {{
                const mainContainer = document.querySelector('.main');
                if (mainContainer) {{
                    mainContainer.classList.add('{class_name}');
                }}
            }});
            </script>
            """,
            unsafe_allow_html=True
        )


# Global instance for easy importing
style_injector = StyleInjector()


def inject_pixel_detective_styles():
    """
    Quick function to inject all Pixel Detective styles
    Use this in your Streamlit screens
    """
    style_injector.inject_styles()
    style_injector.apply_theme_class()


def create_styled_container(content, container_class="pd-container"):
    """
    Create a styled container with custom CSS classes
    
    Args:
        content (str): HTML content to wrap
        container_class (str): CSS class for the container
    
    Returns:
        Streamlit markdown component with styled content
    """
    return st.markdown(
        f"""
        <div class="{container_class}">
            {content}
        </div>
        """,
        unsafe_allow_html=True
    )


def create_hero_section(title, subtitle, icon="🕵️‍♂️"):
    """
    Create a styled hero section
    
    Args:
        title (str): Main title
        subtitle (str): Subtitle text
        icon (str): Emoji or icon
    """
    hero_content = f"""
    <div class="pd-hero pd-fade-in">
        <div style="font-size: 3rem; margin-bottom: 1rem;">{icon}</div>
        <h1 class="pd-title" style="color: white; margin-bottom: 0.5rem;">{title}</h1>
        <p class="pd-subheading" style="color: rgba(255, 255, 255, 0.9); margin-bottom: 0;">{subtitle}</p>
    </div>
    """
    
    st.markdown(hero_content, unsafe_allow_html=True)


def create_feature_cards(features):
    """
    Create a grid of feature cards
    
    Args:
        features (list): List of dicts with 'icon', 'title', 'description'
    """
    if not features:
        return
    
    # Create columns based on number of features
    cols = st.columns(len(features))
    
    for i, feature in enumerate(features):
        with cols[i]:
            card_content = f"""
            <div class="pd-feature-card pd-stagger-item pd-hover-lift">
                <div class="pd-feature-card-icon">{feature.get('icon', '✨')}</div>
                <div class="pd-feature-card-title">{feature.get('title', 'Feature')}</div>
                <div class="pd-feature-card-description">{feature.get('description', 'Description')}</div>
            </div>
            """
            st.markdown(card_content, unsafe_allow_html=True)


def create_styled_button(text, button_type="primary", size="", icon="", onclick_class=""):
    """
    Create a styled button with custom CSS
    
    Args:
        text (str): Button text
        button_type (str): Button variant (primary, secondary, success, outline, ghost)
        size (str): Button size (sm, lg, xl)
        icon (str): Icon to include
        onclick_class (str): Additional class for click animations
    
    Returns:
        HTML string for the button
    """
    size_class = f"pd-btn-{size}" if size else ""
    icon_class = "pd-btn-icon" if icon else ""
    click_class = onclick_class if onclick_class else "pd-btn-press"
    
    icon_html = f'<span style="margin-right: 0.5rem;">{icon}</span>' if icon else ""
    
    button_html = f"""
    <button class="pd-btn pd-btn-{button_type} {size_class} {icon_class} {click_class} pd-hover-lift">
        {icon_html}{text}
    </button>
    """
    
    return button_html


def create_progress_bar(percentage, animated=True, show_percentage=False):
    """
    Create a styled progress bar
    
    Args:
        percentage (int): Progress percentage (0-100)
        animated (bool): Whether to show animation
        show_percentage (bool): Whether to show percentage text
    """
    animation_class = "pd-wave" if animated else ""
    
    progress_html = f"""
    <div class="pd-progress {animation_class}">
        <div class="pd-progress-bar" style="width: {percentage}%;"></div>
    </div>
    """
    
    if show_percentage:
        progress_html += f"""
        <div style="text-align: center; margin-top: 0.5rem; font-size: 0.875rem; color: var(--pd-text-secondary);">
            {percentage}%
        </div>
        """
    
    st.markdown(progress_html, unsafe_allow_html=True)


def create_status_indicator(status, text, with_dot=True):
    """
    Create a status indicator
    
    Args:
        status (str): Status type (success, warning, info)
        text (str): Status text
        with_dot (bool): Whether to show status dot
    """
    dot_html = '<div class="pd-status-dot"></div>' if with_dot else ""
    
    status_html = f"""
    <div class="pd-status pd-status-{status}">
        {dot_html}
        <span>{text}</span>
    </div>
    """
    
    st.markdown(status_html, unsafe_allow_html=True)


def create_loading_spinner(text="Loading...", spinner_type="spinner"):
    """
    Create a loading spinner with text
    
    Args:
        text (str): Loading text
        spinner_type (str): Type of spinner (spinner, dots, bounce)
    """
    if spinner_type == "spinner":
        spinner_html = '<div class="pd-spinner"></div>'
    elif spinner_type == "dots":
        spinner_html = '''
        <div class="pd-loading-dots">
            <div class="pd-loading-dot"></div>
            <div class="pd-loading-dot"></div>
            <div class="pd-loading-dot"></div>
        </div>
        '''
    elif spinner_type == "bounce":
        spinner_html = '''
        <div class="pd-bounce-loader">
            <div class="pd-bounce-dot"></div>
            <div class="pd-bounce-dot"></div>
            <div class="pd-bounce-dot"></div>
        </div>
        '''
    else:
        spinner_html = '<div class="pd-spinner"></div>'
    
    loading_html = f"""
    <div style="display: flex; align-items: center; gap: 1rem; justify-content: center; padding: 2rem;">
        {spinner_html}
        <span style="color: var(--pd-text-secondary);">{text}</span>
    </div>
    """
    
    st.markdown(loading_html, unsafe_allow_html=True)


# Example usage functions for testing
def demo_style_components():
    """Demo function to show all styled components"""
    inject_pixel_detective_styles()
    
    # Hero section
    create_hero_section(
        "Pixel Detective", 
        "Lightning-fast AI image search", 
        "🕵️‍♂️"
    )
    
    # Feature cards
    features = [
        {
            "icon": "🔍",
            "title": "Smart Search",
            "description": "Find images using natural language descriptions"
        },
        {
            "icon": "🖼️",
            "title": "Visual Similarity",
            "description": "Upload any photo to find similar images"
        },
        {
            "icon": "🎮",
            "title": "AI Games",
            "description": "Let AI guess your photos in fun games"
        }
    ]
    
    create_feature_cards(features)
    
    # Progress bar
    st.markdown("### Progress Example")
    create_progress_bar(75, animated=True, show_percentage=True)
    
    # Status indicators
    st.markdown("### Status Examples")
    col1, col2, col3 = st.columns(3)
    with col1:
        create_status_indicator("success", "Ready", True)
    with col2:
        create_status_indicator("warning", "Processing", True)
    with col3:
        create_status_indicator("info", "Loading", True)


if __name__ == "__main__":
    # Run demo if this file is executed directly
    demo_style_components() 