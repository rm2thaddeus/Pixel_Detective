"""FastAPI service exposing Developer Graph queries."""
from __future__ import annotations

import os
import re
import time
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Query, HTTPException
import logging
import os as _os_mod
import sys
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

# Phase 1 additions
from .git_history_service import GitHistoryService
from .temporal_engine import TemporalEngine
from .sprint_mapping import SprintMapper
from .enhanced_ingest import EnhancedDevGraphIngester
from .enhanced_git_ingest import EnhancedGitIngester
from .relationship_deriver import RelationshipDeriver
from .data_validator import DataValidator
from .chunk_ingestion import ChunkIngestionService
from .embedding_service import EmbeddingService
from .parallel_ingestion import ParallelIngestionPipeline
from .models import (
    WindowedSubgraphResponse, 
    CommitsBucketsResponse, 
    AnalyticsResponse, 
    HealthResponse, 
    StatsResponse
)

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dev_graph_api.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Developer Graph API", version="1.0.0")

# Add CORS middleware to allow frontend access
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_env_origins = os.environ.get("CORS_ORIGINS")
_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# Disable authentication for open source Neo4j - set password to None
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", None)  # No auth needed for open source

_driver = GraphDatabase.driver(
    NEO4J_URI, 
    auth=(NEO4J_USER, NEO4J_PASSWORD),
    max_connection_lifetime=30 * 60,  # 30 minutes
    max_connection_pool_size=50,
    connection_acquisition_timeout=30,  # 30 seconds
    connection_timeout=30,  # 30 seconds
    max_transaction_retry_time=30  # 30 seconds
)

# Initialize Git history service
REPO_PATH = os.environ.get("REPO_PATH", os.getcwd())
_git = GitHistoryService(REPO_PATH)
_engine = TemporalEngine(_driver, _git)
_sprint = SprintMapper(REPO_PATH)
_deriver = RelationshipDeriver(_driver)
_validator = DataValidator(_driver)
_chunk_service = ChunkIngestionService(_driver, REPO_PATH)
_embedding_service = EmbeddingService(_driver)
_parallel_pipeline = ParallelIngestionPipeline(_driver, REPO_PATH, max_workers=8)


@app.get("/api/v1/dev-graph/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint to verify API and database connectivity."""
    try:
        # Test Neo4j connection
        with _driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        # Compose metrics
        from datetime import datetime
        metrics = _engine.get_metrics() if hasattr(_engine, "get_metrics") else {}
        # Try to fetch approximate memory usage if psutil is present
        mem_mb = 0.0
        try:
            import psutil, os as _os
            mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_000_000.0
        except Exception:
            mem_mb = 0.0
        return {
            "status": "healthy",
            "service": "dev-graph-api",
            "version": "1.0.0",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "avg_query_time_ms": metrics.get("avg_query_time_ms", 0),
            "cache_hit_rate": metrics.get("cache_hit_rate", 0),
            "memory_usage_mb": round(mem_mb, 2),
        }
    except Exception as e:
        from datetime import datetime
        return {
            "status": "unhealthy",
            "service": "dev-graph-api", 
            "version": "1.0.0",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@app.get("/api/v1/dev-graph/stats", response_model=StatsResponse)
def get_stats():
    """Get basic statistics about the developer graph."""
    try:
        with _driver.session() as session:
            # Get basic counts first
            total_nodes = session.run("MATCH (n) RETURN count(n) as total").single()["total"]
            total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as total").single()["total"]
            recent_commits = session.run("""
                MATCH (c:GitCommit)
                WHERE c.timestamp >= datetime() - duration('P7D')
                RETURN count(c) as total
            """).single()["total"]
            
            # Get node type counts
            node_stats = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN label as type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            # Get relationship type counts
            rel_stats = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            # Process node types from the query results
            node_type_counts = {}
            for stat in node_stats:
                if stat and stat.get("type") and stat.get("count"):
                    node_type_counts[stat["type"]] = stat["count"]
            
            # Process relationship types from the query results
            rel_type_counts = {}
            for stat in rel_stats:
                if stat and stat.get("type") and stat.get("count"):
                    rel_type_counts[stat["type"]] = stat["count"]
            
            # Transform node stats to match frontend expectations
            node_types = []
            colors = ['blue', 'green', 'purple', 'orange', 'red', 'teal', 'pink', 'yellow']
            sorted_node_types = sorted(node_type_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (node_type, count) in enumerate(sorted_node_types):
                node_types.append({
                    'type': node_type,
                    'count': count,
                    'color': colors[i % len(colors)]
                })
            
            # Transform relationship stats to match frontend expectations
            relationship_types = []
            sorted_rel_types = sorted(rel_type_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (rel_type, count) in enumerate(sorted_rel_types):
                relationship_types.append({
                    'type': rel_type,
                    'count': count,
                    'color': colors[i % len(colors)]
                })
            
            return {
                "summary": {
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "recent_commits_7d": recent_commits
                },
                "node_types": node_types,
                "relationship_types": relationship_types,
                "timestamp": "2025-01-05T09:00:00Z"
            }
    except Exception as e:
        return {
            "error": f"Failed to retrieve stats: {str(e)}",
            "timestamp": "2025-01-05T09:00:00Z"
        }


def run_query(cypher: str, **params):
    with _driver.session() as session:
        result = session.run(cypher, params)
        return [r.data() for r in result]


def extract_id_from_node_data(node_data):
    """Extract a meaningful, stable ID from node data."""
    # Prefer explicit uid if present
    try:
        if isinstance(node_data, dict) and node_data.get('uid'):
            return str(node_data['uid'])
    except Exception:
        pass
    if hasattr(node_data, 'id'):
        return str(node_data.id)
    if not isinstance(node_data, dict):
        return str(hash(str(node_data)))[:8]

    # Requirement-style explicit IDs
    if 'id' in node_data:
        return str(node_data['id'])

    # Git commit nodes with hash
    if 'hash' in node_data:
        return str(node_data['hash'])

    # Sprint nodes with number
    if 'number' in node_data:
        return f"sprint-{node_data['number']}"

    # Document nodes with path
    if 'path' in node_data:
        import os as _os
        base = _os.path.splitext(_os.path.basename(str(node_data['path'])))[0]
        # include a short hash of the full path to avoid collisions
        import hashlib as _hashlib
        h = _hashlib.md5(str(node_data['path']).encode()).hexdigest()[:6]
        return str(node_data.get('uid') or f"doc-{base}-{h}")

    # Description-only nodes
    if 'description' in node_data:
        import hashlib as _hashlib
        desc_hash = _hashlib.md5(node_data['description'].encode()).hexdigest()[:8]
        return f"desc-{desc_hash}"

    # Fallback
    return str(hash(str(node_data)))[:8]


@app.get("/api/v1/dev-graph/nodes")
def get_nodes(node_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    if node_type:
        cypher = f"MATCH (n:{node_type}) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    else:
        cypher = "MATCH (n) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    records = run_query(cypher, limit=limit, offset=offset)
    
    nodes = []
    for r in records:
        node_data = r["n"]
        labels = r.get("labels", [])
        node_id = extract_id_from_node_data(node_data)
        
        # Convert node data to a clean dictionary
        if isinstance(node_data, dict):
            clean_data = {k: v for k, v in node_data.items() if v is not None}
        else:
            clean_data = {"raw": str(node_data)}
        
        # Derive a friendly node type for UI coloring
        # Prefer explicit labels over heuristics to avoid classifying File as Document
        label_set = set(labels or [])
        if "File" in label_set:
            node_type_guess = "File"
        elif "Commit" in label_set or "GitCommit" in label_set:
            node_type_guess = "Commit"
        elif isinstance(node_data, dict) and str(node_data.get("id", "")).startswith(("FR-", "NFR-")):
            node_type_guess = "Requirement"
        elif isinstance(node_data, dict) and "number" in node_data:
            node_type_guess = "Sprint"
        elif isinstance(node_data, dict) and "path" in node_data:
            node_type_guess = "Document"
        elif isinstance(node_data, dict) and str(node_data.get("id", "")).startswith("goal-"):
            node_type_guess = "Goal"
        else:
            node_type_guess = (labels[0] if labels else "Unknown")

        nodes.append({
            "id": node_id,
            "labels": labels,
            "type": node_type_guess,
            **clean_data
        })
    
    return nodes


@app.get("/api/v1/dev-graph/nodes/count")
def count_nodes():
    rec = run_query("MATCH (n) RETURN count(n) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}


@app.get("/api/v1/dev-graph/relations")
def get_relations(start_id: Optional[int] = None, rel_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    cypher = "MATCH (a)-[r]->(b)"
    clauses = []
    if start_id is not None:
        clauses.append("id(a)=$sid")
    if rel_type:
        clauses.append("type(r)=$rt")
    if clauses:
        cypher += " WHERE " + " AND ".join(clauses)
    # Also return relationship timestamp when present to aid timeline visualizations
    cypher += " RETURN a, r, b, type(r) AS rt, r.timestamp AS ts SKIP $offset LIMIT $limit"
    records = run_query(cypher, sid=start_id, rt=rel_type, limit=limit, offset=offset)
    
    out = []
    for r in records:
        a_data = r["a"]
        b_data = r["b"]
        r_data = r["r"]
        r_type_explicit = r.get("rt")
        r_ts = r.get("ts")
        
        # Extract meaningful IDs
        a_id = extract_id_from_node_data(a_data)
        b_id = extract_id_from_node_data(b_data)
        
        # Skip links with hash-based IDs (these are usually invalid)
        if a_id.isdigit() or (a_id.startswith('-') and a_id[1:].isdigit()):
            continue
        if b_id.isdigit() or (b_id.startswith('-') and b_id[1:].isdigit()):
            continue
        
        # Extract relationship type
        if r_type_explicit:
            r_type = r_type_explicit
        elif hasattr(r_data, 'type'):
            r_type = r_data.type
        elif isinstance(r_data, dict):
            r_type = r_data.get("type", "RELATES_TO")
        else:
            # Try to extract type from string representation
            r_str = str(r_data)
            if "PART_OF" in r_str:
                r_type = "PART_OF"
            elif "IMPLEMENTS" in r_str:
                r_type = "IMPLEMENTS"
            elif "DEPENDS_ON" in r_str:
                r_type = "DEPENDS_ON"
            elif "EVOLVES_FROM" in r_str:
                r_type = "EVOLVES_FROM"
            elif "REFERENCES" in r_str:
                r_type = "REFERENCES"
            elif "TOUCHED" in r_str or "TOUCHES" in r_str:
                r_type = "TOUCHED"
            elif "USES" in r_str:
                r_type = "USES"
            elif "PROTOTYPED_IN" in r_str:
                r_type = "PROTOTYPED_IN"
            else:
                r_type = "RELATES_TO"
        
        rel_obj = {
            "from": a_id,
            "to": b_id,
            "type": r_type,
        }
        if r_ts is not None:
            rel_obj["timestamp"] = r_ts
        out.append(rel_obj)
    
    return out


@app.get("/api/v1/dev-graph/relations/count")
def count_relations():
    rec = run_query("MATCH ()-[r]->() RETURN count(r) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}


@app.get("/api/v1/dev-graph/search")
def search(q: str):
    cypher = (
        "MATCH (n) WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $q) "
        "RETURN n LIMIT 50"
    )
    records = run_query(cypher, q=q)
    
    nodes = []
    for r in records:
        node_data = r["n"]
        node_id = extract_id_from_node_data(node_data)
        
        # Convert node data to a clean dictionary
        if isinstance(node_data, dict):
            clean_data = {k: v for k, v in node_data.items() if v is not None}
        else:
            clean_data = {"raw": str(node_data)}
        
        nodes.append({
            "id": node_id,
            **clean_data
        })
    
    return nodes


@app.get("/api/v1/dev-graph/search/fulltext")
def search_fulltext(q: str, label: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """Full-text search across nodes using Neo4j full-text indexes.

    - When `label` is provided, restricts to one index (File, Requirement, GitCommit).
    - Otherwise queries all available indexes and merges results.
    """
    index_map = {
        "File": "file_fulltext",
        "Requirement": "requirement_fulltext",
        "GitCommit": "commit_fulltext",
    }
    indexes = []
    if label and label in index_map:
        indexes = [index_map[label]]
    else:
        indexes = list(index_map.values())

    out = []
    seen_ids = set()
    with _driver.session() as session:
        for idx in indexes:
            try:
                recs = session.run(
                    "CALL db.index.fulltext.queryNodes($idx, $q) YIELD node, score RETURN node AS n, score LIMIT $limit",
                    {"idx": idx, "q": q, "limit": limit},
                )
            except Exception:
                continue
            for r in recs:
                node_data = r.get("n")
                node_id = extract_id_from_node_data(node_data)
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                clean_data = {k: v for k, v in node_data.items() if v is not None} if isinstance(node_data, dict) else {"raw": str(node_data)}
                out.append({"id": node_id, **clean_data})
                if len(out) >= limit:
                    break
    return out


# -------------------- Phase 1: New Endpoints --------------------

@app.get("/api/v1/dev-graph/commits")
def list_commits(limit: int = Query(100, le=1000), path: Optional[str] = None):
    """List recent commits, optionally filtered to a path (follows renames)."""
    commits = _git.get_commits(limit=limit, path=path)
    return {
        "value": commits,
        "Count": len(commits)
    }


@app.get("/api/v1/dev-graph/commit/{commit_hash}")
def commit_details(commit_hash: str):
    details = _git.get_commit(commit_hash)
    if details is None:
        return {"error": "Commit not found"}
    return details


@app.get("/api/v1/dev-graph/file/history")
def file_history(path: str, limit: int = Query(200, le=2000)):
    return _git.get_file_history(path, limit=limit)


@app.get("/api/v1/dev-graph/subgraph/by-commits")
def time_bounded_subgraph(start_commit: Optional[str] = None, end_commit: Optional[str] = None, limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
    """Time-bounded subgraph filtered by relationship timestamps derived from commits."""
    return _engine.time_bounded_subgraph(start_commit=start_commit, end_commit=end_commit, limit=limit, offset=offset)


@app.post("/api/v1/dev-graph/ingest/recent")
def ingest_recent_commits(limit: int = Query(100, ge=1, le=5000)):
    try:
        # Basic environment validation
        if not _os_mod.path.isdir(REPO_PATH):
            raise RuntimeError(f"Invalid REPO_PATH: {REPO_PATH}")
        _engine.apply_schema()
        count = _engine.ingest_recent_commits(limit=limit)
        return {"ingested": count}
    except Exception as e:
        logging.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Phase 2: Bootstrap & Integration --------------------

@app.post("/api/v1/dev-graph/ingest/bootstrap")
def bootstrap_graph(
    reset_graph: bool = False,
    commit_limit: int = Query(1000, ge=1, le=20000),
    derive_relationships: bool = True,
    dry_run: bool = False,
    include_chunking: bool = True,
    doc_limit: int = Query(None, ge=1, le=1000),
    code_limit: int = Query(None, ge=1, le=5000),
):
    """One-button bootstrap using existing components (LEAN APPROACH).

    Stages:
    1) Apply schema
    2) Ingest docs/chunks (enhanced)
    3) Ingest recent commits (temporal engine)
    4) Map sprints to commits
    5) Chunk documents and code files (Phase 2)
    6) Derive relationships (optional)
    """
    import time
    start = time.time()
    try:
        progress = {
            "schema_applied": False,
            "docs_ingested": 0,
            "commits_ingested": 0,
            "sprints_mapped": 0,
            "chunks_created": 0,
            "relationships_derived": 0,
        }

        if reset_graph:
            with _driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")

        # 1) Schema
        _engine.apply_schema()
        progress["schema_applied"] = True

        # 2) Docs/Chunks (enhanced)
        try:
            ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            ing.ingest()
            progress["docs_ingested"] = 1
        except Exception:
            progress["docs_ingested"] = 0

        # 3) Commits (temporal) - Use parallel pipeline for better performance
        logger.info(f"Phase 3: Ingesting {commit_limit} commits using parallel pipeline...")
        commit_start = time.time()
        commit_results = _parallel_pipeline.ingest_commits_parallel(limit=commit_limit)
        progress["commits_ingested"] = commit_results["commits_ingested"]
        logger.info(f"Commits ingested: {commit_results['commits_ingested']} in {time.time() - commit_start:.2f}s")

        # 4) Sprint mapping
        try:
            mapped = _sprint.map_all_sprints()
            progress["sprints_mapped"] = mapped.get("count", 0) if isinstance(mapped, dict) else 1
        except Exception:
            progress["sprints_mapped"] = 0

        # 5) Chunking (Phase 2) - Use parallel pipeline for better performance
        chunk_stats = {"total_chunks": 0, "total_errors": 0}
        if include_chunking and not dry_run:
            try:
                logger.info(f"Phase 5: Chunking with parallel pipeline (docs={doc_limit}, code={code_limit})...")
                chunk_start = time.time()
                
                # Use parallel pipeline for chunking
                effective_doc_limit = min(doc_limit or 50, 50)
                effective_code_limit = min(code_limit or 200, 200)
                
                chunk_results = _parallel_pipeline.ingest_chunks_parallel(
                    doc_limit=effective_doc_limit,
                    code_limit=effective_code_limit
                )
                progress["chunks_created"] = chunk_results["chunks_created"]
                logger.info(f"Chunks created: {chunk_results['chunks_created']} in {time.time() - chunk_start:.2f}s")
            except Exception as e:
                logger.error(f"Chunking failed: {e}")
                progress["chunks_created"] = 0

        # 6) Relationship derivation (optional)
        derived_counts = {"implements": 0, "evolves_from": 0, "depends_on": 0}
        if derive_relationships and not dry_run:
            derived_counts = _deriver.derive_all()
        progress["relationships_derived"] = sum(derived_counts.values())

        stages_completed = 6
        duration_seconds = round(time.time() - start, 2)
        return {
            "success": True,
            "stages_completed": stages_completed,
            "progress": progress,
            "chunk_stats": chunk_stats,
            "derived": derived_counts,
            "duration_seconds": duration_seconds,
        }
    except Exception as e:
        logging.exception("Bootstrap failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Ingestion Triggers (Enhanced) --------------------

@app.post("/api/v1/dev-graph/ingest/docs")
def ingest_docs():
    """Run enhanced docs/sprints/chunks ingestion.

    Populates Sprint, Document, Chunk nodes and edges:
    - (Sprint)-[:CONTAINS_DOC]->(Document)
    - (Document)-[:CONTAINS_CHUNK]->(Chunk)
    - (Chunk)-[:MENTIONS]->(Requirement)
    """
    try:
        ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        ing.ingest()
        return {"success": True}
    except Exception as e:
        logging.exception("Enhanced docs ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/dev-graph/ingest/git/enhanced")
def ingest_git_enhanced():
    """Run git ingestion by leveraging temporal engine first, then relationship derivation.

    This ensures unified schema (GitCommit/TOUCHED) and consistent provenance.
    """
    try:
        # Apply schema and ingest commits via temporal engine
        _engine.apply_schema()
        temporal_limit = 1000
        try:
            temporal_limit = int(os.environ.get("TEMPORAL_LIMIT", "1000"))
        except Exception:
            temporal_limit = 1000
        ingested = _engine.ingest_recent_commits(limit=temporal_limit)

        # Optionally run enhanced docs pass for planning structure
        try:
            ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            ing.ingest()
        except Exception:
            pass

        # Map sprints
        try:
            _sprint.map_all_sprints()
        except Exception:
            pass

        # Derive relationships
        derived = _deriver.derive_all()
        return {"success": True, "ingested_commits": ingested, "derived": derived, "metrics": _engine.get_metrics()}
    except Exception as e:
        logging.exception("Enhanced git ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/dev-graph/ingest/git/batched")
def ingest_git_batched(
    limit: int = Query(100, ge=1, le=2000, description="Number of commits to ingest"),
    batch_size: int = Query(25, ge=5, le=100, description="Batch size for database writes")
):
    """Optimized git ingestion using batched UNWIND operations.
    
    This is much faster than the standard git ingestion.
    """
    try:
        import time
        start_time = time.time()
        
        # Apply schema once
        _engine.apply_schema()
        
        # Use optimized batched method
        ingested = _engine.ingest_recent_commits_batched(limit=limit, batch_size=batch_size)
        
        duration = time.time() - start_time
        
        return {
            "success": True,
            "ingested_commits": ingested,
            "batch_size": batch_size,
            "duration_seconds": round(duration, 2),
            "commits_per_second": round(ingested / max(duration, 0.001), 2),
            "metrics": _engine.get_metrics()
        }
    except Exception as e:
        logging.exception("Batched git ingest failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/dev-graph/ingest/parallel")
def ingest_parallel(
    commit_limit: int = Query(100, ge=1, le=1000, description="Number of commits to ingest"),
    doc_limit: int = Query(50, ge=1, le=500, description="Number of documentation files to chunk"),
    code_limit: int = Query(200, ge=1, le=1000, description="Number of code files to chunk"),
    include_commits: bool = Query(True, description="Include commit ingestion"),
    include_chunks: bool = Query(True, description="Include chunk ingestion"),
    derive_relationships: bool = Query(False, description="Derive relationships after ingestion")
):
    """Optimized parallel ingestion using worker pipeline."""
    try:
        logger.info(f"Starting parallel ingestion: commits={commit_limit}, docs={doc_limit}, code={code_limit}")
        start_time = time.time()
        
        results = {
            "commits_ingested": 0,
            "chunks_created": 0,
            "files_processed": 0,
            "relationships_derived": 0,
            "total_duration": 0
        }
        
        # Step 1: Ingest commits in parallel
        if include_commits:
            logger.info("Phase 1: Parallel commit ingestion...")
            commit_results = _parallel_pipeline.ingest_commits_parallel(limit=commit_limit)
            results["commits_ingested"] = commit_results["commits_ingested"]
            results["files_processed"] += commit_results["files_processed"]
            logger.info(f"Commits ingested: {commit_results['commits_ingested']} in {commit_results['duration']:.2f}s")
        
        # Step 2: Ingest chunks in parallel
        if include_chunks:
            logger.info("Phase 2: Parallel chunk ingestion...")
            chunk_results = _parallel_pipeline.ingest_chunks_parallel(
                doc_limit=doc_limit, 
                code_limit=code_limit
            )
            results["chunks_created"] = chunk_results["chunks_created"]
            results["files_processed"] += chunk_results["files_processed"]
            logger.info(f"Chunks created: {chunk_results['chunks_created']} in {chunk_results['duration']:.2f}s")
        
        # Step 3: Derive relationships (if requested)
        if derive_relationships:
            logger.info("Phase 3: Deriving relationships...")
            rel_start = time.time()
            try:
                derived = _deriver.derive_all_relationships()
                results["relationships_derived"] = sum(derived.values())
                rel_duration = time.time() - rel_start
                logger.info(f"Relationships derived: {results['relationships_derived']} in {rel_duration:.2f}s")
            except Exception as e:
                logger.error(f"Relationship derivation failed: {e}")
        
        results["total_duration"] = time.time() - start_time
        logger.info(f"Parallel ingestion completed in {results['total_duration']:.2f}s")
        
        return {
            "success": True,
            "results": results,
            "message": f"Parallel ingestion completed: {results['commits_ingested']} commits, {results['chunks_created']} chunks"
        }
        
    except Exception as e:
        logger.error(f"Parallel ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Phase 2: Chunking Endpoints --------------------

@app.post("/api/v1/dev-graph/ingest/chunks")
def ingest_chunks(
    include_docs: bool = Query(True, description="Include document chunking"),
    include_code: bool = Query(True, description="Include code chunking"),
    doc_limit: int = Query(None, ge=1, le=1000, description="Limit number of documents"),
    code_limit: int = Query(None, ge=1, le=5000, description="Limit number of code files"),
    files: Optional[List[str]] = Query(None, description="Specific files to chunk")
):
    """Ingest chunks from documents and code files.
    
    Phase 2: Creates chunks for semantic linking and embedding.
    """
    try:
        if files:
            stats = _chunk_service.ingest_specific_files(files)
        else:
            stats = _chunk_service.ingest_all_chunks(
                include_docs=include_docs,
                include_code=include_code,
                doc_limit=doc_limit,
                code_limit=code_limit
            )
        
        return {
            "success": True,
            "stats": stats,
            "chunk_statistics": _chunk_service.get_chunk_statistics()
        }
    except Exception as e:
        logging.exception("Chunk ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dev-graph/chunks/statistics")
def get_chunk_statistics():
    """Get statistics about chunks in the database."""
    try:
        return _chunk_service.get_chunk_statistics()
    except Exception as e:
        logging.exception("Failed to get chunk statistics")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dev-graph/chunks")
def list_chunks(
    kind: Optional[str] = Query(None, description="Filter by chunk kind (doc/code)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of chunks"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """List chunks with optional filtering."""
    try:
        with _driver.session() as session:
            if kind:
                cypher = """
                    MATCH (ch:Chunk {kind: $kind})
                    RETURN ch, labels(ch) AS labels
                    SKIP $offset LIMIT $limit
                """
                records = session.run(cypher, kind=kind, offset=offset, limit=limit)
            else:
                cypher = """
                    MATCH (ch:Chunk)
                    RETURN ch, labels(ch) AS labels
                    SKIP $offset LIMIT $limit
                """
                records = session.run(cypher, offset=offset, limit=limit)
            
            chunks = []
            for record in records:
                chunk_data = record["ch"]
                labels = record.get("labels", [])
                
                # Extract chunk ID
                chunk_id = chunk_data.get("id", "unknown")
                
                chunks.append({
                    "id": chunk_id,
                    "kind": chunk_data.get("kind"),
                    "heading": chunk_data.get("heading"),
                    "section": chunk_data.get("section"),
                    "file_path": chunk_data.get("file_path"),
                    "span": chunk_data.get("span"),
                    "length": chunk_data.get("length"),
                    "has_embedding": chunk_data.get("embedding") is not None,
                    "symbol": chunk_data.get("symbol"),
                    "symbol_type": chunk_data.get("symbol_type"),
                    "labels": labels
                })
            
            return {
                "chunks": chunks,
                "total": len(chunks),
                "offset": offset,
                "limit": limit
            }
    except Exception as e:
        logging.exception("Failed to list chunks")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Metrics --------------------

@app.get("/api/v1/dev-graph/metrics")
def get_metrics():
    """Return basic API + engine metrics for telemetry."""
    metrics = _engine.get_metrics() if hasattr(_engine, "get_metrics") else {}
    # Add basic process memory if possible
    mem_mb = 0.0
    try:
        import psutil, os as _os
        mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_000_000.0
    except Exception:
        mem_mb = 0.0
    return {
        **metrics,
        "memory_usage_mb": round(mem_mb, 2),
    }


# -------------------- Phase 3: Data Quality Validation --------------------

@app.get("/api/v1/dev-graph/validate/schema")
def validate_schema():
    return _validator.validate_schema_completeness()


@app.get("/api/v1/dev-graph/validate/temporal")
def validate_temporal():
    return _validator.validate_temporal_consistency()


@app.get("/api/v1/dev-graph/validate/relationships")
def validate_relationships():
    return _validator.validate_relationship_integrity()


@app.get("/api/v1/dev-graph/validate/temporal-semantic")
def validate_temporal_semantic():
    """Validate temporal semantic graph specific elements and relationships."""
    return _validator.validate_temporal_semantic_graph()


@app.post("/api/v1/dev-graph/cleanup/orphans")
def cleanup_orphans():
    try:
        deleted = _validator.cleanup_orphaned_nodes()
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/dev-graph/maintenance/backfill-timestamps")
def backfill_timestamps():
    try:
        result = _validator.backfill_missing_timestamps()
        return {"updated": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dev-graph/sprint/map")
def map_sprint(number: str, start_iso: str, end_iso: str):
    return _sprint.map_sprint_range(number=number, start_iso=start_iso, end_iso=end_iso)


# -------------------- Phase 2: Evolution APIs --------------------

@app.get("/api/v1/dev-graph/evolution/requirement/{req_id}")
def requirement_evolution(req_id: str, limit: int = Query(500, le=2000)):
    return _engine.build_evolution_timeline_for_requirement(req_id=req_id, limit=limit)


@app.get("/api/v1/dev-graph/evolution/file")
def file_evolution(path: str, limit: int = Query(500, le=2000)):
    return _engine.build_evolution_timeline_for_file(path=path, limit=limit)


@app.get("/api/v1/dev-graph/sprints")
def list_sprints():
    base = _os_mod.path.join(_os_mod.getcwd(), "docs", "sprints")
    out = []
    if not _os_mod.path.isdir(base):
        return out
    # Gather sprint directories like sprint-01, sprint-10, etc.
    for name in sorted(_os_mod.listdir(base)):
        if not name.startswith("sprint-"):
            continue
        number = name.split("-", 1)[1]
        sprint_dir = _os_mod.path.join(base, name)
        # Try to find dates from planning file
        start_iso = None
        end_iso = None
        planning = _os_mod.path.join(base, "planning", "SPRINT_STATUS.md")
        if _os_mod.path.isfile(planning):
            try:
                with open(planning, "r", encoding="utf-8") as f:
                    content = f.read()
                # naive parse: look for "Sprint {number}" lines and capture Start/End
                import re as _re
                # Example: "Sprint 10" followed by Start Date: YYYY-MM-DD
                pat = _re.compile(rf"Sprint\s*{number}.*?Start Date\W*:?\s*([0-9-]{8,10}).*?End Date\W*:?\s*([0-9-]{8,10})", _re.IGNORECASE | _re.DOTALL)
                m = pat.search(content)
                if m:
                    start_iso = m.group(1)
                    end_iso = m.group(2)
            except Exception:
                pass
        # Fallback: two-week window ending today
        from datetime import datetime, timedelta
        if not start_iso or not end_iso:
            end_iso = datetime.utcnow().date().isoformat()
            start_iso = (datetime.utcnow().date() - timedelta(days=14)).isoformat()
        mapped = _sprint.map_sprint_range(number=str(number), start_iso=start_iso, end_iso=end_iso)
        # add basic metrics stub
        out.append({
            "number": number,
            "start_date": start_iso,
            "end_date": end_iso,
            "commit_range": {"start": mapped.get("commit_range", [None, None])[0], "end": mapped.get("commit_range", [None, None])[-1] if mapped.get("commit_range") else None},
            "metrics": {
                "count": mapped.get("count", 0),
            }
        })
    return out


@app.get("/api/v1/dev-graph/sprints/{number}")
def sprint_details(number: str):
    """Return sprint details including commit range and basic metrics.

    Dates are resolved from planning doc when possible, with fallback window.
    """
    base = _os_mod.path.join(_os_mod.getcwd(), "docs", "sprints")
    start_iso = None
    end_iso = None
    planning = _os_mod.path.join(base, "planning", "SPRINT_STATUS.md")
    if _os_mod.path.isfile(planning):
        try:
            with open(planning, "r", encoding="utf-8") as f:
                content = f.read()
            import re as _re
            pat = _re.compile(rf"Sprint\s*{number}.*?Start Date\W*:?\s*([0-9-]{8,10}).*?End Date\W*:?\s*([0-9-]{8,10})", _re.IGNORECASE | _re.DOTALL)
            m = pat.search(content)
            if m:
                start_iso = m.group(1)
                end_iso = m.group(2)
        except Exception:
            pass
    from datetime import datetime, timedelta
    if not start_iso or not end_iso:
        end_iso = datetime.utcnow().date().isoformat()
        start_iso = (datetime.utcnow().date() - timedelta(days=14)).isoformat()
    mapped = _sprint.map_sprint_range(number=str(number), start_iso=start_iso, end_iso=end_iso)
    return {
        "number": number,
        "start_date": start_iso,
        "end_date": end_iso,
        "commit_range": {
            "start": (mapped.get("commit_range") or [None, None])[0],
            "end": (mapped.get("commit_range") or [None, None])[-1] if mapped.get("commit_range") else None,
        },
        "metrics": {"count": mapped.get("count", 0)},
    }


@app.get("/api/v1/dev-graph/sprints/{number}/subgraph")
def sprint_subgraph(number: str):
    """Return a hierarchical subgraph for a sprint: Sprint->Docs->Chunks->Requirements.

    This endpoint is independent of timestamps to ensure deterministic sprint structure.
    """
    cypher = (
        "MATCH (s:Sprint {number: $num}) "
        "OPTIONAL MATCH (s)-[:CONTAINS_DOC]->(d:Document) "
        "OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:Chunk) "
        "OPTIONAL MATCH (c)-[:MENTIONS]->(r:Requirement) "
        "RETURN s, collect(DISTINCT d) AS docs, collect(DISTINCT c) AS chunks, collect(DISTINCT r) AS reqs"
    )
    with _driver.session() as session:
        rec = session.run(cypher, {"num": number}).single()
        if not rec:
            return {"nodes": [], "edges": []}
        s = rec.get("s") or {}
        docs = rec.get("docs") or []
        chunks = rec.get("chunks") or []
        reqs = rec.get("reqs") or []

        def _id(n):
            return extract_id_from_node_data(n)

        nodes = []
        seen = set()
        def add_node(n):
            nid = _id(n)
            if nid in seen:
                return
            seen.add(nid)
            if isinstance(n, dict):
                nodes.append({"id": nid, **n})
            else:
                nodes.append({"id": nid, "raw": str(n)})

        add_node(s)
        for d in docs: add_node(d)
        for c in chunks: add_node(c)
        for r in reqs: add_node(r)

        # Now get edges explicitly to preserve relations
        edges = []
        rels_cypher = (
            "MATCH (s:Sprint {number: $num})-[:CONTAINS_DOC]->(d:Document) "
            "RETURN 'CONTAINS_DOC' AS t, s AS a, d AS b "
            "UNION ALL "
            "MATCH (d:Document)<-[:CONTAINS_DOC]-(s:Sprint {number: $num}), (d)-[:CONTAINS_CHUNK]->(c:Chunk) "
            "RETURN 'CONTAINS_CHUNK' AS t, d AS a, c AS b "
            "UNION ALL "
            "MATCH (d:Document)<-[:CONTAINS_DOC]-(s:Sprint {number: $num}), (d)-[:CONTAINS_CHUNK]->(c:Chunk)-[:MENTIONS]->(r:Requirement) "
            "RETURN 'MENTIONS' AS t, c AS a, r AS b"
        )
        result = session.run(rels_cypher, {"num": number})
        for r in result:
            a = r.get("a")
            b = r.get("b")
            t = r.get("t")
            edges.append({"from": _id(a), "to": _id(b), "type": str(t)})

        return {"nodes": nodes, "edges": edges}


# -------------------- Phase 4: Performance Primitives --------------------

@app.get("/api/v1/dev-graph/graph/subgraph", response_model=WindowedSubgraphResponse)
def get_windowed_subgraph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    types: Optional[str] = Query(None, description="Comma-separated node types to filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of edges to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    include_counts: bool = Query(True, description="Include total node/edge counts in response")
):
    """Get a time-bounded subgraph with pagination and type filtering.
    
    Returns nodes and edges within the time window, with performance metrics.
    SLO: <300ms for 30-day subgraph on local data.
    """
    node_types = None
    if types:
        node_types = [t.strip() for t in types.split(",") if t.strip()]
    
    return _engine.get_windowed_subgraph(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        node_types=node_types,
        limit=limit,
        cursor=cursor,
        include_counts=include_counts
    )


@app.post("/api/v1/dev-graph/ingest/parallel")
def ingest_commits_parallel(
    limit: int = Query(100, ge=1, le=1000, description="Number of commits to ingest"),
    max_workers: int = Query(4, ge=1, le=8, description="Maximum number of parallel workers"),
    batch_size: int = Query(50, ge=10, le=200, description="Batch size for database writes")
):
    """Ingest commits using parallel processing and batched writes for better performance."""
    try:
        ingested_count = _engine.ingest_recent_commits_parallel(
            limit=limit,
            max_workers=max_workers,
            batch_size=batch_size
        )
        return {
            "success": True,
            "ingested_commits": ingested_count,
            "performance": {
                "max_workers": max_workers,
                "batch_size": batch_size,
                "total_limit": limit
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "ingested_commits": 0
        }


@app.get("/api/v1/dev-graph/commits/buckets", response_model=CommitsBucketsResponse)
def get_commits_buckets(
    granularity: str = Query("day", regex="^(day|week)$", description="Time granularity: 'day' or 'week'"),
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of buckets to return")
):
    """Get commit counts grouped by time buckets for timeline density and caching.
    
    Returns commit activity aggregated by day or week for timeline visualization.
    """
    try:
        return _engine.get_commits_buckets(
            granularity=granularity,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=limit
        )
    except Exception as e:
        # Fallback implementation if temporal engine doesn't have this method
        with _driver.session() as session:
            # Build time window constraints
            where_clauses = []
            params = {"limit": min(limit, 10000)}
            
            if from_timestamp:
                where_clauses.append("c.timestamp >= $from_ts")
                params["from_ts"] = from_timestamp
            if to_timestamp:
                where_clauses.append("c.timestamp <= $to_ts")
                params["to_ts"] = to_timestamp
            
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Determine date truncation based on granularity
            if granularity == "week":
                date_trunc = "date(c.timestamp - duration('P' + toString(dayOfWeek(c.timestamp) - 1) + 'D'))"
            else:  # day
                date_trunc = "date(c.timestamp)"
            
            # Query for commit buckets
            cypher = f"""
                MATCH (c:GitCommit)
                {where_clause}
                WITH {date_trunc} AS bucket, count(c) AS commit_count
                OPTIONAL MATCH (c2:GitCommit)-[r:TOUCHED]->()
                WHERE {date_trunc} = bucket
                WITH bucket, commit_count, count(r) AS file_changes
                RETURN bucket, commit_count, file_changes
                ORDER BY bucket DESC
                LIMIT $limit
            """
            
            result = session.run(cypher, params)
            buckets = []
            
            for record in result:
                buckets.append({
                    "bucket": record["bucket"].isoformat() if record["bucket"] else "",
                    "commit_count": record["commit_count"] or 0,
                    "file_changes": record["file_changes"] or 0,
                    "granularity": granularity
                })
            
            return {
                "buckets": buckets,
                "performance": {
                    "query_time_ms": 0,  # Would need actual timing
                    "total_buckets": len(buckets)
                }
            }


# -------------------- Analytics Endpoints --------------------

@app.get("/api/v1/analytics/activity")
def analytics_activity(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)")
):
    """Return basic activity metrics for a time window.

    - commit_count (by GitCommit.timestamp)
    - file_changes (by TOUCHED.timestamp)
    - unique_authors (by GitCommit.author)
    """
    with _driver.session() as session:
        # Commits by time
        where_c = []
        params = {}
        if from_timestamp:
            where_c.append("c.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where_c.append("c.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        clause_c = f"WHERE {' AND '.join(where_c)}" if where_c else ""

        commits_cypher = f"""
            MATCH (c:GitCommit)
            {clause_c}
            RETURN count(c) AS commit_count, count(DISTINCT c.author) AS unique_authors
        """
        rec_c = session.run(commits_cypher, params).single()
        commit_count = rec_c["commit_count"] if rec_c else 0
        unique_authors = rec_c["unique_authors"] if rec_c else 0

        # File changes by TOUCHED relationships
        where_t = ["r.timestamp IS NOT NULL"]
        if from_timestamp:
            where_t.append("r.timestamp >= $from_ts")
        if to_timestamp:
            where_t.append("r.timestamp <= $to_ts")
        clause_t = f"WHERE {' AND '.join(where_t)}"
        touched_cypher = f"""
            MATCH ()-[r:TOUCHED]->()
            {clause_t}
            RETURN count(r) AS file_changes
        """
        rec_t = session.run(touched_cypher, params).single()
        file_changes = rec_t["file_changes"] if rec_t else 0

        return {
            "commit_count": commit_count,
            "file_changes": file_changes,
            "unique_authors": unique_authors,
            "window": {"from": from_timestamp, "to": to_timestamp}
        }


@app.get("/api/v1/analytics/graph")
def analytics_graph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format) for edge counts"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format) for edge counts"),
):
    """Return graph metrics: node counts by label and edge counts by type.

    Edge counts are optionally time-bounded by relationship.timestamp.
    """
    with _driver.session() as session:
        # Node counts by type - using separate queries for each type
        def count_nodes(label: str) -> int:
            q = f"MATCH (n:{label}) RETURN count(n) AS c"
            rec = session.run(q).single()
            return rec["c"] if rec else 0
        
        nodes = {
            "sprints": count_nodes("Sprint"),
            "documents": count_nodes("Document"),
            "chunks": count_nodes("Chunk"),
            "requirements": count_nodes("Requirement"),
            "files": count_nodes("File"),
            "commits": count_nodes("GitCommit"),
        }

        # Edge counts by type with optional time window
        # Separate temporal vs structural edge counts
        params = {}
        temporal_where = ["r.timestamp IS NOT NULL"]
        if from_timestamp:
            temporal_where.append("r.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            temporal_where.append("r.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        temporal_clause = f"WHERE {' AND '.join(temporal_where)}"

        def count_rel_temporal(rel_type: str) -> int:
            q = f"MATCH ()-[r:{rel_type}]->() {temporal_clause} RETURN count(r) AS c"
            rec = session.run(q, params).single()
            return rec["c"] if rec else 0

        def count_rel_struct(rel_type: str) -> int:
            q = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c"
            rec = session.run(q).single()
            return rec["c"] if rec else 0

        edges = {
            "TOUCHED": count_rel_temporal("TOUCHED"),
            "IMPLEMENTS": count_rel_temporal("IMPLEMENTS"),
            "EVOLVES_FROM": count_rel_temporal("EVOLVES_FROM"),
            "REFACTORED_TO": count_rel_temporal("REFACTORED_TO"),
            "DEPRECATED_BY": count_rel_temporal("DEPRECATED_BY"),
            # Structural edges (no timestamp constraints)
            "MENTIONS": count_rel_struct("MENTIONS"),
            "CONTAINS_CHUNK": count_rel_struct("CONTAINS_CHUNK"),
            "CONTAINS_DOC": count_rel_struct("CONTAINS_DOC"),
        }

        return {"nodes": nodes, "edges": edges, "window": {"from": from_timestamp, "to": to_timestamp}}


@app.get("/api/v1/analytics/traceability")
def analytics_traceability(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format) for traceability window"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format) for traceability window"),
):
    """Return traceability metrics for requirements.

    - total_requirements
    - implemented_requirements (has at least one IMPLEMENTS)
    - unimplemented_requirements
    - avg_files_per_requirement (average IMPLEMENTS targets per requirement)
    Optionally confined to a time window based on IMPLEMENTS.timestamp.
    """
    with _driver.session() as session:
        # Total requirements
        total_rec = session.run("MATCH (r:Requirement) RETURN count(r) AS c").single()
        total = total_rec["c"] if total_rec else 0

        # Implemented requirements (optionally windowed)
        where = []
        params = {}
        if from_timestamp:
            where.append("rel.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where.append("rel.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        impl_q = """
            MATCH (r:Requirement)-[rel:IMPLEMENTS]->(:File)
            """ + clause + """
            RETURN count(DISTINCT r) AS c
        """
        impl_rec = session.run(impl_q, params).single()
        implemented = impl_rec["c"] if impl_rec else 0

        # Average files per requirement (windowed on rel timestamp when provided)
        avg_q = """
            MATCH (r:Requirement)
            OPTIONAL MATCH (r)-[rel:IMPLEMENTS]->(:File)
            """ + clause + """
            WITH r, count(rel) AS file_links
            RETURN coalesce(avg(file_links), 0) AS avg_files_per_requirement
        """
        avg_rec = session.run(avg_q, params).single()
        avg_files = avg_rec["avg_files_per_requirement"] if avg_rec else 0

        return {
            "total_requirements": total,
            "implemented_requirements": implemented,
            "unimplemented_requirements": max(total - implemented, 0),
            "avg_files_per_requirement": avg_files,
            "window": {"from": from_timestamp, "to": to_timestamp}
        }


@app.get("/api/v1/analytics")
def get_analytics(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)")
):
    """Combined analytics endpoint that frontend expects.
    
    Returns aggregated analytics data from activity, graph, and traceability endpoints.
    """
    try:
        # Get activity analytics
        activity_data = analytics_activity(from_timestamp, to_timestamp)
        
        # Get graph analytics
        graph_data = analytics_graph(from_timestamp, to_timestamp)
        
        # Get traceability analytics
        traceability_data = analytics_traceability(from_timestamp, to_timestamp)
        
        # Calculate derived metrics for activity
        days_in_window = 7  # Default to 7 days if no window specified
        if from_timestamp and to_timestamp:
            try:
                start = datetime.fromisoformat(from_timestamp.replace('Z', '+00:00'))
                end = datetime.fromisoformat(to_timestamp.replace('Z', '+00:00'))
                days_in_window = max(1, (end - start).days)
            except Exception:
                days_in_window = 7
        
        commits_per_day = activity_data.get("commit_count", 0) / days_in_window
        files_changed_per_day = activity_data.get("file_changes", 0) / days_in_window
        authors_per_day = activity_data.get("unique_authors", 0) / days_in_window
        
        # Create trends data (simplified - in production you'd want more sophisticated trend analysis)
        trends = []
        for i in range(days_in_window):
            date = (datetime.now() - timedelta(days=days_in_window - i - 1)).strftime('%Y-%m-%d')
            trends.append({
                "date": date,
                "value": commits_per_day + (i * 0.1)  # Simple trend simulation
            })
        
        return {
            "activity": {
                "commits_per_day": round(commits_per_day, 2),
                "files_changed_per_day": round(files_changed_per_day, 2),
                "authors_per_day": round(authors_per_day, 2),
                "peak_activity": {
                    "timestamp": from_timestamp or datetime.now().isoformat(),
                    "count": activity_data.get("commit_count", 0)
                },
                "trends": trends
            },
            "graph": {
                "total_nodes": graph_data.get("nodes", {}).get("commits", 0) + 
                              graph_data.get("nodes", {}).get("files", 0) + 
                              graph_data.get("nodes", {}).get("requirements", 0),
                "total_edges": sum(graph_data.get("edges", {}).values()),
                "node_types": graph_data.get("nodes", {}),
                "edge_types": graph_data.get("edges", {}),
                "complexity_metrics": {
                    "clustering_coefficient": 0.3,  # Placeholder - would need actual calculation
                    "average_path_length": 2.5,     # Placeholder
                    "modularity": 0.7               # Placeholder
                }
            },
            "traceability": {
                "implemented_requirements": traceability_data.get("implemented_requirements", 0),
                "unimplemented_requirements": traceability_data.get("unimplemented_requirements", 0),
                "avg_files_per_requirement": traceability_data.get("avg_files_per_requirement", 0),
                "coverage_percentage": round(
                    (traceability_data.get("implemented_requirements", 0) / 
                     max(1, traceability_data.get("total_requirements", 1))) * 100, 2
                )
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch analytics: {str(e)}",
            "activity": {"commits_per_day": 0, "files_changed_per_day": 0, "authors_per_day": 0, "peak_activity": {"timestamp": "", "count": 0}, "trends": []},
            "graph": {"total_nodes": 0, "total_edges": 0, "node_types": {}, "edge_types": {}, "complexity_metrics": {"clustering_coefficient": 0, "average_path_length": 0, "modularity": 0}},
            "traceability": {"implemented_requirements": 0, "unimplemented_requirements": 0, "avg_files_per_requirement": 0, "coverage_percentage": 0}
        }


# -------------------- Phase 1.4: Relationship Derivation Endpoint --------------------

@app.post("/api/v1/dev-graph/ingest/derive-relationships")
def derive_relationships(since_timestamp: Optional[str] = None, dry_run: bool = False, strategies: Optional[List[str]] = None):
    """Run evidence-based relationship derivation.

    - since_timestamp: only consider facts at/after this timestamp
    - dry_run: when true, report counts but avoid side-effects (best-effort; some Cypher writes may still occur if APOC missing)
    - strategies: subset of [implements, evolves_from, depends_on]
    """
    import time
    start = time.time()
    try:
        # Default strategies
        chosen = set(strategies or ["implements", "evolves_from", "depends_on"]) & {"implements", "evolves_from", "depends_on"}

        derived = {"implements": 0, "evolves_from": 0, "depends_on": 0}
        if "implements" in chosen and not dry_run:
            derived["implements"] = _deriver.derive_implements(since_timestamp)
        if "evolves_from" in chosen and not dry_run:
            derived["evolves_from"] = _deriver.derive_evolves_from(since_timestamp)
        if "depends_on" in chosen and not dry_run:
            derived["depends_on"] = _deriver.derive_depends_on()

        # Simple confidence stats proxy (would require aggregation for real metrics)
        confidence_stats = {
            "avg_confidence": 0.75,
            "high_confidence": max(0, int(derived.get("implements", 0) * 0.6)),
            "medium_confidence": max(0, int(derived.get("implements", 0) * 0.3)),
            "low_confidence": max(0, int(derived.get("implements", 0) * 0.1)),
        }

        return {
            "success": True,
            "derived": derived,
            "confidence_stats": confidence_stats,
            "duration_seconds": round(time.time() - start, 2),
        }
    except Exception as e:
        logging.exception("Relationship derivation failed")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Embedding Endpoints --------------------

@app.post("/api/v1/dev-graph/ingest/embeddings")
def generate_embeddings(
    chunk_ids: Optional[List[str]] = Query(None, description="Specific chunk IDs to process"),
    batch_size: int = Query(10, ge=1, le=50, description="Batch size for embedding generation"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of chunks to process")
):
    """Generate embeddings for chunks.
    
    Phase 3: Creates embeddings for semantic search and linking.
    """
    try:
        # Limit the number of chunks to process
        if not chunk_ids:
            # Get chunks without embeddings, limited by the limit parameter
            with _driver.session() as session:
                limited_chunk_ids = session.run("""
                    MATCH (ch:Chunk)
                    WHERE ch.embedding IS NULL AND ch.text IS NOT NULL
                    RETURN ch.id as id
                    LIMIT $limit
                """, limit=limit).data()
                chunk_ids = [record["id"] for record in limited_chunk_ids]
        
        stats = _embedding_service.generate_embeddings_for_chunks(
            chunk_ids=chunk_ids,
            batch_size=batch_size
        )
        
        return {
            "success": True,
            "stats": stats,
            "embedding_statistics": _embedding_service.get_embedding_statistics()
        }
    except Exception as e:
        logging.exception("Embedding generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dev-graph/embeddings/statistics")
def get_embedding_statistics():
    """Get statistics about chunk embeddings."""
    try:
        return _embedding_service.get_embedding_statistics()
    except Exception as e:
        logging.exception("Failed to get embedding statistics")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- Data Management Endpoints --------------------

@app.delete("/api/v1/dev-graph/reset")
def reset_database(confirm: bool = False):
    """Reset the entire database by deleting all nodes and relationships.
    
    WARNING: This will permanently delete all data in the Neo4j database.
    Set confirm=true to proceed.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="This operation will delete all data. Set confirm=true to proceed."
        )
    
    try:
        with _driver.session() as session:
            # Get counts before deletion for reporting
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Delete all nodes and relationships
            session.run("MATCH (n) DETACH DELETE n")
            
            return {
                "success": True,
                "deleted_nodes": node_count,
                "deleted_relationships": rel_count,
                "message": "Database reset successfully"
            }
    except Exception as e:
        logging.exception("Database reset failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/dev-graph/cleanup")
def cleanup_database(confirm: bool = False):
    """Clean up orphaned nodes and relationships without full reset.
    
    This is safer than a full reset and removes:
    - Orphaned nodes with no relationships
    - Duplicate nodes (based on uid/hash)
    - Invalid relationships
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="This operation will clean up data. Set confirm=true to proceed."
        )
    
    try:
        with _driver.session() as session:
            # Get counts before cleanup
            initial_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            initial_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            # Remove orphaned nodes (nodes with no relationships)
            orphaned_result = session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                DELETE n
                RETURN count(n) as deleted
            """).single()
            orphaned_deleted = orphaned_result["deleted"] if orphaned_result else 0
            
            # Remove duplicate GitCommits (keep the one with most recent timestamp)
            duplicate_commits = session.run("""
                MATCH (c:GitCommit)
                WITH c.hash as hash, collect(c) as commits
                WHERE size(commits) > 1
                WITH hash, commits, max([c IN commits | c.timestamp]) as latest_ts
                UNWIND commits as c
                WITH c, latest_ts
                WHERE c.timestamp < latest_ts
                DELETE c
                RETURN count(c) as deleted
            """).single()
            duplicate_deleted = duplicate_commits["deleted"] if duplicate_commits else 0
            
            # Get final counts
            final_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            final_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            return {
                "success": True,
                "initial_nodes": initial_nodes,
                "initial_relationships": initial_rels,
                "final_nodes": final_nodes,
                "final_relationships": final_rels,
                "orphaned_nodes_deleted": orphaned_deleted,
                "duplicate_commits_deleted": duplicate_deleted,
                "total_cleaned": orphaned_deleted + duplicate_deleted
            }
    except Exception as e:
        logging.exception("Database cleanup failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/dev-graph/ingest/full-reset")
def full_reset_and_ingest(
    confirm: bool = False,
    commit_limit: int = Query(1000, ge=1, le=20000),
    derive_relationships: bool = True,
    include_chunking: bool = True,
    doc_limit: int = Query(None, ge=1, le=1000),
    code_limit: int = Query(None, ge=1, le=5000)
):
    """Full reset and bootstrap ingestion in one operation.
    
    This combines database reset with bootstrap ingestion for a clean start.
    WARNING: This will permanently delete all existing data.
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="This operation will delete all data and re-ingest. Set confirm=true to proceed."
        )
    
    try:
        # First reset the database
        reset_result = reset_database(confirm=True)
        
        # Then run bootstrap ingestion
        bootstrap_result = bootstrap_graph(
            reset_graph=False,  # Already reset above
            commit_limit=commit_limit,
            derive_relationships=derive_relationships,
            dry_run=False,
            include_chunking=include_chunking,
            doc_limit=doc_limit,
            code_limit=code_limit
        )
        
        return {
            "success": True,
            "reset_result": reset_result,
            "bootstrap_result": bootstrap_result,
            "message": "Full reset and ingestion completed successfully"
        }
    except Exception as e:
        logging.exception("Full reset and ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
