import os, sys; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from fastapi.testclient import TestClient
from gpu_umap_service.main import app
import numpy as np

client = TestClient(app)

def test_transform_requires_fit():
    data = np.random.rand(5, 5).tolist()
    response = client.post("/umap/transform", json={"data": data})
    assert response.status_code == 400

    data = np.random.rand(10, 5).tolist()
    fit_resp = client.post("/umap/fit_transform", json={"data": data})
    assert fit_resp.status_code == 200

    response = client.post("/umap/transform", json={"data": data[:5]})
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_cluster_dbscan():
    data = np.random.rand(20, 3).tolist()
    resp = client.post("/umap/cluster", json={"data": data, "algorithm": "dbscan"})
    assert resp.status_code == 200
    labels = resp.json()["labels"]
    assert len(labels) == 20


def test_cluster_hdbscan():
    data = np.random.rand(15, 3).tolist()
    resp = client.post("/umap/cluster", json={"data": data, "algorithm": "hdbscan"})
    assert resp.status_code == 200
    labels = resp.json()["labels"]
    assert len(labels) == 15
