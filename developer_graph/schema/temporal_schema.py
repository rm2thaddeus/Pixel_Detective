"""Temporal Neo4j Schema Utilities

Phase 1: provide minimal schema helpers for GitCommit and File nodes, and
relationships that carry commit/timestamp metadata.
"""

from __future__ import annotations

from typing import Dict

from neo4j import Driver


def apply_schema(driver: Driver) -> None:
    """Create constraints and indexes required by the temporal graph."""
    with driver.session() as session:
        # Core constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ch:Chunk) REQUIRE ch.id IS UNIQUE")
        
        # Phase 4: Performance indexes for time-bounded queries
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:GitCommit) ON (c.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Commit) ON (c.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.path)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (r:Requirement) ON (r.id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (ch:Chunk) ON (ch.id)")
        
        # Relationship indexes for temporal queries
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:TOUCHED]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:IMPLEMENTS]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:EVOLVES_FROM]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:REFACTORED_TO]-() ON (r.timestamp)")
        session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:DEPRECATED_BY]-() ON (r.timestamp)")

        # Full-text indexes to accelerate search
        # Neo4j 4.x/5.x syntax; create indexes per label for clarity
        try:
            session.run("CREATE FULLTEXT INDEX file_fulltext IF NOT EXISTS FOR (f:File) ON EACH [f.path]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX requirement_fulltext IF NOT EXISTS FOR (r:Requirement) ON EACH [r.id, r.title]")
        except Exception:
            pass
        try:
            session.run("CREATE FULLTEXT INDEX commit_fulltext IF NOT EXISTS FOR (c:GitCommit) ON EACH [c.message, c.author]")
        except Exception:
            pass


def merge_commit(tx, commit: Dict[str, object]):
    tx.run(
        """
        MERGE (c:GitCommit {hash: $hash})
        ON CREATE SET c.message = $message, c.author = $author, c.timestamp = $timestamp, c.branch = $branch, c.uid = $uid
        ON MATCH SET c.message = coalesce(c.message, $message),
                      c.uid = coalesce(c.uid, $uid)
        """,
        hash=commit["hash"],
        message=commit.get("message"),
        author=commit.get("author_email") or commit.get("author"),
        timestamp=commit.get("timestamp"),
        branch=commit.get("branch", "unknown"),
        uid=str(commit["hash"]) if "hash" in commit else None,
    )


def merge_file(tx, file_info: Dict[str, object]):
    tx.run(
        """
        MERGE (f:File {path: $path})
        ON CREATE SET f.language = $language, f.uid = $uid
        ON MATCH SET f.uid = coalesce(f.uid, $uid)
        """,
        path=file_info["path"],
        language=file_info.get("language"),
        uid=str(file_info["path"]) if "path" in file_info else None,
    )


def relate_commit_touched_file(tx, commit_hash: str, file_path: str, change_type: str, timestamp: str):
    tx.run(
        """
        MATCH (c:GitCommit {hash: $hash})
        MERGE (f:File {path: $path})
        MERGE (c)-[r:TOUCHED]->(f)
        ON CREATE SET r.change_type = $change_type, r.timestamp = $timestamp
        ON MATCH SET r.timestamp = coalesce(r.timestamp, $timestamp)
        """,
        hash=commit_hash,
        path=file_path,
        change_type=change_type,
        timestamp=timestamp,
    )


# -------------------- Phase 2: Enhanced Schema Helpers --------------------

def merge_requirement(tx, requirement: Dict[str, object]):
    """Merge a Requirement node.

    Expected keys: id, title, author, date_created (ISO), goal_alignment, tags
    """
    tx.run(
        """
        MERGE (r:Requirement {id: $id})
        ON CREATE SET r.title = $title,
                      r.author = $author,
                      r.date_created = $date_created,
                      r.goal_alignment = $goal_alignment,
                      r.tags = $tags,
                      r.uid = $uid
        ON MATCH SET r.title = coalesce($title, r.title),
                     r.goal_alignment = coalesce($goal_alignment, r.goal_alignment),
                     r.uid = coalesce(r.uid, $uid)
        """,
        id=requirement["id"],
        title=requirement.get("title"),
        author=requirement.get("author"),
        date_created=requirement.get("date_created"),
        goal_alignment=requirement.get("goal_alignment"),
        tags=requirement.get("tags"),
        uid=str(requirement["id"]) if "id" in requirement else None,
    )


def relate_implements(tx, requirement_id: str, file_path: str, commit_hash: str, timestamp: str):
    """Create IMPLEMENTS relationship with commit metadata."""
    tx.run(
        """
        MERGE (r:Requirement {id: $rid})
        MERGE (f:File {path: $path})
        MERGE (r)-[rel:IMPLEMENTS]->(f)
        ON CREATE SET rel.commit = $commit, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        rid=requirement_id,
        path=file_path,
        commit=commit_hash,
        ts=timestamp,
    )


def relate_evolves_from_requirement(
    tx,
    new_req_id: str,
    old_req_id: str,
    commit_hash: str,
    diff_summary: str | None = None,
    timestamp: str | None = None,
):
    """Create EVOLVES_FROM relationship between Requirement nodes.

    Optionally set a `timestamp` when available to enable time-bounded queries.
    """
    tx.run(
        """
        MERGE (n:Requirement {id: $new_id})
        MERGE (o:Requirement {id: $old_id})
        MERGE (n)-[rel:EVOLVES_FROM]->(o)
        ON CREATE SET rel.commit = $commit, rel.diff_summary = $diff, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        new_id=new_req_id,
        old_id=old_req_id,
        commit=commit_hash,
        diff=diff_summary,
        ts=timestamp,
    )


def relate_refactored_file(
    tx,
    old_path: str,
    new_path: str,
    commit_hash: str,
    refactor_type: str | None = None,
    timestamp: str | None = None,
):
    """Create REFACTORED_TO relationship between File nodes with commit metadata.

    Optionally set a `timestamp` when available to enable time-bounded queries.
    """
    tx.run(
        """
        MERGE (o:File {path: $old})
        MERGE (n:File {path: $new})
        MERGE (o)-[rel:REFACTORED_TO]->(n)
        ON CREATE SET rel.commit = $commit, rel.refactor_type = $rtype, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        old=old_path,
        new=new_path,
        commit=commit_hash,
        rtype=refactor_type,
        ts=timestamp,
    )


def relate_deprecated_by(
    tx,
    node_label: str,
    node_key: str,
    node_value: str,
    replacement_label: str,
    replacement_key: str,
    replacement_value: str,
    commit_hash: str,
    reason: str | None = None,
    timestamp: str | None = None,
):
    """Create DEPRECATED_BY relationship between arbitrary nodes with commit metadata.

    node_label/replacement_label should be labels like 'Requirement' or 'File'.
    Keys are property names (e.g., 'id' for Requirement, 'path' for File).
    """
    tx.run(
        f"""
        MERGE (n:{node_label} {{{node_key}: $nval}})
        MERGE (r:{replacement_label} {{{replacement_key}: $rval}})
        MERGE (n)-[rel:DEPRECATED_BY]->(r)
        ON CREATE SET rel.commit = $commit, rel.reason = $reason, rel.timestamp = $ts
        ON MATCH SET rel.commit = coalesce(rel.commit, $commit),
                      rel.timestamp = coalesce(rel.timestamp, $ts)
        """,
        nval=node_value,
        rval=replacement_value,
        commit=commit_hash,
        reason=reason,
        ts=timestamp,
    )

