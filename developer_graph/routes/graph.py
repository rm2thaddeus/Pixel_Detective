from __future__ import annotations

from typing import Optional, Dict, Any, List
import re
from fastapi import APIRouter, Query, HTTPException
from ..app_state import engine, driver
from neo4j.graph import Node, Relationship, Path
from ..models import WindowedSubgraphResponse, CommitsBucketsResponse, CypherQueryRequest, CypherQueryResponse


router = APIRouter()


@router.get("/api/v1/dev-graph/graph/subgraph", response_model=WindowedSubgraphResponse)
def get_windowed_subgraph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    types: Optional[str] = Query(None, description="Comma-separated node types to filter"),
    limit: int = Query(1000, ge=1, le=50000, description="Maximum number of edges to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    include_counts: bool = Query(True, description="Include total node/edge counts in response")
):
    node_types = None
    if types:
        node_types = [t.strip() for t in types.split(",") if t.strip()]
    return engine.get_windowed_subgraph(
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        node_types=node_types,
        limit=limit,
        cursor=cursor,
        include_counts=include_counts,
    )


@router.get("/api/v1/dev-graph/commits/buckets", response_model=CommitsBucketsResponse)
def get_commits_buckets(
    granularity: str = Query("day", regex="^(day|week)$", description="Time granularity: 'day' or 'week'"),
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of buckets to return")
):
    try:
        return engine.get_commits_buckets(
            granularity=granularity,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=limit,
        )
    except Exception:
        # Fallback implementation if engine lacks this method
        with driver.session() as session:
            where_clauses = []
            params = {"limit": min(limit, 10000)}
            if from_timestamp:
                where_clauses.append("c.timestamp >= $from_ts")
                params["from_ts"] = from_timestamp
            if to_timestamp:
                where_clauses.append("c.timestamp <= $to_ts")
                params["to_ts"] = to_timestamp
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            if granularity == "week":
                date_trunc = "date(c.timestamp - duration('P' + toString(dayOfWeek(c.timestamp) - 1) + 'D'))"
            else:
                date_trunc = "date(c.timestamp)"
            cypher = f"""
                MATCH (c:GitCommit)
                {where_clause}
                WITH {date_trunc} AS bucket, count(c) AS commit_count
                OPTIONAL MATCH (c2:GitCommit)-[r:TOUCHED]->()
                WHERE {date_trunc} = bucket
                WITH bucket, commit_count, count(r) AS file_changes
                RETURN bucket, commit_count, file_changes
                ORDER BY bucket DESC
                LIMIT $limit
            """
            result = session.run(cypher, params)
            buckets = []
            for record in result:
                buckets.append({
                    "bucket": record["bucket"].isoformat() if hasattr(record["bucket"], "isoformat") else record["bucket"],
                    "commit_count": record["commit_count"],
                    "file_changes": record["file_changes"],
                })
            return {"granularity": granularity, "buckets": buckets}


@router.post("/api/v1/dev-graph/graph/cypher", response_model=CypherQueryResponse)
def run_cypher_query(payload: CypherQueryRequest) -> CypherQueryResponse:
    """Run a read-only Cypher query and materialize the result as a lightweight subgraph."""
    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if "return" not in query.lower():
        raise HTTPException(status_code=400, detail="Query must include a RETURN clause")

    forbidden = re.compile(r"(MERGE|CREATE|DELETE|DETACH|SET|DROP|REMOVE|CALL\s+dbms|CALL\s+db\.|LOAD\s+CSV|APOC\.)", re.IGNORECASE)
    if forbidden.search(query):
        raise HTTPException(status_code=400, detail="Only read-only queries are permitted in this endpoint")

    node_limit = payload.max_nodes or 500
    rel_limit = payload.max_relationships or 1000
    params = payload.parameters or {}

    nodes: Dict[str, Dict[str, Any]] = {}
    relationships: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    rows = 0
    limit_flags = {"nodes": False, "relationships": False}

    def _make_json_serializable(value: Any) -> Any:
        """Best-effort conversion of Neo4j values to JSON-serializable types.
        - Uses isoformat() when available (date/time types)
        - Recursively processes dicts and sequences
        - Falls back to str(value) for unknown objects
        """
        try:
            # Simple primitives pass through
            if value is None or isinstance(value, (bool, int, float, str)):
                return value
            # Datetime-like objects
            iso = getattr(value, "isoformat", None)
            if callable(iso):
                return iso()
            # Sequences
            if isinstance(value, (list, tuple, set)):
                return [_make_json_serializable(v) for v in value]
            # Mappings
            if isinstance(value, dict):
                return {k: _make_json_serializable(v) for k, v in value.items()}
        except Exception:
            pass
        # Fallback to string representation
        return str(value)

    def _collect(value: Any) -> None:
        if isinstance(value, Node):
            # Neo4j v5 prefers element_id; fall back to legacy id when unavailable
            try:
                node_id = str(getattr(value, "element_id", None) or value.id)
            except Exception:
                node_id = str(value.id)
            if node_id in nodes:
                return
            if len(nodes) >= node_limit:
                limit_flags["nodes"] = True
                return
            props = _make_json_serializable(dict(value))
            node_data: Dict[str, Any] = {
                "id": node_id,
                "labels": list(value.labels),
                "properties": props,
            }
            if value.labels:
                node_data["type"] = next(iter(value.labels))
            for candidate in ("name", "title", "path", "hash", "id"):
                display = props.get(candidate)
                if display:
                    node_data["display"] = display
                    break
            nodes[node_id] = node_data
        elif isinstance(value, Relationship):
            # Use element_id when available to avoid id() deprecation issues
            try:
                rel_id = str(getattr(value, "element_id", None) or value.id)
            except Exception:
                rel_id = str(value.id)
            if rel_id in relationships:
                return
            if len(relationships) >= rel_limit:
                limit_flags["relationships"] = True
                return
            relationships[rel_id] = {
                "id": rel_id,
                "from": str(getattr(value.start_node, "element_id", None) or value.start_node.id),
                "to": str(getattr(value.end_node, "element_id", None) or value.end_node.id),
                "type": value.type,
                "properties": _make_json_serializable(dict(value)),
            }
            _collect(value.start_node)
            _collect(value.end_node)
        elif isinstance(value, Path):
            for node in value.nodes:
                _collect(node)
            for rel in value.relationships:
                _collect(rel)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                _collect(item)
        elif isinstance(value, dict):
            for item in value.values():
                _collect(item)

    summary_dict: Dict[str, Any] = {}
    try:
        with driver.session() as session:
            result = session.run(query, params)
            for record in result:
                rows += 1
                for value in record.values():
                    _collect(value)
                if len(nodes) >= node_limit and len(relationships) >= rel_limit:
                    warnings.append("Result truncated because of node/relationship limits")
                    break
            summary = result.consume()
            summary_dict = {
                "rows": rows,
                "result_available_after_ms": getattr(summary, "result_available_after", None),
                "result_consumed_after_ms": getattr(summary, "result_consumed_after", None),
                "limits": {
                    "max_nodes": node_limit,
                    "max_relationships": rel_limit,
                    "nodes_truncated": limit_flags["nodes"],
                    "relationships_truncated": limit_flags["relationships"],
                },
            }
    except Exception as exc:  # pragma: no cover - relies on live database
        raise HTTPException(status_code=400, detail=f"Failed to execute query: {exc}") from exc

    if limit_flags["nodes"] and "nodes truncated" not in "".join(warnings):
        warnings.append(f"Returned node list truncated to {node_limit} entries")
    if limit_flags["relationships"] and "relationships truncated" not in "".join(warnings):
        warnings.append(f"Returned relationship list truncated to {rel_limit} entries")

    return CypherQueryResponse(
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        summary=summary_dict,
        warnings=warnings,
    )
