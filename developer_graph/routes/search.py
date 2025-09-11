from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from ..app_state import driver
from ..web_utils import run_query


router = APIRouter()


@router.get("/api/v1/dev-graph/search")
def search(q: str):
    cypher = (
        "MATCH (n) WHERE any(prop in keys(n) WHERE "
        "CASE WHEN n[prop] IS NOT NULL AND NOT n[prop] IS LIST THEN toString(n[prop]) CONTAINS $q "
        "ELSE false END) "
        "RETURN n LIMIT 50"
    )
    records = run_query(driver, cypher, q=q)
    nodes = []
    for r in records:
        node_data = r["n"]
        clean_data = {k: v for k, v in node_data.items() if v is not None} if isinstance(node_data, dict) else {"raw": str(node_data)}
        nodes.append({"id": clean_data.get("uid") or clean_data.get("id") or clean_data.get("hash") or clean_data.get("path") or str(hash(str(clean_data)))[:8], **clean_data})
    return nodes


@router.get("/api/v1/dev-graph/search/fulltext")
def search_fulltext(q: str, label: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    index_map = {
        "File": "file_fulltext",
        "Requirement": "requirement_fulltext",
        "GitCommit": "commit_fulltext",
    }
    indexes = [index_map[label]] if label and label in index_map else list(index_map.values())
    out = []
    seen_ids = set()
    with driver.session() as session:
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
                nid = node_data.get("uid") if isinstance(node_data, dict) else None
                if not nid:
                    if isinstance(node_data, dict):
                        nid = node_data.get("id") or node_data.get("hash") or node_data.get("path")
                nid = nid or str(hash(str(node_data)))[:8]
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                clean_data = {k: v for k, v in node_data.items() if v is not None} if isinstance(node_data, dict) else {"raw": str(node_data)}
                out.append({"id": nid, **clean_data})
                if len(out) >= limit:
                    break
    return out

