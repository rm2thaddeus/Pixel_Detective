from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from ..app_state import driver, git, engine
from ..schema.temporal_schema import get_commit_sequence, get_commit_timeline
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/v1/dev-graph/commits")
def list_commits(limit: int = Query(100, le=1000), path: Optional[str] = None):
    commits = git.get_commits(limit=limit, path=path)
    return {"value": commits, "Count": len(commits)}


@router.get("/api/v1/dev-graph/evolution/timeline")
def get_evolution_timeline(limit: int = Query(50, ge=1, le=200), max_files_per_commit: int = Query(50, ge=1, le=200)):
    try:
        with driver.session() as session:
            commits_query = """
                MATCH (c:GitCommit)
                OPTIONAL MATCH (c)-[r:TOUCHED]->(f:File)
                WITH c, collect({
                    path: f.path,
                    action: CASE 
                        WHEN coalesce(r.change_type, 'M') = 'A' THEN 'created'
                        WHEN coalesce(r.change_type, 'M') = 'M' THEN 'modified' 
                        WHEN coalesce(r.change_type, 'M') = 'D' THEN 'deleted'
                        ELSE 'modified'
                    END,
                    size: coalesce(r.lines_after, f.loc, 0),
                    type: CASE
                        WHEN f.path CONTAINS '.py' OR f.path CONTAINS '.js' OR f.path CONTAINS '.ts' THEN 'code'
                        WHEN f.path CONTAINS '.md' OR f.path CONTAINS '.txt' THEN 'document'
                        WHEN f.path CONTAINS '.json' OR f.path CONTAINS '.yaml' OR f.path CONTAINS '.yml' THEN 'config'
                        ELSE 'other'
                    END
                }) as files
                RETURN c.hash as hash, c.timestamp as timestamp, c.message as message, c.author as author, 
                       files[0..$max_files_per_commit] as files
                ORDER BY c.timestamp ASC
                LIMIT $limit
            """
            commits_result = session.run(commits_query, limit=limit, max_files_per_commit=max_files_per_commit)
            commits = []
            for record in commits_result:
                commit_data = {
                    "hash": record["hash"],
                    "timestamp": record["timestamp"],
                    "message": record["message"],
                    "author": record["author"],
                    "files": [f for f in record["files"] if f["path"]],
                }
                commits.append(commit_data)

            lifecycle_query = """
                MATCH (f:File)
                OPTIONAL MATCH (c:GitCommit)-[r:TOUCHED]->(f)
                WITH f, collect({
                    commit_hash: c.hash,
                    timestamp: c.timestamp,
                    action: CASE 
                        WHEN coalesce(r.change_type, 'M') = 'A' THEN 'created'
                        WHEN coalesce(r.change_type, 'M') = 'M' THEN 'modified'
                        WHEN coalesce(r.change_type, 'M') = 'D' THEN 'deleted'
                        ELSE 'modified'
                    END,
                    size: coalesce(r.lines_after, f.loc, 0)
                }) as evolution_history
                WHERE size(evolution_history) > 0
                WITH f, evolution_history
                ORDER BY f.path
                RETURN f.path as path,
                       head([ev IN evolution_history | ev.timestamp]) as created_at,
                       head([ev IN evolution_history WHERE ev.action = 'deleted' | ev.timestamp]) as deleted_at,
                       size([ev IN evolution_history WHERE ev.action = 'modified' | ev]) as modifications,
                       0 as current_size,
                       CASE
                           WHEN f.path CONTAINS '.py' OR f.path CONTAINS '.js' OR f.path CONTAINS '.ts' THEN 'code'
                           WHEN f.path CONTAINS '.md' OR f.path CONTAINS '.txt' THEN 'document'
                           WHEN f.path CONTAINS '.json' OR f.path CONTAINS '.yaml' OR f.path CONTAINS '.yml' THEN 'config'
                           ELSE 'other'
                       END as type,
                       evolution_history
                LIMIT 1000
            """
            lifecycle_result = session.run(lifecycle_query)
            file_lifecycles = []
            for record in lifecycle_result:
                evolution_history = []
                for ev in record["evolution_history"]:
                    if ev and ev.get("timestamp"):
                        evolution_history.append({
                            "commit_hash": ev.get("commit_hash") or "unknown",
                            "timestamp": ev["timestamp"],
                            "action": ev.get("action") or "modified",
                            "size": ev.get("size") or 0,
                            "color": "#3b82f6" if ev.get("action") == "created" else "#10b981" if ev.get("action") == "modified" else "#ef4444",
                        })
                evolution_history.sort(key=lambda x: x["timestamp"])
                lifecycle_data = {
                    "path": record["path"],
                    "created_at": record["created_at"],
                    "deleted_at": record["deleted_at"],
                    "modifications": record["modifications"] or 0,
                    "current_size": record["current_size"] or 0,
                    "type": record["type"],
                    "evolution_history": evolution_history,
                }
                file_lifecycles.append(lifecycle_data)

            return {
                "commits": commits,
                "file_lifecycles": file_lifecycles,
                "total_commits": len(commits),
                "total_files": len(file_lifecycles),
            }
    except Exception as e:
        logger.error(f"Failed to get evolution timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/commit/{commit_hash}")
def commit_details(commit_hash: str):
    """Return commit details along with per-file diffs (additions, deletions, lines_after)."""
    try:
        with driver.session() as session:
            rec = session.run(
                """
                MATCH (c:GitCommit {hash: $hash})
                OPTIONAL MATCH (c)-[r:TOUCHED]->(f:File)
                RETURN c.hash AS hash, c.message AS message, c.author AS author, c.timestamp AS timestamp,
                       collect({path: f.path, additions: r.additions, deletions: r.deletions, lines_after: coalesce(r.lines_after, f.loc, 0), change_type: r.change_type}) AS files
                """,
                {"hash": commit_hash},
            ).single()
            if not rec:
                return {"error": "Commit not found"}
            return {
                "hash": rec["hash"],
                "message": rec["message"],
                "author": rec["author"],
                "timestamp": rec["timestamp"],
                "files": [f for f in rec["files"] if f.get("path")],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/file/history")
def file_history(path: str, limit: int = Query(200, le=2000)):
    return git.get_file_history(path, limit=limit)


@router.get("/api/v1/dev-graph/subgraph/by-commits")
def time_bounded_subgraph(start_commit: Optional[str] = None, end_commit: Optional[str] = None, limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
    return engine.time_bounded_subgraph(start_commit=start_commit, end_commit=end_commit, limit=limit, offset=offset)


# Phase 2: Commit ordering endpoints
@router.get("/api/v1/dev-graph/commits/sequence")
def get_commit_sequence_endpoint(
    start_hash: str = Query(..., description="Hash of the starting commit"),
    direction: str = Query("next", description="Direction: 'next' for forward, 'prev' for backward"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of commits to return")
):
    """Get a sequence of commits in chronological order using NEXT_COMMIT/PREV_COMMIT relationships.
    
    Phase 2: Commit ordering for timeline navigation.
    """
    try:
        with driver.session() as session:
            commits = session.execute_read(get_commit_sequence, start_hash, direction, limit)
            return {
                "success": True,
                "commits": commits,
                "count": len(commits),
                "direction": direction,
                "start_hash": start_hash
            }
    except Exception as e:
        logger.error(f"Failed to get commit sequence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/commits/timeline")
def get_commit_timeline_endpoint(
    from_timestamp: str = Query(..., description="Start timestamp (ISO format)"),
    to_timestamp: str = Query(..., description="End timestamp (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of commits to return")
):
    """Get commits in a time window with ordering relationships.
    
    Phase 2: Timeline view with commit ordering for UI navigation.
    """
    try:
        with driver.session() as session:
            commits = session.execute_read(get_commit_timeline, from_timestamp, to_timestamp, limit)
            return {
                "success": True,
                "commits": commits,
                "count": len(commits),
                "from_timestamp": from_timestamp,
                "to_timestamp": to_timestamp
            }
    except Exception as e:
        logger.error(f"Failed to get commit timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/commits/next/{commit_hash}")
def get_next_commit(commit_hash: str):
    """Get the next commit in chronological order.
    
    Phase 2: Simple navigation to next commit.
    """
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:GitCommit {hash: $commit_hash})-[:NEXT_COMMIT]->(next:GitCommit)
                RETURN next.hash as hash,
                       next.message as message,
                       next.author as author,
                       next.timestamp as timestamp
            """, commit_hash=commit_hash)
            
            record = result.single()
            if record:
                return {
                    "success": True,
                    "next_commit": {
                        "hash": record["hash"],
                        "message": record["message"],
                        "author": record["author"],
                        "timestamp": record["timestamp"]
                    }
                }
            else:
                return {
                    "success": True,
                    "next_commit": None,
                    "message": "No next commit found (this is the latest commit)"
                }
    except Exception as e:
        logger.error(f"Failed to get next commit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/dev-graph/commits/prev/{commit_hash}")
def get_prev_commit(commit_hash: str):
    """Get the previous commit in chronological order.
    
    Phase 2: Simple navigation to previous commit.
    """
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (c:GitCommit {hash: $commit_hash})-[:PREV_COMMIT]->(prev:GitCommit)
                RETURN prev.hash as hash,
                       prev.message as message,
                       prev.author as author,
                       prev.timestamp as timestamp
            """, commit_hash=commit_hash)
            
            record = result.single()
            if record:
                return {
                    "success": True,
                    "prev_commit": {
                        "hash": record["hash"],
                        "message": record["message"],
                        "author": record["author"],
                        "timestamp": record["timestamp"]
                    }
                }
            else:
                return {
                    "success": True,
                    "prev_commit": None,
                    "message": "No previous commit found (this is the earliest commit)"
                }
    except Exception as e:
        logger.error(f"Failed to get previous commit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

