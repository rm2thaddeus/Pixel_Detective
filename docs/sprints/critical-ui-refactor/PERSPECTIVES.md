# critical-ui-refactor - Sprint Perspectives

## Artifacts

- `SPRINT_PERSPECTIVES_CARDS.html` or `SPRINT_PERSPECTIVES_CARDS.pdf` (cards)
- `_linked_docs.json` (evidence docs only)
- `_cochanged_files.json` (all co-changed files)

## Cold Open

Name: Critical UI Refactor Purpose: Refactor the frontend to improve performance, decouple from Streamlit, and implement a scalable, real-time UI using Next.js and modern React tooling.


## The Plan

The bet: ship the smallest workflow slice that can be verified.

- Core screens implemented and fully navigable
- Real-time logs and progress indicators functional
- State management stable with minimal bugs
- Consistent, responsive styling across devices
- Linting, unit tests, and integration tests all passing

## The Build

What shipped, grouped by user workflow: explore -> curate -> accelerate.

## The Receipts

Proof lives in numbers and in the paper trail (docs that moved while the sprint story was written).

- Commits touching sprint docs: 2
- Engineering footprint: +8170 / -5138 lines across 12 languages
- Evidence pack: 10 linked docs (git co-updated)

### Evidence Pack (git co-updated)

- `docs/CHANGELOG.md` - 1x - CHANGELOG
- `docs/PROJECT_STATUS.md` - 1x - Pixel Detective - Project Status Dashboard
- `frontend/README.md` - 1x - Getting Started
- `docs/reference_guides/ui.md` - 1x | evidence, reference - UI Service Documentation
- `docs/sprints/sprint-09/PRD.md` - 1x | sprint - Sprint 09 Product Requirements Document (PRD)
- `docs/sprints/sprint-09/README.md` - 1x | sprint - Sprint 09 README
- `docs/sprints/sprint-09/Task_Breakdown.md` - 1x | sprint
- `docs/sprints/sprint-09/transition-to-sprint-09.md` - 1x | sprint - Transition to Sprint 09: Backend Validation & Streamlit Removal
- `services/ingestion_orchestration_service/requirements.txt` - 1x
- `services/ml_inference_service/requirements.txt` - 1x

### Engineering Footprint (churn)

- Total churn: +8170 / -5138 lines

#### By language
- JSON: +7175 / -39
- Other: +46 / -3739
- Python: +245 / -774
- Docs (Markdown): +381 / -498
- CSS: +210 / -0
- TypeScript: +78 / -0
- YAML: +0 / -62
- PowerShell: +19 / -0
- Docs (Text): +0 / -17
- MJS: +16 / -0
- INFO: +0 / -9
- LOG: +0 / -0

#### Hotspots
- `frontend/package-lock.json`: +7116 / -0
- `services/ingestion_orchestration_service/database_utils/qdrant_connector.py`: +0 / -377
- `docs/sprints/sprint-09/Task_Breakdown.md`: +0 / -321
- `docs/sprints/sprint-09/transition-to-sprint-09.md`: +107 / -143
- `qdrant_storage/collections/image_vectors/0/segments/12e5899c-4665-4858-b6e5-c41411bb6f2d/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/54e1e992-bb76-408a-868b-f1a8482268ee/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/76580e40-3458-4e5d-b92d-e5c8d5a265ff/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/8acac431-3d23-4d71-8c3a-bcc1afa35579/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/9ed0be32-e6bc-42b2-ba8e-b6cdf9274f2f/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/cdf2c5ae-777a-4112-a7b5-755209ce9fd8/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/e90c405a-769a-4e3e-8234-c23a6c69b0d5/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/f382780a-fded-4ab0-8922-84fa2648fd59/payload_index/LOG`: +0 / -244
- `qdrant_storage/collections/image_vectors/0/segments/12e5899c-4665-4858-b6e5-c41411bb6f2d/payload_index/OPTIONS-000007`: +0 / -214
- `qdrant_storage/collections/image_vectors/0/segments/54e1e992-bb76-408a-868b-f1a8482268ee/payload_index/OPTIONS-000007`: +0 / -214
- `qdrant_storage/collections/image_vectors/0/segments/76580e40-3458-4e5d-b92d-e5c8d5a265ff/payload_index/OPTIONS-000007`: +0 / -214

## The Next Scene

The loop is live. Next is reducing friction and deepening semantics.


## Inputs
- README.md
- PRD.md
- completion-summary.md
- technical-implementation-plan.md
- QUICK_REFERENCE.md
