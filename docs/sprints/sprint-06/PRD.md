# Sprint 06 PRD: Modular Service Architecture with Docker Compose

**Sprint Duration:** 2025-06-04 to 2025-06-10 (Adjust as needed)
**Sprint Lead:** TBD
**Created:** 2025-05-28
**Last Updated:** 2025-05-28

## Executive Summary

Sprint 05 achieved partial success in UI implementation but highlighted critical performance bottlenecks and architectural limitations due to the application's monolithic nature. The primary learning is that the current architecture cannot sustainably support our performance and scalability goals, especially for data ingestion and ML model serving.

Sprint 06 will address this by initiating a significant architectural refactor. We will begin modularizing the application by decomposing the database building pipeline into a set_of_interconnected, containerized services managed by Docker Compose. This strategic shift aims to improve scalability, maintainability, and deployment flexibility, starting with the most resource-intensive components. The goal is to lay a robust foundation for a high-performance, scalable application.

## Sprint 05 Review & Learnings
- **Partial Successes**:
    - Basic UI screens (FAST_UI, LOADING, ADVANCED_UI) were prototyped.
    - Some progress on stabilizing BLIP captioning.
- **Key Challenges & Learnings**:
    - Startup optimization goals (deferring ML imports, <1s render) were not fully met due to the tight coupling of ML models with the main application thread.
    - The monolithic structure makes it difficult to isolate resource-intensive processes (like model loading and batch processing), impacting overall UI responsiveness and development agility.
    - Scaling individual components (e.g., the ML model serving or database ingestion) is not feasible with the current architecture.
    - A radical shift to a service-oriented architecture is necessary for long-term viability and performance.

## Sprint 06 Objectives
1.  **Design Service Architecture**: Define the boundaries and APIs for:
    *   An ML Inference Service (for CLIP embeddings and BLIP captioning).
    *   A Database Service (Qdrant).
    *   An Ingestion Orchestration Service (to manage the database building workflow, metadata extraction, and interaction between other services).
2.  **Implement ML Inference Service**:
    *   Containerize CLIP and BLIP models using FastAPI.
    *   Expose HTTP endpoints for image embedding and captioning.
3.  **Deploy Database Service**:
    *   Utilize the official Qdrant Docker container.
    *   Configure persistent storage.
4.  **Implement Ingestion Orchestration Service**:
    *   Develop a FastAPI service to handle requests for batch processing.
    *   This service will orchestrate calls to the ML Inference Service for model predictions and the Database Service (Qdrant client) for data storage.
    *   Include metadata extraction logic within this service or as a sub-module.
5.  **Develop Docker Compose Configuration**:
    *   Create a `docker-compose.yml` file to define, configure, and link all services (ML Inference, Database, Ingestion Orchestration).
6.  **Adapt Batch Processing Client**:
    *   Modify the existing `scripts/mvp_app.py` (or create a new client script) to interact with the new Ingestion Orchestration Service via HTTP requests to build/update the database.
7.  **Documentation**:
    *   Document the new service architecture, API endpoints, and `docker-compose` setup.
8.  **Decommissioning Monolithic Components**: 
    *   Identify and document components of the existing monolithic architecture (primarily within `core/`, `models/`, and `components/` related to data ingestion and local ML model management) that are superseded by the new service architecture.
    *   Plan for the phased deprecation and removal of this legacy code in alignment with the successful deployment and verification of the new services. Initial focus is on migrating functionality, with actual file deletions to follow after thorough testing.

## Success Criteria
1.  **Service Functionality**:
    *   ML Inference Service successfully serves embedding and captioning requests via its HTTP API.
    *   Qdrant Database Service is operational, and data can be written to and read from it via the Qdrant client.
    *   Ingestion Orchestration Service can successfully receive a batch request, interact with the ML and Database services, and report completion/errors.
2.  **Docker Compose Integration**:
    *   `docker-compose up` successfully launches all defined services.
    *   Services can communicate with each other as defined (e.g., Ingestion Service can call ML Service and Qdrant).
3.  **Batch Database Building**:
    *   The adapted client script can successfully trigger and complete a database build process by making requests to the Ingestion Orchestration Service.
    *   Data (embeddings, captions, metadata) is correctly stored in Qdrant.
4.  **Isolation**: Heavy ML model loading and processing demonstrably occur *only* within the ML Inference Service container, not in the client script or other services.
5.  **Basic Documentation**: High-level architecture diagram and instructions for running the services with Docker Compose are created.

## Key Stakeholders
- **Product Owner:** TBD
- **Tech Lead:** TBD
- **Development Team:** TBD

## Requirements Matrix (Sprint 06)
| ID        | Requirement                                                     | Priority | Acceptance Criteria                                                                                                |
|-----------|-----------------------------------------------------------------|----------|--------------------------------------------------------------------------------------------------------------------|
| ARC-06-01 | Design service-oriented architecture for database pipeline        | High     | Diagram and API definitions for ML, DB, and Ingestion services complete.                                             |
| SVC-06-01 | Implement ML Inference Service (FastAPI + Docker)               | High     | Serves `/embed` and `/caption` endpoints; models load on startup; containerized.                                   |
| SVC-06-02 | Deploy Qdrant Database Service (Docker)                         | High     | Official Qdrant container runs; persistent storage configured; accessible by other services.                       |
| SVC-06-03 | Implement Ingestion Orchestration Service (FastAPI + Docker)    | High     | Accepts batch requests; calls ML service for inference; calls Qdrant for storage; includes metadata extraction.  |
| INF-06-01 | Create Docker Compose configuration                             | High     | `docker-compose.yml` defines and links all services; `docker-compose up` works.                                  |
| CLI-06-01 | Adapt/Create client for batch DB building via services          | High     | Client script successfully uses Ingestion Service API to build a database.                                           |
| DOC-06-01 | Document new service architecture and Docker Compose setup        | Medium   | README updated with architecture overview and setup instructions.                                                    |

## Definition of Done (Sprint 06)
- All acceptance criteria for Sprint 06 requirements are met.
- Each service has a Dockerfile.
- `docker-compose.yml` is complete and functional.
- The batch database building process using the new services is successfully demonstrated.
- Code for new services and client modifications is reviewed and merged.
- Basic documentation for the new architecture and setup is published.

---
*Self-reflection: Sprint 05's challenges are reframed as drivers for this critical architectural evolution. Sprint 06 focuses on building the backend service infrastructure. Full integration with the Streamlit frontend will likely be a subsequent sprint, building upon this new foundation.* 