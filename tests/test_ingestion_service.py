from fastapi.testclient import TestClient
import sys
import os
import pytest

# Add project root to sys.path to allow importing the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# We need to import the app after adjusting the path
# It's better to make the project installable, but this works for now.
from backend.ingestion_orchestration_fastapi_app.main import app

client = TestClient(app)

def test_health_check():
    """
    Tests the /health endpoint to ensure the service is running.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"service": "ingestion-orchestration", "status": "ok"}

# You can add more tests here. For example, a test for the root endpoint:
def test_root():
    """
    Tests the root endpoint /.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Ingestion Orchestration Service is running"}

# To run these tests, you would use pytest from your terminal in the project root:
# > pytest 