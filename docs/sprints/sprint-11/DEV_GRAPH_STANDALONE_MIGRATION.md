# DevGraph Standalone Migration Playbook

> Scope: Final sprint extraction tasks for Developer Graph components prior to Pixel Detective hand-off.
> Author: Codex Automation (Jan 2025)

## 1. Runtime & Dependency Surface
- **Backend** (`developer_graph/`)
  - Python 3.11+, FastAPI, Neo4j driver 5.x
  - GitPython, tenacity, python-dotenv
  - Optional: RAPIDS/Numba stack for temporal analysis (guarded by env flags)
- **Frontend** (`tools/dev-graph-ui/`)
  - Next.js 14 app router, Chakra UI, React Query
  - D3.js for SVG fallback; Deck.GL/WebGL modules are optional and lazy loaded
- **Data Services**
  - Neo4j 5.x (Bolt) with ROUTING disabled, bolt+s protocol supported
  - File-system access to source repository for git ingest
  - Optional Qdrant/postgres integrations are not required for the DevGraph slice

## 2. Files to Extract
- `developer_graph/` (entire package)
- `tools/dev-graph-ui/src/app/dev-graph/**/*`
- `docs/sprints/sprint-11/*` (planning + validation docs)
- Shared utilities: `scripts/update_dev_graph.sh`, `dev_graph_API_refactor_plan.md`

## 3. Migration Steps
1. **Bootstrap repository**
   - Initialise new git repo, copy backend tree under `/backend`
   - Create `requirements.txt` from current `developer_graph` module dependencies
   - Add FastAPI entrypoint (`developer_graph/app.py`) to new repo root
2. **Frontend split**
   - Copy `tools/dev-graph-ui` to `/frontend`
   - Replace API base url with relative env (`NEXT_PUBLIC_DEV_GRAPH_API_URL`)
   - Wire Next.js dev server to proxy `/api/v1/dev-graph/*` to backend
3. **Infrastructure**
   - Provide `docker-compose.yml` with Neo4j + backend service
   - Document `.env` variables (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `REPO_PATH`)
   - Optional GitHub Actions workflow for lint + pytest

## 4. Validation Checklist
- [ ] Run `pytest tests/test_dev_graph_quality.py` (guards ingest + relationship derivation)
- [ ] Smoke test `/api/v1/dev-graph/analytics/data-quality`
- [ ] Run `curl http://localhost:8080/api/v1/dev-graph/graph/subgraph?limit=25`
- [ ] Frontend: load `/dev-graph/welcome` (verify placeholders render when metrics empty)
- [ ] Frontend: toggle edges in Structure Analysis graph and confirm warning logged if empty

## 5. Relationship Derivation Status
- Added unit test to ensure `RelationshipDeriver.derive_all` aggregates counts with mocked driver
- Ingest pipeline now raises on missing `uid` / `is_code` / `is_doc`, preventing silent graph drift
- `sprint_mapper.map_all_sprints` normalises sprint windows and feeds rollups — prerequisite for `IMPLEMENTS` doc evidence

## 6. Known Gaps / TODO After Extraction
- Neo4j schema automation (`engine.apply_schema`) still tied to Pixel Detective CLI — mirror into standalone repo
- Data quality dashboard currently surfaces aggregate counts only; consider historics once standalone DB deployed
- Temporal engine endpoints untouched; disable if Neo4j APOC not available in new environment

## 7. Next Steps for New Maintainer
1. `python -m developer_graph.cli.bootstrap --limit 250` (seed graph)
2. `npm run dev -- --port 3001` in `/frontend`
3. Document ingestion REPO_PATH mapping for the new machine (WSL vs native paths)
4. Evaluate substituting HuggingFace models for commit analysis per appendix C of PRD
