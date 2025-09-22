from __future__ import annotations

from fastapi import APIRouter
from datetime import datetime
from ..app_state import driver, engine
from ..models import HealthResponse, StatsResponse

router = APIRouter()


@router.get("/api/v1/dev-graph/health", response_model=HealthResponse)
def health_check():
    try:
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            result.single()
        metrics = engine.get_metrics() if hasattr(engine, "get_metrics") else {}
        mem_mb = 0.0
        try:
            import psutil, os as _os
            mem_mb = psutil.Process(_os.getpid()).memory_info().rss / 1_000_000.0
        except Exception:
            mem_mb = 0.0
        return {
            "status": "healthy",
            "service": "dev-graph-api",
            "version": "1.0.0",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "avg_query_time_ms": metrics.get("avg_query_time_ms", 0),
            "cache_hit_rate": metrics.get("cache_hit_rate", 0),
            "memory_usage_mb": round(mem_mb, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "dev-graph-api",
            "version": "1.0.0",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


@router.get("/api/v1/dev-graph/stats", response_model=StatsResponse)
def get_stats():
    try:
        with driver.session() as session:
            record = session.run(
                """
                CALL {
                    MATCH (n)
                    RETURN count(n) AS total_nodes
                }
                CALL {
                    MATCH ()-[r]->()
                    RETURN count(r) AS total_relationships
                }
                CALL {
                    MATCH (c:GitCommit)
                    WHERE c.timestamp >= datetime() - duration('P7D')
                    RETURN count(c) AS recent_commits_7d
                }
                CALL {
                    MATCH (n)
                    UNWIND labels(n) AS label
                    RETURN label, count(*) AS cnt
                }
                WITH total_nodes, total_relationships, recent_commits_7d, collect({type: label, count: cnt}) AS node_type_list
                CALL {
                    MATCH ()-[r]->()
                    RETURN type(r) AS rel_type, count(r) AS cnt
                }
                RETURN total_nodes, total_relationships, recent_commits_7d,
                       node_type_list, collect({type: rel_type, count: cnt}) AS rel_type_list
                """
            ).single()

        if not record:
            raise RuntimeError("Failed to collect stats")

        total_nodes = record.get("total_nodes", 0) or 0
        total_relationships = record.get("total_relationships", 0) or 0
        recent_commits = record.get("recent_commits_7d", 0) or 0

        colors = ['blue', 'green', 'purple', 'orange', 'red', 'teal', 'pink', 'yellow']

        node_types = []
        for idx, entry in enumerate(sorted(record.get("node_type_list", []), key=lambda item: item.get("count", 0), reverse=True)):
            node_types.append({
                'type': entry.get('type'),
                'count': entry.get('count', 0),
                'color': colors[idx % len(colors)]
            })

        relationship_types = []
        for idx, entry in enumerate(sorted(record.get("rel_type_list", []), key=lambda item: item.get("count", 0), reverse=True)):
            relationship_types.append({
                'type': entry.get('type'),
                'count': entry.get('count', 0),
                'color': colors[idx % len(colors)]
            })

        return {
            "summary": {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships,
                "recent_commits_7d": recent_commits,
            },
            "node_types": node_types,
            "relationship_types": relationship_types,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {
            "summary": {"total_nodes": 0, "total_relationships": 0, "recent_commits_7d": 0},
            "node_types": [],
            "relationship_types": [],
            "timestamp": "2025-01-05T09:00:00Z",
            "error": f"Failed to retrieve stats: {str(e)}"
        }
