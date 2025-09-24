"""Document to code linking utilities.

Creates relationships between sprint documentation chunks and code artifacts
(files, commits) by scanning chunk text for inline mentions and correlating
with sprint commit activity.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from neo4j import Driver

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileMention:
    chunk_id: str
    file_path: str
    term: str
    method: str
    confidence: float


@dataclass(frozen=True)
class CommitMention:
    chunk_id: str
    commit_hash: str
    term: str
    method: str
    confidence: float


class DocumentCodeLinker:
    """Derives relationships between documentation chunks and code artifacts."""

    FILE_PATH_PATTERN = re.compile(
        r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,6})"
    )
    FILE_BASENAME_PATTERN = re.compile(
        r"(?<![\w./-])([A-Za-z0-9_.-]+\.(?:py|tsx|ts|js|jsx|md|json|yml|yaml|css|scss|html|proto|sql))"
    )
    COMMIT_PATTERN = re.compile(r"\b[0-9a-f]{10,40}\b", re.IGNORECASE)
    IGNORE_PREFIXES: Tuple[str, ...] = ("http://", "https://", "www.")
    SUPPORTED_EXTENSIONS: Set[str] = {
        ".py",
        ".tsx",
        ".ts",
        ".js",
        ".jsx",
        ".md",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".cfg",
        ".css",
        ".scss",
        ".html",
        ".proto",
        ".sql",
    }

    def __init__(self, driver: Driver, repo_path: Path | str, batch_size: int = 200):
        self.driver = driver
        self.repo_root = Path(repo_path).resolve()
        self.batch_size = batch_size
        self.logger = logger

    # ------------------------------------------------------------------
    def link_documents_to_code(self) -> Dict[str, int]:
        """Main entry point to derive document → code relationships."""

        file_index = self._load_file_index()
        commit_index = self._load_commit_index()
        chunks = self._load_doc_chunks()

        if not chunks:
            self.logger.info("DocumentCodeLinker: no document chunks found")
            stats = self._refresh_sprint_file_links()
            stats.update(
                {
                    "chunk_file_links_created": 0,
                    "chunk_file_links_removed": 0,
                    "chunk_commit_links_created": 0,
                    "chunk_commit_links_removed": 0,
                    "doc_file_rollups": 0,
                    "doc_commit_rollups": 0,
                }
            )
            return stats

        chunk_file_mentions: Dict[str, List[FileMention]] = {}
        chunk_commit_mentions: Dict[str, List[CommitMention]] = {}

        for chunk in chunks:
            chunk_id = chunk["id"]
            mentions = self._find_file_mentions(
                chunk_id=chunk_id,
                text=chunk.get("text") or "",
                heading=chunk.get("heading") or "",
                file_index=file_index,
            )
            chunk_file_mentions[chunk_id] = mentions

            commit_mentions = self._find_commit_mentions(
                chunk_id=chunk_id,
                text=chunk.get("text") or "",
                heading=chunk.get("heading") or "",
                commit_index=commit_index,
            )
            chunk_commit_mentions[chunk_id] = commit_mentions

        stats = {}
        stats.update(self._apply_chunk_file_mentions(chunk_file_mentions))
        stats.update(self._apply_chunk_commit_mentions(chunk_commit_mentions))
        stats.update(self._rollup_document_file_mentions())
        stats.update(self._rollup_document_commit_mentions())
        stats.update(self._refresh_sprint_file_links())
        return stats

    # ------------------------------------------------------------------
    def _load_file_index(self) -> Dict[str, object]:
        """Return lookup structures for repository files."""
        with self.driver.session() as session:
            records = session.run("MATCH (f:File) RETURN f.path AS path")
            paths = [record["path"] for record in records]

        full_paths: Set[str] = set(paths)
        basename_index: Dict[str, Set[str]] = defaultdict(set)
        for path in paths:
            basename_index[Path(path).name.lower()].add(path)
        return {"full": full_paths, "by_basename": basename_index}

    def _load_commit_index(self) -> Dict[str, str]:
        with self.driver.session() as session:
            records = session.run("MATCH (c:GitCommit) RETURN c.hash AS hash")
            hashes = [record["hash"].lower() for record in records]

        prefix_index: Dict[str, str] = {}
        for commit_hash in hashes:
            for length in range(10, len(commit_hash) + 1):
                prefix = commit_hash[:length]
                prefix_index.setdefault(prefix, commit_hash)
        return prefix_index

    def _load_doc_chunks(self) -> List[Dict[str, object]]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Chunk)
                WHERE coalesce(c.kind, 'doc') IN ['doc', 'document', 'markdown']
                OPTIONAL MATCH (d:Document)-[:CONTAINS_CHUNK]->(c)
                RETURN c.id AS id, c.text AS text, c.heading AS heading, d.path AS doc_path
                """
            )
            return result.data()

    # ------------------------------------------------------------------
    def _find_file_mentions(
        self,
        chunk_id: str,
        text: str,
        heading: str,
        file_index: Dict[str, object],
    ) -> List[FileMention]:
        candidates: Set[Tuple[str, str, str, float]] = set()
        content = "\n".join(filter(None, [heading, text]))

        for match in self.FILE_PATH_PATTERN.finditer(content):
            raw = self._normalise_candidate(match.group(1))
            if not raw:
                continue
            if raw.lower().startswith(self.IGNORE_PREFIXES):
                continue
            if raw in file_index["full"]:
                candidates.add((raw, match.group(1), "full-path", 1.0))
            else:
                normalised = self._trim_repo_prefix(raw)
                if normalised in file_index["full"]:
                    candidates.add((normalised, match.group(1), "full-path", 0.95))

        for match in self.FILE_BASENAME_PATTERN.finditer(content):
            name = self._normalise_candidate(match.group(1))
            if not name:
                continue
            if Path(name).suffix not in self.SUPPORTED_EXTENSIONS:
                continue
            matches = file_index["by_basename"].get(name.lower())
            if not matches:
                continue
            if len(matches) == 1:
                target = next(iter(matches))
                candidates.add((target, name, "basename", 0.7))

        mentions = [
            FileMention(
                chunk_id=chunk_id,
                file_path=item[0],
                term=item[1],
                method=item[2],
                confidence=item[3],
            )
            for item in sorted(candidates)
        ]
        return mentions

    def _find_commit_mentions(
        self,
        chunk_id: str,
        text: str,
        heading: str,
        commit_index: Dict[str, str],
    ) -> List[CommitMention]:
        content = "\n".join(filter(None, [heading, text]))
        mentions: Dict[str, CommitMention] = {}

        for match in self.COMMIT_PATTERN.finditer(content):
            token = self._normalise_candidate(match.group(0)).lower()
            if len(token) < 10:
                continue
            if any(ch not in "0123456789abcdef" for ch in token):
                continue
            mapped = commit_index.get(token)
            if not mapped:
                mapped = commit_index.get(token[:12])
            if not mapped:
                continue
            mentions[mapped] = CommitMention(
                chunk_id=chunk_id,
                commit_hash=mapped,
                term=match.group(0),
                method="hash-prefix",
                confidence=0.9 if len(token) >= 12 else 0.75,
            )
        return list(mentions.values())

    # ------------------------------------------------------------------
    def _apply_chunk_file_mentions(self, mentions: Dict[str, List[FileMention]]) -> Dict[str, int]:
        created = 0
        removed = 0

        with self.driver.session() as session:
            for chunk_id, items in mentions.items():
                payload = [item.__dict__ for item in items]
                if payload:
                    summary = session.run(
                        """
                        UNWIND $batch AS mention
                        MATCH (c:Chunk {id: mention.chunk_id})
                        MATCH (f:File {path: mention.file_path})
                        MERGE (c)-[rel:MENTIONS_FILE {source: 'doc-text'}]->(f)
                        ON CREATE SET rel.created_at = datetime()
                        SET rel.last_seen = datetime(),
                            rel.term = mention.term,
                            rel.method = mention.method,
                            rel.confidence = mention.confidence
                        RETURN count(rel) AS relationships
                        """,
                        batch=payload,
                    ).single()
                    if summary and summary["relationships"]:
                        created += int(summary["relationships"])

                current_paths = [item.file_path for item in items]
                removal = session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})-[rel:MENTIONS_FILE {source: 'doc-text'}]->(f:File)
                    WHERE NOT f.path IN $paths
                    WITH rel
                    DELETE rel
                    RETURN count(rel) AS removed
                    """,
                    chunk_id=chunk_id,
                    paths=current_paths or ["__none__"],
                ).single()
                if removal and removal["removed"]:
                    removed += int(removal["removed"])

                session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})
                    SET c.file_mentions_hash = $hash,
                        c.file_mentions_last = datetime(),
                        c.file_mentions_count = $count
                    """,
                    chunk_id=chunk_id,
                    hash=self._hash_mentions(items),
                    count=len(items),
                )

            # remove annotations for chunks without mentions
            session.run(
                """
                MATCH (c:Chunk)
                WHERE coalesce(c.kind, 'doc') IN ['doc', 'document', 'markdown']
                AND NOT (c)-[:MENTIONS_FILE {source: 'doc-text'}]->(:File)
                REMOVE c.file_mentions_hash, c.file_mentions_last, c.file_mentions_count
                """
            )

        return {
            "chunk_file_links_created": created,
            "chunk_file_links_removed": removed,
        }

    def _apply_chunk_commit_mentions(self, mentions: Dict[str, List[CommitMention]]) -> Dict[str, int]:
        created = 0
        removed = 0

        with self.driver.session() as session:
            for chunk_id, items in mentions.items():
                payload = [item.__dict__ for item in items]
                if payload:
                    summary = session.run(
                        """
                        UNWIND $batch AS mention
                        MATCH (c:Chunk {id: mention.chunk_id})
                        MATCH (g:GitCommit {hash: mention.commit_hash})
                        MERGE (c)-[rel:MENTIONS_COMMIT {source: 'doc-text'}]->(g)
                        ON CREATE SET rel.created_at = datetime()
                        SET rel.last_seen = datetime(),
                            rel.term = mention.term,
                            rel.method = mention.method,
                            rel.confidence = mention.confidence
                        RETURN count(rel) AS relationships
                        """,
                        batch=payload,
                    ).single()
                    if summary and summary["relationships"]:
                        created += int(summary["relationships"])

                current_hashes = [item.commit_hash for item in items]
                removal = session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})-[rel:MENTIONS_COMMIT {source: 'doc-text'}]->(g:GitCommit)
                    WHERE NOT g.hash IN $hashes
                    WITH rel
                    DELETE rel
                    RETURN count(rel) AS removed
                    """,
                    chunk_id=chunk_id,
                    hashes=current_hashes or ["__none__"],
                ).single()
                if removal and removal["removed"]:
                    removed += int(removal["removed"])

                session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})
                    SET c.commit_mentions_hash = CASE WHEN $count > 0 THEN $hash ELSE NULL END,
                        c.commit_mentions_last = CASE WHEN $count > 0 THEN datetime() ELSE NULL END,
                        c.commit_mentions_count = CASE WHEN $count > 0 THEN $count ELSE NULL END
                    """,
                    chunk_id=chunk_id,
                    hash=self._hash_commit_mentions(items),
                    count=len(items),
                )

            session.run(
                """
                MATCH (c:Chunk)
                WHERE coalesce(c.kind, 'doc') IN ['doc', 'document', 'markdown']
                AND NOT (c)-[:MENTIONS_COMMIT {source: 'doc-text'}]->(:GitCommit)
                REMOVE c.commit_mentions_hash, c.commit_mentions_last, c.commit_mentions_count
                """
            )

        return {
            "chunk_commit_links_created": created,
            "chunk_commit_links_removed": removed,
        }

    def _rollup_document_file_mentions(self) -> Dict[str, int]:
        with self.driver.session() as session:
            summary = session.run(
                """
                MATCH (d:Document)-[:CONTAINS_CHUNK]->(c:Chunk)-[:MENTIONS_FILE {source: 'doc-text'}]->(f:File)
                WITH d, f, count(DISTINCT c) AS occurrences
                MERGE (d)-[rel:MENTIONS_FILE {source: 'doc-text-rollup'}]->(f)
                ON CREATE SET rel.created_at = datetime()
                SET rel.last_seen = datetime(),
                    rel.chunk_occurrences = occurrences
                RETURN count(rel) AS relationships
                """
            ).single()
            removed = session.run(
                """
                MATCH (d:Document)-[rel:MENTIONS_FILE {source: 'doc-text-rollup'}]->(f:File)
                WHERE NOT EXISTS {
                    MATCH (d)-[:CONTAINS_CHUNK]->(:Chunk)-[:MENTIONS_FILE {source: 'doc-text'}]->(f)
                }
                WITH rel
                DELETE rel
                RETURN count(rel) AS removed
                """
            ).single()
        return {
            "doc_file_rollups": int(summary["relationships"]) if summary else 0,
            "doc_file_rollups_removed": int(removed["removed"]) if removed else 0,
        }

    def _rollup_document_commit_mentions(self) -> Dict[str, int]:
        with self.driver.session() as session:
            summary = session.run(
                """
                MATCH (d:Document)-[:CONTAINS_CHUNK]->(c:Chunk)-[:MENTIONS_COMMIT {source: 'doc-text'}]->(g:GitCommit)
                WITH d, g, count(DISTINCT c) AS occurrences
                MERGE (d)-[rel:MENTIONS_COMMIT {source: 'doc-text-rollup'}]->(g)
                ON CREATE SET rel.created_at = datetime()
                SET rel.last_seen = datetime(),
                    rel.chunk_occurrences = occurrences
                RETURN count(rel) AS relationships
                """
            ).single()
            removed = session.run(
                """
                MATCH (d:Document)-[rel:MENTIONS_COMMIT {source: 'doc-text-rollup'}]->(g:GitCommit)
                WHERE NOT EXISTS {
                    MATCH (d)-[:CONTAINS_CHUNK]->(:Chunk)-[:MENTIONS_COMMIT {source: 'doc-text'}]->(g)
                }
                WITH rel
                DELETE rel
                RETURN count(rel) AS removed
                """
            ).single()
        return {
            "doc_commit_rollups": int(summary["relationships"]) if summary else 0,
            "doc_commit_rollups_removed": int(removed["removed"]) if removed else 0,
        }

    def _refresh_sprint_file_links(self) -> Dict[str, int]:
        with self.driver.session() as session:
            summary = session.run(
                """
                MATCH (s:Sprint)-[:INCLUDES]->(c:GitCommit)-[:TOUCHED]->(f:File)
                WITH s, f, count(DISTINCT c) AS commit_count
                MERGE (s)-[rel:INVOLVES_FILE {source: 'sprint-commits'}]->(f)
                ON CREATE SET rel.created_at = datetime()
                SET rel.last_seen = datetime(),
                    rel.commit_count = commit_count
                RETURN count(rel) AS relationships
                """
            ).single()
            removed = session.run(
                """
                MATCH (s:Sprint)-[rel:INVOLVES_FILE {source: 'sprint-commits'}]->(f:File)
                WHERE NOT EXISTS {
                    MATCH (s)-[:INCLUDES]->(:GitCommit)-[:TOUCHED]->(f)
                }
                WITH rel
                DELETE rel
                RETURN count(rel) AS removed
                """
            ).single()
        return {
            "sprint_file_links": int(summary["relationships"]) if summary else 0,
            "sprint_file_links_removed": int(removed["removed"]) if removed else 0,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_candidate(value: str) -> str:
        return value.strip("`'\"<>[](){}.,;:")

    @staticmethod
    def _hash_mentions(mentions: Sequence[FileMention]) -> Optional[str]:
        if not mentions:
            return None
        digest = hashlib.sha1()
        for mention in sorted(mentions, key=lambda item: (item.file_path, item.term)):
            digest.update(mention.file_path.encode("utf-8"))
            digest.update(b"|")
            digest.update(mention.term.encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _hash_commit_mentions(mentions: Sequence[CommitMention]) -> Optional[str]:
        if not mentions:
            return None
        digest = hashlib.sha1()
        for mention in sorted(mentions, key=lambda item: (item.commit_hash, item.term)):
            digest.update(mention.commit_hash.encode("utf-8"))
            digest.update(b"|")
            digest.update(mention.term.encode("utf-8"))
        return digest.hexdigest()

    def _trim_repo_prefix(self, path_value: str) -> str:
        candidate = path_value
        # Remove leading repo-specific prefixes like ./ or absolute references to repo root
        candidate = candidate.lstrip("./")
        repo_name = self.repo_root.name
        if candidate.startswith(repo_name + "/"):
            candidate = candidate[len(repo_name) + 1 :]
        return candidate

