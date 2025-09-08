from __future__ import annotations

from typing import Dict, List, Optional

from neo4j import Driver


class RelationshipDeriver:
    """Evidence-based relationship derivation with confidence scoring (scaffold).

    Strategies:
    - IMPLEMENTS from commit messages and doc mentions
    - EVOLVES_FROM from message patterns
    - DEPENDS_ON via import graph overlap (placeholder)
    """

    def __init__(self, driver: Driver):
        self.driver = driver

    def derive_implements(self, since_timestamp: Optional[str] = None) -> int:
        """Derive Requirement-[:IMPLEMENTS]->File using commit-message evidence.

        Returns number of relationships created/updated.
        """
        created = 0
        with self.driver.session() as session:
            params = {}
            ts_clause = ""
            if since_timestamp:
                ts_clause = "WHERE c.timestamp >= $since"
                params["since"] = since_timestamp

            # Commit-message evidence: FR-XX-YY in commit message mapping to files touched
            cypher = """
                MATCH (c:GitCommit)-[t:TOUCHED]->(f:File)
                """ + ts_clause + """
                WITH c, f
                WITH c, f, toString(c.message) AS msg, toString(c.timestamp) AS ts
                WITH c, f, ts, [m IN split(msg, ' ') WHERE m =~ '(?i)\\b(?:FR|NFR)-\\d{2}-\\d{2}\\b' | m] AS groups
                UNWIND groups AS g
                WITH c, f, ts, g AS rid
                MERGE (r:Requirement {id: rid})
                MERGE (r)-[rel:IMPLEMENTS]->(f)
                ON CREATE SET rel.commit = c.hash, rel.timestamp = ts, rel.sources = ['commit-message'], rel.confidence = 0.9
                ON MATCH SET rel.timestamp = coalesce(rel.timestamp, ts),
                               rel.sources = coalesce(rel.sources, []) + CASE WHEN 'commit-message' IN rel.sources THEN [] ELSE ['commit-message'] END,
                               rel.confidence = 1 - (1 - coalesce(rel.confidence, 0.5)) * (1 - 0.9)
                RETURN count(*) AS cnt
            """
            try:
                rec = session.run(cypher, params).single()
                created += int(rec["cnt"]) if rec and rec.get("cnt") is not None else 0
            except Exception:
                # APOC may be unavailable; skip gracefully
                pass
        return created

    def derive_evolves_from(self, since_timestamp: Optional[str] = None) -> int:
        """Derive EVOLVES_FROM using message patterns."""
        created = 0
        with self.driver.session() as session:
            params = {}
            ts_clause = ""
            if since_timestamp:
                ts_clause = "WHERE c.timestamp >= $since"
                params["since"] = since_timestamp
            cypher = """
                MATCH (c:GitCommit)
                """ + ts_clause + """
                WITH c, toLower(toString(c.message)) AS m, toString(c.timestamp) AS ts
                WITH c, m, ts, [x IN split(m, ' ') WHERE x =~ '(?i)\\b(?:nfr|fr)-\\d{2}-\\d{2}\\b' | x] AS reqs
                WHERE size(reqs) >= 2
                WITH c, ts, reqs[0] AS new_id, reqs[1] AS old_id
                WHERE new_id <> old_id
                MERGE (n:Requirement {id: toUpper(new_id)})
                MERGE (o:Requirement {id: toUpper(old_id)})
                MERGE (n)-[rel:EVOLVES_FROM]->(o)
                ON CREATE SET rel.commit = c.hash, rel.timestamp = ts, rel.sources = ['commit-message'], rel.confidence = 0.7
                ON MATCH SET rel.timestamp = coalesce(rel.timestamp, ts)
                RETURN count(*) AS cnt
            """
            try:
                rec = session.run(cypher, params).single()
                created += int(rec["cnt"]) if rec and rec.get("cnt") is not None else 0
            except Exception:
                pass
        return created

    def derive_depends_on(self) -> int:
        """Placeholder for import graph-based dependency inference."""
        # Minimal scaffold: no-op for now
        return 0

    def derive_all(self, since_timestamp: Optional[str] = None) -> Dict[str, int]:
        return {
            "implements": self.derive_implements(since_timestamp),
            "evolves_from": self.derive_evolves_from(since_timestamp),
            "depends_on": self.derive_depends_on(),
        }


