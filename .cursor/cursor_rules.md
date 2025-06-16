# 📂 File Path: /project_root/.cursor/cursor_rules.md
# 📌 Purpose: Project rules for the Pixel Detective application.
# 🔄 Latest Changes: Added comprehensive MCP integration and sprint planning workflows.
# ⚙️ Key Logic: Guidelines for maintaining the UI styling and development workflows.
# 🧠 Reasoning: Ensures consistent styling, behavior, and sprint planning across the codebase.

# Pixel Detective Project Rules - Next.js/FastAPI Architecture

## 🚨 CRITICAL: Sprint 10 Lessons Integration

This project follows comprehensive rules based on Sprint 10 debugging experiences. **ALWAYS consult nested rules before starting work.**

### 📁 Rule Structure Overview

```
.cursor/rules/                    # Project-wide rules
├── sprint-lessons-learned.mdc    # 🔥 MASTER reference - Sprint 10 failures
├── mcp-browser-tools-setup.mdc   # 3-component MCP setup protocol
├── sprint-planning.mdc           # Sprint workflow and planning
├── use-mcp-servers.mdc          # MCP server integration patterns
├── debugging.mdc                # General debugging protocols
└── [other project rules...]

frontend/.cursor/rules/           # Frontend-specific rules
├── nextjs-hydration-prevention.mdc  # Hydration error prevention (critical)
└── react-query-api-integration.mdc  # Server state management patterns

backend/.cursor/rules/            # Backend-specific rules
└── fastapi-dependency-injection.mdc # Circular import prevention
```

### 🎯 MANDATORY PRE-WORK PROTOCOL

**Before ANY development work, check these rules in order:**

1. **Sprint Context**: Review `.cursor/rules/sprint-lessons-learned.mdc` for applicable lessons
2. **Frontend Work**: Check `frontend/.cursor/rules/` for Next.js/React patterns
3. **Backend Work**: Check `backend/.cursor/rules/` for FastAPI patterns
4. **MCP Usage**: Verify setup with `.cursor/rules/mcp-browser-tools-setup.mdc`

## 🔥 Critical Technical Patterns (From Sprint 10)

### Next.js Hydration Prevention
```tsx
// ✅ ALWAYS use mounted state for client-only features
const [mounted, setMounted] = useState(false);
useEffect(() => setMounted(true), []);
if (!mounted) return <PlaceholderComponent />;
```

### FastAPI Dependency Injection
```python
# ✅ ALWAYS use dependencies.py, NEVER import main.py in routers
from ..dependencies import get_qdrant_client
def endpoint(client: QdrantClient = Depends(get_qdrant_client)):
```

### React Query for Server State
```tsx
// ✅ ALWAYS use React Query, NEVER manual useEffect for API calls
const { data, isLoading, error } = useQuery({
  queryKey: ['collections'],
  queryFn: () => api.get('/api/v1/collections')
});
```

## 🚀 MCP-Driven Development Workflow

### Before Using Any MCP Tools
1. **Verify Setup**: Follow `.cursor/rules/mcp-browser-tools-setup.mdc` verification protocol
2. **Node.js Check**: `node --version` must show ≥18.0.0
3. **Server Check**: Browser Tools server running on port 3025
4. **Extension Check**: Chrome extension installed and connected

### Sprint Planning Integration
1. **Context7 Research**: Use Context7 MCP for technology research
2. **Documentation**: Follow `.cursor/rules/sprint-planning.mdc` for PRD generation
3. **GitHub Integration**: Use GitHub MCP for milestone management
4. **Visual Planning**: Use Mindmap MCP for architecture planning

## 🧪 Testing & Quality Assurance

### Frontend Testing Protocol
- [ ] **Hydration Check**: `npm run build && npm start` - no console errors
- [ ] **Theme Testing**: Both light/dark modes work without flash
- [ ] **Client-Only**: All browser API usage wrapped in mounted state
- [ ] **Query Integration**: All server state uses React Query

### Backend Testing Protocol
- [ ] **Import Check**: No circular imports detected
- [ ] **Dependency Injection**: All shared resources use `Depends()`
- [ ] **Startup Clean**: uvicorn starts without errors
- [ ] **Type Safety**: All dependencies properly typed

### MCP Testing Protocol
- [ ] **3-Component Verification**: Node.js ≥18, server on 3025, extension installed
- [ ] **Basic Connectivity**: `mcp_browser-tools_wipeLogs` succeeds
- [ ] **Full Functionality**: Screenshot capture works
- [ ] **Fallback Strategy**: Manual debugging available if MCP fails

## 📊 Emergency Recovery Protocols

### Hydration Error Recovery
```bash
1. rm -rf .next && npm run dev
2. Check browser console for specific mismatch
3. Apply mounted state pattern to problematic component
4. Last resort: Dynamic import with ssr: false
```

### Backend Circular Import Recovery
```bash
1. python -m py_compile main.py
2. Verify dependencies.py exists and is importable
3. Check lifespan function is properly async
4. Use dependency injection everywhere
```

### MCP Connection Failure Recovery
```bash
1. node --version ≥18
2. curl localhost:3025/health
3. Reinstall Chrome extension
4. Check DevTools "BrowserTools" tab
```

## 🎯 Success Metrics

- **Zero hydration errors** in console during development
- **Clean backend startup** without circular import warnings
- **First-try MCP success** rate >90%
- **All server state** managed by React Query
- **All point IDs** are valid UUIDs (not SHA256 hashes)

---

**⚡ Quick Reference Links:**
- **🧭 Rule Navigation**: `.cursor/rules/cross-reference-guide.mdc` (START HERE for navigation)
- **🚨 Emergency Issues**: `.cursor/rules/quick-troubleshooting-index.mdc` (30-sec fixes)
- **🔥 Sprint 10 Failures**: `.cursor/rules/sprint-lessons-learned.mdc` (master reference)
- **🧪 Testing Patterns**: `.cursor/rules/sprint10-testing-patterns.mdc` (prevention)
- **📋 Frontend Development**: `frontend/.cursor/rules/frontend-development-index.mdc` (START HERE for frontend work)
- **💧 Hydration Prevention**: `frontend/.cursor/rules/nextjs-hydration-prevention.mdc`
- **🔄 API Integration**: `frontend/.cursor/rules/react-query-api-integration.mdc`
- **🏗️ Component Architecture**: `frontend/.cursor/rules/component-architecture-patterns.mdc` (component design patterns)
- **🎨 UX Workflows**: `frontend/.cursor/rules/ux-workflow-patterns.mdc` (user experience patterns)
- **⚡ Performance**: `frontend/.cursor/rules/nextjs-performance-optimization.mdc` (Next.js optimization)
- **📋 Backend Development**: `backend/.cursor/rules/backend-development-index.mdc` (START HERE for backend work)
- **🔗 Backend Architecture**: `backend/.cursor/rules/fastapi-dependency-injection.mdc`
- **🏗️ Service Patterns**: `backend/.cursor/rules/fastapi-microservice-patterns.mdc` (comprehensive FastAPI patterns)
- **🤖 ML Integration**: `backend/.cursor/rules/ml-service-integration.mdc` (GPU-optimized ML services)
- **🔌 API Design**: `backend/.cursor/rules/api-design-patterns.mdc` (RESTful design patterns)
- **🔧 MCP Setup**: `.cursor/rules/mcp-browser-tools-setup.mdc`

*This architecture prevents the Sprint 10 failures that cost days of debugging time. Follow religiously.*

## 🤖 **Universal Auto-Activation System**

### **Mandatory Rule Auto-Application**
- **PowerShell Syntax**: Auto-applied for ALL Windows terminal commands (prevents && errors)
- **Sprint Lessons**: Auto-applied for ALL development work (prevents known failures)
- **MCP Setup**: Auto-applied for ALL frontend work (ensures tools work)
- **Configuration**: See `.cursor/rules/auto-activation-config.mdc` for details

### **AI Assistant Integration**
All AI assistants automatically:
1. **Detect environment** (Windows → PowerShell protection mandatory)
2. **Apply prevention rules** BEFORE generating any commands
3. **Integrate seamlessly** with context-specific rules
4. **Provide bulletproof results** without user intervention

# Pixel Detective Project Rules

## MCP Integration & Sprint Planning

### MCP-Driven Development Workflow

1. **Sprint Planning Integration**:
   - Follow sprint planning workflow defined in `.cursor/rules/sprint-planning.mdc`
   - Use Context7 MCP for technology research during sprint planning
   - Use Mindmap MCP for visual requirement and architecture planning
   - Generate PRDs using the integrated workflow before starting development

2. **Technology Research Protocol**:
   - Always use Context7 MCP to research implementation patterns before coding
   - Document Context7 findings in `/docs/sprints/sprint-{number}/research/`
   - Reference Context7 documentation in code comments and PRD sections

3. **Visual Planning Requirements**:
   - Use Mindmap MCP for complex feature architecture before implementation
   - Create sprint overview and feature architecture mindmaps
   - Convert mindmaps to structured documentation in PRDs

4. **GitHub Integration Standards**:
   - All sprint work must reference PRD sections in commit messages
   - Use GitHub MCP for milestone and issue management during sprints
   - Follow conventional commit messages with sprint/PRD references

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

4. **MCP-Driven Testing**:
   - Use Browser Tools MCP for automated audits after UI changes
   - Capture screenshots using Browser Tools MCP for visual regression testing
   - Run performance audits using Browser Tools MCP after significant changes

## Sprint Integration Guidelines

### When Starting New Features
1. Check if feature is part of current sprint PRD
2. Reference PRD section in feature branch names and commit messages
3. Follow Context7 implementation patterns documented in sprint research
4. Update PRD with implementation progress and any deviations

### Daily Development Workflow
1. Reference sprint planning rules from `.cursor/rules/sprint-planning.mdc`
2. Use MCP server guidelines from `.cursor/rules/use-mcp-servers.mdc`
3. Follow debugging protocols from `.cursor/rules/debugging.mdc`
4. Adhere to feature implementation standards from `.cursor/rules/feature-request.mdc`

### Sprint Documentation
- Update sprint PRD with completion status
- Document any architectural decisions using Mindmap MCP
- Archive sprint artifacts in `/docs/sprints/sprint-{number}/`
- Use GitHub MCP to update project milestones and close completed issues

---

**Related Rules:**
- **Sprint Planning:** `.cursor/rules/sprint-planning.mdc`
- **MCP Server Usage:** `.cursor/rules/use-mcp-servers.mdc`  
- **Feature Development:** `.cursor/rules/feature-request.mdc`
- **Debugging:** `.cursor/rules/debugging.mdc`
- **Documentation:** `.cursor/rules/commentsoverwrite.mdc`

*This rule set ensures consistent UI development integrated with comprehensive sprint planning and MCP-driven workflows.* 