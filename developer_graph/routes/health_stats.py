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
            # Simplified stats query to avoid timeouts
            result = session.run(
                """
                MATCH (n)
                WITH count(n) as total_nodes
                MATCH ()-[r]->()
                WITH total_nodes, count(r) as total_rels
                MATCH (c:GitCommit)
                WHERE c.timestamp >= datetime() - duration('P7D')
                RETURN total_nodes, total_rels, count(c) as recent_commits
                """
            ).single()
            
            # Get node type counts separately
            node_result = session.run(
                """
                MATCH (n)
                UNWIND labels(n) as label
                RETURN label as type, count(*) as count
                ORDER BY count DESC
                """
            ).data()
            
            # Get relationship type counts separately
            rel_result = session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
                """
            ).data()

            if not result:
                return {
                    "summary": {"total_nodes": 0, "total_relationships": 0, "recent_commits_7d": 0},
                    "node_types": [],
                    "relationship_types": [],
                    "timestamp": "2025-01-05T09:00:00Z"
                }

            total_nodes = result["total_nodes"] or 0
            total_rels = result["total_rels"] or 0
            recent_commits = result["recent_commits"] or 0

            node_type_counts = {}
            for stat in node_result:
                if stat and stat.get("type") and stat.get("count"):
                    node_type_counts[stat["type"]] = stat["count"]

            rel_type_counts = {}
            for stat in rel_result:
                if stat and stat.get("type") and stat.get("count"):
                    rel_type_counts[stat["type"]] = stat["count"]

            node_types = []
            colors = ['blue', 'green', 'purple', 'orange', 'red', 'teal', 'pink', 'yellow']
            sorted_node_types = sorted(node_type_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (node_type, count) in enumerate(sorted_node_types):
                node_types.append({'type': node_type, 'count': count, 'color': colors[i % len(colors)]})

            relationship_types = []
            sorted_rel_types = sorted(rel_type_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (rel_type, count) in enumerate(sorted_rel_types):
                relationship_types.append({'type': rel_type, 'count': count, 'color': colors[i % len(colors)]})

            return {
                "summary": {
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "recent_commits_7d": recent_commits,
                },
                "node_types": node_types,
                "relationship_types": relationship_types,
                "timestamp": "2025-01-05T09:00:00Z",
            }
    except Exception as e:
        return {
            "summary": {"total_nodes": 0, "total_relationships": 0, "recent_commits_7d": 0},
            "node_types": [],
            "relationship_types": [],
            "timestamp": "2025-01-05T09:00:00Z",
            "error": f"Failed to retrieve stats: {str(e)}"
        }

