# PRD: Temporal Semantic Dev Graph (Sprint 11)

Owner: [You]
Version: 1.0
Date: 2025-09-07
Status: Planned for Sprint 11

---

## 1) Problem & Vision

Teams need to query a repository “as of” any point in time and connect planning artifacts (PRDs, ADRs, sprint docs) to the code that implements them. Current ingestion is temporal for Git but lacks document/code chunking, embeddings, and evidence-based doc↔code links with provenance and confidence.

Vision: a lean, temporal-first graph with chunk-level semantic linking and time-bounded search that runs well on a developer laptop.

---

## 2) Goals & Non-Goals

Goals
- Unified temporal schema centered on GitCommit + TOUCHED(timestamp).
- Incremental ingestion for commits, docs, and code with chunking.
- Embeddings for DocChunk and CodeChunk, vector indexes in Neo4j.
- Evidence-based relationships with confidence and provenance.
- Time-bounded API for subgraphs, search, lineage, and metrics.

Non-Goals (Sprint 11)
- Distributed infra or multi-node scale-out.
- Full blob-level FileVersion snapshots (keep File + TOUCHED for MVP).
- OCR or binary content understanding.

---

## 3) Users & Core Use Cases

Users
- Developers/Architects: validate PRD/ADR alignment with code.
- PMs: sprint coverage and requirement traceability.
- Researchers: evolution and dependency analysis.

Core Use Cases
- Repo at commit X or window [from_ts, to_ts].
- “Which code chunks implement ADR-005/FR-11-02?”
- “Semantic search for ‘token minting’ within Sprint 12 window.”
- Track requirement evolution (EVOLVES_FROM), deprecations, and refactors.

---

## 4) System Overview

Components
- Ingestors: Git temporal ingest, Docs ingest, Code chunk ingest.
- Chunkers: Markdown (H2/H3) and code (function + sliding window fallback).
- Embedder: text embeddings via ML service (/embed_text), pluggable model.
- Graph Store: Neo4j 5.x with vector indexes on Chunk.embedding.
- Deriver: evidence-based relationships (IMPLEMENTS, LINKS_TO, EVOLVES_FROM).
- API: FastAPI endpoints for ingestion triggers, exploration, search, validation.

---

## 5) Data Model (Unified Temporal Schema)

Node Labels
- GitCommit { hash, message, author, timestamp, branch, uid }
- File { path, language?, is_code?, is_doc?, extension?, uid }
- Document { path, title?, type?, uid }
- Chunk { id, kind: 'doc'|'code', heading?, section?, file_path?, span?, text, length, embedding?, uid }
- Requirement { id, title?, description?, tags?, uid }
- Sprint { number, name, start_date?, end_date?, uid }
- GitAuthor { email, name, uid } (optional)

Relationships
- (GitCommit)-[:TOUCHED {change_type, additions?, deletions?, timestamp}]->(File)
- (Sprint)-[:INCLUDES]->(GitCommit)
- (Document)-[:CONTAINS_CHUNK]->(Chunk)
- (Chunk {kind:'code'})-[:PART_OF]->(File)
- (Requirement)-[:IMPLEMENTS {sources, confidence, commit?, timestamp, provenance}]->(File)
- (Chunk {kind:'doc'})-[:LINKS_TO {method, score, sources, confidence, timestamp, provenance}]->(Chunk {kind:'code'})
- (Requirement)-[:EVOLVES_FROM {sources, confidence, commit?, timestamp, diff_summary?}]->(Requirement)
- (Sprint)-[:CONTAINS_DOC]->(Document)
- (Document)-[:REFERENCES]->(Requirement|Sprint|Document) (optional)
- (GitCommit)-[:BY]->(GitAuthor) (optional)

Indexes & Constraints (Neo4j)
- Unique: (:GitCommit.hash), (:File.path), (:Requirement.id), (:Chunk.id)
- Property indexes: (:GitCommit.timestamp), (:File.path), (:Requirement.id), (:Chunk.id)
- Relationship property indexes: ()–[r:TOUCHED|IMPLEMENTS|EVOLVES_FROM|DEPRECATED_BY|REFACTORED_TO]–() ON (r.timestamp)
- Vector: (:Chunk.embedding) (cosine)

Notes
- Keep File + TOUCHED(timestamp) as MVP for temporal queries; consider FileVersion later if blob-level replay is required.

---

## 6) Temporal Modeling & Queries

Temporal State
- Each commit merges/upserts a GitCommit and TOUCHED(timestamp) to affected Files.
- Windowed subgraphs filter on 
.timestamp for temporal relationships.

Typical Queries
- Repo at commit or window
  `cypher
  MATCH (c:GitCommit)
  WHERE c.hash = 
  MATCH (c)-[r:TOUCHED]->(f:File)
  RETURN f.path, r.change_type, r.timestamp
  `
- Windowed subgraph (existing endpoint), constrained by 
.timestamp.
- Sprint evolution
  `cypher
  MATCH (s:Sprint {number:})-[:INCLUDES]->(c:GitCommit)-[t:TOUCHED]->(f:File)
  RETURN f.path, min(c.timestamp) AS first_ts, max(c.timestamp) AS last_ts, count(t) AS touches
  `

---

## 7) Chunking Specification

Doc Chunking (Markdown)
- Parse .md files under docs/sprints/** and other configured roots.
- Split on H2/H3; for each section capture:
  - Chunk(kind:'doc', id=doc_path#slug-ordinal, heading, section, text, length)
  - (Document)-[:CONTAINS_CHUNK]->(Chunk)
- Extract requirement mentions (e.g., FR-\d{2}-\d{2}) and sprint refs; optional (Document)-[:REFERENCES]->(...).

Code Chunking
- Languages: start with Python + TS/JS; fallback for others using sliding windows of ~80 LOC, 20 LOC overlap.
- Preferred unit: function/method; fallback window produces span="start:end" and snippet text.
- Create Chunk(kind:'code', id=file_path#span|symbol, file_path, span, text, length) and connect (:Chunk)-[:PART_OF]->(:File).

Quality Constraints
- Minimum chunk length (chars/tokens) to avoid noise.
- Stable id generation for reproducibility.

---

## 8) Embeddings & Vector Indexing

Model & Pipeline
- MVP: Reuse ML service /embed_text to embed chunk text (CLIP text) with batching & backoff.
- Pluggable model selection via env: EMBED_MODEL=text-clip|bge-m3|... (future).

Storage
- Persist float array into Chunk.embedding.
- Create vector index (cosine) on Chunk.embedding.

Performance
- Batch size tuned by ML service capability endpoint /capabilities.
- Skip embedding for chunks over max length; optionally summarize first N tokens.

**Model Research Requirements (Post-MVP)**
- **Code-Document Similarity Models**: Research specialized models for linking code chunks to documentation chunks (e.g., CodeBERT, GraphCodeBERT, or fine-tuned CLIP variants).
- **Requirement-Implementation Models**: Investigate models that can identify which code files implement specific requirements based on semantic similarity.
- **Evolution Detection Models**: Research models that can detect when requirements evolve or when code refactors occur based on semantic changes.
- **Confidence Scoring Models**: Develop models to assign confidence scores to derived relationships based on multiple evidence sources.
- **Evaluation Framework**: Create evaluation metrics and test datasets to validate model performance for each relationship type.

---

## 9) Evidence-Based Linking (Doc↔Code)

Recall & Ranking
- Lexical recall: use full-text index on Files/Chunks; match by file names, symbols, requirement IDs.
- Vector recall: kNN on Chunk(kind:'code') for each Chunk(kind:'doc') text embedding.
- Rerank & fuse: merge candidates; compute final score and confidence with method-aware weighting.

Edge Creation
- (docChunk)-[:LINKS_TO {method, score, sources, confidence, timestamp, provenance}]->(codeChunk)
  - method: 'lexical|vector|hybrid'
  - sources: ['doc-mention', 'symbol', 'similarity']
  - provenance: { doc_path, file_path, strategy, params }
  - 	imestamp: now or commit window center if provided

Requirement Links
- Derive (Requirement)-[:IMPLEMENTS]->(File) using commit-message evidence (FR-XX-YY in touched commits), extend to doc mentions.
- Confidence combine: c_new = 1 - (1 - c_old) * (1 - c_evidence).

Validation
- Thresholds per method; cap edges per docChunk to avoid noise (e.g., top 5).

---

## 10) API Endpoints (Additions/Updates)

Ingestion
- POST /api/v1/dev-graph/ingest/bootstrap
  - Runs: apply schema → git ingest (recent) → docs ingest → code chunk ingest → embeddings → derivations.
  - Idempotent; accepts optional {since_timestamp}.

Exploration
- GET /api/v1/dev-graph/docs/{chunk_id}/links
  - Returns linked code chunks with {score, confidence, method, sources, provenance}.

Search
- POST /api/v1/dev-graph/search
  - Body: { q: string, label?: 'File'|'Chunk'|'Requirement', from_ts?: string, to_ts?: string, k?: number }
  - Executes lexical + vector search; time-bounds via commit/relationship timestamps.

Validation
- GET /api/v1/dev-graph/validate/schema – extended to confirm vector indexes.
- GET /api/v1/dev-graph/validate/temporal – cross-check counts vs git for sampled window.
- GET /api/v1/dev-graph/validate/relationships – thresholds, dangling refs, distribution sanity.

Metrics
- GET /api/v1/dev-graph/metrics – {avg_query_time_ms, cache_hit_rate, memory_usage_mb, vector_search_ms}.

---

## 11) Performance Targets (Sprint 11)

- Windowed subgraph (30 days): < 300 ms.
- Semantic search (commit-bounded): < 150 ms.
- Bootstrap ingestion (1k commits, modest docs): < 5 minutes on 16GB laptop.
- Memory: < 4 GB for ≤ 1M LOC repos.

---

## 12) Implementation Plan (Sprint 11)

Phase 1: Schema & Plumbing (1–2d)
- Add vector index on Chunk.embedding and confirm constraints.
- Ensure subgraph responses include labels for UI typing.
- Extend validators to check new indexes.

Phase 2: Chunkers & Ingestion (2–3d)
- Implement Markdown doc chunker (H2/H3) and ingestion script.
- Implement code chunker (Python + TS/JS; sliding window fallback) and ingestion script.
- Wire both into bootstrap endpoint.

Phase 3: Embeddings (1–2d)
- Batch embed chunks via ML service /embed_text with adaptive batch sizing.
- Persist embeddings; handle retries; mark chunks with embedding_error on failure.

Phase 4: Linking & Derivations (2–3d)
- Implement lexical recall + vector kNN + fusion; write LINKS_TO with provenance.
- Extend IMPLEMENTS derivation to include doc evidence; combine confidence.
- **Model Research Phase**: Begin research on specialized models for code-document linking and requirement-implementation mapping.

Phase 4.5: Model Integration (Future Sprint)
- Integrate research findings from Phase 4 model research.
- Implement specialized models for high-confidence relationship derivation.
- Deploy evaluation framework for model performance validation.

Phase 5: API & Validation (1–2d)
- Add /docs/{chunk_id}/links and enhanced /search.
- Extend /validate/* and /metrics.

Buffer: 1d for hardening and docs.

---

## 13) Acceptance Criteria

Functional
- Running POST /ingest/bootstrap from a clean Neo4j builds: commits, files, documents, chunks, embeddings, and derived links without error.
- GET /docs/{chunk_id}/links returns top-5 code chunks with method, score, and confidence.
- POST /search returns relevant results; rom_ts/	o_ts limit scope correctly.

Temporal Correctness
- Repo-at-commit queries match git for sampled commits (file counts and touched paths).

Quality
- On 10–20 sampled doc chunks, ≥70% of top-5 links are judged relevant by a developer.
- **Model Research Deliverables**: Research report on specialized models for code-document linking with performance benchmarks and integration recommendations.

Performance
- Meets targets in section 11 on a representative repo subset.

---

## 14) Risks & Mitigations

- Neo4j vector index size: embeddings inflate node size.
  - Mitigate with dimensionality choice, summarize long chunks, or store vectors only for kind in ['doc','code'].
- Model mismatch for code: CLIP text underperforms on code.
  - MVP on CLIP; abstract embedder; evaluate code-specialized model next sprint.
- Chunk noise and ID instability.
  - Minimum length, stable IDs, language-aware symbol extraction.
- Graph growth & UI density.
  - Keep windowed queries; cap linked edges per doc chunk; expose thresholds.

---

## 15) Telemetry & Ops

- Metrics: average query times, vector search timings, cache hit rate, memory usage.
- Health: /health returns service, DB connection, and timestamp.
- Config: REPO_PATH, NEO4J_URI, EMBED_MODEL, EMBED_BATCH, SEARCH_K.
- Runbook: Docker compose (Neo4j + API), UI env NEXT_PUBLIC_DEV_GRAPH_API_URL.

---

## 16) Rollout & Ownership

- Branch: eature/sprint11-temporal-semantic-graph.
- PRs by phase, merge sequentially; keep /validate/* green.
- Owner: You; Reviewer: Core backend dev; Support: UI dev for linking views.

---

## 17) Appendix: Index & Example Cypher

Schema Application (pseudo)
`python
CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.id IS UNIQUE;
CREATE INDEX IF NOT EXISTS FOR (c:GitCommit) ON (c.timestamp);
CREATE INDEX IF NOT EXISTS FOR ()-[r:TOUCHED]-() ON (r.timestamp);
CREATE INDEX IF NOT EXISTS FOR ()-[r:IMPLEMENTS]-() ON (r.timestamp);
// Vector index
CREATE VECTOR INDEX chunk_vec_idx IF NOT EXISTS
FOR (ch:Chunk) ON (ch.embedding)
OPTIONS {indexConfig: {ector.dimensions: 512, ector.similarity_function: 'cosine'}};
`

Link Derivation (sketch)
`cypher
// Lexical recall (example):
CALL db.index.fulltext.queryNodes('file_fulltext', ) YIELD node AS f, score AS s
WITH f, s WHERE s > 0.5
MATCH (cc:Chunk {kind:'code'})-[:PART_OF]->(f)
RETURN cc, s LIMIT 100;

// Vector kNN (example):
MATCH (dc:Chunk {id:}) WHERE exists(dc.embedding)
CALL db.index.vector.queryNodes('chunk_vec_idx', , dc.embedding) YIELD node, score
WITH node AS cc, score
WHERE cc.kind = 'code'
RETURN cc, score;
`

---

End of document.
