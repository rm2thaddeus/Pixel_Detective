Developer Graph API — Architecture and Performance Guide

Overview
- Purpose: Provide a temporal, traceable knowledge graph of development activity (code, commits, requirements, docs) for fast data visualization and analytics.
- Tech: FastAPI + Neo4j. Temporal edges store `timestamp` to enable bounded subgraphs and timelines. Git is the source of truth for time.

Domain Model
- Node Labels:
  - GitCommit: `hash`, `author`, `message`, `timestamp`, `branch`, `uid`.
  - File: `path`, `language`, `uid`.
  - Requirement: `id`, `title`, `author`, `date_created`, `goal_alignment`, `tags`, `uid`.
  - Document: `path`, optional derived fields; used for sprint and doc-chunk hierarchy.
  - Chunk: `id`, content‑oriented slices for doc granularity.
  - Sprint: `number`, `start_date`, `end_date` (resolved by mapper at query time).

- Relationships (all may carry `timestamp` when applicable):
  - (GitCommit)-[:TOUCHED {change_type, timestamp}]->(File)
  - (Requirement)-[:IMPLEMENTS {commit, timestamp}]->(File)
  - (Requirement)-[:EVOLVES_FROM {commit, diff_summary, timestamp}]->(Requirement)
  - (File)-[:REFACTORED_TO {commit, refactor_type, timestamp}]->(File)
  - (A)-[:DEPRECATED_BY {commit, reason, timestamp}]->(B) where A,B can be Requirement or File
  - Structural: (Sprint)-[:CONTAINS_DOC]->(Document), (Document)-[:CONTAINS_CHUNK]->(Chunk), (Chunk)-[:MENTIONS]->(Requirement)

Stable Node Identity
- Problem: Prior versions derived IDs differently client‑side, causing instability and mismatches.
- Change: All core nodes now persist `uid`:
  - GitCommit.uid = hash
  - File.uid = path
  - Requirement.uid = id
- API prefers `uid` as the returned `id` to stabilize linking and visualization.

Schema and Indexing
- Constraints:
  - UNIQUE: GitCommit.hash, File.path, Requirement.id, Chunk.id
- Property Indexes:
  - GitCommit.timestamp, Commit.timestamp (compat), File.path, Requirement.id, Chunk.id
- Relationship Indexes (temporal):
  - TOUCHED.timestamp, IMPLEMENTS.timestamp, EVOLVES_FROM.timestamp, REFACTORED_TO.timestamp, DEPRECATED_BY.timestamp
- Full‑Text Indexes (new):
  - file_fulltext on File(path)
  - requirement_fulltext on Requirement(id, title)
  - commit_fulltext on GitCommit(message, author)

API Surface (key routes)
- Retrieval
  - GET /api/v1/dev-graph/nodes: label‑filtered list with pagination (offset/limit). For large graphs, prefer subgraph endpoints.
  - GET /api/v1/dev-graph/relations: relation list with optional type and start Neo4j internal id; prefer windowed subgraph.
  - GET /api/v1/dev-graph/graph/subgraph: time‑bounded subgraph with type filtering and cursor pagination; returns nodes, edges, counts, perf.
  - GET /api/v1/dev-graph/commits/buckets: bucketized commit activity (day|week) for timeline prefetch/caching.
  - GET /api/v1/dev-graph/search: fallback scan search (small datasets only).
  - NEW GET /api/v1/dev-graph/search/fulltext: fast full‑text search over File/Requirement/GitCommit using FT indexes.
- Git helpers
  - GET /api/v1/dev-graph/commits, /commit/{hash}, /file/history
- Evolution/Traceability
  - GET /api/v1/dev-graph/evolution/requirement/{id}
  - GET /api/v1/dev-graph/evolution/file?path=...
  - GET /api/v1/analytics/activity, /api/v1/analytics/graph, /api/v1/analytics/traceability

Performance Audit and Bottlenecks
- Full Scan Search: `/search` uses `any(prop in keys(n) ...)` which forces label‑agnostic scans. Use `/search/fulltext` instead.
- Skip/Limit on Large Sets: `SKIP` suffers on big edge sets. For interactive timelines use keyset pagination: `ORDER BY r.timestamp DESC, r.commit` with a cursor `{last_ts, last_commit}` to avoid deep skips.
- Unstable IDs: Client deduced IDs from mixed properties, breaking link reuse and cache. Now `uid` normalizes identity.
- Label‑less Patterns: `MATCH (a)-[r]->(b)` has poor selectivity. Prefer label‑constrained patterns and temporal predicates when practical.
- Missing Hints for Viz: Nodes often lacked `x`, `y`, `size`. The subgraph endpoint now ensures deterministic coordinates and default sizes by label to stabilize rendering.

Recommended Query Patterns
- Time‑bounded subgraph (use indexes):
  - Predicate: `r.timestamp IS NOT NULL AND r.timestamp >= $from AND r.timestamp <= $to`
  - Constrain with labels when feasible: `(c:GitCommit)-[r:TOUCHED]->(f:File)`
- Keyset pagination for edges:
  - First page: `ORDER BY r.timestamp DESC LIMIT $limit`
  - Next page: add `AND (r.timestamp < $last_ts OR (r.timestamp = $last_ts AND r.commit < $last_commit))`
- Full‑text search:
  - `CALL db.index.fulltext.queryNodes('requirement_fulltext', $q)`; follow with label‑specific expansions.

Ingestion Pipeline
- Source: Git via GitPython (`GitHistoryService`)
- Flow: Read commits -> `merge_commit` -> touched files -> `merge_file` -> `relate_commit_touched_file`
- Requirement references: Extract FR-/NFR- patterns from messages; `merge_requirement`, `relate_implements`.
- Evolution signals: Simple heuristics for `EVOLVES_FROM`, `DEPRECATED_BY` and file renames for `REFACTORED_TO`.
- Schema: `apply_schema()` creates constraints, indexes, and full‑text indexes.

Visualization‑Oriented Node Properties
- `uid`: stable identity for nodes in client graphs
- `labels`: returned on subgraph nodes for consistent coloring/typing
- Coordinates: subgraph provides deterministic `x`,`y` fallback based on `uid` hash
- `size`: lightweight defaults by label (Requirement > File > Commit > Document/Chunk)

Concrete Optimizations to Implement (High Impact)
- Replace `/search` usage with `/search/fulltext` in the UI.
- Prefer `/graph/subgraph` for primary data fetch. Avoid raw `/relations` in the UI unless tightly filtered by type and time.
- Add keyset pagination to `/graph/subgraph` (cursor as `{ts, rel_type, commit}`) to eliminate deep `SKIP`.
- Add label constraints in heavy queries:
  - e.g., analytics edge counts: split by type already; ensure covered by `r.timestamp` index predicate.
- Cache layer (optional):
  - Server‑side LRU memo for recent windowed subgraphs keyed by `{from,to,types,limit,cursor}` for short bursts.
  - Precompute commit buckets daily and cache for quick timeline loads.

Schema Extensions (Optional, for richer viz)
- Author node: `(GitAuthor {email,name})` and `(GitCommit)-[:BY]->(GitAuthor)` to power author‑centric views and reuse strings.
- Directory hierarchy: `(Folder {path})` with `(Folder)-[:CONTAINS]->(File)` for structure layouts.
- Topic/Tag nodes: normalize `Requirement.tags` to nodes to cluster by themes.

Operational Notes
- Neo4j tuning: ensure pagecache (~graph size), enable metrics; for large datasets consider 5.x and GDS for centrality precomputes.
- Data volume expectations: edges with timestamps dominate timelines; indexes on rel.timestamps are already created to keep these fast.
- Security: current config can run without password in dev; configure `NEO4J_PASSWORD` in production.

Known Gaps / Next Steps
- Implement keyset cursor in `/graph/subgraph` to avoid `SKIP`.
- Add an init endpoint to trigger `apply_schema()` at startup or during migrations.
- Expand full‑text to Documents/Chunks if needed for content search.
- Consider projections via GDS for community detection precomputation (cached attributes on nodes for layout seeding).

Appendix: File Map
- API: `developer_graph/api.py`
- Temporal Engine: `developer_graph/temporal_engine.py`
- Schema Helpers: `developer_graph/schema/temporal_schema.py`
- Git Integration: `developer_graph/git_history_service.py`

