from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from ..app_state import engine, driver
from ..models import WindowedSubgraphResponse, CommitsBucketsResponse


router = APIRouter()


@router.get("/api/v1/dev-graph/graph/subgraph", response_model=WindowedSubgraphResponse)
def get_windowed_subgraph(
    from_timestamp: Optional[str] = Query(None, description="Start timestamp (ISO format)"),
    to_timestamp: Optional[str] = Query(None, description="End timestamp (ISO format)"),
    types: Optional[str] = Query(None, description="Comma-separated node types to filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of edges to return"),
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

