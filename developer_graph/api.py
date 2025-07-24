"""FastAPI service exposing Developer Graph queries."""
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, Query
from neo4j import GraphDatabase

app = FastAPI(title="Developer Graph API")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def run_query(cypher: str, **params):
    with _driver.session() as session:
        result = session.run(cypher, params)
        return [r.data() for r in result]


@app.get("/api/v1/dev-graph/nodes")
def get_nodes(node_type: Optional[str] = None, limit: int = Query(50, le=100)):
    if node_type:
        cypher = f"MATCH (n:{node_type}) RETURN n LIMIT $limit"
    else:
        cypher = "MATCH (n) RETURN n LIMIT $limit"
    records = run_query(cypher, limit=limit)
    return [{"id": r["n"].id, **r["n"]._properties} for r in records]


@app.get("/api/v1/dev-graph/relations")
def get_relations(start_id: Optional[int] = None, rel_type: Optional[str] = None, limit: int = Query(50, le=100)):
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
        out.append({
            "from": r["a"].id,
            "to": r["b"].id,
            "type": r["r"].type,
        })
    return out


@app.get("/api/v1/dev-graph/search")
def search(q: str):
    cypher = (
        "MATCH (n) WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $q) "
        "RETURN n LIMIT 50"
    )
    records = run_query(cypher, q=q)
    return [{"id": r["n"].id, **r["n"]._properties} for r in records]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
