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

    def apply_schema(self) -> None:
        apply_schema(self.driver)

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
            f"WHERE {' AND '.join(where_clauses)} "
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
        cursor: Optional[str] = None
    ) -> Dict[str, object]:
        """Get a time-bounded subgraph with pagination and type filtering.
        
        Returns nodes and edges within the time window, with counts and pagination info.
        """
        import time
        start_time = time.time()
        
        # Build WHERE clause for time bounds
        where_clauses = ["r.timestamp IS NOT NULL"]
        params = {"limit": max(1, min(limit, 5000))}
        
        if from_timestamp:
            where_clauses.append("r.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where_clauses.append("r.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
            
        # Add node type filtering if specified
        node_type_filter = ""
        if node_types:
            type_conditions = [f"'{t}' IN labels(a)" for t in node_types]
            type_conditions.extend([f"'{t}' IN labels(b)" for t in node_types])
            where_clauses.append(f"({' OR '.join(type_conditions)})")
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Get total counts first
        count_cypher = f"""
            MATCH (a)-[r]->(b) {where_clause}
            RETURN count(DISTINCT a) + count(DISTINCT b) AS node_count, count(r) AS edge_count
        """
        
        with self.driver.session() as session:
            count_result = session.run(count_cypher, params).single()
            total_nodes = count_result["node_count"] if count_result else 0
            total_edges = count_result["edge_count"] if count_result else 0
            
            # Get paginated results
            offset = 0
            if cursor:
                try:
                    offset = int(cursor)
                except ValueError:
                    offset = 0
            
            params["offset"] = offset
            
            # Main query with pagination
            main_cypher = f"""
                MATCH (a)-[r]->(b) {where_clause}
                RETURN DISTINCT a, labels(a) AS a_labels, b, labels(b) AS b_labels, r, type(r) AS rel_type, r.timestamp AS ts
                ORDER BY ts DESC
                SKIP $offset LIMIT $limit
            """
            
            result = session.run(main_cypher, params)
            
            # Process results
            nodes_seen = {}
            edges = []
            
            for rec in result:
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
                            return f"sprint-{node_data['number']}"
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
                    "properties": {k: v for k, v in r.items() if v is not None} if isinstance(r, dict) else {}
                })
            
            # Calculate next cursor
            next_cursor = None
            if len(edges) == limit and (offset + limit) < total_edges:
                next_cursor = str(offset + limit)
            
            query_time = time.time() - start_time
            
            return {
                "nodes": list(nodes_seen.values()),
                "edges": edges,
                "pagination": {
                    "total_nodes": total_nodes,
                    "total_edges": total_edges,
                    "returned_nodes": len(nodes_seen),
                    "returned_edges": len(edges),
                    "limit": limit,
                    "offset": offset,
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
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}"
        
        cypher = f"""
            MATCH (c:GitCommit)-[r:TOUCHED]->()
            {where_clause}
            WITH {time_format} AS bucket, count(DISTINCT c) AS commit_count, count(r) AS file_changes
            RETURN bucket, commit_count, file_changes
            ORDER BY bucket DESC
            LIMIT $limit
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, params)
            buckets = []
            
            for rec in result:
                buckets.append({
                    "bucket": rec["bucket"],
                    "commit_count": rec["commit_count"],
                    "file_changes": rec["file_changes"],
                    "granularity": granularity
                })
            
            query_time = time.time() - start_time
            
            return {
                "buckets": buckets,
                "performance": {
                    "query_time_ms": round(query_time * 1000, 2),
                    "granularity": granularity,
                    "total_buckets": len(buckets)
                }
            }

