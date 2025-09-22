#!/usr/bin/env python3
"""
Data Quality Repair Script for Developer Graph
Fixes critical data quality issues identified in the analysis.
"""

import os
import sys
from neo4j import GraphDatabase
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_driver():
    """Get Neo4j driver with environment variables."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))

def fix_missing_timestamps(driver):
    """Fix missing timestamps on temporal relationships."""
    print("🔧 Fixing missing timestamps...")
    
    with driver.session() as session:
        # Fix TOUCHED relationships missing timestamps
        result1 = session.run("""
            MATCH (c:GitCommit)-[r:TOUCHED]->(f:File)
            WHERE r.timestamp IS NULL
            SET r.timestamp = c.timestamp
            RETURN count(r) AS fixed
        """)
        touched_fixed = result1.single()["fixed"]
        
        # Fix IMPLEMENTS relationships missing timestamps
        result2 = session.run("""
            MATCH (req:Requirement)-[r:IMPLEMENTS]->(f:File)
            WHERE r.timestamp IS NULL
            OPTIONAL MATCH (c:GitCommit)-[t:TOUCHED]->(f)
            WITH req, r, f, min(t.timestamp) AS earliest_timestamp
            SET r.timestamp = COALESCE(earliest_timestamp, datetime())
            RETURN count(r) AS fixed
        """)
        implements_fixed = result2.single()["fixed"]
        
        print(f"✅ Fixed {touched_fixed} TOUCHED relationships")
        print(f"✅ Fixed {implements_fixed} IMPLEMENTS relationships")
        
        return touched_fixed + implements_fixed

def cleanup_dangling_relationships(driver):
    """Clean up dangling relationships."""
    print("🧹 Cleaning up dangling relationships...")
    
    with driver.session() as session:
        # Remove dangling IMPLEMENTS relationships
        result1 = session.run("""
            MATCH (req:Requirement)-[r:IMPLEMENTS]->(f:File)
            WHERE NOT (req)-[:PART_OF]->() OR NOT (f)-[:TOUCHED]->()
            DELETE r
            RETURN count(r) AS deleted
        """)
        dangling_implements = result1.single()["deleted"]
        
        # Remove orphaned nodes
        result2 = session.run("""
            MATCH (n)
            WHERE NOT (n)--()
            WITH n LIMIT 1000
            DETACH DELETE n
            RETURN count(n) AS deleted
        """)
        orphaned_nodes = result2.single()["deleted"]
        
        print(f"✅ Removed {dangling_implements} dangling IMPLEMENTS relationships")
        print(f"✅ Removed {orphaned_nodes} orphaned nodes")
        
        return dangling_implements + orphaned_nodes

def fix_chunk_relationships(driver):
    """Fix chunk relationship issues."""
    print("🔗 Fixing chunk relationships...")
    
    with driver.session() as session:
        # Ensure all chunks have proper relationships
        result1 = session.run("""
            MATCH (c:Chunk)
            WHERE NOT (c)-[:CONTAINS_CHUNK]-()
            OPTIONAL MATCH (d:Document {path: c.doc_path})
            FOREACH (x IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                MERGE (d)-[:CONTAINS_CHUNK]->(c)
            )
            RETURN count(c) AS processed
        """)
        chunks_processed = result1.single()["processed"]
        
        # Fix chunk kind property
        result2 = session.run("""
            MATCH (c:Chunk)
            WHERE c.kind IS NULL
            SET c.kind = COALESCE(c.chunk_type, 'unknown')
            RETURN count(c) AS updated
        """)
        chunks_updated = result2.single()["updated"]
        
        print(f"✅ Processed {chunks_processed} chunk relationships")
        print(f"✅ Updated {chunks_updated} chunk kind properties")
        
        return chunks_processed + chunks_updated

def get_data_quality_score(driver):
    """Get current data quality score."""
    with driver.session() as session:
        # Get current stats
        result = session.run("""
            MATCH (n)
            WITH labels(n) as labels, count(n) as count
            UNWIND labels as label
            RETURN label, sum(count) as total
        """)
        
        node_counts = {record["label"]: record["total"] for record in result}
        
        # Get relationship counts
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as total
        """)
        
        rel_counts = {record["rel_type"]: record["total"] for record in result}
        
        # Get quality metrics
        result = session.run("""
            MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphaned
        """)
        orphaned = result.single()["orphaned"]
        
        result = session.run("""
            MATCH ()-[r:TOUCHED|IMPLEMENTS]->()
            WHERE r.timestamp IS NULL
            RETURN count(r) AS missing_ts
        """)
        missing_ts = result.single()["missing_ts"]
        
        total_nodes = sum(node_counts.values())
        total_rels = sum(rel_counts.values())
        
        # Calculate quality score
        orphan_ratio = orphaned / total_nodes if total_nodes > 0 else 0
        timestamp_ratio = missing_ts / total_rels if total_rels > 0 else 0
        
        quality_score = max(0, 100 - (orphan_ratio * 50) - (timestamp_ratio * 30))
        
        return {
            "quality_score": round(quality_score, 1),
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "orphaned_nodes": orphaned,
            "missing_timestamps": missing_ts,
            "node_breakdown": node_counts,
            "relationship_breakdown": rel_counts
        }

def main():
    """Main repair function."""
    print("🚀 Starting Developer Graph Data Quality Repair...")
    print("=" * 60)
    
    driver = get_driver()
    
    try:
        # Get initial quality score
        print("📊 Initial Data Quality Assessment:")
        initial_stats = get_data_quality_score(driver)
        print(f"   Quality Score: {initial_stats['quality_score']}/100")
        print(f"   Total Nodes: {initial_stats['total_nodes']:,}")
        print(f"   Total Relationships: {initial_stats['total_relationships']:,}")
        print(f"   Orphaned Nodes: {initial_stats['orphaned_nodes']:,}")
        print(f"   Missing Timestamps: {initial_stats['missing_timestamps']:,}")
        print()
        
        # Apply fixes
        timestamps_fixed = fix_missing_timestamps(driver)
        relationships_cleaned = cleanup_dangling_relationships(driver)
        chunks_fixed = fix_chunk_relationships(driver)
        
        print()
        print("📊 Final Data Quality Assessment:")
        final_stats = get_data_quality_score(driver)
        print(f"   Quality Score: {final_stats['quality_score']}/100")
        print(f"   Total Nodes: {final_stats['total_nodes']:,}")
        print(f"   Total Relationships: {final_stats['total_relationships']:,}")
        print(f"   Orphaned Nodes: {final_stats['orphaned_nodes']:,}")
        print(f"   Missing Timestamps: {final_stats['missing_timestamps']:,}")
        
        print()
        print("✅ Data Quality Repair Complete!")
        print(f"   Timestamps Fixed: {timestamps_fixed:,}")
        print(f"   Relationships Cleaned: {relationships_cleaned:,}")
        print(f"   Chunks Fixed: {chunks_fixed:,}")
        print(f"   Quality Improvement: {initial_stats['quality_score']:.1f} → {final_stats['quality_score']:.1f}")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()
