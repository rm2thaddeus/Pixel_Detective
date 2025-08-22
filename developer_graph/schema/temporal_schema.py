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
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:GitCommit) REQUIRE c.hash IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE")


def merge_commit(tx, commit: Dict[str, object]):
    tx.run(
        """
        MERGE (c:GitCommit {hash: $hash})
        ON CREATE SET c.message = $message, c.author = $author, c.timestamp = $timestamp, c.branch = $branch
        ON MATCH SET c.message = coalesce(c.message, $message)
        """,
        hash=commit["hash"],
        message=commit.get("message"),
        author=commit.get("author_email") or commit.get("author"),
        timestamp=commit.get("timestamp"),
        branch=commit.get("branch", "unknown"),
    )


def merge_file(tx, file_info: Dict[str, object]):
    tx.run(
        """
        MERGE (f:File {path: $path})
        ON CREATE SET f.language = $language
        """,
        path=file_info["path"],
        language=file_info.get("language"),
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


