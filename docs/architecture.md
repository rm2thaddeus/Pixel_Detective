# Pixel Detective - System Architecture

**Current Version:** Post-Sprint 11 (October 2025)  
**Status:** Production-Ready Dual Application Platform  
**Last Updated:** October 2025

---

## 🎯 **Executive Summary**

Pixel Detective is a dual-application platform featuring two distinct, production-ready systems:

1. **Pixel Detective (Media Search)**: AI-powered media search engine using CLIP/BLIP models, Qdrant vector database, and GPU-accelerated processing
2. **Dev Graph**: Temporal knowledge graph for tracking code evolution using Neo4j, git history analysis, and semantic linking

Both applications share a modern microservices architecture with Next.js frontends and FastAPI backends, demonstrating advanced full-stack development capabilities.

### **🏗️ Platform Architecture Diagram**

```
┌──────────────────────────────────────────────────────────────────────┐
│                     PIXEL DETECTIVE PLATFORM                          │
├─────────────────────────────────┬────────────────────────────────────┤
│   Application 1: Media Search  │   Application 2: Dev Graph         │
├─────────────────────────────────┼────────────────────────────────────┤
│                                 │                                    │
│  ┌────────────────┐            │  ┌────────────────┐                │
│  │  Next.js UI    │            │  │  Next.js UI    │                │
│  │  (Port 3000)   │            │  │  (Port 3001)   │                │
│  └───────┬────────┘            │  └───────┬────────┘                │
│          │                      │          │                         │
│    ┌─────┴──────┬─────┬────┐  │     ┌────┴─────────┐               │
│    │            │     │    │  │     │              │               │
│  ┌─▼──┐  ┌────▼──┐ ┌▼──┐ ┌▼┐  │  ┌──▼──────────┐ ┌─▼─────┐          │
│  │Ing.│  │  ML   │ │GPU│ │Q│  │  │ Dev Graph   │ │ Neo4j │          │
│  │8002│  │ 8001  │ │8003│ │D│  │  │ API (8080)  │ │7687/74│          │
│  └────┘  └───────┘ └───┘ └─┘  │  └─────────────┘ └───────┘          │
│                                 │                                    │
│  CLIP/BLIP, Qdrant Vector DB   │  Neo4j Graph, Git Analysis         │
└─────────────────────────────────┴────────────────────────────────────┘
```

---

## ✅ **Current System Status**

**Overall Platform Health:** Production-ready dual-application platform. Both applications are stable, scalable, and independently deployable.

**Key Architectural Pillars:**

### **Shared Principles**
-   **Microservices Architecture:** Decoupled services with clear responsibilities
-   **API-Driven Communication:** REST APIs with JSON payloads
-   **Next.js Frontends:** Modern React 18 with App Router
-   **FastAPI Backends:** Async/await, type-safe Python services
-   **Docker Deployment:** Containerized services for consistency

### **Application-Specific**
-   **Pixel Detective:** GPU-accelerated AI/ML with vector search (Qdrant)
-   **Dev Graph:** Temporal graph analysis with relationship tracking (Neo4j)

---

## 🔧 **Core Components**

### **1. Frontend Application (`/frontend`)**

**Technology Stack:**
- **Framework:** Next.js 15 with App Router
- **Language:** TypeScript
- **UI Library:** Chakra UI v3
- **State Management:** React Query (Server State) + Zustand (Client State)
- **Styling:** CSS Modules + Chakra UI Semantic Tokens
- **API Client:** Axios

**Key Features:**
- **Component Architecture:** Modular, single-responsibility components following patterns defined in `.cursor/rules/`.
- **Hydration Safety:** Strict separation of server and client components to prevent hydration errors.
- **Theme System:** Complete dark/light mode support with persistent user preference.
- **Performance:** Optimized image loading with `next/image`, efficient re-renders via React Query.

### **2. Backend Services (`/backend`)**

#### **a. Ingestion Orchestration Service (`/ingestion_orchestration_fastapi_app`)**
- **Purpose:** The primary entry point for the frontend. Manages collections, image ingestion, search operations, and data curation.
- **Port:** 8002
- **Key Responsibilities:**
  - `Collection Management`: CRUD operations for Qdrant collections.
  - `Ingestion Pipeline`: Orchestrates file processing, **dynamically auto-sizes batch parameters on startup and periodically syncs with the ML service to ensure optimal batch sizes and readiness, even if the ML service is slow to start or restarts**.
  - `Search Gateway`: Receives search queries, gets embeddings from the ML service, and queries Qdrant.
  - `Image Serving`: Provides endpoints for retrieving image thumbnails and full-resolution files.
  - `Duplicate Detection`: Manages tasks for finding near-duplicates within a collection.

#### **b. ML Inference Service (`/ml_inference_fastapi_app`)**
- **Purpose:** A dedicated service for handling computationally expensive AI model inferences.
- **Port:** 8001
- **Features:**
  - CUDA-optimized inference for CLIP (embeddings) and BLIP (captioning) models.
  - Dynamic batch sizing to maximize GPU utilization without causing out-of-memory errors (**`SAFE_BATCH_SIZE` auto-probes VRAM at startup**).
  - **CPU thread-pool oversubscription** (default `os.cpu_count()*2`, tunable via `ML_CPU_WORKERS`) for faster image decode.
  - Model caching and lazy-loading strategies to optimize resource usage.
  - Provides simple, stateless endpoints for text embedding, image embedding, and captioning.

#### **c. GPU UMAP Service (`/gpu_umap_service`)**
- **Purpose:** Provides GPU-accelerated dimensionality reduction and clustering for latent space visualization.
- **Port:** 8003
- **Features:**
  - Leverages cuML for high-speed UMAP `fit_transform` and `transform` operations.
  - Offers GPU-accelerated clustering algorithms (DBSCAN, K-Means).
  - Exposes a dedicated API for fitting UMAP models and performing clustering on demand.

### **3. Vector Database (`/database`)**

**Technology:** Qdrant
- **Purpose:** Stores all image embeddings and associated metadata for efficient similarity search.
- **Features:**
  - Persistent, on-disk collections.
  - Supports hybrid search (vector similarity + metadata filtering).
  - Accessed exclusively by the **Ingestion Orchestration Service**.

---

## 🗺️ **Application 2: Dev Graph**

### **Purpose**
Temporal knowledge graph for tracking code evolution, linking documentation to code, and visualizing development over time.

### **Architecture Components**

#### **1. Dev Graph API (`/developer_graph`)**
- **Purpose:** Central FastAPI service for graph ingestion, queries, and data quality.
- **Port:** 8080
- **Key Responsibilities:**
  - **8-Stage Ingestion Pipeline:** Git history → Sprint mapping → Chunking → Symbol extraction → Library discovery → Linking → Embedding → Derivation
  - **Graph Queries:** Cypher-based queries for complex relationships
  - **Quality Auditing:** Data integrity checks and validation
  - **Background Jobs:** Non-blocking ingestion with progress tracking

#### **2. Dev Graph UI (`/tools/dev-graph-ui`)**
- **Purpose:** Interactive visualization and exploration of the knowledge graph.
- **Port:** 3001
- **Technology:** Next.js 14, WebGL2, DeckGL, Chakra UI
- **Key Features:**
  - **Timeline Visualization:** 3D temporal view of code changes
  - **Graph Explorer:** Interactive node and relationship browsing
  - **Sprint Analytics:** Commit and file activity per sprint
  - **Requirement Tracking:** Implementation status monitoring

#### **3. Neo4j Graph Database**
- **Purpose:** Store nodes and relationships representing code, documentation, and their connections.
- **Ports:** 7474 (browser), 7687 (bolt)
- **Current Scale:**
  - **Nodes:** 30,822 (Symbols, Chunks, Files, Commits, Documents, Libraries, Requirements, Sprints)
  - **Relationships:** 255,389 (TOUCHED, MENTIONS_*, IMPLEMENTS, DEPENDS_ON, etc.)
  - **Quality Score:** 100%

### **8-Stage Ingestion Pipeline**

```
Stage 1: Git History        → Extract commits, authors, TOUCHED relationships
Stage 2: Sprint Mapping     → Link commits to sprint windows
Stage 3: Chunking           → Create Document/Chunk nodes, normalize encoding
Stage 4: Symbol Extraction  → Parse classes/functions, DEFINED_IN relationships
Stage 5: Library Discovery  → Extract imports, USES_LIBRARY relationships
Stage 6: Linking            → MENTIONS_* relationships (symbol, file, commit)
Stage 7: Embedding          → [Future] Semantic embeddings for chunks
Stage 8: Derivation         → IMPLEMENTS, DEPENDS_ON, EVOLVES_FROM relationships
```

### **Key Data Model**

**Node Types:**
- `GitCommit`, `File`, `Document`, `Chunk`, `Symbol`, `Library`, `Requirement`, `Sprint`

**Relationship Types:**
- `TOUCHED` (commit → file)
- `MENTIONS_SYMBOL`, `MENTIONS_FILE`, `MENTIONS_COMMIT` (chunk → code)
- `IMPLEMENTS` (requirement → file)
- `DEPENDS_ON` (file → file)
- `USES_LIBRARY` (file → library)

---

## 🔄 **Data Flow & User Workflows**

### **Image Ingestion Pipeline**
1. **User Action:** User uploads images via the Next.js frontend.
2. **API Call:** Frontend sends files to the Ingestion Service (`POST /api/v1/ingest/upload`).
3. **Orchestration (Ingestion Service):**
   a. Saves files to a temporary location.
   b. Batch sizes are **auto-calculated** by `autosize_batches()` based on free RAM and the ML service's capabilities.
   c. Encodes each image to PNG **on the ingestion host** and, if enabled, streams the batch as `multipart/form-data` to `POST /api/v1/batch_embed_and_caption_multipart`; otherwise falls back to the JSON base64 endpoint.
   d. The ML service returns embeddings and captions.
4. **Progress Tracking:** Frontend polls the Ingestion Service (`GET /api/v1/ingest/status/{job_id}`) to display real-time progress.

### **Text Search Workflow**
1. **User Query:** User enters a text query in the frontend search bar.
2. **Frontend Call:** Frontend sends the query to the Ingestion Service (`POST /api/v1/search/text`).
3. **Backend Processing:**
   a. The Ingestion Service sends the text query to the **ML Inference Service** (`POST /api/v1/embed_text`) to get a query vector.
   b. The Ingestion Service uses the returned vector to perform a similarity search in Qdrant.
4. **Response:** The Ingestion Service returns ranked search results to the frontend for display.

### **Latent Space Visualization Workflow**
1. **User Action:** User navigates to the Latent Space page.
2. **Frontend Call:** Frontend requests a UMAP projection from the Ingestion Service (`GET /umap/projection`).
3. **Backend Processing (Ingestion Service):**
   a. Samples data from the active Qdrant collection.
   b. Sends the high-dimensional vectors to the **GPU UMAP Service** (`POST /umap/fit_transform`).
   c. The GPU UMAP service computes the 2D projection and returns it.
4. **Response:** The Ingestion service forwards the 2D points to the frontend for visualization.

---

## 🚀 **Deployment Architecture**

### **Development Environment**

#### **Pixel Detective (Media Search)**
```powershell
# Full stack (recommended)
.\start_pixel_detective.ps1

# Individual services (development mode)
docker compose up -d qdrant_db
uvicorn backend.ingestion_orchestration_fastapi_app.main:app --reload --port 8002
uvicorn backend.ml_inference_fastapi_app.main:app --reload --port 8001
cd frontend && npm run dev
```

**Access:** http://localhost:3000

#### **Dev Graph (Knowledge Graph)**
```powershell
# Full stack (recommended)
.\start_dev_graph.ps1

# Individual services (development mode)
docker compose up -d neo4j_db
uvicorn developer_graph.api:app --reload --port 8080
cd tools/dev-graph-ui && npm run dev
```

**Access:** http://localhost:3001

### **Service Port Mapping**

| Service | Port | Application | Purpose |
|---------|------|-------------|---------|
| **Frontend (Media Search)** | 3000 | Pixel Detective | User interface |
| **Frontend (Dev Graph)** | 3001 | Dev Graph | User interface |
| **Ingestion API** | 8002 | Pixel Detective | Collection & search |
| **ML Inference API** | 8001 | Pixel Detective | CLIP/BLIP models |
| **GPU-UMAP API** | 8003 | Pixel Detective | UMAP clustering |
| **Dev Graph API** | 8080 | Dev Graph | Graph queries |
| **Qdrant** | 6333 | Pixel Detective | Vector database |
| **Neo4j Browser** | 7474 | Dev Graph | Graph UI |
| **Neo4j Bolt** | 7687 | Dev Graph | Database protocol |

### **Production Considerations**
- **Containerization:** All services containerized with Docker
- **Orchestration:** Docker Compose (single-node) or Kubernetes (multi-node)
- **Load Balancing:** Nginx reverse proxy for backend services
- **GPU Requirements:** Pixel Detective benefits from NVIDIA GPU (optional)
- **Database Scaling:** Qdrant Cloud, Neo4j Aura for production

---

## 📁 **Repository Organization**

### **Application Directories**

```
pixel-detective/
├── 🎨 Pixel Detective (Media Search)
│   ├── frontend/                 # Next.js UI (port 3000)
│   └── backend/                  # 3 FastAPI services
│       ├── ingestion_orchestration_fastapi_app/  # Port 8002
│       ├── ml_inference_fastapi_app/              # Port 8001
│       └── gpu_umap_service/                      # Port 8003
│
├── 🗺️ Dev Graph (Knowledge Graph)
│   ├── tools/dev-graph-ui/       # Next.js UI (port 3001)
│   └── developer_graph/           # FastAPI API (port 8080)
│
├── 📚 Shared Resources
│   ├── docs/                     # Project documentation
│   ├── utils/                    # Shared Python utilities
│   ├── database/                 # Database connectors
│   ├── config.py                 # Global configuration
│   └── .cursor/rules/            # AI coding guidelines
│
└── 🔧 DevOps
    ├── docker-compose.yml        # Service orchestration
    ├── start_pixel_detective.*   # Launch scripts
    ├── start_dev_graph.*         # Launch scripts
    └── scripts/                  # Automation & utilities
```

### **Key Shared Components**

-   **`database/`**: Standalone database connectors (`qdrant_connector.py`, etc.) for external scripts
-   **`utils/`**: Utility scripts (`cuda_utils.py`, `duplicate_detector.py`, etc.) for specialized tasks
-   **`scripts/`**: Testing, benchmarking, and development automation tools
-   **`.cursor/rules/`**: AI agent guidelines and coding patterns for consistent development

---

**Architecture Status:** ✅ **Production Ready (Both Applications)**  
**Next Review:** Quarterly architecture review planned  
**Documentation:** Auto-generated API docs at `/docs` endpoints for all services

---

## 🚀 **Recent Performance Enhancements**

### **Pixel Detective Optimizations (Sprint 11)**

The October 2025 batch-size initiative introduced several architecture-level enhancements:

- **RAM- & GPU-Aware Autosizing**: `autosize_batches()` negotiates optimal batch numbers at runtime (no manual tuning)
- **Capabilities Endpoints**: Both ingestion (`/api/v1/capabilities`) and ML inference services expose live limits for dynamic adaptation
- **Thread-Pool Oversubscription**: ML service decoders run on `cpu×2` workers by default for high core utilization
- **Multipart Image Streaming**: Pre-decoded PNG streaming removes base64 overhead and overlaps CPU decode with network I/O
- **Bigger Qdrant Scrolls**: Duplicate scanner now pages 1000 vectors per request (env-tunable), cutting API round-trips by 10×

**Result:** Sustained ingestion throughput increased ~2× on 64 GB, single-GPU workstation.

### **Dev Graph Optimizations (Sprint 11)**

- **8-Stage Unified Pipeline**: Consolidated ingestion into cohesive pipeline with proper stage ordering
- **Background Job Support**: Non-blocking ingestion prevents UI freezes during large operations
- **Batch UNWIND Operations**: Bulk node/relationship creation with optimized Cypher queries
- **Chunk Normalization**: UTF-8 encoding fixes resolved data integrity issues
- **Enhanced Linking**: Automatic PART_OF relationships reduce orphaned requirements

**Result:** Full ingestion completes in ~14.5 minutes with 100% quality score.

---

## 📊 **Platform Statistics**

### **Codebase Metrics**

| Category | Count |
|----------|-------|
| **Total Lines of Code** | ~50,000 |
| **Python Files** | ~200 |
| **TypeScript/JavaScript Files** | ~150 |
| **React Components** | ~80 |
| **API Endpoints** | ~60 |
| **Database Systems** | 2 (Qdrant + Neo4j) |
| **Docker Services** | 8 |
| **Sprints Completed** | 11 |

### **Pixel Detective Statistics**

| Metric | Current State |
|--------|---------------|
| **Search Latency** | ~500ms average |
| **Ingestion Rate** | 60-80 images/minute |
| **GPU Batch Size** | 471 images (auto-probed) |
| **Cache Hit Rate** | > 80% for repeated ingestion |
| **Supported Formats** | JPEG, PNG, WebP, RAW (DNG, CR2, NEF, ARW) |

### **Dev Graph Statistics**

| Metric | Current State |
|--------|---------------|
| **Total Nodes** | 30,822 |
| **Total Relationships** | 255,389 |
| **Quality Score** | 100.0% |
| **Orphaned Nodes** | 7 (0.02%) |
| **Full Ingestion Time** | ~14.5 minutes |
| **Supported Languages** | Python, TypeScript, JavaScript |

---

## 🎯 **Technology Decisions & Rationale**

### **Why This Stack?**

#### **FastAPI (Backend)**
- ✅ Native async/await support for high concurrency
- ✅ Built-in Pydantic validation with type hints
- ✅ Auto-generated OpenAPI documentation
- ✅ Excellent performance (one of fastest Python frameworks)

#### **Next.js (Frontend)**
- ✅ Server components for SEO and performance
- ✅ Modern App Router with React 18
- ✅ Built-in image optimization CDN
- ✅ Full TypeScript support

#### **Qdrant (Vector Database)**
- ✅ Fast vector similarity search
- ✅ Hybrid search (vector + metadata)
- ✅ Easy deployment (single Docker container)
- ✅ Native async Python client

#### **Neo4j (Graph Database)**
- ✅ Graph-native optimizations
- ✅ Expressive Cypher query language
- ✅ Rich APOC algorithm library
- ✅ Built-in visualization UI

#### **CLIP/BLIP (AI Models)**
- ✅ State-of-the-art vision-language models
- ✅ Open source (MIT/Apache licenses)
- ✅ GPU-optimized for fast inference
- ✅ Active research community

---

## 🔮 **Future Roadmap**

### **Pixel Detective**
- [ ] Multi-modal search (text + image + metadata filters)
- [ ] Video frame analysis support
- [ ] User authentication and collection sharing
- [ ] Advanced duplicate detection (perceptual hashing)
- [ ] Cloud deployment (AWS/GCP)

### **Dev Graph**
- [ ] True incremental/delta ingestion
- [ ] Semantic embedding generation (Stage 7)
- [ ] GraphQL API layer
- [ ] Multi-repository support
- [ ] ML-based relationship confidence scoring

### **Platform-Wide**
- [ ] Unified authentication system
- [ ] Cross-application analytics dashboard
- [ ] Kubernetes deployment manifests
- [ ] CI/CD pipeline automation
- [ ] Comprehensive monitoring and alerting

---

## 📚 **Related Documentation**

### **Pixel Detective**
- [Backend Architecture](../backend/ARCHITECTURE.md) - Detailed backend service architecture
- [Frontend Architecture](../frontend/ARCHITECTURE.md) - Frontend component design
- [Backend AGENTS](../backend/AGENTS.md) - Backend development guidelines
- [Frontend AGENTS](../frontend/AGENTS.md) - Frontend development guidelines

### **Dev Graph**
- [Dev Graph Architecture](../developer_graph/architecture.md) - Data model and ingestion pipeline
- [Dev Graph AGENTS](../developer_graph/AGENTS.md) - Development guidelines
- [Route Handlers AGENTS](../developer_graph/routes/AGENTS.md) - API route patterns

### **Project-Wide**
- [README](../README.md) - Project overview and quick start
- [Root AGENTS](../AGENTS.md) - Navigation hub for all guidelines
- [Developer Guide](../DEVELOPER_GUIDE.md) - Comprehensive onboarding
- [Sprint Documentation](sprints/) - Sprint planning and retrospectives

---

**🚀 Built with AI | 🏗️ Microservices Architecture | 🎯 Dual Production-Ready Applications**

*Last Updated: October 2025 (Sprint 11)*

