## Dev Graph: Link Integrity & Coverage Improvements

### Context
- Baseline audit showed heavy under-counting: only 15 `Library` nodes, 295 `USES_LIBRARY`, 2,157 `MENTIONS_LIBRARY`, and 9,541 `chunks_without_links`.
- Stage telemetry confirmed the ingestion pipeline finished successfully (quality score 99.9, 27,892 nodes / 210,842 relationships), so gaps stem from extraction logic rather than job failures.

### Verification Highlights
- Stage 8 already relied on `CodeSymbolExtractor`, but library coverage depended purely on in-file import heuristics; no manifest seeding or doc-based mentions ran, so missing packages never became `Library` nodes.
- TypeScript/JavaScript import parsing ignored scoped packages, dynamic `import()` calls, and alias segments, so many npm modules were not normalised to canonical IDs.
- Chunk ingestion wrote `Chunk-[:PART_OF]->File` but never created `File-[:CONTAINS_CHUNK]->Chunk`, so audits flagged more than nine thousand chunks as “unlinked” despite having the one-way relationship.
- Document chunk rendering failed fast on non UTF-8 files and code chunking silently trimmed characters via `errors='ignore'`, making older docs/code invisible to mention extractors. No visibility existed for fallback decoding.
- `/api/v1/dev-graph/audit` did not report library coverage or decode health, so tracking regressions required manual queries.

### Implemented Changes
1. **Manifest-driven library coverage** (`developer_graph/code_symbol_extractor.py`)
   - Parse `package.json` (all dependency sections) and `requirements.txt`; seed/merge `Library` nodes with version, source, and slug metadata.
   - Expand normalisation helpers to recognise scoped packages, nested modules, and Python dotted imports via `_generate_module_candidates` and `_canonicalize_library_name`.
   - Extend doc-term dictionary dynamically so the fulltext sweep now includes manifest packages; expose refresh decisions through `doc_library_refresh` in Stage 8 stats.

2. **Chunk link integrity guardrails** (`developer_graph/chunk_ingestion.py`, `developer_graph/routes/unified_ingest.py`)
   - Chunk writers now create both `Chunk-[:PART_OF]->File` and `File-[:CONTAINS_CHUNK]->Chunk` for code and docs, persisting decode metadata on `File.decoding`.
   - Added `_normalize_chunk_relationships` inside Stage 8 so reruns backfill missing edges/text/kind before symbol extraction, exposing the counts via a `chunk_normalization` payload.
   - Stage 3 results now surface `doc_encoding_summary` / `code_encoding_summary` so UI dashboards can flag fallback decodes immediately.

3. **Encoding resilience & observability** (`developer_graph/chunk_ingestion.py`)
   - Introduced `_read_text_with_fallback` using UTF-8 with BOM handling, optional `charset_normalizer`/`chardet`, Unicode normalisation, and replacement character tracking.
   - Summarise fallback counts, detectors, and samples (top 5) for docs and code, logging when fallbacks occur so ingestion issues are auditable.

4. **Audit extensions** (`developer_graph/routes/ingest.py`)
   - `/api/v1/dev-graph/audit` now returns `library_summary` (manifest sources, declared languages, top library usage) and `decode_stats` (per-encoding counts plus fallback samples).
   - Orphan detection uses an `OPTIONAL MATCH` fallback so Neo4j deployments without `degree()` support still produce accurate counts.

### Operational Notes
- Stage 8 run output now includes manifest metrics: `manifest_entries`, `manifest_sources`, `manifest_aliases_tracked`, and `doc_library_refresh` along with the new chunk normalisation summary.
- Stage 3 results add `doc_encoding_summary` / `code_encoding_summary`; Frontend can surface them without extra queries.
- Audit responses expose library and decode sections; update dashboards/reporting to consume the new fields.

### Validation Steps
1. Run a full ingestion (`POST /api/v1/dev-graph/ingest/unified/start`) to populate manifest-driven libraries and new chunk links.
2. Trigger an audit (`POST /api/v1/dev-graph/audit`) and verify:
   - `library_summary.sources` covers `package.json` and `requirements.txt` entries.
   - `decode_stats.by_encoding` shows the expected fallback counts and `chunks_without_links` drops near zero thanks to two-way chunk edges.
3. Spot-check Stage 8 payload (`GET /api/v1/dev-graph/ingest/status/{job_id}`) for `manifest_entries`, `doc_library_refresh`, and `chunk_normalization` to confirm the new metrics are flowing.

### Status
- **Status:** Implemented
- **Owner:** Dev Graph Team
- **Artifacts:** `dev_graph_audit/last_report.json`, `dev_graph_audit/audit-20250929-095704.json`
