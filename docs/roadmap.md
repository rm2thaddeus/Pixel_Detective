# Project Roadmap

This roadmap outlines planned optimizations, features, and enhancements for the Pixel Detective application, organized by timeline.

---

## Short-term (Next 1–2 Weeks)

0. **Environment Setup**
   - Create and document a Python virtual environment (`.venv`) for dependency management and reproducibility.
   - **Upgrade to CUDA-enabled PyTorch (2.7.0+cu118) and document GPU troubleshooting in README.**

1. **Optimize Image Processing Pipeline**
   - Parallelize metadata extraction in `metadata_extractor.py` using thread pools or asyncio.
   - Batch process images in `pipeline.py` to reduce I/O overhead.

2. **Implement Caching & Checkpointing**
   - Cache extracted metadata and embeddings locally to avoid redundant work on subsequent runs.
   - Add checkpoint files in `scripts/pipeline.py` to resume interrupted indexing.

3. **Improve UI Feedback**
   - Integrate `st.progress` bars and status messages in `app.py` and `ui` components.
   - Display per-folder or per-batch progress during database building.

4. **Lazy Model Loading**
   - Defer CLIP/BLIP model loading in `ModelManager` until first usage.
   - Expose a toggle in `config.py` to control eager vs. lazy loading.

---

## Medium-term (3–6 Weeks)

1. **Refactor Vector Database Operations**
   - Switch to asynchronous Qdrant client in `vector_db.py` for non-blocking upserts and queries.
   - Support bulk upsert and batch query APIs.

2. **Incremental & Resumable Builds**
   - Store ingestion state in the vector DB or in sidecar files to allow incremental updates.
   - Add CLI flags in `scripts/pipeline.py` for full vs. incremental indexing.

3. **8-bit Quantization & Memory Tuning**
   - Expose `bitsandbytes` quantization options in the UI and config.
   - Provide per-model memory usage reports via `utils/cuda_utils.py`.

4. **Containerization & Deployment**
   - Create a Dockerfile for app + dependencies.
   - Publish container image to Docker Hub or GitHub Container Registry.
   - Add Helm chart or Docker Compose for local and cloud deployment.

5. **CI/CD & Automated Testing**
   - Write unit tests for core modules (`models/`, `database/`, `utils/`).
   - Add GitHub Actions workflows for linting, testing, and building the Docker image.

---

## Long-term (1–3 Months)

1. **Multi-User & Collaboration**
   - Integrate authentication (OAuth or API keys).
   - Add per-user image collections and shared projects.

2. **Cloud-Hosted Vector Database**
   - Support hosting Qdrant on a managed cloud service.
   - Implement secure connection and environment-based configuration.

3. **Scalable Storage & Caching**
   - Integrate S3/GCS for large image storage.
   - Use Redis or similar for caching immediate query results.

4. **Real-Time Collaboration**
   - WebSocket-based update streams for collaborative searching and tagging.

5. **Performance Benchmarking & Optimization**
   - Establish baseline benchmarks for ingestion and query latencies.
   - Profile hotspots in Python code and optimize critical paths (C/C++ extensions or offloading).

---

## Backlog & Icebox

- Interactive image annotation and manual caption correction.
- Fine-tune CLIP/BLIP on custom domain datasets.
- Support additional image formats: TIFF, RAW (via `rawpy`).
- UI theming, accessibility, and mobile-responsive design.
- Localization and translation support for multilingual queries.
- Modular plugin system for custom algorithms and data sources. 