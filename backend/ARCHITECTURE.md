# Vibe Coding – Backend Architecture Specification (June 2025)

> **Scope**  This document describes the high-level architecture of the backend stack located in `/backend`. It is aimed at frontend engineers and new backend contributors who need a concise yet technically detailed overview of how the services fit together.

---

## 1  Service Overview

| Service | Location | Runtime | Responsibilities |
|---------|----------|---------|------------------|
| **Ingestion Orchestration API** | `backend/ingestion_orchestration_fastapi_app` | FastAPI (Python 3.11) | Traverses a local directory, computes hashes, resizes/encodes images if needed, batches them and calls the ML service; writes vectors & metadata to Qdrant; exposes CRUD/query endpoints for the image collection. |
| **ML Inference API** | `backend/ml_inference_fastapi_app` | FastAPI + PyTorch 2 | Runs CLIP & BLIP models on GPU to generate image embeddings & captions; returns results for single images or batches; reports GPU capability info. |
| **Vector DB (Qdrant)** | External container / local native | Rust server | Stores high-dimensional image embeddings plus arbitrary JSON payload; provides similarity search. |
| **Disk Cache** | `backend/.diskcache` (SQLite) | Python `diskcache` | Local on-disk cache used by ingestion service for deduplication and progress persistence. |

---

## 2  API Endpoints

### 2.1  Ingestion Orchestration API (`/api/v1`)

| Method | Path | Request Payload | Response Payload |
|--------|------|-----------------|------------------|
| `POST` | `/ingest/` | `{ directory_path: str }` | `{ job_id: str }` (202 response) |
| `GET` | `/ingest/status/{job_id}` | *–* | `{ job_id, status, progress, logs, result? }` |
| `GET` | `/collections` | *–* | `[ "collection_a", "collection_b", … ]` |
| `POST` | `/collections` | `{ collection_name: str, vector_size?: int, distance?: str }` | `{ message: "created", collection_name }` |
| `DELETE` | `/collections/{collection}` | *–* | `{ message: "deleted", collection_name }` |
| `POST` | `/collections/select` | `{ collection_name: str }` | `{ message: "selected", collection_name }` |
| `POST` | `/collections/cache/clear` | *–* | `{ message: "cache cleared" }` |
| `POST` | `/search` | `{ embedding: float[], filters?: object, limit?: int, offset?: int }` | search results array |
| `GET` | `/images` | query params `page, per_page, filters?, sort_by?, sort_order?` | paginated list |
| `GET` | `/random` | *–* | `{ image, metadata }` |
| `POST` | `/duplicates` | *(optional JSON body for threshold/limit)* | `{ duplicates: [...] }` |

### 2.2  ML Inference API (`/api/v1`)

| Method | Path | Request Payload | Response Payload |
|--------|------|-----------------|------------------|
| `POST` | `/embed` | `{ image_base64: str, filename: str }` | `{ embedding: float[], embedding_shape: int[2] }` |
| `POST` | `/caption` | same as `/embed` | `{ caption: str }` |
| `POST` | `/batch_embed_and_caption` | `{ images: [ { unique_id, image_base64, filename } ] }` | `{ results: [ { unique_id, filename, embedding?, caption?, error? } ] }` |
| `GET` | `/capabilities` | *–* | `{ safe_clip_batch: int }` |

> *Planned*: `/batch_embed_and_caption_multipart` (multipart upload) once roadmap task *C-2* lands.

---

## 3  Database Design

### 3.1  Qdrant Collections (Vector DB)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID / hash (`unique_id`) | Primary point identifier. |
| `vector` | `float[512]` | CLIP embedding (ViT-B/32 FP16). |
| `payload` | JSON | `{ filename, caption?, width, height, created_at, ... }`. |

*Initialization*: Upon first run the ingestion service checks for the configured collection and creates it via Qdrant HTTP API if missing (see `create_collection` endpoint). `vector_size` & `distance` parameters default to *512 / Cosine*.

### 3.2  Disk Cache (dedup/job progress)

`diskcache` automatically creates an SQLite DB (`backend/.diskcache/cache.db`). It stores key/value blobs:

```
CREATE TABLE Cache (
    key BLOB PRIMARY KEY,
    raw INTEGER,
    store_time REAL,
    expire_time REAL,
    access_time REAL,
    access_count INTEGER DEFAULT 0,
    tag BLOB,
    size INTEGER DEFAULT 0,
    mode INTEGER DEFAULT 0,
    filename TEXT,
    value BLOB
);
```

Keys include `sha256:<hash>` (dedup lookup) and `job:<id>:state` (progress snapshots).

### 3.3  ML Inference Service

No persistent database – model weights are loaded at runtime; transient tensors live in GPU memory only.

---

## 4  Inter-service Communication

1. **REST over HTTP** – The ingestion service calls the ML service via `httpx.AsyncClient` at `POST /api/v1/batch_embed_and_caption`.
2. **Batch Size Negotiation** – At startup the ingestion service queries `/api/v1/capabilities` to retrieve `safe_clip_batch` and clamps its own `ML_INFERENCE_BATCH_SIZE` env value.
3. **Vector Storage** – After receiving embeddings & captions, the ingestion service upserts data into **Qdrant** using its Python SDK (gRPC under the hood).
4. **Deduplication** – Ingestion computes SHA-256 hashes locally; misses/hits cached in Disk Cache.

Dependency graph:

```
Ingestion API  →  ML API  →  GPU
        ↘            ↘
          Qdrant      Disk Cache (local)
```

---

## 5  Frontend Integration

Endpoints that the UI (or CLI) may call directly:

* **/ingest/** – kick off a job.
* **/ingest/status/{job_id}** – poll progress.
* **/collections** (GET/POST/DELETE) – manage datasets.
* **/search** – similarity search.
* **/random**, **/images** – gallery views.

### Authentication / Authorization

Currently **none** (services assume trusted LAN). The roadmap lists an *API-Key* mechanism as **Priority 2**; once implemented clients must add header `x-api-key` to protected endpoints.

---

## 6  Architecture Diagram (Mermaid)

```mermaid
graph TD
    subgraph "Clients"
        FE["Frontend (React/Streamlit)"]
        CLI["CLI / cURL"]
    end

    subgraph "Service Layer"
        ING["Ingestion Orchestration API\n(FastAPI, port 8000)"]
        ML["ML Inference API\n(FastAPI + GPU, port 8001)"]
    end

    subgraph "State & Infra"
        VDB["Qdrant Vector DB\n(port 6333)"]
        DKC["Diskcache SQLite"]
        GPU[("NVIDIA GPU")]
    end

    FE -- REST --> ING
    CLI -- REST --> ING

    ING -- "/batch_embed_and_caption" --> ML
    ING -- SDK --> VDB
    ING -- diskcache --> DKC

    ML -- GPU-compute --> GPU

    ML -- "/capabilities" --> ING
```

---

**Revision history**

| Date | Author | Notes |
|------|--------|-------|
| 2025-06-12 | Senior Backend Architect (AI) | Initial architecture spec covering both backend services and data stores. | 