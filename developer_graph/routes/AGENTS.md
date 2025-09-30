# Developer Graph Routes - Agent Guidelines

## Overview
This folder contains the FastAPI route handlers for the Developer Graph ingestion and query API. The routes orchestrate the multi-stage ingestion pipeline, relationship derivation, and data quality auditing.

## Key Files

### `unified_ingest.py`
**Primary ingestion pipeline orchestrator**

**Core Responsibilities:**
- Orchestrates 8-stage unified ingestion pipeline
- Manages background job execution with status tracking
- Normalizes chunk and requirement relationships
- Coordinates symbol extraction, library discovery, and relationship derivation

**Key Classes:**
- `UnifiedIngestionPipeline`: Main pipeline class with 8 stages
  - Stage 1: Database reset & schema
  - Stage 2: Parallel commit ingestion
  - Stage 3: Repository discovery & chunking (docs + code)
  - Stage 4: Code file processing
  - Stage 5: Sprint mapping
  - Stage 6: Relationship derivation (IMPLEMENTS, EVOLVES_FROM, DEPENDS_ON)
  - Stage 7: Embeddings (currently skipped)
  - Stage 8: Enhanced connectivity (symbols, libraries, co-occurrence)

**Recent Changes (2025-09-30):**
- Fixed sprint datetime concatenation bug (removed duplicate time appending)
- Added requirement linking logic in `_normalize_chunk_relationships()`
- Requirements now linked to documents via PART_OF when chunks mention them
- Added dual-strategy linking: document-based and sprint-pattern based

**Critical Methods:**
- `_normalize_chunk_relationships()`: Ensures data integrity
  - Backfills missing chunk.text and chunk.kind
  - Creates missing PART_OF relationships for chunks
  - Creates bidirectional CONTAINS_CHUNK relationships
  - **NEW**: Links requirements to documents/sprints via PART_OF

**API Endpoints:**
- `POST /api/v1/dev-graph/ingest/unified`: Full pipeline (synchronous)
- `POST /api/v1/dev-graph/ingest/unified/start`: Background job kickoff
- `GET /api/v1/dev-graph/ingest/status`: Global status
- `GET /api/v1/dev-graph/ingest/status/{job_id}`: Job-specific status
- `GET /api/v1/dev-graph/ingest/report`: Latest successful ingestion report

**Known Issues:**
- 51/64 requirements still lack PART_OF links (commit-message generated requirements don't follow FR-XX pattern)
- Sprint datetime values must be full ISO8601 format (handled by sprint_mapping.py)

---

### `ingest.py`
**Legacy and specialized ingestion endpoints**

**Purpose:**
- Provides legacy bootstrap and full-reset endpoints
- Offers specialized ingestion modes (temporal-semantic, batched git)
- Audit endpoint for database health checks

**Key Endpoints:**
- `POST /api/v1/dev-graph/ingest/full-reset`: Legacy full reset (use unified instead)
- `POST /api/v1/dev-graph/ingest/bootstrap`: Legacy bootstrap (use unified instead)
- `POST /api/v1/dev-graph/audit`: Comprehensive database audit

**Recent Changes (2025-09-30):**
- Fixed Neo4j decoding property access (bracket → dot notation)
- Audit now uses `decoding.encoding` instead of `decoding['encoding']`

**Audit Capabilities:**
- Node and relationship counts by type
- Orphan node detection
- Data quality checks (requirements_without_part_of, chunks_without_links, etc.)
- Library coverage analysis
- File decoding statistics

---

### `graph.py`
**Query and analytics endpoints**

**Purpose:**
- Provides read-only query access to the graph
- Exposes graph statistics and analytics
- Supports subgraph extraction for UI visualization

**Key Endpoints:**
- `GET /api/v1/dev-graph/stats`: Node/relationship counts
- `GET /api/v1/dev-graph/analytics`: Advanced graph metrics
- `GET /api/v1/dev-graph/graph/subgraph`: Windowed subgraph extraction
- `GET /api/v1/dev-graph/commits`: Recent commits
- `GET /api/v1/dev-graph/sprints`: Sprint information

---

## Architecture Patterns

### Job Management
- Background jobs use threading for long-running operations
- Job status tracked in `ingestion_state` dictionary
- Each job gets unique UUID for status polling
- Jobs report per-stage progress with telemetry

### Error Handling
- Stage-level exception handling prevents cascade failures
- Errors captured in job.error field for debugging
- Failed stages don't prevent subsequent stages from running
- Comprehensive logging at INFO/ERROR levels

### Concurrency Control
- Global `ingestion_state["is_running"]` prevents overlapping runs
- Background job kickoff returns job_id immediately
- Status polling via job_id for non-blocking progress tracking

### Data Normalization
- Stage 3 normalizes chunk relationships after ingestion
- Missing PART_OF links created from file_path
- Bidirectional CONTAINS_CHUNK relationships ensured
- Requirements linked to parent entities (documents/sprints)

---

## Development Guidelines

### Adding New Endpoints
1. Follow FastAPI conventions (type hints, Pydantic models)
2. Use dependency injection for database driver
3. Add to appropriate router (ingest vs. graph)
4. Document in API docstring and this AGENTS.md

### Modifying Pipeline Stages
1. Update `UnifiedIngestionPipeline` class methods
2. Ensure stage telemetry includes duration, counts, errors
3. Test with `reset_graph=true` for clean validation
4. Update stage count if adding/removing stages

### Query Optimization
- Use `UNWIND` for batch operations (>100 items)
- Limit result sets with explicit `LIMIT` clauses
- Use indexes on frequently queried properties (hash, id, path)
- Avoid cartesian products in relationship queries

### Testing
- Use `dry_run=true` for non-destructive testing
- Compare audit results before/after changes
- Verify relationship counts match expected patterns
- Check `quality_score` remains at 99.9%+

---

## Common Issues & Solutions

### Issue: Requirements without PART_OF
**Symptom:** `requirements_without_part_of` count > 0 in audit
**Cause:** Commit-message requirements don't follow FR-XX-XXX pattern
**Solution:** Requirements are now linked via chunks that mention them (implemented)
**Status:** Reduced from 64 to 51 (ongoing improvement)

### Issue: Sprint datetime parsing errors
**Symptom:** Neo4j syntax error "Text cannot be parsed to a DateTime"
**Cause:** Duplicate datetime concatenation (e.g., "2025-05-23T22:59:33+02:00T00:00:00")
**Solution:** Use sprint dates as-is without appending time (fixed)
**Prevention:** Sprint mapper returns full ISO8601, no concatenation needed

### Issue: Audit decoding property errors
**Symptom:** Neo4j warning about "missing property name: decoding"
**Cause:** Old bracket notation `decoding['encoding']` vs Neo4j map access
**Solution:** Use dot notation `decoding.encoding` (fixed)

### Issue: Frontend rebuild interruption
**Symptom:** Ingestion stops when UI refreshes
**Cause:** Synchronous API call blocked by frontend lifecycle
**Solution:** Use `/ingest/unified/start` for background jobs (implemented)
**Usage:** Frontend polls `/ingest/status/{job_id}` for progress

---

## Performance Benchmarks

### Full Ingestion (2025-09-30)
- **Duration**: ~14.5 minutes (870 seconds)
- **Nodes Created**: 30,822
- **Relationships Created**: 255,389
- **Quality Score**: 100.0%

### Stage Breakdown (typical)
1. Reset & Schema: ~8 seconds
2. Commit Ingestion: ~70 seconds (289 commits, 3,773 files)
3. Chunking: ~26 seconds (13,829 chunks)
4. Code Processing: ~22 seconds (340 files)
5. Sprint Mapping: ~12 seconds (12 sprints)
6. Relationship Derivation: ~5 seconds (1,448 relationships)
7. Embeddings: Skipped
8. Enhanced Connectivity: ~236 seconds (13,892 symbols, 177k+ symbol relationships)

### Bottlenecks
- Stage 2 (commits): 32% of total time
- Stage 8 (symbols): 26% of total time
- Recommended: Increase max_workers for parallel stages

---

## Future Improvements

### Priority 1: Data Quality
- [ ] Link remaining 51 requirements without PART_OF
- [ ] Increase MENTIONS_COMMIT relationships (currently only 9)
- [ ] Add EVOLVES_FROM relationship detection
- [ ] Improve document-to-commit cross-referencing

### Priority 2: Performance
- [ ] Profile Stage 2 commit ingestion for optimization
- [ ] Implement true async/await for background jobs
- [ ] Add caching for frequently accessed subgraphs
- [ ] Optimize symbol extraction batch sizes

### Priority 3: Features
- [ ] Add incremental/delta ingestion mode
- [ ] Implement embedding generation (Stage 7)
- [ ] Add graph diff/comparison endpoints
- [ ] Support custom relationship types

---

## Related Documentation
- `../architecture.md`: Overall system architecture
- `../ARCHITECTURE.md`: Technical implementation details
- `../../docs/DEV_GRAPH_MIGRATION_PLAN.md`: Migration strategy
- `../../docs/sprints/`: Sprint planning and tracking
