# Pixel Detective: AI-Powered Image Search

Pixel Detective is an advanced image search application that uses AI to analyze, caption, and search through your image collection. It combines multiple state-of-the-art AI models to provide a powerful and intuitive image search experience.

## 🚀 **LATEST**: GPU-Optimised Backend & Persistent Collections (Sprint 09)

Pixel Detective's latest sprint delivers massive backend improvements while paving the way for a new UI stack:

* **GPU Batching & Mixed Precision** – Up to 89 % faster inference via dynamic batch sizing and `torch.cuda.amp.autocast`.
* **Persistent Qdrant Collections** – Collections survive restarts; folder-ingestion task runs only on first launch.
* **FastAPI Services Refactor** – Separate Ingestion & ML services with richer progress endpoints.
* **Streamlit Sunset Plan** – Current Streamlit UI enters maintenance mode; reusable UX patterns archived for React/Vite rewrite.
* **Docs Overhaul** – Architecture, status dashboard, and PRDs fully refreshed.

The classic **3-screen Streamlit experience** remains for now:

### Screen 1: Simple Setup 🚀
- **User-focused folder selection** - No technical jargon, just "where are your photos?"
- **Quick start guidance** - Clear instructions and common folder shortcuts
- **Instant validation** - Real-time feedback on folder selection

### Screen 2: Engaging Progress 📊  
- **Excitement-building progress** - "Discovering your photos", "Teaching AI your style"
- **Feature previews** - Shows what's coming to build anticipation
- **Smart time estimates** - User-friendly progress tracking

### Screen 3: Sophisticated Features 🎛️
- **Advanced search** - Natural language and image similarity search
- **AI games** - Interactive photo guessing games  
- **Visual exploration** - UMAP-based similarity visualization
- **Duplicate detection** - Smart photo organization tools

## 🛠️ Technical Architecture

### Component System (NEW - Refined in Sprint 08)
```
frontend/
├── components/
│   ├── search/           # Text search, image search, AI games, duplicates UI
│   ├── visualization/    # UMAP (API-driven), interactive plots
│   └── sidebar/         # Context-aware sidebar content, including adv. filters
├── core/service_api.py # Central API client for all backend communication
└── screens/            # API-driven Streamlit screens (fast_ui, loading, advanced_ui)

backend/
├── ml_inference_fastapi_app/    # Handles ML model inference (CLIP, BLIP)
└── ingestion_orchestration_fastapi_app/ # Handles data ingestion, Qdrant interaction, other core logic

```

### Screen Architecture (API-Driven)
```
screens/
├── fast_ui_screen.py     # ✅ Simplified & user-focused  
├── loading_screen.py     # ✅ Engaging progress experience
└── advanced_ui_screen.py # ✅ Sophisticated with real components
```

## 🔍 Key Features

- **Advanced Hybrid Search**: Combines semantic vector search with metadata filtering using Qdrant's Query API
  - Natural language queries (e.g., "happy family photos")
  - Metadata-aware search (e.g., "camera:canon iso:100")
  - Soft constraint filtering that boosts relevance without restricting results
  - RRF (Reciprocal Rank Fusion) for optimal result ranking
- **AI-Powered Image Search**: Search your image collection using natural language queries (via Qdrant & ML backend)
- **Automatic Image Captioning**: Generate high-quality captions for all your images using BLIP (via ML backend)
- **Semantic Understanding**: Extract meaningful concepts and tags from your images using CLIP (via ML backend)
- **Comprehensive Metadata Extraction**: Extract and index 80+ metadata fields from EXIF/XMP data
  - Camera settings (aperture, ISO, focal length, etc.)
  - Geographic information (GPS coordinates, location names)
  - Temporal data (dates taken, modified, digitized)
  - Technical details (color temperature, white balance, flash settings)
  - Custom tags and keywords
- **RAW/DNG Support**: Full support for DNG (RAW) images. DNG files are processed for both CLIP embeddings and BLIP captions using rawpy and PIL interoperability.
- **GPU Acceleration**: Optimized to run efficiently on consumer GPUs (6GB VRAM minimum recommended)
- **Interactive UI**: User-friendly Streamlit interface with **unified 3-screen experience, now fully API-driven**
- **Latent Space Explorer**: Visualize image embeddings in 2D using UMAP (data via API, UMAP on frontend) with interactive clustering
- **AI Games**: Interactive photo guessing games and challenges (API-driven)
- **Duplicate Detection**: UI to identify and manage duplicate images (backend algorithm finalization in S09)
- **Random Image Selection**: UI and API to fetch and display random images
- **Advanced Filtering & Sorting**: UI controls in sidebar for refining image lists

## 🔍 Enhanced Search Capabilities

Pixel Detective features a sophisticated hybrid search system powered by Qdrant and backend FastAPI services:

1. **Vector Similarity Search**: Semantic understanding of image content using CLIP embeddings
2. **Metadata Filtering**: Precise filtering based on extracted EXIF/XMP metadata
3. **Query Intelligence**: Automatic parsing of complex queries like "sunset photos taken with Canon in 2023"

**Example Queries:**
- `"happy family"` - Semantic search for family photos
- `"camera:canon"` - All photos taken with Canon cameras  
- `"iso:100 aperture:2.8"` - Technical specifications
- `"strasbourg 2023"` - Location and time-based search
- `"landscape sunset"` - Combined semantic and descriptive search

The system uses SHOULD-based logic, meaning queries return relevant results even when specific metadata constraints aren't perfectly matched, ensuring you always discover relevant images.

## 🧠 AI Models

Pixel Detective leverages two powerful AI models:

- **CLIP** (Contrastive Language-Image Pre-training): Creates embeddings that connect images and text in the same semantic space, enabling natural language search
- **BLIP** (Bootstrapping Language-Image Pre-training): Generates detailed captions for images, enhancing searchability and organization

## 📄 Metadata Structure Reference (`metadata.csv`)

The `metadata.csv` file located in this `docs` directory serves as a reference for the expected structure and an example of the metadata that Pixel Detective aims to capture and store in its database for each image. This includes fields extracted from EXIF/XMP data, as well as AI-generated captions and tags. While the application dynamically handles various metadata, this CSV provides a clear example of the comprehensive data points the system works with.

## 📋 Requirements

**Recommended**: Create and activate a Python virtual environment for dependency isolation before installing dependencies:

```
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Unix/macOS
source .venv/bin/activate
```

**Install CUDA-enabled PyTorch (required for GPU acceleration):**

- Visit https://pytorch.org/get-started/locally/ and select your CUDA version (e.g., CUDA 11.8)
- Example for CUDA 11.8:
```
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```
- After install, verify with:
```
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```
- You should see a version like `2.7.0+cu118`, a CUDA version string, and `True` for CUDA availability.

**Troubleshooting:**
- If you see `torch.cuda.is_available() == False`, check your NVIDIA drivers and CUDA installation, and ensure you installed the correct PyTorch version for your CUDA toolkit.
- If you run out of disk space, clear your pip cache with `pip cache purge`.

**Qdrant Vector Database Required for Metadata-Based Filtering and Hybrid Search:**
- For advanced search features (metadata-based filtering, hybrid vector+metadata search), you must have the Qdrant vector database running locally or remotely. The easiest way is via Docker:
```
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```
- Backend FastAPI services (`ml_inference_fastapi_app` and `ingestion_orchestration_fastapi_app`) also need to be running. See their respective `README.md` files in the `backend/` directory for startup instructions.
- If Qdrant or backend services are not running, features will not work and you may see errors or missing results in the UI.

The following packages are required to run this application (see `requirements.txt` in `frontend/` and `backend/` directories for specific service dependencies):

```
torch==2.7.0+cu118
torchvision==0.22.0+cu118
torchaudio==2.7.0+cu118
# ...
```

## 🏢 **Enterprise & Large Collections**

### **For Professional Collections (10k-100k+ Images)**

Pixel Detective includes a powerful **CLI tool** specifically designed for large-scale, professional image processing:

```bash
# Process 100,000+ images efficiently
python scripts/mvp_app.py \
  --folder "/path/to/massive/collection" \
  --batch-size 32 \
  --max-workers 8 \
  --save-summary \
  --watch  # Continuous indexing
```

**Enterprise Features:**
- **🏭 Industrial Scale**: Optimized for 100k+ image collections
- **📸 Professional Formats**: Native RAW/DNG support with `rawpy`
- **🚀 Batch Processing**: Memory-efficient processing with configurable batches
- **🔄 Incremental Updates**: Watch folders for automatic indexing of new images
- **💾 Smart Caching**: Embedding cache prevents reprocessing (SQLite-based)
- **📊 Detailed Reporting**: Comprehensive progress tracking and performance metrics
- **🛡️ Error Recovery**: Graceful handling of corrupted or problematic images
- **🏃‍♂️ Headless Operation**: Perfect for servers and automated workflows

**Performance for Large Collections:**
- **Memory Management**: Models load/unload automatically to prevent OOM
- **Parallel Processing**: Multi-threaded caption generation
- **CUDA Optimization**: Smart GPU memory allocation and cleanup
- **Robust Database**: Direct Qdrant integration with batch upserts

**Use Cases:**
- **Photography Studios**: Process client shoots efficiently
- **Stock Photography**: Index massive image libraries
- **Media Companies**: Organize and search video frame collections  
- **Research Institutions**: Analyze large datasets with AI
- **Digital Asset Management**: Enterprise-scale image organization

---

## 🚀 Quick Start

### 1. Run the Main Application
```bash
streamlit run app.py
```

### 2. Use the 3-Screen Experience
1. **Screen 1**: Enter your image folder path
2. **Screen 2**: Watch the engaging progress as AI processes your photos  
3. **Screen 3**: Explore with advanced search, AI games, and visualization

### 3. Non-Interactive Script (Alternative)
```bash
python scripts/mvp_app.py --folder "C:\Users\aitor\OneDrive\Escritorio\test images" --batch-size 16 --max-workers 4 --query "a cat"
```

---

## 🚧 Development Status

**Current Status: Sprint 08 ✅ COMPLETED**

### ✅ **Sprint 08: Qdrant Integration & Frontend Decoupling**
**COMPLETED** - Successfully integrated Qdrant, delivered key new features, and refactored frontend to be API-driven.

**Key Achievements:**
- ✅ **Qdrant Integration**: Replaced placeholder search/list with Qdrant-powered APIs (`/api/v1/search`, `/api/v1/images`).
- ✅ **New Features (UI & Core API an Frontend Logic)**:
    - Duplicate Detection (UI complete, backend algorithm finalization pending in S09).
    - Random Image selection.
    - Advanced Filtering & Sorting UI and backend support.
- ✅ **Major Frontend Refactor**:
    - All UI screens are now API-driven via `frontend/core/service_api.py`.
    - UI is stateless, enhancing predictability and maintainability.
    - `frontend/components/visualization/latent_space.py` refactored to use API data.
    - Standardized error handling and loading states for new components.
- ✅ **Backend Services**: Established FastAPI services for ML inference and ingestion/orchestration.
- ✅ **Optimized `requirements.txt`** for frontend and backend services.

### ✅ **Sprint 01: UI/UX Architecture Integration** 
**COMPLETED** - Successfully unified dual UI systems into clean 3-screen architecture

**Achievements:**
- ✅ **Simplified Screen 1** - User-focused folder selection (removed technical jargon)
- ✅ **Engaging Screen 2** - Excitement-building progress (replaced boring logs)  
- ✅ **Sophisticated Screen 3** - Integrated all advanced features with graceful fallbacks
- ✅ **Component Architecture** - Extracted and organized sophisticated components
- ✅ **Performance Maintained** - <1s startup preserved throughout transformation

### 🔜 **Sprint 09: Testing, Stabilization & Final Polish** 
**UP NEXT** - Focus on ensuring system robustness, completing pending items, and documentation.

**Planned Focus:**
- 🧪 **Comprehensive Testing**: Unit, integration, and E2E tests for Sprint 08 features and core system.
- ⚙️ **Finalize Duplicate Detection**: Implement the full backend algorithm for duplicate detection.
- 📊 **Performance Benchmarking**: Validate API latencies and UI responsiveness.
- 📄 **Documentation Overhaul**: Update `README.md`, `roadmap.md`, `architecture.md`, and API docs.
- ✨ **Bug Fixing & Polish**: Address issues found during testing.

**Recently Completed (Sprint 08) ✅**
- Qdrant integration for search and image listing.
- New features: Duplicate Detection UI, Random Image, Advanced Filtering & Sorting.
- Major frontend refactor: API-driven, stateless UI, `service_api.py` centralization.
- `latent_space.py` refactor to be API-driven.

**Coming Next (Sprint 09) 🔄**
- Full testing suite implementation.
- Completion of duplicate detection backend.
- Documentation updates.
- Performance validation and final polish.

For detailed development plans, see:
- [`docs/PROJECT_STATUS.md`](./docs/PROJECT_STATUS.md) - Current overall project status
- [`docs/sprints/sprint-08/BACKLOG.md`](./docs/sprints/sprint-08/BACKLOG.md) - Backlog for Sprint 09
- [`docs/sprints/sprint-08/`](./docs/sprints/sprint-08/) - Sprint 08 complete documentation
- [`docs/roadmap.md`](./docs/roadmap.md) - Long-term development roadmap (to be updated for S09)
- [`docs/architecture.md`](./docs/architecture.md) - Technical architecture details (to be updated for S08 changes)