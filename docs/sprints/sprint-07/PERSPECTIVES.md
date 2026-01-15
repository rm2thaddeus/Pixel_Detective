# sprint-07 - Sprint Perspectives

## Artifacts

- `SPRINT_PERSPECTIVES_CARDS.html` or `SPRINT_PERSPECTIVES_CARDS.pdf` (cards)
- `_linked_docs.json` (evidence docs only)
- `_cochanged_files.json` (all co-changed files)

## Cold Open

Sprint narrative and receipts.

- Sprint Duration: YYYY-MM-DD to YYYY-MM-DD (e.g., 2025-06-11 to 2025-06-17)

## The Plan

The bet: ship the smallest workflow slice that can be verified.

- The ML Inference Service runs successfully on the local host.
- `docker-compose up` successfully launches Qdrant and the Ingestion Orchestration Service.
- The Dockerized Ingestion Orchestration service communicates correctly with the locally running ML Inference service and the Dockerized Qdrant service.
- The Ingestion Orchestration Service uses a persistent cache, and cached data survives service restarts.
- Cache effectively prevents re-processing of known images.

## The Build

What shipped, grouped by user workflow: explore -> curate -> accelerate.

## The Receipts

Proof lives in numbers and in the paper trail (docs that moved while the sprint story was written).

- For Sprint 08, add detailed time profiling to the ML Inference Service (especially BLIP captioning) to identify and optimize slow steps. This may allow significant improvements in BLIP captioning performance and overall batch throughput.
- Commits touching sprint docs: 5
- Engineering footprint: +1676 / -811 lines across 7 languages
- Evidence pack: 12 linked docs (git co-updated)

### Evidence Pack (git co-updated)

- `docs/sprints/sprint-07/RECONNECT_UI_REFACTOR_PLAN.md` - 4x | plan, sprint - Sprint 07 Refactoring Plan: Reconnecting the UI to Service-Oriented Backend & Frontend Folderization
- `docs/PROJECT_STATUS.md` - 1x - Pixel Detective - Project Status Dashboard
- `docs/README.md` - 1x - Pixel Detective: AI-Powered Media Search Engine
- `docs/sprints/sprint-01/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-02/SPRINT_02_MINDMAP.md` - 1x | sprint - Sprint 02: Visual Design System - Comprehensive Mindmap
- `docs/sprints/sprint-03/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-04/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-06/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-08/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-09/mindmap.md` - 1x | sprint - ```mermaid
- `docs/sprints/sprint-11/PRD.md` - 1x | sprint - Sprint 11 PRD: Latent Space Visualization Tab
- `docs/sprints/sprint-11/QUICK_REFERENCE.md` - 1x | evidence, sprint - Sprint 11 Quick Reference: Latent Space Visualization Tab

### Engineering Footprint (churn)

- Total churn: +1676 / -811 lines

#### By language
- Docs (Markdown): +838 / -312
- Python: +467 / -433
- Other: +233 / -0
- TypeScript: +91 / -38
- YAML: +44 / -26
- Docs (Text): +3 / -2
- DB-WAL: +0 / -0

#### Hotspots
- `backend/ml_inference_fastapi_app/main.py`: +142 / -132
- `docs/sprints/sprint-07/o3research`: +214 / -0
- `docs/sprints/sprint-02/SPRINT_02_MINDMAP.md`: +17 / -177
- `docs/sprints/sprint-07/RECONNECT_UI_REFACTOR_PLAN.md`: +158 / -25
- `docs/sprints/sprint-07/TASK_BREAKDOWN.md`: +151 / -24
- `frontend/core/service_api.py`: +98 / -63
- `docs/sprints/sprint-07/PRD.md`: +128 / -8
- `frontend/src/app/latent-space/components/ClusterLabelingPanel.tsx`: +91 / -38
- `frontend/screens/fast_ui_screen.py`: +3 / -117
- `docs/PROJECT_STATUS.md`: +55 / -62
- `backend/ingestion_orchestration_fastapi_app/main.py`: +96 / -13
- `docs/sprints/sprint-07/README.md`: +78 / -1
- `frontend/screens/advanced_ui_screen.py`: +45 / -32
- `docs/sprints/sprint-07/BACKLOG.md`: +59 / -12
- `docker-compose.yml`: +44 / -26

## The Next Scene

The loop is live. Next is reducing friction and deepening semantics.


## Inputs
- README.md
- PRD.md
- mindmap.md
- TASK_BREAKDOWN.md
- BACKLOG.md
