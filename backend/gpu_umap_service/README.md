# GPU UMAP Service

A FastAPI microservice providing GPU-accelerated UMAP dimensionality reduction using RAPIDS cuML when available.

## Setup

```bash
pip install -r requirements.txt
uvicorn umap_service.main:app --host 0.0.0.0 --port 8001
```

## Docker

```bash
docker build -t gpu-umap-service .
docker run --gpus all -p 8001:8001 gpu-umap-service
```

## Endpoints

- `POST /umap/fit_transform` – fit a new UMAP model and return a 2D embedding.
- `POST /umap/transform` – transform new data with the fitted model.
- `POST /umap/cluster` – perform clustering (DBSCAN, HDBSCAN, or KMeans) on provided data.

## Example

```bash
curl -X POST http://localhost:8001/umap/fit_transform \
     -H 'Content-Type: application/json' \
     -d '{"data": [[0.1,0.2],[0.2,0.3]]}'

curl -X POST http://localhost:8001/umap/cluster \
     -H 'Content-Type: application/json' \
     -d '{"data": [[0.1,0.2],[0.2,0.3]], "algorithm": "dbscan"}'
```
