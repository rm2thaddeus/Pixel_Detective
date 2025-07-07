import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import base64
import io
from PIL import Image
import torch
import sys
import os

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

        # Mock model inference functions
        mock_clip.encode_image_batch.return_value = torch.tensor([[0.1, 0.2, 0.3]])
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
    response = client.post("/api/v1/batch_embed_and_caption", json=payload)

    # --- Assert ---
    assert response.status_code == 200
    result = response.json()['results'][0]
    
    assert result['unique_id'] == "123"
    assert result['error'] is None
    assert result['caption'] == "a test caption"
    assert result['embedding'] is not None
    
    mock_clip, mock_blip = mock_models
    mock_clip.encode_image_batch.assert_called_once()
    mock_blip.generate_captions.assert_called_once()

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
    response = client.post("/api/v1/batch_embed_and_caption", json=payload)

    # --- Assert ---
    assert response.status_code == 200
    result = response.json()['results'][0]

    assert result['unique_id'] == "456"
    assert result['error'] is not None
    assert "Failed to decode image" in result['error']
    assert result['embedding'] is None
    assert result['caption'] is None

    mock_clip, mock_blip = mock_models
    mock_clip.encode_image_batch.assert_not_called()
    mock_blip.generate_captions.assert_not_called() 