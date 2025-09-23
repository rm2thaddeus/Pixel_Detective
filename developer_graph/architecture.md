Developer Graph API - Architecture Overview
===========================================

Status
------
- Last updated: 2025-09-24 (addendum merged into main architecture; original final recorded 2025-09-23)
- Owners: Dev Graph Platform Team
- Repository root: `C:\Users\aitor\OneDrive\Escritorio\Vibe Coding`

Quick Start Commands
--------------------

```bash
# API only (from repo root)
python -m uvicorn developer_graph.api:app --reload --host 0.0.0.0 --port 8080

# Complete stack
./start_app.ps1

# Frontend only (from tools/dev-graph-ui)
npm run dev
```

System Overview
---------------

The Developer Graph platform fuses Git history, documentation, sprint planning, and semantic chunking into a time-aware knowledge graph. It is composed of:

- **Backend API (FastAPI)** - routers in `developer_graph/routes/*` exposing graph operations, analytics, ingestion, and admin endpoints.
- **Graph Persistence (Neo4j 5.x)** - temporal schema with strict uniqueness constraints, timestamped relationships, fulltext, and vector indexes.
- **Ingestion Services**
  - `ParallelIngestionPipeline` for commit extraction and batched writes.
  - `ChunkIngestionService` for document/code discovery and chunk creation.
  - `UnifiedIngestionPipeline` combining reset, commits, chunks, sprint mapping, relationship derivation, and optional embeddings behind `/api/v1/dev-graph/ingest/unified`.
- **Shared Services (`app_state.py`)** - GitHistoryService, TemporalEngine, SprintMapper, RelationshipDeriver, ChunkIngestionService, EmbeddingService, ParallelIngestionPipeline.
- **Frontend (Next.js 15.5)** - biological evolution graphs, timelines, and analytics dashboards located under `tools/dev-graph-ui`.

API Surface (Current)
---------------------

- `GET /api/v1/dev-graph/health`, `GET /api/v1/dev-graph/metrics` - liveness and baseline metrics.
- Ingestion endpoints:
  - `POST /api/v1/dev-graph/ingest/unified` plus `/status`, `/stop`, `/report` for progress tracking.
  - `POST /api/v1/dev-graph/ingest/optimized` - experimental high-parallel path (see `developer_graph/routes/optimized_ingest.py:639`).
  - `POST /api/v1/dev-graph/ingest/unlimited` - queue-backed variant for no-limit processing.
  - `POST /api/v1/dev-graph/ingest/bootstrap`, `/bootstrap/lean`, `/bootstrap/complete` - legacy bootstraps covering schema + commits + derivation.
  - `POST /api/v1/dev-graph/ingest/chunks` - direct chunking via `ChunkIngestionService` with optional targeted `files`.
  - `POST /api/v1/dev-graph/ingest/recent`, `/git/enhanced`, `/git/batched`, `/temporal-semantic`, `/parallel` - commit-focused ingestion choices.
- Graph queries & analytics: search, sprint, timeline, evolution, quality, admin routes in `developer_graph/routes/*`.

Data Model (Temporal Semantic)
------------------------------

- **Nodes** - `GitCommit`, `File`, `Document`, `Chunk`, `Requirement`, `Sprint`, with derived attributes (language, type, UID).
- **Relationships** - timestamped `TOUCHED`, `IMPLEMENTS`, `EVOLVES_FROM`, `REFACTORED_TO`, `CONTAINS_CHUNK`, `MENTIONS`, sprint inclusion edges, and optional dependency links.
- **Indexes & Constraints** - unique constraints on core node identifiers; range indexes on timestamps; fulltext indexes for search; optional vector index on `Chunk.embedding` for semantic similarity.

Ingestion Architecture
----------------------

1. **Stage 1 - Reset & Schema**
   - Optional graph wipe followed by schema application (`TemporalEngine.apply_schema`).
   - All constraint/index creation is idempotent; noisy but harmless Neo4j notices are expected after the first run.
2. **Stage 2 - Commit Ingestion**
   - `ParallelIngestionPipeline.ingest_commits_parallel()` pulls Git history with `git --name-status`, fanning out to worker threads for diff parsing, and writes commits in 200-size batches.
3. **Stage 3 - Repository Discovery & Chunking**
   - `ChunkIngestionService.discover_all_files()` walks the repo once, normalizing Windows paths to POSIX and categorising into documents, code, config, data, and other files.
   - `ChunkIngester` reads files, generates Markdown or code chunks, and merges them into Neo4j with consistent repo-relative paths.
   - Limits are optional; omitting them processes *all* discovered files and logs the effective limit (`no limit`, `0 (skip)`, etc.).
4. **Stage 4 - Chunk Summary**
   - Reuses cached discovery results to report code ingestion metrics without reprocessing files.
   - Note: In current code this stage is a summary only; all chunking work happens in Stage 3.
5. **Stage 5 - Sprint Mapping**
   - `SprintMapper.map_all_sprints()` imports sprint windows and links documents/commits.
6. **Stage 6 - Relationship Derivation**
   - `RelationshipDeriver` applies heuristic strategies (commit messages, doc mentions, dependency analysis) with accumulated confidences.
7. **Stage 7 - Embeddings (Optional)**
   - `EmbeddingService` can populate vector embeddings for chunks; defaults to off to keep ingestion latency manageable.

Reality Check vs Code
---------------------

- `UnifiedIngestionPipeline` sets `total_stages = 6` even though seven stages execute (see `developer_graph/routes/unified_ingest.py:51`); adjust or merge Stage 3+4 when reporting.
- Chunk writers diverge: `ChunkIngestionService` persists `Chunk.text`/`kind`, while parallel/optimized paths also set `c.content` and alternate relationships (e.g., `BELONGS_TO`). Standardise on `text` as the primary payload and `kind = doc|code`.
- Relationship derivation expects `(:File)-[:IMPORTS]->(:File)` edges; none are created yet, so DEPENDS_ON warnings are expected until an import graph exists.

Path Normalisation & Consistency
--------------------------------

- Repo root resolved once (`ChunkIngestionService.repo_root`).
- All stored paths use forward slashes relative to the repo root; ingestion gracefully handles relative or absolute inputs during manual runs.
- Failures during chunk creation are logged with file path plus exception for triage.

Performance Snapshot (2025-09-23)
---------------------------------

| Stage                                 | Metric / Output                                     | Result |
|---------------------------------------|------------------------------------------------------|--------|
| Commit extraction (Stage 2)           | 273 commits parsed                                   | 0.60 s |
| Commit processing (Stage 2)           | 273 commits with 8 workers                           | 54.67 s |
| Commit writes (Stage 2)               | 273 commits written (200 + 73 batch)                 | 56.91 s total |
| Document ingestion (Stage 3)          | 172 documents -> 2,627 chunks                        | 42m 16s |
| Code ingestion (Stage 3)              | 440 code files -> 13,234 chunks                      | 42m 16s |
| Sprint mapping (Stage 5)              | 12 sprints                                           | 12.6 s |
| Relationship derivation (Stage 6)     | 482 relationships (warning: missing `DEPENDS_ON`)    | 3.4 s |
| Unified pipeline (Stage 1-6)          | Final graph: 18,840 nodes / 21,254 relationships     | 2,611 s |

> Observation: chunk creation dominates wall-clock time (~42 minutes) versus <1 minute for commit ingestion. The total unified run (reset through derivation) completes in ~43.5 minutes.

Operational Audit
-----------------

Completed:
- Unified ingestion endpoint uses optional limits and reports discovery vs. selected vs. processed counts.
- Path handling consolidated across pipelines; Neo4j now stores consistent repo-relative POSIX paths.
- Stage logs and final report include discovery summaries, sample paths, per-stage durations, and final graph totals.

Needs Improvement (Tracked)
---------------------------

- Stage accounting mismatch between implemented stages and reported `total_stages` in `UnifiedIngestionPipeline`.
- Chunk ingestion remains single-threaded; batching with worker/process pools should trim the 42-minute runtime.
- Chunk schema is inconsistent across writers (`text` vs `content`, varying relationships); normalise for downstream consumers.
- Long-running chunking lacks streaming progress feedback; add job IDs and status feeds to avoid timeouts.
- Relationship derivation warns on DEPENDS_ON because no import graph exists yet; need import extraction or guardrails.

Streamlining Plan (Next Steps)
------------------------------

Implementation Update (October 2025)
-----------------------------------

- Unified ingestion now issues job identifiers, exposes `/status/{job_id}` lookups, and stores per-stage telemetry so long-running runs can stream progress without holding the request open.
- Incremental manifest tracking writes a snapshot with repo hash, size, mtime, and the latest commit hash; Stage 2 stores the newest commit so delta runs only touch updated files while the cleanup pass deletes orphan chunks/files.
- Document/code chunking runs through a `ProcessPoolExecutor` with batched UNWIND writes, normalized chunk payload (`text`, `content`, `kind`), and logs the top slow documents/code files for visibility.
- Import graph derivation now generates `(:File)-[:IMPORTS]->(:File)` edges for Python/TS/JS and only emits DEPENDS_ON when import evidence exists.
- `/ingest/unified` accepts `profile=full|delta|quick`, optional `subpath` scoping, and returns the `job_id` alongside results; skip paths are now tracked per stage.
- `/metrics` reports stage throughput (e.g., Stage 3 chunks/min vs target), surfaced alerts when throughput drops, and surfaces the slowest files from the most recent job.

1. **Unify Chunk Schema and Writers**
   - Standardise `Chunk` payload (`id`, `kind`, `text`, `file_path`, `heading`, `section|symbol`, `span`, `length`).
   - Ensure all writers set `text` and `kind`; write `content` in parallel for one release before removing it.
   - Normalise relationships to `(:Document)-[:CONTAINS_CHUNK]->(:Chunk)` and `(:Chunk)-[:PART_OF]->(:File)`.

2. **Incremental Ingestion (Manifest + Delta)**
   - Generate a manifest (repo-relative path, size, mtime, SHA-1) using `git ls-files` plus hashing.
   - Compare manifests to skip unchanged files and delete orphaned chunks/files.
   - Extend derivation watermarks to track last ingested commit for incremental runs.

3. **True Parallel Chunking**
   - Wrap `ChunkIngestionService` work in a `ProcessPoolExecutor` with bounded queues and batched UNWIND writes (500-1,000 chunks/transaction).
   - Preserve idempotent MERGE semantics.

4. **Import Graph for DEPENDS_ON**
   - Parse imports/includes for Python/TS/JS during chunking to create `(:File)-[:IMPORTS]->(:File)`.
   - Gate DEPENDS_ON derivation until import edges exist to silence warnings.

5. **Job Control and Streaming Progress**
   - Introduce `ingestion_job_id`, allow `/status/{job_id}` polling or SSE, and persist job snapshots in memory or a lightweight store.

6. **Profiles and Scoping**
   - Add `profile=full|delta|quick` and optional `subpath` filters to `/ingest/unified`.

7. **Observability and SLOs**
   - Emit per-stage throughput to `/metrics` and alert when Stage 3 drops below target; log top-N slowest files.

Phased Implementation
---------------------

- **Phase A (quick wins, 1-2 days)**
  - Fix `total_stages` reporting to 7 (or merge Stage 3+4) and update the final report.
  - Standardise chunk writes (`text`, `kind`) while keeping `content` as a transitional alias.
  - Guard DEPENDS_ON derivation when no `IMPORTS` edges exist.
  - Align timeline endpoint caps to the PRD (`limit=5000`) where safe.

- **Phase B (incremental + parallel, 1-2 sprints)**
  - Ship manifest + delta planner and store last-run manifest (Neo4j node or JSON artifact).
  - Move chunking to `ProcessPoolExecutor` with bounded queues and batched UNWIND writes.
  - Add job IDs and profile/subpath arguments to unified ingestion.
  - Build minimum viable import graph for Python/TS to unlock DEPENDS_ON.

- **Phase C (quality + embeddings, ongoing)**
  - Run background embeddings with quotas/backoff and stamp `embedding_ts`.
  - Add data quality gate that fails the unified run when orphan/timestamp ratios breach thresholds.

Acceptance Metrics
------------------

- Stage 3 throughput ≥ 600 chunks/min with 8 workers on this repo.
- Delta runs at least 10× faster than full ingest when <10% of files change.
- Unified report node/relationship totals within ±1% of Neo4j counts.
- No DEPENDS_ON warnings when imports are absent; counts >0 once import graph lands.

Graph Quality (Connectivity & Clustering)
----------------------------------------

Baseline (Sept 2025 UI snapshot)
- Clustering coefficient ~ 0.017 (goal: >0.15 for tighter local communities).
- Average path length ~ 11.7 (goal: <8 for faster traversal).
- Network density ~ 1.7% (goal: target 4-6% without overwhelming visualization).
- Modularity ~ 0.259 (goal: >0.4 for well-separated thematic clusters once connectivity improves).

Connectivity Improvement Tactics
- **Derive additional edges:**
  - Co-change: link files frequently touched in the same commit window to surface implicit architectural ties (TOUCHED aggregation).
  - Static imports: persist (:File)-[:IMPORTS]->(:File) for Python/TS/JS and propagate to requirements (ties in with DEPENDS_ON work item).
  - Semantic chunk links: run cosine similarity on embeddings to create (:Chunk)-[:RELATES_TO]->(:Chunk) above a confidence threshold.
  - Doc cross-references: detect [link](...) syntax and inline references to connect documents and requirements.
- **Strengthen requirement coverage:** backfill (:Requirement)-[:IMPLEMENTS]->(:File) via doc chunk patterns, issue IDs, and PR metadata; enrich with sprint-to-requirement edges.
- **Normalize orphan cleanup:** incremental runs should delete stale nodes/relationships so density gains reflect real structure.
- **Weight & filter:** maintain relationship weights (co-change frequency, import strength, semantic score) to support UI sliders and avoid noise.

Metric Feedback Loop
- Instrument /api/v1/dev-graph/quality to capture these metrics after each unified run; persist a history for regression tracking.
- Alert when clustering drops >10% or path length grows >15% relative to a trailing three-run average.
- Expose an admin endpoint to recompute modularity/density on demand after schema changes.

Performance Improvement Ideas (Legacy Reference)
-----------------------------------------------

1. **Parallel Chunk Ingestion**
   - Use a worker pool (ThreadPoolExecutor or ProcessPool for CPU-bound parsing) to ingest documents/code concurrently.
   - Aggregate per-file results and execute batched Neo4j writes to avoid excessive transactions.

2. **Incremental Chunking Cache**
   - Track file hashes (e.g., SHA-1) and skip unchanged files between runs, drastically reducing ingestion for stable repos.

3. **Streaming Chunk Writes**
   - Replace per-chunk write transactions with batched UNWIND statements to lower transaction overhead.

4. **Hardware Acceleration**
   - GPU acceleration applies mainly to embedding generation; ingestion itself is IO/CPU-bound. Profiling may reveal hotspots suitable for Cython or Rust extensions.
   - Consider memory-mapped file reading for large docs or codebases to reduce Python-level overhead.

5. **Monitoring & Alerts**
   - Expose ingestion duration metrics via `/metrics` and alert when stages exceed target thresholds.

Roadmap: Advanced Relationship Derivation
-----------------------------------------

- Evaluate ML-based semantic similarity (e.g., cross-encoder or graph neural nets) to derive higher-confidence `IMPLEMENTS`/`DEPENDS_ON` edges.
- Integrate lightweight LLM summarisation for commit-to-requirement mapping.
- Next research milestones are tracked in `docs/sprints/sprint-11/DEV_GRAPH_TEMPORAL_SEMANTIC_PRD.md` under "ML Relationship Enhancements".

Operational Notes & Environment
-------------------------------

- Core env vars: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `REPO_PATH`, optional `CORS_ORIGINS`.
- Logs: stdout + `dev_graph_api.log`; keep log rotation plan for long-running ingestion.
- Supporting scripts: `verify_docs.py` for document sanity checks, `fix_data_quality.py` for ad hoc cleanups.

Extensibility Guidelines
------------------------

- Add routers under `developer_graph/routes/` and include them in `developer_graph/api.py`.
- Shared services are available via `developer_graph.app_state` to avoid circular initialisation.
- Version breaking API changes by adding `/api/v2/*` endpoints to safeguard frontend integrations.
- For new visualisations, place components in `tools/dev-graph-ui/src/app/dev-graph/components/` and leverage D3 + Chakra UI conventions.

Change Log
----------
- 2025-09-24: Integrated architecture addendum (original final 2025-09-23) into main doc; added API surface and streamlining plan with phased rollout.
- 2025-09-23: Documented unified ingestion architecture, updated performance metrics with 43.5-minute pipeline run, and recorded optimisation backlog.
- 2025-09-15: Initial Sprint 11 biological evolution UI architecture review (superseded).

Reality Check — Latest Run
--------------------------

- Full reset performed prior to validation run:
  - Removed 18,840 nodes and 21,254 relationships.
- Unified ingestion (no overrides) completed all 7 stages with high quality:
  - Stage 3 (documents): 172 documents processed; 2,620–2,627 chunks; 0 errors.
  - Stage 4 (code): 440+ code files processed; 14,089 total chunks; 0 errors.
  - Commits: 274 total; Sprints mapped: 12; Derived relationships: 482.
  - Final graph: 17,042 nodes, 21,062 relationships. Quality score: 99.9/100.
  - End-to-end duration: ~104 seconds on this repo.
- Fixes applied during validation:
  - Added missing pipeline helpers in `UnifiedIngestionPipeline`:
    - `_check_for_stop`, `_enter_stage`, `_publish_stage`.
  - Resolved `latest_commit` reference by surfacing most-recent commit from
    parallel commit ingestion and threading it into later stages (delta +
    derivation watermarks).
  - Restarted API, re‑ran unified ingestion, confirmed expected totals.
