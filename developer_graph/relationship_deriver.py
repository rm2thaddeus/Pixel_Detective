"""Evidence-Based Relationship Derivation with Confidence Scoring

Phase 1: Implements evidence-based relationship derivation with confidence scoring
and provenance tracking for all derived relationships.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Any
from neo4j import Driver


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
                "low_confidence": 0
            }
        }
        
        with self.driver.session() as session:
            # Derive IMPLEMENTS relationships
            implements_result = session.execute_write(self._derive_implements_relationships, since_timestamp)
            results["implements"] = implements_result["count"]
            
            # Derive EVOLVES_FROM relationships
            evolves_result = session.execute_write(self._derive_evolves_from_relationships, since_timestamp)
            results["evolves_from"] = evolves_result["count"]
            
            # Derive DEPENDS_ON relationships
            depends_result = session.execute_write(self._derive_depends_on_relationships)
            results["depends_on"] = depends_result["count"]
            
            # Calculate confidence statistics
            confidence_stats = session.execute_write(self._calculate_confidence_stats)
            results["confidence_stats"] = confidence_stats
            
            # Update watermarks
            session.execute_write(self._update_watermarks, since_timestamp)
        
        return results
    
    def _load_watermarks(self) -> Dict[str, str]:
        """Load derivation watermarks for incremental updates."""
        with self.driver.session() as session:
            result = session.run("MATCH (w:DerivationWatermark) RETURN w.key as key, w.last_ts as ts")
            return {record["key"]: record["ts"] for record in result}
    
    @staticmethod
    def _derive_implements_relationships(tx, since_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Derive IMPLEMENTS relationships using multiple evidence sources."""
        count = 0
        
        # 1. Commit-message evidence (confidence: 0.9)
        commit_message_result = tx.run("""
            MATCH (c:GitCommit)-[:TOUCHED]->(f:File)
            WHERE c.message =~ '.*FR-\\d+-\\d+.*'
            WITH c, f, c.timestamp as ts, 'commit-message' as source, 0.9 as conf
            MATCH (r:Requirement {id: extract_fr_id(c.message)})
            MERGE (r)-[rel:IMPLEMENTS]->(f)
            ON CREATE SET rel.timestamp = ts, 
                          rel.sources = [source], 
                          rel.confidence = conf,
                          rel.first_seen_ts = ts,
                          rel.last_seen_ts = ts
            ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, ts),
                         rel.last_seen_ts = max(rel.last_seen_ts, ts),
                         rel.sources = rel.sources + [source],
                         rel.confidence = 1 - (1 - rel.confidence) * (1 - conf)
            RETURN count(rel) as count
        """)
        count += commit_message_result.single()["count"] or 0
        
        # 2. Doc-mention evidence (confidence: 0.4-0.6)
        doc_mention_result = tx.run("""
            MATCH (ch:Chunk)-[:MENTIONS]->(r:Requirement)
            WHERE ch.content =~ '.*' + f.path + '.*'
            WITH ch, r, ch.last_modified_timestamp as ts, 'doc-mention' as source, 0.6 as conf
            MATCH (d:Document)-[:CONTAINS_CHUNK]->(ch)
            MATCH (d)-[:CONTAINS_DOC]-(s:Sprint)-[:INCLUDES]->(c:GitCommit)-[:TOUCHED]->(f:File)
            MERGE (r)-[rel:IMPLEMENTS]->(f)
            ON CREATE SET rel.timestamp = ts, 
                          rel.sources = [source], 
                          rel.confidence = conf,
                          rel.first_seen_ts = ts,
                          rel.last_seen_ts = ts
            ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, ts),
                         rel.last_seen_ts = max(rel.last_seen_ts, ts),
                         rel.sources = rel.sources + [source],
                         rel.confidence = 1 - (1 - rel.confidence) * (1 - conf)
            RETURN count(rel) as count
        """)
        count += doc_mention_result.single()["count"] or 0
        
        # 3. Code-comment evidence (confidence: 0.8)
        code_comment_result = tx.run("""
            MATCH (c:GitCommit)-[:TOUCHED]->(f:File)
            WHERE f.is_code = true AND c.message =~ '.*FR-\\d+-\\d+.*'
            WITH c, f, c.timestamp as ts, 'code-comment' as source, 0.8 as conf
            MATCH (r:Requirement {id: extract_fr_id(c.message)})
            MERGE (r)-[rel:IMPLEMENTS]->(f)
            ON CREATE SET rel.timestamp = ts, 
                          rel.sources = [source], 
                          rel.confidence = conf,
                          rel.first_seen_ts = ts,
                          rel.last_seen_ts = ts
            ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, ts),
                         rel.last_seen_ts = max(rel.last_seen_ts, ts),
                         rel.sources = rel.sources + [source],
                         rel.confidence = 1 - (1 - rel.confidence) * (1 - conf)
            RETURN count(rel) as count
        """)
        count += code_comment_result.single()["count"] or 0
        
        return {"count": count}
    
    @staticmethod
    def _derive_evolves_from_relationships(tx, since_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Derive EVOLVES_FROM relationships using pattern matching."""
        result = tx.run("""
            MATCH (c:GitCommit)
            WHERE c.message =~ '.*(replaces|evolves from|supersedes).*FR-\\d+-\\d+.*'
            WITH c, extract_old_fr(c.message) as old_id, extract_new_fr(c.message) as new_id
            MATCH (old_r:Requirement {id: old_id}), (new_r:Requirement {id: new_id})
            MERGE (new_r)-[rel:EVOLVES_FROM]->(old_r)
            ON CREATE SET rel.timestamp = c.timestamp, 
                          rel.sources = ['commit-message'], 
                          rel.confidence = 0.9,
                          rel.first_seen_ts = c.timestamp,
                          rel.last_seen_ts = c.timestamp
            ON MATCH SET rel.first_seen_ts = coalesce(rel.first_seen_ts, c.timestamp),
                         rel.last_seen_ts = max(rel.last_seen_ts, c.timestamp),
                         rel.sources = rel.sources + ['commit-message'],
                         rel.confidence = 1 - (1 - rel.confidence) * 0.1
            RETURN count(rel) as count
        """)
        
        return {"count": result.single()["count"] or 0}
    
    @staticmethod
    def _derive_depends_on_relationships(tx) -> Dict[str, Any]:
        """Derive DEPENDS_ON relationships using import graph analysis."""
        # First, build import graph
        tx.run("""
            MATCH (f1:File)-[:IMPORTS]->(f2:File)
            WHERE f1.is_code = true AND f2.is_code = true
            WITH f1, f2, count(*) as import_count
            MATCH (r1:Requirement)-[:IMPLEMENTS]->(f1)
            MATCH (r2:Requirement)-[:IMPLEMENTS]->(f2)
            WITH r1, r2, count(*) as shared_imports, 
                 count{(r1)-[:IMPLEMENTS]->()} as r1_files,
                 count{(r2)-[:IMPLEMENTS]->()} as r2_files
            WHERE shared_imports >= 0.3 * r1_files AND shared_imports >= 2
            MERGE (r1)-[rel:DEPENDS_ON]->(r2)
            ON CREATE SET rel.confidence = 0.8, 
                          rel.sources = ['import-graph'],
                          rel.first_seen_ts = datetime(),
                          rel.last_seen_ts = datetime()
            ON MATCH SET rel.sources = rel.sources + ['import-graph'],
                         rel.confidence = 1 - (1 - rel.confidence) * 0.2
        """)
        
        # Count the created relationships
        result = tx.run("MATCH ()-[r:DEPENDS_ON]->() RETURN count(r) as count")
        return {"count": result.single()["count"] or 0}
    
    @staticmethod
    def _calculate_confidence_stats(tx) -> Dict[str, Any]:
        """Calculate confidence statistics for derived relationships."""
        result = tx.run("""
            MATCH ()-[r:IMPLEMENTS|EVOLVES_FROM|DEPENDS_ON]->()
            WHERE r.confidence IS NOT NULL
            RETURN avg(r.confidence) as avg_confidence,
                   count(CASE WHEN r.confidence >= 0.8 THEN 1 END) as high_confidence,
                   count(CASE WHEN r.confidence >= 0.5 AND r.confidence < 0.8 THEN 1 END) as medium_confidence,
                   count(CASE WHEN r.confidence < 0.5 THEN 1 END) as low_confidence
        """)
        
        stats = result.single()
        return {
            "avg_confidence": round(stats["avg_confidence"] or 0.0, 3),
            "high_confidence": stats["high_confidence"] or 0,
            "medium_confidence": stats["medium_confidence"] or 0,
            "low_confidence": stats["low_confidence"] or 0
        }
    
    @staticmethod
    def _update_watermarks(tx, since_timestamp: Optional[str] = None):
        """Update derivation watermarks for incremental updates."""
        current_time = since_timestamp or "datetime()"
        
        tx.run("""
            MERGE (w:DerivationWatermark {key: 'implements'})
            SET w.last_ts = $current_time
        """, current_time=current_time)
        
        tx.run("""
            MERGE (w:DerivationWatermark {key: 'evolves_from'})
            SET w.last_ts = $current_time
        """, current_time=current_time)
        
        tx.run("""
            MERGE (w:DerivationWatermark {key: 'depends_on'})
            SET w.last_ts = $current_time
        """, current_time=current_time)


# Helper functions for pattern extraction
def extract_fr_id(message: str) -> str:
    """Extract FR/NFR ID from commit message."""
    match = re.search(r'\b(FR|NFR)-\d{2}-\d{2}\b', message)
    return match.group(0) if match else None


def extract_old_fr(message: str) -> str:
    """Extract old FR ID from evolution message."""
    # Look for patterns like "FR-11-02 replaces FR-10-01"
    match = re.search(r'(replaces|evolves from|supersedes)\s+(FR|NFR)-\d{2}-\d{2}', message)
    return match.group(2) + match.group(3) if match else None


def extract_new_fr(message: str) -> str:
    """Extract new FR ID from evolution message."""
    # Look for patterns like "FR-11-02 replaces FR-10-01"
    match = re.search(r'(FR|NFR)-\d{2}-\d{2}\s+(replaces|evolves from|supersedes)', message)
    return match.group(1) + match.group(2) if match else None