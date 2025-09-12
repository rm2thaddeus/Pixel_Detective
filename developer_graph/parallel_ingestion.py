"""Parallel Ingestion Pipeline for Temporal Semantic Dev Graph

Implements worker pipeline with parallel extraction and batched writes for optimal performance.
"""

import logging
import time
import queue
import threading
import os
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

    def _normalize_repo_relative_path(self, file_path: str) -> str:
        """Return repo-relative POSIX path for a given (possibly relative) path."""
        try:
            root = os.path.abspath(self.repo_path)
            abs_path = file_path
            if not os.path.isabs(abs_path):
                abs_path = os.path.abspath(os.path.join(root, file_path))
            rel = os.path.relpath(abs_path, root)
            return rel.replace('\\', '/')
        except Exception:
            return file_path.replace('\\', '/')
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
                "git", "--no-pager", "log",  # Disable pager correctly
                "--name-status",
                f"--pretty=format:%H\t%an\t%ae\t%aI\t%B",  # Use %B for full commit message
                f"-n{limit}"
            ]
            
            logger.info(f"Running git log command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                capture_output=True, 
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=60,  # Increased timeout
                env={**os.environ, 'GIT_PAGER': 'cat'}  # Disable pager
            )
            
            if result.returncode != 0:
                logger.error(f"Git log failed with return code {result.returncode}: {result.stderr}")
                return []
            
            logger.info(f"Git log output length: {len(result.stdout)} characters")
            return self._parse_git_log_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            logger.error(f"Git log command timed out after 60 seconds")
            return []
        except Exception as e:
            logger.error(f"Error extracting commits: {e}")
            return []
    
    def _parse_git_log_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse git log output into commit objects."""
        commits = []
        lines = output.strip().split('\n')
        
        current_commit = None
        current_files = []
        in_commit_message = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a commit header (has 4 tabs and starts with commit hash)
            if line.count('\t') == 4 and len(line.split('\t')[0]) == 40:
                # Save previous commit if exists
                if current_commit:
                    current_commit["files"] = current_files
                    commits.append(current_commit)
                
                # Start new commit
                parts = line.split('\t', 4)
                if len(parts) == 5:
                    commit_hash, author, email, timestamp, message = parts
                    current_commit = {
                        "hash": commit_hash,
                        "message": message.strip(),
                        "author": author,
                        "email": email,
                        "timestamp": timestamp
                    }
                    current_files = []
                    in_commit_message = True
            
            # Check if this is a file change (has 1 tab and we're not in commit message)
            elif line.count('\t') == 1 and current_commit and not in_commit_message:
                file_parts = line.split('\t', 1)
                if len(file_parts) == 2:
                    change_type, file_path = file_parts
                    current_files.append({
                        "path": file_path,
                        "change_type": self._normalize_change_type(change_type)
                    })
            
            # If we're in a commit message and hit a file change, switch to file parsing
            elif line.count('\t') == 1 and current_commit and in_commit_message:
                in_commit_message = False
                file_parts = line.split('\t', 1)
                if len(file_parts) == 2:
                    change_type, file_path = file_parts
                    current_files.append({
                        "path": file_path,
                        "change_type": self._normalize_change_type(change_type)
                    })
        
        # Don't forget the last commit
        if current_commit:
            current_commit["files"] = current_files
            commits.append(current_commit)
        
        logger.info(f"Parsed {len(commits)} commits from git log output")
        if len(commits) == 0:
            logger.warning(f"No commits parsed from {len(lines)} lines")
            if lines:
                logger.debug(f"First line: {lines[0][:200]}...")
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
        """Process a single commit with LOC calculation."""
        try:
            # Calculate LOC for each file
            enriched_files = []
            for file_info in commit_data["files"]:
                enriched_file = file_info.copy()
                
                # Calculate LOC data
                loc_data = self._calculate_file_loc(commit_data["hash"], file_info["path"], file_info["change_type"])
                enriched_file.update(loc_data)
                
                enriched_files.append(enriched_file)
            
            return CommitOperation(
                hash=commit_data["hash"],
                message=commit_data["message"],
                author=commit_data["author"],
                email=commit_data["email"],
                timestamp=commit_data["timestamp"],
                files=enriched_files
            )
        except Exception as e:
            logger.error(f"Error processing commit {commit_data.get('hash', 'unknown')}: {e}")
            return None
    
    def _calculate_file_loc(self, commit_hash: str, file_path: str, change_type: str) -> Dict[str, Any]:
        """Calculate LOC data for a file at a specific commit."""
        try:
            # For deleted files, return 0 LOC
            if change_type == 'D':
                return {
                    "lines_after": 0,
                    "additions": 0,
                    "deletions": 0
                }
            
            # Get file content at this commit
            content = self._get_file_content_at_commit(commit_hash, file_path)
            if not content:
                return {
                    "lines_after": 0,
                    "additions": 0,
                    "deletions": 0
                }
            
            # Calculate lines of code
            lines_after = content.count('\n') + (0 if content.endswith('\n') else 1)
            
            # For now, we'll set additions and deletions to 0 since we don't have diff data
            # In a more sophisticated implementation, we could calculate these from git diff
            return {
                "lines_after": lines_after,
                "additions": 0,  # TODO: Calculate from git diff
                "deletions": 0   # TODO: Calculate from git diff
            }
            
        except Exception as e:
            logger.error(f"Error calculating LOC for {file_path} at {commit_hash}: {e}")
            return {
                "lines_after": 0,
                "additions": 0,
                "deletions": 0
            }
    
    def _get_file_content_at_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """Get file content at a specific commit using git show."""
        try:
            # Ensure POSIX-style path for git
            posix_path = file_path.replace('\\', '/')
            
            # Use git show to get file content at specific commit
            cmd = ["git", "show", f"{commit_hash}:{posix_path}"]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.debug(f"Could not get content for {file_path} at {commit_hash}: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting content for {file_path} at {commit_hash}")
            return None
        except Exception as e:
            logger.error(f"Error getting content for {file_path} at {commit_hash}: {e}")
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
                # UNWIND template for commits and files with LOC calculation
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
                    r.timestamp = c.timestamp,
                    r.lines_after = f.lines_after,
                    r.additions = f.additions,
                    r.deletions = f.deletions
                SET fl.loc = CASE f.change_type WHEN 'D' THEN 0 ELSE f.lines_after END
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
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
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
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
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
                norm = self._normalize_repo_relative_path(file_path)
                return self._chunk_documentation(norm, content)
            else:
                norm = self._normalize_repo_relative_path(file_path)
                return self._chunk_code(norm, content)
                
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
