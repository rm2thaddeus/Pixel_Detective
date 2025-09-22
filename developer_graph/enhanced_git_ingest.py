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
import logging

from git import Repo, Commit
from neo4j import GraphDatabase

from .sprint_mapping import SprintMapper

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
    loc_after: int = 0

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

logger = logging.getLogger(__name__)


class EnhancedGitIngester:
    """Enhanced git-based ingestion that creates proper planning-to-implementation links."""

    def __init__(self, repo_path: str, neo4j_uri: str, user: str, password: str):
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        self.requirement_map = {}
        self.sprint_map: Dict[str, Tuple[str, str]] = {}
        self.sprint_mapper = SprintMapper(repo_path)

    def _get_file_content_at_commit(self, commit: Commit, path: Optional[str]) -> Optional[str]:
        """Return text content of a file at a specific commit.

        Tries tree lookup first, then falls back to `git show` plumbing. Handles
        platform path separators robustly.
        """
        if not path:
            return None

        # Ensure POSIX-style path for git
        posix_path = path.replace('\\', '/')

        # Attempt 1: tree lookup
        try:
            blob = commit.tree / posix_path
            if blob is not None and getattr(blob, 'type', None) == 'blob':
                return blob.data_stream.read().decode('utf-8', errors='ignore')
        except Exception:
            # Fall through to git plumbing fallback
            pass

        # Attempt 2: git show (robust to path resolution quirks)
        try:
            return self.repo.git.show(f"{commit.hexsha}:{posix_path}")
        except Exception:
            return None

    # -------------------- Validation helpers --------------------
    def _validate_commit_processing(self, commit_analysis: CommitAnalysis) -> bool:
        commit = commit_analysis.commit
        try:
            if not commit.hexsha or len(commit.hexsha) < 7:
                logger.error("Invalid commit hash detected; skipping commit")
                return False
            if not getattr(commit, "committed_datetime", None):
                logger.error("Missing timestamp on commit %s", commit.hexsha)
                return False
            return True
        except Exception as exc:
            logger.exception("Commit validation failed for %s", getattr(commit, "hexsha", "<unknown>"), exc_info=exc)
            return False

    def _validate_file_change(self, file_change: FileChange) -> bool:
        if not file_change.path:
            logger.warning("Skipping file change with empty path")
            return False
        if file_change.change_type not in {"A", "M", "D", "R"}:
            logger.warning("Skipping file change %s with unsupported type %s", file_change.path, file_change.change_type)
            return False
        return True

    def _backfill_file_flags(self) -> None:
        code_ext = sorted(CODE_EXTENSIONS)
        doc_ext = sorted(DOC_EXTENSIONS)
        query = """
            MATCH (f:File)
            WITH f,
                 CASE
                     WHEN f.extension IS NOT NULL THEN toLower(f.extension)
                     WHEN f.path CONTAINS '.' THEN '.' + toLower(last(split(f.path, '.')))
                     ELSE ''
                 END AS ext
            SET f.extension = CASE WHEN f.extension IS NULL AND ext <> '' THEN ext ELSE f.extension END,
                f.is_code = CASE WHEN f.is_code IS NULL THEN ext IN $code_ext ELSE f.is_code END,
                f.is_doc = CASE WHEN f.is_doc IS NULL THEN ext IN $doc_ext ELSE f.is_doc END
        """
        with self.driver.session() as session:
            session.run(query, {"code_ext": code_ext, "doc_ext": doc_ext})
            session.run(
                """
                MATCH (c:GitCommit)
                WHERE (c.uid IS NULL OR trim(c.uid) = '') AND c.hash IS NOT NULL
                SET c.uid = c.hash
                """
            )

    def _assert_ingest_guards(self) -> None:
        cypher = """
            CALL {
                MATCH (c:GitCommit)
                WHERE c.uid IS NULL OR trim(c.uid) = ''
                RETURN count(c) AS missing_commit_uid
            }
            CALL {
                MATCH (f:File)
                WHERE f.is_code IS NULL
                RETURN count(f) AS missing_is_code
            }
            CALL {
                MATCH (f:File)
                WHERE f.is_doc IS NULL
                RETURN count(f) AS missing_is_doc
            }
            RETURN missing_commit_uid, missing_is_code, missing_is_doc
        """
        with self.driver.session() as session:
            record = session.run(cypher).single()

        missing_commit_uid = record.get("missing_commit_uid", 0) if record else 0
        missing_is_code = record.get("missing_is_code", 0) if record else 0
        missing_is_doc = record.get("missing_is_doc", 0) if record else 0

        if any(val > 0 for val in (missing_commit_uid, missing_is_code, missing_is_doc)):
            raise ValueError(
                f"Data validation failure after ingest: commits missing uid={missing_commit_uid}, "
                f"files missing is_code={missing_is_code}, files missing is_doc={missing_is_doc}"
            )

    def ingest(self):
        """Main ingestion process with enhanced git analysis."""
        logger.info("Starting enhanced git-based ingestion...")

        # Optional full reset (fresh graph)
        reset = os.environ.get("RESET_GRAPH", "").lower() in {"1", "true", "yes"}
        if reset:
            with self.driver.session() as session:
                logger.warning("RESET_GRAPH enabled — clearing existing graph data…")
                session.run("MATCH (n) DETACH DELETE n")

        # First, run the basic enhanced ingest to get sprints, requirements, documents, chunks
        self._run_basic_ingest()

        # Ensure constraints for core labels used here
        with self.driver.session() as session:
            session.execute_write(self._create_constraints)

        # Then analyze git commits to create Touches relationships
        commits = self._analyze_git_commits()
        
        logger.info("Analyzed %d commits", len(commits))
        
        with self.driver.session() as session:
            # Create Touches relationships between commits and files
            for commit_analysis in commits:
                session.execute_write(self._create_commit_touches, commit_analysis)

                # Create chunk-level change tracking
                session.execute_write(self._create_chunk_changes, commit_analysis)

                # Create Requirement->File IMPLEMENTS edges inferred from commit mentions
                session.execute_write(self._create_requirement_touches, commit_analysis)

            # Phase 2: Create commit ordering relationships
            session.execute_write(self._create_commit_ordering, commits)

            # Create planning-to-code Touches relationships
            session.execute_write(self._create_planning_touches)

            # Link requirements to their source documents
            session.execute_write(self._link_requirements_to_documents)

        # Link sprints to commits based on planning windows
        self._link_sprints_to_commits()

        # Optional roll-up: create sprint-level TOUCHED to files (counts)
        if os.environ.get("ENABLE_SPRINT_FILE_ROLLUP", "1") not in {"0", "false", "no"}:
            self._rollup_sprint_file_touches()

        # Optional: run temporal ingestion to enrich GitCommit/TOUCHED graph
        if os.environ.get("RUN_TEMPORAL", "1") not in {"0", "false", "no"}:
            try:
                from .git_history_service import GitHistoryService
                from .temporal_engine import TemporalEngine
                temporal_limit = int(os.environ.get("TEMPORAL_LIMIT", "1000"))
                git_svc = GitHistoryService(self.repo_path)
                engine = TemporalEngine(self.driver, git_svc)
                engine.apply_schema()
                ingested = engine.ingest_recent_commits(limit=temporal_limit)
                logger.info("Temporal ingestion added GitCommit graph: %s commits", ingested)
            except Exception as exc:
                logger.exception("Temporal ingestion failed", exc_info=exc)
        
        self._backfill_file_flags()
        self._assert_ingest_guards()

        logger.info("Enhanced git-based ingestion completed!")

    @staticmethod
    def _create_constraints(tx):
        """Create uniqueness constraints for nodes used by this ingester."""
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE")
        tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")

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
            logger.debug("Analyzing commit %s - %s", commit.hexsha[:8], commit.message.strip())
            logger.debug("Commit %s has %d parents", commit.hexsha[:8], len(commit.parents))
            
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
                
                logger.debug("File change %s – %s", change_type, path)
                
                # Get diff content as string
                diff_content = str(item.diff) if item.diff else ""

                # Lines of code after this commit for the file (approximate)
                loc_after = 0
                try:
                    if not item.deleted_file:
                        content = self._get_file_content_at_commit(commit, path)
                        if content:
                            loc_after = content.count('\n') + (0 if content.endswith('\n') else 1)
                    else:
                        # File deleted -> zero LOC after
                        loc_after = 0
                except Exception:
                    loc_after = 0
                
                file_change = FileChange(
                    path=path,
                    change_type=change_type,
                    old_path=old_path,
                    additions=diff_content.count('\n+'),
                    deletions=diff_content.count('\n-'),
                    loc_after=0 if change_type == 'D' else loc_after
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
                        content = self._get_file_content_at_commit(commit, file_change.path)
                        if content:
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
            
        except Exception as exc:
            logger.exception("Error analyzing commit %s", getattr(commit, "hexsha", "<unknown>"), exc_info=exc)
            return None

    def _create_commit_touches(self, tx, commit_analysis: CommitAnalysis):
        """Create Touches relationships between commits and files."""
        commit_hash = commit_analysis.commit.hexsha

        if not self._validate_commit_processing(commit_analysis):
            logger.error("Skipping commit %s due to validation failure", commit_hash)
            return

        # Create or update commit node (unified schema: GitCommit)
        tx.run("""
            MERGE (c:GitCommit {hash: $hash})
            SET c.message = $message,
                c.author = $author_email,
                c.timestamp = $timestamp,
                c.code_files_count = $code_files_count,
                c.doc_files_count = $doc_files_count,
                c.uid = coalesce(c.uid, $hash)
        """,
        hash=commit_hash,
        message=commit_analysis.commit.message,
        author_email=commit_analysis.commit.author.email,
        timestamp=commit_analysis.commit.committed_datetime.isoformat(),
        code_files_count=len(commit_analysis.code_files),
        doc_files_count=len(commit_analysis.doc_files))

        # Create Touches relationships for all changed files
        for file_change in commit_analysis.file_changes:
            if not self._validate_file_change(file_change):
                continue
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

            # Create TOUCHED relationship with timestamp (temporal schema)
            tx.run("""
                MATCH (c:GitCommit {hash: $commit_hash})
                MATCH (f:File {path: $file_path})
                MERGE (c)-[r:TOUCHED]->(f)
                SET r.change_type = $change_type,
                    r.additions = $additions,
                    r.deletions = $deletions,
                    r.lines_after = $loc_after,
                    r.timestamp = $timestamp
                SET f.loc = CASE $change_type WHEN 'D' THEN 0 ELSE $loc_after END
            """,
            commit_hash=commit_hash,
            file_path=file_change.path,
            change_type=file_change.change_type,
            additions=file_change.additions,
            deletions=file_change.deletions,
            loc_after=file_change.loc_after,
            timestamp=commit_analysis.commit.committed_datetime.isoformat())

            # If file was renamed, record refactor edge between files
            if file_change.change_type == 'R' and file_change.old_path and file_change.path:
                tx.run("""
                    MERGE (o:File {path: $old})
                    MERGE (n:File {path: $new})
                    MERGE (o)-[rr:REFACTORED_TO]->(n)
                    ON CREATE SET rr.commit = $commit_hash, rr.refactor_type = 'rename', rr.timestamp = $ts
                    ON MATCH SET rr.commit = coalesce(rr.commit, $commit_hash), rr.timestamp = coalesce(rr.timestamp, $ts)
                """,
                old=file_change.old_path,
                new=file_change.path,
                commit_hash=commit_hash,
                ts=commit_analysis.commit.committed_datetime.isoformat())

        logger.debug("Created TOUCHED relationships for commit %s", commit_hash)

        # Create Commit->Requirement IMPLEMENTS edges (provenance)
        all_reqs = set(commit_analysis.requirements_mentioned or set()).union(commit_analysis.message_requirements or set())
        for rid in all_reqs:
            tx.run("""
                MATCH (c:GitCommit {hash: $hash})
                MATCH (r:Requirement {id: $rid})
                MERGE (c)-[rel:IMPLEMENTS]->(r)
                ON CREATE SET rel.timestamp = $ts
                ON MATCH SET rel.timestamp = coalesce(rel.timestamp, $ts)
            """,
            hash=commit_hash,
            rid=rid,
            ts=commit_analysis.commit.committed_datetime.isoformat())

    def _create_requirement_touches(self, tx, commit_analysis: CommitAnalysis):
        """Create IMPLEMENTS relationships between requirements and code files.

        Source heuristic: requirement IDs present in commit message/code and files touched in that commit.
        """
        all_requirements = commit_analysis.requirements_mentioned.union(commit_analysis.message_requirements)

        for req_id in all_requirements:
            for code_file in commit_analysis.code_files:
                # Create IMPLEMENTS relationship between requirement and code file with commit provenance
                tx.run("""
                    MATCH (r:Requirement {id: $req_id})
                    MATCH (f:File {path: $file_path})
                    MERGE (r)-[t:IMPLEMENTS]->(f)
                    SET t.commit = $commit_hash,
                        t.timestamp = $timestamp
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
                    MERGE (s)-[t:TOUCHED {via_commit: $commit_hash, timestamp: $timestamp}]->(f)
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
                    # Fetch content robustly for this commit
                    content = self._get_file_content_at_commit(commit_analysis.commit, file_change.path)
                    if not content:
                        continue

                    # Extract structured chunks with consistent IDs
                    for ch in self._extract_chunks_from_text(str(file_change.path), content):
                        chunk_id = ch['id']
                        # Merge chunk and update provenance
                        tx.run("""
                            MERGE (ch:Chunk {id: $chunk_id})
                            SET ch.doc_path = $doc_path,
                                ch.heading = coalesce(ch.heading, $heading),
                                ch.level = coalesce(ch.level, $level),
                                ch.ordinal = coalesce(ch.ordinal, $ordinal),
                                ch.last_modified_commit = $commit_hash,
                                ch.last_modified_timestamp = $timestamp
                        """,
                        chunk_id=chunk_id,
                        doc_path=str(file_change.path),
                        heading=ch.get('heading'),
                        level=ch.get('level'),
                        ordinal=ch.get('ordinal'),
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

                        # Link commit to chunk with provenance
                        tx.run("""
                            MATCH (c:GitCommit {hash: $commit_hash})
                            MATCH (ch:Chunk {id: $chunk_id})
                            MERGE (c)-[m:MODIFIED]->(ch)
                            ON CREATE SET m.timestamp = $timestamp, m.file_path = $file_path
                            ON MATCH SET m.timestamp = coalesce(m.timestamp, $timestamp)
                        """,
                        commit_hash=commit_analysis.commit.hexsha,
                        chunk_id=chunk_id,
                        timestamp=commit_analysis.commit.committed_datetime.isoformat(),
                        file_path=file_change.path)

                        # Extract and link requirements mentioned inside chunk content
                        if ch.get('content'):
                            for req_id in REQ_PATTERN.findall(ch['content']):
                                tx.run("""
                                    MATCH (r:Requirement {id: $req_id})
                                    MATCH (ch:Chunk {id: $chunk_id})
                                    MERGE (r)-[:MENTIONS]->(ch)
                                """,
                                req_id=req_id,
                                chunk_id=chunk_id)
                                    
        except Exception as exc:
            logger.exception("Error processing chunks for %s", file_change.path, exc_info=exc)

    @staticmethod
    def _slugify(text: str) -> str:
        t = re.sub(r"[^a-zA-Z0-9\s-]", "", text.strip().lower())
        t = re.sub(r"\s+", "-", t)
        t = re.sub(r"-+", "-", t)
        return t or "section"

    def _extract_chunks_from_text(self, path: str, text: str) -> List[Dict[str, object]]:
        """Extract chunks consistent with enhanced_ingest IDs (path#slug-ordinal)."""
        lines = text.splitlines()
        chunks: List[Dict[str, object]] = []
        current: Optional[Dict[str, object]] = None
        ordinals: Dict[int, int] = {1: 0, 2: 0, 3: 0}
        buffer: List[str] = []

        def flush():
            nonlocal current, buffer
            if current is not None:
                content = "\n".join(buffer)
                current['content'] = content
                chunks.append(current)
            current = None
            buffer = []

        for line in lines:
            m = re.match(r"^(#{1,3})\s+(.*)$", line)
            if m:
                flush()
                level = len(m.group(1))
                heading = m.group(2).strip()
                ordinals[level] = ordinals.get(level, 0) + 1
                slug = self._slugify(heading)
                cid = f"{path}#{slug}-{ordinals[level]:02d}"
                current = {
                    'id': cid,
                    'doc_path': path,
                    'heading': heading,
                    'level': level,
                    'ordinal': ordinals[level],
                }
            else:
                buffer.append(line)
        flush()
        return chunks

    # -------------------- Linking Helpers --------------------
    def _link_requirements_to_documents(self, tx):
        tx.run(
            """
            MATCH (r:Requirement)
            WHERE r.source_file IS NOT NULL
            MATCH (d:Document {path: r.source_file})
            MERGE (r)-[:SPECIFIED_IN]->(d)
            """
        )

    def _parse_sprint_windows(self) -> Dict[str, Tuple[str, str]]:
        """Return sprint windows via the shared SprintMapper cache."""
        try:
            windows_meta = self.sprint_mapper.get_sprint_windows()
        except Exception as exc:
            logger.warning("Failed to load sprint windows: %s", exc)
            return {}

        windows: Dict[str, Tuple[str, str]] = {}
        for number, meta in windows_meta.items():
            start_iso = meta.get("start")
            end_iso = meta.get("end")
            if start_iso and end_iso:
                windows[str(number)] = (start_iso, end_iso)

        self.sprint_map = windows
        return windows

    def _link_sprints_to_commits(self):
        windows = self._parse_sprint_windows()
        if not windows:
            return
        with self.driver.session() as session:
            for num, (start_iso, end_iso) in windows.items():
                session.run(
                    """
                    MATCH (s:Sprint {number: $num})
                    WITH s
                    MATCH (c:GitCommit)
                    WHERE datetime(c.timestamp) >= datetime($start + 'T00:00:00')
                      AND datetime(c.timestamp) <= datetime($end + 'T23:59:59')
                    MERGE (s)-[:INCLUDES]->(c)
                    """,
                    num=num, start=start_iso, end=end_iso
                )

    def _rollup_sprint_file_touches(self):
        windows = self._parse_sprint_windows()
        if not windows:
            return
        with self.driver.session() as session:
            for num, (start_iso, end_iso) in windows.items():
                session.run(
                    """
                    MATCH (s:Sprint {number: $num})
                    MATCH (s)-[:INCLUDES]->(c:GitCommit)-[:TOUCHED]->(f:File)
                    WITH s,f, min(c.timestamp) AS first_ts, max(c.timestamp) AS last_ts, count(*) AS cnt
                    MERGE (s)-[r:TOUCHED]->(f)
                    SET r.scope = 'sprint', r.first_ts = first_ts, r.last_ts = last_ts, r.count = cnt
                    """,
                    num=num, start=start_iso, end=end_iso
                )

    def _create_planning_touches(self, tx):
        """Create Touches relationships between planning documents and code files."""
        logger.info("Creating planning-to-code Touches relationships…")
        
        # Get all requirements and sprints
        requirements = tx.run("MATCH (r:Requirement) RETURN r.id as id, coalesce(r.description, r.raw, '') as content").data()
        sprints = tx.run("MATCH (s:Sprint) RETURN s.number as number, s.name as name").data()
        
        # Get all code files
        code_files = tx.run("MATCH (f:File) WHERE f.is_code = true RETURN f.path as path").data()
        
        touches_count = 0
        
        # Analyze requirements for code file references
        for req in requirements:
            req_id = req['id']
            content = req.get('content', '') or ''
            
            # Look for file path references in requirement content
            for code_file in code_files:
                file_path = code_file['path']
                file_name = Path(file_path).name
                
                # Check if requirement mentions this file
                if (file_name in content or 
                    file_path in content or
                    any(part in content for part in file_path.split('/') if len(part) > 3)):
                    
                    # Create IMPLEMENTS relationship (doc-based mention signal)
                    tx.run("""
                        MATCH (r:Requirement {id: $req_id})
                        MATCH (f:File {path: $file_path})
                        MERGE (r)-[t:IMPLEMENTS]->(f)
                        ON CREATE SET t.source = 'doc-mention'
                        ON MATCH SET t.source = coalesce(t.source, 'doc-mention')
                    """, req_id=req_id, file_path=file_path)
                    touches_count += 1
        
        # Analyze sprints for code file references
        for sprint in sprints:
            sprint_num = sprint['number']
            sprint_name = sprint['name']
            
            # Look for file path references in sprint name and related documents
            for code_file in code_files:
                file_path = code_file['path']
                file_name = Path(file_path).name
                
                # Check if sprint mentions this file (basic heuristic)
                if (file_name in sprint_name or 
                    any(part in sprint_name for part in file_path.split('/') if len(part) > 3)):
                    
                    # Create MENTIONS relationship (structural mention signal)
                    tx.run("""
                        MATCH (s:Sprint {number: $sprint_num})
                        MATCH (f:File {path: $file_path})
                        MERGE (s)-[t:MENTIONS]->(f)
                    """, sprint_num=sprint_num, file_path=file_path)
                    touches_count += 1
        
        logger.info("Created %d planning-to-code Touches relationships", touches_count)

    @staticmethod
    def _create_commit_ordering(tx, commits: List[CommitAnalysis]) -> None:
        """Create NEXT_COMMIT and PREV_COMMIT relationships between commits.
        
        Phase 2: Add commit ordering relationships for timeline navigation.
        """
        if len(commits) < 2:
            return
        
        # Convert CommitAnalysis objects to dictionaries for sorting
        commit_data = []
        for commit_analysis in commits:
            commit_data.append({
                'hash': commit_analysis.commit.hexsha,
                'timestamp': commit_analysis.commit.committed_datetime.isoformat()
            })
        
        # Sort commits by timestamp to ensure proper ordering
        sorted_commits = sorted(commit_data, key=lambda x: x['timestamp'])
        
        # Create NEXT_COMMIT relationships (current -> next)
        for i in range(len(sorted_commits) - 1):
            current_hash = sorted_commits[i]['hash']
            next_hash = sorted_commits[i + 1]['hash']
            timestamp = sorted_commits[i + 1]['timestamp']  # Use next commit's timestamp
            
            tx.run("""
                MATCH (current:GitCommit {hash: $current_hash})
                MATCH (next:GitCommit {hash: $next_hash})
                MERGE (current)-[r:NEXT_COMMIT]->(next)
                SET r.timestamp = $timestamp
            """, current_hash=current_hash, next_hash=next_hash, timestamp=timestamp)
        
        # Create PREV_COMMIT relationships (current -> previous)
        for i in range(1, len(sorted_commits)):
            current_hash = sorted_commits[i]['hash']
            prev_hash = sorted_commits[i - 1]['hash']
            timestamp = sorted_commits[i]['timestamp']  # Use current commit's timestamp
            
            tx.run("""
                MATCH (current:GitCommit {hash: $current_hash})
                MATCH (prev:GitCommit {hash: $prev_hash})
                MERGE (current)-[r:PREV_COMMIT]->(prev)
                SET r.timestamp = $timestamp
            """, current_hash=current_hash, prev_hash=prev_hash, timestamp=timestamp)
        
        logger.info("Created commit ordering relationships for %d commits", len(sorted_commits))


def main():
    """Main entry point."""
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    # Disable authentication for open source Neo4j - set password to None
    password = os.environ.get("NEO4J_PASSWORD", None)  # No auth needed for open source
    repo = os.environ.get("REPO_PATH", str(Path(__file__).resolve().parents[1]))
    
    ingester = EnhancedGitIngester(str(repo), uri, user, password)
    ingester.ingest()


if __name__ == "__main__":
    main()
