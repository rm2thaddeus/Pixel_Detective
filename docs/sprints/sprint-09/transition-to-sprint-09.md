# 🚀 Transition to Sprint 09: Project Plan

## 1. Sprint Theme & Goals
**Theme:**  
> **Recovery and Robustness:** Restore all core user flows (especially "folder load"), ensure API-driven architecture is stable, and improve error handling and test coverage.

**Primary Goals:**
- Restore and robustly test all critical features broken or degraded by the recent refactor.
- Ensure seamless UI → API → backend roundtrip for all user actions.
- Add/restore user feedback for errors and edge cases.
- Strengthen integration and end-to-end testing.

---

## 2. Backlog Refinement

### High Priority
- **TASK-09-01:** Restore "Folder Load" functionality (UI → API → backend).
  - Diagnose and fix the broken flow.
  - Ensure user feedback for errors.
  - Add integration tests for this flow.
- **TASK-09-02:** Expand integration tests for all major user flows (search, duplicate detection, random image, filtering).
- **TASK-09-03:** Ensure all API endpoints are covered by unit and integration tests.
- **TASK-09-04:** Add robust error handling and user feedback for all critical UI actions.

### Medium Priority
- **TASK-09-05:** Performance benchmarking of key endpoints and flows.
- **TASK-09-06:** UI polish and bug fixes identified during Sprint 08/09 testing.

### Low Priority
- **TASK-09-07:** Documentation updates (API docs, architecture diagrams, changelogs).
- **TASK-09-08:** Cleanup of legacy modules and code.

---

## 3. Key Action Items

- **A. Diagnose and Fix "Folder Load"**
  - Trace the UI action to the backend.
  - Ensure the API endpoint exists and is reachable.
  - Add error handling and user feedback.
  - Write integration tests for this flow.

- **B. Test All Major Flows**
  - Manual and automated (integration/E2E) testing for:
    - Search
    - Duplicate detection
    - Random image
    - Filtering

- **C. Error Handling**
  - Ensure all user actions provide clear feedback on failure.
  - Log errors for debugging.

- **D. Documentation**
  - Update `/docs/sprints/sprint-09/transition-to-sprint-09.md` (or similar).
  - Update `/docs/CHANGELOG.md` with major changes and fixes.

---

## 4. Sprint Rituals & Standards

- **Daily Standups:** Focus on blockers for recovery tasks.
- **Code Reviews:** Emphasize test coverage and error handling.
- **Demo/Review:** Show restored flows and improved robustness.

---

## 5. Detailed Task List: Frontend-Backend Integration User Stories

Based on the primary goals, we need to ensure the following user flows are fully restored and robust, with clear UI-API-Backend communication and error handling.

### Core User Flows (High Priority)

**Flow: Folder Load**
-   **User Story:** As a user, I want to select a folder in the UI and see its image contents displayed, so that I can browse my image collection.
    -   **Details:**
        -   UI component allows user to select a folder path.
        -   Frontend sends the selected folder path to the backend API's folder loading endpoint.
        -   Backend processes the path, reads image files (or relevant data), and handles potential file system errors (permissions, invalid path).
        -   API returns a list of image data (paths, metadata) or a clear error message if loading fails.
        -   Frontend receives the data and displays image previews/information.
        -   Frontend displays user-friendly error messages for API failures, invalid paths, or backend processing issues.

**Flow: Search**
-   **User Story:** As a user, I want to enter a search query in the UI and see matching images displayed, so that I can quickly find specific images in my loaded collection.
    -   **Details:**
        -   UI provides a search input field.
        -   Frontend sends the search query to the backend API's search endpoint.
        -   Backend performs the search within the currently loaded image data.
        -   API returns a list of image data that matches the query or indicates no results found.
        -   Frontend receives the search results and updates the displayed images.
        -   Frontend handles potential API errors during the search request and provides feedback.

**Flow: Duplicate Detection**
-   **User Story:** As a user, I want to initiate duplicate detection from the UI and see groups of duplicate images, so that I can manage my storage space.
    -   **Details:**
        -   UI element (button/menu item) triggers duplicate detection.
        -   Frontend sends a request to the backend API's duplicate detection endpoint.
        -   Backend initiates the duplicate detection process.
        -   API provides updates on the detection progress (if applicable) and returns the results, grouped by duplicate sets.
        -   Frontend receives the results and displays the duplicate groups clearly.
        -   Frontend provides feedback during the potentially long-running detection process and handles errors if the process fails.

**Flow: Random Image**
-   **User Story:** As a user, I want to request a random image from the loaded collection via the UI, so that I can serendipitously discover images.
    -   **Details:**
        -   UI element (button) triggers a random image request.
        -   Frontend sends a request to the backend API's random image endpoint.
        -   Backend selects a random image from the available data.
        -   API returns the selected image data.
        -   Frontend receives and displays the random image.
        -   Frontend handles errors, such as requesting a random image from an empty collection.

**Flow: Filtering**
-   **User Story:** As a user, I want to apply filters (e.g., by tag, date, size) in the UI and see only the images that match, so that I can refine my view of the collection.
    -   **Details:**
        -   UI provides filtering options.
        -   Frontend sends the selected filter criteria to the backend API's filtering endpoint.
        -   Backend applies the filters to the currently loaded image data.
        -   API returns the filtered list of image data.
        -   Frontend receives the filtered results and updates the displayed images.
        -   Frontend handles potential errors during the filtering request or if invalid filters are applied.

### Backend API and Logging Enhancements (Ingestion Service) - NEW

**Goal:** Enable the backend to provide detailed, real-time progress and logs for ingestion jobs, consumable by the frontend.

**Task: Implement Real Job Management & Background Processing for Ingestion**
-   **User Story:** As a backend developer, I want the `/api/v1/ingest/` endpoint to initiate folder ingestion as a background task and return a `job_id` immediately, so that the API is non-blocking.
    -   **Details:**
        -   Modify `ingest_directory_v1` (or its equivalent) to use FastAPI's `BackgroundTasks` or a similar mechanism.
        -   Generate a unique `job_id` for each ingestion request.
        -   Store initial job status (e.g., "pending") associated with the `job_id`.

**Task: Implement Persistent Job State Storage (Status, Progress, Logs)**
-   **User Story:** As a backend developer, I want to store the status, progress percentage, and detailed log messages for each ingestion job, so that this information can be retrieved later.
    -   **Details:**
        -   Choose a storage mechanism for job state (e.g., in-memory dictionary for simplicity, Redis for scalability).
        -   The background ingestion task must update this store with:
            -   Current status (e.g., "processing", "completed", "failed").
            -   Progress percentage (e.g., based on files processed / total files).
            -   A list of log messages (strings) detailing its operations and any errors.

**Task: Enhance Ingestion Task Logging**
-   **User Story:** As a backend developer, I want the ingestion background task to capture detailed operational logs (e.g., file being processed, ML service calls, errors), so that users can see fine-grained progress.
    -   **Details:**
        -   Leverage existing `logger` calls within the ingestion logic.
        -   Ensure these log messages are collected and associated with the correct `job_id` in the persistent job state.
        -   Logs should include timestamps and clear descriptions of actions or errors.

**Task: Update `/ingest/status/{job_id}` Endpoint for Real Data**
-   **User Story:** As a backend developer, I want the `/api/v1/ingest/status/{job_id}` endpoint to return the actual status, progress, and detailed logs for the specified job, so that the frontend can display this information.
    -   **Details:**
        -   Modify `get_ingestion_status_v1` to retrieve job information from the persistent store using the `job_id`.
        -   Populate the `JobStatusResponse` model:
            -   `status` with the current job status.
            -   `progress` with the current progress percentage.
            -   `message` field should contain the collected log messages (e.g., as a newline-separated string or a JSON string representing a list of logs). Consider adding a new `logs: List[str]` field if more structured logs are preferred, but update frontend accordingly.
        -   Handle cases where the `job_id` is not found.

This detailed list will help guide the implementation and testing efforts for Sprint 09. 