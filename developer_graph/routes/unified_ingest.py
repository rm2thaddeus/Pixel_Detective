"""
Unified Parallel Ingestion Pipeline
Single robust endpoint that handles all ingestion in one go with comprehensive reporting.
"""

import os
import time
import logging
import uuid
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
    import_extractor,
    parallel_pipeline,
    chunk_service,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    REPO_PATH,
)
from ..code_symbol_extractor import CodeSymbolExtractor
from ..document_code_linker import DocumentCodeLinker

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
    "last_successful_run": None,
    "ingestion_job_id": None,
    "stop_requested": False
}

ingestion_jobs: Dict[str, Dict[str, Any]] = {}


class IngestionStopped(Exception):
    """Raised when an ingestion job is cancelled by the user."""



def _create_ingestion_job(profile: str, delta: bool, subpath: Optional[str]) -> str:
    job_id = str(uuid.uuid4())
    now = time.time()
    ingestion_jobs[job_id] = {
        'job_id': job_id,
        'status': 'running',
        'profile': profile,
        'delta': delta,
        'subpath': subpath,
        'started_at': now,
        'updated_at': now,
        'finished_at': None,
        'current_stage': None,
        'stages_completed': 0,
        'total_stages': 0,
        'percent_complete': None,
        'progress': {},
        'error': None,
        'result': None,
    }
    ingestion_state.update({
        'is_running': True,
        'current_stage': None,
        'progress': ingestion_jobs[job_id]['progress'],
        'start_time': now,
        'end_time': None,
        'error': None,
        'ingestion_job_id': job_id,
        'stop_requested': False,
    })
    return job_id


def _get_job(job_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not job_id:
        return None
    return ingestion_jobs.get(job_id)


def _set_job_total_stages(job_id: str, total: int) -> None:
    job = ingestion_jobs.get(job_id)
    if not job:
        return
    job['total_stages'] = total
    job['updated_at'] = time.time()


def _set_job_stage(job_id: str, stage_index: int, description: str) -> None:
    job = ingestion_jobs.get(job_id)
    if not job:
        return
    label = f"Stage {stage_index}/{job.get('total_stages') or '?'}: {description}"
    job['current_stage'] = {'index': stage_index, 'description': description, 'label': label}
    job['updated_at'] = time.time()
    ingestion_state['current_stage'] = job['current_stage']


def _record_job_stage(job_id: str, stage_key: str, data: Dict[str, Any]) -> None:
    job = ingestion_jobs.get(job_id)
    if not job:
        return
    job['progress'][stage_key] = data
    job['stages_completed'] = len(job['progress'])
    total = job.get('total_stages') or 0
    job['percent_complete'] = round((job['stages_completed'] / total) * 100, 1) if total else None
    job['updated_at'] = time.time()
    ingestion_state['progress'] = job['progress']


def _finalize_job(job_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
    job = ingestion_jobs.get(job_id)
    if not job:
        return
    now = time.time()
    job['status'] = status
    job['finished_at'] = now
    job['updated_at'] = now
    job['current_stage'] = {'index': None, 'description': status, 'label': status.title()}
    if result is not None:
        job['result'] = result
    if error:
        job['error'] = error
    ingestion_state['is_running'] = False
    ingestion_state['end_time'] = now
    ingestion_state['error'] = error
    ingestion_state['stop_requested'] = False



class UnifiedIngestionPipeline:
    """Unified ingestion pipeline that handles everything in parallel with comprehensive reporting."""
    
    def __init__(self, driver: Driver, repo_path: str, job_id: Optional[str] = None):
        self.driver = driver
        self.repo_path = repo_path
        self.job_id = job_id
        self.start_time = None
        self.stages_completed = 0
        self.total_stages = 8
        self.results = {}
        self.last_commit_ingested = None
        self.doc_chunks_processed = 0
        self.subpath = None
        self.delta = False
        if self.job_id:
            _set_job_total_stages(self.job_id, self.total_stages)
    
    def _check_for_stop(self):
        """Check if ingestion should be stopped."""
        if ingestion_state.get("stop_requested", False):
            raise IngestionStopped("Ingestion stopped by user request")
    
    def _enter_stage(self, stage_num: int, description: str):
        """Enter a new stage and update job status."""
        if self.job_id:
            _set_job_stage(self.job_id, stage_num, description)
    
    def _publish_stage(self, stage_key: str, stage_data: Dict[str, Any]):
        """Publish stage results to job tracking."""
        if self.job_id:
            _record_job_stage(self.job_id, stage_key, stage_data)
        
    def run_complete_ingestion(self, 
                              reset_graph: bool = True,
                              commit_limit: Optional[int] = None,
                              doc_limit: Optional[int] = None,
                              code_limit: Optional[int] = None,
                              derive_relationships: bool = True,
                              include_embeddings: bool = False,
                              max_workers: int = 4,
                              delta: bool = False,
                              subpath: Optional[str] = None) -> Dict[str, Any]:
        """Run complete unified ingestion pipeline."""

        self.start_time = time.time()
        self.chunk_stats = None
        self.subpath = subpath
        self.delta = delta
        logger.info("Starting Unified Parallel Ingestion Pipeline")

        try:
            # Stage 1: Reset and Schema
            self._stage_1_reset_and_schema(reset_graph)

            # Stage 2: Parallel Commit Ingestion
            self._stage_2_parallel_commits(commit_limit, max_workers)

            # Stage 3: Repository Discovery & Chunking
            self._stage_3_parallel_documents(doc_limit, code_limit, max_workers, delta, subpath)

            # Stage 4: Code Chunk Summary
            self._stage_4_parallel_code_chunking(code_limit, max_workers)

            # Stage 5: Sprint Mapping
            self._stage_5_sprint_mapping()

            # Stage 6: Relationship Derivation
            if derive_relationships:
                self._stage_6_relationship_derivation()
            else:
                self._enter_stage(6, "Relationship Derivation")
                stage_payload = {"skipped": True, "reason": "derive_relationships disabled"}
                self.stages_completed += 1
                self._publish_stage("stage_6", stage_payload)

            # Stage 7: Embeddings (optional)
            if include_embeddings:
                self._stage_7_embeddings()
            else:
                self._enter_stage(7, "Embeddings")
                stage_payload = {"skipped": True, "reason": "embeddings disabled"}
                self.stages_completed += 1
                self._publish_stage("stage_7", stage_payload)

            # Stage 8: Enhanced Connectivity (Code Symbols & Co-occurrence)
            self._stage_8_enhanced_connectivity()

            final_report = self._generate_final_report()
            if self.job_id:
                _finalize_job(self.job_id, 'completed', result=final_report)
            return final_report

        except IngestionStopped as stop:
            logger.info("Unified ingestion stopped: %s", stop)
            self.results["error"] = str(stop)
            self.results["success"] = False
            self.results["stopped"] = True
            if self.job_id:
                _finalize_job(self.job_id, 'stopped', result=self.results, error=str(stop))
            return self.results

        except Exception as e:
            logger.error(f"Unified ingestion failed: {e}")
            self.results["error"] = str(e)
            self.results["success"] = False
            if self.job_id:
                _finalize_job(self.job_id, 'failed', result=self.results, error=str(e))
            return self.results

    def _stage_1_reset_and_schema(self, reset_graph: bool):
        """Stage 1: Reset database and apply schema."""
        self._check_for_stop()
        self._enter_stage(1, "Reset and Schema")
        logger.info("Stage 1/8: Reset and Schema")

        if reset_graph:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Database reset complete")

        engine.apply_schema()
        logger.info("Schema applied")

        stage_payload = {
            "database_reset": reset_graph,
            "schema_applied": True,
            "duration": time.time() - self.start_time,
        }
        self.stages_completed += 1
        self._publish_stage("stage_1", stage_payload)

    def _stage_2_parallel_commits(self, commit_limit: int, max_workers: int):
        """Stage 2: Parallel commit ingestion."""
        self._check_for_stop()
        self._enter_stage(2, "Parallel Commit Ingestion")
        logger.info("Stage 2/8: Parallel Commit Ingestion")

        start_time = time.time()
        commit_results = parallel_pipeline.ingest_commits_parallel(limit=commit_limit)

        stage_payload = {
            "commits_ingested": commit_results.get("commits_ingested", 0),
            "files_processed": commit_results.get("files_processed", 0),
            "duration": time.time() - start_time,
            "max_workers": max_workers,
            "last_commit": commit_results.get("last_commit")
        }
        self.last_commit_ingested = commit_results.get("last_commit")
        self.stages_completed += 1
        self._publish_stage("stage_2", stage_payload)

    def _stage_3_parallel_documents(self, doc_limit: Optional[int], code_limit: Optional[int], max_workers: int, delta: bool, subpath: Optional[str]):
        """Stage 3: Discover files and create chunks."""
        self._check_for_stop()
        self._enter_stage(3, "Repository Discovery & Chunking")
        logger.info("Stage 3/8: Repository Discovery & Chunking")

        start_time = time.time()
        should_process_docs = doc_limit is None or doc_limit > 0
        should_process_code = code_limit is None or code_limit > 0

        original_workers = getattr(chunk_service, 'parallel_workers', None)
        chunk_service.parallel_workers = max_workers
        try:
            self.chunk_stats = chunk_service.ingest_all_chunks(
                include_docs=should_process_docs,
                include_code=should_process_code,
                doc_limit=doc_limit,
                code_limit=code_limit,
                delta=delta,
                subpath=subpath,
                last_commit=self.last_commit_ingested,
            )
        finally:
            if original_workers is not None:
                chunk_service.parallel_workers = original_workers

        doc_info = self.chunk_stats.get("documents", {})
        code_info = self.chunk_stats.get("code_files", {})
        discovery = self.chunk_stats.get("discovery", {})
        samples = self.chunk_stats.get("samples", {})
        stage_duration = time.time() - start_time

        stage_payload = {
            "documents_discovered": doc_info.get("discovered", 0),
            "documents_selected": doc_info.get("selected", 0),
            "documents_processed": doc_info.get("processed", 0),
            "doc_chunks_created": doc_info.get("chunks", 0),
            "doc_errors": doc_info.get("errors", 0),
            "doc_delta_filtered": doc_info.get("delta_filtered", 0),
            "doc_skipped": doc_info.get("skipped_due_to_limit", 0),
            "doc_failures": doc_info.get("failures", []),
            "doc_duration": doc_info.get("duration", stage_duration),
            "doc_limit": doc_limit,
            "code_files_discovered": code_info.get("discovered", 0),
            "code_files_selected": code_info.get("selected", 0),
            "code_files_processed": code_info.get("processed", 0),
            "code_chunks_created": code_info.get("chunks", 0),
            "code_errors": code_info.get("errors", 0),
            "code_delta_filtered": code_info.get("delta_filtered", 0),
            "code_skipped": code_info.get("skipped_due_to_limit", 0),
            "code_failures": code_info.get("failures", []),
            "code_duration": code_info.get("duration", 0.0),
            "code_limit": code_limit,
            "discovery_summary": discovery,
            "discovery_samples": samples,
            "manifest": self.chunk_stats.get("manifest", {}),
            "cleanup": self.chunk_stats.get("cleanup", {}),
            "limits": self.chunk_stats.get("limits", {"doc_limit": doc_limit, "code_limit": code_limit}),
            "slow_documents": self.chunk_stats.get("slow_documents", []),
            "slow_code": self.chunk_stats.get("slow_code", []),
            "total_chunks": self.chunk_stats.get("total_chunks", 0),
            "total_errors": self.chunk_stats.get("total_errors", 0),
            "duration": stage_duration,
            "max_workers": max_workers,
            "delta_mode": delta,
            "subpath": subpath,
        }
        self.doc_chunks_processed = doc_info.get("processed", 0)
        self.code_files_processed = code_info.get("processed", 0)
        self.stages_completed += 1
        if stage_payload.get('slow_documents'):
            logger.info("Top slow documents: %s", stage_payload['slow_documents'])
        if stage_payload.get('slow_code'):
            logger.info("Top slow code files: %s", stage_payload['slow_code'])
        self._publish_stage("stage_3", stage_payload)

    def _stage_4_parallel_code_chunking(self, code_limit: Optional[int], max_workers: int):
        """Stage 4: Summarize code chunking results."""
        self._check_for_stop()
        self._enter_stage(4, "Code Chunk Summary")
        logger.info("Stage 4/8: Code Chunk Summary")

        if not self.chunk_stats:
            stage_payload = {
                "code_files_discovered": 0,
                "code_files_selected": 0,
                "code_files_processed": 0,
                "code_chunks_created": 0,
                "code_errors": 0,
                "code_skipped": 0,
                "code_failures": [],
                "code_duration": 0.0,
                "code_limit": code_limit,
                "duration": 0.0,
                "max_workers": max_workers
            }
            self.stages_completed += 1
            self._publish_stage("stage_4", stage_payload)
            return

        code_info = self.chunk_stats.get("code_files", {})
        stage_payload = {
            "code_files_discovered": code_info.get("discovered", 0),
            "code_files_selected": code_info.get("selected", 0),
            "code_files_processed": code_info.get("processed", 0),
            "code_chunks_created": code_info.get("chunks", 0),
            "code_errors": code_info.get("errors", 0),
            "code_delta_filtered": code_info.get("delta_filtered", 0),
            "code_skipped": code_info.get("skipped_due_to_limit", 0),
            "code_failures": code_info.get("failures", []),
            "code_duration": code_info.get("duration", 0.0),
            "code_limit": code_limit,
            "duration": code_info.get("duration", 0.0),
            "max_workers": max_workers
        }
        self.stages_completed += 1
        self._publish_stage("stage_4", stage_payload)

    def _stage_5_sprint_mapping(self):
        """Stage 5: Sprint Mapping."""
        self._check_for_stop()
        self._enter_stage(5, "Sprint Mapping")
        logger.info("Stage 5/8: Sprint Mapping")

        start_time = time.time()
        sprint_results = sprint_mapper.map_all_sprints()

        stage_payload = {
            "sprints_mapped": sprint_results.get("sprints_mapped", 0),
            "documents_linked": sprint_results.get("documents_linked", 0),
            "commits_linked": sprint_results.get("commits_linked", 0),
            "duration": time.time() - start_time
        }
        self.stages_completed += 1
        self._publish_stage("stage_5", stage_payload)

    def _stage_6_relationship_derivation(self):
        """Stage 6: Relationship derivation."""
        self._check_for_stop()
        self._enter_stage(6, "Relationship Derivation")
        logger.info("Stage 6/8: Relationship Derivation")

        start_time = time.time()
        import_start = time.time()
        import_stats = import_extractor.refresh_import_graph()
        import_stats["duration"] = time.time() - import_start
        logger.info(
            "Stage 6: Import graph upserted %d edges (created %d, deleted %d)",
            import_stats.get("relationships_upserted", 0),
            import_stats.get("relationships_created", 0),
            import_stats.get("relationships_deleted", 0),
        )

        derivation_results = deriver.derive_all(last_commit=self.last_commit_ingested)

        total_relationships = (
            import_stats.get("relationships_upserted", 0)
            + derivation_results.get("implements", 0)
            + derivation_results.get("evolves_from", 0)
            + derivation_results.get("depends_on", 0)
        )

        stage_payload = {
            "import_graph": import_stats,
            "implements": derivation_results.get("implements", 0),
            "evolves_from": derivation_results.get("evolves_from", 0),
            "depends_on": derivation_results.get("depends_on", 0),
            "depends_on_skipped": derivation_results.get("depends_on_skipped", False),
            "confidence_stats": derivation_results.get("confidence_stats", {}),
            "duration": time.time() - start_time,
            "total_relationships": total_relationships,
            "last_commit": self.last_commit_ingested,
        }
        self.stages_completed += 1
        self._publish_stage("stage_6", stage_payload)

    def _stage_7_embeddings(self):
        """Stage 7: Generate embeddings for chunks."""
        self._check_for_stop()
        self._enter_stage(7, "Embeddings")
        logger.info("Stage 7/8: Embeddings Generation")

        start_time = time.time()
        embedded_count = 0
        total_chunks = 0

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Chunk)
                WHERE c.embedding IS NULL
                RETURN count(c) AS total
                """
            )
            total_chunks = result.single()["total"]

            if total_chunks == 0:
                logger.info("No chunks require embeddings")
            else:
                logger.info("Generating embeddings for %d chunks", total_chunks)
                chunk_records = session.run(
                    """
                    MATCH (c:Chunk)
                    WHERE c.embedding IS NULL
                    RETURN c.id as chunk_id
                    """
                )
                for record in chunk_records:
                    try:
                        embedding = [0.0] * 512  # Placeholder embedding logic
                        session.run(
                            """
                            MATCH (c:Chunk {id: $chunk_id})
                            SET c.embedding = $embedding
                            """,
                            chunk_id=record["chunk_id"],
                            embedding=embedding,
                        )
                        embedded_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to embed chunk {record['chunk_id']}: {e}")

        stage_payload = {
            "chunks_embedded": embedded_count,
            "total_chunks": total_chunks,
            "duration": time.time() - start_time
        }
        self.stages_completed += 1
        self._publish_stage("stage_7", stage_payload)

    def _stage_8_enhanced_connectivity(self):
        """Stage 8: Enhanced connectivity through code symbols and co-occurrence analysis."""
        self._check_for_stop()
        self._enter_stage(8, "Enhanced Connectivity")
        logger.info("Stage 8/8: Enhanced Connectivity")

        start_time = time.time()

        try:
            extractor = CodeSymbolExtractor(self.driver, self.repo_path)
            doc_linker = DocumentCodeLinker(self.driver, self.repo_path)

            with self.driver.session() as session:
                query = (
                    """
                    MATCH (f:File)
                    WHERE NOT coalesce(f.is_doc, false)
                      AND f.path =~ $pattern
                    """
                )
                params = {"pattern": "(?i).*\.(py|ts|tsx|js|jsx)$"}
                if self.subpath:
                    query += " AND f.path STARTS WITH $subpath"
                    params["subpath"] = self.subpath
                query += " RETURN f.path AS path, f.symbol_hash AS symbol_hash ORDER BY f.path"

                records = session.run(query, **params)
                code_files = [
                    {"path": record["path"], "symbol_hash": record.get("symbol_hash")}
                    for record in records
                ]

            force_doc_refresh = bool(self.doc_chunks_processed)
            logger.info(f"Stage 8: Processing {len(code_files)} code files")
            
            try:
                symbol_results = extractor.run_enhanced_connectivity(
                    code_files,
                    force_doc_refresh=force_doc_refresh,
                )
                logger.info(f"Stage 8: Symbol extraction completed: {symbol_results}")
            except Exception as symbol_exc:
                logger.exception("Symbol extraction failed: %s", symbol_exc)
                symbol_results = {"symbol_error": str(symbol_exc)}
            
            try:
                doc_results = doc_linker.link_documents_to_code()
                logger.info(f"Stage 8: Document linking completed: {doc_results}")
            except Exception as doc_exc:
                logger.exception("Document/code linking failed: %s", doc_exc)
                doc_results = {"doc_link_error": str(doc_exc)}

            stage_payload = {
                **symbol_results,
                **doc_results,
                "duration": time.time() - start_time,
                "candidates": len(code_files),
                "force_doc_refresh": force_doc_refresh,
            }
        except Exception as exc:
            logger.exception("Enhanced connectivity failed: %s", exc)
            stage_payload = {
                "error": str(exc),
                "duration": time.time() - start_time,
            }

        self.stages_completed += 1
        self._publish_stage("stage_8", stage_payload)
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
    doc_limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum documents to process (omit for all)"),
    code_limit: Optional[int] = Query(None, ge=1, le=5000, description="Maximum code files to process (omit for all)"),
    derive_relationships: bool = Query(True, description="Derive semantic relationships"),
    include_embeddings: bool = Query(False, description="Generate embeddings for chunks"),
    max_workers: int = Query(4, ge=1, le=8, description="Maximum parallel workers"),
    profile: str = Query("full", regex="^(full|delta|quick)$", description="Ingestion profile"),
    subpath: Optional[str] = Query(None, description="Limit ingestion to files under this repo-relative path")
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
        if ingestion_state["is_running"]:
            current_job_id = ingestion_state.get("ingestion_job_id")
            return {
                "success": False,
                "error": "Ingestion already in progress",
                "job_id": current_job_id,
                "job": _get_job(current_job_id),
            }

        profile_value = profile.strip().lower() if profile else "full"
        normalized_subpath = subpath.replace('\\', '/').strip('/') if subpath else None

        delta_flag = profile_value == "delta"
        if profile_value == "quick":
            delta_flag = False
            if doc_limit is None:
                doc_limit = 50
            if code_limit is None:
                code_limit = 100

        job_id = _create_ingestion_job(profile_value, delta_flag, normalized_subpath)

        pipeline = UnifiedIngestionPipeline(driver, REPO_PATH, job_id=job_id)
        results = pipeline.run_complete_ingestion(
            reset_graph=reset_graph,
            commit_limit=commit_limit,
            doc_limit=doc_limit,
            code_limit=code_limit,
            derive_relationships=derive_relationships,
            include_embeddings=include_embeddings,
            max_workers=max_workers,
            delta=delta_flag,
            subpath=normalized_subpath,
        )

        if results.get("success"):
            ingestion_state["last_successful_run"] = results
        ingestion_state["progress"] = results
        results["job_id"] = job_id
        return results

    except Exception as e:
        logger.error(f"Unified ingestion failed: {e}")
        job_id = ingestion_state.get("ingestion_job_id")
        if job_id:
            _finalize_job(job_id, 'failed', error=str(e))
        else:
            ingestion_state["is_running"] = False
            ingestion_state["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/dev-graph/ingest/status")
def get_ingestion_status():
    """Get current ingestion status and progress."""
    job_id = ingestion_state.get("ingestion_job_id")
    job = _get_job(job_id)
    return {
        "is_running": ingestion_state["is_running"],
        "current_stage": ingestion_state["current_stage"],
        "start_time": ingestion_state["start_time"],
        "end_time": ingestion_state["end_time"],
        "error": ingestion_state["error"],
        "duration": (ingestion_state["end_time"] or time.time()) - (ingestion_state["start_time"] or 0) if ingestion_state["start_time"] else 0,
        "job_id": job_id,
        "job": job,
        "jobs": list(ingestion_jobs.values()),
    }


@router.get("/api/v1/dev-graph/ingest/status/{job_id}")
def get_ingestion_job_status(job_id: str):
    """Get status for a specific ingestion job."""
    job = _get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}

@router.post("/api/v1/dev-graph/ingest/stop")
def stop_ingestion():
    """Stop current ingestion (if running)."""
    if not ingestion_state.get("is_running"):
        return {"success": False, "message": "No ingestion currently running"}

    ingestion_state["stop_requested"] = True
    job_id = ingestion_state.get("ingestion_job_id")
    job = _get_job(job_id)
    if job and job.get('status') == 'running':
        job['status'] = 'stopping'
        job['updated_at'] = time.time()
    return {"success": True, "message": "Stop requested", "job_id": job_id}

@router.get("/api/v1/dev-graph/ingest/report")
def get_ingestion_report():
    """Get comprehensive ingestion report."""
    job_id = ingestion_state.get("ingestion_job_id")
    job = _get_job(job_id)
    report_data = None
    if job and job.get('result'):
        report_data = job['result']

    if not report_data:
        progress = ingestion_state.get("progress") or {}
        if progress.get("success"):
            report_data = progress
        else:
            report_data = ingestion_state.get("last_successful_run")

    if not report_data:
        return {"success": False, "message": "No successful ingestion data available"}

    return {
        "success": True,
        "report": report_data,
        "job_id": job_id,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }







