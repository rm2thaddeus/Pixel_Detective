import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.ingestion_orchestration_fastapi_app.pipeline.cpu_processor import process_files, cache
from backend.ingestion_orchestration_fastapi_app.pipeline.manager import JobContext

# Pytest mark for async tests
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_job_context():
    """Fixture to create a mock JobContext."""
    ctx = JobContext(job_id="test_job")
    ctx.raw_queue = AsyncMock(spec=asyncio.Queue)
    ctx.ml_queue = AsyncMock(spec=asyncio.Queue)
    ctx.db_queue = AsyncMock(spec=asyncio.Queue)
    return ctx

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear diskcache before each test."""
    cache.clear()

async def test_cpu_worker_cache_miss_success(mock_job_context):
    """
    Tests the successful processing of a new image (cache miss).
    """
    # --- Setup ---
    ctx = mock_job_context
    test_file_path = "/tmp/test.dng"
    test_file_hash = "fake_hash_123"
    collection_name = "test_collection"

    # Mock the file path queue
    async def get_side_effect():
        if not get_side_effect.called:
            get_side_effect.called = True
            return test_file_path
        # Stop the worker loop
        raise asyncio.CancelledError
    get_side_effect.called = False
    ctx.raw_queue.get.side_effect = get_side_effect

    # Mock utilities
    mock_pil_image = Image.new('RGB', (10, 10), color = 'red')

    # Patch the functions that are called
    with patch('backend.ingestion_orchestration_fastapi_app.pipeline.utils.compute_sha256', return_value=test_file_hash) as mock_hash, \
         patch('backend.ingestion_orchestration_fastapi_app.pipeline.image_processing.decode_and_prep_image', return_value=(mock_pil_image, None)) as mock_decode, \
         patch('backend.ingestion_orchestration_fastapi_app.pipeline.utils.extract_image_metadata', return_value={"filename": "test.dng"}) as mock_metadata:
        
        # --- Act ---
        await process_files(ctx, collection_name)

        # --- Assert ---
        # Ensure external functions were called
        mock_hash.assert_called_once_with(test_file_path)
        mock_decode.assert_called_once_with(test_file_path)
        mock_metadata.assert_called_once_with(test_file_path)

        # Ensure the correct payload was put into the ml_queue
        ctx.ml_queue.put.assert_called_once()
        call_args = ctx.ml_queue.put.call_args[0][0]
        
        assert call_args['unique_id'] == test_file_hash
        assert call_args['file_hash'] == test_file_hash
        assert call_args['filename'] == "test.dng"
        assert 'image_base64' in call_args
        assert call_args['collection_name'] == collection_name
        
        # Ensure nothing was put in the db_queue
        ctx.db_queue.put.assert_not_called()

        # Ensure counters are correct
        assert ctx.processed_files == 1
        assert ctx.failed_files == 0
        assert ctx.cached_files == 0

async def test_cpu_worker_decode_failure(mock_job_context):
    """
    Tests how the worker handles a failure in image decoding.
    """
    # --- Setup ---
    ctx = mock_job_context
    test_file_path = "/tmp/broken.jpg"
    test_file_hash = "fake_hash_456"
    collection_name = "test_collection"
    error_message = "Corrupt file"

    async def get_side_effect():
        if not get_side_effect.called:
            get_side_effect.called = True
            return test_file_path
        raise asyncio.CancelledError
    get_side_effect.called = False
    ctx.raw_queue.get.side_effect = get_side_effect

    # Mock utilities to simulate a decoding failure
    with patch('backend.ingestion_orchestration_fastapi_app.pipeline.utils.compute_sha256', return_value=test_file_hash), \
         patch('backend.ingestion_orchestration_fastapi_app.pipeline.image_processing.decode_and_prep_image', return_value=(None, error_message)) as mock_decode:
        
        # --- Act ---
        await process_files(ctx, collection_name)

        # --- Assert ---
        mock_decode.assert_called_once_with(test_file_path)
        
        # Ensure nothing was queued
        ctx.ml_queue.put.assert_not_called()
        ctx.db_queue.put.assert_not_called()

        # Ensure failure is logged and counted
        assert ctx.failed_files == 1
        assert ctx.processed_files == 0
        ctx.add_log.assert_called_with(f"Failed to decode {os.path.basename(test_file_path)}: {error_message}", level="error") 