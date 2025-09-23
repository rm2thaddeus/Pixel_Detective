"""Evidence-Based Relationship Derivation with Confidence Scoring

Implements evidence-based relationship derivation with confidence scoring
and provenance tracking for all derived relationships.

Notes:
- Avoids reliance on custom Cypher functions; uses Python regex extraction.
- Idempotent MERGE operations with confidence accumulation and source tracking.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from neo4j import Driver
import re


class RelationshipDeriver:
    """Evidence-based relationship derivation with confidence scoring."""

    def __init__(self, driver: Driver):
        self.driver = driver
        self.watermarks = self._load_watermarks()

    def derive_all(self, since_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Derive all relationship types with evidence-based confidence scoring."""
        results = {
            "implements": 0,
            "evolves_from": 0,
            "depends_on": 0,
            "confidence_stats": {
                "avg_confidence": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
            },
        }

        with self.driver.session() as session:
            # IMPLEMENTS
            implements_result = session.execute_write(
                self._derive_implements_relationships, since_timestamp
            )
            results["implements"] = implements_result.get("count", 0)

            # EVOLVES_FROM
            evolves_result = session.execute_write(
                self._derive_evolves_from_relationships, since_timestamp
            )
            results["evolves_from"] = evolves_result.get("count", 0)

            # DEPENDS_ON (best-effort)
            depends_result = session.execute_write(self._derive_depends_on_relationships)
            results["depends_on"] = depends_result.get("count", 0)

            # Confidence stats
            confidence_stats = session.execute_write(self._calculate_confidence_stats)
            results["confidence_stats"] = confidence_stats

            # Watermarks
            session.execute_write(self._update_watermarks, since_timestamp)

        return results

    def _load_watermarks(self) -> Dict[str, str]:
        """Load derivation watermarks for incremental updates."""
        with self.driver.session() as session:
            result = session.run(
                "MATCH (w:DerivationWatermark) RETURN w.key as key, w.last_ts as ts"
            )
            return {record["key"]: record["ts"] for record in result}

    @staticmethod
    def _derive_implements_relationships(
        tx, since_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Derive IMPLEMENTS relationships from multiple evidence sources."""
        total = 0
        
        # Updated patterns to match actual commit messages
        implement_patterns = [
            r'\b(?:implements?|adds?|creates?|builds?|develops?)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:fixes?|resolves?)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:enhances?|improves?)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:refactors?|updates?)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:feature|functionality|component)\s+([a-zA-Z0-9_-]+)'
        ]
        
        # 1) Commit-message evidence (0.8) - Updated to work with natural language
        q1 = (
            "MATCH (c:GitCommit)-[t:TOUCHED]->(f:File) "
            "WHERE ($since IS NULL OR coalesce(t.timestamp, c.timestamp) >= $since) "
            "AND (c.message CONTAINS 'implements' OR c.message CONTAINS 'adds' OR c.message CONTAINS 'creates' "
            "OR c.message CONTAINS 'fixes' OR c.message CONTAINS 'enhances' OR c.message CONTAINS 'refactor') "
            "RETURN c.message AS message, f.path AS path, coalesce(t.timestamp, c.timestamp) AS ts"
        )
        for rec in tx.run(q1, since=since_timestamp or None, timeout=30):
            msg = rec.get("message") or ""
            path = rec.get("path")
            ts = rec.get("ts")
            
            # Extract feature/component names from commit messages
            for pattern in implement_patterns:
                matches = re.findall(pattern, msg, re.IGNORECASE)
                for match in matches:
                    # Create a requirement ID from the match
                    req_id = f"REQ-{match.upper().replace(' ', '-')}"
                    total += RelationshipDeriver._merge_implements(
                        tx, req_id, path, ts, sources=["commit-message"], conf=0.8
                    )

        # 2) Doc-mention evidence (0.6)
        # Use file-linked chunks to avoid dependency on Document/Sprint routes.
        q2a = (
            "MATCH (ch:Chunk)-[:MENTIONS]->(r:Requirement) "
            "MATCH (f:File)-[:CONTAINS_CHUNK]->(ch) "
            "MATCH (c:GitCommit)-[t:TOUCHED]->(f) "
            "WHERE ($since IS NULL OR coalesce(t.timestamp, c.timestamp) >= $since) "
            "RETURN DISTINCT r.id AS rid, f.path AS path, coalesce(t.timestamp, c.timestamp) AS ts"
        )
        for rec in tx.run(q2a, since=since_timestamp or None, timeout=30):
            rid = rec.get("rid")
            path = rec.get("path")
            ts = rec.get("ts")
            if rid and path:
                total += RelationshipDeriver._merge_implements(
                    tx, rid, path, ts, sources=["doc-mention"], conf=0.6
                )
        # Fallback for older ingestions: Chunk -> PART_OF -> File
        q2b = (
            "MATCH (ch:Chunk)-[:MENTIONS]->(r:Requirement) "
            "MATCH (ch)-[:PART_OF]->(f:File) "
            "MATCH (c:GitCommit)-[t:TOUCHED]->(f) "
            "WHERE ($since IS NULL OR coalesce(t.timestamp, c.timestamp) >= $since) "
            "RETURN DISTINCT r.id AS rid, f.path AS path, coalesce(t.timestamp, c.timestamp) AS ts"
        )
        for rec in tx.run(q2b, since=since_timestamp or None, timeout=30):
            rid = rec.get("rid")
            path = rec.get("path")
            ts = rec.get("ts")
            if rid and path:
                total += RelationshipDeriver._merge_implements(
                    tx, rid, path, ts, sources=["doc-mention"], conf=0.6
                )

        # 3) Code-comment evidence (proxy via commit-message on code files) (0.8)
        # Pattern to extract FR- and NFR- IDs from commit messages
        fr_pattern = re.compile(r'(FR-\d+|NFR-\d+)', re.IGNORECASE)
        q3 = (
            "MATCH (c:GitCommit)-[t:TOUCHED]->(f:File) "
            "WHERE f.is_code = true AND ($since IS NULL OR coalesce(t.timestamp, c.timestamp) >= $since) "
            "AND (c.message CONTAINS 'FR-' OR c.message CONTAINS 'NFR-') "
            "RETURN c.message AS message, f.path AS path, coalesce(t.timestamp, c.timestamp) AS ts"
        )
        for rec in tx.run(q3, since=since_timestamp or None, timeout=30):
            msg = rec.get("message") or ""
            path = rec.get("path")
            ts = rec.get("ts")
            for rid in set(fr_pattern.findall(msg)):
                total += RelationshipDeriver._merge_implements(
                    tx, rid, path, ts, sources=["code-comment"], conf=0.8
                )

        return {"count": total}

    @staticmethod
    def _merge_implements(
        tx,
        requirement_id: str,
        file_path: str,
        timestamp: Optional[str],
        sources: List[str],
        conf: float,
    ) -> int:
        """MERGE IMPLEMENTS relationship and accumulate confidence/sources.

        Returns 1 per call for counting purposes.
        """
        if not requirement_id or not file_path:
            return 0
        tx.run(
            """
            MERGE (r:Requirement {id: $rid})
            MERGE (f:File {path: $path})
            MERGE (r)-[rel:IMPLEMENTS]->(f)
            ON CREATE SET rel.timestamp = $ts,
                          rel.sources = $sources,
                          rel.confidence = $conf,
                          rel.first_seen_ts = $ts,
                          rel.last_seen_ts = $ts
            ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, $ts),
                         rel.last_seen_ts = CASE WHEN $ts IS NULL OR rel.last_seen_ts IS NULL THEN coalesce($ts, rel.last_seen_ts) ELSE (CASE WHEN $ts > rel.last_seen_ts THEN $ts ELSE rel.last_seen_ts END) END,
                         rel.sources = coalesce(rel.sources, []) + $sources,
                         rel.confidence = CASE WHEN rel.confidence IS NULL THEN $conf ELSE 1 - (1 - rel.confidence) * (1 - $conf) END
            """,
            rid=requirement_id,
            path=file_path,
            ts=timestamp,
            sources=sources,
            conf=conf,
        )
        return 1

    @staticmethod
    def _derive_evolves_from_relationships(
        tx, since_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Derive EVOLVES_FROM relationships using commit message patterns."""
        total = 0
        
        # Updated patterns to match actual commit messages
        evolve_patterns = [
            r'\b(?:replaces?|substitutes?|supersedes?)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:evolves?\s+from|based\s+on|derived\s+from)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:refactors?\s+from|migrates?\s+from)\s+([a-zA-Z0-9_-]+)',
            r'\b(?:updates?\s+from|enhances?\s+from)\s+([a-zA-Z0-9_-]+)'
        ]
        
        q = (
            "MATCH (c:GitCommit) "
            "WHERE ($since IS NULL OR c.timestamp >= $since) "
            "AND (c.message CONTAINS 'replaces' OR c.message CONTAINS 'evolves' OR c.message CONTAINS 'supersedes' "
            "OR c.message CONTAINS 'refactor' OR c.message CONTAINS 'migrate' OR c.message CONTAINS 'update') "
            "RETURN c.message AS message, c.timestamp AS ts"
        )
        for rec in tx.run(q, since=since_timestamp or None):
            msg = rec.get("message") or ""
            ts = rec.get("ts")
            for new_id, old_id in RelationshipDeriver._extract_evolution_pairs(msg):
                tx.run(
                    """
                    MERGE (n:Requirement {id: $new_id})
                    MERGE (o:Requirement {id: $old_id})
                    MERGE (n)-[rel:EVOLVES_FROM]->(o)
                    ON CREATE SET rel.timestamp = $ts,
                                  rel.sources = ['commit-message'],
                                  rel.confidence = 0.9,
                                  rel.first_seen_ts = $ts,
                                  rel.last_seen_ts = $ts
                    ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, $ts),
                                 rel.last_seen_ts = CASE WHEN $ts IS NULL OR rel.last_seen_ts IS NULL THEN coalesce($ts, rel.last_seen_ts) ELSE (CASE WHEN $ts > rel.last_seen_ts THEN $ts ELSE rel.last_seen_ts END) END,
                                 rel.sources = coalesce(rel.sources, []) + ['commit-message'],
                                 rel.confidence = CASE WHEN rel.confidence IS NULL THEN 0.9 ELSE 1 - (1 - rel.confidence) * (1 - 0.9) END
                    """,
                    new_id=new_id,
                    old_id=old_id,
                    ts=ts,
                )
                total += 1
        return {"count": total}

    @staticmethod
    def _derive_depends_on_relationships(tx) -> Dict[str, Any]:
        """Derive DEPENDS_ON relationships using import graph analysis (best-effort)."""
        tx.run(
            """
            MATCH (f1:File)-[:IMPORTS]->(f2:File)
            WHERE f1.is_code = true AND f2.is_code = true
            WITH f1, f2
            MATCH (r1:Requirement)-[:IMPLEMENTS]->(f1)
            MATCH (r2:Requirement)-[:IMPLEMENTS]->(f2)
            WITH r1, r2, count(*) as shared
            WHERE shared >= 2
            MERGE (r1)-[rel:DEPENDS_ON]->(r2)
            ON CREATE SET rel.confidence = 0.8, rel.sources = ['import-graph'], rel.first_seen_ts = datetime(), rel.last_seen_ts = datetime()
            ON MATCH SET rel.sources = coalesce(rel.sources, []) + ['import-graph'], rel.confidence = CASE WHEN rel.confidence IS NULL THEN 0.8 ELSE 1 - (1 - rel.confidence) * (1 - 0.8) END
            """
        )
        result = tx.run("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r) as count")
        return {"count": result.single()["count"] or 0}

    @staticmethod
    def _calculate_confidence_stats(tx) -> Dict[str, Any]:
        """Calculate confidence statistics for derived relationships."""
        # Check if confidence relationships exist first
        check_result = tx.run("""
            MATCH ()-[r]->()
            WHERE r.confidence IS NOT NULL
            RETURN count(r) as total_with_confidence
        """).single()
        
        if not check_result or check_result["total_with_confidence"] == 0:
            return {
                "avg_confidence": 0.0,
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0
            }
        
        result = tx.run(
            """
            MATCH ()-[r]->()
            WHERE r.confidence IS NOT NULL
            RETURN avg(r.confidence) as avg_confidence,
                   count(CASE WHEN r.confidence >= 0.8 THEN 1 END) as high_confidence,
                   count(CASE WHEN r.confidence >= 0.5 AND r.confidence < 0.8 THEN 1 END) as medium_confidence,
                   count(CASE WHEN r.confidence < 0.5 THEN 1 END) as low_confidence
            """
        )
        stats = result.single()
        return {
            "avg_confidence": round(stats["avg_confidence"] or 0.0, 3),
            "high_confidence": stats["high_confidence"] or 0,
            "medium_confidence": stats["medium_confidence"] or 0,
            "low_confidence": stats["low_confidence"] or 0,
        }

    @staticmethod
    def _update_watermarks(tx, since_timestamp: Optional[str] = None):
        """Update derivation watermarks for incremental updates."""
        if since_timestamp:
            for k in ("implements", "evolves_from", "depends_on"):
                tx.run(
                    "MERGE (w:DerivationWatermark {key: $k}) SET w.last_ts = $ts",
                    k=k,
                    ts=since_timestamp,
                )
        else:
            for k in ("implements", "evolves_from", "depends_on"):
                tx.run(
                    "MERGE (w:DerivationWatermark {key: $k}) SET w.last_ts = datetime()",
                    k=k,
                )

    @staticmethod
    def _extract_evolution_pairs(message: str) -> List[Tuple[str, str]]:
        """Extract (new_id, old_id) pairs from a message describing evolution."""
        if not message:
            return []
        pat = re.compile(
            r"\b(?P<new>(?:FR|NFR)-\d{2}-\d{2})\b[^\n]*?\b(replaces|supersedes|evolves from)\b[^\n]*?\b(?P<old>(?:FR|NFR)-\d{2}-\d{2})\b",
            re.IGNORECASE | re.DOTALL,
        )
        out: List[Tuple[str, str]] = []
        for m in pat.finditer(message):
            new_id = (m.group("new") or "").upper()
            old_id = (m.group("old") or "").upper()
            if new_id and old_id and new_id != old_id:
                out.append((new_id, old_id))
        return out
