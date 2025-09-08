"""Parallel Ingestion Pipeline for Temporal Semantic Dev Graph

Implements worker pipeline with parallel extraction and batched writes for optimal performance.
"""

import logging
import time
import queue
import threading
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from neo4j import Driver
import subprocess
import json

logger = logging.getLogger(__name__)


@dataclass
class CommitOperation:
    """Represents a commit and its associated operations."""
    hash: str
    message: str
    author: str
    email: str
    timestamp: str
    files: List[Dict[str, str]]  # [{"path": str, "change_type": str}]


@dataclass
class ChunkOperation:
    """Represents a chunk and its relationships."""
    id: str
    content: str
    chunk_type: str
    doc_path: str
    mentions: List[str]
    metadata: Dict[str, Any]


class ParallelIngestionPipeline:
    """Worker pipeline for parallel ingestion with batched writes."""
    
    def __init__(self, driver: Driver, repo_path: str, max_workers: int = 8):
        self.driver = driver
        self.repo_path = repo_path
        self.max_workers = max_workers
        self.commit_queue = queue.Queue(maxsize=1000)
        self.chunk_queue = queue.Queue(maxsize=2000)
        self.batch_size = 200
        self.flush_interval = 0.2  # 200ms
        
    def ingest_commits_parallel(self, limit: int = 100) -> Dict[str, int]:
        """Ingest commits using parallel extraction and batched writes."""
        logger.info(f"Starting parallel commit ingestion (limit={limit})")
        start_time = time.time()
        
        # Step 1: Extract commits using single git log command
        logger.info("Extracting commits from git log...")
        commits = self._extract_commits_batched(limit)
        logger.info(f"Extracted {len(commits)} commits in {time.time() - start_time:.2f}s")
        
        if not commits:
            return {"commits_ingested": 0, "files_processed": 0, "duration": 0}
        
        # Step 2: Process commits in parallel batches
        logger.info(f"Processing {len(commits)} commits with {self.max_workers} workers...")
        process_start = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit commit processing tasks
            future_to_commit = {
                executor.submit(self._process_commit, commit): commit 
                for commit in commits
            }
            
            # Collect results as they complete
            processed_commits = []
            for future in as_completed(future_to_commit):
                try:
                    result = future.result()
                    if result:
                        processed_commits.append(result)
                except Exception as e:
                    logger.error(f"Error processing commit: {e}")
        
        logger.info(f"Processed {len(processed_commits)} commits in {time.time() - process_start:.2f}s")
        
        # Step 3: Batch write to database
        logger.info("Writing commits to database in batches...")
        write_start = time.time()
        commits_written = self._batch_write_commits(processed_commits)
        
        total_duration = time.time() - start_time
        logger.info(f"Parallel ingestion completed: {commits_written} commits in {total_duration:.2f}s")
        
        return {
            "commits_ingested": commits_written,
            "files_processed": sum(len(c.files) for c in processed_commits),
            "duration": total_duration
        }
    
    def _extract_commits_batched(self, limit: int) -> List[Dict[str, Any]]:
        """Extract commits using single git log command with name-status."""
        try:
            # Use git log with name-status for efficient parsing
            cmd = [
                "git", "log", 
                "--name-status",
                f"--pretty=format:%H\t%an\t%ae\t%aI\t%s",
                f"-n{limit}"
            ]
            
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Git log failed: {result.stderr}")
                return []
            
            return self._parse_git_log_output(result.stdout)
            
        except Exception as e:
            logger.error(f"Error extracting commits: {e}")
            return []
    
    def _parse_git_log_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse git log output into commit objects."""
        commits = []
        lines = [line.strip() for line in output.split('\n') if line.strip()]
        
        i = 0
        while i < len(lines):
            # Parse commit header
            if '\t' in lines[i] and len(lines[i].split('\t')) >= 5:
                parts = lines[i].split('\t', 4)
                commit_hash, author, email, timestamp, message = parts
                
                # Collect file changes
                files = []
                i += 1
                while i < len(lines) and lines[i] and '\t' in lines[i]:
                    # Parse file change line (status\tpath)
                    file_parts = lines[i].split('\t', 1)
                    if len(file_parts) == 2:
                        change_type, file_path = file_parts
                        files.append({
                            "path": file_path,
                            "change_type": self._normalize_change_type(change_type)
                        })
                    i += 1
                
                commits.append({
                    "hash": commit_hash,
                    "message": message,
                    "author": author,
                    "email": email,
                    "timestamp": timestamp,
                    "files": files
                })
            else:
                i += 1
        
        return commits
    
    def _normalize_change_type(self, status: str) -> str:
        """Normalize git status to change type."""
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
    
    def _process_commit(self, commit_data: Dict[str, Any]) -> Optional[CommitOperation]:
        """Process a single commit (placeholder for future enrichment)."""
        try:
            return CommitOperation(
                hash=commit_data["hash"],
                message=commit_data["message"],
                author=commit_data["author"],
                email=commit_data["email"],
                timestamp=commit_data["timestamp"],
                files=commit_data["files"]
            )
        except Exception as e:
            logger.error(f"Error processing commit {commit_data.get('hash', 'unknown')}: {e}")
            return None
    
    def _batch_write_commits(self, commits: List[CommitOperation]) -> int:
        """Write commits to database using batched UNWIND operations."""
        if not commits:
            return 0
        
        logger.info(f"Writing {len(commits)} commits to database...")
        
        # Prepare data for UNWIND
        commit_data = []
        for commit in commits:
            commit_data.append({
                "hash": commit.hash,
                "message": commit.message,
                "author": commit.author,
                "email": commit.email,
                "timestamp": commit.timestamp,
                "files": commit.files
            })
        
        # Write in batches
        written = 0
        batch_size = min(self.batch_size, len(commits))
        
        for i in range(0, len(commits), batch_size):
            batch = commit_data[i:i + batch_size]
            written += self._write_commit_batch(batch)
        
        return written
    
    def _write_commit_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Write a batch of commits using UNWIND operations."""
        try:
            with self.driver.session() as session:
                # UNWIND template for commits and files
                query = """
                UNWIND $commits AS c
                MERGE (gc:GitCommit {hash: c.hash}) 
                ON CREATE SET 
                    gc.message = c.message,
                    gc.author = c.author,
                    gc.email = c.email,
                    gc.timestamp = c.timestamp,
                    gc.created_at = datetime()
                ON MATCH SET
                    gc.message = c.message,
                    gc.author = c.author,
                    gc.email = c.email,
                    gc.timestamp = c.timestamp,
                    gc.updated_at = datetime()
                
                WITH c, gc
                UNWIND c.files AS f
                MERGE (fl:File {path: f.path})
                MERGE (gc)-[r:TOUCHED]->(fl) 
                SET r.change_type = f.change_type, 
                    r.timestamp = c.timestamp
                """
                
                result = session.run(query, commits=batch)
                result.consume()  # Execute the query
                
                logger.info(f"Wrote batch of {len(batch)} commits")
                return len(batch)
                
        except Exception as e:
            logger.error(f"Error writing commit batch: {e}")
            return 0
    
    def ingest_chunks_parallel(self, doc_limit: int = 100, code_limit: int = 500) -> Dict[str, int]:
        """Ingest chunks using parallel processing and batched writes."""
        logger.info(f"Starting parallel chunk ingestion (doc_limit={doc_limit}, code_limit={code_limit})")
        start_time = time.time()
        
        # Step 1: Discover files
        logger.info("Discovering files to chunk...")
        files = self._discover_files(doc_limit, code_limit)
        logger.info(f"Found {len(files)} files to process")
        
        if not files:
            return {"chunks_created": 0, "files_processed": 0, "duration": 0}
        
        # Step 2: Process files in parallel
        logger.info(f"Processing {len(files)} files with {self.max_workers} workers...")
        process_start = time.time()
        
        all_chunks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, file_path, file_type): file_path 
                for file_path, file_type in files
            }
            
            for future in as_completed(future_to_file):
                try:
                    chunks = future.result()
                    if chunks:
                        all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Error processing file: {e}")
        
        logger.info(f"Generated {len(all_chunks)} chunks in {time.time() - process_start:.2f}s")
        
        # Step 3: Batch write chunks
        logger.info("Writing chunks to database...")
        write_start = time.time()
        chunks_written = self._batch_write_chunks(all_chunks)
        
        total_duration = time.time() - start_time
        logger.info(f"Parallel chunk ingestion completed: {chunks_written} chunks in {total_duration:.2f}s")
        
        return {
            "chunks_created": chunks_written,
            "files_processed": len(files),
            "duration": total_duration
        }
    
    def _discover_files(self, doc_limit: int, code_limit: int) -> List[Tuple[str, str]]:
        """Discover files to process, split by type."""
        files = []
        
        # Find documentation files
        doc_patterns = ['*.md', '*.rst', '*.txt']
        for pattern in doc_patterns:
            try:
                result = subprocess.run(
                    ['git', 'ls-files', pattern],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    doc_files = [f for f in result.stdout.strip().split('\n') if f][:doc_limit]
                    files.extend([(f, 'documentation') for f in doc_files])
            except Exception as e:
                logger.error(f"Error finding {pattern} files: {e}")
        
        # Find code files
        code_patterns = ['*.py', '*.js', '*.ts', '*.tsx', '*.jsx']
        for pattern in code_patterns:
            try:
                result = subprocess.run(
                    ['git', 'ls-files', pattern],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    code_files = [f for f in result.stdout.strip().split('\n') if f][:code_limit]
                    files.extend([(f, 'code') for f in code_files])
            except Exception as e:
                logger.error(f"Error finding {pattern} files: {e}")
        
        return files
    
    def _process_file(self, file_path: str, file_type: str) -> List[ChunkOperation]:
        """Process a single file and return chunks."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Simple chunking based on file type
            if file_type == 'documentation':
                return self._chunk_documentation(file_path, content)
            else:
                return self._chunk_code(file_path, content)
                
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []
    
    def _chunk_documentation(self, file_path: str, content: str) -> List[ChunkOperation]:
        """Chunk documentation files by sections."""
        chunks = []
        sections = content.split('\n\n')
        
        for i, section in enumerate(sections):
            if section.strip():
                chunk_id = f"{file_path}:doc:{i}"
                chunks.append(ChunkOperation(
                    id=chunk_id,
                    content=section.strip(),
                    chunk_type='documentation',
                    doc_path=file_path,
                    mentions=[],  # TODO: Extract requirement mentions
                    metadata={}  # Simplified metadata for now
                ))
        
        return chunks
    
    def _chunk_code(self, file_path: str, content: str) -> List[ChunkOperation]:
        """Chunk code files by functions/classes."""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        chunk_index = 0
        
        for line in lines:
            # Simple heuristic: start new chunk on function/class definitions
            if (line.strip().startswith('def ') or 
                line.strip().startswith('class ') or
                line.strip().startswith('function ') or
                line.strip().startswith('export ')):
                
                if current_chunk:
                    chunk_id = f"{file_path}:code:{chunk_index}"
                    chunks.append(ChunkOperation(
                        id=chunk_id,
                        content='\n'.join(current_chunk),
                        chunk_type='code',
                        doc_path=file_path,
                        mentions=[],  # TODO: Extract requirement mentions
                        metadata={}  # Simplified metadata for now
                    ))
                    chunk_index += 1
                    current_chunk = []
            
            current_chunk.append(line)
        
        # Add final chunk
        if current_chunk:
            chunk_id = f"{file_path}:code:{chunk_index}"
            chunks.append(ChunkOperation(
                id=chunk_id,
                content='\n'.join(current_chunk),
                chunk_type='code',
                doc_path=file_path,
                mentions=[],
                metadata={}  # Simplified metadata for now
            ))
        
        return chunks
    
    def _batch_write_chunks(self, chunks: List[ChunkOperation]) -> int:
        """Write chunks to database using batched UNWIND operations."""
        if not chunks:
            return 0
        
        logger.info(f"Writing {len(chunks)} chunks to database...")
        
        # Prepare data for UNWIND
        chunk_data = []
        for chunk in chunks:
            chunk_data.append({
                "id": chunk.id,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type,
                "doc_path": chunk.doc_path,
                "mentions": chunk.mentions,
                "metadata": chunk.metadata
            })
        
        # Write in batches
        written = 0
        batch_size = min(self.batch_size, len(chunks))
        
        for i in range(0, len(chunks), batch_size):
            batch = chunk_data[i:i + batch_size]
            written += self._write_chunk_batch(batch)
        
        return written
    
    def _write_chunk_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Write a batch of chunks using UNWIND operations."""
        try:
            with self.driver.session() as session:
                # UNWIND template for chunks
                query = """
                UNWIND $chunks AS ch
                MERGE (c:Chunk {id: ch.id}) 
                ON CREATE SET 
                    c.content = ch.content,
                    c.chunk_type = ch.chunk_type,
                    c.doc_path = ch.doc_path,
                    c.created_at = datetime()
                ON MATCH SET
                    c.content = ch.content,
                    c.chunk_type = ch.chunk_type,
                    c.doc_path = ch.doc_path,
                    c.updated_at = datetime()
                
                WITH ch, c
                MATCH (d:Document {path: ch.doc_path})
                MERGE (d)-[:CONTAINS_CHUNK]->(c)
                
                WITH ch, c
                UNWIND ch.mentions AS rid
                MERGE (r:Requirement {id: rid})
                MERGE (c)-[:MENTIONS]->(r)
                """
                
                result = session.run(query, chunks=batch)
                result.consume()  # Execute the query
                
                logger.info(f"Wrote batch of {len(batch)} chunks")
                return len(batch)
                
        except Exception as e:
            logger.error(f"Error writing chunk batch: {e}")
            return 0
