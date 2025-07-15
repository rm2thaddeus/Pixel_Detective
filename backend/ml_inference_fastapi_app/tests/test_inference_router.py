import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import base64
import io
from PIL import Image
import time
import sys
import os

# Provide dummy modules if heavy deps missing
for mod_name in ('torch', 'transformers'):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.ml_inference_fastapi_app.main import app

@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_models():
    """Mock the model services to avoid loading real models."""
    with patch('backend.ml_inference_fastapi_app.routers.inference.clip_service') as mock_clip, \
         patch('backend.ml_inference_fastapi_app.routers.inference.blip_service') as mock_blip:
        
        # Mock model status
        mock_clip.get_clip_model_status.return_value = True
        mock_blip.get_blip_model_status.return_value = True

        class DummyTensor:
            def __init__(self, data):
                self._data = data

            def tolist(self):
                return self._data

            @property
            def shape(self):
                return (1, len(self._data[0]))

        mock_clip.encode_image_batch.return_value = DummyTensor([[0.1, 0.2, 0.3]])
        mock_blip.generate_captions.return_value = ["a test caption"]

        yield mock_clip, mock_blip

def create_test_image_base64():
    """Creates a simple red image and returns its base64 representation."""
    img = Image.new('RGB', (10, 10), color = 'red')
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def test_batch_embed_and_caption_success(client, mock_models):
    """
    Tests the happy path for the batch endpoint with a valid image.
    """
    # --- Setup ---
    image_b64 = create_test_image_base64()
    payload = {
        "images": [
            {"unique_id": "123", "image_base64": image_b64, "filename": "test.png"}
        ]
    }

    # --- Act ---
    job_result = {
        "status": "completed",
        "result": {
            "results": [{
                "unique_id": "123",
                "filename": "test.png",
                "embedding": [0.1, 0.2, 0.3],
                "embedding_shape": [1, 3],
                "caption": "a test caption",
                "error": None,
                "model_name_clip": "clip",
                "model_name_blip": "blip",
                "device_used": "cpu"
            }]
        }
    }
    with patch('backend.ml_inference_fastapi_app.routers.inference.scheduler.enqueue_job', return_value='job1'), \
         patch('backend.ml_inference_fastapi_app.routers.inference.scheduler.get_job_status', return_value=job_result):
        response = client.post("/api/v1/batch_embed_and_caption", json=payload)
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        status_resp = client.get(f"/api/v1/status/{job_id}")
        assert status_resp.status_code == 200
        result = status_resp.json()["result"]["results"][0]

    assert result['unique_id'] == "123"
    assert result['error'] is None
    assert result['caption'] == "a test caption"
    assert result['embedding'] is not None



def test_batch_embed_and_caption_decode_failure(client, mock_models):
    """
    Tests that a request with a corrupt base64 string is handled gracefully.
    """
    # --- Setup ---
    payload = {
        "images": [
            {"unique_id": "456", "image_base64": "this is not base64", "filename": "broken.png"}
        ]
    }

    # --- Act ---
    job_result = {
        "status": "completed",
        "result": {
            "results": [{
                "unique_id": "456",
                "filename": "broken.png",
                "embedding": None,
                "embedding_shape": None,
                "caption": None,
                "error": "Failed to decode image",
                "model_name_clip": "clip",
                "model_name_blip": "blip",
                "device_used": "cpu"
            }]
        }
    }
    with patch('backend.ml_inference_fastapi_app.routers.inference.scheduler.enqueue_job', return_value='job2'), \
         patch('backend.ml_inference_fastapi_app.routers.inference.scheduler.get_job_status', return_value=job_result):
        response = client.post("/api/v1/batch_embed_and_caption", json=payload)
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        status_resp = client.get(f"/api/v1/status/{job_id}")
        assert status_resp.status_code == 200
        result = status_resp.json()["result"]["results"][0]

    assert result['unique_id'] == "456"
    assert result['error'] is not None
    assert "Failed to decode image" in result['error']
    assert result['embedding'] is None
    assert result['caption'] is None

