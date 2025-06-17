# 📖 Architecture Evolution: A Sprint-by-Sprint Journey

This document provides a narrative of the Pixel Detective application's architectural evolution, highlighting key decisions, changes, and milestones from its inception through ongoing development.

---

## 🌱 Initial State & Vision (Pre-Sprint 01)

*(Details of the initial state before Sprint 01, if available, would go here. It was characterized by a fragmented dual UI system.)*

---

## 🚀 Sprint 01: Unified 3-Screen Frontend Architecture

**Theme:** UI/UX Architecture Integration

**Key Goals & Achievements:**
-   **Problem Solved:** Transformed a fragmented dual UI system (original `ui/` sophisticated components + `screens/` basic flow) into a single, coherent 3-screen Streamlit application.
-   **Core Structure:**
    -   Established the `fast_ui_screen.py` (simplified user-focused folder selection), `loading_screen.py` (engaging progress experience), and `advanced_ui_screen.py` (sophisticated features with component integration).
    -   Sophisticated UI functionalities were extracted from the legacy `ui/` directory and reorganized into a new, more modular `frontend/components/` structure (e.g., `search/`, `visualization/`, `sidebar/`).
-   **State Management:** Introduced `frontend/core/app_state.py` for managing transitions between the three screens and `frontend/core/session_manager.py` for session state.
-   **Performance:** Maintained a key performance indicator of <1s application startup time despite major structural changes.
-   **User Experience:** Focused on removing technical jargon and creating a more engaging, user-friendly flow, aligning with `UX_FLOW_DESIGN.md`.
-   **Documentation:** Sprint 01 PRD, technical plan, and completion summary were created, documenting this foundational shift.

**Reference:** `docs/sprints/sprint-01/`

---

## ✨ Sprint 02: Visual Design System & Accessibility

**Theme:** Visual Polish, Accessibility, and Performance Optimization

**Key Goals & Achievements:**
-   **Visual Enhancements:** Implemented a professional, gradient-based visual theme.
-   **User Experience:** Introduced contextual skeleton loading states (`frontend/components/skeleton_screens.py`) to improve perceived performance and user engagement during loading phases.
-   **Accessibility:** Achieved WCAG 2.1 AA compliance (`frontend/components/accessibility.py`), making the application usable for a wider range of users. This involved ARIA labels, keyboard navigation, etc.
-   **Performance:** Further optimized startup time, reportedly achieving 0.001s (significantly exceeding the <1s target) through techniques like lazy loading and critical CSS inlining.
-   **Testing:** Achieved 100% test coverage for new components related to these enhancements.

**Reference:** `docs/sprints/sprint-02/`, `docs/sprints/planning/SPRINT_STATUS.md`

---

## 🛠️ Sprints 03-07: Progressive Enhancements & Backend Foundations (Assumed Broad Strokes)

**Themes:** (Specific themes for these sprints would be based on their respective PRDs)

**Assumed Key Developments (General Architectural Impact):**
-   **Feature Development:** Continued addition of new user-facing features and refinement of existing ones within the established 3-screen frontend architecture.
-   **Backend Services - Initial Stages:** Likely saw the initial design and development of backend services (which would later become the FastAPI apps). This might have involved:
    -   Exploring technologies (FastAPI chosen).
    -   Defining initial API contracts.
    -   Developing core logic for ML model inference and data handling.
-   **Qdrant Exploration & Initial Integration:** First steps towards using Qdrant as the vector database. This could have included schema design, basic CRUD operations, and initial search functionalities.
-   **Refinement of `service_api.py`**: The concept of a dedicated API service layer in the frontend probably started taking shape or was progressively built out during this period, though it was formally solidified in Sprint 08.
-   **Tooling & Utilities:** Development or refinement of shared utilities for image processing, metadata extraction, model management (`models/`, `utils/`, `metadata_extractor.py`, `database/qdrant_connector.py` at the root level might have seen significant work here).

*(Detailed architectural changes for Sprints 03-07 would require reviewing their specific PRDs and completion summaries.)*

**Reference:** `docs/sprints/sprint-03/` through `docs/sprints/sprint-07/`

---

## 🔗 Sprint 08: Solidified API-Driven Architecture & Backend Services

**Theme:** Qdrant Integration, Advanced Features, UI Feedback, Stability, and Documentation.

**Key Architectural Changes & Achievements:**
-   **API-Driven Frontend Solidified:** All frontend-to-backend communication was formally centralized through `frontend/service_api.py`. This marked a critical step in decoupling the frontend UI from direct backend logic.
-   **Decoupled Backend Services (FastAPI):**
    -   Backend functionalities were clearly delineated into standalone FastAPI applications:
        -   `backend/ingestion_orchestration_fastapi_app/`: Responsible for managing the folder ingestion pipeline (metadata, embeddings via ML service, Qdrant upsertion).
        -   `backend/ml_inference_fastapi_app/`: Provided ML model inferences (CLIP, BLIP).
    -   These services provided clear API endpoints (e.g., `/api/v1/search`, `/api/v1/images`, `/api/v1/duplicates`, `/api/v1/random`, `/api/v1/vectors/all-for-visualization`).
-   **Qdrant Integration Matured:** Qdrant was used as the primary vector database, managed via Docker Compose for local development. Backend services interacted with it directly.
-   **Stateless & API-Driven UI Components:** Frontend screens and components (e.g., `latent_space.py`, `context_sidebar.py` for folder ingestion) were updated to be API-driven and stateless, relying on `service_api.py` for data and actions.

**Reference:** `docs/sprints/sprint-08/PRD.md`, `docs/architecture.md` (Post-S08 state)

---

## 🛡️ Sprint 09: Backend Validation, GPU Optimisation & Streamlit Sunset (In&nbsp;Progress)

**Theme:** Recovery, Robustness, and Feature Enhancement.

**Key Architectural Enhancements Delivered / In&nbsp;Progress:**
-   **Persistent Qdrant Collections (✅ Implemented):**
    - Collections now survive restarts.  Startup checks the configured collection name and either loads it or prompts the user to ingest a folder.
    - Ingestion service exposes richer progress logs that the frontend polls.
-   **GPU Batching & Mixed Precision (✅ Implemented):** Dynamic batch sizing and AMP in the ML inference service deliver ~89 % speed-ups.
-   **Enhanced UI Feedback via APIs (✅ Implemented):** Streamlit loading screen polls `/ingest/status` for live progress and error logs.
-   **"Folder Load" Flow Restored:** Background ingestion is fully functional under the new persistent collection mechanism.

**Reference:** `docs/sprints/sprint-09/PRD.md`, `docs/sprints/sprint-09/README.md`, `docs/architecture.md` (S09 in-progress)

---

## 🔮 Future Architectural Considerations (Beyond Sprint 09)

-   **Refined Backend Service APIs**: Continuous iteration on API design based on frontend needs, performance, and error reporting.
-   **Scalability & Performance Tuning**: For both backend services and Qdrant, especially under load and with larger datasets.
-   **Monitoring & Structured Logging**: Implementation across frontend and backend for better operational insight and debugging.
-   **Addressing Legacy Code**: Strategic refactoring or retirement of older top-level utility folders as their functionality is fully absorbed by backend services or `frontend/service_api.py`.
-   **Advanced Caching Strategies**: Explore more sophisticated caching in backend services and potentially in `service_api.py`.
-   **Asynchronous Operations in Frontend**: Further leverage asynchronous patterns in Streamlit (if feasible and beneficial) for non-blocking UI updates tied to backend polling.

This document will be updated as the application continues to evolve. 