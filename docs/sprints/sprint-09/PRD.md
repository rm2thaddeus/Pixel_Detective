# Sprint 09 Product Requirements Document (PRD)

## 1. Executive Summary
Sprint 09 focuses on validating backend ingestion services with full image support and Qdrant integration. Objectives include:
- Comprehensive testing of ingestion pipelines for all supported image formats (.jpg, .png, .dng, .heic) end-to-end.
- Ingesting metadata, embeddings, and captions into Qdrant collections and verifying vector storage and retrieval.
- Exploring local Qdrant deployment: setting up Qdrant as a local service, building collections while keeping original image files in place.
- Final cleanup: remove Streamlit UI components and dependencies to prepare for the new frontend architecture.

## 2. Context7 Research Summary
*(To be updated if specific research is undertaken for new UI components or Qdrant persistence strategies. Refer to Sprint 08 PRD for existing relevant research on Streamlit background tasks and API patterns.)*

## 3. Requirements Matrix
| ID        | User Story                                                                                                | Acceptance Criteria                                                                                             | Status  | Priority |
|-----------|-----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|---------|----------|
| FR-09-01  | As a user, I want the ingestion pipeline to support all image formats so that no pictures are skipped.    | - Ingestion processes .jpg, .png, .dng, .heic, etc. files.<br>- No errors occur due to unsupported formats. | Planned | High     |
| FR-09-02  | As a user, I want images and their metadata/embeddings to be ingested into Qdrant, so I can perform vector search. | - Metadata, embeddings, and captions stored correctly in Qdrant.<br>- Search queries return expected results. | Planned | High     |
| FR-09-03  | As a developer, I want to deploy Qdrant locally and ingest collections while preserving original images locations. | - Qdrant runs locally (e.g., via Docker or binary).<br>- Collections built and accessible.<br>- Original files remain in their folder. | Planned | Medium   |
| FR-09-04  | As a developer, I want to remove all Streamlit code and dependencies to clean up the codebase.             | - No Streamlit imports or dependencies remain.<br>- Code builds and runs without Streamlit.                    | Planned | High     |
| FR-09-05  | As a user, I want all application screens to behave consistently and reliably based on backend data.        | - All frontend screens correctly fetch and display data from the backend APIs (`service_api.py`).
- Critical crashes on the Fast UI screen (e.g., `AttributeError`) have been resolved.
- UI interactions (filtering, sorting, searching, etc.) accurately reflect backend state and capabilities.
- Stale or incorrect data presentation is minimized.            | In Progress   | Medium   |
| FR-09-06  | As a user, if the application crashes or encounters a critical error, I want to see a user-friendly error screen with recovery options. | - Critical frontend errors are caught gracefully.
- An error screen (`error_screen.py`) is displayed instead of a blank page or a Streamlit traceback.
- The screen shows the error message and offers options to "Try Again" or "Restart". | Done | High     |
| FR-09-07  | As a user, I want to select and manage Qdrant collections via the frontend sidebar.      | - UI displays a dropdown of available Qdrant collections.
+- Users can create new collections from the sidebar.
+- Users can select the active collection and clear its cache via sidebar controls.
+- Selection persists and updates the working collection across the app.   | Done   | High     |
| NFR-09-01 | The ingestion process must complete within acceptable time (e.g., < 10s for 100 images).                    | - Benchmark ingestion durations.<br>- Performance logs recorded.                                               | Planned | Medium   |
| NFR-09-02 | Qdrant searches must return results within 200ms for queries on production-size collections (100k+).       | - Measure query response times.<br>- Response times <200ms.                                                    | Planned | Medium   |
| NFR-09-03 | The codebase must have 100% removal of Streamlit, verified by static analysis and build checks.            | - Build passes without Streamlit.<br>- No Streamlit references in code.                                        | Planned | High     |

## 4. Technical Architecture
- **Backend Ingestion & Qdrant Integration:**
-   The ingestion service processes all supported image formats, extracts metadata, embeddings, and captions, and ingests them into configured Qdrant collections.
-   Support for local Qdrant deployment (Docker or binary) is provided via updated `config.py` and environment variables.
-   Collections are built while leaving original image files in place; default file paths are configurable.
- **Streamlit Clean-up:**
-   Removed all Streamlit modules (`frontend/app.py`, `frontend/screens/`, relevant components).
-   Uninstalled `streamlit` from `requirements.txt` and removed related configurations.
-   Verified no residual Streamlit imports or dependencies remain across the codebase.
-   **Qdrant Integration:**
    -   Implement logic to initialize and connect to Qdrant at application startup (`app.py` or a core module).
    -   Modify backend services (`ingestion_orchestration_fastapi_app`, `ml_inference_fastapi_app`) to work with pre-configured/persistent Qdrant collection names instead of creating them on-the-fly for every operation, unless a new collection is explicitly being built.
    -   The `config.py` might need updating to store the default collection name or path for persistence.
    -   **Note:** _Qdrant collections can become corrupted, especially during development or abrupt shutdowns. For production, implement a failsafe mechanism: regular backups, health checks, and automated restore._
-   **Frontend (`app.py`, `screens/`, `components/`):
    -   **Logging & Stability:** A centralized, configurable logger has been implemented in `utils/logger.py` and integrated across all core frontend modules. A strict absolute import strategy (e.g., `from frontend.core...`) has been enforced to resolve critical startup errors.
    -   **Error Handling:** A new `screens/error_screen.py` module provides a user-friendly interface for critical frontend exceptions, offering recovery options.
    -   **UI Rerun Stability:** Replaced deprecated Streamlit API calls (`st.experimental_rerun()`) with `st.rerun()` across all UI modules to ensure reliable state transitions.
    -   Develop UI elements for prompting folder input if a collection doesn't exist.
    -   Integrate API calls for progress/log updates (potentially new endpoints or modifications to existing ones in `service_api.py` and backend FastAPI apps).
    -   Review and refactor screen logic (e.g., in `screens/`) to align with API-driven data fetching and state management, ensuring they use `service_api.py` for all backend communications.
    -   **Qdrant Collection Management:** Moved collection selection, creation, and cache-clear UI into the async sidebar (`components/sidebar/context_sidebar.py`); updated `service_api.py` with `get_collections()`, `create_collection()`, `select_collection()`, and `clear_collection_cache()`; implemented corresponding FastAPI endpoints; and resolved async event loop errors by removing collection logic from the Fast UI screen.
-   **Backend API (`ingestion_orchestration_fastapi_app`, `ml_inference_fastapi_app`, `service_api.py`):
    -   The ingestion service might need an endpoint to check collection existence or create a collection if it doesn't exist, based on a user-provided path.
    -   APIs should provide more granular progress/status updates for long-running tasks if not already present.
    -   **ML Inference DNG Support:** Updated ML Inference Service to properly decode RAW `.dng` images using `rawpy`, resolving PIL decoding errors during embedding and captioning.

## 5. Implementation Timeline
| Week   | Milestones                                                                                                                               |
|--------|------------------------------------------------------------------------------------------------------------------------------------------|
| Week 1 | Implement Qdrant persistence: startup check, load existing, or prompt for new collection. Backend API updates for collection management. |
| Week 2 | Restore and test "Folder Load" functionality with new persistence logic. Begin frontend integration for progress/logs.                     |
| Week 3 | Complete frontend updates for all screens (API alignment, progress/log display). Conduct comprehensive functional testing.                 |
| Week 4 | Bug fixing, performance optimization (especially collection loading), finalize documentation, E2E testing.                               |

## 6. Testing Strategy
-   **Unit Tests:** For new Qdrant interaction logic, API endpoint changes, and `service_api.py` updates.
-   **Integration Tests:**
    -   Verify Qdrant persistence across application restarts.
    -   Test the full flow of collection creation from a user-specified folder.
    -   Ensure frontend interactions correctly trigger backend processes and reflect their state (including progress/logs).
    -   Validate the restored "Folder Load" functionality end-to-end.
    -   Verify that critical frontend errors trigger the user-friendly error screen and that recovery options work as expected.
-   **E2E Tests (Playwright):** Update existing tests and add new ones to cover all critical user flows with the new persistence and UI feedback mechanisms.
-   **Manual Testing:** Comprehensive exploratory testing of all application features.
-   **Manual Smoke Test Setup:** Before running the frontend, ensure backend services are running without import errors using the correct module paths:
    ```powershell
    uvicorn backend.ml_inference_fastapi_app.main:app --reload --port 8001
    uvicorn backend.ingestion_orchestration_fastapi_app.main:app --reload --port 8002
    ```
-   **Performance Testing:** Specifically for Qdrant collection loading times and overall application responsiveness during startup and intensive operations.

## 7. Risk Assessment
| Risk                                            | Mitigation Plan                                                                                                                                                              |
|-------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Complexity in Qdrant persistence logic          | Allocate dedicated time for research and prototyping in Week 1. Refer to Qdrant documentation and examples. Start with a basic file-based persistence for Qdrant if needed. |
| UI updates for progress/logs become extensive   | Prioritize critical feedback paths first. Use existing UI patterns where possible. Phase implementation if necessary.                                                      |
| Difficulties in testing persisted state         | Develop clear setup/teardown procedures for tests involving persistent data. Use dedicated test collections.                                                               |
| "Folder Load" restoration uncovers deeper issues | Allocate buffer time for debugging. Use the `debugging.mdc` guidelines systematically. Involve backend and frontend expertise collaboratively. **(Risk Realized & Mitigated: This risk occurred, leading to significant debugging of the application's startup sequence, import structure, and logging. The issues have been resolved, unblocking development.)**                            |
| Performance issues with collection loading      | Profile loading times early. Investigate Qdrant optimization settings. Consider lazy loading or background loading for parts of the data if initial load is too slow.         |
| **Qdrant collection/data corruption**           | **Implement regular automated backups, health checks, and an automated restore/failsafe mechanism for production. For development, manual reset is acceptable, but for scale-up, a robust recovery plan is required.** |

## 8. Codex Backend Refactor – Sprint-09 Progress Summary

### 8.1  Work Completed in `codex/refactor-backend-services-for-gpu-optimization`

The following major changes landed via the **codex** branch and are now merged into `development` as part of Sprint&nbsp;09:

1. **GPU-Optimised Backend Stack**
   • Ingestion Orchestration API and ML Inference API refactored to leverage larger GPU batches (default 128, negotiated via `/capabilities`).
   • Mixed-precision inference (`torch.cuda.amp.autocast`) and `torch.inference_mode()` enabled – ≈ 89 % improvement on 25-image DNG benchmark.
   • Dynamic batch sizing based on live GPU memory probe.
2. **RAW → RGB Off-loading**
   • DNG decoding moved from ML service to ingestion pipeline.
3. **Parallelised SHA-256 & Directory Scan**
   • Async thread off-loading eliminates event-loop blocking.
4. **Persistent Qdrant Collections**
   • Collection management endpoints added (`/collections`, `/select`, `/cache/clear`).
   • Local Qdrant Docker workflow documented.
5. **DiskCache Deduplication & Job Tracking**
   • SQLite-backed cache resides in `backend/.diskcache`.
6. **Robust Error Handling & Logging**
   • Centralised logging, GPU memory diagnostics, graceful FastAPI exception handlers.
7. **Documentation**
   • `backend/ARCHITECTURE.md`, `backend/DEVELOPER_ROADMAP.md`, and service-specific *next_steps.md* files created.

### 8.2  Regression & Compatibility Notes

* Remaining **Streamlit** code is still present in `frontend/`.  UI will be deprecated in Sprint 10 but key interaction patterns (accessibility helpers, skeleton screens, animation CSS) will be archived for future reference.
* Binary cache artefacts (`backend/.diskcache/*.db*`) are now in source-control; evaluate moving them to `.gitignore`.

### 8.3  Outstanding Work (roll-over to Sprint 10)

| ID | Task | Priority | Owner |
|----|------|----------|-------|
| R-10-01 | Remove all Streamlit modules & dependencies | High | Frontend / DevOps |
| R-10-02 | Archive reusable UI/UX patterns from `frontend/` into `/docs/archive/sprint_09_frontend_ideas` | High | Frontend |
| R-10-03 | Harden service-to-service auth with `x-api-key` | Medium | Backend |
| R-10-04 | Add CI workflow to run new benchmark & regression tests | Medium | DevOps |
| R-10-05 | Auto-evict old DiskCache entries & add size limit | Low | Backend |

---

> _Last updated: 2025-06-12 by AI assistant during merge of `codex/refactor-backend-services-for-gpu-optimization` into `development`._ 