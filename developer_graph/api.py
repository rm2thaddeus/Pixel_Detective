"""FastAPI service exposing Developer Graph queries."""
from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException
import logging
import os as _os_mod
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

# Phase 1 additions
from .git_history_service import GitHistoryService
from .temporal_engine import TemporalEngine
from .sprint_mapping import SprintMapper

app = FastAPI(title="Developer Graph API")

# Add CORS middleware to allow frontend access
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_env_origins = os.environ.get("CORS_ORIGINS")
_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
# Disable authentication for open source Neo4j - set password to None
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", None)  # No auth needed for open source

_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Initialize Git history service
REPO_PATH = os.environ.get("REPO_PATH", os.getcwd())
_git = GitHistoryService(REPO_PATH)
_engine = TemporalEngine(_driver, _git)
_sprint = SprintMapper(REPO_PATH)


def run_query(cypher: str, **params):
    with _driver.session() as session:
        result = session.run(cypher, params)
        return [r.data() for r in result]


def extract_id_from_node_data(node_data):
    """Extract a meaningful, stable ID from node data."""
    # Prefer explicit uid if present
    try:
        if isinstance(node_data, dict) and node_data.get('uid'):
            return str(node_data['uid'])
    except Exception:
        pass
    if hasattr(node_data, 'id'):
        return str(node_data.id)
    if not isinstance(node_data, dict):
        return str(hash(str(node_data)))[:8]

    # Requirement-style explicit IDs
    if 'id' in node_data:
        return str(node_data['id'])

    # Git commit nodes with hash
    if 'hash' in node_data:
        return str(node_data['hash'])

    # Sprint nodes with number
    if 'number' in node_data:
        return f"sprint-{node_data['number']}"

    # Document nodes with path
    if 'path' in node_data:
        import os as _os
        base = _os.path.splitext(_os.path.basename(str(node_data['path'])))[0]
        # include a short hash of the full path to avoid collisions
        import hashlib as _hashlib
        h = _hashlib.md5(str(node_data['path']).encode()).hexdigest()[:6]
        return str(node_data.get('uid') or f"doc-{base}-{h}")

    # Description-only nodes
    if 'description' in node_data:
        import hashlib as _hashlib
        desc_hash = _hashlib.md5(node_data['description'].encode()).hexdigest()[:8]
        return f"desc-{desc_hash}"

    # Fallback
    return str(hash(str(node_data)))[:8]


@app.get("/api/v1/dev-graph/nodes")
def get_nodes(node_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    if node_type:
        cypher = f"MATCH (n:{node_type}) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    else:
        cypher = "MATCH (n) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    records = run_query(cypher, limit=limit, offset=offset)
    
    nodes = []
    for r in records:
        node_data = r["n"]
        labels = r.get("labels", [])
        node_id = extract_id_from_node_data(node_data)
        
        # Convert node data to a clean dictionary
        if isinstance(node_data, dict):
            clean_data = {k: v for k, v in node_data.items() if v is not None}
        else:
            clean_data = {"raw": str(node_data)}
        
        # Derive a friendly node type for UI coloring
        # Prefer explicit labels over heuristics to avoid classifying File as Document
        label_set = set(labels or [])
        if "File" in label_set:
            node_type_guess = "File"
        elif "Commit" in label_set or "GitCommit" in label_set:
            node_type_guess = "Commit"
        elif isinstance(node_data, dict) and str(node_data.get("id", "")).startswith(("FR-", "NFR-")):
            node_type_guess = "Requirement"
        elif isinstance(node_data, dict) and "number" in node_data:
            node_type_guess = "Sprint"
        elif isinstance(node_data, dict) and "path" in node_data:
            node_type_guess = "Document"
        elif isinstance(node_data, dict) and str(node_data.get("id", "")).startswith("goal-"):
            node_type_guess = "Goal"
        else:
            node_type_guess = (labels[0] if labels else "Unknown")

        nodes.append({
            "id": node_id,
            "labels": labels,
            "type": node_type_guess,
            **clean_data
        })
    
    return nodes


@app.get("/api/v1/dev-graph/nodes/count")
def count_nodes():
    rec = run_query("MATCH (n) RETURN count(n) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}


@app.get("/api/v1/dev-graph/relations")
def get_relations(start_id: Optional[int] = None, rel_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    cypher = "MATCH (a)-[r]->(b)"
    clauses = []
    if start_id is not None:
        clauses.append("id(a)=$sid")
    if rel_type:
        clauses.append("type(r)=$rt")
    if clauses:
        cypher += " WHERE " + " AND ".join(clauses)
    # Also return relationship timestamp when present to aid timeline visualizations
    cypher += " RETURN a, r, b, type(r) AS rt, r.timestamp AS ts SKIP $offset LIMIT $limit"
    records = run_query(cypher, sid=start_id, rt=rel_type, limit=limit, offset=offset)
    
    out = []
    for r in records:
        a_data = r["a"]
        b_data = r["b"]
        r_data = r["r"]
        r_type_explicit = r.get("rt")
        r_ts = r.get("ts")
        
        # Extract meaningful IDs
        a_id = extract_id_from_node_data(a_data)
        b_id = extract_id_from_node_data(b_data)
        
        # Skip links with hash-based IDs (these are usually invalid)
        if a_id.isdigit() or (a_id.startswith('-') and a_id[1:].isdigit()):
            continue
        if b_id.isdigit() or (b_id.startswith('-') and b_id[1:].isdigit()):
            continue
        
        # Extract relationship type
        if r_type_explicit:
            r_type = r_type_explicit
        elif hasattr(r_data, 'type'):
            r_type = r_data.type
        elif isinstance(r_data, dict):
            r_type = r_data.get("type", "RELATES_TO")
        else:
            # Try to extract type from string representation
            r_str = str(r_data)
            if "PART_OF" in r_str:
                r_type = "PART_OF"
            elif "IMPLEMENTS" in r_str:
                r_type = "IMPLEMENTS"
            elif "DEPENDS_ON" in r_str:
                r_type = "DEPENDS_ON"
            elif "EVOLVES_FROM" in r_str:
                r_type = "EVOLVES_FROM"
            elif "REFERENCES" in r_str:
                r_type = "REFERENCES"
            elif "TOUCHED" in r_str or "TOUCHES" in r_str:
                r_type = "TOUCHES"
            elif "USES" in r_str:
                r_type = "USES"
            elif "PROTOTYPED_IN" in r_str:
                r_type = "PROTOTYPED_IN"
            else:
                r_type = "RELATES_TO"
        
        rel_obj = {
            "from": a_id,
            "to": b_id,
            "type": r_type,
        }
        if r_ts is not None:
            rel_obj["timestamp"] = r_ts
        out.append(rel_obj)
    
    return out


@app.get("/api/v1/dev-graph/relations/count")
def count_relations():
    rec = run_query("MATCH ()-[r]->() RETURN count(r) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}


@app.get("/api/v1/dev-graph/search")
def search(q: str):
    cypher = (
        "MATCH (n) WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $q) "
        "RETURN n LIMIT 50"
    )
    records = run_query(cypher, q=q)
    
    nodes = []
    for r in records:
        node_data = r["n"]
        node_id = extract_id_from_node_data(node_data)
        
        # Convert node data to a clean dictionary
        if isinstance(node_data, dict):
            clean_data = {k: v for k, v in node_data.items() if v is not None}
        else:
            clean_data = {"raw": str(node_data)}
        
        nodes.append({
            "id": node_id,
            **clean_data
        })
    
    return nodes


@app.get("/api/v1/dev-graph/search/fulltext")
def search_fulltext(q: str, label: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    """Full-text search across nodes using Neo4j full-text indexes.

    - When `label` is provided, restricts to one index (File, Requirement, GitCommit).
    - Otherwise queries all available indexes and merges results.
    """
    index_map = {
        "File": "file_fulltext",
        "Requirement": "requirement_fulltext",
        "GitCommit": "commit_fulltext",
    }
    indexes = []
    if label and label in index_map:
        indexes = [index_map[label]]
    else:
        indexes = list(index_map.values())

    out = []
    seen_ids = set()
    with _driver.session() as session:
        for idx in indexes:
            try:
                recs = session.run(
                    "CALL db.index.fulltext.queryNodes($idx, $q) YIELD node, score RETURN node AS n, score LIMIT $limit",
                    {"idx": idx, "q": q, "limit": limit},
                )
            except Exception:
                continue
            for r in recs:
                node_data = r.get("n")
                node_id = extract_id_from_node_data(node_data)
                if node_id in seen_ids:
                    continue
                seen_ids.add(node_id)
                clean_data = {k: v for k, v in node_data.items() if v is not None} if isinstance(node_data, dict) else {"raw": str(node_data)}
                out.append({"id": node_id, **clean_data})
                if len(out) >= limit:
                    break
    return out


# -------------------- Phase 1: New Endpoints --------------------

@app.get("/api/v1/dev-graph/commits")
def list_commits(limit: int = Query(100, le=1000), path: Optional[str] = None):
    """List recent commits, optionally filtered to a path (follows renames)."""
    return _git.get_commits(limit=limit, path=path)


@app.get("/api/v1/dev-graph/commit/{commit_hash}")
def commit_details(commit_hash: str):
    details = _git.get_commit(commit_hash)
    if details is None:
        return {"error": "Commit not found"}
    return details


@app.get("/api/v1/dev-graph/file/history")
def file_history(path: str, limit: int = Query(200, le=2000)):
    return _git.get_file_history(path, limit=limit)


@app.get("/api/v1/dev-graph/subgraph/by-commits")
def time_bounded_subgraph(start_commit: Optional[str] = None, end_commit: Optional[str] = None, limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
    """Time-bounded subgraph filtered by relationship timestamps derived from commits."""
    return _engine.time_bounded_subgraph(start_commit=start_commit, end_commit=end_commit, limit=limit, offset=offset)


@app.post("/api/v1/dev-graph/ingest/recent")
def ingest_recent_commits(limit: int = Query(100, ge=1, le=5000)):
    try:
        # Basic environment validation
        if not _os_mod.path.isdir(REPO_PATH):
            raise RuntimeError(f"Invalid REPO_PATH: {REPO_PATH}")
        _engine.apply_schema()
        count = _engine.ingest_recent_commits(limit=limit)
        return {"ingested": count}
    except Exception as e:
        logging.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dev-graph/sprint/map")
def map_sprint(number: str, start_iso: str, end_iso: str):
    return _sprint.map_sprint_range(number=number, start_iso=start_iso, end_iso=end_iso)


# -------------------- Phase 2: Evolution APIs --------------------

@app.get("/api/v1/dev-graph/evolution/requirement/{req_id}")
def requirement_evolution(req_id: str, limit: int = Query(500, le=2000)):
    return _engine.build_evolution_timeline_for_requirement(req_id=req_id, limit=limit)


@app.get("/api/v1/dev-graph/evolution/file")
def file_evolution(path: str, limit: int = Query(500, le=2000)):
    return _engine.build_evolution_timeline_for_file(path=path, limit=limit)


@app.get("/api/v1/dev-graph/sprints")
def list_sprints():
    base = _os_mod.path.join(_os_mod.getcwd(), "docs", "sprints")
    out = []
    if not _os_mod.path.isdir(base):
        return out
    # Gather sprint directories like sprint-01, sprint-10, etc.
    for name in sorted(_os_mod.listdir(base)):
        if not name.startswith("sprint-"):
            continue
        number = name.split("-", 1)[1]
        sprint_dir = _os_mod.path.join(base, name)
        # Try to find dates from planning file
        start_iso = None
        end_iso = None
        planning = _os_mod.path.join(base, "planning", "SPRINT_STATUS.md")
        if _os_mod.path.isfile(planning):
            try:
                with open(planning, "r", encoding="utf-8") as f:
                    content = f.read()
                # naive parse: look for "Sprint {number}" lines and capture Start/End
                import re as _re
                # Example: "Sprint 10" followed by Start Date: YYYY-MM-DD
                pat = _re.compile(rf"Sprint\s*{number}.*?Start Date\W*:?\s*([0-9-]{8,10}).*?End Date\W*:?\s*([0-9-]{8,10})", _re.IGNORECASE | _re.DOTALL)
                m = pat.search(content)
                if m:
                    start_iso = m.group(1)
                    end_iso = m.group(2)
            except Exception:
                pass
        # Fallback: two-week window ending today
        from datetime import datetime, timedelta
        if not start_iso or not end_iso:
            end_iso = datetime.utcnow().date().isoformat()
            start_iso = (datetime.utcnow().date() - timedelta(days=14)).isoformat()
        mapped = _sprint.map_sprint_range(number=str(number), start_iso=start_iso, end_iso=end_iso)
        # add basic metrics stub
        out.append({
            "number": number,
            "start_date": start_iso,
            "end_date": end_iso,
            "commit_range": {"start": mapped.get("commit_range", [None, None])[0], "end": mapped.get("commit_range", [None, None])[-1] if mapped.get("commit_range") else None},
            "metrics": {
                "count": mapped.get("count", 0),
            }
        })
    return out


@app.get("/api/v1/dev-graph/sprints/{number}")
def sprint_details(number: str):
    """Return sprint details including commit range and basic metrics.

    Dates are resolved from planning doc when possible, with fallback window.
    """
    base = _os_mod.path.join(_os_mod.getcwd(), "docs", "sprints")
    start_iso = None
    end_iso = None
    planning = _os_mod.path.join(base, "planning", "SPRINT_STATUS.md")
    if _os_mod.path.isfile(planning):
        try:
            with open(planning, "r", encoding="utf-8") as f:
                content = f.read()
            import re as _re
            pat = _re.compile(rf"Sprint\s*{number}.*?Start Date\W*:?\s*([0-9-]{8,10}).*?End Date\W*:?\s*([0-9-]{8,10})", _re.IGNORECASE | _re.DOTALL)
            m = pat.search(content)
            if m:
                start_iso = m.group(1)
                end_iso = m.group(2)
        except Exception:
            pass
    from datetime import datetime, timedelta
    if not start_iso or not end_iso:
        end_iso = datetime.utcnow().date().isoformat()
        start_iso = (datetime.utcnow().date() - timedelta(days=14)).isoformat()
    mapped = _sprint.map_sprint_range(number=str(number), start_iso=start_iso, end_iso=end_iso)
    return {
        "number": number,
        "start_date": start_iso,
        "end_date": end_iso,
        "commit_range": {
            "start": (mapped.get("commit_range") or [None, None])[0],
            "end": (mapped.get("commit_range") or [None, None])[-1] if mapped.get("commit_range") else None,
        },
        "metrics": {"count": mapped.get("count", 0)},
    }


@app.get("/api/v1/dev-graph/sprints/{number}/subgraph")
def sprint_subgraph(number: str):
    """Return a hierarchical subgraph for a sprint: Sprint->Docs->Chunks->Requirements.

    This endpoint is independent of timestamps to ensure deterministic sprint structure.
    """
    cypher = (
        "MATCH (s:Sprint {number: $num}) "
        "OPTIONAL MATCH (s)-[:CONTAINS_DOC]->(d:Document) "
        "OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:Chunk) "
        "OPTIONAL MATCH (c)-[:MENTIONS]->(r:Requirement) "
        "RETURN s, collect(DISTINCT d) AS docs, collect(DISTINCT c) AS chunks, collect(DISTINCT r) AS reqs"
    )
    with _driver.session() as session:
        rec = session.run(cypher, {"num": number}).single()
        if not rec:
            return {"nodes": [], "edges": []}
        s = rec.get("s") or {}
        docs = rec.get("docs") or []
        chunks = rec.get("chunks") or []
        reqs = rec.get("reqs") or []

        def _id(n):
            return extract_id_from_node_data(n)

        nodes = []
        seen = set()
        def add_node(n):
            nid = _id(n)
            if nid in seen:
                return
            seen.add(nid)
            if isinstance(n, dict):
                nodes.append({"id": nid, **n})
            else:
                nodes.append({"id": nid, "raw": str(n)})

        add_node(s)
        for d in docs: add_node(d)
        for c in chunks: add_node(c)
        for r in reqs: add_node(r)

        # Now get edges explicitly to preserve relations
        edges = []
        rels_cypher = (
            "MATCH (s:Sprint {number: $num})-[:CONTAINS_DOC]->(d:Document) "
            "RETURN 'CONTAINS_DOC' AS t, s AS a, d AS b "
            "UNION ALL "
            "MATCH (d:Document)<-[:CONTAINS_DOC]-(s:Sprint {number: $num}), (d)-[:CONTAINS_CHUNK]->(c:Chunk) "
            "RETURN 'CONTAINS_CHUNK' AS t, d AS a, c AS b "
            "UNION ALL "
            "MATCH (d:Document)<-[:CONTAINS_DOC]-(s:Sprint {number: $num}), (d)-[:CONTAINS_CHUNK]->(c:Chunk)-[:MENTIONS]->(r:Requirement) "
            "RETURN 'MENTIONS' AS t, c AS a, r AS b"
        )
        result = session.run(rels_cypher, {"num": number})
        for r in result:
            a = r.get("a")
            b = r.get("b")
            t = r.get("t")
            edges.append({"from": _id(a), "to": _id(b), "type": str(t)})

        return {"nodes": nodes, "edges": edges}


# -------------------- Phase 4: Performance Primitives --------------------

@app.get("/api/v1/dev-graph/graph/subgraph")
def get_windowed_subgraph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    types: Optional[str] = Query(None, description="Comma-separated node types to filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of edges to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor")
):
    """Get a time-bounded subgraph with pagination and type filtering.
    
    Returns nodes and edges within the time window, with performance metrics.
    SLO: <300ms for 30-day subgraph on local data.
    """
    node_types = None
    if types:
        node_types = [t.strip() for t in types.split(",") if t.strip()]
    
    return _engine.get_windowed_subgraph(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        node_types=node_types,
        limit=limit,
        cursor=cursor
    )


@app.get("/api/v1/dev-graph/commits/buckets")
def get_commits_buckets(
    granularity: str = Query("day", regex="^(day|week)$", description="Time granularity: 'day' or 'week'"),
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of buckets to return")
):
    """Get commit counts grouped by time buckets for timeline density and caching.
    
    Returns commit activity aggregated by day or week for timeline visualization.
    """
    return _engine.get_commits_buckets(
        granularity=granularity,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        limit=limit
    )


# -------------------- Analytics Endpoints --------------------

@app.get("/api/v1/analytics/activity")
def analytics_activity(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)")
):
    """Return basic activity metrics for a time window.

    - commit_count (by GitCommit.timestamp)
    - file_changes (by TOUCHED.timestamp)
    - unique_authors (by GitCommit.author)
    """
    with _driver.session() as session:
        # Commits by time
        where_c = []
        params = {}
        if from_timestamp:
            where_c.append("c.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where_c.append("c.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        clause_c = f"WHERE {' AND '.join(where_c)}" if where_c else ""

        commits_cypher = f"""
            MATCH (c:GitCommit)
            {clause_c}
            RETURN count(c) AS commit_count, count(DISTINCT c.author) AS unique_authors
        """
        rec_c = session.run(commits_cypher, params).single()
        commit_count = rec_c["commit_count"] if rec_c else 0
        unique_authors = rec_c["unique_authors"] if rec_c else 0

        # File changes by TOUCHED relationships
        where_t = ["r.timestamp IS NOT NULL"]
        if from_timestamp:
            where_t.append("r.timestamp >= $from_ts")
        if to_timestamp:
            where_t.append("r.timestamp <= $to_ts")
        clause_t = f"WHERE {' AND '.join(where_t)}"
        touched_cypher = f"""
            MATCH ()-[r:TOUCHED]->()
            {clause_t}
            RETURN count(r) AS file_changes
        """
        rec_t = session.run(touched_cypher, params).single()
        file_changes = rec_t["file_changes"] if rec_t else 0

        return {
            "commit_count": commit_count,
            "file_changes": file_changes,
            "unique_authors": unique_authors,
            "window": {"from": from_timestamp, "to": to_timestamp}
        }


@app.get("/api/v1/analytics/graph")
def analytics_graph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format) for edge counts"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format) for edge counts"),
):
    """Return graph metrics: node counts by label and edge counts by type.

    Edge counts are optionally time-bounded by relationship.timestamp.
    """
    with _driver.session() as session:
        # Node counts by type
        nodes_cypher = (
            "RETURN "+
            "[(MATCH (n:Sprint) RETURN count(n))][0] AS sprints, "+
            "[(MATCH (n:Document) RETURN count(n))][0] AS documents, "+
            "[(MATCH (n:Chunk) RETURN count(n))][0] AS chunks, "+
            "[(MATCH (n:Requirement) RETURN count(n))][0] AS requirements, "+
            "[(MATCH (n:File) RETURN count(n))][0] AS files, "+
            "[(MATCH (n:GitCommit) RETURN count(n))][0] AS commits"
        )
        rec_n = session.run(nodes_cypher).single()
        nodes = {
            "sprints": rec_n.get("sprints", 0) if rec_n else 0,
            "documents": rec_n.get("documents", 0) if rec_n else 0,
            "chunks": rec_n.get("chunks", 0) if rec_n else 0,
            "requirements": rec_n.get("requirements", 0) if rec_n else 0,
            "files": rec_n.get("files", 0) if rec_n else 0,
            "commits": rec_n.get("commits", 0) if rec_n else 0,
        }

        # Edge counts by type with optional time window
        where = ["r.timestamp IS NOT NULL"]
        params = {}
        if from_timestamp:
            where.append("r.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where.append("r.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        clause = f"WHERE {' AND '.join(where)}"

        def count_rel(rel_type: str) -> int:
            q = f"MATCH ()-[r:{rel_type}]->() {clause} RETURN count(r) AS c"
            rec = session.run(q, params).single()
            return rec["c"] if rec else 0

        edges = {
            "TOUCHED": count_rel("TOUCHED"),
            "IMPLEMENTS": count_rel("IMPLEMENTS"),
            "EVOLVES_FROM": count_rel("EVOLVES_FROM"),
            "REFACTORED_TO": count_rel("REFACTORED_TO"),
            "DEPRECATED_BY": count_rel("DEPRECATED_BY"),
            "MENTIONS": count_rel("MENTIONS"),
            "CONTAINS_CHUNK": count_rel("CONTAINS_CHUNK"),
            "CONTAINS_DOC": count_rel("CONTAINS_DOC"),
        }

        return {"nodes": nodes, "edges": edges, "window": {"from": from_timestamp, "to": to_timestamp}}


@app.get("/api/v1/analytics/traceability")
def analytics_traceability(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format) for traceability window"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format) for traceability window"),
):
    """Return traceability metrics for requirements.

    - total_requirements
    - implemented_requirements (has at least one IMPLEMENTS)
    - unimplemented_requirements
    - avg_files_per_requirement (average IMPLEMENTS targets per requirement)
    Optionally confined to a time window based on IMPLEMENTS.timestamp.
    """
    with _driver.session() as session:
        # Total requirements
        total_rec = session.run("MATCH (r:Requirement) RETURN count(r) AS c").single()
        total = total_rec["c"] if total_rec else 0

        # Implemented requirements (optionally windowed)
        where = []
        params = {}
        if from_timestamp:
            where.append("rel.timestamp >= $from_ts")
            params["from_ts"] = from_timestamp
        if to_timestamp:
            where.append("rel.timestamp <= $to_ts")
            params["to_ts"] = to_timestamp
        clause = ("WHERE " + " AND ".join(where)) if where else ""

        impl_q = f"""
            MATCH (r:Requirement)-[rel:IMPLEMENTS]->(:File)
            {clause}
            RETURN count(DISTINCT r) AS c
        """
        impl_rec = session.run(impl_q, params).single()
        implemented = impl_rec["c"] if impl_rec else 0

        # Average files per requirement (windowed on rel timestamp when provided)
        avg_q = f"""
            MATCH (r:Requirement)
            OPTIONAL MATCH (r)-[rel:IMPLEMENTS]->(:File)
            {clause}
            WITH r, count(rel) AS file_links
            RETURN coalesce(avg(file_links), 0) AS avg_files_per_requirement
        """
        avg_rec = session.run(avg_q, params).single()
        avg_files = avg_rec["avg_files_per_requirement"] if avg_rec else 0

        return {
            "total_requirements": total,
            "implemented_requirements": implemented,
            "unimplemented_requirements": max(total - implemented, 0),
            "avg_files_per_requirement": avg_files,
            "window": {"from": from_timestamp, "to": to_timestamp}
        }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
