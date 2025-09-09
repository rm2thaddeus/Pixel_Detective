from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
import logging
from ..app_state import driver
from .ingest import bootstrap_graph


router = APIRouter()
logger = logging.getLogger(__name__)


@router.delete("/api/v1/dev-graph/reset")
def reset_database(confirm: bool = False):
    if not confirm:
        raise HTTPException(status_code=400, detail="This operation will delete all data. Set confirm=true to proceed.")
    try:
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            session.run("MATCH (n) DETACH DELETE n")
            return {
                "success": True,
                "deleted_nodes": node_count,
                "deleted_relationships": rel_count,
                "message": "Database reset successfully",
            }
    except Exception as e:
        logger.exception("Database reset failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/v1/dev-graph/cleanup")
def cleanup_database(confirm: bool = False):
    if not confirm:
        raise HTTPException(status_code=400, detail="This operation will clean up data. Set confirm=true to proceed.")
    try:
        with driver.session() as session:
            initial_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            initial_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            orphaned_result = session.run(
                """
                MATCH (n)
                WHERE NOT (n)--()
                DELETE n
                RETURN count(n) as deleted
                """
            ).single()
            orphaned_deleted = orphaned_result["deleted"] if orphaned_result else 0
            duplicate_commits = session.run(
                """
                MATCH (c:GitCommit)
                WITH c.hash as hash, collect(c) as commits
                WHERE size(commits) > 1
                WITH hash, commits, max([c IN commits | c.timestamp]) as latest_ts
                UNWIND commits as c
                WITH c, latest_ts
                WHERE c.timestamp < latest_ts
                DELETE c
                RETURN count(c) as deleted
                """
            ).single()
            duplicate_deleted = duplicate_commits["deleted"] if duplicate_commits else 0
            final_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            final_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            return {
                "success": True,
                "initial_nodes": initial_nodes,
                "initial_relationships": initial_rels,
                "final_nodes": final_nodes,
                "final_relationships": final_rels,
                "orphaned_nodes_deleted": orphaned_deleted,
                "duplicate_commits_deleted": duplicate_deleted,
                "total_cleaned": orphaned_deleted + duplicate_deleted,
            }
    except Exception as e:
        logger.exception("Database cleanup failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/dev-graph/ingest/full-reset")
def full_reset_and_ingest(
    confirm: bool = False,
    commit_limit: int = Query(1000, ge=1, le=20000),
    derive_relationships: bool = True,
    include_chunking: bool = True,
    doc_limit: int = Query(None, ge=1, le=1000),
    code_limit: int = Query(None, ge=1, le=5000),
):
    if not confirm:
        raise HTTPException(status_code=400, detail="This operation will delete all data and re-ingest. Set confirm=true to proceed.")
    try:
        reset_result = reset_database(confirm=True)
        bootstrap_result = bootstrap_graph(
            reset_graph=False,
            commit_limit=commit_limit,
            derive_relationships=derive_relationships,
            dry_run=False,
            include_chunking=include_chunking,
            doc_limit=doc_limit,
            code_limit=code_limit,
        )
        return {"success": True, "reset_result": reset_result, "bootstrap_result": bootstrap_result, "message": "Full reset and ingestion completed successfully"}
    except Exception as e:
        logger.exception("Full reset and ingest failed")
        raise HTTPException(status_code=500, detail=str(e))

