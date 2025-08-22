# Codebase Evolution Tracking System - Final PRD

**Sprint 11 Final Deliverable**  
**Status**: Ready for Implementation  
**Last Updated**: June 2025

---

## 🎯 **Executive Summary**

Transform the current developer graph from a static relationship mapper into a dynamic **codebase evolution tracking system** that tells the story of how ideas, features, and architectural decisions evolved over time. The system will integrate git history, track idea lifecycles, and provide insights into what worked vs. what didn't.

**Core Vision**: A living, breathing knowledge atlas for our codebase that serves as both a temporal narrative and structural map, enabling developers to understand not just what the codebase is, but how it got there and what we can learn from that journey.

---

## 🚨 **Problem Statement**

The current dev-graph suffers from several critical shortcomings:

### **1. No Temporal Awareness**
- Nodes and relations appear frozen in amber
- Users cannot tell when requirements were added, refined, or deprecated
- No way to determine if seemingly related nodes actually existed years apart

### **2. Graph Hairball Effect**
- Poorly designed network diagrams become "tangled and frustrating" (Cambridge Intelligence)
- Current implementation offers only rudimentary toggles
- Quickly devolves into unreadable tangle on anything but smallest datasets

### **3. Lack of Interactive Depth**
- No timeline slider, diff view, or detailed node inspection
- Missing point-and-click exploration with search and perspectives
- No file histories, commit graphs, or blame annotations

### **4. No Success/Failure Insight**
- Without metrics tied to performance or adoption, we cannot identify:
  - Which architectural decisions were good or bad
  - What patterns led to successful implementations
  - How to avoid repeating past mistakes

---

## 🔍 **Research & Inspiration**

### **Git-Centric Analysis Tools**
- **GitKraken & GMaster**: Interactive branch explorers with drag-and-drop commits
- **GitLens for VS Code**: Colorful commit graphs, file-level history, blame annotations
- **GitUp**: Branch labyrinth rendering tens of thousands of commits in real-time

### **Graph Visualization Best Practices**
- **Cambridge Intelligence Guidelines**: "Effortless understanding of complex relationships"
- **Neo4j Bloom**: Point-and-click exploration with perspectives and custom styling
- **Neo4j Visualization Library (NVL)**: First-class Neo4j integration with React wrapper

### **JavaScript Libraries**
- **D3.js**: Flexibility and rich interactivity
- **Sigma.js**: Large networks with built-in force-directed layouts
- **Vis.js**: Simple APIs for dynamic graphs and timelines
- **React-Force-Graph**: Currently used, evaluate for performance

### **Timeline Libraries**
- **Vis-Timeline**: Interactive timelines with start/end dates, zooming, dragging
- **React-Chrono**: React-based timeline components

---

## 🎨 **Product Vision**

We envision a **Developer-Graph Evolution Service** that serves as a knowledge atlas for our codebase. At its heart is a temporal graph database built on Neo4j with git-derived timestamps. The frontend provides two synchronized panels:

1. **Timeline Panel**: Shows evolution of requirements, sprints, and files
2. **Graph Panel**: Reveals structural relationships with time-aware filtering

**Key Experience**: When you scrub through time, the graph highlights only nodes and edges relevant at that moment. Users can search for requirements, jump to implementations, inspect commits, and compare performance metrics before and after major changes.

---

## 🏗️ **Core Requirements**

### **1. Temporal Relationship Tracking (MANDATORY)**

#### **Git-Driven Timestamps (CRITICAL)**
- **ALL temporal data MUST be derived from git commits**
- Each node and relationship must store creation and modification commit hash/timestamp
- **Document and file timestamps are EXPLICITLY FORBIDDEN**
- Use `git log --follow` for file evolution tracking
- Implement `git blame` for line-level change authorship

#### **Versioned Relationships**
- Relationship edges have start and end commit hashes
- Relations exist only during valid commit ranges
- Enable time-range queries and historical state reconstruction

#### **Sprint Mapping**
- Sprint nodes map to commit ranges
- `git_history_service` must map each sprint to commit hashes between start/end dates
- Attach all changes within sprint windows

#### **Entity Lifecycle Events**
- Track for each requirement, file, or document:
  - Creation, update, deprecation, replacement
  - Reasons (extracted from commit messages or PR descriptions)

#### **Temporal Queries**
- "Show state of node X on date Y"
- "List all changes affecting requirement R between commits A and B"
- "Find when feature F was deprecated and by what"

### **2. Enhanced Node & Relationship Types**

#### **Node Types**
```cypher
// Idea Nodes
CREATE (r:Requirement {
    id: "FR-123",
    title: "Feature X",
    author: "developer@example.com",
    date_created: "2024-01-01T10:00:00Z",  // From git
    goal_alignment: "Performance",
    tags: ["frontend", "critical"]
})

// Implementation Nodes
CREATE (f:File {
    path: "frontend/src/components/FeatureX.tsx",
    first_commit: "abc123",
    last_commit: "def456",
    total_commits: 25,
    authors: ["dev1@example.com", "dev2@example.com"],
    language: "typescript"
})

// Sprint Nodes
CREATE (s:Sprint {
    number: "Sprint-11",
    start_date: "2024-06-01T00:00:00Z",
    end_date: "2024-06-30T23:59:59Z",
    velocity: 85,
    commit_range: ["abc123", "def456"]
})

// Git Commit Nodes (Temporal Backbone)
CREATE (c:GitCommit {
    hash: "abc123",
    message: "Implement feature X",
    author: "developer@example.com",
    timestamp: "2024-01-01T10:00:00Z",
    branch: "main",
    files_changed: ["frontend/src/components/FeatureX.tsx"],
    lines_added: 150,
    lines_deleted: 20
})
```

#### **Relationship Types**
```cypher
// Core Relationships
CREATE (req:Requirement)-[:IMPLEMENTS {commit: "abc123", timestamp: "2024-01-01T10:00:00Z"}]->(f:File)
CREATE (req:Requirement)-[:EVOLVES_FROM {commit: "def456", diff_summary: "Added validation"}]->(old_req:Requirement)
CREATE (old_file:File)-[:REFACTORED_TO {commit: "ghi789", refactor_type: "Component extraction"}]->(new_file:File)
CREATE (node:Node)-[:DEPRECATED_BY {commit: "jkl012", reason: "Performance issues"}]->(replacement:Node)

// Context Relationships
CREATE (req:Requirement)-[:INSPIRED_BY {source: "Research paper X"}]->(research:Document)
CREATE (req:Requirement)-[:BLOCKED_BY {commit: "mno345", blocker: "Database dependency"}]->(blocker:Requirement)
CREATE (req:Requirement)-[:DEPENDS_ON {commit: "pqr678", dependency_type: "Infrastructure"}]->(dependency:Requirement)
```

### **3. Interactive Frontend Components**

#### **A. TimelineView (Chronological Visualization)**
- **Scale-aware timeline** using vis-timeline or react-chrono
- **Event stacking with participants** on lanes (requirement, file, sprint)
- **Heatmap overlay** for large time spans with activity spikes
- **Success/failure annotations** with icons and explanations
- **Zooming** from hours to years with drag navigation

#### **B. EvolutionGraph (Interactive Network View)**
- **Graph rendering engine**: Evaluate Neo4j Visualization Library (NVL) vs Sigma.js
- **Filtering & perspectives**: Side panel for node/relationship type selection
- **Time-aware graph**: Responds to timeline slider with opacity/color changes
- **Node and edge styling**: Consistent colors, shapes, and hover tooltips
- **Clutter reduction**: Toggles for collapsing sub-graphs and hiding low-degree nodes

#### **C. Detail Drawers and Diff Views**
- **Node detail drawer**: Commit history, evolution timeline, implementation links
- **Diff viewer**: Code diffs for files, requirement evolution diffs
- **Commit explorer**: List commits with messages, authors, timestamps, changed files

### **4. Success and Pattern Analytics**

#### **Success/Failure Metrics**
- **Success criteria**: Meets acceptance criteria, remains active for N sprints without major refactoring
- **Failure indicators**: Deprecated within short window, high bug counts
- **Data sources**: Performance tests, adoption statistics, code quality tools

#### **Pattern Recognition Engine**
- Identify successful design patterns and anti-patterns
- Feed insights back into timeline via annotations
- Provide "Success Patterns" view for analysis

#### **Impact Analysis**
- Track downstream impacts when requirements/technologies are deprecated
- Summarize impacts to avoid repeating mistakes

---

## 🚀 **Implementation Roadmap**

### **Phase 1: Temporal Foundation (Weeks 1-4)**

#### **Backend Implementation**
- [x] **Git History Service** (`developer_graph/git_history_service.py`)
  - [x] Parse commit logs with `git log --follow` (via GitPython plumbing)
  - [x] Extract commit metadata (hash, author, timestamp, message, files)
  - [x] Implement `git blame` for line-level tracking (basic support)
  - [ ] Map sprints to commit ranges (planned)
  - [x] Detect file renames and moves (via `--name-status` with rename codes)

- [x] **Enhanced Neo4j Schema** (`developer_graph/schema/`)
  - [x] Add GitCommit and File nodes (constraints + merge helpers)
  - [ ] Store commit ranges on relationship edges (Phase 2)
  - [ ] Implement schema versioning strategy (planned)
  - [ ] Write tests for temporal accuracy (planned)

- [x] **Basic API Endpoints** (`developer_graph/api.py`)
  - [x] Expose existing endpoints for nodes, relations, search (unchanged)
  - [x] Add new endpoints for commit details (`/commit/{hash}`)
  - [x] Add file history endpoints (`/file/history?path=...`)
  - [x] Implement time-bounded subgraph queries (basic stub using relationship timestamps)

#### **Frontend Foundation**
- [x] **Timeline Component** (`frontend/src/app/dev-graph/components/TimelineView.tsx`)
  - [ ] Build using vis-timeline or react-chrono (Phase 2 enhancement)
  - [x] Integrate with existing graph view (basic list, commits feed)
  - [ ] Add time slider for node filtering (planned)
  - [x] Implement basic event rendering (commit-based entries)

#### ✅ Additional Progress (Phase 1 wrap-up + Phase 2 early)

- [x] Sprint mapping utility (`developer_graph/sprint_mapping.py`) and endpoint
  - [x] `GET /api/v1/dev-graph/sprint/map?number=...&start_iso=...&end_iso=...`
  - Maps sprint windows to [start_hash, end_hash] using date filters

- [x] Temporal ingestion engine (Phase 2 stub) (`developer_graph/temporal_engine.py`)
  - [x] Schema application helper
  - [x] Ingest recent commits → merge `GitCommit`/`File` nodes and `TOUCHED` rels
  - [x] Endpoint: `POST /api/v1/dev-graph/ingest/recent?limit=100`

- [x] Dev-graph page enhancements (`frontend/src/app/dev-graph/page.tsx`)
  - [x] Time slider controls commit timeline limit (20–500)
  - [x] Commit feed bound to slider

- [x] Tests
  - [x] `tests/test_git_history_service.py` basic coverage for commits and file history

#### **Testing & Validation**
- [ ] **Git History Validation** (`developer_graph/tests/`)
  - [ ] Create test suite for git history extraction
  - [ ] Validate temporal accuracy against known commit history
  - [ ] Test git blame integration
  - [ ] Performance testing with sample data

### **Phase 2: Evolution Tracking & UI (Weeks 5-12)**

#### **Backend Enhancement**
- [ ] **Requirement & Implementation Tracking**
  - [ ] Link requirements to commits and files
  - [ ] Track evolution events and changes
  - [ ] Implement relationship discovery with NLP
  - [ ] Add commit-based relationship evolution

- [ ] **Temporal Engine** (`developer_graph/temporal_engine.py`)
  - [ ] Build evolution timeline for any node
  - [ ] Combine Neo4j relationships with git data
  - [ ] Support time-bounded queries
  - [ ] Implement change impact analysis

#### **Frontend Enhancement**
- [ ] **Interactive Graph** (`frontend/src/app/dev-graph/components/EvolutionGraph.tsx`)
  - [ ] Evaluate NVL vs Sigma.js for performance
  - [ ] Implement filtering by node/relationship type
  - [ ] Add timeline synchronization
  - [ ] Implement node detail drawers

- [ ] **Search & Perspectives**
  - [ ] Build search bar for node discovery
  - [ ] Allow saving custom perspectives
  - [ ] Implement filtering and layout settings
  - [ ] Add node clustering and summarization

### **Phase 3: Success Metrics & Analytics (Weeks 13-24)**

#### **Success Detection**
- [ ] **Success/Failure Criteria**
  - [ ] Define objective success metrics
  - [ ] Integrate with performance pipelines
  - [ ] Add timeline annotations
  - [ ] Create summary panels

#### **Pattern Recognition**
- [ ] **Analytics Engine**
  - [ ] Implement evolution pattern algorithms
  - [ ] Correlate patterns with success metrics
  - [ ] Provide "Success Patterns" view
  - [ ] Add comparative feature analysis

#### **Performance Optimization**
- [ ] **Scalability Improvements**
  - [ ] Introduce caching and incremental updates
  - [ ] Evaluate Sigma.js scalability features
  - [ ] Use Web Workers for heavy computations
  - [ ] Implement cluster collapsing for large graphs

### **Phase 4: Advanced Features & Integration (Weeks 25-48)**

#### **Machine Learning Integration**
- [ ] **Predictive Analytics**
  - [ ] Train models on historical data
  - [ ] Predict success/failure likelihood
  - [ ] Provide warnings for failure-prone patterns
  - [ ] Implement pattern similarity scoring

#### **CI/CD Integration**
- [ ] **Pipeline Integration**
  - [ ] Hook into CI pipelines for test results
  - [ ] Capture performance metrics
  - [ ] Link metrics to commits and requirements
  - [ ] Real-time graph updates

#### **Third-Party Tools**
- [ ] **External Integrations**
  - [ ] GitHub/GitLab for PR discussions
  - [ ] Jira for issue tracking
  - [ ] Slack for notifications
  - [ ] SonarQube/Code Climate for quality metrics

#### **User Customization**
- [ ] **Export & Sharing**
  - [ ] Export timeline views as images/HTML
  - [ ] Share custom perspectives across team
  - [ ] User preference management
  - [ ] Collaborative annotation features

---

## ⚠️ **Technical Risks & Mitigations**

### **1. Scalability of Graph Rendering**
- **Risk**: Large codebases overwhelm browser
- **Mitigation**: Use Sigma.js for scale, implement cluster collapsing, limit rendered nodes

### **2. Inaccurate Commit Parsing**
- **Risk**: Ambiguous commit messages lead to false relationships
- **Mitigation**: Encourage commit conventions, use NLP extraction, provide manual override

### **3. Data Freshness**
- **Risk**: Real-time updates are costly
- **Mitigation**: Incremental git parsing, background jobs, stale data indicators

### **4. Privacy & Security**
- **Risk**: Sensitive information in commits/documents
- **Mitigation**: Access control, redaction, audit logging

---

## 📊 **Success Metrics**

### **Technical Metrics**
- **Temporal Accuracy**: % of nodes/relationships correctly annotated with commit data
- **Performance**: Query response times for temporal queries
- **Data Freshness**: How current the evolution data is

### **User Experience Metrics**
- **Navigation Efficiency**: Time to find implementation history or specific commits
- **Insight Discovery**: Number of unique patterns identified by users
- **User Adoption**: Active users, sessions per week, satisfaction scores

### **Business Metrics**
- **Development Velocity**: Story points per sprint before/after adoption
- **Code Quality**: Bug counts, technical debt reduction
- **Knowledge Retention**: Onboarding time for new team members

---

## 🎯 **Immediate Next Steps (Sprint 11 Completion)**

### **Week 1-2: Foundation Setup**
1. [ ] Install GitPython and set up git repository access
2. [ ] Create basic `git_history_service.py` with commit parsing
3. [ ] Design enhanced Neo4j schema with git-based nodes
4. [ ] Set up development environment for timeline components

### **Week 3-4: Core Implementation**
1. [ ] Implement git history extraction and validation
2. [ ] Build basic timeline component with vis-timeline
3. [ ] Create enhanced Neo4j schema and constraints
4. [ ] Write comprehensive tests for temporal accuracy

### **Week 5-6: Integration & Testing**
1. [ ] Integrate timeline with existing graph view
2. [ ] Implement time-based node filtering
3. [ ] Add basic commit detail endpoints
4. [ ] Perform end-to-end testing with real repository data

---

## 🏁 **Conclusion**

This unified PRD transforms the original high-level vision into a concrete, implementable plan for an interactive, intuitive, and truly temporal dev-graph. By anchoring all temporal data to git history, borrowing best practices from graph visualization and git tools, and focusing on user experience and success metrics, we can build a system that not only shows relationships but tells the story of how the codebase evolves.

**Key Principles**:
- **Git history is the single source of truth** for all temporal data
- **User experience drives technical decisions** - avoid hairballs, enable exploration
- **Performance and scalability** are non-negotiable for large repositories
- **Success metrics must be objective** and tied to actual development outcomes

With careful implementation following this roadmap, this service will become a cornerstone of our development workflow and a model for how to visualize the life of a codebase. It will guide developers through the labyrinth of history and enable them to make better architectural decisions based on data-driven insights rather than intuition alone.

---

**Document Status**: ✅ **FINAL - Ready for Implementation**  
**Sprint 11 Deliverable**: ✅ **Complete**  
**Next Phase**: Implementation following Phase 1 roadmap
