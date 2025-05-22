# 📂 File Path: /project_root/.cursor/cursor_rules.md
# 📌 Purpose: Project rules for the Pixel Detective application.
# 🔄 Latest Changes: Created Cursor Project Rules for UI configuration.
# ⚙️ Key Logic: Guidelines for maintaining the UI styling of the application.
# 🧠 Reasoning: Ensures consistent styling and behavior across the codebase.

# Pixel Detective Project Rules

## UI Configuration Rules

### Dark Mode Configuration

1. **Use Streamlit's Built-in Dark Mode**: 
   - Always use Streamlit's default dark mode theme by setting `base = "dark"` in `.streamlit/config.toml`.
   - Avoid custom color overrides unless absolutely necessary.
   - If custom colors are needed, document them clearly in comments.

2. **Minimal Custom CSS**:
   - Keep the `.streamlit/custom.css` file minimal and focused only on essential styling.
   - Custom CSS should primarily focus on the sidebar and image display components.
   - Document any custom CSS with clear comments explaining its purpose.

3. **Theme Consistency**:
   - All UI components should respect the dark mode theme.
   - Text should be light-colored on dark backgrounds, with sufficient contrast.
   - Interactive elements should have hover states that are visible in dark mode.

### Extendable Sidebar for Images

1. **Sidebar Structure**:
   - The sidebar should be designed to be extendable to accommodate varying amounts of content.
   - Image containers in the sidebar should use the `.stImage` CSS class for consistent styling.
   - Always set `initial_sidebar_state="expanded"` in `st.set_page_config()`.

2. **Image Display**:
   - Images displayed in the sidebar should be responsive and properly sized.
   - Implement fallback mechanisms for images that fail to load.
   - Ensure images have proper alt text and metadata for accessibility.

3. **Sidebar Interactivity**:
   - Sidebar components should have clear interactive states (hover, focus, active).
   - Clickable elements should have appropriate cursor styling.
   - Expand/collapse states should be clearly indicated to users.

## Implementation Guidelines

1. **Sidebar Implementation**:
   - Keep the sidebar code in `ui/sidebar.py` to maintain separation of concerns.
   - The `render_sidebar()` function should return any configuration needed by the main interface.
   - Import the sidebar into the main interface rather than duplicating code.

2. **CSS Loading**:
   - Load CSS using the `load_custom_css()` function in `app.py`.
   - Ensure CSS is loaded after page configuration but before any UI components.
   - Handle file not found errors gracefully.

3. **UI Component Relationships**:
   - Maintain clear relationships between the sidebar and main content.
   - Use session state to pass information between components.
   - Ensure consistent styling across all components.

## Testing UI Changes

1. **Dark Mode Testing**:
   - Test all UI changes in dark mode to ensure proper visibility and contrast.
   - Check text readability against all background colors.
   - Verify that all interactive elements are clearly visible.

2. **Sidebar Testing**:
   - Test sidebar with both minimal and extensive content to ensure proper expansion.
   - Verify that the sidebar scrolls correctly when content exceeds the viewport.
   - Test image loading in the sidebar with various image sizes and formats.

3. **Cross-Browser Compatibility**:
   - Test UI changes in multiple browsers to ensure consistent behavior.
   - Address any browser-specific CSS issues with appropriate fallbacks. 