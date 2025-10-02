from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from ..app_state import driver
from ..web_utils import run_query, extract_id_from_node_data


router = APIRouter()


@router.get("/api/v1/dev-graph/nodes")
def get_nodes(node_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    if node_type:
        cypher = f"MATCH (n:{node_type}) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    else:
        cypher = "MATCH (n) RETURN n, labels(n) AS labels SKIP $offset LIMIT $limit"
    records = run_query(driver, cypher, limit=limit, offset=offset)

    nodes = []
    for r in records:
        node_data = r["n"]
        labels = r.get("labels", [])
        node_id = extract_id_from_node_data(node_data)

        if isinstance(node_data, dict):
            clean_data = {k: v for k, v in node_data.items() if v is not None}
        else:
            clean_data = {"raw": str(node_data)}

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

        nodes.append({"id": node_id, "labels": labels, "type": node_type_guess, **clean_data})
    return nodes


@router.get("/api/v1/dev-graph/nodes/count")
def count_nodes():
    rec = run_query(driver, "MATCH (n) RETURN count(n) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}


@router.get("/api/v1/dev-graph/relations")
def get_relations(start_id: Optional[int] = None, rel_type: Optional[str] = None, limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    cypher = "MATCH (a)-[r]->(b)"
    clauses = []
    if start_id is not None:
        clauses.append("id(a)=$sid")
    if rel_type:
        clauses.append("type(r)=$rt")
    if clauses:
        cypher += " WHERE " + " AND ".join(clauses)
    cypher += " RETURN a, r, b, type(r) AS rt, r.timestamp AS ts SKIP $offset LIMIT $limit"
    records = run_query(driver, cypher, sid=start_id, rt=rel_type, limit=limit, offset=offset)

    out = []
    for r in records:
        a_data, r_data, b_data = r["a"], r["r"], r["b"]
        r_type_explicit = r.get("rt")
        r_ts = r.get("ts")
        a_id = extract_id_from_node_data(a_data)
        b_id = extract_id_from_node_data(b_data)
        if a_id.isdigit() or (a_id.startswith('-') and a_id[1:].isdigit()):
            continue
        if b_id.isdigit() or (b_id.startswith('-') and b_id[1:].isdigit()):
            continue

        if r_type_explicit:
            r_type = r_type_explicit
        elif hasattr(r_data, 'type'):
            r_type = r_data.type
        elif isinstance(r_data, dict):
            r_type = r_data.get("type", "RELATES_TO")
        else:
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
                r_type = "TOUCHED"
            elif "USES" in r_str:
                r_type = "USES"
            elif "PROTOTYPED_IN" in r_str:
                r_type = "PROTOTYPED_IN"
            else:
                r_type = "RELATES_TO"

        rel_obj = {"from": a_id, "to": b_id, "type": r_type}
        if r_ts is not None:
            rel_obj["timestamp"] = r_ts
        out.append(rel_obj)
    return out


@router.get("/api/v1/dev-graph/relations/count")
def count_relations():
    rec = run_query(driver, "MATCH ()-[r]->() RETURN count(r) AS total")
    total = rec[0]["total"] if rec else 0
    return {"total": total}

