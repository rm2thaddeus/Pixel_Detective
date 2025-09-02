# Dev Graph Migration

Status: Draft for Side‑Project Spin‑off
Last Updated: 2025‑09‑02

---

## Executive Summary

We are migrating the Dev Graph feature into a standalone, doc‑centric side project to:
- Isolate performance cost from the main app.
- Simplify the model by anchoring on deterministic Markdown structure instead of fuzzy detection.
- Enable easy portability to new machines by consuming a Git clone (local or remote).

This document captures the context, decisions, architecture, data model, and a pragmatic implementation plan. It also refines the original objective of “Knowledge Graph Extraction from Sprint‑Based Markdown Docs and Git History” into a clear, testable spec.

---

## Implementation Status Update (2025‑09‑02)

The standalone Dev Graph now captures sprints, documents, chunks, and commits as specified. Recent work added a deterministic chunking layer and connecting edges:
- Chunk nodes: H1/H2/H3 sections parsed into `:Chunk` with stable IDs `path#slug-ordinal`, including `heading`, `level`, `ordinal`, `content_preview`, `length`, and `mentions`.
  - Code: `developer_graph/enhanced_ingest.py:264`
- Sprint→Document edges: `(Sprint)-[:CONTAINS_DOC]->(Document)` inferred from document paths in `docs/sprints/sprint-*` or `docs/sprints/s-*`.
  - Code: `developer_graph/enhanced_ingest.py:446`
- Document→Chunk edges: `(Document)-[:CONTAINS_CHUNK]->(Chunk)`.
  - Code: `developer_graph/enhanced_ingest.py:455`
- Chunk→Requirement edges: `(Chunk)-[:MENTIONS]->(Requirement)` when chunk text includes `FR-..`/`NFR-..`.
  - Code: `developer_graph/enhanced_ingest.py:464`
- Constraints: unique `Chunk.id` added alongside existing Sprint/Requirement/Document constraints.
  - Code: `developer_graph/enhanced_ingest.py:375`

Operational note: Because the API image bakes the `developer_graph/` sources at build time, rebuild `dev_graph_api` after code updates or mount the source for hot‑reload during development. See Ops section below.

## Conversation Highlights (Context)

- Pain points: The in‑app Dev Graph added heavy dependencies and lag. Interaction changes (migration to Sigma.js) improved scale but removed some familiar affordances. The resulting graph felt like a tangle with limited interpretability.
- Insight: The docs folder already encodes structure and meaning (sprint folders, PRDs, READMEs, transitions, status index). A doc‑centric graph is more deterministic and interpretable.
- Direction: Split Dev Graph as a standalone pair (Neo4j + API + optional mini UI). Prefer a docs‑first graph with optional Git enrichment. Support remote Git cloning so it can run off a server repo rather than a personal machine.

## Comprehensive Code References

### Core API & Services
- **Main API**: `developer_graph/api.py` - FastAPI service with comprehensive endpoints
- **Git History Service**: `developer_graph/git_history_service.py` - Git commit parsing, file history, blame support
- **Temporal Engine**: `developer_graph/temporal_engine.py` - Neo4j ingestion with temporal relationships
- **Sprint Mapping**: `developer_graph/sprint_mapping.py` - Maps sprint windows to commit ranges
- **Schema Utilities**: `developer_graph/schema/temporal_schema.py` - Neo4j constraints and relationship helpers
- **Legacy Ingest**: `developer_graph/ingest.py` - Original ingestion logic (sprint docs, requirements, commits)

### Docker & Infrastructure
- **Docker Compose**: `docker-compose.yml` (services `neo4j`, `dev_graph_api`)
- **Standalone Dockerfile**: `backend/developer_graph_service/Dockerfile`
- **Service Entry Point**: `backend/developer_graph_service/main.py`
- **Dependencies**: `backend/developer_graph_service/requirements.txt`

### Frontend Components (Salvageable)
- **Main Page**: `frontend/src/app/dev-graph/page.tsx` - Complete UI with tabs, timeline, analytics
- **Evolution Graph**: `frontend/src/app/dev-graph/components/EvolutionGraph.tsx` - Sigma.js-based graph visualization
- **Timeline View**: `frontend/src/app/dev-graph/components/TimelineView.tsx` - Commit timeline with range selection
- **Sprint View**: `frontend/src/app/dev-graph/components/SprintView.tsx` - Sprint-based navigation
- **Node Details**: `frontend/src/app/dev-graph/components/NodeDetailDrawer.tsx` - Node inspection drawer
- **Search**: `frontend/src/app/dev-graph/components/SearchBar.tsx` - Graph search functionality
- **Analytics**: `frontend/src/app/dev-graph/components/TemporalAnalytics.tsx` - Temporal analysis views

### Documentation Structure
- **Sprint Folders**: `docs/sprints/sprint-*` - 11 sprints with PRDs, READMEs, transitions
- **Planning Index**: `docs/sprints/planning/SPRINT_STATUS.md` - Sprint dates and status tracking
- **Templates**: `docs/sprints/templates/` - PRD and sprint creation templates

---

## Goals

- **Performance isolation**: run Dev Graph independent of the main app.
- **Git-centric knowledge graph**: Git history is the primary temporal backbone, with docs providing semantic structure.
- **Deterministic, interpretable model**: leverage docs structure for semantic meaning, Git for temporal evolution.
- **Portability**: accept a remote `GIT_REMOTE_URL` or a bind‑mounted repo.
- **Comprehensive evolution tracking**: Sprint → Doc → Chunk graph with full Git commit lineage and requirement evolution.

**Core Philosophy**: Git commits are the source of truth for temporal relationships. Documentation provides semantic structure and requirement definitions. The graph connects both to show how requirements evolve through commits and how documentation reflects implementation reality.

Non‑Goals (initial phase):
- Real‑time graph of entire codebase activity.
- Heavy, physics‑based layouts in the UI.

---

## Target Architecture (Standalone)

Components:
- Neo4j (graph DB)
- Dev Graph API (FastAPI): exposes endpoints to parse docs, build a graph model (JSON and/or Neo4j), and serve subgraphs.
- Optional Dev Graph UI (Next.js or minimal SPA) for browsing.

Deployment Modes:
1) Local bind‑mount: mount the project repo read‑only and set `REPO_PATH`.
2) Remote clone: container clones from `GIT_REMOTE_URL` (and `GIT_BRANCH`) into `/repo`, sets `REPO_PATH=/repo`.

Operational Notes:
- CORS origins should be configurable via env (e.g., `CORS_ORIGINS=..., ...`).
- API should expose both raw JSON graph and Neo4j ingest option (toggleable).

---

## Git-Centric Data Model (Core)

Node Types:
- **Sprint**: `{ id: 'sprint-11', number: '11', start_date, end_date, commit_range: [start_hash, end_hash] }`
- **Doc**: `{ id, sprint_id, path, title, type, last_modified_commit? }` where `type ∈ {PRD, README, SUMMARY, TRANSITION, PLAN, BACKLOG, MINDMAP, OTHER}`
- **Chunk**: `{ id, doc_id, heading_level, heading_text, ordinal, content, summary?, created_commit?, modified_commit? }`
- **Requirement**: `{ id: 'FR-123' | 'NFR-45', title, author, date_created, goal_alignment?, tags? }` (extracted from docs and commits)
- **GitCommit**: `{ hash, message, author, timestamp, branch, files_changed[] }` (core temporal backbone)
- **File**: `{ path, language?, last_modified_commit? }` (tracked through Git history)

Core Relationships (Git-driven):
- `(:GitCommit)-[:TOUCHED {change_type, timestamp}]->(:File)` - File modification history
- `(:GitCommit)-[:IMPLEMENTS {timestamp}]->(:Requirement)` - Requirement implementation
- `(:Requirement)-[:IMPLEMENTS {commit, timestamp}]->(:File)` - Requirement to file mapping
- `(:Requirement)-[:EVOLVES_FROM {commit, diff_summary, timestamp}]->(:Requirement)` - Requirement evolution
- `(:File)-[:REFACTORED_TO {commit, refactor_type, timestamp}]->(:File)` - File refactoring/renames

Documentation Relationships:
- `(:Sprint)-[:CONTAINS_DOC]->(:Doc)`
- `(:Doc)-[:CONTAINS_CHUNK]->(:Chunk)`
- `(:Chunk)-[:REFERENCES {anchor?}]->(:Doc|:Chunk)` for Markdown links
- `(:Chunk)-[:MENTIONS]->(:Requirement)` when content contains `\b(FR|NFR)-\d+\b`
- `(:Sprint)-[:TRANSITION_TO]->(:Sprint)` using explicit transition docs

ID Strategy:
- Sprint: folder name (e.g., `sprint-07`).
- Doc: normalized path (e.g., `docs/sprints/sprint-07/PRD.md`).
- Chunk: `doc_path#h2_slug` (and optional `/h3_slug`) plus a short hash to avoid collisions.

Metadata:
- Keep `sprint`, `file`, `heading`, `position`, `keywords?`, `created_at?` (when derivable), and link anchors.

---

## Cross‑Sprint Evolution (Phase 2)

Goal: Connect how concepts evolve across sprints without fuzzy magic.

Signals (deterministic first, heuristic later):
1) Transition docs: `sprint-N/transition-to-sprint-(N+1).md` → creates `(:Sprint {N})-[:TRANSITION_TO]->(:Sprint {N+1})`.
2) Filename/topic continuity: PRD/README for same feature terms across adjacent sprints (heuristic: shared headings or exact phrase matches).
3) Direct cross‑links: Markdown links pointing to prior sprint docs.

Edges:
- `(:Chunk|:Doc)-[:EVOLVES_FROM {signal: 'transition'|'heading_match'|'explicit_link', score}] -> (:Chunk|:Doc)`.

Validation UI:
- Present suggested evolution pairs with reason codes and allow manual confirmation/ignore.

---

## Git Integration Strategy (Core Feature)

Git history provides the temporal backbone for all relationships:
- **Commit Import**: Import commits in bounded windows (configurable limit, default 1000)
- **File Tracking**: Track all file modifications through Git history with `--follow` support
- **Requirement Mapping**: Extract FR/NFR references from commit messages and link to files
- **Evolution Detection**: Detect requirement evolution patterns in commit messages
- **Refactoring Detection**: Track file renames and refactoring through Git diff analysis

**Existing Implementation**: The current codebase already includes comprehensive Git integration:
- `GitHistoryService` provides commit parsing, file history, and blame support
- `TemporalEngine` handles Neo4j ingestion with temporal relationships
- `SprintMapper` maps sprint windows to commit ranges
- Schema utilities support all temporal relationship types

**Performance Considerations**:
- Bounded commit windows prevent unbounded growth
- Lazy loading of commit details
- Indexed queries on timestamp and commit hash
- Configurable limits for different use cases

---

## Extraction Pipeline (Git-Centric)

Inputs:
- **Git Repository**: Local or remote clone with full history
- **Documentation**: `docs/sprints/` structure with planning index
- **Configuration**: Commit limits, date ranges, file filters

Steps:
1) **Git Foundation**: Import commits in bounded window → create GitCommit and File nodes
2) **Sprint Discovery**: Parse `docs/sprints/` folders → create Sprint nodes with commit ranges
3) **Document Parsing**: Parse Markdown docs → create Doc and Chunk nodes (H1/H2/H3 into `:Chunk`) with stable IDs and references
4) **Requirement Extraction**: Extract FR/NFR from docs and commits → create Requirement nodes
5) **Relationship Building**: 
   - Link commits to files (TOUCHED relationships)
   - Link requirements to files (IMPLEMENTS relationships)
   - Detect evolution patterns (EVOLVES_FROM relationships)
   - Map sprint transitions (TRANSITION_TO relationships)
   - Connect sprints to documents (CONTAINS_DOC)
   - Connect documents to chunks (CONTAINS_CHUNK)
   - Connect chunks to requirements (MENTIONS)
6) **Temporal Indexing**: Build time-bounded subgraph capabilities
7) **Output Generation**: JSON graph + Neo4j ingest

**Existing Implementation**: The current pipeline is already implemented:
- `TemporalEngine.ingest_recent_commits()` handles Git import
- `EnhancedDevGraphIngester` provides sprint/document parsing plus Chunk extraction and linking (Sprint→Document, Document→Chunk, Chunk→Requirement)
- `GitHistoryService` provides commit and file history
- Schema utilities handle all relationship types

Output Formats:
- `docs_graph.json` (default): portable, versionable, diff‑friendly
- Neo4j ingest (core): Full temporal graph with commit lineage

Quality Gates:
- Deterministic IDs; no duplicate node IDs
- All reference edges point to existing targets
- Commit timestamps are valid ISO8601 strings
- File paths are normalized and consistent

---

## API Surface (Existing Comprehensive API)

**Current Implementation** (`developer_graph/api.py`):

### Core Graph Endpoints
- `GET /api/v1/dev-graph/nodes` – list nodes by type/limit/offset (for UI pagination)
- `GET /api/v1/dev-graph/nodes/count` – total node count
- `GET /api/v1/dev-graph/relations` – list edges by type/limit/offset
- `GET /api/v1/dev-graph/relations/count` – total relationship count
- `GET /api/v1/dev-graph/search` – search nodes by content

### Git Integration Endpoints (Core)
- `GET /api/v1/dev-graph/commits` – list recent commits with optional path filtering
- `GET /api/v1/dev-graph/commit/{commit_hash}` – commit details with stats
- `GET /api/v1/dev-graph/file/history` – file history with rename tracking
- `POST /api/v1/dev-graph/ingest/recent` – ingest recent commits into Neo4j

### Temporal & Sprint Endpoints
- `GET /api/v1/dev-graph/subgraph/by-commits` – time-bounded subgraph by commit range
- `GET /api/v1/dev-graph/sprint/map` – map sprint to commit range
- `GET /api/v1/dev-graph/sprints` – list all sprints with commit ranges
- `GET /api/v1/dev-graph/sprints/{number}` – sprint details with metrics

### Evolution & Analytics Endpoints
- `GET /api/v1/dev-graph/evolution/requirement/{req_id}` – requirement evolution timeline
- `GET /api/v1/dev-graph/evolution/file` – file evolution timeline

### Environment Configuration
- `REPO_PATH` – root of repo (bind‑mounted or cloned)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` – Neo4j connection
- `CORS_ORIGINS` – comma‑separated origins for the UI (currently: localhost:3000)

---

## UI (Existing Comprehensive Frontend)

**Current Implementation** (`frontend/src/app/dev-graph/`):

### Core Components
- **Main Page** (`page.tsx`): Complete UI with tabs, timeline, analytics, and graph visualization
- **Evolution Graph** (`EvolutionGraph.tsx`): Sigma.js-based graph with clustering and time filtering
- **Timeline View** (`TimelineView.tsx`): Commit timeline with range selection and time scrubbing
- **Sprint View** (`SprintView.tsx`): Sprint-based navigation with commit range mapping
- **Node Details** (`NodeDetailDrawer.tsx`): Comprehensive node inspection with evolution timelines
- **Search** (`SearchBar.tsx`): Graph search with filtering capabilities
- **Analytics** (`TemporalAnalytics.tsx`): Temporal analysis and metrics

### Key Features
- **Multi-view Interface**: Timeline, Sprint, and Analytics tabs
- **Time-bounded Queries**: Filter graph by commit ranges and timestamps
- **Interactive Graph**: Sigma.js visualization with clustering and zoom
- **Evolution Tracking**: Requirement and file evolution timelines
- **Sprint Integration**: Sprint-based filtering with commit range mapping
- **Real-time Updates**: Live commit ingestion and graph updates

### Design Principles
- **Git-centric Navigation**: Time-based filtering as primary interaction
- **Sprint Context**: Sprint-based organization with commit lineage
- **Evolution Focus**: Emphasis on how requirements and files evolve over time
- **Performance**: Paginated loading, lazy content, optimized queries

---

## Migration Plan

### Current State Analysis
✅ **Already Implemented**:
- Complete FastAPI service with comprehensive Git integration
- Full Neo4j schema with temporal relationships
- Comprehensive frontend with Sigma.js visualization
- Docker containerization with proper networking
- Git history service with commit parsing and file tracking
- Sprint mapping and temporal analytics

### Phase A – Standalone Deployment (Ready to Execute)
1) **Extract Services**: Use existing `neo4j` and `dev_graph_api` from `docker-compose.yml`
2) **Configure Environment**: Set `REPO_PATH` to bind-mounted path (read-only)
3) **Update CORS**: Configure `CORS_ORIGINS` for standalone UI access
4) **Test API**: Verify all endpoints work at `http://localhost:8080`

### Phase B – Remote Clone Support (Enhancement)
1) **Add Entrypoint**: Create `entrypoint.sh` for automatic Git cloning
2) **Environment Variables**: Support `GIT_REMOTE_URL` and `GIT_BRANCH`
3) **Volume Persistence**: Use Docker volume for `/repo` persistence
4) **Clone Logic**: Implement repository cloning on container startup

### Phase C – Standalone UI (Extraction)
1) **Create Standalone App**: Extract `frontend/src/app/dev-graph/*` to `tools/dev-graph-ui/`
2) **Update Configuration**: Point `NEXT_PUBLIC_DEV_GRAPH_API_URL` to standalone API
3) **Remove from Main App**: Remove Dev Graph from main frontend build
4) **Independent Deployment**: Deploy UI separately from main application

### Phase D – Enhanced Features (Future)
1) **Document Parsing**: Enhance Markdown parsing for better chunk extraction
2) **Cross-Sprint Evolution**: Improve requirement evolution detection
3) **Performance Optimization**: Add caching and query optimization
4) **Export/Import**: Add graph snapshot capabilities

### Immediate Next Steps
1) **Test Current Implementation**: Verify Docker services work correctly
2) **Document API Usage**: Create API documentation and examples
3) **Performance Testing**: Test with full repository history
4) **UI Extraction**: Begin standalone UI creation

---

## Improved Spec: Knowledge Graph Extraction from Sprint Docs + Git

Objective:
- Build a traceable knowledge graph of sprint documentation, showing how concepts evolve across sprints, with optional links to code commits.

Inputs:
- `docs/sprints/sprint-*` Markdown folders; planning index at `docs/sprints/planning/SPRINT_STATUS.md`.
- Optional Git repository (local or remote).

Primary Tasks (Doc‑First):
1) Parse Markdown across sprint folders: extract H1/H2/H3, links, FR/NFR.
2) Chunk content by H2 (primary), optionally H3; capture summaries.
3) Build nodes (Sprint, Doc, Chunk, Requirement) and edges (`CONTAINS_DOC`, `CONTAINS_CHUNK`, `REFERENCES`, `MENTIONS`, `TRANSITION_TO`).
4) Suggest cross‑sprint `EVOLVES_FROM` links with reason codes; keep them reviewable.

Optional Tasks (Git):
5) Import commits in a bounded window and map relevant relationships (`IMPLEMENTS`, `TOUCHED`), keeping provenance and scores explicit.

Output:
- JSON graph (portable) and/or Neo4j ingest.
- Node metadata includes sprint, path, heading, position, and tags.

Requirements:
- Resource‑efficient (runs outside main app; dockerized).
- Modular; Git enrichment is optional and isolated.
- Traceability: every edge has a reason and/or source text.

Acceptance Criteria:
- Deterministic IDs; 0 dangling reference edges in baseline build.
- For any sprint, the graph reconstructs Sprint → Docs → Chunks with accurate links.
- Cross‑sprint suggestions include reason codes and can be toggled off.

---

## Example JSON Shape (Docs Graph)

```json
{
  "nodes": [
    {"id": "sprint-11", "type": "Sprint", "number": "11", "start_date": "2025-01-01", "end_date": "2025-01-31"},
    {"id": "docs/sprints/sprint-11/PRD.md", "type": "Doc", "sprint": "sprint-11", "title": "PRD", "doc_type": "PRD"},
    {"id": "docs/sprints/sprint-11/PRD.md#feature-x", "type": "Chunk", "doc": "docs/sprints/sprint-11/PRD.md", "heading": "Feature X", "level": 2, "ordinal": 1, "summary": "..."},
    {"id": "FR-123", "type": "Requirement"}
  ],
  "edges": [
    {"type": "CONTAINS_DOC", "from": "sprint-11", "to": "docs/sprints/sprint-11/PRD.md"},
    {"type": "CONTAINS_CHUNK", "from": "docs/sprints/sprint-11/PRD.md", "to": "docs/sprints/sprint-11/PRD.md#feature-x"},
    {"type": "MENTIONS", "from": "docs/sprints/sprint-11/PRD.md#feature-x", "to": "FR-123"},
    {"type": "TRANSITION_TO", "from": "sprint-10", "to": "sprint-11"}
  ]
}
```

---

## Ops Cookbook

Compose (reuse existing services):
```bash
docker compose up -d neo4j dev_graph_api
```

Environment ideas:
```bash
export NEO4J_PASSWORD=change_me
export CORS_ORIGINS=http://localhost:3001
# Bind mount repo:
export REPO_PATH=/workspace
# Or remote clone (phase 1.5):
export GIT_REMOTE_URL=https://github.com/you/your-repo.git
export GIT_BRANCH=main

# Rebuild API after code changes to developer_graph/* (baked at build time)
docker compose build dev_graph_api && docker compose up -d dev_graph_api

# Or mount sources for dev (hot reload within container)
# In docker-compose.yml under dev_graph_api.volumes add:
#   - ./developer_graph:/app/developer_graph:ro
# Then restart the service
```

Neo4j Browser:
- http://localhost:7474 (default creds `neo4j/password` unless overridden)

API:
- http://localhost:8080/docs

---

## Roadmap

### ✅ Phase 1: Core Implementation (COMPLETED)
- ✅ Complete Git integration with commit parsing and file tracking
- ✅ Comprehensive API with temporal endpoints
- ✅ Neo4j schema with temporal relationships
- ✅ Full frontend with Sigma.js visualization
- ✅ Sprint mapping and evolution tracking
- ✅ Docker containerization and networking

### 🔄 Phase 2: Standalone Migration (IN PROGRESS)
- 🔄 Extract services from main application
- 🔄 Configure standalone deployment
- 🔄 Update CORS and environment configuration
- 🔄 Test standalone API functionality

### 📋 Phase 3: UI Extraction (PLANNED)
- 📋 Create standalone Next.js application
- 📋 Extract frontend components
- 📋 Update API configuration
- 📋 Remove from main application

### 🚀 Phase 4: Enhanced Features (FUTURE)
- 🚀 Remote repository cloning support
- 🚀 Enhanced document parsing and chunking
- 🚀 Cross-sprint evolution improvements
- 🚀 Performance optimization and caching
- 🚀 Export/import capabilities
- 🚀 CI/CD integration for graph updates

### 🎯 Phase 5: Production Readiness (FUTURE)
- 🎯 Access control and authentication
- 🎯 Graph snapshot and backup
- 🎯 Monitoring and alerting
- 🎯 Documentation and user guides

---

## Risks & Mitigations

### Performance Risks
- **Large Repository History**: Git history can be extensive → Mitigation: Bounded commit windows, configurable limits, lazy loading
- **Neo4j Query Performance**: Complex temporal queries can be slow → Mitigation: Proper indexing, query optimization, pagination
- **Frontend Rendering**: Large graphs can impact UI performance → Mitigation: Sigma.js clustering, viewport culling, progressive loading

### Data Quality Risks
- **Over-linking**: Too many relationships can create noise → Mitigation: Reason codes, confidence scores, manual validation
- **Commit Message Parsing**: Inconsistent commit messages → Mitigation: Multiple pattern matching, fallback strategies
- **File Rename Detection**: Git rename detection can miss some cases → Mitigation: Manual validation, multiple detection strategies

### Operational Risks
- **Docker Resource Usage**: Neo4j and Git operations can be resource-intensive → Mitigation: Resource limits, monitoring, scaling options
- **Data Consistency**: Concurrent updates can cause inconsistencies → Mitigation: Transaction isolation, proper locking
- **Backup and Recovery**: Graph data loss → Mitigation: Regular snapshots, export capabilities, version control

### Migration Risks
- **Service Dependencies**: Breaking changes in main application → Mitigation: Gradual migration, feature flags, rollback plan
- **API Compatibility**: Frontend breaking changes → Mitigation: Versioned APIs, backward compatibility
- **Data Migration**: Existing graph data → Mitigation: Export/import tools, data validation

---

## Appendix: Complete Code Reference Map

### Backend Services
- **Main API**: `developer_graph/api.py` - Complete FastAPI service with all endpoints
- **Git Service**: `developer_graph/git_history_service.py` - Git commit parsing and file history
- **Temporal Engine**: `developer_graph/temporal_engine.py` - Neo4j ingestion with temporal relationships
- **Sprint Mapper**: `developer_graph/sprint_mapping.py` - Sprint to commit range mapping
- **Schema Utils**: `developer_graph/schema/temporal_schema.py` - Neo4j constraints and helpers
- **Legacy Ingest**: `developer_graph/ingest.py` - Original document parsing logic

### Infrastructure
- **Docker Compose**: `docker-compose.yml` - Neo4j and API service definitions
- **API Dockerfile**: `backend/developer_graph_service/Dockerfile` - Standalone container
- **Service Entry**: `backend/developer_graph_service/main.py` - Service entry point
- **Dependencies**: `backend/developer_graph_service/requirements.txt` - Python packages

### Frontend Components
- **Main Page**: `frontend/src/app/dev-graph/page.tsx` - Complete UI with tabs and controls
- **Graph Visualization**: `frontend/src/app/dev-graph/components/EvolutionGraph.tsx` - Sigma.js graph
- **Timeline**: `frontend/src/app/dev-graph/components/TimelineView.tsx` - Commit timeline
- **Sprint View**: `frontend/src/app/dev-graph/components/SprintView.tsx` - Sprint navigation
- **Node Details**: `frontend/src/app/dev-graph/components/NodeDetailDrawer.tsx` - Node inspection
- **Search**: `frontend/src/app/dev-graph/components/SearchBar.tsx` - Graph search
- **Analytics**: `frontend/src/app/dev-graph/components/TemporalAnalytics.tsx` - Analytics views

### Documentation Structure
- **Sprint Folders**: `docs/sprints/sprint-*` - 11 sprints with comprehensive documentation
- **Planning**: `docs/sprints/planning/SPRINT_STATUS.md` - Sprint status and dates
- **Templates**: `docs/sprints/templates/` - PRD and sprint creation templates
- **Migration Doc**: `docs/DEV_GRAPH_MIGRATION.md` - This document

### Key Implementation Notes
- **Git Integration**: Fully implemented with commit parsing, file tracking, and evolution detection
- **Temporal Relationships**: Complete Neo4j schema with timestamp-based queries
- **Frontend**: Comprehensive UI with multiple views and interactive features
- **Docker**: Ready for standalone deployment with proper networking
- **API**: Complete REST API with pagination, search, and temporal filtering
