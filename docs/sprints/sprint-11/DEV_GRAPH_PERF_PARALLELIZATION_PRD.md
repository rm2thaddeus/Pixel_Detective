Title: Dev Graph Performance & Parallelization PRD (Sprint 11)

Owner: Dev Graph
Status: Draft
Target: First-paint < 300ms for initial subgraph page; no main-thread long tasks > 50ms during hydration on typical datasets.

1) Overview
- Goal: Improve perceived and actual performance of the Developer Graph by parallelizing CPU-heavy client tasks, reducing synchronous blocking, and trimming backend round-trips. Deliver progressive, interactive loading with stable layouts.
- Scope: Frontend (web workers for layout/clustering, progressive hydration), Backend (optional counts, in-memory cache), Ingest (parallel extract, batched writes).
- Non-Goals: Full GPU layout implementation; switching graph renderer; major schema changes.

2) Current Behavior & Bottlenecks (with code refs)
- Client-side clustering runs on UI thread:
  - `frontend/src/components/explore/KnowledgeGraph.tsx:58` calls `louvain.assign(graph, { resolution: 1.0 });` synchronously.
- Large eager hydration on mount:
  - Fetch: `frontend/src/components/explore/KnowledgeGraph.tsx:21` requests `/api/v1/dev-graph/graph/subgraph` with `limit: 1000`.
  - Graph rebuild: `frontend/src/components/explore/KnowledgeGraph.tsx:33` clears, `:35-46` adds nodes, `:48-54` adds edges synchronously.
- Renderer work on main thread:
  - `frontend/src/components/explore/KnowledgeGraph.tsx:76` instantiates Sigma on main thread.
- Backend performs counts + distinct pass before main fetch:
  - Endpoint: `developer_graph/api.py:520` → `_engine.get_windowed_subgraph`.
  - Engine counts edges/nodes before fetching page: see `developer_graph/temporal_engine.py:300` (count query assembled just above main query; exact lines in Design below).
- Ingest is strictly sequential per commit:
  - `developer_graph/temporal_engine.py:36-79` loops commits, parses content, and writes within a single transaction per commit.

3) Requirements
- Progressive hydration: First page of data loads fast, graph is interactable while subsequent pages stream.
- Offload CPU-heavy tasks: Community detection and layout must run off the main thread when N > threshold.
- Stable coordinates: Use server-provided `x/y` when present; otherwise incremental ForceAtlas2 in a worker.
- Backend tunables: Allow skipping counts; provide small in-memory TTL cache for repeated subgraph queries.
- Ingest throughput: Parallelize CPU-bound extraction; batch Neo4j writes to reduce transaction overhead.

4) Proposed Changes

4.1 Frontend: Progressive Hydration and Web Workers
- Progressive fetch:
  - Change initial request to `limit=250` and loop using `pagination.next_cursor` from `/api/v1/dev-graph/graph/subgraph`.
  - Apply nodes/edges in batches with `requestIdleCallback` or microtasks between batches to avoid long tasks.
  - References to update:
    - Fetch site: `frontend/src/components/explore/KnowledgeGraph.tsx:21-28`.
    - Add batching around node/edge insertion: `frontend/src/components/explore/KnowledgeGraph.tsx:35-54`.

- Web worker for community detection:
  - Create `frontend/src/workers/louvain.worker.ts` to run `graphology-communities-louvain` on a transferable representation (nodes/edges list) and return `{ nodeId -> community }`.
  - Apply results in batched `graph.updateEachNodeAttributes` calls on the main thread.
  - Replace `louvain.assign(...)` at `frontend/src/components/explore/KnowledgeGraph.tsx:58` with worker orchestration.

- Web worker for layout (optional, thresholded):
  - Create `frontend/src/workers/layout.worker.ts` using `graphology-layout-forceatlas2` (worker mode) to compute incremental positions. Post positions every N iterations; apply to the Sigma graph incrementally.
  - Only trigger when > X nodes lack coordinates (e.g., X=200) and user opts-in or a toggle is set.

- Rendering tweaks:
  - Limit label rendering to hover or to ≤ 1,000 nodes (Sigma option at `frontend/src/components/explore/KnowledgeGraph.tsx:76`).
  - Defer hide/show logic in focus mode to a rAF cycle.

4.2 Backend: Optional Counts + In-memory Cache
- Add `include_counts: bool = Query(True)` to `/api/v1/dev-graph/graph/subgraph`.
  - When `False`, skip the preliminary count query; directly return first page and pagination cursor.
  - File references:
    - Endpoint signature: `developer_graph/api.py:521-543`.
    - Engine function: `developer_graph/temporal_engine.py:260` (start of `get_windowed_subgraph`).
- Add an in-process LRU/TTL cache (e.g., 60s) keyed by `(from,to,types,limit,cursor,include_counts)`.
  - Implement within `TemporalEngine.get_windowed_subgraph` with a module-level cache or a small `functools.lru_cache` + manual TTL wrapper.
  - References:
    - Add cache near top of file or within class.
    - Wrap the final return object.

4.2.1 Backend Contracts & Telemetry (Separation of Concerns)
- Prefer `/api/v1/dev-graph/graph/subgraph` for all graph data; move to keyset pagination (cursor `{last_ts, last_commit}`) to avoid deep SKIP.
- Expose ingestion triggers for docs/git enhanced ingest as POST endpoints to avoid out-of-band scripts.
- Add telemetry endpoint (or extend `/health`) returning `{avg_query_time_ms, cache_hit_rate, memory_usage_mb}` so the UI can display operational health.

4.3 Ingest: Parallel Extract, Batched Writes
- Split extraction from writes:
  - Use `concurrent.futures.ThreadPoolExecutor(max_workers=4)` to parse commit messages, resolve file lists, and extract doc chunks concurrently.
  - Accumulate per-commit operations; write in batches to Neo4j (e.g., 50–100 relationships per transaction) to reduce overhead.
  - Maintain entity-key serialization to avoid deadlocks (e.g., writes grouped by File path or Requirement id).
  - References:
    - Ingest loop: `developer_graph/temporal_engine.py:36-79`.
    - Chunk extraction (enhanced ingests): `developer_graph/enhanced_ingest.py:265`, `:290` and `developer_graph/enhanced_git_ingest.py:441`.

5) Detailed Design

5.1 Frontend Changes
- API usage & pagination
  - Change initial fetch to: `GET /api/v1/dev-graph/graph/subgraph?limit=250&include_counts=false`.
  - Use `sub.pagination.next_cursor` to fetch subsequent pages until `has_more=false`.
  - Code touch points:
    - `frontend/src/components/explore/KnowledgeGraph.tsx:21` (request params)
    - `frontend/src/components/explore/KnowledgeGraph.tsx:33` (clear graph only once on first page)
    - `frontend/src/components/explore/KnowledgeGraph.tsx:35` (batch add nodes)
    - `frontend/src/components/explore/KnowledgeGraph.tsx:48` (batch add edges)

- Worker: Louvain
  - New file: `frontend/src/workers/louvain.worker.ts`:
    - Input: `{ nodes: Array<{id:string}>, edges: Array<{source:string,target:string}> }`
    - Output: `{ [id: string]: number }` communities
    - Main thread: apply via `graph.updateNodeAttributes(id, attrs => ({...attrs, color}))` in batches.
  - Replace `louvain.assign` at `frontend/src/components/explore/KnowledgeGraph.tsx:58` with worker call + application.

- Worker: Layout (ForceAtlas2)
  - New file: `frontend/src/workers/layout.worker.ts` using `graphology-layout-forceatlas2` in worker mode.
  - Input: graph snapshot; parameters (iterations, gravity, scaling, linLog, barnesHut).
  - Output: periodic position maps `{ [id: string]: {x:number,y:number} }`.
  - Apply incrementally only to nodes without `x/y`; stop when stability threshold reached.

- Progressive application & main-thread hygiene
  - Use `requestIdleCallback` (polyfill for Safari) to chunk `graph.addNode`/`addEdge` calls in groups of ~200.
  - Wrap visibility/color updates inside a single `graph.startBatch()`/`graph.endBatch()` section to minimize reflow.

5.2 Backend Changes
- `include_counts` flag
  - Update endpoint signature at `developer_graph/api.py:521-527` to add `include_counts: bool = Query(True)`.
  - In `developer_graph/temporal_engine.py:300` area, guard the COUNT cypher execution behind `if include_counts:`.

- In-memory cache
  - Add at module or class level in `developer_graph/temporal_engine.py`:
    - A small dict: `{ key: { value, expires_at } }`, with `key = (from,to,tuple(node_types or []),limit,cursor,include_counts)`.
    - Purge lazy on access; TTL default 60s.
  - Wrap before/after the main query block around `developer_graph/temporal_engine.py:338-420` (where we iterate results and build response).

5.3 Ingest Parallelism
- Introduce an extraction pipeline using `ThreadPoolExecutor` (I/O-bound git + light CPU) and channel results to a batched write function that opens fewer transactions.
- Keep per-entity ordering (e.g., merge `File` by path) to avoid lock contention.
- Optionally, parallelize per-commit ingestion sessions when their file sets don’t overlap heavily.
- Update sites:
  - `developer_graph/temporal_engine.py:36-79` (factor out per-commit compute; batch writes every N items or end-of-commit).

6) API Spec Changes
- `GET /api/v1/dev-graph/graph/subgraph`
  - New query param: `include_counts` (bool, default true)
  - Response (when `include_counts=false`): `pagination.total_nodes` and `pagination.total_edges` may be `null` or omitted; `next_cursor` still provided.

7) Telemetry & Acceptance Criteria
- Instrument query time (already returned):
  - `developer_graph/temporal_engine.py:query_time_ms` included in response; verify it drops for `include_counts=false`.
- Frontend Performance (Chrome Performance panel):
  - First page paint under 300ms on reference dataset.
  - No long tasks (>50ms) during progressive hydration.
  - Interaction (hover focus mode) stays responsive while streaming pages.
- Functional:
  - Graph renders same number of nodes/edges after all pages as before.
  - Colors/communities match worker results (spot-check against previous sync method on small graphs).

8) Rollout Plan
- Phase A (1 day): Backend `include_counts` flag + TTL cache, ship behind default `include_counts=false` in UI.
- Phase B (1–2 days): Frontend progressive hydration + label/render tuning.
- Phase C (1–2 days): Web workers for Louvain and ForceAtlas2; ship Louvain first, then optional layout.
- Phase D (1–1.5 days, optional now): Ingest parallel extraction + batched writes.

9) Effort Estimate
- Backend params + cache: 0.5 day.
- Frontend progressive hydration + batching: 0.5–1 day.
- Louvain worker + wiring: 0.5–1 day.
- Layout worker + wiring (optional): 1 day.
- Ingest parallelism and batching: 1–1.5 days.
- Total: 3–5 days depending on layout worker and ingest scope.

10) Risks & Mitigations
- Worker serialization overhead: Use compact arrays and avoid transferring large attribute maps; only send ids/edges.
- Neo4j lock contention with parallel ingest: Batch writes, group by entity, limit concurrency.
- Cache staleness: Short TTL (60s) and only for read-only analytical endpoints; allow bypass via `cache=false` param if needed (future).

11) Open Questions
- Do we want to persist server-computed coordinates (`x/y`) on nodes for reuse across sessions? If yes, add minimal write on first layout convergence.
- What node-count threshold should enable workers by default? Propose 200.

12) Work Items (Traceable to Code)
- Frontend
  - Progressive pagination: `frontend/src/components/explore/KnowledgeGraph.tsx:21`, `:33`, `:35`, `:48`.
  - Remove sync `louvain.assign`: `frontend/src/components/explore/KnowledgeGraph.tsx:58` → worker.
  - Add workers: `frontend/src/workers/louvain.worker.ts`, `frontend/src/workers/layout.worker.ts`.
  - Sigma config tuning: `frontend/src/components/explore/KnowledgeGraph.tsx:76`.
- Backend
  - Endpoint param: `developer_graph/api.py:521-527` add `include_counts`.
  - Engine guard and cache: `developer_graph/temporal_engine.py:260` (function signature) and around `:338-420` for response assembly.
- Ingest
  - Parallel extract + batched writes: `developer_graph/temporal_engine.py:36-79` and chunk-related extraction in `developer_graph/enhanced_ingest.py:265`, `:290` and `developer_graph/enhanced_git_ingest.py:441`.
