# Sprint 08: Qdrant Integration, Core Feature Delivery & Frontend Refactoring

**Status**: PLANNED  
**Start Date**: 2025-06-01  
**End Date**: 2025-06-28  

## 1. Objectives
1. Achieve full Qdrant integration in backend for search and image listing.
2. Implement Duplicate Detection and Random Image endpoints & UI features.
3. Enable Advanced Filtering, Sorting, and Pagination UI controls.
4. **Refactor key frontend components (`context_sidebar.py`, `latent_space.py`) to exclusively use `service_api.py` for backend communication, enhancing decoupling and UI responsiveness.**
5. Improve Error Handling and UI polish (skeleton screens, feedback, accessibility).
6. Strengthen Testing & Stability (unit, integration, E2E, performance benchmarks).
7. Continue Legacy Code Cleanup and Documentation.

## 2. Key Deliverables
- 📦 Backend services: `/api/v1/search`, `/api/v1/images`, `/api/v1/duplicates`, `/api/v1/random`, **and `/api/v1/vectors/all-for-visualization`**.
- 🖥️ Frontend:
    - Duplicate Detection Tab, Random Image Selector, Filtering/Sorting controls, skeleton/loading states.
    - **Refactored `context_sidebar.py` and `latent_space.py` for API-driven operations.**
- 🧪 Tests: Integration tests for all new endpoints, E2E pipelines, error-case tests, performance benchmarks
- 📚 Documentation: Service API docs, updated architecture diagrams, developer/user guides, CHANGELOG updates reflecting frontend refactoring.
- 🧹 Cleanup: Deprecate legacy modules, remove deprecated scripts, audit session state usage

## 3. Sprint Documents
- 📋 [Product Requirements (PRD)](./PRD.md)
- 🔧 [Technical Implementation Plan](./technical-implementation-plan.md)
- 📑 [Task Breakdown](./TASK_BREAKDOWN.md)
- 🗂️ [Sprint Backlog](./BACKLOG.md)

## Sprint Goals:

1.  **Advanced UI Implementation (Continued):**
    *   ✅ Complete all core UI components for the Advanced UI screen.
    *   ✅ Implement robust data visualization for latent space (ensure it uses `service_api.py`).
    *   🔄 **Refactor UI for Decoupling:** Systematically remove direct model loading, database interactions, and `LazySessionManager` dependencies from UI components. All backend operations must go through `service_api.py`. (Partially Complete, Ongoing)
        *   AppConfig import issues resolved.
        *   `latent_space.py` indentation error fixed by commenting out older logic.
        *   Direct `torch` import removed from `frontend/config.py`.
        *   Removed `LazySessionManager` import from `app_state.py`.
2.  **Performance Optimization:**
    *   🟡 **Initial Load Time:** Address initial slowness observed in the application. (Pending critical bug fix)
    *   🟡 **Component Responsiveness:** Ensure UI remains responsive during backend calls. (Partially Addressed by async calls, further improvements pending)
3.  **Bug Fixing & Stability:**
    *   🔄 **Critical: Ingestion Service Call Failure:** Frontend fails when calling the backend ingestion service. (Under Investigation - Blocker)
    *   🟡 **Investigate Torch Runtime Messages:** Address potential underlying issues with Torch environment or stray frontend imports. (Ongoing)
    *   ✅ Resolve startup crashes related to imports and component errors. (Largely Addressed)
4.  **Backend API Integration & Refinement:**
    *   ✅ Ensure `service_api.py` is the sole interface for frontend-backend communication.
    *   ✅ Implement `get_all_vectors_for_latent_space` endpoint in backend and integrate with frontend. (Assumed done based on previous work, verification pending full app functionality)

### Key Achievements (Update)

- ✅ **Frontend fully decoupled from backend logic:** All legacy model loading, direct database/model access, and background task orchestration have been removed from the frontend.
- ✅ **API-driven UI:** All user actions (folder processing, merging, search, visualization) now trigger backend FastAPI endpoints via `service_api.py`.
- ✅ **Obsolete code and files deleted:** Removed `task_orchestrator.py`, `performance_optimizer.py`, and all direct torch/model imports.
- ✅ **UI code is now minimal, stateless, and maintainable.**

### Roadblocks & Challenges:

*   **Critical Blocker:** The application fails when the frontend attempts to call the backend ingestion service. This needs immediate investigation (requires full frontend error logs and backend service logs).
*   **Performance:** Initial application load time is reported as slow.
*   **Potential Torch Environment Issues:** Lingering `torch` runtime messages in logs need investigation to ensure a clean frontend environment.
*   **Completeness of Decoupling:** Need to systematically verify that all direct backend operations and legacy state management are removed from UI components.

### Next Steps: UI Refactoring

1. **UI/UX Polish & Consistency**
   - Review all UI screens for consistency in style, feedback, and error handling.
   - Ensure all loading, error, and empty states are user-friendly and visually clear.
   - Standardize button placement, sidebar layout, and tab navigation.

2. **Componentization & Reusability**
   - Break down large UI files into smaller, reusable components (e.g., result cards, loaders, error banners).
   - Move repeated UI patterns into shared components.

3. **Async/Await Modernization**
   - Where possible, refactor event loop usage (`asyncio.new_event_loop()`, `run_until_complete`) to use native async/await patterns, especially if Streamlit or your framework supports it.

4. **Accessibility & Responsiveness**
   - Use the `accessibility.py` helpers to audit and improve accessibility (ARIA labels, keyboard navigation, color contrast).
   - Test and refine the UI for different screen sizes and devices.

5. **Testing & Error Handling**
   - Add or update unit/integration tests for UI logic (where possible).
   - Simulate backend failures and ensure the UI degrades gracefully.

6. **Documentation**
   - Update `/docs/services/ui.md` to reflect the new API-driven, stateless frontend architecture.
   - Add code comments and docstrings to new/updated components.

7. **Performance Profiling**
   - Profile the UI for any remaining bottlenecks (e.g., large dataframes, image rendering).
   - Optimize where needed, but avoid premature optimization.

8. **Feature Enhancements**
   - Implement or polish advanced features (duplicate detection tab, random image selector, advanced filtering/sorting) as described in Sprint 08 goals.
   - Ensure all new features use the backend API and follow the new architecture. 