# UI Service Documentation

## 1. Overview
The UI is now fully decoupled from backend logic. All model inference, data processing, and ingestion are handled by backend FastAPI services. The frontend interacts with these services exclusively via `service_api.py` using HTTP APIs. No direct model loading, database access, or local data processing remains in the UI.

---

## 2. Directory Structure
```
components/
├── search/
│   └── search_tabs.py           # Search tabs: text, image, AI games, duplicates
├── visualization/
│   └── latent_space.py          # UMAP, DBSCAN, interactive plots
└── sidebar/
    └── context_sidebar.py       # Context-aware sidebar content

screens/
├── fast_ui_screen.py            # Screen 1: Folder selection
├── loading_screen.py            # Screen 2: Progress and anticipation
└── advanced_ui_screen.py        # Screen 3: Sophisticated features

core/
├── app_state.py                 # 3-screen state management
├── background_loader.py         # Non-blocking progress tracking
└── session_manager.py           # Session state handling
```

---

## 3. Component Descriptions

### `components/search/search_tabs.py`
- **Purpose:** Implements the main search interface, including text search, image search, AI guessing game, and duplicate detection.
- **Inputs:**
    - Search queries (text/image) from user
    - Search results, metadata, and duplicate info from backend APIs
- **Backend Dependencies:**
    - `/api/search` (POST): Submits search queries, receives ranked results
    - `/api/duplicates` (GET): Fetches duplicate detection results
    - `/api/guessing-game` (POST/GET): Handles AI guessing game logic
- **Outputs:**
    - Renders search results, duplicate clusters, and game UI
- **Fallbacks:**
    - Displays user-friendly error messages if API calls fail
    - Shows loading indicators while awaiting responses

### `components/visualization/latent_space.py`
- **Purpose:** Visualizes image embeddings in 2D using UMAP and overlays DBSCAN clustering for interactive exploration.
- **Inputs:**
    - Embedding vectors and metadata from backend
- **Backend Dependencies:**
    - `/api/latent-space-data` (GET): Retrieves embeddings and metadata for visualization
- **Outputs:**
    - Interactive Plotly scatter plot with cluster overlays
- **Fallbacks:**
    - Shows placeholder or error if data is unavailable
    - Handles empty or malformed responses gracefully

### `components/sidebar/context_sidebar.py`
- **Purpose:** Provides context-aware sidebar content, including collection stats, search filters, and user guidance.
- **Inputs:**
    - Collection metadata, search/filter options from backend
- **Backend Dependencies:**
    - `/api/collection-metadata` (GET): Fetches collection stats and metadata
    - `/api/search-filters` (GET): Retrieves available filters and options
- **Outputs:**
    - Renders sidebar controls, stats, and contextual help
- **Fallbacks:**
    - Displays default or minimal sidebar if API data is missing

---

## 4. API Interactions

### Main Endpoints Used by UI Components
| Endpoint                  | Method | Purpose                                 | Used By                                 |
|--------------------------|--------|-----------------------------------------|-----------------------------------------|
| `/api/search`            | POST   | Submit search queries, get results      | search_tabs.py                          |
| `/api/duplicates`        | GET    | Get duplicate detection results         | search_tabs.py                          |
| `/api/guessing-game`     | POST/GET | AI guessing game logic                 | search_tabs.py                          |
| `/api/latent-space-data` | GET    | Get embeddings for visualization        | latent_space.py                         |
| `/api/collection-metadata` | GET  | Get collection stats                    | context_sidebar.py                      |
| `/api/search-filters`    | GET    | Get available search filters            | context_sidebar.py                      |

- **Request/Response:** All endpoints use JSON for requests and responses. Errors are returned with appropriate HTTP status codes and error messages.
- **Usage Patterns:**
    - Search and game endpoints are called on user action (form submit, button click)
    - Visualization and sidebar endpoints are called on screen load or when relevant state changes
    - All calls are async; UI shows loading indicators and disables controls as needed

---

## 5. Data Flow
1. **User Action:** User interacts with UI (e.g., submits a search, selects a tab, adjusts a filter)
2. **API Call:** The relevant component sends an HTTP request to the backend service
3. **Backend Processing:** Backend service (ML Inference, Database, Orchestrator) processes the request and returns data
4. **UI Update:** Component receives response, updates UI (renders results, updates plots, etc.)
5. **Error Handling:** If the API call fails, the component displays an error or fallback UI

---

## 6. Error Handling & Fallbacks
- **API Errors:**
    - If an API call fails (timeout, 5xx, 4xx), the component displays a user-friendly error message and disables affected controls
- **Missing/Incomplete Data:**
    - Components check for required fields in responses and show placeholders or minimal UI if data is missing
- **Service Unavailability:**
    - If a backend service is down, the UI notifies the user and suggests retrying later
- **Graceful Degradation:**
    - The UI is designed to remain usable even if some advanced features are unavailable

---

## 7. Migration Notes
- All direct function calls to model inference, database queries, or batch processing have been replaced with HTTP API requests via `service_api.py`.
- Components now use async requests and handle loading/error states explicitly.
- State management is updated to reflect async data fetching and error propagation.
- All legacy code, background task orchestration, and direct backend logic have been removed from the frontend.

---

## 8. Extending the UI
- **Adding New Components:**
    - Place new components in the appropriate `components/` subdirectory
    - Define new backend API endpoints as needed and document their usage
    - Follow existing patterns for async data fetching, error handling, and user feedback
- **Best Practices:**
    - Keep UI logic decoupled from backend implementation details
    - Use clear, consistent error messages and loading indicators
    - Document all new API interactions in this file and in the backend service docs 