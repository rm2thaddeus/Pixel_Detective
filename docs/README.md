# Vibe Coding: AI-Powered Media Search Engine

Vibe Coding is an advanced, locally-hosted search engine designed to index and search a personal media library using state-of-the-art AI models. It combines a high-performance backend with a (forthcoming) modern web interface to provide a seamless and powerful user experience.

## 🚀 **LATEST**: Backend Complete, Preparing for New UI (Post-Sprint 09)

The project has recently completed a major backend overhaul, achieving massive performance gains and preparing the application for a new, modern user interface.

*   **GPU-Optimized Backend**: Up to 89% faster inference via dynamic batch sizing and mixed-precision compute.
*   **Persistent Vector Storage**: Robust Qdrant collections that survive restarts, ensuring data persistence.
*   **Decoupled FastAPI Services**: A clean architecture with separate services for ML inference and ingestion orchestration.
*   **Legacy UI Removed**: The original Streamlit UI has been completely deprecated and removed, making way for a modern stack.
*   **Documentation Overhaul**: All backend, sprint, and project-level documentation has been refreshed and is up-to-date.

## 🛠️ Technical Architecture

### System Architecture (Post-Sprint 09)
```
backend/
├── ml_inference_fastapi_app/    # Handles ML model inference (CLIP, BLIP)
└── ingestion_orchestration_fastapi_app/ # Handles data ingestion & Qdrant interaction

utils/
└── service_api.py          # API client for communicating with the backend

docs/
├── backend/                # Detailed backend architecture & roadmap
└── sprints/                 # All sprint documentation, including the next one
```

## 🔍 Key Features (Backend)

The backend is feature-complete and provides a powerful set of APIs for:

-   **Advanced Hybrid Search**: Combines semantic vector search with rich metadata filtering.
-   **Automatic Image Captioning & Tagging**: Uses BLIP and CLIP to generate high-quality, descriptive metadata.
-   **Comprehensive Metadata Extraction**: Extracts over 80 fields from EXIF/XMP data.
-   **RAW/DNG Support**: Natively handles professional camera formats.
-   **GPU Acceleration**: Optimized for high-speed processing on consumer GPUs.
-   **Duplicate Detection**: An API to identify and manage duplicate images.

## 🚧 Development Status

**Current Status: Planning for Sprint 10 ✅**

### ✅ **Sprint 09: Backend Overhaul & Cleanup**
**COMPLETED** - Successfully refactored the entire backend for performance and stability, and removed the legacy frontend.

**Key Achievements:**
-   ✅ Major performance gains from GPU optimization and improved batching.
-   ✅ Complete removal of the Streamlit frontend.
-   ✅ Comprehensive update of all project documentation.

### 🔜 **Sprint 10: Critical UI Refactor**
**UP NEXT** - The next phase of development will focus on building a brand-new frontend using a modern web stack (Next.js, TypeScript, Chakra UI).

**Planned Focus:**
-   🧪 **Build all UI screens** as defined in the [PRD](./sprints/critical-ui-refactor/PRD.md).
-   ⚙️ **Connect to the backend** using the existing `utils/service_api.py`.
-   📊 **Implement a full test suite** to ensure application reliability.

For detailed development plans and status, see:
-   [`docs/PROJECT_STATUS.md`](./PROJECT_STATUS.md) - Current overall project status
-   [`docs/roadmap.md`](./roadmap.md) - Long-term development roadmap
-   [`backend/ARCHITECTURE.md`](./backend/ARCHITECTURE.md) - Detailed backend architecture