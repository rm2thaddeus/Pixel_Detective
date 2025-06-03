# Sprint 09 Backlog (Items carried over from Sprint 08)

This backlog outlines tasks carried over from Sprint 08 and planned for Sprint 09. Sprint 08 focused on Qdrant integration, key feature delivery (duplicate detection UI, random image, advanced filtering/sorting UI), and a major frontend refactor to make UI screens API-driven and stateless.

---

## High Priority (Testing & Core Functionality Finalization)
- ⚪ TASK-08-02-02: Full implementation of duplicate detection algorithm (backend).
- ⚪ TASK-08-01-04: Write unit tests for `/api/v1/search` and `/api/v1/images` endpoints.
- ⚪ TASK-08-02-05: Develop integration tests for duplicate detection flow (UI to backend).
- ⚪ TASK-08-03-05: Write unit and integration tests for random image endpoint and UI component.
- ⚪ TASK-08-04-04: Write tests for filter logic and UI behavior under edge cases.
- ⚪ TASK-08-06-01: Expand integration tests for full UI → API → Qdrant roundtrip (manual FastAPI, Qdrant via Docker).
- ⚪ TASK-08-06-02: Develop end-to-end tests with Playwright for critical user flows (search, duplicates, random, filtering).
- ⚪ TASK-08-06-03: Add negative tests for invalid parameters and no-data scenarios.

## Medium Priority (Stability & Performance Verification)
- ⚪ TASK-08-06-04: Benchmark performance of key endpoints with `pytest-benchmark` and analyze with `nsys`.
- ⚪ Address any remaining UI polish or minor bug fixes identified during Sprint 08 testing and carry-over.

## Low Priority (Documentation & Cleanup - Deferred from Sprint 08)
- ⚪ Legacy Module Removal: Review and potentially deprecate/remove `core/fast_startup_manager.py` and `utils/embedding_cache.py` if fully superseded by new architecture.
- ⚪ MVP App Refactor: Review and potentially clean up or remove `scripts/mvp_app.py` features not using `service_api.py`.
- ⚪ API Documentation: Auto-generate/update Swagger/OpenAPI docs for new/changed endpoints from Sprint 08.
- ⚪ Architecture Diagrams Update: Refresh diagrams in `/docs/architecture.md` to reflect Sprint 08 changes (API-driven frontend, FastAPI services, Qdrant).

---

**Note**: This backlog is based on the outcomes and pending items from Sprint 08, as detailed in `docs/sprints/sprint-08/TASK_BREAKDOWN.md`. It will form the basis for Sprint 09 planning. 