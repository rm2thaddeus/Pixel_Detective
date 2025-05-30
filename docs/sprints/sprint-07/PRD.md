# Sprint 07 PRD: Service Hardening, UI Integration, and Legacy Cleanup

**Sprint Duration:** YYYY-MM-DD to YYYY-MM-DD (e.g., 2025-06-11 to 2025-06-17)
**Sprint Lead:** TBD
**Created:** YYYY-MM-DD (Current Date)
**Last Updated:** YYYY-MM-DD (Current Date)

## Executive Summary

Sprint 06 successfully established a service-oriented backend for batch image ingestion, including ML inference, database storage, and orchestration. This significantly improved the potential for scalability and maintainability. However, the new services (ML Inference and Ingestion Orchestration) are not yet Dockerized, the image hash cache in the Ingestion Service is in-memory, the Streamlit UI is not yet integrated with these new services, and significant legacy code remains.

Sprint 07 will focus on:
1.  **Dockerizing the Ingestion Orchestration FastAPI service** for consistent deployment and easier management, while the **ML Inference service will be run locally** to optimize development workflow and avoid performance overhead observed with its Dockerization on the development machine.
2.  Implementing a **persistent cache** for the Ingestion Orchestration Service.
3.  Beginning the **integration of the Streamlit UI** with the new backend services.
4.  Continuing the **deprecation and cleanup of legacy code** superseded by the new architecture.
5.  **Preparing for merge to main branch** by ensuring stability and comprehensive testing of the new services.

This sprint aims to solidify the new architecture, make it more robust, and start delivering its benefits to the end-user through UI interaction.

## Sprint 06 Review & Learnings
-   **Successes**:
    -   Functional ML Inference Service (FastAPI).
    -   Functional Ingestion Orchestration Service (FastAPI) with in-memory caching and batching.
    -   Qdrant DB Service operational via Docker.
    -   Client script successfully uses the new services for batch ingestion.
-   **Key Learnings & Carry-overs**:
    -   The FastAPI services need Dockerization for production-like environments and simplified deployment. However, initial attempts to Dockerize the ML Inference service on the primary development machine led to significant overhead (large image size, long build times), making a hybrid approach more suitable for this sprint.
    -   In-memory cache is volatile; a persistent cache is required for robustness.
    -   The UI remains disconnected from the new backend.
    -   Legacy code decommissioning is an ongoing effort.

## Sprint 07 Objectives
1.  **Dockerize Ingestion Orchestration Service & Configure Local ML Service**:
    *   The ML Inference Service (`backend/ml_inference_fastapi_app/`) will be configured to run directly on the host machine.
    *   Create `Dockerfile` for the Ingestion Orchestration Service (`backend/ingestion_orchestration_fastapi_app/`).
    *   Update `docker-compose.yml` to manage Qdrant and the Ingestion Orchestration service. The Ingestion service will connect to the ML service running on the host.
2.  **Implement Persistent Cache**:
    *   Modify the Ingestion Orchestration Service to use a persistent cache mechanism (e.g., SQLite, Redis, or a simple file-based key-value store) for image content hashes.
3.  **Streamlit UI Integration (Phase 1 - Read Operations)**:
    *   Identify key UI components in the Streamlit application that display data now managed by the new services (e.g., image listings, search results).
    *   Develop API endpoints in the Ingestion Orchestration Service (or a new dedicated UI Backend Service if complexity warrants) to serve data required by the UI.
    *   Modify the Streamlit UI to fetch and display data from these new API endpoints. Focus on read operations first (e.g., displaying images and metadata).
4.  **Continue Legacy Code Deprecation (Phase 3 from Sprint 06 Refactor Plan)**:
    *   Systematically review and refactor/remove modules identified in `SPRINT_06_REFACTOR_PLAN.md` (Phase 3) from `core/`, `models/`, and other locations.
    *   Prioritize modules whose functionality is fully covered and tested by the new services.
    *   Ensure remaining parts of `scripts/mvp_app.py` are updated to use new services if they interact with ingestion or data querying.
5.  **Testing and Stability**:
    *   Develop unit and integration tests for the new services and their interactions.
    *   Conduct thorough end-to-end testing of the ingestion pipeline with Dockerized services.
    *   Ensure the system is stable and performs as expected before considering a merge to the main branch.
6.  **Documentation**:
    *   Update `docs/sprints/sprint-06/README.md` if any final details from S06 were missed.
    *   Document the Dockerization setup and persistent cache mechanism.
    *   Document new API endpoints created for UI integration.
    *   Update overall architecture diagrams.

## Success Criteria
1.  **Dockerized Ingestion Service & Local ML Service**:
    *   The ML Inference Service runs successfully on the local host.
    *   `docker-compose up` successfully launches Qdrant and the Ingestion Orchestration Service.
    *   The Dockerized Ingestion Orchestration service communicates correctly with the locally running ML Inference service and the Dockerized Qdrant service.
2.  **Persistent Cache**:
    *   The Ingestion Orchestration Service uses a persistent cache, and cached data survives service restarts.
    *   Cache effectively prevents re-processing of known images.
3.  **UI Integration (Phase 1)**:
    *   [x] At least one key Streamlit UI component (the advanced UI screen) successfully fetches and displays data from the new backend services via HTTP API calls.
    *   [x] The UI is now fully decoupled from local model/DB logic and interacts only via HTTP APIs (using the service API layer).
    *   [ ] Duplicate detection and some advanced features are pending backend endpoint support.
    *   Data displayed is accurate and consistent with the database.
4.  **Legacy Code Reduction**:
    *   At least 2-3 major legacy modules/files (e.g., from `core/` or `models/`) are successfully deprecated and removed or significantly refactored.
    *   Progress on `SPRINT_06_REFACTOR_PLAN.md` Phase 3 is evident.
5.  **System Stability & Testing**:
    *   New unit/integration tests pass.
    *   The full ingestion pipeline works reliably in the Dockerized environment.
    *   No major regressions are introduced.
6.  **Documentation Complete**: All new features, changes, and architectural updates are documented.

## Key Stakeholders
- Product Owner: TBD
- Tech Lead: TBD
- Development Team: TBD

## Requirements Matrix (Sprint 07)
| ID        | Requirement                                                                 | Priority | Acceptance Criteria                                                                                                                                    |
|-----------|-----------------------------------------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| INF-07-01 | Configure ML Inference Service for Local Execution                          | High     | ML Inference service runs directly on the host machine, is accessible, and functions correctly.                                                          |
| INF-07-02 | Dockerize Ingestion Orchestration Service                                   | High     | `Dockerfile` created; service runs in Docker via `docker-compose`; API endpoints functional; connects to ML (on host) and DB (Dockerized) services. |
| INF-07-03 | Update `docker-compose.yml` for hybrid setup                                | High     | `docker-compose.yml` manages Qdrant and Ingestion Orchestration services; Ingestion service configured to connect to local ML service.              |
| SVC-07-01 | Implement Persistent Cache in Ingestion Service                             | High     | Ingestion service uses a persistent key-value store for image hashes; cache survives restarts; performance benefit demonstrable.                      |
| UI-07-01  | Develop API endpoints for UI data needs (Phase 1)                           | High     | New/updated API endpoints in Ingestion Service (or dedicated UI service) provide data for initial UI screens (e.g., image list, basic search).        |
| UI-07-02  | Integrate Streamlit UI with backend services (Phase 1 - Read)               | High     | At least one Streamlit screen fetches and displays data from the new backend API endpoints.                                                              |
| CLEAN-07-01| Continue legacy code deprecation (Phase 3 of S06 Plan)                       | Medium   | Identified legacy modules (min. 2-3) are refactored/removed; `SPRINT_06_REFACTOR_PLAN.md` updated with progress.                                    |
| TEST-07-01| Develop tests for new services and Dockerized environment                   | High     | Unit/integration tests for FastAPI services; E2E tests for Dockerized ingestion pipeline.                                                              |
| DOC-07-01 | Document Sprint 07 changes (Docker, Cache, APIs, Architecture)              | Medium   | READMEs, architecture diagrams, and API documentation updated to reflect Sprint 07 work.                                                                 |

## Definition of Done (Sprint 07)
- All acceptance criteria for Sprint 07 requirements are met.
- The Ingestion Orchestration FastAPI service is Dockerized and managed by `docker-compose`. The ML Inference service runs locally.
- Persistent caching is functional and verified.
- Initial Streamlit UI integration (read operations) is demonstrated.
- Progress on legacy code cleanup is made and documented.
- All new code is reviewed, merged, and accompanied by relevant tests.
- All documentation is updated.
- The system is stable and ready for potential merge to the main branch after this sprint.

---
*Self-reflection: Sprint 07 is crucial for stabilizing the architecture introduced in Sprint 06 and starting to realize its value through UI integration. The decision to run the ML inference service locally during development aims to maintain development velocity by mitigating issues encountered with its Dockerization (large image sizes, extended build times). Successful completion will mark a major milestone towards a robust and scalable application.* 

**Update (Sprint 07 Progress):**
- The advanced UI screen is now fully refactored to use only service API calls for all backend interactions.
- The UI is decoupled from backend logic and communicates exclusively via HTTP APIs.
- Duplicate detection and some advanced features are pending backend endpoint support. 