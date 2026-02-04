from __future__ import annotations

from typing import Any, Dict, Optional
from neo4j import Driver
import hashlib
import os


def run_query(driver: Driver, cypher: str, **params):
    with driver.session() as session:
        result = session.run(cypher, params)
        return [r.data() for r in result]


def extract_id_from_node_data(node_data: Any) -> str:
    """Extract a meaningful, stable ID from node data.

    Mirrors logic originally in api.py to keep UI stable.
    """
    try:
        if isinstance(node_data, dict) and node_data.get('uid'):
            return str(node_data['uid'])
    except Exception:
        pass
    if hasattr(node_data, 'id'):
        return str(node_data.id)
    if not isinstance(node_data, dict):
        return str(hash(str(node_data)))[:8]

    if 'id' in node_data:
        return str(node_data['id'])
    if 'hash' in node_data:
        return str(node_data['hash'])
    if 'number' in node_data:
        return f"sprint-{node_data['number']}"
    if 'path' in node_data:
        base = os.path.splitext(os.path.basename(str(node_data['path'])))[0]
        h = hashlib.md5(str(node_data['path']).encode()).hexdigest()[:6]
        return str(node_data.get('uid') or f"doc-{base}-{h}")
    if 'description' in node_data:
        desc_hash = hashlib.md5(node_data['description'].encode()).hexdigest()[:8]
        return f"desc-{desc_hash}"
    return str(hash(str(node_data)))[:8]

