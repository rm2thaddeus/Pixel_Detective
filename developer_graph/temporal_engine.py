"""Temporal ingestion engine (Phase 2 stub).

Merges commit and file facts into Neo4j using temporal schema helpers.
"""

from __future__ import annotations

from typing import Iterable, Dict, List, Optional
import re
from math import isfinite

from neo4j import Driver

from .git_history_service import GitHistoryService
from .schema.temporal_schema import (
    apply_schema,
    merge_commit,
    merge_file,
    relate_commit_touched_file,
    merge_requirement,
    relate_implements,
    relate_evolves_from_requirement,
    relate_refactored_file,
    relate_deprecated_by,
)


class TemporalEngine:
    def __init__(self, driver: Driver, git: GitHistoryService):
        self.driver = driver
        self.git = git
        # TTL cache for subgraph queries
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds TTL
        # Telemetry: cache and perf
        self._cache_hits = 0
        self._cache_misses = 0
        try:
            from collections import deque  # noqa: F401
            self._q_times_ms = deque(maxlen=100)
        except Exception:
            self._q_times_ms = []  # type: ignore[assignment]
        # Store last query summaries for diagnostics
        self._last_query_metrics = {
            "windowed_subgraph": {},
            "commit_buckets": {},
        }

    def apply_schema(self) -> None:
        apply_schema(self.driver)

    def _get_cache_key(self, from_timestamp, to_timestamp, node_types, limit, cursor, include_counts):
        """Generate cache key for subgraph query."""
        return (
            from_timestamp or "",
            to_timestamp or "",
            tuple(sorted(node_types or [])),
            limit,
            cursor or "",
            include_counts
        )

    def _get_cached_result(self, cache_key):
        """Get cached result if not expired."""
        import time
        if cache_key in self._cache:
            cached_data, expires_at = self._cache[cache_key]
            if time.time() < expires_at:
                try:
                    self._cache_hits += 1
                except Exception:
                    pass
                return cached_data
            else:
                del self._cache[cache_key]
        return None

    def _cache_result(self, cache_key, result):
        """Cache result with TTL."""
        import time
        self._cache[cache_key] = (result, time.time() + self._cache_ttl)

    def ingest_recent_commits(self, limit: int = 100) -> int:
        commits = self.git.get_commits(limit=limit)
        ingested = 0
        with self.driver.session() as session:
            for c in commits:
                def _tx(tx):
                    merge_commit(tx, {
                        "hash": c["hash"],
                        "message": c.get("message"),
                        "author": c.get("author_email"),
                        "timestamp": c.get("timestamp"),
                        "branch": "unknown",
                    })
                    for f in c.get("files_changed", []) or []:
                        merge_file(tx, {"path": f})
                        relate_commit_touched_file(
                            tx,
                            commit_hash=c["hash"],
                            file_path=f,
                            change_type="M",
                            timestamp=c.get("timestamp", ""),
                        )
                    # Extract requirement references from commit message (e.g., FR-123, NFR-45)
                    message: str = c.get("message", "") or ""
                    req_ids = set(re.findall(r"\b(?:FR|NFR)-\d+\b", message))
                    for req_id in req_ids:
                        # Merge requirement with minimal info; enrichment can occur later
                        merge_requirement(tx, {
                            "id": req_id,
                            "title": message.split("\n", 1)[0][:120],
                            "author": c.get("author_email"),
                            "date_created": c.get("timestamp"),
                            "goal_alignment": None,
                            "tags": None,
                        })
                        for f in c.get("files_changed", []) or []:
                            relate_implements(
                                tx,
                                requirement_id=req_id,
                                file_path=f,
                                commit_hash=c["hash"],
                                timestamp=c.get("timestamp", ""),
                            )
                    # Detect requirement evolution or deprecation patterns
                    try:
                        msg_lower = (message or "").lower()
                        # Pattern: NEW replaces OLD / supersedes / evolves from
                        pat_forward = re.compile(r"\b((?:nfr|fr)-\d+)\b\s*(replaces|supersedes|evolves from|in favor of)\s*\b((?:nfr|fr)-\d+)\b", re.IGNORECASE)
                        # Pattern: deprecate OLD in favor of NEW / -> NEW
                        pat_deprec = re.compile(r"deprecat(?:e|ed)\s+((?:nfr|fr)-\d+)\b.*?(?:in favor of|->|to)\s+((?:nfr|fr)-\d+)", re.IGNORECASE)
                        for m in pat_forward.finditer(message or ""):
                            new_id = m.group(1).upper()
                            old_id = m.group(3).upper()
                            # Ensure nodes exist
                            merge_requirement(tx, {
                                "id": new_id,
                                "title": message.split("\n", 1)[0][:120],
                                "author": c.get("author_email"),
                                "date_created": c.get("timestamp"),
                                "goal_alignment": None,
                                "tags": None,
                            })
                            merge_requirement(tx, {"id": old_id})
                            relate_evolves_from_requirement(
                                tx,
                                new_req_id=new_id,
                                old_req_id=old_id,
                                commit_hash=c["hash"],
                                diff_summary=None,
                                timestamp=c.get("timestamp", ""),
                            )
                        for m in pat_deprec.finditer(msg_lower):
                            old_id = m.group(1).upper()
                            new_id = m.group(2).upper()
                            merge_requirement(tx, {"id": new_id})
                            merge_requirement(tx, {"id": old_id})
                            relate_deprecated_by(
                                tx,
                                node_label="Requirement",
                                node_key="id",
                                node_value=old_id,
                                replacement_label="Requirement",
                                replacement_key="id",
                                replacement_value=new_id,
                                commit_hash=c["hash"],
                                reason="commit_message",
                                timestamp=c.get("timestamp", ""),
                            )
                    except Exception:
                        # Soft-fail NLP pattern extraction
                        pass

                    # Detect file refactors (renames) for this commit
                    try:
                        commit_obj = self.git.repo.commit(c["hash"])  # type: ignore[attr-defined]
                        parents = list(commit_obj.parents)
                        if parents:
                            diff_index = parents[0].diff(commit_obj, rename_find=True)
                            for d in diff_index:
                                if getattr(d, "change_type", None) == 'R':
                                    old_path = getattr(d, "a_path", None)
                                    new_path = getattr(d, "b_path", None)
                                    if old_path and new_path and old_path != new_path:
                                        merge_file(tx, {"path": old_path})
                                        merge_file(tx, {"path": new_path})
                                        relate_refactored_file(
                                            tx,
                                            old_path=old_path,
                                            new_path=new_path,
                                            commit_hash=c["hash"],
                                            refactor_type="rename",
                                            timestamp=c.get("timestamp", ""),
                                        )
                    except Exception:
                        # Soft-fail rename detection
                        pass
                session.write_transaction(_tx)
                ingested += 1
        return ingested

    def ingest_recent_commits_batched(self, limit: int = 100, batch_size: int = 50) -> int:
        """Optimized: Ingest commits using batched UNWIND operations."""
        commits = self.git.get_commits_batched(limit=limit)
        ingested = 0
        
        # Process in batches
        for i in range(0, len(commits), batch_size):
            batch = commits[i:i + batch_size]
            ingested += self._ingest_commit_batch(batch)
        
        return ingested

    def _ingest_commit_batch(self, commits: List[Dict]) -> int:
        """Ingest a batch of commits using UNWIND operations."""
        with self.driver.session() as session:
            # Prepare commit data for UNWIND
            commit_data = []
            file_data = []
            requirement_data = []
            implements_data = []
            
            for commit in commits:
                commit_hash = commit["hash"]
                timestamp = commit.get("timestamp")
                message = commit.get("message", "")
                
                # Add commit data
                commit_data.append({
                    "hash": commit_hash,
                    "message": message,
                    "author": commit.get("author_email", ""),
                    "timestamp": timestamp,
                    "branch": "unknown"
                })
                
                # Add file data for this commit
                for file_info in commit.get("files_changed", []):
                    if isinstance(file_info, dict):
                        file_path = file_info.get("path", "")
                        change_type = file_info.get("change_type", "M")
                    else:
                        file_path = str(file_info)
                        change_type = "M"
                    
                    if file_path:
                        file_data.append({
                            "commit_hash": commit_hash,
                            "file_path": file_path,
                            "change_type": change_type,
                            "timestamp": timestamp
                        })
                
                # Extract requirement references from commit message
                req_ids = set(re.findall(r"\b(?:FR|NFR)-\d+\b", message))
                for req_id in req_ids:
                    requirement_data.append({
                        "id": req_id,
                        "title": message.split("\n", 1)[0][:120],
                        "author": commit.get("author_email", ""),
                        "date_created": timestamp,
                        "goal_alignment": None,
                        "tags": None
                    })
                    
                    # Add implements relationships for all files in this commit
                    for file_info in commit.get("files_changed", []):
                        if isinstance(file_info, dict):
                            file_path = file_info.get("path", "")
                        else:
                            file_path = str(file_info)
                        
                        if file_path:
                            implements_data.append({
                                "requirement_id": req_id,
                                "file_path": file_path,
                                "commit_hash": commit_hash,
                                "timestamp": timestamp
                            })
            
            # Execute batched operations
            def _tx(tx):
                # Batch create commits
                if commit_data:
                    tx.run("""
                        UNWIND $commits as c
                        MERGE (gc:GitCommit {hash: c.hash})
                        ON CREATE SET gc.message = c.message,
                                      gc.author = c.author,
                                      gc.timestamp = datetime(c.timestamp),
                                      gc.branch = c.branch,
                                      gc.uid = c.hash
                        ON MATCH SET gc.message = coalesce(c.message, gc.message),
                                     gc.author = coalesce(c.author, gc.author),
                                     gc.timestamp = coalesce(datetime(c.timestamp), gc.timestamp),
                                     gc.branch = coalesce(c.branch, gc.branch)
                    """, commits=commit_data)
                
                # Batch create files and relationships
                if file_data:
                    tx.run("""
                        UNWIND $files as f
                        MERGE (fl:File {path: f.file_path})
                        ON CREATE SET fl.uid = f.file_path
                        MERGE (gc:GitCommit {hash: f.commit_hash})
                        MERGE (gc)-[r:TOUCHED]->(fl)
                        ON CREATE SET r.change_type = f.change_type,
                                      r.timestamp = datetime(f.timestamp)
                        ON MATCH SET r.change_type = coalesce(f.change_type, r.change_type),
                                     r.timestamp = coalesce(datetime(f.timestamp), r.timestamp)
                    """, files=file_data)
                
                # Batch create requirements
                if requirement_data:
                    tx.run("""
                        UNWIND $requirements as r
                        MERGE (req:Requirement {id: r.id})
                        ON CREATE SET req.title = r.title,
                                      req.author = r.author,
                                      req.date_created = datetime(r.date_created),
                                      req.goal_alignment = r.goal_alignment,
                                      req.tags = r.tags,
                                      req.uid = r.id
                        ON MATCH SET req.title = coalesce(r.title, req.title),
                                     req.author = coalesce(r.author, req.author),
                                     req.date_created = coalesce(datetime(r.date_created), req.date_created)
                    """, requirements=requirement_data)
                
                # Batch create implements relationships
                if implements_data:
                    tx.run("""
                        UNWIND $implements as i
                        MATCH (req:Requirement {id: i.requirement_id})
                        MATCH (fl:File {path: i.file_path})
                        MERGE (req)-[r:IMPLEMENTS]->(fl)
                        ON CREATE SET r.commit_hash = i.commit_hash,
                                      r.timestamp = datetime(i.timestamp),
                                      r.sources = ['commit_message'],
                                      r.confidence = 0.7
                        ON MATCH SET r.commit_hash = coalesce(i.commit_hash, r.commit_hash),
                                     r.timestamp = coalesce(datetime(i.timestamp), r.timestamp)
                    """, implements=implements_data)
            
            session.execute_write(_tx)
            return len(commits)

    def ingest_recent_commits_parallel(self, limit: int = 100, max_workers: int = 4, batch_size: int = 50) -> int:
        """Parallel version of ingest_recent_commits with batched writes for better performance."""
        import concurrent.futures
        from collections import defaultdict
        import threading
        
        commits = self.git.get_commits(limit=limit)
        ingested = 0
        
        # Thread-safe collections for batching
        operations_lock = threading.Lock()
        operations_batch = []
        
        def extract_commit_data(commit):
            """Extract all data from a single commit (CPU-bound work)."""
            c = commit
            operations = []
            
            # Commit data
            operations.append(('merge_commit', {
                "hash": c["hash"],
                "message": c.get("message"),
                "author": c.get("author_email"),
                "timestamp": c.get("timestamp"),
                "branch": "unknown",
            }))
            
            # File operations
            for f in c.get("files_changed", []) or []:
                operations.append(('merge_file', {"path": f}))
                operations.append(('relate_commit_touched_file', {
                    "commit_hash": c["hash"],
                    "file_path": f,
                    "change_type": "M",
                    "timestamp": c.get("timestamp", ""),
                }))
            
            # Requirement extraction
            message: str = c.get("message", "") or ""
            req_ids = set(re.findall(r"\b(?:FR|NFR)-\d+\b", message))
            for req_id in req_ids:
                operations.append(('merge_requirement', {
                    "id": req_id,
                    "title": message.split("\n", 1)[0][:120],
                    "author": c.get("author_email"),
                    "date_created": c.get("timestamp"),
                    "goal_alignment": None,
                    "tags": None,
                }))
                for f in c.get("files_changed", []) or []:
                    operations.append(('relate_implements', {
                        "requirement_id": req_id,
                        "file_path": f,
                        "commit_hash": c["hash"],
                        "timestamp": c.get("timestamp", ""),
                    }))
            
            # Pattern matching for requirement evolution
            try:
                msg_lower = (message or "").lower()
                pat_forward = re.compile(r"\b((?:nfr|fr)-\d+)\b\s*(replaces|supersedes|evolves from|in favor of)\s*\b((?:nfr|fr)-\d+)\b", re.IGNORECASE)
                pat_deprec = re.compile(r"deprecat(?:e|ed)\s+((?:nfr|fr)-\d+)\b.*?(?:in favor of|->|to)\s+((?:nfr|fr)-\d+)", re.IGNORECASE)
                
                for m in pat_forward.finditer(message or ""):
                    new_id = m.group(1).upper()
                    old_id = m.group(3).upper()
                    operations.append(('merge_requirement', {
                        "id": new_id,
                        "title": message.split("\n", 1)[0][:120],
                        "author": c.get("author_email"),
                        "date_created": c.get("timestamp"),
                        "goal_alignment": None,
                        "tags": None,
                    }))
                    operations.append(('merge_requirement', {"id": old_id}))
                    operations.append(('relate_evolves_from_requirement', {
                        "new_req_id": new_id,
                        "old_req_id": old_id,
                        "commit_hash": c["hash"],
                        "diff_summary": None,
                        "timestamp": c.get("timestamp", ""),
                    }))
                
                for m in pat_deprec.finditer(msg_lower):
                    old_id = m.group(1).upper()
                    new_id = m.group(2).upper()
                    operations.append(('merge_requirement', {"id": new_id}))
                    operations.append(('merge_requirement', {"id": old_id}))
                    operations.append(('relate_deprecated_by', {
                        "node_label": "Requirement",
                        "node_key": "id",
                        "node_value": old_id,
                        "replacement_label": "Requirement",
                        "replacement_key": "id",
                        "replacement_value": new_id,
                        "commit_hash": c["hash"],
                        "reason": "commit_message",
                        "timestamp": c.get("timestamp", ""),
                    }))
            except Exception:
                pass
            
            # File refactor detection
            try:
                commit_obj = self.git.repo.commit(c["hash"])
                parents = list(commit_obj.parents)
                if parents:
                    diff_index = parents[0].diff(commit_obj, rename_find=True)
                    for d in diff_index:
                        if getattr(d, "change_type", None) == 'R':
                            old_path = getattr(d, "a_path", None)
                            new_path = getattr(d, "b_path", None)
                            if old_path and new_path and old_path != new_path:
                                operations.append(('merge_file', {"path": old_path}))
                                operations.append(('merge_file', {"path": new_path}))
                                operations.append(('relate_refactored_file', {
                                    "old_path": old_path,
                                    "new_path": new_path,
                                    "commit_hash": c["hash"],
                                    "refactor_type": "rename",
                                    "timestamp": c.get("timestamp", ""),
                                }))
            except Exception:
                pass
            
            return operations
        
        def write_batch(operations_batch):
            """Write a batch of operations to Neo4j."""
            if not operations_batch:
                return
            
            with self.driver.session() as session:
                def _tx(tx):
                    for op_type, params in operations_batch:
                        if op_type == 'merge_commit':
                            merge_commit(tx, params)
                        elif op_type == 'merge_file':
                            merge_file(tx, params)
                        elif op_type == 'relate_commit_touched_file':
                            relate_commit_touched_file(tx, **params)
                        elif op_type == 'merge_requirement':
                            merge_requirement(tx, params)
                        elif op_type == 'relate_implements':
                            relate_implements(tx, **params)
                        elif op_type == 'relate_evolves_from_requirement':
                            relate_evolves_from_requirement(tx, **params)
                        elif op_type == 'relate_deprecated_by':
                            relate_deprecated_by(tx, **params)
                        elif op_type == 'relate_refactored_file':
                            relate_refactored_file(tx, **params)
                
                session.write_transaction(_tx)
        
        # Use ThreadPoolExecutor for parallel extraction
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all commit processing tasks
            future_to_commit = {
                executor.submit(extract_commit_data, commit): commit 
                for commit in commits
            }
            
            # Process completed extractions and batch writes
            for future in concurrent.futures.as_completed(future_to_commit):
                try:
                    operations = future.result()
                    
                    with operations_lock:
                        operations_batch.extend(operations)
                        
                        # Write batch when it reaches the batch size
                        if len(operations_batch) >= batch_size:
                            write_batch(operations_batch)
                            operations_batch.clear()
                            ingested += 1
                            
                except Exception as e:
                    print(f"Error processing commit: {e}")
                    continue
        
        # Write any remaining operations
        with operations_lock:
            if operations_batch:
                write_batch(operations_batch)
                ingested += 1
        
        return ingested


    # -------------------- Phase 2: Evolution & Temporal Queries --------------------

    def _commit_timestamps_from_hashes(self, start_commit: Optional[str], end_commit: Optional[str]) -> Dict[str, Optional[str]]:
        start_ts: Optional[str] = None
        end_ts: Optional[str] = None
        if start_commit:
            sc = self.git.get_commit(start_commit)
            start_ts = sc.get("timestamp") if sc else None
        if end_commit:
            ec = self.git.get_commit(end_commit)
            end_ts = ec.get("timestamp") if ec else None
        return {"start": start_ts, "end": end_ts}

    def time_bounded_subgraph(self, start_commit: Optional[str], end_commit: Optional[str], limit: int = 1000, offset: int = 0) -> Dict[str, object]:
        bounds = self._commit_timestamps_from_hashes(start_commit, end_commit)
        start_ts = bounds.get("start")
        end_ts = bounds.get("end")
        # Build WHERE clause based on available bounds; relationships must carry r.timestamp
        where_clauses: List[str] = ["r.timestamp IS NOT NULL"]
        params: Dict[str, object] = {"limit": max(1, min(limit, 2000))}
        if start_ts:
            where_clauses.append("r.timestamp >= $start_ts")
            params["start_ts"] = start_ts
        if end_ts:
            where_clauses.append("r.timestamp <= $end_ts")
            params["end_ts"] = end_ts

        cypher = (
            "MATCH (a)-[r]->(b) "
            "WHERE " + " AND ".join(where_clauses) + " "
            "RETURN a, TYPE(r) AS type, r.timestamp AS ts, b "
            "ORDER BY ts DESC "
            "SKIP $offset LIMIT $limit"
        )

        nodes_seen: Dict[str, Dict[str, object]] = {}
        links: List[Dict[str, object]] = []
        with self.driver.session() as session:
            params["offset"] = max(0, int(offset))
            result = session.run(cypher, params)
            for rec in result:
                a = rec.get("a", {})
                b = rec.get("b", {})
                rtype = rec.get("type", "RELATED")
                ts = rec.get("ts")
                # Use basic extraction mirroring API util to avoid import cycle
                def _nid(node):
                    if isinstance(node, dict):
                        if "id" in node:
                            return str(node["id"])
                        if "number" in node:
                            return f"sprint-{node['number']}"
                        if "path" in node:
                            return node["path"]
                    return str(abs(hash(str(node))))[:10]
                for node_data in (a, b):
                    nid = _nid(node_data)
                    if nid not in nodes_seen:
                        nodes_seen[nid] = {"id": nid, **(node_data if isinstance(node_data, dict) else {"raw": str(node_data)})}
                links.append({"from": _nid(a), "to": _nid(b), "type": rtype, "timestamp": ts})
        return {"nodes": list(nodes_seen.values()), "links": links}

    def build_evolution_timeline_for_requirement(self, req_id: str, limit: int = 500) -> List[Dict[str, object]]:
        """Return chronological events for a Requirement: IMPLEMENTS, EVOLVES_FROM edges, etc."""
        cypher = (
            "MATCH (r:Requirement {id: $rid}) "
            "OPTIONAL MATCH (r)-[imp:IMPLEMENTS]->(f:File) "
            "WITH r, collect({type:'IMPLEMENTS', ts: imp.timestamp, commit: imp.commit, file: f.path}) AS impls "
            "OPTIONAL MATCH (r)-[e:EVOLVES_FROM]->(prev:Requirement) "
            "WITH r, impls, collect({type:'EVOLVES_FROM', ts: e.commit, commit: e.commit, from: prev.id, diff: e.diff_summary}) AS evs "
            "RETURN impls + evs AS events"
        )
        with self.driver.session() as session:
            rec = session.run(cypher, {"rid": req_id}).single()
            events = rec["events"] if rec and rec.get("events") else []
        # Normalize and sort
        norm: List[Dict[str, object]] = []
        for e in events or []:
            ts = e.get("ts") or e.get("timestamp") or ""
            etype = e.get("type") or "EVENT"
            title = (
                f"Implements {e.get('file')}" if etype == "IMPLEMENTS" else
                f"Evolves from {e.get('from')}" if etype == "EVOLVES_FROM" else etype
            )
            norm.append({"type": etype, "timestamp": ts, "title": title, **e})
        norm.sort(key=lambda x: x.get("timestamp") or "")
        return norm[:limit]

    def build_evolution_timeline_for_file(self, path: str, limit: int = 500) -> List[Dict[str, object]]:
        """Return chronological events for a File: TOUCHED by commits, REFACTORED_TO."""
        cypher = (
            "MATCH (c:GitCommit)-[t:TOUCHED]->(f:File {path: $path}) "
            "WITH collect({type:'TOUCHED', ts: t.timestamp, commit: c.hash}) AS touches "
            "OPTIONAL MATCH (f)-[r:REFACTORED_TO]->(nf:File) "
            "WITH touches + collect({type:'REFACTORED_TO', ts: r.commit, commit: r.commit, to: nf.path, refactor_type: r.refactor_type}) AS events "
            "RETURN events"
        )
        with self.driver.session() as session:
            rec = session.run(cypher, {"path": path}).single()
            events = rec["events"] if rec and rec.get("events") else []
        norm: List[Dict[str, object]] = []
        for e in events or []:
            ts = e.get("ts") or e.get("timestamp") or ""
            etype = e.get("type") or "EVENT"
            title = (
                f"Touched by {e.get('commit')}" if etype == "TOUCHED" else
                f"Refactored to {e.get('to')}" if etype == "REFACTORED_TO" else etype
            )
            norm.append({"type": etype, "timestamp": ts, "title": title, **e})
        norm.sort(key=lambda x: x.get("timestamp") or "")
        return norm[:limit]

    # -------------------- Phase 4: Performance Primitives --------------------

    def get_windowed_subgraph(
        self, 
        from_timestamp: Optional[str] = None, 
        to_timestamp: Optional[str] = None,
        node_types: Optional[List[str]] = None,
        limit: int = 1000,
        cursor: Optional[str] = None,
        include_counts: bool = True
    ) -> Dict[str, object]:
        """Get a time-bounded subgraph with pagination and type filtering.
        
        Returns nodes and edges within the time window, with counts and pagination info.
        """
        print(f"get_windowed_subgraph called with include_counts={include_counts}")
        import time
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(from_timestamp, to_timestamp, node_types, limit, cursor, include_counts)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            try:
                self._cache_hits += 1
            except Exception:
                pass
            return cached_result
        try:
            self._cache_misses += 1
        except Exception:
            pass
        
        # Build WHERE clause for time bounds
        # Include both temporal relationships and non-temporal relationships (like Sprint nodes)
        where_clauses = ["(r.timestamp IS NOT NULL OR type(r) IN ['INCLUDES', 'CONTAINS_DOC', 'CONTAINS_CHUNK', 'PART_OF', 'IMPLEMENTS', 'MENTIONS', 'EVOLVES_FROM', 'REFACTORED_TO'])"]
        params = {"limit": max(1, min(limit, 50000))}
        
        # Performance optimization: If no time bounds specified, limit to last 7 days
        # This prevents scanning the entire graph when no time filter is provided
        if not from_timestamp and not to_timestamp:
            from datetime import datetime, timedelta
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            where_clauses.append("(r.timestamp IS NULL OR r.timestamp >= $default_from_ts)")
            params["default_from_ts"] = seven_days_ago
        
        if from_timestamp:
            where_clauses.append("(r.timestamp IS NULL OR r.timestamp >= $from_ts)")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where_clauses.append("(r.timestamp IS NULL OR r.timestamp <= $to_ts)")
            params["to_ts"] = to_timestamp
            
        # Add node type filtering if specified
        node_type_filter = ""
        if node_types:
            type_conditions = ["'" + t + "' IN labels(a)" for t in node_types]
            type_conditions.extend(["'" + t + "' IN labels(b)" for t in node_types])
            where_clauses.append("(" + " OR ".join(type_conditions) + ")")
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Get total counts first (only if include_counts is True)
        total_nodes = None
        total_edges = None
        if include_counts:
            # Count all nodes and edges, not just those with temporal relationships
            # Optimized count queries - only count recent data for performance
            count_cypher = """
                MATCH (n)
                WHERE (n.timestamp IS NULL OR n.timestamp >= $default_from_ts)
                RETURN count(n) AS node_count
            """
            edge_count_cypher = """
                MATCH ()-[r]->()
                WHERE (r.timestamp IS NULL OR r.timestamp >= $default_from_ts)
                RETURN count(r) AS edge_count
            """
            print(f"Executing count query: {count_cypher}")
        
        with self.driver.session() as session:
            if include_counts:
                print(f"include_counts is True, executing count query")
                # Get node count
                count_result_cursor = session.run(count_cypher, params)
                count_record = None
                try:
                    count_record = count_result_cursor.single()
                    print(f"Count query result: {count_record}")
                    # consume to collect timings/summary after getting the data
                    summary = count_result_cursor.consume()
                    self._last_query_metrics["windowed_subgraph"]["count_ms"] = getattr(summary, "result_available_after", 0)
                except Exception as e:
                    print(f"Count query error: {e}")
                    count_record = None
                    self._last_query_metrics["windowed_subgraph"]["count_ms"] = 0
                total_nodes = count_record["node_count"] if count_record else 0
                
                # Get edge count
                edge_count_record = None
                try:
                    edge_count_cursor = session.run(edge_count_cypher, params)
                    edge_count_record = edge_count_cursor.single()
                    print(f"Edge count query result: {edge_count_record}")
                    edge_count_cursor.consume()
                except Exception as e:
                    print(f"Edge count query error: {e}")
                    edge_count_record = None
                total_edges = edge_count_record["edge_count"] if edge_count_record else 0
                
                print(f"Final counts - total_nodes: {total_nodes}, total_edges: {total_edges}")
            else:
                print(f"include_counts is False")
            
            # Keyset pagination support: parse cursor as "<ts>|<rid>" or fallback to numeric offset
            keyset = None
            is_legacy_offset = False
            if cursor:
                try:
                    if '|' in cursor:
                        c_ts, c_rid_str = cursor.split('|', 1)
                        if c_ts:
                            keyset = (c_ts, int(c_rid_str))
                    else:
                        _ = int(cursor)
                        is_legacy_offset = True
                except Exception:
                    is_legacy_offset = False

            if is_legacy_offset:
                try:
                    params["offset"] = int(cursor) if cursor else 0
                except Exception:
                    params["offset"] = 0

            extra_clause = ""
            if keyset is not None:
                params["c_ts"] = keyset[0]
                params["c_rid"] = keyset[1]
                extra_clause = " AND (r.timestamp < $c_ts OR (r.timestamp = $c_ts AND elementId(r) < $c_rid))"

            # Ultra-optimized query: Start with recent commits and their immediate relationships
            # This avoids the expensive full graph scan
            if not from_timestamp and not to_timestamp and limit <= 100:
                # For small requests without time bounds, use a much faster approach
                # Include all relationship types, not just TOUCHED
                main_cypher = (
                    "MATCH (a)-[r]->(b) "
                    "WHERE (r.timestamp IS NULL OR r.timestamp >= $default_from_ts) "
                    "WITH a, b, r, type(r) AS rel_type, COALESCE(r.timestamp, datetime()) AS ts, elementId(r) AS rid "
                    "ORDER BY ts DESC, rid DESC "
                    "LIMIT $limit "
                    "RETURN DISTINCT a, labels(a) AS a_labels, b, labels(b) AS b_labels, r, rel_type, ts, rid"
                )
            else:
                # Original optimized query for larger requests or with time bounds
                main_cypher = (
                    "MATCH (a)-[r]->(b) " + where_clause
                    + (extra_clause if keyset is not None else "")
                    + " WITH a, b, r, type(r) AS rel_type, r.timestamp AS ts, elementId(r) AS rid"
                    + " ORDER BY ts DESC, rid DESC"
                    + (" SKIP $offset" if is_legacy_offset else "")
                    + " LIMIT $limit"
                    + " RETURN DISTINCT a, labels(a) AS a_labels, b, labels(b) AS b_labels, r, rel_type, ts, rid"
                )
            
            result_cursor = session.run(main_cypher, params)
            
            # Process results
            nodes_seen = {}
            edges = []
            
            for rec in result_cursor:
                a = rec.get("a", {})
                b = rec.get("b", {})
                a_labels = rec.get("a_labels") or []
                b_labels = rec.get("b_labels") or []
                r = rec.get("r", {})
                rel_type = rec.get("rel_type", "RELATED")
                ts = rec.get("ts")
                
                # Extract node IDs using consistent logic
                def extract_node_id(node_data):
                    if isinstance(node_data, dict):
                        if "id" in node_data:
                            return str(node_data["id"])
                        if "hash" in node_data:
                            return str(node_data["hash"])
                        if "number" in node_data:
                            return "sprint-" + str(node_data['number'])
                        if "path" in node_data:
                            return node_data["path"]
                    return str(abs(hash(str(node_data))))[:10]
                
                a_id = extract_node_id(a)
                b_id = extract_node_id(b)
                
                # Store nodes
                for node_data, node_id, labels in [(a, a_id, a_labels), (b, b_id, b_labels)]:
                    if node_id not in nodes_seen:
                        clean_data = {k: v for k, v in node_data.items() if v is not None} if isinstance(node_data, dict) else {"raw": str(node_data)}
                        # include labels to help UI typing/color
                        if labels:
                            clean_data = {"labels": labels, **clean_data}

                        # Provide deterministic fallback coordinates to stabilize client rendering
                        if "x" not in clean_data or "y" not in clean_data:
                            import hashlib, math
                            # Stable hash from node id
                            h = int(hashlib.md5(str(node_id).encode("utf-8")).hexdigest()[:8], 16)
                            angle = (h % 3600) / 3600.0 * 2 * math.pi
                            # Spread radius in a ring to avoid piling up
                            ring = (h // 3600) % 4  # 0..3 rings
                            radius = 350 + ring * 180
                            clean_data["x"] = float(radius * math.cos(angle))
                            clean_data["y"] = float(radius * math.sin(angle))
                        else:
                            # Ensure coordinates are valid numbers
                            try:
                                clean_data["x"] = float(clean_data["x"])
                                clean_data["y"] = float(clean_data["y"])
                                if not isfinite(clean_data["x"]) or not isfinite(clean_data["y"]):
                                    raise ValueError("Invalid coordinates")
                            except (ValueError, TypeError):
                                # Fallback to generated coordinates
                                import hashlib, math
                                h = int(hashlib.md5(str(node_id).encode("utf-8")).hexdigest()[:8], 16)
                                angle = (h % 3600) / 3600.0 * 2 * math.pi
                                ring = (h // 3600) % 4
                                radius = 350 + ring * 180
                                clean_data["x"] = float(radius * math.cos(angle))
                                clean_data["y"] = float(radius * math.sin(angle))

                        # Lightweight default size based on label/type
                        if "size" not in clean_data:
                            lbls = set((labels or []))
                            if "Requirement" in lbls:
                                clean_data["size"] = 2.0
                            elif "GitCommit" in lbls or "Commit" in lbls:
                                clean_data["size"] = 1.2
                            elif "File" in lbls:
                                clean_data["size"] = 1.4
                            elif "Document" in lbls or "Chunk" in lbls:
                                clean_data["size"] = 1.0
                            else:
                                clean_data["size"] = 1.0

                        nodes_seen[node_id] = {"id": node_id, **clean_data}
                
                # Store edge
                edges.append({
                    "from": a_id,
                    "to": b_id,
                    "type": rel_type,
                    "timestamp": ts,
                    "rid": rec.get("rid"),
                    "properties": {k: v for k, v in r.items() if v is not None} if isinstance(r, dict) else {}
                })
            
            # Calculate next cursor
            next_cursor = None
            if len(edges) == limit:
                last = edges[-1] if edges else None
                if last and last.get("timestamp") is not None and last.get("rid") is not None:
                    next_cursor = str(last['timestamp']) + "|" + str(last['rid'])
                elif is_legacy_offset:
                    next_cursor = str(params.get("offset", 0) + limit)
            
            # capture summary timings if available
            try:
                summary = result_cursor.consume()
                plan_time = getattr(summary, "result_available_after", 0)
                self._last_query_metrics["windowed_subgraph"]["query_ms_driver"] = plan_time
            except Exception:
                pass
            query_time = time.time() - start_time
            
            result = {
                "nodes": list(nodes_seen.values()),
                "edges": edges,
                "pagination": {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "returned_nodes": len(nodes_seen),
                    "returned_edges": len(edges),
                    "limit": limit,
                    "offset": (params.get("offset", 0) if is_legacy_offset else 0),
                    "next_cursor": next_cursor,
                    "has_more": next_cursor is not None
                },
                "performance": {
                    "query_time_ms": round(query_time * 1000, 2),
                    "filters": {
                        "from_timestamp": from_timestamp,
                        "to_timestamp": to_timestamp,
                        "node_types": node_types
                    }
                }
            }
            
            # Add counts only if include_counts is True
            if include_counts:
                result["total_nodes"] = total_nodes
                result["total_edges"] = total_edges
                result["pagination"]["total_nodes"] = total_nodes
                result["pagination"]["total_edges"] = total_edges
            
            # Record perf sample
            try:
                val = round(query_time * 1000, 2)
                if hasattr(self, "_q_times_ms") and self._q_times_ms is not None:
                    try:
                        self._q_times_ms.append(val)  # type: ignore[attr-defined]
                    except Exception:
                        # list fallback
                        self._q_times_ms.append(val)  # type: ignore[operator]
            except Exception:
                pass

            # Add cache hit status
            result["performance"]["cache_hit"] = False

            # Cache the result
            self._cache_result(cache_key, result)
            
            return result

    def get_commits_buckets(
        self, 
        granularity: str = "day",
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, object]]:
        """Get commit counts grouped by time buckets for timeline density.
        
        granularity: 'day' or 'week'
        """
        import time
        start_time = time.time()
        
        # Validate granularity
        if granularity not in ["day", "week"]:
            granularity = "day"
        
        # Build time formatting for grouping
        if granularity == "day":
            time_format = "date(datetime(r.timestamp))"
        else:  # week
            time_format = "date(datetime(r.timestamp) - duration('P' + toString(dayOfWeek(datetime(r.timestamp)) - 1) + 'D'))"
        
        # Build WHERE clause
        where_clauses = ["r.timestamp IS NOT NULL"]
        params = {"limit": max(1, min(limit, 10000))}
        
        if from_timestamp:
            where_clauses.append("r.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where_clauses.append("r.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        
        where_clause = "WHERE " + " AND ".join(where_clauses)
        
        cypher = """
            MATCH (c:GitCommit)-[r:TOUCHED]->()
            """ + where_clause + """
            WITH """ + time_format + """ AS bucket, count(DISTINCT c) AS commit_count, count(r) AS file_changes
            RETURN bucket, commit_count, file_changes
            ORDER BY bucket DESC
            LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, params)
            buckets = []
            
            for record in result:
                bucket_date = record["bucket"]
                if bucket_date:
                    buckets.append({
                        "bucket": bucket_date.isoformat(),
                        "commit_count": record["commit_count"] or 0,
                        "file_changes": record["file_changes"] or 0,
                        "granularity": granularity
                    })
            
            # Capture driver timings if possible
            try:
                summary = result.consume()
                self._last_query_metrics["commit_buckets"]["query_ms_driver"] = getattr(summary, "result_available_after", 0)
            except Exception:
                pass
            query_time = time.time() - start_time
            
            return {
                "buckets": buckets,
                "performance": {
                    "query_time_ms": round(query_time * 1000, 2),
                    "total_buckets": len(buckets)
                }
            }

    # -------------------- Metrics --------------------
    def get_metrics(self) -> Dict[str, object]:
        """Return simple engine metrics for telemetry."""
        hits = getattr(self, "_cache_hits", 0)
        misses = getattr(self, "_cache_misses", 0)
        denom = hits + misses
        hit_rate = (hits / denom) if denom else 0.0
        # average of subgraph query times
        avg_ms = 0.0
        try:
            samples = list(self._q_times_ms) if hasattr(self, "_q_times_ms") else []
            if samples:
                avg_ms = sum(samples) / len(samples)
        except Exception:
            avg_ms = 0.0
        return {
            "avg_query_time_ms": round(avg_ms, 2),
            "cache_hit_rate": round(hit_rate, 4),
            "cache_size": len(self._cache or {}),
            "query_samples": (len(self._q_times_ms) if hasattr(self, "_q_times_ms") else 0),
            "last_query_metrics": self._last_query_metrics,
        }

    def _cache_result(self, cache_key, result):
        """Cache a result with TTL."""
        try:
            import time
            self._cache[cache_key] = {
                "result": result,
                "timestamp": time.time()
            }
        except Exception:
            pass

    def _get_cached_result(self, cache_key):
        """Get cached result if not expired."""
        try:
            import time
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                if time.time() - cached["timestamp"] < self._cache_ttl:
                    return cached["result"]
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
        except Exception:
            pass
        return None

