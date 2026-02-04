# Developer Graph Module - Agent Guidelines

## Overview
The `developer_graph` module is the core backend system for building and maintaining a temporal semantic knowledge graph of a software development project. It ingests git history, code structure, documentation, and planning artifacts into a Neo4j graph database with rich relationship types.

## Architecture

### Core Components

1. **Ingestion Pipeline** (`routes/unified_ingest.py`)
   - 8-stage unified pipeline for complete graph construction
   - Background job support for non-blocking operations
   - Comprehensive status tracking and error handling

2. **Code Analysis** (`code_symbol_extractor.py`)
   - Extracts symbols (classes, functions, methods) from Python/TS/JS
   - Links symbols to documentation chunks via fulltext search
   - Discovers library usage from imports and manifest files

3. **Temporal Engine** (`temporal_engine.py`)
   - Ingests git commit history with file relationships
   - Extracts requirements from commit messages
   - Creates TOUCHED relationships between commits and files

4. **Chunk Ingestion** (`chunk_ingestion.py`)
   - Processes documents and code into searchable chunks
   - Maintains chunk→file→document relationships
   - Handles encoding detection and UTF-8 normalization

5. **Relationship Derivation** (`relationship_deriver.py`)
   - Evidence-based IMPLEMENTS relationships (requirement→file)
   - EVOLVES_FROM tracking for requirement evolution
   - DEPENDS_ON inference from import relationships

6. **Sprint Mapping** (`sprint_mapping.py`)
   - Maps sprint windows to commit ranges
   - Links documents to sprints via folder structure
   - Creates INCLUDES relationships (sprint→commit)

7. **Document-Code Linking** (`document_code_linker.py`)
   - Links documentation chunks to code files via path mentions
   - Creates MENTIONS_COMMIT relationships from commit hash references
   - Rolls up chunk-level mentions to document level

---

## Data Model

### Node Types
- **GitCommit**: Version control commits
- **File**: Source files, documents, config files
- **Document**: Markdown/text documentation
- **Chunk**: Text segments from documents or code
- **Symbol**: Code symbols (class, function, method, interface)
- **Library**: External dependencies
- **Requirement**: Functional/non-functional requirements
- **Sprint**: Time-boxed development periods
- **DerivationWatermark**: System metadata for incremental updates

### Key Relationship Types

#### Git & Files
- `(:GitCommit)-[:TOUCHED]->(:File)` - Commit modified file
- `(:File)-[:CO_OCCURS_WITH]->(:File)` - Files changed together

#### Documentation & Chunks
- `(:Document)-[:CONTAINS_CHUNK]->(:Chunk)` - Document contains chunk
- `(:Chunk)-[:PART_OF]->(:File)` - Chunk belongs to file
- `(:File)-[:CONTAINS_CHUNK]->(:Chunk)` - Bidirectional linkage
- `(:Chunk)-[:MENTIONS]->(:Requirement)` - Chunk references requirement

#### Code Structure
- `(:Symbol)-[:DEFINED_IN]->(:File)` - Symbol defined in file
- `(:File)-[:IMPORTS]->(:File)` - Import/dependency relationship

#### Semantic Links
- `(:Chunk)-[:MENTIONS_SYMBOL]->(:Symbol)` - Doc mentions code symbol
- `(:Document)-[:MENTIONS_SYMBOL]->(:Symbol)` - Rollup from chunks
- `(:Chunk)-[:MENTIONS_FILE]->(:File)` - Doc references file
- `(:Chunk)-[:MENTIONS_COMMIT]->(:GitCommit)` - Doc references commit
- `(:Chunk)-[:MENTIONS_LIBRARY]->(:Library)` - Doc mentions library
- `(:Chunk)-[:RELATES_TO]->(:File)` - Semantic connection via library

#### Libraries
- `(:File)-[:USES_LIBRARY]->(:Library)` - File imports library
- `(:Library)` - Properties: name, language, manifest_sources

#### Requirements & Implementation
- `(:Requirement)-[:PART_OF]->(:Document|:Sprint)` - Requirement scope
- `(:Requirement)-[:IMPLEMENTS]->(:File)` - Implementation evidence
- `(:Requirement)-[:EVOLVES_FROM]->(:Requirement)` - Version tracking
- `(:File)-[:DEPENDS_ON]->(:File)` - Dependency from imports

#### Sprint Management
- `(:Sprint)-[:INCLUDES]->(:GitCommit)` - Commits in sprint window
- `(:Sprint)-[:INVOLVES_FILE]->(:File)` - Files active in sprint

---

## Recent Changes (2025-09-30)

### Bug Fixes
1. **Sprint Datetime Concatenation** (`unified_ingest.py`)
   - Fixed duplicate datetime appending in sprint-commit linking
   - Sprint dates now used as-is from ISO8601 format

2. **Neo4j Property Access** (`ingest.py`)
   - Changed `decoding['encoding']` to `decoding.encoding`
   - Fixed audit queries for file decoding stats

3. **Requirement Linking** (`unified_ingest.py`)
   - Added automatic PART_OF linking for requirements
   - Links requirements to documents via chunks that mention them
   - Reduced unlinked requirements from 64 to 51

### Performance Improvements
- Background job support prevents UI blocking
- Chunk normalization in Stage 3 ensures data integrity
- Bidirectional relationship creation for better query performance

---

## Current Stats (Latest Run)

### Database Composition
- **Total Nodes**: 30,822
- **Total Relationships**: 255,389
- **Quality Score**: 100.0%
- **Orphaned Nodes**: 7 (0.02%)

### Node Breakdown
| Type | Count | % of Total |
|------|-------|------------|
| Symbol | 13,892 | 45.1% |
| Chunk | 13,829 | 44.9% |
| File | 2,461 | 8.0% |
| GitCommit | 290 | 0.9% |
| Document | 174 | 0.6% |
| Library | 97 | 0.3% |
| Requirement | 64 | 0.2% |
| Sprint | 12 | 0.04% |

### Relationship Breakdown (Top 10)
| Type | Count | Purpose |
|------|-------|---------|
| RELATES_TO | 84,503 | Semantic connections |
| MENTIONS_SYMBOL | 83,710 | Doc→symbol links |
| CO_OCCURS_WITH | 20,175 | File co-occurrence |
| CONTAINS_CHUNK | 16,523 | Container→chunk |
| DEFINED_IN | 13,892 | Symbol→file |
| PART_OF | 13,842 | Chunk/req→parent |
| INVOLVES_FILE | 10,918 | Sprint→file |
| MENTIONS_LIBRARY | 3,957 | Doc→library |
| TOUCHED | 3,773 | Commit→file |
| MENTIONS_FILE | 1,445 | Doc→file |

---

## Development Workflow

### Running Full Ingestion
```powershell
# Synchronous (blocks until complete)
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/ingest/unified?reset_graph=true&derive_relationships=true&max_workers=4" -Method POST

# Background (returns job_id immediately)
$start = Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/ingest/unified/start?reset_graph=true&derive_relationships=true&max_workers=4" -Method POST
$jobId = ($start.Content | ConvertFrom-Json).job_id

# Poll status
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/ingest/status/$jobId"
```

### Running Audit
```powershell
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/audit" -Method POST | Select-Object -ExpandProperty Content | Out-File dev_graph_audit/audit.json
```

### Viewing Results
```powershell
# Get report
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/ingest/report"

# Get stats
Invoke-WebRequest -Uri "http://localhost:8080/api/v1/dev-graph/stats"
```

---

## Known Issues & Workarounds

### 1. Requirements Without PART_OF (51 remaining)
**Issue:** Commit-generated requirements don't follow FR-XX-XXX pattern  
**Impact:** Requirements orphaned, harder to query by sprint  
**Workaround:** Linking via chunks that mention them (partially implemented)  
**TODO:** Extract sprint context from commit timestamps

### 2. Low MENTIONS_COMMIT Count (only 9)
**Issue:** Document-to-commit linking requires exact hash references  
**Impact:** Limited temporal tracking of documentation evolution  
**Workaround:** Use TOUCHES relationships for file-level commit tracking  
**TODO:** Implement fuzzy commit reference matching

### 3. No EVOLVES_FROM Relationships (0)
**Issue:** Evolution pattern not detected in commit messages  
**Impact:** Can't track requirement version history  
**Workaround:** Manual sprint-to-sprint requirement mapping  
**TODO:** Enhance commit message parsing patterns

### 4. Files Without TOUCHED (198 files)
**Issue:** Files never modified in git history  
**Impact:** Limited temporal context for these files  
**Workaround:** Expected for generated/config files  
**Note:** Not a bug, these are legitimately untracked files

---

## Testing & Validation

### Pre-Deployment Checklist
- [ ] Run full ingestion with `reset_graph=true`
- [ ] Verify quality_score = 100.0%
- [ ] Check `requirements_without_part_of` ≤ 55
- [ ] Verify `chunks_without_links` = 0
- [ ] Confirm total_relationships > 250,000
- [ ] Validate orphaned_nodes < 10

### Performance Benchmarks
- **Full ingestion**: ~14.5 minutes
- **Throughput**: ~35 nodes/second, ~295 relationships/second
- **Memory usage**: ~500MB peak during Stage 8

### Regression Tests
1. Compare node/relationship counts with previous audit
2. Verify no new orphan nodes introduced
3. Check data quality metrics don't degrade
4. Ensure all 8 stages complete successfully

---

## Configuration

### Environment Variables
- `NEO4J_URI`: Neo4j connection string (default: bolt://localhost:7687)
- `NEO4J_USER`: Neo4j username (default: neo4j)
- `NEO4J_PASSWORD`: Neo4j password
- `REPO_PATH`: Path to git repository root

### Pipeline Parameters
- `reset_graph`: Clear database before ingestion (default: false)
- `derive_relationships`: Run relationship derivation (default: true)
- `max_workers`: Parallel workers for chunking (default: 4)
- `subpath`: Limit ingestion to subdirectory (optional)

---

## Troubleshooting

### Ingestion Hangs on Stage X
1. Check Neo4j is running and accessible
2. Review logs for timeout errors
3. Increase Neo4j query timeout settings
4. Reduce `max_workers` if memory constrained

### Neo4j Syntax Errors
1. Verify Neo4j version compatibility (requires 4.4+)
2. Check for breaking changes in Cypher syntax
3. Test queries in Neo4j Browser first
4. Review property access patterns (use dot notation)

### Low Relationship Counts
1. Verify fulltext index exists: `chunk_fulltext`
2. Check symbol extraction didn't skip files
3. Review logs for Stage 8 errors
4. Ensure library manifest files are present

### Memory Issues
1. Reduce `max_workers` parameter
2. Increase Docker/Neo4j memory limits
3. Process in batches using `subpath`
4. Clear browser cache and restart frontend

---

## Future Roadmap

### Q4 2024
- [ ] Implement true incremental/delta ingestion
- [ ] Add embedding generation (Stage 7 activation)
- [ ] Enhance EVOLVES_FROM detection
- [ ] Improve requirement linking accuracy

### Q1 2025
- [ ] Add GraphQL API layer
- [ ] Implement graph diff/comparison
- [ ] Support custom relationship types
- [ ] Add webhook notifications for ingestion events

### Q2 2025
- [ ] Multi-repository support
- [ ] Advanced analytics and metrics
- [ ] Machine learning for relationship confidence
- [ ] Real-time incremental updates

---

## Related Documentation
- `routes/AGENTS.md`: FastAPI route handlers guide
- `architecture.md`: System architecture deep-dive
- `../docs/DEV_GRAPH_MIGRATION_PLAN.md`: Migration strategy
- `../docs/sprints/`: Sprint planning artifacts
- `../frontend/ARCHITECTURE.md`: Frontend integration guide
