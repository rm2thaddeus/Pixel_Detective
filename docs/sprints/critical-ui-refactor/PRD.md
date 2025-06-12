# Product Requirements Document (Critical UI Refactor)

## Objective

Migrate and refactor the existing Streamlit frontend to a scalable Next.js application that meets performance, UX, and real-time requirements.

## Requirements

### Functional Requirements

1. **Home Screen**
   - Display app health/status (ping backend)
   - Options to open existing collection or create new collection
   - Real-time log or progress display for background processes

2. **Tabs Interface**
   - **Search Tab**
     - Text prompt input
     - Image upload support
     - Filters and parameters selection
     - Display top-N results with images and metadata
   - **AI Guessing Game Tab**
     - Show random image from collection
     - Display AI model predictions (captions, tags)
     - Optional user interaction/guessing feature
   - **Latent Space Visualization Tab**
     - Generate 2D projection (UMAP/t-SNE)
     - Interactive map with hover/clickable image points
     - Grouping and navigation controls
   - **Add Images Tab**
     - Folder selection for new images
     - Trigger ingestion pipeline (metadata, embeddings, captions)
     - Real-time progress/log updates via WebSocket

### Non-Functional Requirements

- **Performance:** Initial load < 2s; component updates < 500ms
- **Scalability:** Handle 100,000+ images without UI degradation
- **Accessibility:** WCAG AA compliance for all screens
- **Maintainability:** Modular, well-documented code structure
- **Security:** Validate inputs and secure API/WebSocket connections

## Success Criteria

- Core screens implemented and fully navigable
- Real-time logs and progress indicators functional
- State management stable with minimal bugs
- Consistent, responsive styling across devices
- Linting, unit tests, and integration tests all passing 