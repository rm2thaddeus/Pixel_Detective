"""Temporal ingestion engine (Phase 2 stub).

Merges commit and file facts into Neo4j using temporal schema helpers.
"""

from __future__ import annotations

from typing import Iterable

from neo4j import Driver

from .git_history_service import GitHistoryService
from .schema.temporal_schema import apply_schema, merge_commit, merge_file, relate_commit_touched_file


class TemporalEngine:
    def __init__(self, driver: Driver, git: GitHistoryService):
        self.driver = driver
        self.git = git

    def apply_schema(self) -> None:
        apply_schema(self.driver)

    def ingest_recent_commits(self, limit: int = 100) -> int:
        commits = self.git.get_commits(limit=limit)
        ingested = 0
        with self.driver.session() as session:
            for c in commits:
                def _tx(tx):
                    merge_commit(tx, {
                        "hash": c["hash"],
                        "message": c.get("message"),
                        "author": c.get("author_email"),
                        "timestamp": c.get("timestamp"),
                        "branch": "unknown",
                    })
                    for f in c.get("files_changed", []) or []:
                        merge_file(tx, {"path": f})
                        relate_commit_touched_file(
                            tx,
                            commit_hash=c["hash"],
                            file_path=f,
                            change_type="M",
                            timestamp=c.get("timestamp", ""),
                        )
                session.write_transaction(_tx)
                ingested += 1
        return ingested


