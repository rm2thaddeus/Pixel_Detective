# Sprint 08 UI Implementation Plan

This document breaks down the UI tasks for Sprint 08. We will tackle these one by one.

## 1. Enhanced SearchScreen UI (Corresponds to TASK-08-04-02, TASK-08-04-03)

- [x] **Filtering Controls (Sidebar):**
    - [x] Implement `st.multiselect` for selecting tags (static for now, can be dynamic).
    - [x] Implement `st.date_input` for date range filtering.
    - [x] Cache filter options with `@st.cache_data`.
- [x] **Sorting Controls (Sidebar/Main Area):**
    - [x] Implement `st.selectbox` for selecting sort field (e.g., 'created_at', 'name').
    - [x] Implement `st.radio` for sort order (asc/desc).
    - [x] Apply sorting to `list_images_qdrant` calls.
- [x] **Display Results:**
    - [x] Display search/list results (images, metadata) in a grid.
    - [x] Implement pagination for results.
- [x] **Loading/Progress Indicators:**
    - [x] Use `st.spinner` during API calls for search/listing.
    > **Done:** Implemented in `frontend/screens/advanced_ui_screen.py` — Sidebar filtering, sorting, pagination, and results display now live.

## 2. Duplicate Detection UI (Corresponds to TASK-08-02-04)

- [x] **New Tab/Section:**
    - [x] Create a dedicated "Duplicate Detection" tab or section in the Streamlit app.
- [x] **Trigger Detection:**
    - [x] Add a button to trigger the duplicate detection process (calls `get_duplicates_qdrant`).
- [x] **Feedback & Progress:**
    - [x] Use `st.spinner` while waiting for the backend acknowledgment.
    - [x] Display acknowledgment message from the backend.
    - [x] (Future enhancement: If backend provides progress, display `st.progress`. Currently, backend task is fire-and-forget for initial version).
- [x] **Display Results:**
    - [x] Design layout to show groups of duplicate images.
    - [x] Use placeholder containers (`st.empty`) for results that might load incrementally or after a delay.
    - [x] Display images and relevant metadata for each duplicate group.
    - [x] Provide visual indicators for duplicates.
    - [x] Implement a results table or structured layout for duplicate groups.
    > **Done:** Implemented in `frontend/screens/advanced_ui_screen.py` — Tab, trigger button, spinner, and grouped results display now live.

## 3. Random Image UI (Corresponds to TASK-08-03-04)

- [x] **New Component/Section:**
    - [x] Create a "Random Image" component or section (as a new tab in Advanced UI).
- [x] **Fetch Button:**
    - [x] Add a button "Show Random Image".
- [x] **Display Image:**
    - [x] On button click, call `get_random_image_qdrant`.
    - [x] Display the fetched random image using `st.image`.
    - [x] Use `st.empty()` as a placeholder before the image loads or if no image is fetched yet.
    - [x] Display relevant metadata alongside the image.
    > **Done:** Implemented in `frontend/screens/advanced_ui_screen.py` — Tab, button, spinner, image, and metadata display now live.

## 4. General UI Polish & Error Handling (Corresponds to TASK-08-05-02, TASK-08-05-03, TASK-08-05-04)

- [x] **Error Handling (TASK-08-05-02):**
    - [x] All new UI interactions check for `{"error": ...}` in API responses.
    - [x] User-friendly error messages are displayed using `st.error`.
    - [x] "Retry" buttons added for failed API calls where appropriate.
- [x] **Loading States (TASK-08-05-03):**
    - [x] All new API calls have appropriate loading states (`st.spinner`, `st.empty`).
- [x] **Accessibility (Initial Pass) (TASK-08-05-04):**
    - [x] New UI components reviewed for keyboard navigation.
    - [x] ARIA labels added via `st.markdown` for custom tab regions.
    > **Done:** Implemented in `frontend/screens/advanced_ui_screen.py` — Error handling, retry, loading, and accessibility improvements now live for Duplicate Detection and Random Image tabs.

- [x] **Vector Search Integration:**
    - [x] Provide UI element (text input for query, file uploader for image) to generate/get an embedding.
    - [x] Call `get_embedding` from `service_api.py` for text-to-image or image-to-image search.
    - [x] Call `search_images_vector` with the embedding and display results in a grid with pagination.
    > **Done:** Implemented in `frontend/screens/advanced_ui_screen.py` — Vector search (text/image), embedding, and results display now live. 