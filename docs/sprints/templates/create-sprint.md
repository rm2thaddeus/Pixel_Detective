# Sprint Setup Quick Start Guide

This guide helps you quickly set up a new sprint using the MCP-driven workflow defined in `.cursor/rules/sprint-planning.mdc`.

## Prerequisites

Ensure you have access to these MCP servers:
- ✅ **GitHub MCP** - For repository and issue management
- ✅ **Context7 MCP** - For technology research and documentation
- ✅ **Mindmap MCP** - For visual planning and architecture
- ✅ **Browser Tools MCP** - For testing and validation

## Sprint Setup Checklist

### Phase 1: Initial Setup (30 minutes)

#### 1. Create Sprint Directory Structure
```bash
# Replace {sprint-number} with actual sprint number (e.g., 01, 02, etc.)
mkdir -p docs/sprints/sprint-{sprint-number}/{planning,execution,review}
mkdir -p docs/sprints/sprint-{sprint-number}/research
mkdir -p docs/sprints/sprint-{sprint-number}/mindmaps
```

#### 2. Initialize Sprint Documents
```bash
# Copy PRD template
cp docs/sprints/templates/PRD-template.md docs/sprints/sprint-{sprint-number}/PRD.md

# Create additional planning documents
touch docs/sprints/sprint-{sprint-number}/requirements.md
touch docs/sprints/sprint-{sprint-number}/tech-stack.md
touch docs/sprints/sprint-{sprint-number}/research/context7-findings.md
```

#### 3. GitHub Sprint Setup
Use GitHub MCP to create sprint infrastructure:

**Create Sprint Milestone:**
```
Use: mcp_github_create_milestone
- title: "Sprint {number}: {sprint-name}"
- description: "Sprint objectives and deliverables"
- due_date: {sprint-end-date}
```

**Create Epic Issue:**
```
Use: mcp_github_create_issue  
- title: "Epic: {sprint-name}"
- body: "Sprint epic covering all user stories and technical tasks"
- labels: ["epic", "sprint-{number}"]
- milestone: {sprint-milestone-id}
```

### Phase 2: Requirements Research (60 minutes)

#### 4. Context7 Technology Research
Research key technologies and patterns:

**Framework Research:**
```
Use: mcp_context7_resolve-library-id
- libraryName: "{primary-framework}" (e.g., "streamlit", "fastapi", "react")

Use: mcp_context7_get-library-docs  
- context7CompatibleLibraryID: "{resolved-id}"
- topic: "{specific-topic}" (e.g., "components", "authentication", "testing")
```

**Database Research:**
```
Use: mcp_context7_resolve-library-id
- libraryName: "{database-tech}" (e.g., "supabase", "postgresql")

Use: mcp_context7_get-library-docs
- context7CompatibleLibraryID: "{resolved-id}"  
- topic: "{database-pattern}" (e.g., "migrations", "security", "performance")
```

**Testing Framework Research:**
```
Use: mcp_context7_resolve-library-id
- libraryName: "{testing-framework}" (e.g., "pytest", "jest", "playwright")

Use: mcp_context7_get-library-docs
- context7CompatibleLibraryID: "{resolved-id}"
- topic: "best-practices"
```

#### 5. Document Research Findings
Create `/docs/sprints/sprint-{number}/research/context7-findings.md`:

```markdown
# Context7 Research Findings - Sprint {number}

## Framework Analysis: {framework-name}
- **Documentation Source:** {context7-id}
- **Key Patterns:** {patterns-discovered}
- **Best Practices:** {practices-to-follow}
- **Implementation Notes:** {specific-guidance}

## Database Patterns: {database-tech}
- **Documentation Source:** {context7-id}
- **Schema Patterns:** {patterns-discovered}
- **Security Guidelines:** {security-notes}
- **Performance Tips:** {performance-guidance}

## Testing Strategy: {testing-framework}
- **Documentation Source:** {context7-id}
- **Testing Patterns:** {patterns-discovered}
- **Coverage Guidelines:** {coverage-requirements}
- **Integration Testing:** {integration-approach}
```

### Phase 3: Visual Planning with Mindmap MCP (45 minutes)

#### 6. Create Sprint Planning Mindmap
Use Mindmap MCP to create visual representations:

**Sprint Overview Mindmap:**
```
Sprint {Number} - {Name}
├── 🎯 Objectives
│   ├── Primary Goal: {main-objective}
│   ├── Secondary Goals: {supporting-objectives}
│   └── Success Metrics: {measurable-outcomes}
├── 📋 Requirements  
│   ├── Functional: {user-facing-features}
│   ├── Non-Functional: {performance-security-usability}
│   └── Technical: {architecture-constraints}
├── 🏗️ Architecture
│   ├── Frontend: {ui-components-and-flows}
│   ├── Backend: {apis-and-services}  
│   ├── Database: {schema-and-data-flows}
│   └── Integrations: {external-apis-and-services}
├── 🧪 Testing
│   ├── Unit Tests: {component-testing-strategy}
│   ├── Integration: {service-integration-testing}
│   └── E2E: {user-journey-testing}
└── 🚀 Delivery
    ├── Milestones: {weekly-deliverables}
    ├── Dependencies: {blocking-and-supporting-tasks}
    └── Risks: {potential-issues-and-mitigations}
```

**Feature Architecture Mindmap:**
```
Feature: {Feature-Name}
├── 📱 User Interface
│   ├── Components: {ui-components-needed}
│   ├── User Flow: {step-by-step-interaction}
│   └── Design System: {styling-and-theming}
├── ⚙️ Backend Logic
│   ├── APIs: {endpoints-and-methods}
│   ├── Business Logic: {core-functionality}
│   └── Data Processing: {transformations-and-validations}
├── 🗄️ Data Layer
│   ├── Schema: {database-tables-and-relationships}
│   ├── Queries: {data-access-patterns}
│   └── Migrations: {schema-change-strategy}
└── 🔗 Integrations
    ├── External APIs: {third-party-services}
    ├── Internal Services: {microservice-communications}
    └── Authentication: {security-and-permissions}
```

#### 7. Save Mindmap Files
Save mindmap outputs in:
- `/docs/sprints/sprint-{number}/mindmaps/sprint-overview.md`
- `/docs/sprints/sprint-{number}/mindmaps/feature-architecture.md`

### Phase 4: PRD Generation (45 minutes)

#### 8. Fill PRD Template
Using the mindmap and Context7 research, populate the PRD template:

1. **Executive Summary** - Extract from sprint overview mindmap
2. **Context7 Research Summary** - Copy from research findings
3. **Requirements Matrix** - Convert mindmap requirements to table format
4. **Technical Architecture** - Use architecture section from mindmap
5. **Implementation Timeline** - Break down milestones from mindmap
6. **Testing Strategy** - Reference Context7 testing framework research
7. **Risk Assessment** - Extract risks from mindmap

#### 9. Create User Stories
Based on the functional requirements in the PRD, create GitHub issues:

```
Use: mcp_github_create_issue for each user story
- title: "Story: As a {user}, I want {functionality} so that {benefit}"
- body: "
  **Acceptance Criteria:**
  - [ ] {criterion-1}
  - [ ] {criterion-2}
  
  **PRD Reference:** Section {x.y.z}
  **Context7 Implementation Guide:** {relevant-docs}
  "
- labels: ["story", "sprint-{number}"]
- milestone: {sprint-milestone-id}
```

### Phase 5: Sprint Kickoff (30 minutes)

#### 10. Team Review
- Review completed PRD with team
- Assign user stories to team members
- Validate timeline and milestones
- Confirm Definition of Done criteria

#### 11. Sprint Documentation
Commit all sprint planning artifacts to repository:

```
Use: mcp_github_push_files
- files: [
    "docs/sprints/sprint-{number}/PRD.md",
    "docs/sprints/sprint-{number}/requirements.md", 
    "docs/sprints/sprint-{number}/tech-stack.md",
    "docs/sprints/sprint-{number}/research/context7-findings.md"
  ]
- message: "docs: Sprint {number} planning artifacts and PRD"
- branch: "main"
```

## Sprint Execution Reminders

### Daily Development
- Reference PRD sections in commit messages
- Follow Context7 implementation patterns
- Update PRD with progress and changes

### Weekly Reviews
- Assess PRD completion percentage
- Update risk assessments
- Document any scope changes

### Sprint Retrospective
- Complete PRD assessment
- Document lessons learned
- Archive sprint artifacts

## Templates Location

All templates are available in:
- **PRD Template:** `docs/sprints/templates/PRD-template.md`
- **Quick Start:** `docs/sprints/templates/create-sprint.md`
- **Mindmap Templates:** Referenced in `sprint-planning.mdc`

---

**Estimated Total Setup Time:** 3.5 hours  
**Prerequisites:** Access to all required MCP servers  
**Output:** Complete sprint planning package ready for execution

*This quick-start guide implements the workflow defined in `.cursor/rules/sprint-planning.mdc`*