# GPU UMAP Service

A FastAPI microservice providing GPU-accelerated UMAP dimensionality reduction using RAPIDS cuML when available.

## Setup

```bash
pip install -r requirements.txt
uvicorn umap_service.main:app --host 0.0.0.0 --port 8003
```

## Docker

```bash
docker build -t gpu-umap-service .
docker run --gpus all -p 8003:8003 gpu-umap-service
```

## 🛠️ Live-Reload Development with Docker Compose

If you want to iterate on the codebase without rebuilding the image after every change, use the provided `docker-compose.dev.yml` file:

```bash
# From the repository root
# 1. Ensure the shared network exists (only needed once)
docker network create vibe_net || true

# 2. Start the GPU UMAP service in dev mode
docker compose -f backend/gpu_umap_service/docker-compose.dev.yml up --build
```

Key points:

1. **Volume Mount** – The service directory is mounted into the container (`.:/app`), so any file edit on your host instantly appears inside the container.
2. **Uvicorn `--reload`** – The command is overridden to start Uvicorn with auto-reload enabled, so the server restarts automatically on code changes.
3. **GPU Passthrough (Optional)** – The Compose file requests one NVIDIA GPU. Make sure you have the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed. Remove the `deploy.resources` stanza if you just want CPU.
4. **Shared Network** – The service joins the same `vibe_net` network declared in the root `docker-compose.yml`, allowing it to communicate with `qdrant_db` or other services you spin up via `docker compose up`.

To stop the service:

```bash
docker compose -f backend/gpu_umap_service/docker-compose.dev.yml down
```

When you are ready for production benchmarking, switch back to the regular `docker build` / `docker run` workflow described above.

## Endpoints

- `POST /umap/fit_transform` – fit a new UMAP model and return a 2D embedding.
- `POST /umap/transform` – transform new data with the fitted model.
- `POST /umap/cluster` – perform clustering (DBSCAN, HDBSCAN, or KMeans) on provided data.

## Example

```bash
curl -X POST http://localhost:8003/umap/fit_transform \
     -H 'Content-Type: application/json' \
     -d '{"data": [[0.1,0.2],[0.2,0.3]]}'

curl -X POST http://localhost:8003/umap/cluster \
     -H 'Content-Type: application/json' \
     -d '{"data": [[0.1,0.2],[0.2,0.3]], "algorithm": "dbscan"}'
```
