from __future__ import annotations

from typing import Dict, List
from neo4j import Driver


class DataValidator:
    """Lightweight data quality checks for the developer graph."""

    def __init__(self, driver: Driver):
        self.driver = driver

    def validate_schema_completeness(self) -> Dict[str, bool]:
        """Check that core constraints/indexes exist and key labels have counts."""
        checks: Dict[str, bool] = {}
        with self.driver.session() as session:
            try:
                rec = session.run("CALL db.constraints()").peek()
                checks["constraints_available"] = rec is not None
            except Exception:
                # Fallback for Neo4j versions where procedure is unavailable
                try:
                    _ = session.run("SHOW CONSTRAINTS").peek()
                    checks["constraints_available"] = True
                except Exception:
                    checks["constraints_available"] = False
            try:
                # basic presence checks
                checks["has_gitcommit"] = (session.run("MATCH (c:GitCommit) RETURN count(c) AS c").single()["c"] or 0) >= 0
                checks["has_file"] = (session.run("MATCH (f:File) RETURN count(f) AS c").single()["c"] or 0) >= 0
                checks["has_requirement"] = (session.run("MATCH (r:Requirement) RETURN count(r) AS c").single()["c"] or 0) >= 0
                checks["has_document"] = (session.run("MATCH (d:Document) RETURN count(d) AS c").single()["c"] or 0) >= 0
                checks["has_chunk"] = (session.run("MATCH (ch:Chunk) RETURN count(ch) AS c").single()["c"] or 0) >= 0
                checks["has_sprint"] = (session.run("MATCH (s:Sprint) RETURN count(s) AS c").single()["c"] or 0) >= 0
                
                # Check for vector index
                try:
                    vector_indexes = session.run("SHOW INDEXES").data()
                    checks["has_vector_index"] = any(
                        idx.get("name") == "chunk_vec_idx" and idx.get("type") == "VECTOR"
                        for idx in vector_indexes
                    )
                except Exception:
                    checks["has_vector_index"] = False
                    
            except Exception:
                checks.setdefault("has_gitcommit", False)
                checks.setdefault("has_file", False)
                checks.setdefault("has_requirement", False)
                checks.setdefault("has_document", False)
                checks.setdefault("has_chunk", False)
                checks.setdefault("has_sprint", False)
                checks.setdefault("has_vector_index", False)
        return checks

    def validate_temporal_consistency(self) -> Dict[str, int]:
        """Counts of temporal edges missing timestamps and orphaned temporal refs."""
        out: Dict[str, int] = {}
        with self.driver.session() as session:
            out["touched_missing_ts"] = session.run("MATCH ()-[r:TOUCHED]->() WHERE r.timestamp IS NULL RETURN count(r) AS c").single()["c"]
            out["implements_missing_ts"] = session.run("MATCH ()-[r:IMPLEMENTS]->() WHERE r.timestamp IS NULL RETURN count(r) AS c").single()["c"]
            out["evolves_missing_ts"] = session.run("MATCH ()-[r:EVOLVES_FROM]->() WHERE r.timestamp IS NULL RETURN count(r) AS c").single()["c"]
            out["refactored_missing_ts"] = session.run("MATCH ()-[r:REFACTORED_TO]->() WHERE r.timestamp IS NULL RETURN count(r) AS c").single()["c"]
            out["deprecated_missing_ts"] = session.run("MATCH ()-[r:DEPRECATED_BY]->() WHERE r.timestamp IS NULL RETURN count(r) AS c").single()["c"]
        return out

    def validate_relationship_integrity(self) -> Dict[str, int]:
        """Counts of dangling relationships and basic integrity issues."""
        out: Dict[str, int] = {}
        with self.driver.session() as session:
            # Dangling IMPLEMENTS (requirement or file missing)
            out["dangling_implements"] = session.run(
                """
                MATCH (r:Requirement)-[rel:IMPLEMENTS]->(f:File)
                WITH count(rel) AS c
                RETURN coalesce(c,0) AS c
                """
            ).single()["c"]
            # Presence of GitCommit nodes referenced by TOUCHED
            out["touched_edges"] = session.run("MATCH (:GitCommit)-[r:TOUCHED]->(:File) RETURN count(r) AS c").single()["c"]
            
            # Phase 1: Temporal semantic graph integrity checks
            out["dangling_links_to"] = session.run(
                """
                MATCH (sc:Chunk)-[rel:LINKS_TO]->(tc:Chunk)
                WITH count(rel) AS c
                RETURN coalesce(c,0) AS c
                """
            ).single()["c"]
            out["dangling_contains_chunk"] = session.run(
                """
                MATCH (d:Document)-[rel:CONTAINS_CHUNK]->(ch:Chunk)
                WITH count(rel) AS c
                RETURN coalesce(c,0) AS c
                """
            ).single()["c"]
            out["dangling_part_of"] = session.run(
                """
                MATCH (ch:Chunk)-[rel:PART_OF]->(f:File)
                WITH count(rel) AS c
                RETURN coalesce(c,0) AS c
                """
            ).single()["c"]
            out["dangling_includes"] = session.run(
                """
                MATCH (s:Sprint)-[rel:INCLUDES]->(c:GitCommit)
                WITH count(rel) AS c
                RETURN coalesce(c,0) AS c
                """
            ).single()["c"]
        return out

    def validate_temporal_semantic_graph(self) -> Dict[str, any]:
        """Validate temporal semantic graph specific elements and relationships."""
        out: Dict[str, any] = {}
        with self.driver.session() as session:
            # Check chunk embeddings
            out["chunks_with_embeddings"] = session.run(
                "MATCH (ch:Chunk) WHERE ch.embedding IS NOT NULL RETURN count(ch) AS c"
            ).single()["c"]
            out["chunks_without_embeddings"] = session.run(
                "MATCH (ch:Chunk) WHERE ch.embedding IS NULL RETURN count(ch) AS c"
            ).single()["c"]
            
            # Check chunk kinds
            out["doc_chunks"] = session.run(
                "MATCH (ch:Chunk {kind: 'doc'}) RETURN count(ch) AS c"
            ).single()["c"]
            out["code_chunks"] = session.run(
                "MATCH (ch:Chunk {kind: 'code'}) RETURN count(ch) AS c"
            ).single()["c"]
            
            # Check LINKS_TO relationships with confidence scores
            out["links_with_confidence"] = session.run(
                "MATCH ()-[r:LINKS_TO]->() WHERE r.confidence IS NOT NULL RETURN count(r) AS c"
            ).single()["c"]
            out["links_without_confidence"] = session.run(
                "MATCH ()-[r:LINKS_TO]->() WHERE r.confidence IS NULL RETURN count(r) AS c"
            ).single()["c"]
            
            # Check enhanced IMPLEMENTS relationships
            out["enhanced_implements"] = session.run(
                "MATCH ()-[r:IMPLEMENTS]->() WHERE r.sources IS NOT NULL AND r.confidence IS NOT NULL RETURN count(r) AS c"
            ).single()["c"]
            out["basic_implements"] = session.run(
                "MATCH ()-[r:IMPLEMENTS]->() WHERE r.sources IS NULL OR r.confidence IS NULL RETURN count(r) AS c"
            ).single()["c"]
            
            # Check vector index availability
            try:
                vector_indexes = session.run("SHOW INDEXES").data()
                out["vector_index_available"] = any(
                    idx.get("name") == "chunk_vec_idx" and idx.get("type") == "VECTOR"
                    for idx in vector_indexes
                )
            except Exception:
                out["vector_index_available"] = False
                
        return out

    def cleanup_orphaned_nodes(self) -> int:
        """Delete obvious orphaned nodes (no relationships) for minor cleanup; return count deleted."""
        with self.driver.session() as session:
            rec = session.run("MATCH (n) WHERE size((n)--())=0 WITH n LIMIT 1000 DETACH DELETE n RETURN count(n) AS c").single()
            return rec["c"] if rec else 0

    def detect_duplicate_relationships(self) -> List[Dict]:
        """Return list of potential duplicate relationships by type and endpoints."""
        with self.driver.session() as session:
            q = (
                "MATCH (a)-[r]->(b) "
                "WITH type(r) AS t, id(a) AS a_id, id(b) AS b_id, collect(r) AS rels "
                "WHERE size(rels) > 1 "
                "RETURN t AS type, a_id, b_id, size(rels) AS dup_count"
            )
            return [dict(record) for record in session.run(q)]

    def backfill_missing_timestamps(self) -> Dict[str, int]:
        """Backfill missing timestamps on temporal relationships using available provenance.

        - IMPLEMENTS: prefer rel.commit -> GitCommit.timestamp; fallback to earliest TOUCHED timestamp on target File
        - EVOLVES_FROM/REFACTORED_TO/DEPRECATED_BY: rel.commit -> GitCommit.timestamp
        """
        results: Dict[str, int] = {"IMPLEMENTS_from_commit": 0, "IMPLEMENTS_from_file": 0, "EVOLVES_FROM": 0, "REFACTORED_TO": 0, "DEPRECATED_BY": 0}
        with self.driver.session() as session:
            # IMPLEMENTS via commit hash
            q1 = (
                "MATCH ()-[rel:IMPLEMENTS]->() "
                "WHERE rel.timestamp IS NULL AND rel.commit IS NOT NULL AND rel.commit <> '' "
                "MATCH (c:GitCommit {hash: rel.commit}) "
                "SET rel.timestamp = c.timestamp "
                "RETURN count(rel) AS c"
            )
            rec1 = session.run(q1).single()
            results["IMPLEMENTS_from_commit"] = rec1["c"] if rec1 else 0

            # IMPLEMENTS via earliest TOUCHED on file
            q2 = (
                "MATCH (:Requirement)-[rel:IMPLEMENTS]->(f:File) "
                "WHERE rel.timestamp IS NULL AND (rel.commit IS NULL OR rel.commit = '') "
                "OPTIONAL MATCH (c:GitCommit)-[t:TOUCHED]->(f) "
                "WITH rel, min(t.timestamp) AS ts "
                "WHERE ts IS NOT NULL "
                "SET rel.timestamp = ts "
                "RETURN count(rel) AS c"
            )
            rec2 = session.run(q2).single()
            results["IMPLEMENTS_from_file"] = rec2["c"] if rec2 else 0

            # EVOLVES_FROM
            q3 = (
                "MATCH ()-[rel:EVOLVES_FROM]->() "
                "WHERE rel.timestamp IS NULL AND rel.commit IS NOT NULL AND rel.commit <> '' "
                "MATCH (c:GitCommit {hash: rel.commit}) "
                "SET rel.timestamp = c.timestamp "
                "RETURN count(rel) AS c"
            )
            rec3 = session.run(q3).single()
            results["EVOLVES_FROM"] = rec3["c"] if rec3 else 0

            # REFACTORED_TO
            q4 = (
                "MATCH ()-[rel:REFACTORED_TO]->() "
                "WHERE rel.timestamp IS NULL AND rel.commit IS NOT NULL AND rel.commit <> '' "
                "MATCH (c:GitCommit {hash: rel.commit}) "
                "SET rel.timestamp = c.timestamp "
                "RETURN count(rel) AS c"
            )
            rec4 = session.run(q4).single()
            results["REFACTORED_TO"] = rec4["c"] if rec4 else 0

            # DEPRECATED_BY
            q5 = (
                "MATCH ()-[rel:DEPRECATED_BY]->() "
                "WHERE rel.timestamp IS NULL AND rel.commit IS NOT NULL AND rel.commit <> '' "
                "MATCH (c:GitCommit {hash: rel.commit}) "
                "SET rel.timestamp = c.timestamp "
                "RETURN count(rel) AS c"
            )
            rec5 = session.run(q5).single()
            results["DEPRECATED_BY"] = rec5["c"] if rec5 else 0

        return results


