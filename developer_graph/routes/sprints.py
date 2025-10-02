from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from ..app_state import driver, sprint_mapper
from ..web_utils import extract_id_from_node_data


router = APIRouter()


@router.get("/api/v1/dev-graph/sprints")
def list_sprints(limit: int = Query(200, ge=1, le=1000)):
    with driver.session() as session:
        recs = session.run(
            "MATCH (s:Sprint) RETURN s ORDER BY toInteger(s.number) DESC LIMIT $limit",
            {"limit": limit},
        )
        out = []
        for r in recs:
            s = r.get("s") or {}
            out.append({"id": extract_id_from_node_data(s), **(s if isinstance(s, dict) else {})})
        return out


@router.get("/api/v1/dev-graph/sprint/map")
def sprint_map(number: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    if number and start_date and end_date:
        mapped = sprint_mapper.map_sprint_range(number=number, start_iso=start_date, end_iso=end_date)
        return {"number": number, "start_date": start_date, "end_date": end_date, "metrics": {"count": mapped.get("count", 0)}}
    return {"error": "Provide number, start_date, end_date"}


@router.get("/api/v1/dev-graph/sprints/{number}")
def sprint_details(number: str):
    with driver.session() as session:
        rec = session.run("MATCH (s:Sprint {number: $n}) RETURN s", {"n": number}).single()
        if not rec:
            return {"error": "Not found"}
        s = rec.get("s")
        return {"id": extract_id_from_node_data(s), **(s if isinstance(s, dict) else {})}


@router.get("/api/v1/dev-graph/sprints/{number}/subgraph")
def sprint_subgraph(number: str):
    cypher = (
        "MATCH (s:Sprint {number: $num}) "
        "OPTIONAL MATCH (s)-[:CONTAINS_DOC]->(d:Document) "
        "OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(c:Chunk) "
        "OPTIONAL MATCH (c)-[:MENTIONS]->(r:Requirement) "
        "RETURN s, collect(DISTINCT d) AS docs, collect(DISTINCT c) AS chunks, collect(DISTINCT r) AS reqs"
    )
    with driver.session() as session:
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

