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

## Conversation Highlights (Context)

- Pain points: The in‑app Dev Graph added heavy dependencies and lag. Interaction changes (migration to Sigma.js) improved scale but removed some familiar affordances. The resulting graph felt like a tangle with limited interpretability.
- Insight: The docs folder already encodes structure and meaning (sprint folders, PRDs, READMEs, transitions, status index). A doc‑centric graph is more deterministic and interpretable.
- Direction: Split Dev Graph as a standalone pair (Neo4j + API + optional mini UI). Prefer a docs‑first graph with optional Git enrichment. Support remote Git cloning so it can run off a server repo rather than a personal machine.

References in repo:
- Dev Graph API containerization exists: `docker-compose.yml` (services `neo4j`, `dev_graph_api`).
- API code and CORS: `developer_graph/api.py`.
- Standalone Dockerfile: `backend/developer_graph_service/Dockerfile`.

---

## Goals

- Performance isolation: run Dev Graph independent of the main app.
- Deterministic, interpretable model: leverage docs structure first; layer Git semantics later.
- Portability: accept a remote `GIT_REMOTE_URL` or a bind‑mounted repo.
- Incremental evolution: start with Sprint → Doc → Chunk graph, then add cross‑sprint evolution and optional commit links.

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

## Doc‑Centric Data Model (MVP)

Node Types:
- Sprint: `{ id: 'sprint-11', number: '11', start_date?, end_date? }`
- Doc: `{ id, sprint_id, path, title, type }` where `type ∈ {PRD, README, SUMMARY, TRANSITION, PLAN, BACKLOG, MINDMAP, OTHER}` (inferred by filename heuristics)
- Chunk: `{ id, doc_id, heading_level, heading_text, ordinal, content, summary? }` (H2 as primary chunks; H3 optionally nested)
- Requirement (optional, phase 2): `{ id: 'FR-123' | 'NFR-45', title? }`

Relationships:
- `(:Sprint)-[:CONTAINS_DOC]->(:Doc)`
- `(:Doc)-[:CONTAINS_CHUNK]->(:Chunk)`
- `(:Chunk)-[:REFERENCES {anchor?}]->(:Doc|:Chunk)` for Markdown links
- `(:Chunk)-[:MENTIONS]->(:Requirement)` when content contains `\b(FR|NFR)-\d+\b`
- `(:Sprint)-[:TRANSITION_TO]->(:Sprint)` using explicit transition docs (e.g., `transition-to-sprint-0X.md`) or planning index

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

## Optional Git Enrichment (Phase 3)

When desired, add commit context without burdening the core model:
- Import `GitCommit` nodes for a bounded window.
- Link `(:Requirement)-[:IMPLEMENTS]->(:File)` and `(:GitCommit)-[:TOUCHED]->(:File)` using the existing temporal helpers (already present in codebase).
- Map chunks to commits via simple heuristics (keywords/file mentions), keep scores and provenance clear.

Edges:
- `(:Chunk|:Doc)-[:MENTIONS_FILE]->(:File)`
- `(:Chunk|:Doc)-[:RELATED_COMMIT {score}] -> (:GitCommit)`

This remains optional and isolated behind a feature flag.

---

## Extraction Pipeline (Docs‑First)

Inputs:
- Root: `docs/sprints/`
- Planning: `docs/sprints/planning/SPRINT_STATUS.md` (dates, summaries)

Steps:
1) Discover sprints: folders `sprint-*` → create Sprint nodes; optionally extract date ranges from planning index.
2) Parse each Markdown doc:
   - Title (H1), type by filename pattern, links, FR/NFR mentions.
   - Chunk at H2 (primary). Optionally nest H3.
   - Compute stable IDs and summaries (first paragraph).
3) Link references: resolve relative links across docs/sprints. Store anchors.
4) Build JSON graph: `nodes[]`, `edges[]` with explicit types and metadata.
5) (Optional) Ingest to Neo4j: one Cypher batch per type.

Output Formats:
- `docs_graph.json` (default): portable, versionable, diff‑friendly.
- Neo4j ingest (optional): Cypher queries executed via API.

Quality Gates:
- Deterministic IDs; no duplicate node IDs.
- All reference edges point to existing targets.
- Summaries never exceed N chars (configurable).

---

## API Surface (Standalone Dev Graph API)

Suggested endpoints:
- `GET /health` – service health.
- `POST /build/docs-graph` – parse docs, return JSON graph; options: `{ includeRequirements, includeCrossSprint, saveJson }`.
- `POST /ingest/neo4j` – load a provided JSON graph into Neo4j.
- `GET /graph/nodes` – list nodes by type/limit/offset (for UI pagination).
- `GET /graph/edges` – list edges by type/limit/offset.
- `GET /subgraph` – filter by sprint(s)/doc(s)/types.
- (Optional) Git endpoints (re‑use current ones) if Git enrichment is enabled.

Environment:
- `REPO_PATH` – root of repo (bind‑mounted or cloned).
- `GIT_REMOTE_URL`, `GIT_BRANCH` – optional remote clone settings (Phase 1.5).
- `CORS_ORIGINS` – comma‑separated origins for the UI.

---

## UI (Minimal, Fast)

Principles:
- Prioritize readability over physics. Tree/column layout: Sprint → Docs → Chunks.
- Simple graph overlay (optional): only Doc and Chunk nodes with straight edges.
- Search: by title, content, FR/NFR, doc type.
- Detail view: show original Markdown excerpt and links.

Controls:
- Sprint filter; doc type filter; show references; toggle requirements.

---

## Migration Plan

Phase A – Isolate Stack
1) Use only `neo4j` and `dev_graph_api` from `docker-compose.yml`.
2) Configure `REPO_PATH` to a bind‑mounted path (read‑only).
3) Expose API at `http://localhost:8080` and update CORS.

Phase B – Optional Remote Clone
1) Add an `entrypoint.sh` to the API image (clone on startup if `GIT_REMOTE_URL` is set).
2) Persist `/repo` with a Docker volume; set `REPO_PATH=/repo`.

Phase C – Separate UI (Optional)
1) Create a minimal Next app (e.g., `tools/dev-graph-ui/`) copying `frontend/src/app/dev-graph/*` primitives.
2) Point `NEXT_PUBLIC_DEV_GRAPH_API_URL` at the API; keep it out of the main app.

Cutover:
- Stop loading Dev Graph within the main app by default. Link out to the standalone UI.

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
```

Neo4j Browser:
- http://localhost:7474 (default creds `neo4j/password` unless overridden)

API:
- http://localhost:8080/docs

---

## Roadmap

Phase 1: Docs Graph MVP
- Parser that outputs `docs_graph.json`.
- API endpoint `POST /build/docs-graph` and `GET /graph/*`.
- Minimal UI: tree view with content panel; search.

Phase 2: Cross‑Sprint Evolution
- Suggest `EVOLVES_FROM` with reason codes; validation UI.
- Improve doc type heuristics and topic continuity.

Phase 3: Git Enrichment (Optional)
- Bounded commit import; file linking; requirement implementation edges.
- Time‑range filtering of edges based on commit timestamps.

Phase 4: Polishing
- Export/Import, snapshots, CI job to regenerate `docs_graph.json`.
- Access control and redaction (if needed).

---

## Risks & Mitigations

- Over‑linking across sprints → Keep suggestions opt‑in with reason codes.
- Performance in UI → Avoid physics; paginate; lazy‑load content.
- Neo4j overhead → Keep JSON‑first; ingest only on demand.

---

## Appendix: Relevant Code References

- Standalone API container: `backend/developer_graph_service/Dockerfile`
- Compose services (neo4j, dev_graph_api): `docker-compose.yml`
- Existing Dev Graph API (for reuse of patterns/CORS): `developer_graph/api.py`

