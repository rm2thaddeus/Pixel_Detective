# Vibe Coding - System Architecture

**Current Version:** Post-Sprint 10 (December 2024)  
**Status:** Production-Ready Microservices Architecture  
**Last Updated:** December 2024

---

## 🎯 **Executive Summary**

Vibe Coding implements a modern, scalable microservices architecture featuring a Next.js frontend, FastAPI backend services, and Qdrant vector database. The system provides AI-powered media search capabilities with semantic similarity and metadata filtering.

### **🏗️ High-Level Architecture Diagram**

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ Next.js 15      │◄───► │ Ingestion Svc.  │◄───► │ Qdrant          │
│ Frontend        │      │ (FastAPI)       │      │ Vector DB       │
│ (Port 3000)     │      │ (Port 8002)     │      │ (Port 6333)     │
└─────────────────┘      └──────┬───▲──────┘      └─────────────────┘
      ▲                        │   │
      │                        │   │
      │                        ▼   │
┌─────┴───────────┐      ┌─────┴───▼──────┐
│ ML Inference Svc. │      │ GPU UMAP Svc.   │
│ (FastAPI)       │      │ (FastAPI)       │
│ (Port 8001)     │      │ (Port 8003)     │
└─────────────────┘      └─────────────────┘
```

---

## ✅ **Current System Status**

**Overall System Health:** Stable and production-ready. The architecture is composed of decoupled services that allow for independent scaling and development.

**Key Architectural Pillars:**
-   **API-Driven Frontend:** The Next.js application interacts with backend services exclusively through their REST APIs.
-   **Decoupled Backend Services:** Three FastAPI applications manage specific domains: Ingestion/Search, ML Inference, and GPU-accelerated UMAP/Clustering.
-   **Persistent Vector Storage:** Qdrant collections are persistent and loaded at application startup.
-   **GPU Acceleration:** Both the ML inference and UMAP/clustering services are designed to leverage CUDA for high-throughput processing.

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
  - `Ingestion Pipeline`: Orchestrates file processing, calling the ML service for embeddings, and storing results in Qdrant.
  - `Search Gateway`: Receives search queries, gets embeddings from the ML service, and queries Qdrant.
  - `Image Serving`: Provides endpoints for retrieving image thumbnails and full-resolution files.
  - `Duplicate Detection`: Manages tasks for finding near-duplicates within a collection.

#### **b. ML Inference Service (`/ml_inference_fastapi_app`)**
- **Purpose:** A dedicated service for handling computationally expensive AI model inferences.
- **Port:** 8001
- **Features:**
  - CUDA-optimized inference for CLIP (embeddings) and BLIP (captioning) models.
  - Dynamic batch sizing to maximize GPU utilization without causing out-of-memory errors.
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

## 🔄 **Data Flow & User Workflows**

### **Image Ingestion Pipeline**
1. **User Action:** User uploads images via the Next.js frontend.
2. **API Call:** Frontend sends files to the Ingestion Service (`POST /api/v1/ingest/upload`).
3. **Orchestration (Ingestion Service):**
   a. Saves files to a temporary location.
   b. Batches images and sends them to the **ML Inference Service** (`POST /api/v1/batch_embed_and_caption`).
   c. The ML service returns embeddings and captions.
   d. The Ingestion service generates thumbnails.
   e. The Ingestion service upserts the embeddings, captions, thumbnails, and metadata into Qdrant.
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

The entire backend stack (Qdrant, ML Inference, Ingestion, and GPU UMAP services) can be launched with a single, convenient script. This is the recommended approach for local development.

```powershell
# From the project root, this script starts all backend services.
./start_backend.ps1
```

The `start_backend.ps1` script handles all necessary Docker containers and starts the FastAPI services. For a detailed breakdown of what the script does, please refer to the script's source code.

**Note on GPU UMAP Service:** The UMAP service runs within a dedicated Docker container (`gpu_umap_service`) to manage its complex CUDA dependencies. This approach avoids the need for a local Conda environment, ensuring that GPU-accelerated UMAP projections are available consistently across different development machines.

For the frontend, run the following command in a separate terminal:
```bash
# Frontend (Next.js)
cd frontend && npm run dev
```

### **Production Considerations**
- **Containerization:** All services are designed to be containerized using Docker.
- **Orchestration:** Docker Compose is suitable for single-machine deployments, while Kubernetes is recommended for scalable, multi-node production environments.
- **Load Balancing:** A reverse proxy (e.g., Nginx) should be placed in front of the backend services.

---

## 📁 **Supporting Directories**

The following top-level directories are not part of a core frontend or backend service, but contain important code for scripts, utilities, and database management.

-   **`database/`**: Contains a standalone `qdrant_connector.py` module. While the primary backend services manage their own database connections, this module can be used by external scripts or for direct database interaction. It is **not** legacy.
-   **`utils/`**: A collection of miscellaneous utility scripts (`cuda_utils.py`, `duplicate_detector.py`, etc.). These are not integrated into the backend services but can be used for various standalone tasks.
-   **`scripts/`**: Contains various scripts for testing, benchmarking, and development. This includes the legacy command-line application `mvp_app.py`, which is preserved for historical reference.

---

**Architecture Status:** ✅ **Production Ready**  
**Next Review:** Quarterly architecture review planned  
**Documentation:** Auto-generated API docs available at the `/docs` endpoint of each running service.

