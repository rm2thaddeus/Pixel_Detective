Developer Graph Services — Architecture Overview

Status: Current as of Sprint 11 - Biological Evolution UI Implementation

## 🚀 Quick Start Commands

```bash
# Quick Developer Graph API reload (from repo root)
python -m uvicorn developer_graph.api:app --reload --host 0.0.0.0 --port 8080

# Complete stack startup
./start_app.ps1

# Frontend only (from tools/dev-graph-ui)
npm run dev
```

### Path normalization and document ingestion (Sprint 11)

- All `Document.path` and chunk `doc_path` values are stored as repo‑relative POSIX paths (e.g. `docs/sprints/critical-ui-refactor/README.md`).
- Both Enhanced and Parallel ingestion pipelines normalize paths consistently:
  - Enhanced: `enhanced_ingest.py` `_normalize_repo_relative_path()`
  - Parallel: `parallel_ingestion.py` `_normalize_repo_relative_path()`
- Titles: markdown document titles are extracted from the first heading and stored in `Document.title`.
- Chunk links: `Document` −[:CONTAINS_CHUNK]→ `Chunk` use normalized paths; verification shows zero mismatches.

Operational notes:
- Reset and bootstrap:
  - DELETE `http://localhost:8080/api/v1/dev-graph/reset?confirm=true`
  - POST `http://localhost:8080/api/v1/dev-graph/ingest/bootstrap?reset_graph=true&commit_limit=2000&derive_relationships=true&include_chunking=true`
- Verification helper: run `python verify_docs.py` from repo root to print counts, sample titles, and path checks.

---

1. Overview
- Purpose: Provide time‑aware developer graph APIs with unified temporal schema, fast ingestion, analytics, evidence‑based relationships, and interactive biological evolution visualizations.
- Tech: FastAPI (routers), Neo4j 5.x, GitPython, Python 3.x, Next.js 15.5, D3.js, Chakra UI.
- Key Concepts: Temporal edges with timestamps (TOUCHED/IMPLEMENTS/EVOLVES_FROM), evidence sources with confidence, biological evolution metaphors for code visualization.

2. High‑Level Components

## 2.1 Backend Services
- app_state.py: Initializes shared services and driver
  - driver: Neo4j driver
  - git: GitHistoryService
  - engine: TemporalEngine
  - sprint_mapper: SprintMapper
  - deriver: RelationshipDeriver
  - validator: DataValidator
  - chunk_service: ChunkIngestionService
  - embedding_service: EmbeddingService
  - parallel_pipeline: ParallelIngestionPipeline
- Routers (developer_graph/routes)
  - health_stats: health, stats
  - nodes_relations: nodes, relations
  - search: property and fulltext search
  - commits_timeline: commits list, timeline, commit detail, file history, subgraph by commit range
  - sprints: sprints list, sprint map, sprint details, sprint subgraph
  - graph: windowed subgraph, commit buckets
  - analytics: activity, graph, combined analytics
  - ingest: bootstrap, docs, git ingestion (enhanced/batched/temporal semantic), parallel ingest, chunks, derive relationships, embeddings
  - chunks: chunk stats/list
  - metrics: engine metrics
  - validate: schema/data validation & cleanup helpers
  - admin: reset/cleanup/full‑reset

## 2.2 Frontend Services (tools/dev-graph-ui)
- Next.js 15.5 application with TypeScript
- D3.js for data visualization and biological evolution animations
- Chakra UI for component library and responsive design
- Key Components:
  - BiologicalEvolutionGraph: Temporal commit tree with file dendrograms, biological metaphors (birth/growth/mutation/death)
  - TemporalEvolutionGraph: Traditional timeline visualization with file lifecycles
  - SimplePhysicsSimulation: Physics-based file movement simulation
  - ProgressiveStructureGraph: Structural analysis over time
- Visualization Features:
  - Biological evolution metaphors (organisms, generations, ecosystem)
  - Physics simulations with gravity, springs, and repulsion forces
  - Interactive timeline controls and playback
  - Real-time data fetching from Developer Graph API

3. Data Model (Temporal Semantic)
- Nodes
  - GitCommit {hash, message, author, timestamp, branch?, uid}
  - File {path, language?, is_code?, is_doc?, extension?, uid}
  - Requirement {id, title?, description?, author?, date_created?, tags?, uid}
  - Document {path, name?, title?, type?, uid}
  - Chunk {id, doc_path?, heading?, level?, ordinal?, content_preview?, length?, kind?, text?, embedding?, uid}
  - Sprint {number, name?, start_date?, end_date?, uid}
- Relationships (selected)
  - (GitCommit)-[:TOUCHED {change_type, additions?, deletions?, timestamp}]->(File)
  - (Requirement)-[:IMPLEMENTS {sources, confidence, commit?, timestamp, provenance?}]->(File)
  - (Requirement)-[:EVOLVES_FROM {sources, confidence, commit?, timestamp, diff_summary?}]->(Requirement)
  - (File)-[:REFACTORED_TO {commit, refactor_type?, timestamp}]->(File)
  - (Sprint)-[:INCLUDES]->(GitCommit)
  - (Sprint)-[:CONTAINS_DOC]->(Document)
  - (Document)-[:CONTAINS_CHUNK]->(Chunk)
  - (Chunk)-[:MENTIONS]->(Requirement)
  - (Sprint)-[:MENTIONS]->(File) (structural planning reference)

4. Schema & Indexing
- Constraints: unique on GitCommit.hash, File.path, Requirement.id, Chunk.id, Document.path, Sprint.number
- Property Indexes: GitCommit.timestamp, File.path, Requirement.id, Chunk.id
- Relationship Indexes: timestamp index on TOUCHED/IMPLEMENTS/EVOLVES_FROM/DEPRECATED_BY/REFACTORED_TO
- Fulltext: file_fulltext, requirement_fulltext, commit_fulltext, chunk_fulltext, document_fulltext
- Vector: Chunk.embedding (cosine), 512 dims (if available)

5. Ingestion Flows
- TemporalEngine (developer_graph/temporal_engine.py)
  - ingest_recent_commits, *_batched, *_parallel
  - time_bounded_subgraph, get_commits_buckets, evolution timelines
  - Creates GitCommit + File + TOUCHED(timestamp), derives IMPLEMENTS from commit messages; detects refactors
- EnhancedDevGraphIngester (developer_graph/enhanced_ingest.py)
  - Sprints, documents, chunk extraction, mentions, references
  - Batch UNWIND operations for performance
- EnhancedGitIngester (developer_graph/enhanced_git_ingest.py)
  - Commit analysis and provenance; sprint rollups; doc chunk modifications
  - Uses GitCommit + TOUCHED(timestamp), and structural MENTIONS for planning
- Bootstrap (routes/ingest.py)
  - Apply schema → enhanced docs → parallel commit ingest → sprint mapping → optional chunking → relationship derivation

6. Evidence‑Based Relationship Derivation
- RelationshipDeriver (developer_graph/relationship_deriver.py)
  - IMPLEMENTS: commit‑message (0.9), doc‑mention (0.6), code‑comment proxy (0.8)
  - EVOLVES_FROM: pattern extraction from commit messages (replaces/evolves from/supersedes)
  - DEPENDS_ON: import graph best‑effort mapping (when File‑[:IMPORTS]->File exists)
  - Confidence accumulation: `1 - (1 - prev) * (1 - new)`; sources appended
  - Watermarks: maintain `DerivationWatermark` per strategy

7. API Contracts (selected)
- GET /api/v1/dev-graph/health: HealthResponse
- GET /api/v1/dev-graph/stats: StatsResponse (consolidated query)
- GET /api/v1/dev-graph/graph/subgraph: WindowedSubgraphResponse
- GET /api/v1/dev-graph/commits/buckets: CommitsBucketsResponse
- GET /api/v1/dev-graph/evolution/timeline: commits + file lifecycles (actions via coalesce(action, change_type))
- POST /api/v1/dev-graph/ingest/bootstrap: staged bootstrap; returns per‑stage progress
- POST /api/v1/dev-graph/ingest/derive-relationships: counts + confidence stats

8. Performance & Caching
- Engine TTL cache (default 60s) for hot subgraphs
- Consolidated stats query (single round‑trip)
- Batched UNWIND writes across ingesters
- Parallel ingestion pipeline for commits and chunks

9. Logging & Telemetry
- Logging to stdout + file `dev_graph_api.log`
- /api/v1/dev-graph/metrics exposes basic engine metrics; health includes memory usage
- Frontend logging via browser console and React Query DevTools

10. Current Implementation Status (Sprint 11)
- ✅ Biological Evolution Graph: Temporal commit tree with file dendrograms
- ✅ Physics Simulation: Basic physics-based file movement
- ✅ Timeline Controls: Playback, navigation, time-based visualization
- ✅ Data Integration: Real-time API integration with Developer Graph
- ⚠️ UI/UX Issues: Physics simulation crowding, canvas space utilization
- 🔄 In Progress: Layout optimization and space utilization improvements

11. Operational Notes
- Environment:
  - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
  - REPO_PATH
  - TEMPORAL_LIMIT (optional)
- Security/CORS: env `CORS_ORIGINS` overrides default localhost origins

12. Service Startup Commands

## 12.1 Complete Stack Startup
```powershell
# From repository root - starts all services
./start_app.ps1
```

## 12.2 Backend Services Only
```powershell
# From repository root - starts all backend services
./start_backend.ps1

# With background jobs (recommended for development)
./start_backend.ps1 -UseJobs

# Skip Docker containers (Python services only)
./start_backend.ps1 -SkipContainers
```

## 12.3 Frontend Development
```powershell
# From tools/dev-graph-ui directory
cd tools/dev-graph-ui
npm run dev
```

## 12.4 Service Endpoints
- **Qdrant UI**: http://localhost:6333
- **Neo4j Browser**: http://localhost:7474 (neo4j/password)
- **Developer Graph API**: http://localhost:8080/docs
- **ML Inference Service**: http://localhost:8001/docs
- **Ingestion Orchestrator**: http://localhost:8002/docs
- **GPU UMAP API**: http://localhost:8003/docs
- **Dev Graph UI**: http://localhost:3000/dev-graph/timeline

13. Extensibility Guidelines
- Add a new router under `developer_graph/routes/` and include it in `developer_graph/api.py`
- Access shared services via `developer_graph/app_state.*`
- Keep endpoint paths stable to avoid FE breakage; add versioned variants if contracts change
- For new relationship derivations, add a strategy to RelationshipDeriver with clear source + confidence math
- For new UI visualizations, add components to `tools/dev-graph-ui/src/app/dev-graph/components/`
- Use D3.js for custom visualizations, Chakra UI for standard components

