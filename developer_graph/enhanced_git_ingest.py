#!/usr/bin/env python3
"""Enhanced Git-based Developer Graph Ingestion.

This version properly analyzes git commits to:
- Extract code files and their changes
- Create "Touches" relationships between planning and implementation
- Track chunk-level changes in git commits
- Link requirements to actual code changes
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Iterable, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

from git import Repo, Commit
from neo4j import GraphDatabase

# Patterns for detecting requirements and references
REQ_PATTERN = re.compile(r"\b(?:FR|NFR)-\d{2}-\d{2}\b")
SPRINT_REF_PATTERN = re.compile(r"\b(?:sprint|Sprint)-(\d+)\b")
REQ_REF_PATTERN = re.compile(r"\b(?:FR|NFR)-(\d{2})-(\d{2})\b")

# File extensions that indicate code files
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.clj', '.hs', '.ml', '.fs', '.vb', '.sql', '.sh', '.ps1', '.bat', '.yaml', '.yml', '.json', '.xml', '.html', '.css', '.scss', '.sass', '.less'}

# File extensions that indicate documentation/planning
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc', '.org', '.tex', '.doc', '.docx', '.pdf'}

@dataclass
class FileChange:
    """Represents a file change in a commit."""
    path: str
    change_type: str  # 'A' (added), 'M' (modified), 'D' (deleted), 'R' (renamed)
    old_path: Optional[str] = None
    additions: int = 0
    deletions: int = 0

@dataclass
class CommitAnalysis:
    """Analysis of a commit with extracted relationships."""
    commit: Commit
    file_changes: List[FileChange]
    code_files: List[str]
    doc_files: List[str]
    requirements_mentioned: Set[str]
    sprints_mentioned: Set[str]
    message_requirements: Set[str]
    message_sprints: Set[str]

class EnhancedGitIngester:
    """Enhanced git-based ingestion that creates proper planning-to-implementation links."""

    def __init__(self, repo_path: str, neo4j_uri: str, user: str, password: str):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        self.requirement_map = {}
        self.sprint_map = {}

    def ingest(self):
        """Main ingestion process with enhanced git analysis."""
        print("Starting enhanced git-based ingestion...")

        # First, run the basic enhanced ingest to get sprints, requirements, documents, chunks
        self._run_basic_ingest()
        
        # Then analyze git commits to create Touches relationships
        commits = self._analyze_git_commits()
        
        print(f"Analyzed {len(commits)} commits")
        
        with self.driver.session() as session:
            # Create Touches relationships between commits and files
            for commit_analysis in commits:
                session.execute_write(self._create_commit_touches, commit_analysis)
                
                # Create relationships between requirements and code files
                session.execute_write(self._create_requirement_touches, commit_analysis)
                
                # Create relationships between sprints and code files
                session.execute_write(self._create_sprint_touches, commit_analysis)
                
                # Create chunk-level change tracking
                session.execute_write(self._create_chunk_changes, commit_analysis)
        
        print("Enhanced git-based ingestion completed!")

    def _run_basic_ingest(self):
        """Run the basic enhanced ingest first."""
        from .enhanced_ingest import EnhancedDevGraphIngester
        
        # Get connection details from environment
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "password")
        
        basic_ingester = EnhancedDevGraphIngester(
            self.repo_path, 
            uri, 
            user, 
            password
        )
        basic_ingester.ingest()

    def _analyze_git_commits(self, limit: int = 1000) -> List[CommitAnalysis]:
        """Analyze git commits to extract file changes and relationships."""
        commits = []
        
        # Get recent commits
        for commit in self.repo.iter_commits(max_count=limit):
            analysis = self._analyze_commit(commit)
            if analysis:
                commits.append(analysis)
        
        return commits

    def _analyze_commit(self, commit: Commit) -> Optional[CommitAnalysis]:
        """Analyze a single commit to extract relationships."""
        try:
            # Get file changes
            file_changes = []
            code_files = []
            doc_files = []
            
            # Analyze commit diff
            for item in commit.diff(commit.parents[0] if commit.parents else None):
                change_type = 'M'  # Modified by default
                if item.new_file:
                    change_type = 'A'
                elif item.deleted_file:
                    change_type = 'D'
                elif item.renamed_file:
                    change_type = 'R'
                
                path = item.b_path if item.b_path else item.a_path
                old_path = item.a_path if item.renamed_file else None
                
                file_change = FileChange(
                    path=path,
                    change_type=change_type,
                    old_path=old_path,
                    additions=item.diff.decode('utf-8', errors='ignore').count('\n+'),
                    deletions=item.diff.decode('utf-8', errors='ignore').count('\n-')
                )
                file_changes.append(file_change)
                
                # Categorize files
                ext = Path(path).suffix.lower()
                if ext in CODE_EXTENSIONS:
                    code_files.append(path)
                elif ext in DOC_EXTENSIONS:
                    doc_files.append(path)
            
            # Extract requirements and sprints from commit message
            message_requirements = set(REQ_PATTERN.findall(commit.message))
            message_sprints = set(SPRINT_REF_PATTERN.findall(commit.message))
            
            # Extract requirements and sprints from file changes
            requirements_mentioned = set()
            sprints_mentioned = set()
            
            for file_change in file_changes:
                # Check if file path contains requirement or sprint references
                path_requirements = REQ_PATTERN.findall(file_change.path)
                path_sprints = SPRINT_REF_PATTERN.findall(file_change.path)
                requirements_mentioned.update(path_requirements)
                sprints_mentioned.update(path_sprints)
                
                # If it's a code file, try to extract requirements from content
                if Path(file_change.path).suffix.lower() in CODE_EXTENSIONS:
                    try:
                        # Get file content at this commit
                        blob = commit.tree / file_change.path
                        if blob:
                            content = blob.data_stream.read().decode('utf-8', errors='ignore')
                            content_requirements = REQ_PATTERN.findall(content)
                            content_sprints = SPRINT_REF_PATTERN.findall(content)
                            requirements_mentioned.update(content_requirements)
                            sprints_mentioned.update(content_sprints)
                    except Exception:
                        # File might not exist at this commit or other issues
                        pass
            
            return CommitAnalysis(
                commit=commit,
                file_changes=file_changes,
                code_files=code_files,
                doc_files=doc_files,
                requirements_mentioned=requirements_mentioned,
                sprints_mentioned=sprints_mentioned,
                message_requirements=message_requirements,
                message_sprints=message_sprints
            )
            
        except Exception as e:
            print(f"Error analyzing commit {commit.hexsha}: {e}")
            return None

    def _create_commit_touches(self, tx, commit_analysis: CommitAnalysis):
        """Create Touches relationships between commits and files."""
        commit_hash = commit_analysis.commit.hexsha
        
        # Create or update commit node
        tx.run("""
            MERGE (c:Commit {hash: $hash})
            SET c.message = $message,
                c.author_name = $author_name,
                c.author_email = $author_email,
                c.timestamp = $timestamp,
                c.code_files_count = $code_files_count,
                c.doc_files_count = $doc_files_count
        """, 
        hash=commit_hash,
        message=commit_analysis.commit.message,
        author_name=commit_analysis.commit.author.name,
        author_email=commit_analysis.commit.author.email,
        timestamp=commit_analysis.commit.committed_datetime.isoformat(),
        code_files_count=len(commit_analysis.code_files),
        doc_files_count=len(commit_analysis.doc_files))
        
        # Create Touches relationships for all changed files
        for file_change in commit_analysis.file_changes:
            # Create or update file node
            tx.run("""
                MERGE (f:File {path: $path})
                SET f.is_code = $is_code,
                    f.is_doc = $is_doc,
                    f.extension = $extension
            """,
            path=file_change.path,
            is_code=Path(file_change.path).suffix.lower() in CODE_EXTENSIONS,
            is_doc=Path(file_change.path).suffix.lower() in DOC_EXTENSIONS,
            extension=Path(file_change.path).suffix.lower())
            
            # Create Touches relationship
            tx.run("""
                MATCH (c:Commit {hash: $commit_hash})
                MATCH (f:File {path: $file_path})
                MERGE (c)-[r:TOUCHES {change_type: $change_type, additions: $additions, deletions: $deletions}]->(f)
            """,
            commit_hash=commit_hash,
            file_path=file_change.path,
            change_type=file_change.change_type,
            additions=file_change.additions,
            deletions=file_change.deletions)

    def _create_requirement_touches(self, tx, commit_analysis: CommitAnalysis):
        """Create Touches relationships between requirements and code files."""
        all_requirements = commit_analysis.requirements_mentioned.union(commit_analysis.message_requirements)
        
        for req_id in all_requirements:
            for code_file in commit_analysis.code_files:
                # Create Touches relationship between requirement and code file
                tx.run("""
                    MATCH (r:Requirement {id: $req_id})
                    MATCH (f:File {path: $file_path})
                    MERGE (r)-[t:TOUCHES {via_commit: $commit_hash, timestamp: $timestamp}]->(f)
                """,
                req_id=req_id,
                file_path=code_file,
                commit_hash=commit_analysis.commit.hexsha,
                timestamp=commit_analysis.commit.committed_datetime.isoformat())

    def _create_sprint_touches(self, tx, commit_analysis: CommitAnalysis):
        """Create Touches relationships between sprints and code files."""
        all_sprints = commit_analysis.sprints_mentioned.union(commit_analysis.message_sprints)
        
        for sprint_num in all_sprints:
            for code_file in commit_analysis.code_files:
                # Create Touches relationship between sprint and code file
                tx.run("""
                    MATCH (s:Sprint {number: $sprint_num})
                    MATCH (f:File {path: $file_path})
                    MERGE (s)-[t:TOUCHES {via_commit: $commit_hash, timestamp: $timestamp}]->(f)
                """,
                sprint_num=sprint_num,
                file_path=code_file,
                commit_hash=commit_analysis.commit.hexsha,
                timestamp=commit_analysis.commit.committed_datetime.isoformat())

    def _create_chunk_changes(self, tx, commit_analysis: CommitAnalysis):
        """Create chunk-level change tracking."""
        for file_change in commit_analysis.file_changes:
            if file_change.change_type in ['M', 'A'] and Path(file_change.path).suffix.lower() in DOC_EXTENSIONS:
                # For documentation files, try to track chunk-level changes
                try:
                    # Get file content at this commit
                    blob = commit_analysis.commit.tree / file_change.path
                    if blob:
                        content = blob.data_stream.read().decode('utf-8', errors='ignore')
                        
                        # Split content into chunks (by headers or sections)
                        chunks = self._split_into_chunks(content)
                        
                        for i, chunk in enumerate(chunks):
                            if chunk.strip():
                                # Create chunk node
                                chunk_id = f"{file_change.path}:chunk:{i}"
                                tx.run("""
                                    MERGE (ch:Chunk {id: $chunk_id})
                                    SET ch.content = $content,
                                        ch.file_path = $file_path,
                                        ch.chunk_index = $chunk_index,
                                        ch.last_modified_commit = $commit_hash,
                                        ch.last_modified_timestamp = $timestamp
                                """,
                                chunk_id=chunk_id,
                                content=chunk.strip(),
                                file_path=file_change.path,
                                chunk_index=i,
                                commit_hash=commit_analysis.commit.hexsha,
                                timestamp=commit_analysis.commit.committed_datetime.isoformat())
                                
                                # Link chunk to file
                                tx.run("""
                                    MATCH (f:File {path: $file_path})
                                    MATCH (ch:Chunk {id: $chunk_id})
                                    MERGE (f)-[:CONTAINS_CHUNK]->(ch)
                                """,
                                file_path=file_change.path,
                                chunk_id=chunk_id)
                                
                                # Extract requirements from chunk and link them
                                chunk_requirements = REQ_PATTERN.findall(chunk)
                                for req_id in chunk_requirements:
                                    tx.run("""
                                        MATCH (r:Requirement {id: $req_id})
                                        MATCH (ch:Chunk {id: $chunk_id})
                                        MERGE (r)-[:MENTIONS]->(ch)
                                    """,
                                    req_id=req_id,
                                    chunk_id=chunk_id)
                                    
                except Exception as e:
                    print(f"Error processing chunks for {file_change.path}: {e}")

    def _split_into_chunks(self, content: str) -> List[str]:
        """Split content into meaningful chunks."""
        # Split by markdown headers
        chunks = re.split(r'\n(#{1,6}\s)', content)
        
        # Recombine headers with their content
        result = []
        for i in range(0, len(chunks), 2):
            if i + 1 < len(chunks):
                chunk = chunks[i] + chunks[i + 1]
                result.append(chunk)
            else:
                result.append(chunks[i])
        
        return [chunk.strip() for chunk in result if chunk.strip()]


def main():
    """Main entry point."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "password")
    repo = os.environ.get("REPO_PATH", str(Path(__file__).resolve().parents[1]))
    
    ingester = EnhancedGitIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
