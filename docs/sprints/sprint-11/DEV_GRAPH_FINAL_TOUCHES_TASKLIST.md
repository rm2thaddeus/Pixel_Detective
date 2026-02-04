# DevGraph Final Touches - Implementation Checklist

> Source: `docs/sprints/sprint-11/DEV_GRAPH_FINAL_TOUCHES_PRD.md`
>
> Status legend: `[ ]` not started, `[~]` in progress, `[x]` completed.

## 1. Data Provenance & Sprint Mapping
- [x] Implement `map_all_sprints` in `developer_graph/sprint_mapping.py` with reliable sprint window parsing and fallbacks.
- [x] Provide reusable sprint window metadata so `_link_sprints_to_commits` and `_rollup_sprint_file_touches` emit `INCLUDES` edges.
- [x] Add ingestion guardrails that raise when new `GitCommit` nodes lack `uid` or `File` nodes miss `is_code` / `is_doc`.
- [x] Collapse `/api/v1/dev-graph/stats` query fan-out into a single Cypher round-trip and expose `/analytics/data-quality` for provenance metrics.

## 2. Structure View Edge Rendering
- [x] Ensure `/api/v1/dev-graph/graph/subgraph` returns edge payloads with types/properties needed by the UI.
- [x] Harden `StructureAnalysisGraph` to default to safe D3 rendering, add edge visibility toggles, and surface "no data" messaging.
- [x] Add lightweight frontend telemetry/logging for empty edge responses.

## 3. Git Commit Logic Validation
- [x] Add commit/file validation helpers inside `EnhancedGitIngester` with actionable logging.
- [x] Wrap `_create_commit_touches` and related workflows with validation + early exits on invalid commits.
- [x] Extend tests (e.g. `tests/test_ingestion.py`) to cover the validation paths and `uid/is_code/is_doc` assertions.

## 4. Relationship Derivation Sanity Checks
- [x] Exercise the existing `RelationshipDeriver` against a fixture graph to confirm `IMPLEMENTS`/`EVOLVES_FROM` basics still pass.
- [x] Capture residual risks/limitations in sprint docs.

## 5. Clean Extraction & Documentation
- [x] Document current DevGraph dependency surface & runtime requirements.
- [x] Produce migration checklist for a standalone DevGraph repo, including backend/frontend split.
- [x] Update README/docs to reflect decoupling strategy and known skips.

## 6. Testing & Verification
- [ ] Run automated backend test suite (`pytest`) and relevant frontend lint/build checks.
- [ ] Smoke-test API endpoints touched in this sprint.
- [ ] Verify repo boots without relying on Pixel Detective app entry points.

---

**Owner:** Codex Automation (2025-??)
**Notes:** Update checkboxes as tasks land; keep commit references for future PR description.
