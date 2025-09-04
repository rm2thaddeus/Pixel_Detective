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

In Progress (Phase 4):
- Graph performance + interactivity (progressive rendering, LoD, focus mode).
- Timeline redesign (canvas-based with range brush and subgraph preview).
- Sprint tree view (hierarchical, worker-based layout + caching).
- Analytics wired to real backend metrics.

---

## Architecture

- UI (Next.js): `tools/dev-graph-ui/`
  - `src/app/dev-graph/complex/page.tsx`: main composite screen.
  - `components/EvolutionGraph.tsx`: Sigma.js graph visualization.
  - `components/EnhancedTimelineView.tsx`: canvas timeline using bucketed commits.
  - `hooks/useWindowedSubgraph.ts`: windowed subgraph + commit buckets.
- API (FastAPI): `developer_graph/api.py`
  - `GET /api/v1/dev-graph/graph/subgraph` windowed subgraph
  - `GET /api/v1/dev-graph/commits/buckets` commit density
  - `GET /api/v1/dev-graph/nodes|relations|search|commits|sprints` core queries
  - `POST /api/v1/dev-graph/ingest/recent` ingestion helper
- Engine: `developer_graph/temporal_engine.py`
  - Git + Neo4j ingest, time-bounded queries, commit bucketing.
- Schema: `developer_graph/schema/temporal_schema.py`
  - Constraints and indexes for nodes; timestamp indexes for relationship types.

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
- Chunk mentions: `(:Chunk)-[:MENTIONS]->(:Requirement)`
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

- `POST /api/v1/dev-graph/ingest/recent?limit=100`
  - On-demand ingestion of recent commits.

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
