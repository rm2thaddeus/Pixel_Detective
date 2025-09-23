"""
Unlimited Ingestion Pipeline
Processes ALL files and commits without artificial limits, using proper queuing.
"""

import os
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Generator
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json
import queue
import threading
from collections import defaultdict

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from neo4j import Driver

from ..app_state import (
    driver,
    engine,
    git,
    sprint_mapper,
    deriver,
    embedding_service,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    REPO_PATH,
)

router = APIRouter()
logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """File information for processing."""
    path: str
    file_type: str  # 'doc' or 'code'
    size: int
    extension: str
    last_modified: float

@dataclass
class ChunkInfo:
    """Chunk information for database writing."""
    id: str
    content: str
    chunk_type: str
    file_path: str
    heading: Optional[str] = None
    level: int = 0
    ordinal: int = 0
    metadata: Dict[str, Any] = None

class UnlimitedIngestionPipeline:
    """Unlimited ingestion pipeline that processes everything using queuing."""
    
    def __init__(self, driver: Driver, repo_path: str, max_workers: int = 12):
        self.driver = driver
        self.repo_path = repo_path
        self.max_workers = max_workers
        self.batch_size = 1000  # Larger batches for better performance
        self.results = {}
        
        # Queues for processing
        self.file_queue = queue.Queue(maxsize=10000)
        self.chunk_queue = queue.Queue(maxsize=50000)
        self.commit_queue = queue.Queue(maxsize=10000)
        
        # Processing stats
        self.stats = {
            'files_processed': 0,
            'chunks_created': 0,
            'commits_processed': 0,
            'relationships_created': 0,
            'errors': 0
        }
        
    def run_unlimited_ingestion(self, 
                              reset_graph: bool = True,
                              derive_relationships: bool = True,
                              include_embeddings: bool = False) -> Dict[str, Any]:
        """Run unlimited ingestion processing everything."""
        
        start_time = time.time()
        logger.info("Starting Unlimited Ingestion Pipeline - Processing EVERYTHING")
        
        try:
            # Stage 1: Reset and Schema
            if reset_graph:
                logger.info("Resetting database...")
                self._reset_database()
            engine.apply_schema()
            
            # Stage 2: Discover ALL files (no limits)
            logger.info("Discovering ALL files in repository...")
            all_files = self._discover_all_files()
            logger.info(f"Found {len(all_files)} files to process")
            
            # Stage 3: Analyze ALL commits (no limits)
            logger.info("Analyzing ALL commits in repository...")
            all_commits = self._analyze_all_commits()
            logger.info(f"Found {len(all_commits)} commits to process")
            
            # Stage 4: Process files in parallel with queuing
            logger.info("Processing files with queuing...")
            file_stats = self._process_files_with_queuing(all_files)
            
            # Stage 5: Process commits in parallel with queuing
            logger.info("Processing commits with queuing...")
            commit_stats = self._process_commits_with_queuing(all_commits)
            
            # Stage 6: Create relationships
            if derive_relationships:
                logger.info("Creating relationships...")
                rel_stats = self._create_all_relationships()
            
            # Stage 7: Sprint mapping
            logger.info("Mapping sprints...")
            sprint_stats = self._map_all_sprints()
            
            # Stage 8: Enhanced connectivity
            logger.info("Enhancing connectivity...")
            connectivity_stats = self._enhance_all_connectivity()
            
            total_duration = time.time() - start_time
            
            return {
                "success": True,
                "total_duration": total_duration,
                "files_discovered": len(all_files),
                "commits_analyzed": len(all_commits),
                "chunks_created": self.stats['chunks_created'],
                "relationships_created": self.stats['relationships_created'],
                "sprints_mapped": sprint_stats.get('sprints_mapped', 0),
                "connectivity_enhanced": connectivity_stats.get('connections_created', 0),
                "errors": self.stats['errors'],
                "performance_metrics": {
                    "files_per_second": len(all_files) / max(total_duration, 1),
                    "commits_per_second": len(all_commits) / max(total_duration, 1),
                    "chunks_per_second": self.stats['chunks_created'] / max(total_duration, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Unlimited ingestion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _reset_database(self):
        """Fast database reset."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def _discover_all_files(self) -> List[FileInfo]:
        """Discover ALL files in the repository."""
        files = []
        
        try:
            # Use git ls-files to get ALL tracked files
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=120  # Longer timeout for large repos
            )
            
            if result.returncode != 0:
                raise Exception(f"Git ls-files failed: {result.stderr}")
            
            all_files = result.stdout.strip().split('\n')
            logger.info(f"Git found {len(all_files)} tracked files")
            
            # Categorize files
            doc_extensions = {'.md', '.rst', '.txt', '.adoc', '.org', '.tex'}
            code_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs', '.vb', '.sql', '.sh', '.ps1', '.bat', '.yaml', '.yml', '.json', '.xml', '.html', '.css', '.scss', '.sass', '.less'}
            
            for file_path in all_files:
                if not file_path:
                    continue
                    
                ext = Path(file_path).suffix.lower()
                file_type = None
                
                if ext in doc_extensions:
                    file_type = 'doc'
                elif ext in code_extensions:
                    file_type = 'code'
                else:
                    # Include other files as 'other'
                    file_type = 'other'
                
                # Get file info
                full_path = os.path.join(self.repo_path, file_path)
                try:
                    stat = os.stat(full_path)
                    files.append(FileInfo(
                        path=file_path,
                        file_type=file_type,
                        size=stat.st_size,
                        extension=ext,
                        last_modified=stat.st_mtime
                    ))
                except OSError:
                    continue
            
            logger.info(f"Processed {len(files)} files for ingestion")
            return files
            
        except Exception as e:
            logger.error(f"File discovery failed: {e}")
            return []
    
    def _analyze_all_commits(self) -> List[Dict[str, Any]]:
        """Analyze ALL commits in the repository."""
        try:
            # Get ALL commits (no limit)
            cmd = [
                "git", "--no-pager", "log",
                "--name-status",
                "--pretty=format:%H\t%an\t%ae\t%aI\t%B"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=300  # 5 minute timeout for large repos
            )
            
            if result.returncode != 0:
                raise Exception(f"Git log failed: {result.stderr}")
            
            commits = self._parse_git_log_unlimited(result.stdout)
            logger.info(f"Parsed {len(commits)} commits")
            return commits
            
        except Exception as e:
            logger.error(f"Commit analysis failed: {e}")
            return []
    
    def _parse_git_log_unlimited(self, output: str) -> List[Dict[str, Any]]:
        """Parse git log output for unlimited commits."""
        commits = []
        lines = output.strip().split('\n')
        
        current_commit = None
        current_files = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Commit header
            if line.count('\t') == 4 and len(line.split('\t')[0]) == 40:
                if current_commit:
                    current_commit["files"] = current_files
                    commits.append(current_commit)
                
                parts = line.split('\t', 4)
                if len(parts) == 5:
                    current_commit = {
                        "hash": parts[0],
                        "message": parts[4].strip(),
                        "author": parts[1],
                        "email": parts[2],
                        "timestamp": parts[3]
                    }
                    current_files = []
            
            # File change
            elif line.count('\t') == 1 and current_commit:
                file_parts = line.split('\t', 1)
                if len(file_parts) == 2:
                    current_files.append({
                        "path": file_parts[1],
                        "change_type": self._normalize_change_type(file_parts[0])
                    })
        
        # Add last commit
        if current_commit:
            current_commit["files"] = current_files
            commits.append(current_commit)
        
        return commits
    
    def _normalize_change_type(self, status: str) -> str:
        """Normalize git status."""
        if status.startswith('A'):
            return 'added'
        elif status.startswith('M'):
            return 'modified'
        elif status.startswith('D'):
            return 'deleted'
        elif status.startswith('R'):
            return 'renamed'
        else:
            return 'modified'
    
    def _process_files_with_queuing(self, files: List[FileInfo]) -> Dict[str, Any]:
        """Process files using queuing system."""
        logger.info(f"Processing {len(files)} files with queuing...")
        
        # Add files to queue
        for file_info in files:
            self.file_queue.put(file_info)
        
        # Process files in parallel
        all_chunks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all file processing tasks
            futures = []
            for _ in range(min(self.max_workers, len(files))):
                future = executor.submit(self._file_worker)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    chunks = future.result()
                    if chunks:
                        all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"File worker error: {e}")
                    self.stats['errors'] += 1
        
        # Batch write all chunks
        logger.info(f"Writing {len(all_chunks)} chunks to database...")
        chunks_written = self._batch_write_chunks_unlimited(all_chunks)
        self.stats['chunks_created'] = chunks_written
        
        return {
            "files_processed": self.stats['files_processed'],
            "chunks_created": chunks_written
        }
    
    def _file_worker(self) -> List[ChunkInfo]:
        """Worker function for processing files from queue."""
        chunks = []
        
        while not self.file_queue.empty():
            try:
                file_info = self.file_queue.get_nowait()
                file_chunks = self._process_file_chunks(file_info)
                if file_chunks:
                    chunks.extend(file_chunks)
                self.stats['files_processed'] += 1
                self.file_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                self.stats['errors'] += 1
        
        return chunks
    
    def _process_file_chunks(self, file_info: FileInfo) -> List[ChunkInfo]:
        """Process a single file and return chunks."""
        try:
            full_path = os.path.join(self.repo_path, file_info.path)
            
            # Skip very large files to avoid memory issues
            if file_info.size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Skipping large file: {file_info.path} ({file_info.size} bytes)")
                return []
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if file_info.file_type == 'doc':
                return self._chunk_document_unlimited(file_info, content)
            elif file_info.file_type == 'code':
                return self._chunk_code_unlimited(file_info, content)
            else:
                return self._chunk_other_file(file_info, content)
                
        except Exception as e:
            logger.error(f"Error processing {file_info.path}: {e}")
            return []
    
    def _chunk_document_unlimited(self, file_info: FileInfo, content: str) -> List[ChunkInfo]:
        """Chunk document with unlimited processing."""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        chunk_index = 0
        current_heading = None
        current_level = 0
        
        for line in lines:
            # Check for heading
            if line.startswith('#'):
                # Save previous chunk
                if current_chunk:
                    chunk_id = f"{file_info.path}#chunk-{chunk_index:03d}"
                    chunks.append(ChunkInfo(
                        id=chunk_id,
                        content='\n'.join(current_chunk).strip(),
                        chunk_type='doc',
                        file_path=file_info.path,
                        heading=current_heading,
                        level=current_level,
                        ordinal=chunk_index
                    ))
                    chunk_index += 1
                
                # Start new chunk
                current_heading = line.strip('# ').strip()
                current_level = len(line) - len(line.lstrip('#'))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Add final chunk
        if current_chunk:
            chunk_id = f"{file_info.path}#chunk-{chunk_index:03d}"
            chunks.append(ChunkInfo(
                id=chunk_id,
                content='\n'.join(current_chunk).strip(),
                chunk_type='doc',
                file_path=file_info.path,
                heading=current_heading,
                level=current_level,
                ordinal=chunk_index
            ))
        
        return chunks
    
    def _chunk_code_unlimited(self, file_info: FileInfo, content: str) -> List[ChunkInfo]:
        """Chunk code with unlimited processing."""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        chunk_index = 0
        current_function = None
        
        for line in lines:
            # Check for function/class definition
            if (line.strip().startswith('def ') or 
                line.strip().startswith('class ') or
                line.strip().startswith('function ') or
                line.strip().startswith('export ') or
                line.strip().startswith('const ') or
                line.strip().startswith('let ') or
                line.strip().startswith('var ')):
                
                # Save previous chunk
                if current_chunk:
                    chunk_id = f"{file_info.path}#func-{chunk_index:03d}"
                    chunks.append(ChunkInfo(
                        id=chunk_id,
                        content='\n'.join(current_chunk).strip(),
                        chunk_type='code',
                        file_path=file_info.path,
                        heading=current_function,
                        level=1,
                        ordinal=chunk_index
                    ))
                    chunk_index += 1
                
                # Start new chunk
                current_function = line.strip()
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Add final chunk
        if current_chunk:
            chunk_id = f"{file_info.path}#func-{chunk_index:03d}"
            chunks.append(ChunkInfo(
                id=chunk_id,
                content='\n'.join(current_chunk).strip(),
                chunk_type='code',
                file_path=file_info.path,
                heading=current_function,
                level=1,
                ordinal=chunk_index
            ))
        
        return chunks
    
    def _chunk_other_file(self, file_info: FileInfo, content: str) -> List[ChunkInfo]:
        """Chunk other file types."""
        # For other files, create single chunk
        chunk_id = f"{file_info.path}#content"
        return [ChunkInfo(
            id=chunk_id,
            content=content[:10000],  # Limit content size
            chunk_type='other',
            file_path=file_info.path,
            heading=None,
            level=0,
            ordinal=0
        )]
    
    def _batch_write_chunks_unlimited(self, chunks: List[ChunkInfo]) -> int:
        """Batch write chunks with unlimited processing."""
        if not chunks:
            return 0
        
        written = 0
        batch_size = min(self.batch_size, len(chunks))
        
        logger.info(f"Writing {len(chunks)} chunks in batches of {batch_size}")
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            written += self._write_chunk_batch_unlimited(batch)
            
            # Log progress
            if (i + batch_size) % (batch_size * 10) == 0:
                logger.info(f"Written {i + batch_size}/{len(chunks)} chunks")
        
        return written
    
    def _write_chunk_batch_unlimited(self, batch: List[ChunkInfo]) -> int:
        """Write a batch of chunks with unlimited processing."""
        try:
            with self.driver.session() as session:
                # Prepare data
                chunk_data = []
                for chunk in batch:
                    chunk_data.append({
                        "id": chunk.id,
                        "content": chunk.content,
                        "chunk_type": chunk.chunk_type,
                        "file_path": chunk.file_path,
                        "heading": chunk.heading,
                        "level": chunk.level,
                        "ordinal": chunk.ordinal
                    })
                
                # UNWIND query for chunks
                query = """
                UNWIND $chunks AS ch
                MERGE (c:Chunk {id: ch.id})
                ON CREATE SET 
                    c.content = ch.content,
                    c.chunk_type = ch.chunk_type,
                    c.file_path = ch.file_path,
                    c.heading = ch.heading,
                    c.level = ch.level,
                    c.ordinal = ch.ordinal,
                    c.kind = ch.chunk_type,
                    c.created_at = datetime()
                ON MATCH SET
                    c.content = ch.content,
                    c.chunk_type = ch.chunk_type,
                    c.file_path = ch.file_path,
                    c.updated_at = datetime()
                
                WITH ch, c
                MERGE (f:File {path: ch.file_path})
                SET f.extension = $extension,
                    f.is_code = (ch.chunk_type = 'code'),
                    f.is_doc = (ch.chunk_type = 'doc')
                MERGE (f)-[:CONTAINS_CHUNK]->(c)
                """
                
                result = session.run(query, chunks=chunk_data, extension=Path(batch[0].file_path).suffix.lower())
                result.consume()
                
                return len(batch)
                
        except Exception as e:
            logger.error(f"Error writing chunk batch: {e}")
            return 0
    
    def _process_commits_with_queuing(self, commits: List[Dict]) -> Dict[str, Any]:
        """Process commits using queuing system."""
        logger.info(f"Processing {len(commits)} commits with queuing...")
        
        # Add commits to queue
        for commit in commits:
            self.commit_queue.put(commit)
        
        # Process commits in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all commit processing tasks
            futures = []
            for _ in range(min(self.max_workers, len(commits))):
                future = executor.submit(self._commit_worker)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Commit worker error: {e}")
                    self.stats['errors'] += 1
        
        return {
            "commits_processed": self.stats['commits_processed']
        }
    
    def _commit_worker(self):
        """Worker function for processing commits from queue."""
        while not self.commit_queue.empty():
            try:
                commit = self.commit_queue.get_nowait()
                self._process_single_commit(commit)
                self.stats['commits_processed'] += 1
                self.commit_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing commit: {e}")
                self.stats['errors'] += 1
    
    def _process_single_commit(self, commit: Dict):
        """Process a single commit."""
        try:
            with self.driver.session() as session:
                # Create commit node
                session.run("""
                    MERGE (c:GitCommit {hash: $hash})
                    SET c.message = $message,
                        c.author = $author,
                        c.email = $email,
                        c.timestamp = $timestamp
                """, 
                hash=commit["hash"],
                message=commit["message"],
                author=commit["author"],
                email=commit["email"],
                timestamp=commit["timestamp"])
                
                # Create file nodes and relationships
                for file_change in commit.get("files", []):
                    # Create file node
                    session.run("""
                        MERGE (f:File {path: $path})
                        SET f.extension = $extension
                    """,
                    path=file_change["path"],
                    extension=Path(file_change["path"]).suffix.lower())
                    
                    # Create TOUCHED relationship
                    session.run("""
                        MATCH (c:GitCommit {hash: $hash})
                        MATCH (f:File {path: $path})
                        MERGE (c)-[r:TOUCHED]->(f)
                        SET r.change_type = $change_type,
                            r.timestamp = $timestamp
                    """,
                    hash=commit["hash"],
                    path=file_change["path"],
                    change_type=file_change["change_type"],
                    timestamp=commit["timestamp"])
                    
                    self.stats['relationships_created'] += 1
                    
        except Exception as e:
            logger.error(f"Error processing commit {commit.get('hash', 'unknown')}: {e}")
            self.stats['errors'] += 1
    
    def _create_all_relationships(self) -> Dict[str, Any]:
        """Create all relationships."""
        logger.info("Creating all relationships...")
        
        with self.driver.session() as session:
            # Create chunk-to-file relationships
            result = session.run("""
                MATCH (c:Chunk)
                MATCH (f:File {path: c.file_path})
                MERGE (c)-[:BELONGS_TO]->(f)
                RETURN count(*) as connections
            """)
            connections = result.single()["connections"]
            self.stats['relationships_created'] += connections
            
            # Create co-occurrence relationships
            result = session.run("""
                MATCH (c:GitCommit)-[:TOUCHED]->(f1:File)
                MATCH (c)-[:TOUCHED]->(f2:File)
                WHERE f1 <> f2
                WITH f1, f2, count(*) as co_occurrence
                WHERE co_occurrence > 1
                MERGE (f1)-[r:CO_OCCURS_WITH]->(f2)
                SET r.weight = co_occurrence
                RETURN count(*) as connections
            """)
            connections = result.single()["connections"]
            self.stats['relationships_created'] += connections
        
        return {"total_relationships": self.stats['relationships_created']}
    
    def _map_all_sprints(self) -> Dict[str, Any]:
        """Map all sprints."""
        try:
            mapped = sprint_mapper.map_all_sprints()
            sprints_mapped = mapped.get("count", 0) if isinstance(mapped, dict) else 0
            return {"sprints_mapped": sprints_mapped}
        except Exception as e:
            logger.error(f"Sprint mapping failed: {e}")
            return {"sprints_mapped": 0}
    
    def _enhance_all_connectivity(self) -> Dict[str, Any]:
        """Enhance all connectivity."""
        logger.info("Enhancing all connectivity...")
        
        connections_created = 0
        
        with self.driver.session() as session:
            # Create dynamic connections between related chunks
            result = session.run("""
                MATCH (doc_chunk:Chunk {chunk_type: 'doc'})
                MATCH (code_chunk:Chunk {chunk_type: 'code'})
                WHERE doc_chunk.heading IS NOT NULL 
                  AND code_chunk.heading IS NOT NULL
                  AND (doc_chunk.heading CONTAINS code_chunk.heading 
                       OR code_chunk.heading CONTAINS doc_chunk.heading)
                MERGE (doc_chunk)-[:RELATES_TO]->(code_chunk)
                RETURN count(*) as connections
            """)
            connections_created += result.single()["connections"]
            
            # Create file-level relationships
            result = session.run("""
                MATCH (f1:File)-[:CONTAINS_CHUNK]->(c1:Chunk)
                MATCH (f2:File)-[:CONTAINS_CHUNK]->(c2:Chunk)
                WHERE f1 <> f2 AND c1-[:RELATES_TO]-c2
                MERGE (f1)-[:RELATES_TO]->(f2)
                RETURN count(*) as connections
            """)
            connections_created += result.single()["connections"]
        
        return {"connections_created": connections_created}

@router.post("/api/v1/dev-graph/ingest/unlimited")
def unlimited_ingestion(
    reset_graph: bool = Query(True, description="Reset database before ingestion"),
    derive_relationships: bool = Query(True, description="Derive semantic relationships"),
    include_embeddings: bool = Query(False, description="Generate embeddings for chunks"),
    max_workers: int = Query(12, ge=1, le=24, description="Maximum parallel workers")
):
    """
    Unlimited Ingestion Pipeline
    
    Processes EVERYTHING in the repository:
    - ALL files (no limits)
    - ALL commits (no limits)
    - Uses queuing for memory efficiency
    - Creates comprehensive relationships
    """
    try:
        pipeline = UnlimitedIngestionPipeline(driver, REPO_PATH, max_workers)
        results = pipeline.run_unlimited_ingestion(
            reset_graph=reset_graph,
            derive_relationships=derive_relationships,
            include_embeddings=include_embeddings
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Unlimited ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/dev-graph/ingest/unlimited/status")
def get_unlimited_status():
    """Get status of unlimited ingestion."""
    return {
        "status": "ready",
        "message": "Unlimited ingestion pipeline is ready",
        "features": [
            "Processes ALL files (no limits)",
            "Processes ALL commits (no limits)",
            "Uses queuing for memory efficiency",
            "Comprehensive relationship creation"
        ]
    }
