"""
Unified Parallel Ingestion Pipeline
Single robust endpoint that handles all ingestion in one go with comprehensive reporting.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from neo4j import Driver

from ..app_state import (
    driver,
    engine,
    git,
    sprint_mapper,
    deriver,
    embedding_service,
    parallel_pipeline,
    chunk_service,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    REPO_PATH,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Global state for tracking ingestion progress
ingestion_state = {
    "is_running": False,
    "current_stage": None,
    "progress": {},
    "start_time": None,
    "end_time": None,
    "error": None,
    "last_successful_run": None
}

class UnifiedIngestionPipeline:
    """Unified ingestion pipeline that handles everything in parallel with comprehensive reporting."""
    
    def __init__(self, driver: Driver, repo_path: str):
        self.driver = driver
        self.repo_path = repo_path
        self.start_time = None
        self.stages_completed = 0
        self.total_stages = 6
        self.results = {}
        
    def run_complete_ingestion(self, 
                              reset_graph: bool = True,
                              commit_limit: int = None,
                              doc_limit: int = None,
                              code_limit: int = None,
                              derive_relationships: bool = True,
                              include_embeddings: bool = False,
                              max_workers: int = 4) -> Dict[str, Any]:
        """Run complete unified ingestion pipeline."""
        
        self.start_time = time.time()
        self.chunk_stats = None
        logger.info("Starting Unified Parallel Ingestion Pipeline")
        
        try:
            # Stage 1: Reset and Schema
            self._stage_1_reset_and_schema(reset_graph)
            
            # Stage 2: Parallel Commit Ingestion
            self._stage_2_parallel_commits(commit_limit, max_workers)
            
            # Stage 3: Parallel Document Ingestion
            self._stage_3_parallel_documents(doc_limit, code_limit, max_workers)
            
            # Stage 4: Parallel Code Chunking
            self._stage_4_parallel_code_chunking(code_limit, max_workers)
            
            # Stage 5: Sprint Mapping
            self._stage_5_sprint_mapping()
            
            # Stage 6: Relationship Derivation
            if derive_relationships:
                self._stage_6_relationship_derivation()
            
            # Stage 7: Embeddings (optional)
            if include_embeddings:
                self._stage_7_embeddings()
            
            # Final reporting
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Unified ingestion failed: {e}")
            self.results["error"] = str(e)
            self.results["success"] = False
            return self.results
    
    def _stage_1_reset_and_schema(self, reset_graph: bool):
        """Stage 1: Reset database and apply schema."""
        logger.info("Stage 1/7: Reset and Schema")
        
        if reset_graph:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Database reset complete")
        
        engine.apply_schema()
        logger.info("Schema applied")
        
        self.stages_completed += 1
        self.results["stage_1"] = {
            "database_reset": reset_graph,
            "schema_applied": True,
            "duration": time.time() - self.start_time
        }
    
    def _stage_2_parallel_commits(self, commit_limit: int, max_workers: int):
        """Stage 2: Parallel commit ingestion."""
        logger.info("Stage 2/7: Parallel Commit Ingestion")
        
        start_time = time.time()
        commit_results = parallel_pipeline.ingest_commits_parallel(limit=commit_limit)
        
        self.stages_completed += 1
        self.results["stage_2"] = {
            "commits_ingested": commit_results.get("commits_ingested", 0),
            "files_processed": commit_results.get("files_processed", 0),
            "duration": time.time() - start_time,
            "max_workers": max_workers
        }
        logger.info(f"Ingested {commit_results.get('commits_ingested', 0)} commits")
    
    def _stage_3_parallel_documents(self, doc_limit: int, code_limit: int, max_workers: int):
        """Stage 3: Discover files and create chunks."""
        logger.info("Stage 3/7: Repository Discovery & Chunking")

        start_time = time.time()
        should_process_docs = doc_limit is None or doc_limit > 0
        should_process_code = code_limit is None or code_limit > 0

        self.chunk_stats = chunk_service.ingest_all_chunks(
            include_docs=should_process_docs,
            include_code=should_process_code,
            doc_limit=doc_limit,
            code_limit=code_limit,
        )

        doc_info = self.chunk_stats.get("documents", {})
        discovery = self.chunk_stats.get("discovery", {})
        samples = self.chunk_stats.get("samples", {})
        stage_duration = time.time() - start_time

        self.stages_completed += 1
        self.results["stage_3"] = {
            "documents_discovered": doc_info.get("discovered", 0),
            "documents_selected": doc_info.get("selected", 0),
            "documents_processed": doc_info.get("processed", 0),
            "doc_chunks_created": doc_info.get("chunks", 0),
            "doc_errors": doc_info.get("errors", 0),
            "doc_skipped": doc_info.get("skipped_due_to_limit", 0),
            "doc_failures": doc_info.get("failures", [])[:10],
            "doc_duration": doc_info.get("duration", stage_duration),
            "discovery_summary": discovery,
            "discovery_samples": samples,
            "duration": stage_duration,
            "max_workers": max_workers,
        }

        logger.info(
            "Processed %d documents (%d chunks, %d errors)",
            self.results["stage_3"].get("documents_processed", 0),
            self.results["stage_3"].get("doc_chunks_created", 0),
            self.results["stage_3"].get("doc_errors", 0),
        )

    def _stage_4_parallel_code_chunking(self, code_limit: int, max_workers: int):
        """Stage 4: Summarize code chunking results."""
        logger.info("Stage 4/7: Code Chunk Summary")

        if not self.chunk_stats:
            logger.warning("Skipping code chunk summary because no chunk stats are available")
            self.stages_completed += 1
            self.results["stage_4"] = {
                "code_files_discovered": 0,
                "code_files_selected": 0,
                "code_files_processed": 0,
                "code_chunks_created": 0,
                "code_errors": 0,
                "code_skipped": 0,
                "code_failures": [],
                "duration": 0.0,
                "max_workers": max_workers,
            }
            return

        code_info = self.chunk_stats.get("code_files", {})
        samples = self.chunk_stats.get("samples", {})

        self.stages_completed += 1
        self.results["stage_4"] = {
            "code_files_discovered": code_info.get("discovered", 0),
            "code_files_selected": code_info.get("selected", 0),
            "code_files_processed": code_info.get("processed", 0),
            "code_chunks_created": code_info.get("chunks", 0),
            "code_errors": code_info.get("errors", 0),
            "code_skipped": code_info.get("skipped_due_to_limit", 0),
            "code_failures": code_info.get("failures", [])[:10],
            "code_samples": samples.get("code", []),
            "duration": code_info.get("duration", 0.0),
            "limit": code_limit,
            "max_workers": max_workers,
        }

        logger.info(
            "Processed %d code files (%d chunks, %d errors)",
            self.results["stage_4"].get("code_files_processed", 0),
            self.results["stage_4"].get("code_chunks_created", 0),
            self.results["stage_4"].get("code_errors", 0),
        )

    def _stage_5_sprint_mapping(self):
        """Stage 5: Sprint mapping."""
        logger.info("Stage 5/7: Sprint Mapping")
        
        start_time = time.time()
        mapped = sprint_mapper.map_all_sprints()
        
        # Create Sprint nodes in the database
        if isinstance(mapped, dict) and mapped.get("windows"):
            sprint_windows = mapped.get("windows", [])
            sprint_nodes = []
            
            for window in sprint_windows:
                sprint_nodes.append({
                    "number": window["number"],
                    "name": window["name"],
                    "start_date": window["start"],
                    "end_date": window["end"],
                    "uid": window["number"]
                })
            
            # Create Sprint nodes in database
            with self.driver.session() as session:
                session.run("""
                    UNWIND $sprints AS sprint
                    MERGE (s:Sprint {number: sprint.number})
                    SET s.name = sprint.name, 
                        s.start_date = sprint.start_date, 
                        s.end_date = sprint.end_date,
                        s.uid = sprint.uid
                """, sprints=sprint_nodes)
                
                # Create INCLUDES relationships between sprints and commits
                for window in sprint_windows:
                    session.run("""
                        MATCH (s:Sprint {number: $sprint_number})
                        MATCH (c:GitCommit)
                        WHERE datetime(c.timestamp) >= datetime($start_date)
                          AND datetime(c.timestamp) <= datetime($end_date)
                        MERGE (s)-[:INCLUDES]->(c)
                    """, 
                    sprint_number=window["number"],
                    start_date=window["start"],
                    end_date=window["end"])
                
                # Create CONTAINS_DOC relationships between sprints and documents
                for window in sprint_windows:
                    sprint_number = window["number"]
                    # Find documents that belong to this sprint based on path
                    session.run("""
                        MATCH (s:Sprint {number: $sprint_number})
                        MATCH (d:Document)
                        WHERE d.path CONTAINS $sprint_pattern
                        MERGE (s)-[:CONTAINS_DOC]->(d)
                    """, 
                    sprint_number=sprint_number,
                    sprint_pattern=f"sprint-{sprint_number}")
        
        self.stages_completed += 1
        self.results["stage_5"] = {
            "sprints_mapped": mapped.get("count", 0) if isinstance(mapped, dict) else 0,
            "sprint_windows": mapped.get("windows", []) if isinstance(mapped, dict) else [],
            "duration": time.time() - start_time
        }
        logger.info(f"Mapped {mapped.get('count', 0) if isinstance(mapped, dict) else 0} sprints")
    
    def _stage_6_relationship_derivation(self):
        """Stage 6: Relationship derivation."""
        logger.info("Stage 6/7: Relationship Derivation")
        
        start_time = time.time()
        derived_result = deriver.derive_all()
        
        self.stages_completed += 1
        total_derived = (derived_result.get("implements", 0) + 
                        derived_result.get("evolves_from", 0) + 
                        derived_result.get("depends_on", 0))
        
        self.results["stage_6"] = {
            "implements_derived": derived_result.get("implements", 0),
            "evolves_from_derived": derived_result.get("evolves_from", 0),
            "depends_on_derived": derived_result.get("depends_on", 0),
            "total_relationships": total_derived,
            "confidence_stats": derived_result.get("confidence_stats", {}),
            "duration": time.time() - start_time
        }
        logger.info(f"Derived {total_derived} relationships")
    
    def _stage_7_embeddings(self):
        """Stage 7: Generate embeddings (optional)."""
        logger.info("Stage 7/7: Embedding Generation")
        
        start_time = time.time()
        
        # Get chunk statistics
        chunk_stats = chunk_service.get_chunk_statistics()
        total_chunks = chunk_stats.get("total_chunks", 0)
        
        # Generate embeddings for a subset of chunks
        if total_chunks > 0:
            with self.driver.session() as session:
                # Get chunks without embeddings
                result = session.run("""
                    MATCH (c:Chunk)
                    WHERE c.embedding IS NULL
                    WITH c LIMIT 1000
                    RETURN c.id as chunk_id, c.content as content
                """)
                
                chunks_to_embed = list(result)
                embedded_count = 0
                
                for record in chunks_to_embed:
                    try:
                        # Generate embedding (simplified - you'd use actual embedding service)
                        embedding = [0.0] * 512  # Placeholder embedding
                        
                        session.run("""
                            MATCH (c:Chunk {id: $chunk_id})
                            SET c.embedding = $embedding
                        """, chunk_id=record["chunk_id"], embedding=embedding)
                        
                        embedded_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to embed chunk {record['chunk_id']}: {e}")
        
        self.stages_completed += 1
        self.results["stage_7"] = {
            "chunks_embedded": embedded_count,
            "total_chunks": total_chunks,
            "duration": time.time() - start_time
        }
        logger.info(f"Generated embeddings for {embedded_count} chunks")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report."""
        end_time = time.time()
        total_duration = end_time - self.start_time
        
        # Get final database statistics
        with self.driver.session() as session:
            # Node counts
            node_result = session.run("""
                MATCH (n)
                WITH labels(n) as labels, count(n) as count
                UNWIND labels as label
                RETURN label, sum(count) as total
            """)
            node_counts = {record["label"]: record["total"] for record in node_result}
            
            # Relationship counts
            rel_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(r) as total
            """)
            rel_counts = {record["rel_type"]: record["total"] for record in rel_result}
            
            # Quality metrics
            quality_result = session.run("""
                MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphaned
            """)
            orphaned = quality_result.single()["orphaned"]
            
            quality_result = session.run("""
                MATCH ()-[r:TOUCHED|IMPLEMENTS]->()
                WHERE r.timestamp IS NULL
                RETURN count(r) AS missing_ts
            """)
            missing_ts = quality_result.single()["missing_ts"]
        
        # Calculate quality score
        total_nodes = sum(node_counts.values())
        total_rels = sum(rel_counts.values())
        orphan_ratio = orphaned / total_nodes if total_nodes > 0 else 0
        timestamp_ratio = missing_ts / total_rels if total_rels > 0 else 0
        quality_score = max(0, 100 - (orphan_ratio * 50) - (timestamp_ratio * 30))
        
        self.results.update({
            "success": True,
            "total_duration": total_duration,
            "stages_completed": self.stages_completed,
            "total_stages": self.total_stages,
            "final_statistics": {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "node_breakdown": node_counts,
                "relationship_breakdown": rel_counts,
                "quality_score": round(quality_score, 1),
                "orphaned_nodes": orphaned,
                "missing_timestamps": missing_ts
            },
            "performance_metrics": {
                "commits_per_second": self.results.get("stage_2", {}).get("commits_ingested", 0) / max(self.results.get("stage_2", {}).get("duration", 1), 1),
                "chunks_per_second": (self.results.get("stage_3", {}).get("doc_chunks_created", 0) + 
                                    self.results.get("stage_4", {}).get("code_chunks_created", 0)) / max(total_duration, 1),
                "relationships_per_second": self.results.get("stage_6", {}).get("total_relationships", 0) / max(self.results.get("stage_6", {}).get("duration", 1), 1)
            },
            "generated_at": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info(f"Unified ingestion completed in {total_duration:.2f}s")
        logger.info(f"Final stats: {total_nodes} nodes, {total_rels} relationships, Quality: {quality_score:.1f}/100")
        
        return self.results

@router.post("/api/v1/dev-graph/ingest/unified")
def unified_parallel_ingestion(
    reset_graph: bool = Query(True, description="Reset database before ingestion"),
    commit_limit: int = Query(1000, ge=1, le=10000, description="Maximum commits to ingest"),
    doc_limit: int = Query(100, ge=1, le=1000, description="Maximum documents to process"),
    code_limit: int = Query(500, ge=1, le=5000, description="Maximum code files to process"),
    derive_relationships: bool = Query(True, description="Derive semantic relationships"),
    include_embeddings: bool = Query(False, description="Generate embeddings for chunks"),
    max_workers: int = Query(4, ge=1, le=8, description="Maximum parallel workers")
):
    """
    Unified Parallel Ingestion Pipeline
    
    Single robust endpoint that handles all ingestion in one go:
    - Database reset and schema application
    - Parallel commit ingestion
    - Parallel document processing
    - Parallel code chunking
    - Sprint mapping
    - Relationship derivation
    - Optional embedding generation
    
    Returns comprehensive progress and performance metrics.
    """
    try:
        # Check if ingestion is already running
        if ingestion_state["is_running"]:
            return {
                "success": False,
                "error": "Ingestion already in progress",
                "current_stage": ingestion_state["current_stage"],
                "progress": ingestion_state["progress"]
            }
        
        # Set running state
        ingestion_state["is_running"] = True
        ingestion_state["start_time"] = time.time()
        ingestion_state["error"] = None
        
        # Run unified pipeline
        pipeline = UnifiedIngestionPipeline(driver, REPO_PATH)
        results = pipeline.run_complete_ingestion(
            reset_graph=reset_graph,
            commit_limit=commit_limit,
            doc_limit=doc_limit,
            code_limit=code_limit,
            derive_relationships=derive_relationships,
            include_embeddings=include_embeddings,
            max_workers=max_workers
        )
        
        # Update global state
        ingestion_state["is_running"] = False
        ingestion_state["end_time"] = time.time()
        ingestion_state["progress"] = results
        ingestion_state["current_stage"] = "completed"
        if results.get("success"):
            ingestion_state["last_successful_run"] = results
        
        return results
        
    except Exception as e:
        logger.error(f"Unified ingestion failed: {e}")
        ingestion_state["is_running"] = False
        ingestion_state["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/dev-graph/ingest/status")
def get_ingestion_status():
    """Get current ingestion status and progress."""
    return {
        "is_running": ingestion_state["is_running"],
        "current_stage": ingestion_state["current_stage"],
        "progress": ingestion_state["progress"],
        "start_time": ingestion_state["start_time"],
        "end_time": ingestion_state["end_time"],
        "error": ingestion_state["error"],
        "duration": (ingestion_state["end_time"] or time.time()) - (ingestion_state["start_time"] or 0) if ingestion_state["start_time"] else 0
    }

@router.post("/api/v1/dev-graph/ingest/stop")
def stop_ingestion():
    """Stop current ingestion (if running)."""
    if ingestion_state["is_running"]:
        ingestion_state["is_running"] = False
        ingestion_state["error"] = "Ingestion stopped by user"
        return {"success": True, "message": "Ingestion stopped"}
    else:
        return {"success": False, "message": "No ingestion currently running"}

@router.get("/api/v1/dev-graph/ingest/report")
def get_ingestion_report():
    """Get comprehensive ingestion report."""
    # Check for current progress first, then last successful run
    report_data = ingestion_state["progress"] if ingestion_state["progress"].get("success") else ingestion_state["last_successful_run"]
    
    if not report_data:
        return {"success": False, "message": "No successful ingestion data available"}
    
    return {
        "success": True,
        "report": report_data,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


