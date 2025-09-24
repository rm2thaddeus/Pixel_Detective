from __future__ import annotations

import os
import sys
import logging
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

from .git_history_service import GitHistoryService
from .temporal_engine import TemporalEngine
from .sprint_mapping import SprintMapper
from .relationship_deriver import RelationshipDeriver
from .data_validator import DataValidator
from .chunk_ingestion import ChunkIngestionService
from .embedding_service import EmbeddingService
from .parallel_ingestion import ParallelIngestionPipeline
from .import_graph_extractor import ImportGraphExtractor


# Configure logging once
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dev_graph_api.log')
    ]
)
logger = logging.getLogger(__name__)


# Environment / connection
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# Disable authentication for open source Neo4j - set password to None
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", None)

REPO_PATH = os.environ.get("REPO_PATH", os.getcwd())

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USER, NEO4J_PASSWORD),
    max_connection_lifetime=30 * 60,
    max_connection_pool_size=50,
    connection_acquisition_timeout=30,
    connection_timeout=30,
    max_transaction_retry_time=30,
)

# Services
git = GitHistoryService(REPO_PATH)
engine = TemporalEngine(driver, git)
sprint_mapper = SprintMapper(REPO_PATH)
deriver = RelationshipDeriver(driver)
validator = DataValidator(driver)
chunk_service = ChunkIngestionService(driver, REPO_PATH)
embedding_service = EmbeddingService(driver)
import_extractor = ImportGraphExtractor(driver, REPO_PATH)
parallel_pipeline = ParallelIngestionPipeline(driver, REPO_PATH, max_workers=8)


__all__ = [
    "logger",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "REPO_PATH",
    "driver",
    "git",
    "engine",
    "sprint_mapper",
    "deriver",
    "validator",
    "chunk_service",
    "embedding_service",
    "import_extractor",
    "parallel_pipeline",
]

