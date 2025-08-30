"""FastAPI service exposing Developer Graph queries."""
from __future__ import annotations

import os
import re
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase

# Phase 1 additions
from .git_history_service import GitHistoryService
from .temporal_engine import TemporalEngine
from .sprint_mapping import SprintMapper

app = FastAPI(title="Developer Graph API")

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

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
    if hasattr(node_data, 'id'):
        return str(node_data.id)
    if not isinstance(node_data, dict):
        return str(hash(str(node_data)))[:8]

    # Requirement-style explicit IDs
    if 'id' in node_data:
        return str(node_data['id'])

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
        return f"doc-{base}-{h}"

    # Description-only nodes
    if 'description' in node_data:
        import hashlib as _hashlib
        desc_hash = _hashlib.md5(node_data['description'].encode()).hexdigest()[:8]
        return f"desc-{desc_hash}"

    # Fallback
    return str(hash(str(node_data)))[:8]


@app.get("/api/v1/dev-graph/nodes")
def get_nodes(node_type: Optional[str] = None, limit: int = Query(200, le=1000)):
    if node_type:
        cypher = f"MATCH (n:{node_type}) RETURN n, labels(n) AS labels LIMIT $limit"
    else:
        cypher = "MATCH (n) RETURN n, labels(n) AS labels LIMIT $limit"
    records = run_query(cypher, limit=limit)
    
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
        node_type_guess = (
            "Requirement" if isinstance(node_data, dict) and str(node_data.get("id", "")).startswith(("FR-", "NFR-")) else
            "Sprint" if isinstance(node_data, dict) and "number" in node_data else
            "Document" if isinstance(node_data, dict) and "path" in node_data else
            "Goal" if isinstance(node_data, dict) and str(node_data.get("id", "")).startswith("goal-") else
            (labels[0] if labels else "Unknown")
        )

        nodes.append({
            "id": node_id,
            "labels": labels,
            "type": node_type_guess,
            **clean_data
        })
    
    return nodes


@app.get("/api/v1/dev-graph/relations")
def get_relations(start_id: Optional[int] = None, rel_type: Optional[str] = None, limit: int = Query(200, le=1000)):
    cypher = "MATCH (a)-[r]->(b)"
    clauses = []
    if start_id is not None:
        clauses.append("id(a)=$sid")
    if rel_type:
        clauses.append("type(r)=$rt")
    if clauses:
        cypher += " WHERE " + " AND ".join(clauses)
    cypher += " RETURN a,r,b LIMIT $limit"
    records = run_query(cypher, sid=start_id, rt=rel_type, limit=limit)
    
    out = []
    for r in records:
        a_data = r["a"]
        b_data = r["b"]
        r_data = r["r"]
        
        # Extract meaningful IDs
        a_id = extract_id_from_node_data(a_data)
        b_id = extract_id_from_node_data(b_data)
        
        # Skip links with hash-based IDs (these are usually invalid)
        if a_id.isdigit() or (a_id.startswith('-') and a_id[1:].isdigit()):
            continue
        if b_id.isdigit() or (b_id.startswith('-') and b_id[1:].isdigit()):
            continue
        
        # Extract relationship type
        if hasattr(r_data, 'type'):
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
            elif "TOUCHES" in r_str:
                r_type = "TOUCHES"
            elif "USES" in r_str:
                r_type = "USES"
            elif "PROTOTYPED_IN" in r_str:
                r_type = "PROTOTYPED_IN"
            else:
                r_type = "RELATES_TO"
        
        out.append({
            "from": a_id,
            "to": b_id,
            "type": r_type,
        })
    
    return out


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
def time_bounded_subgraph(start_commit: Optional[str] = None, end_commit: Optional[str] = None, limit: int = Query(500, le=2000)):
    """Time-bounded subgraph filtered by relationship timestamps derived from commits."""
    return _engine.time_bounded_subgraph(start_commit=start_commit, end_commit=end_commit, limit=limit)


@app.post("/api/v1/dev-graph/ingest/recent")
def ingest_recent_commits(limit: int = Query(100, le=1000)):
    _engine.apply_schema()
    count = _engine.ingest_recent_commits(limit=limit)
    return {"ingested": count}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
