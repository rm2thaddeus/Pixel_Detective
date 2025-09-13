# Dev Graph Migration (Consolidated)

Status: Phase 2 & 3 COMPLETE; Phase 4 IN PROGRESS
Last Updated: 2025-09-03

---

## Executive Summary

We split the Dev Graph into a standalone, docs-first app to:
- Isolate performance cost from the main app.
- Rely on deterministic Markdown structure instead of fuzzy detection.
- Run anywhere by pointing at a Git repo (local or remote).

This document consolidates status, architecture, data model, performance addendum, and a concrete plan to ship a smooth, responsive experience.

---

## Current Status

Done (Phases 1–3):
- Standalone UI: Next.js app at `tools/dev-graph-ui/` with Timeline, Sprint, Analytics, and Graph views.
- API & Engine: FastAPI at `developer_graph/api.py` backed by `TemporalEngine` with Git history and Neo4j integration.
- Schema & Indexes: Constraints + indexes for commits, files, requirements, chunks, and relationship timestamps.
- Performance primitives: Windowed subgraph and commit-buckets endpoints implemented.
- Bug fixes: Import path resolutions, infinite loop prevention on viewport changes, stable memoization.

**NEW (Phase 4 - WebGL Timeline):**
- ✅ **WebGL Timeline Renderer**: CUDA-accelerated WebGL2 visualization with real-time commit progression
- ✅ **Dual Rendering Engine**: SVG (detailed) and WebGL (performance) modes with seamless switching
- ✅ **Reactive Timeline**: Real-time highlighting of current commit and connected files/edges
- ✅ **Performance Optimization**: Single WebGL context, proper resource cleanup, stable FPS
- ✅ **Progressive Data Loading**: Time-based commit filtering with adaptive node budgets
- ✅ **Interactive Controls**: Play/pause, speed control, range selection, folder filtering

In Progress (Phase 4):
- Graph performance + interactivity (progressive rendering, LoD, focus mode).
- Sprint tree view (hierarchical, worker-based layout + caching).
- Analytics wired to real backend metrics.

---

## Architecture

- UI (Next.js): `tools/dev-graph-ui/`
  - `src/app/dev-graph/complex/page.tsx`: main composite screen.
  - `src/app/dev-graph/timeline/page.tsx`: **NEW** - Interactive timeline with dual rendering engines.
  - `components/BiologicalEvolutionGraph.tsx`: graph visualization.
  - `components/WebGLEvolutionGraph.tsx`: **NEW** - CUDA-accelerated WebGL2 timeline renderer.
  - `components/ProgressiveStructureGraph.tsx`: SVG-based detailed visualization.
  - `hooks/*`: windowed subgraph + commit buckets.
- API (FastAPI): `developer_graph/api.py` (router composition)
  - `developer_graph/app_state.py`: initializes `driver`, `engine`, and services
  - Routers under `developer_graph/routes/` (paths unchanged):
    - health_stats, nodes_relations, search, commits_timeline, sprints, graph, analytics,
      ingest, chunks, metrics, validate, admin, evolution
  - Example endpoints:
    - `GET /api/v1/dev-graph/graph/subgraph` windowed subgraph
    - `GET /api/v1/dev-graph/commits/buckets` commit density
    - `GET /api/v1/dev-graph/sprints/{number}/subgraph` sprint hierarchy
    - `GET /api/v1/dev-graph/evolution/timeline` **NEW** - Timeline data with commit progression
    - `GET /api/v1/dev-graph/subgraph/by-commits` **NEW** - Commit-scoped subgraph data
    - `POST /api/v1/dev-graph/ingest/bootstrap` bootstrap ingestion
- Engine: `developer_graph/temporal_engine.py`
  - Git + Neo4j ingest, time-bounded queries, commit bucketing
- Schema: `developer_graph/schema/temporal_schema.py`
  - Constraints and indexes for nodes; timestamp indexes for relationships

## Separation of Concerns (Backend vs Frontend)

- Backend (FastAPI + Neo4j): authoritative data and query contracts (modular routers)
  - Ingestion
    - Git temporal ingest via `TemporalEngine` (Commits, Files, TOUCHED/IMPLEMENTS, rename detection).
    - Docs/Sprints/Chunks ingest available via scripts (`developer_graph/enhanced_ingest.py`, `developer_graph/enhanced_git_ingest.py`).
    - Add API triggers to run enhanced ingests from UI (POST endpoints), so Sprints/Docs/Chunks are populated without manual scripts.
  - Preferred query endpoints
    - `GET /api/v1/dev-graph/graph/subgraph?from_timestamp&to_timestamp&types&limit&cursor&include_counts`
    - `GET /api/v1/dev-graph/commits/buckets?granularity=day|week&from_timestamp&to_timestamp&limit`
    - `GET /api/v1/dev-graph/evolution/file|requirement`
    - `GET /api/v1/dev-graph/sprints`, `GET /api/v1/dev-graph/sprints/{number}/subgraph`
    - `GET /api/v1/dev-graph/search/fulltext?q=&label=`
  - Performance & pagination
    - Move to keyset pagination for subgraph (cursor = `{last_ts, last_commit}`) to avoid deep `SKIP`.
    - Keep relationship `timestamp` indexes and label-constrained patterns.
    - TTL cache (~60s) for hot windowed subgraphs.
  - Telemetry & health
    - `/api/v1/dev-graph/health`, `/api/v1/dev-graph/metrics` expose `{avg_query_time_ms, cache_hit_rate, memory_usage_mb}`.
  - Optional
    - Persist server-computed coordinates (`x/y`) to stabilize layouts across sessions.

- Frontend (Next.js UI): rendering, interaction, progressive usage of backend
  - Data usage
    - Default to `/graph/subgraph` + pagination; use commit buckets for timeline density.
    - Avoid legacy `/nodes` and `/relations` at large scale except for debug.
  - Rendering
    - Sigma.js + Graphology with level-of-detail reducers: hide labels/edges at low zoom; show on hover/zoom-in.
    - Progressive hydration, batch insertions; worker-based clustering/layout for large graphs.
    - Two modes per PRD: Structure (force-directed) and Time (time‑radial) with deterministic coordinates.
  - Views
    - Timeline: canvas + bucketed density; range selection updates subgraph.
    - Sprint Tree: hierarchical Sprint→Docs→Chunks→Requirements via sprint subgraph endpoint.
    - Analytics: wire real `/analytics/*` endpoints; remove mock data.

## Backend Additions Proposed (Phase 4)

- API triggers for enhanced ingests
  - `POST /api/v1/dev-graph/ingest/docs` → run `enhanced_ingest.py`
  - `POST /api/v1/dev-graph/ingest/git/enhanced` → run `enhanced_git_ingest.py`
- Keyset pagination for `/graph/subgraph`
  - Cursor carries `{last_ts, last_commit[, rel_type]}`; order by `(r.timestamp DESC, r.commit)`.
- Telemetry endpoint
  - `GET /api/v1/dev-graph/metrics` → `{avg_query_time_ms, cache_hit_rate, memory_usage_mb}`.
- Optional
  - Temporal snapshot: `GET /api/v1/dev-graph/temporal/state?timestamp=...`
  - Complexity metrics: `GET /api/v1/dev-graph/metrics/complexity?from&to`
  - Node evolution detail: `GET /api/v1/dev-graph/nodes/{id}/evolution`

## Frontend Additions Proposed (Phase 4)

- Prefer `/graph/subgraph` everywhere; stream pages and merge progressively.
- Wire Timeline to commit buckets and add range→subgraph preview.
- Sprint Tree view consumes `sprints/{number}/subgraph` and caches layouts.
- Use workers for Louvain and FA2 when N exceeds thresholds; keep LoD reducers enabled.

---

## WebGL Timeline Architecture

### Rendering Engine Comparison

| Feature | SVG Mode | WebGL Mode |
|---------|----------|------------|
| **Performance** | ~100-500 nodes | ~2000+ nodes |
| **Interactivity** | Full D3.js zoom/pan | Basic highlighting |
| **Detail Level** | High (labels, tooltips) | Medium (size/color encoding) |
| **Memory Usage** | DOM-based | GPU buffers |
| **Use Case** | Analysis, debugging | Overview, progression |

### WebGL Implementation Details

**Core Components:**
- `WebGLEvolutionGraph.tsx`: Main WebGL2 renderer with CUDA-like processing simulation
- Single WebGL context with proper resource lifecycle management
- Reactive data updates via refs (no re-initialization on data changes)
- Dual shader programs: point sprites for nodes, line segments for edges

**Performance Optimizations:**
- Adaptive node budgets based on device capabilities (memory, CPU cores, viewport)
- Progressive data loading with time-based filtering
- GPU buffer management with proper cleanup
- Stable FPS calculation and performance monitoring

**Timeline Features:**
- Real-time commit progression with visual highlighting
- Edge brightness boosting for connected nodes
- Size/color encoding based on file types and commit activity
- Range selection with live filtering

---

## Data Model (Snapshot)

Nodes:
- Sprint: `{ number, start_date, end_date, commit_range }`
- Document: `{ path, title?, type?, last_modified_commit? }`
- Chunk: `{ id: path#slug-ordinal, heading, level, ordinal, content_preview, length, mentions[] }`
- Requirement: `{ id: FR-..|NFR-.., title?, author?, date_created?, goal_alignment?, tags? }`
- GitCommit: `{ hash, message, author, timestamp, files_changed[] }`
- File: `{ path, language?, last_modified_commit? }`

Relationships:
- Commit→File: `(:GitCommit)-[:TOUCHED {change_type, timestamp}]->(:File)`
- Requirement→File: `(:Requirement)-[:IMPLEMENTS {commit, timestamp}]->(:File)`
- Requirement evolution: `(:Requirement)-[:EVOLVES_FROM {commit, diff_summary, timestamp}]->(:Requirement)`
- File refactor: `(:File)-[:REFACTORED_TO {commit, refactor_type, timestamp}]->(:File)`
- Sprint→Document: `(:Sprint)-[:CONTAINS_DOC]->(:Document)`
- Document→Chunk: `(:Document)-[:CONTAINS_CHUNK]->(:Chunk)`
 - Chunk mentions: `(:Chunk)-[:MENTIONS]->(:Requirement)`; Sprint→File planning links use `MENTIONS` (structural)
- Cross-links: `(:Chunk)-[:REFERENCES {anchor?}]->(:Document|:Chunk)`
- Sprint transitions: `(:Sprint)-[:TRANSITION_TO]->(:Sprint)`

ID strategy:
- Sprint: `sprint-N`
- Document: normalized path
- Chunk: `doc_path#slug-ordinal` (stable)

---

## Performance Addendum (Phase 4)

Key issues observed:
- Graph rendering warnings and instability from invalid/missing coordinates under large loads.
- Timeline rendering using heavy list components instead of lightweight visualization.
- Missing progressive rendering/LoD; edges and labels too dense at initial zoom.
- Sprint view not hierarchical; analytics tab using mock data.

Mitigations implemented:
- Windowed subgraph endpoint with pagination and type filtering.
- Commits bucket endpoint for fast timeline density.
- Windowed subgraph now returns node labels to improve UI typing/color.
- Deterministic coordinates + validation on the client; robust fallbacks.
- Optional layout/clustering now gated by size to avoid O(N²) blow-ups.
- Progressive graph rendering: labels on hover or above zoom threshold; edges hidden at very low zoom; optional light edges; focus mode dims non‑neighbors.
- Sprint Hierarchy: new sprint subgraph endpoint and nested tree view (Sprint→Docs→Chunks→Requirements).
- Canvas-based timeline with range selection; hooks to update subgraph window.

Planned next steps:
- Progressive edge/label rendering (zoom-aware), focus/dim neighborhood interactions.
- Worker-based DAG layout for sprint tree view; cache per sprint.
- Real analytics endpoints wired to UI; remove mock data.

SLOs:
- <1s first paint for a 30‑day window.
- >45 FPS pan/zoom on typical project graphs.
- <300ms for timeline bucket queries; <250ms subgraph preview after range selection.

---

## API Quick Reference

- `GET /api/v1/dev-graph/graph/subgraph?from_timestamp&to_timestamp&types&limit&cursor`
  - Returns nodes/edges within a time window with pagination + perf metrics.

- `GET /api/v1/dev-graph/commits/buckets?granularity=day|week&from_timestamp&to_timestamp&limit`
  - Returns commit density buckets with query timing.

- `GET /api/v1/dev-graph/sprints/{number}/subgraph`
  - Returns hierarchical sprint subgraph (Sprint→Docs→Chunks→Requirements).



- `GET /api/v1/analytics/activity?from_timestamp&to_timestamp`
  - Returns commit_count, file_changes, unique_authors for the window.

- `GET /api/v1/analytics/graph?from_timestamp&to_timestamp`
  - Returns node counts by label, edge counts by type (time-bounded on edge timestamps).

- `GET /api/v1/analytics/traceability?from_timestamp&to_timestamp`
  - Returns requirement traceability metrics (implemented, unimplemented, avg files per requirement).
- `GET /api/v1/dev-graph/nodes|relations|commits|sprints`, `GET /api/v1/dev-graph/search?q=...`
  - Core listing and search utilities.

- `POST /api/v1/dev-graph/ingest/bootstrap`
  - One-button ingestion: schema, docs/chunks, commits, sprint mapping, relationship derivation

---

## Operations

Docker (API + Neo4j):
- `docker compose up -d neo4j dev_graph_api`
- API: http://localhost:8080/docs • Neo4j: http://localhost:7474

UI (standalone):
- `cd tools/dev-graph-ui && npm i && npm run dev`
- `NEXT_PUBLIC_DEV_GRAPH_API_URL=http://localhost:8080`

Environment:
- `REPO_PATH` for API to target a repo (or `GIT_REMOTE_URL` + `GIT_BRANCH` for remote clone flow).
- `CORS_ORIGINS` to allow UI origin.
- `NEXT_PUBLIC_DEV_GRAPH_DEBUG=1` to enable UI debug logging (dev only).

UI controls (Graph tab):
- Light edges: reduces visual weight at medium/low zoom.
- Focus mode: dims non-neighbors on hover to improve readability.
- Viewport-only: hides offscreen nodes to keep frame rates high.
- Clustering: enable Louvain for small graphs (auto-skipped for large graphs).

---

## Acceptance Criteria

- Stable graph rendering without coordinate warnings on 30‑day window datasets.
- Smooth interactions: hover labels only, dim non-neighbors on focus, quick filters.
- Timeline: bucketed dots/bars with range brush updating the subgraph instantly.
- Sprint view: hierarchical tree with collapse/expand; cross‑sprint edges toggle off by default.
- Analytics: real metrics surfaced (activity, graph, traceability, quality).

---

## Open Risks & Mitigations

- Very large graphs: rely on windowed queries; skip client layout > N nodes; add Redis/LRU caching server-side if needed.
- Label/type consistency: include labels in subgraph responses to improve UI coloring; current UI falls back to heuristics.
- Noise in edges: use reducers and zoom thresholds; expose edge weight toggle.

---

## Appendix: Indexes & Constraints (Neo4j)

Applied:
- Unique: `(:GitCommit.hash)`, `(:File.path)`, `(:Requirement.id)`, `(:Chunk.id)`
- Property indexes: `(:GitCommit.timestamp)`, `(:Commit.timestamp)`, `(:File.path)`, `(:Requirement.id)`, `(:Chunk.id)`
- Relationship property indexes on `timestamp` for `TOUCHED`, `IMPLEMENTS`, `EVOLVES_FROM`, `REFACTORED_TO`, `DEPRECATED_BY`

Recommendation:
- Include `labels(a)`/`labels(b)` in windowed subgraph queries to enrich node typing in UI.

---

References:
- UI: `tools/dev-graph-ui/`
- API: `developer_graph/api.py`
- Engine: `developer_graph/temporal_engine.py`
- Schema: `developer_graph/schema/temporal_schema.py`
