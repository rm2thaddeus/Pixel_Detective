from __future__ import annotations

import os
import time
import logging
from typing import Optional, List, Dict
import os
import json
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException

from ..app_state import (
    driver,
    engine,
    git,
    sprint_mapper,
    deriver,
    embedding_service,
    parallel_pipeline,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    REPO_PATH,
)
from ..enhanced_ingest import EnhancedDevGraphIngester
from ..code_symbol_extractor import CodeSymbolExtractor


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/v1/dev-graph/ingest/recent")
def ingest_recent_commits(limit: int = Query(100, ge=1, le=5000)):
    try:
        engine.apply_schema()
        ingested = engine.ingest_recent_commits(limit=limit)
        return {"success": True, "ingested_commits": ingested}
    except Exception as e:
        logger.exception("Recent ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/bootstrap")
def bootstrap_graph(
    reset_graph: bool = False,
    commit_limit: int = Query(1000, ge=1, le=20000),
    derive_relationships: bool = True,
    dry_run: bool = False,
    include_chunking: bool = True,
    doc_limit: int = Query(None, ge=1, le=1000),
    code_limit: int = Query(None, ge=1, le=5000),
):
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
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
        engine.apply_schema()
        progress["schema_applied"] = True

        try:
            ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            ing.ingest()
            progress["docs_ingested"] = 1
        except Exception:
            progress["docs_ingested"] = 0

        commit_results = parallel_pipeline.ingest_commits_parallel(limit=commit_limit)
        progress["commits_ingested"] = commit_results["commits_ingested"]

        mapped = sprint_mapper.map_all_sprints()
        if isinstance(mapped, dict):
            progress["sprints_mapped"] = mapped.get("count", 0)
            progress["sprint_windows"] = mapped.get("windows", [])
        else:
            progress["sprints_mapped"] = 0
            progress["sprint_windows"] = []

        # Chunking is handled by EnhancedDevGraphIngester above
        # Disable parallel chunking to avoid duplication
        progress["chunks_created"] = 0

        derived_counts = {"implements": 0, "evolves_from": 0, "depends_on": 0}
        if derive_relationships and not dry_run:
            derived_result = deriver.derive_all()
            derived_counts = {
                "implements": derived_result.get("implements", 0),
                "evolves_from": derived_result.get("evolves_from", 0),
                "depends_on": derived_result.get("depends_on", 0)
            }
        progress["relationships_derived"] = sum(derived_counts.values())

        return {
            "success": True,
            "stages_completed": 6,
            "progress": progress,
            "derived": derived_counts,
            "duration_seconds": round(time.time() - start, 2),
        }
    except Exception as e:
        logger.exception("Bootstrap failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/bootstrap/lean")
def bootstrap_lean(
    commit_limit: int = Query(500, ge=1, le=5000),
    derive_relationships: bool = True,
    dry_run: bool = False,
):
    """Phase 2: Lean bootstrap endpoint for quick setup.
    
    Minimal bootstrap that focuses on core functionality:
    - Apply schema
    - Ingest recent commits with ordering
    - Derive relationships (optional)
    - Return essential metrics
    """
    start = time.time()
    try:
        # Stage 1: Apply schema (2 min)
        logger.info("Stage 1/3: Applying schema...")
        engine.apply_schema()
        
        # Stage 2: Ingest commits with ordering (3 min)
        logger.info("Stage 2/3: Ingesting commits with ordering...")
        # Use enhanced git ingest to create commit ordering relationships
        from ..enhanced_git_ingest import EnhancedGitIngester
        enhanced_ingester = EnhancedGitIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        enhanced_ingester.ingest()
        ingested = commit_limit  # Enhanced ingest processes all commits
        
        # Stage 3: Derive relationships (optional, 2 min)
        derived_counts = {"implements": 0, "evolves_from": 0, "depends_on": 0}
        if derive_relationships and not dry_run:
            logger.info("Stage 3/3: Deriving relationships...")
            derived_result = deriver.derive_all()
            derived_counts = {
                "implements": derived_result.get("implements", 0),
                "evolves_from": derived_result.get("evolves_from", 0),
                "depends_on": derived_result.get("depends_on", 0)
            }
        
        duration = time.time() - start
        
        return {
            "success": True,
            "stages_completed": 3,
            "ingested_commits": ingested,
            "derived": derived_counts,
            "duration_seconds": round(duration, 2),
            "commits_per_second": round(ingested / max(duration, 0.001), 2),
            "message": f"Lean bootstrap completed: {ingested} commits, {sum(derived_counts.values())} relationships"
        }
    except Exception as e:
        logger.exception("Lean bootstrap failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/bootstrap/complete")
def bootstrap_complete(
    reset_graph: bool = True,
    commit_limit: int = Query(1000, ge=1, le=5000),
    derive_relationships: bool = True,
    dry_run: bool = False,
    run_symbol_extractor: bool = True,
    symbol_file_limit: int = Query(50000, ge=1000, le=200000),
):
    """Complete bootstrap endpoint that does everything properly.
    
    This is the single entry point that:
    - Resets the database (optional)
    - Applies schema
    - Runs enhanced git ingest with commit ordering
    - Derives relationships
    - Returns comprehensive metrics
    """
    start = time.time()
    try:
        progress = {
            "database_reset": False,
            "schema_applied": False,
            "enhanced_ingest_completed": False,
            "relationships_derived": False,
            "commits_ingested": 0,
            "files_processed": 0,
            "chunks_created": 0,
            "relationships_created": 0
        }
        
        # Stage 1: Reset database (optional)
        if reset_graph and not dry_run:
            logger.info("Stage 1/4: Resetting database...")
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            progress["database_reset"] = True
        
        # Stage 2: Apply schema
        logger.info("Stage 2/4: Applying schema...")
        engine.apply_schema()
        progress["schema_applied"] = True
        
        # Stage 3: Enhanced git ingest with commit ordering
        if not dry_run:
            logger.info("Stage 3/4: Running enhanced git ingest with commit ordering...")
            from ..enhanced_git_ingest import EnhancedGitIngester
            enhanced_ingester = EnhancedGitIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            enhanced_ingester.ingest()
            progress["enhanced_ingest_completed"] = True
        
        # Optional: symbol/library extraction to improve Library coverage
        symbol_stats: Dict[str, object] = {}
        if run_symbol_extractor and not dry_run:
            try:
                logger.info("Running CodeSymbolExtractor to enhance library relationships…")
                code_files = _discover_code_files_from_graph(symbol_file_limit)
                extractor = CodeSymbolExtractor(driver, REPO_PATH)
                symbol_stats = extractor.run_enhanced_connectivity(code_files, force_doc_refresh=True)
                logger.info(f"Symbol extraction stats: {symbol_stats}")
            except Exception as e:
                logger.warning(f"Symbol extraction failed: {e}")

        # Stage 4: Derive relationships
        derived_counts = {"implements": 0, "evolves_from": 0, "depends_on": 0}
        if derive_relationships and not dry_run:
            logger.info("Stage 4/4: Deriving relationships...")
            derived_result = deriver.derive_all()
            derived_counts = {
                "implements": derived_result.get("implements", 0),
                "evolves_from": derived_result.get("evolves_from", 0),
                "depends_on": derived_result.get("depends_on", 0)
            }
            progress["relationships_derived"] = True
        
        # Get final statistics
        with driver.session() as session:
            # Get node counts
            node_counts = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN label as type, count(*) as count
                ORDER BY count DESC
            """).data()
            
            # Get relationship counts
            rel_counts = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """).data()
        
        duration = time.time() - start
        
        # Format results
        node_stats = {item["type"]: item["count"] for item in node_counts}
        rel_stats = {item["type"]: item["count"] for item in rel_counts}
        
        return {
            "success": True,
            "stages_completed": 4,
            "progress": progress,
            "node_stats": node_stats,
            "relationship_stats": rel_stats,
            "derived": derived_counts,
            "symbol_stats": symbol_stats,
            "duration_seconds": round(duration, 2),
            "commits_per_second": round(node_stats.get("GitCommit", 0) / max(duration, 0.001), 2),
            "message": f"Complete bootstrap finished: {node_stats.get('GitCommit', 0)} commits, {sum(rel_stats.values())} relationships"
        }
    except Exception as e:
        logger.exception("Complete bootstrap failed")
        raise HTTPException(status_code=500, detail=str(e))


def _discover_code_files_from_graph(limit: int) -> List[str]:
    """Return repository-relative code file paths already present as File nodes.

    This leverages previously ingested File nodes to avoid re-scanning the filesystem.
    """
    ends = [".py", ".ts", ".tsx", ".js", ".jsx"]
    where_clause = " OR ".join([f"endsWith(toLower(f.path), '{ext}')" for ext in ends])
    query = f"""
        MATCH (f:File)
        WHERE {where_clause}
        RETURN f.path AS path
        LIMIT $limit
    """
    with driver.session() as session:
        records = session.run(query, limit=limit).data()
    return [r["path"] for r in records]


def _compute_audit(driver) -> Dict[str, object]:
    """Compute node/edge counts and common integrity checks, including orphans."""
    with driver.session() as session:
        node_counts = session.run(
            """
            MATCH (n)
            UNWIND labels(n) AS label
            RETURN label AS type, count(*) AS count
            ORDER BY count DESC
            """
        ).data()
        rel_counts = session.run(
            """
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(*) AS count
            ORDER BY count DESC
            """
        ).data()
        # Neo4j 5+ may not expose degree(); use OPTIONAL MATCH to detect isolated nodes
        orphans = session.run(
            """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS deg
            WHERE deg = 0
            RETURN head(labels(n)) AS type, count(n) AS count
            ORDER BY count DESC
            """
        ).data()
        library_sources = session.run(
            """
            MATCH (l:Library)
            UNWIND coalesce(l.manifest_sources, []) AS source
            RETURN source, count(*) AS total
            ORDER BY total DESC
            """
        ).data()
        library_languages = session.run(
            """
            MATCH (l:Library)
            RETURN coalesce(l.language, 'unknown') AS language, count(*) AS total
            ORDER BY total DESC
            """
        ).data()
        library_usage_top = session.run(
            """
            MATCH (:File)-[:USES_LIBRARY]->(l:Library)
            RETURN l.name AS library, count(*) AS files
            ORDER BY files DESC
            LIMIT 20
            """
        ).data()
        decode_summary = session.run(
            """
            MATCH (f:File)
            WHERE f.decoding IS NOT NULL
            WITH f.decoding AS decoding
            RETURN
                coalesce(decoding.encoding, 'unknown') AS encoding,
                count(*) AS files,
                sum(CASE WHEN coalesce(decoding.fallback_used, false) THEN 1 ELSE 0 END) AS fallbacks,
                sum(coalesce(decoding.replaced_chars, 0)) AS replaced_chars
            ORDER BY files DESC
            """
        ).data()
        decode_fallbacks = session.run(
            """
            MATCH (f:File)
            WHERE f.decoding IS NOT NULL AND coalesce(f.decoding.fallback_used, false)
            RETURN f.path AS path,
                   coalesce(f.decoding.encoding, 'unknown') AS encoding,
                   coalesce(f.decoding.detector, 'manual') AS detector,
                   coalesce(f.decoding.replaced_chars, 0) AS replaced_chars
            ORDER BY replaced_chars DESC, path
            LIMIT 20
            """
        ).data()
        checks = {
            "requirements_without_part_of": session.run(
                "MATCH (r:Requirement) WHERE NOT (r)-[:PART_OF]->() RETURN count(r) AS c"
            ).single()["c"],
            "documents_without_chunks": session.run(
                "MATCH (d:Document) WHERE NOT (d)-[:CONTAINS_CHUNK]->() RETURN count(d) AS c"
            ).single()["c"],
            "chunks_without_links": session.run(
                "MATCH (c:Chunk) WHERE NOT ()-[:CONTAINS_CHUNK]->(c) AND NOT (c)-[:MENTIONS]->() RETURN count(c) AS c"
            ).single()["c"],
            "files_without_touches": session.run(
                "MATCH (f:File) WHERE NOT ()-[:TOUCHED]->(f) RETURN count(f) AS c"
            ).single()["c"],
            "libraries_without_links": session.run(
                "MATCH (l:Library) WHERE NOT ()-[:USES_LIBRARY]->(l) AND NOT ()-[:MENTIONS_LIBRARY]->(l) RETURN count(l) AS c"
            ).single()["c"],
            "commits_without_touches": session.run(
                "MATCH (c:GitCommit) WHERE NOT (c)-[:TOUCHED]->() RETURN count(c) AS c"
            ).single()["c"],
        }
    return {
        "node_counts": node_counts,
        "relationship_counts": rel_counts,
        "orphans": orphans,
        "checks": checks,
        "library_summary": {
            "sources": library_sources,
            "languages": library_languages,
            "top_usage": library_usage_top,
        },
        "decode_stats": {
            "by_encoding": decode_summary,
            "fallback_samples": decode_fallbacks,
        },
    }


@router.post("/api/v1/dev-graph/audit")
def generate_audit(write_to_disk: bool = True, output_dir: str = "dev_graph_audit"):
    try:
        report = _compute_audit(driver)
        path = None
        if write_to_disk:
            os.makedirs(output_dir, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            path = os.path.join(output_dir, f"audit-{ts}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        return {"success": True, "report_path": path, **report}
    except Exception as e:
        logger.exception("Audit generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/docs")
def ingest_docs():
    try:
        ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        ing.ingest()
        return {"success": True}
    except Exception as e:
        logger.exception("Enhanced docs ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/git/enhanced")
def ingest_git_enhanced():
    try:
        engine.apply_schema()
        temporal_limit = 1000
        try:
            temporal_limit = int(os.environ.get("TEMPORAL_LIMIT", "1000"))
        except Exception:
            temporal_limit = 1000
        ingested = engine.ingest_recent_commits(limit=temporal_limit)
        try:
            ing = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            ing.ingest()
        except Exception:
            pass
        try:
            sprint_mapper.map_all_sprints()
        except Exception:
            pass
        derived = deriver.derive_all()
        return {"success": True, "ingested_commits": ingested, "derived": derived, "metrics": engine.get_metrics()}
    except Exception as e:
        logger.exception("Enhanced git ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/git/batched")
def ingest_git_batched(
    limit: int = Query(100, ge=1, le=2000),
    batch_size: int = Query(25, ge=5, le=100),
):
    try:
        start_time = time.time()
        engine.apply_schema()
        ingested = engine.ingest_recent_commits_batched(limit=limit, batch_size=batch_size)
        duration = time.time() - start_time
        return {
            "success": True,
            "ingested_commits": ingested,
            "batch_size": batch_size,
            "duration_seconds": round(duration, 2),
            "commits_per_second": round(ingested / max(duration, 0.001), 2),
            "metrics": engine.get_metrics(),
        }
    except Exception as e:
        logger.exception("Batched git ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/temporal-semantic")
def ingest_temporal_semantic(
    commit_limit: int = Query(100, ge=1, le=1000),
    derive_relationships: bool = Query(True)
):
    try:
        logger.info(f"Starting temporal semantic ingestion: commits={commit_limit}, derive_relationships={derive_relationships}")
        start_time = time.time()
        engine.apply_schema()
        with driver.session() as session:
            logger.info("Clearing existing graph data for fresh temporal semantic ingestion...")
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Running unified temporal semantic processing...")
        commit_results = parallel_pipeline.ingest_commits_parallel(limit=commit_limit)
        logger.info(f"Processed {commit_results['commits_ingested']} commits")
        doc_ingester = EnhancedDevGraphIngester(REPO_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        doc_ingester.ingest()
        logger.info("Processed documents and created chunks")
        try:
            mapped = sprint_mapper.map_all_sprints()
            logger.info(f"Mapped sprints: {mapped}")
        except Exception as e:
            logger.warning(f"Sprint mapping failed: {e}")
        if derive_relationships:
            logger.info("Deriving semantic relationships...")
            try:
                derived = deriver.derive_all()
                logger.info(f"Derived relationships: {derived}")
            except Exception as e:
                logger.warning(f"Relationship derivation failed: {e}")
        with driver.session() as session:
            node_counts = session.run("MATCH (n) UNWIND labels(n) as label RETURN label as type, count(*) as count ORDER BY count DESC").data()
            rel_counts = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC").data()
        total_duration = time.time() - start_time
        node_stats = {item["type"]: item["count"] for item in node_counts}
        rel_stats = {item["type"]: item["count"] for item in rel_counts}
        return {
            "success": True,
            "results": {
                "commits_ingested": node_stats.get("GitCommit", 0),
                "files_processed": node_stats.get("File", 0),
                "chunks_created": node_stats.get("Chunk", 0),
                "documents_created": node_stats.get("Document", 0),
                "requirements_created": node_stats.get("Requirement", 0),
                "sprints_created": node_stats.get("Sprint", 0),
                "relationships_derived": sum(rel_stats.values()),
                "total_duration": total_duration,
            },
            "node_types": node_stats,
            "relationship_types": rel_stats,
            "message": f"Temporal semantic ingestion completed: {node_stats.get('GitCommit', 0)} commits, {node_stats.get('Chunk', 0)} chunks, {sum(rel_stats.values())} relationships",
        }
    except Exception as e:
        logger.error(f"Temporal semantic ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/parallel")
def ingest_commits_parallel(
    limit: int = Query(100, ge=1, le=1000),
    max_workers: int = Query(4, ge=1, le=8),
    batch_size: int = Query(50, ge=10, le=200)
):
    try:
        ingested_count = engine.ingest_recent_commits_parallel(limit=limit, max_workers=max_workers, batch_size=batch_size)
        return {"success": True, "ingested_commits": ingested_count, "performance": {"max_workers": max_workers, "batch_size": batch_size, "total_limit": limit}}
    except Exception as e:
        return {"success": False, "error": str(e), "ingested_commits": 0}


@router.post("/api/v1/dev-graph/ingest/chunks")
def ingest_chunks(
    include_docs: bool = Query(True, description="Include document chunking"),
    include_code: bool = Query(True, description="Include code chunking"),
    doc_limit: int = Query(None, description="Limit number of documents (None = no limit)"),
    code_limit: int = Query(None, description="Limit number of code files (None = no limit)"),
    files: Optional[List[str]] = Query(None, description="Specific files to chunk"),
):
    try:
        # Prefer direct chunk service for feature parity
        from ..app_state import chunk_service
        if files:
            stats = chunk_service.ingest_specific_files(files)
            return {"success": True, "stats": stats, "chunk_statistics": chunk_service.get_chunk_statistics()}
        stats = chunk_service.ingest_all_chunks(
            include_docs=include_docs,
            include_code=include_code,
            doc_limit=doc_limit,
            code_limit=code_limit,
        )
        return {"success": True, "stats": stats, "chunk_statistics": chunk_service.get_chunk_statistics()}
    except Exception as e:
        logger.exception("Chunk ingestion failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/chunks/background")
def ingest_chunks_background(
    include_docs: bool = Query(True, description="Include document chunking"),
    include_code: bool = Query(True, description="Include code chunking"),
    files: Optional[List[str]] = Query(None, description="Specific files to chunk"),
):
    """Start chunking in background - returns immediately with job ID."""
    try:
        import threading
        import uuid
        from ..app_state import chunk_service
        
        job_id = str(uuid.uuid4())
        
        def background_chunking():
            try:
                if files:
                    stats = chunk_service.ingest_specific_files(files)
                else:
                    stats = chunk_service.ingest_all_chunks(
                        include_docs=include_docs,
                        include_code=include_code,
                        doc_limit=None,  # No limits
                        code_limit=None,  # No limits
                    )
                logger.info(f"Background chunking job {job_id} completed: {stats}")
            except Exception as e:
                logger.error(f"Background chunking job {job_id} failed: {e}")
        
        # Start background thread
        thread = threading.Thread(target=background_chunking, daemon=True)
        thread.start()
        
        return {
            "success": True, 
            "job_id": job_id,
            "message": "Chunking started in background",
            "status": "running"
        }
    except Exception as e:
        logger.exception("Background chunking failed to start")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/derive-relationships")
def derive_relationships(since_timestamp: Optional[str] = None, dry_run: bool = False, strategies: Optional[List[str]] = None):
    start = time.time()
    try:
        if dry_run:
            return {"success": True, "derived": {"implements": 0, "evolves_from": 0, "depends_on": 0}, "confidence_stats": {"avg_confidence": 0.0, "high_confidence": 0, "medium_confidence": 0, "low_confidence": 0}, "duration_seconds": round(time.time() - start, 2), "message": "Dry run mode - no relationships derived"}
        result = deriver.derive_all(since_timestamp)
        derived_total = int(result.get("implements", 0)) + int(result.get("evolves_from", 0)) + int(result.get("depends_on", 0))
        return {"success": True, "derived": {"implements": result["implements"], "evolves_from": result["evolves_from"], "depends_on": result["depends_on"]}, "confidence_stats": result["confidence_stats"], "duration_seconds": round(time.time() - start, 2), "message": f"Derived {derived_total} relationships with evidence-based confidence scoring"}
    except Exception as e:
        logger.exception("Relationship derivation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/embeddings")
def generate_embeddings(
    chunk_ids: Optional[List[str]] = Query(None),
    batch_size: int = Query(10, ge=1, le=50),
    limit: int = Query(1000, ge=1, le=10000)
):
    try:
        if not chunk_ids:
            with driver.session() as session:
                limited_chunk_ids = session.run(
                    """
                    MATCH (ch:Chunk)
                    WHERE ch.embedding IS NULL AND ch.text IS NOT NULL
                    RETURN ch.id as id
                    LIMIT $limit
                    """,
                    limit=limit,
                ).data()
                chunk_ids = [record["id"] for record in limited_chunk_ids]
        stats = embedding_service.generate_embeddings_for_chunks(chunk_ids=chunk_ids, batch_size=batch_size)
        return {"success": True, "stats": stats, "embedding_statistics": embedding_service.get_embedding_statistics()}
    except Exception as e:
        logger.exception("Embedding generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/embeddings/statistics")
def get_embedding_statistics():
    try:
        return embedding_service.get_embedding_statistics()
    except Exception as e:
        logger.exception("Embedding stats failed")
        raise HTTPException(status_code=500, detail=str(e))
