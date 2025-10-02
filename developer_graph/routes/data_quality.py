"""
Data Quality Monitoring and Repair Endpoints
Provides real-time data quality monitoring and repair capabilities.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from neo4j import Driver
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()

def get_driver() -> Driver:
    """Get Neo4j driver from app state."""
    from ..app_state import driver
    return driver

@router.get("/api/v1/dev-graph/data-quality/overview")
def get_data_quality_overview():
    """Get comprehensive data quality overview."""
    try:
        driver = get_driver()
        with driver.session() as session:
            # Get basic counts
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
            
            # Get chunk statistics
            result = session.run("""
                MATCH (c:Chunk)
                RETURN 
                    count(c) as total_chunks,
                    count(CASE WHEN c.kind = 'doc' THEN 1 END) as doc_chunks,
                    count(CASE WHEN c.kind = 'code' THEN 1 END) as code_chunks,
                    count(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as chunks_with_embeddings
            """)
            chunk_stats = result.single()
            
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
                "relationship_breakdown": rel_counts,
                "chunk_statistics": dict(chunk_stats),
                "quality_issues": {
                    "orphan_ratio": round(orphan_ratio * 100, 2),
                    "timestamp_ratio": round(timestamp_ratio * 100, 2),
                    "critical_issues": orphaned + missing_ts
                },
                "generated_at": datetime.utcnow().isoformat() + "Z"
            }
            
    except Exception as e:
        logger.error(f"Error getting data quality overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/dev-graph/data-quality/fix-timestamps")
def fix_missing_timestamps():
    """Fix missing timestamps on temporal relationships."""
    try:
        driver = get_driver()
        with driver.session() as session:
            # Fix TOUCHED relationships
            result1 = session.run("""
                MATCH (c:GitCommit)-[r:TOUCHED]->(f:File)
                WHERE r.timestamp IS NULL
                SET r.timestamp = c.timestamp
                RETURN count(r) AS fixed
            """)
            touched_fixed = result1.single()["fixed"]
            
            # Fix IMPLEMENTS relationships
            result2 = session.run("""
                MATCH (req:Requirement)-[r:IMPLEMENTS]->(f:File)
                WHERE r.timestamp IS NULL
                OPTIONAL MATCH (c:GitCommit)-[t:TOUCHED]->(f)
                WITH req, r, f, min(t.timestamp) AS earliest_timestamp
                SET r.timestamp = COALESCE(earliest_timestamp, datetime())
                RETURN count(r) AS fixed
            """)
            implements_fixed = result2.single()["fixed"]
            
            return {
                "success": True,
                "touched_fixed": touched_fixed,
                "implements_fixed": implements_fixed,
                "total_fixed": touched_fixed + implements_fixed
            }
            
    except Exception as e:
        logger.error(f"Error fixing timestamps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/dev-graph/data-quality/cleanup-dangling")
def cleanup_dangling_relationships():
    """Clean up dangling relationships and orphaned nodes."""
    try:
        driver = get_driver()
        with driver.session() as session:
            # Remove dangling IMPLEMENTS relationships
            result1 = session.run("""
                MATCH (req:Requirement)-[r:IMPLEMENTS]->(f:File)
                WHERE NOT (req)-[:PART_OF]->() OR NOT (f)-[:TOUCHED]->()
                DELETE r
                RETURN count(r) AS deleted
            """)
            dangling_implements = result1.single()["deleted"]
            
            # Remove orphaned nodes (limit to prevent accidental mass deletion)
            result2 = session.run("""
                MATCH (n)
                WHERE NOT (n)--()
                WITH n LIMIT 1000
                DETACH DELETE n
                RETURN count(n) AS deleted
            """)
            orphaned_nodes = result2.single()["deleted"]
            
            return {
                "success": True,
                "dangling_implements_removed": dangling_implements,
                "orphaned_nodes_removed": orphaned_nodes,
                "total_cleaned": dangling_implements + orphaned_nodes
            }
            
    except Exception as e:
        logger.error(f"Error cleaning up dangling relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/dev-graph/data-quality/fix-chunks")
def fix_chunk_relationships():
    """Fix chunk relationship issues."""
    try:
        driver = get_driver()
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
            
            return {
                "success": True,
                "chunks_processed": chunks_processed,
                "chunks_updated": chunks_updated,
                "total_fixed": chunks_processed + chunks_updated
            }
            
    except Exception as e:
        logger.error(f"Error fixing chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/v1/dev-graph/data-quality/repair-all")
def repair_all_data_quality_issues():
    """Run all data quality repairs in sequence."""
    try:
        results = {}
        
        # Fix timestamps
        timestamp_result = fix_missing_timestamps()
        results["timestamps"] = timestamp_result
        
        # Cleanup dangling relationships
        cleanup_result = cleanup_dangling_relationships()
        results["cleanup"] = cleanup_result
        
        # Fix chunks
        chunk_result = fix_chunk_relationships()
        results["chunks"] = chunk_result
        
        # Get final quality score
        overview = get_data_quality_overview()
        results["final_quality_score"] = overview["quality_score"]
        
        return {
            "success": True,
            "repairs_completed": results,
            "final_quality_score": overview["quality_score"],
            "message": f"Data quality repair completed. Final score: {overview['quality_score']}/100"
        }
        
    except Exception as e:
        logger.error(f"Error in comprehensive repair: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/dev-graph/data-quality/health-check")
def health_check():
    """Quick health check for data quality."""
    try:
        driver = get_driver()
        with driver.session() as session:
            # Quick checks
            result = session.run("MATCH (n) RETURN count(n) AS total_nodes")
            total_nodes = result.single()["total_nodes"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS total_rels")
            total_rels = result.single()["total_rels"]
            
            result = session.run("MATCH (n) WHERE NOT (n)--() RETURN count(n) AS orphaned")
            orphaned = result.single()["orphaned"]
            
            result = session.run("MATCH ()-[r:TOUCHED|IMPLEMENTS]->() WHERE r.timestamp IS NULL RETURN count(r) AS missing_ts")
            missing_ts = result.single()["missing_ts"]
            
            # Calculate health score
            health_score = max(0, 100 - (orphaned / max(total_nodes, 1)) * 50 - (missing_ts / max(total_rels, 1)) * 30)
            
            return {
                "healthy": health_score > 70,
                "health_score": round(health_score, 1),
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "orphaned_nodes": orphaned,
                "missing_timestamps": missing_ts,
                "status": "healthy" if health_score > 70 else "needs_attention"
            }
            
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "healthy": False,
            "health_score": 0,
            "error": str(e),
            "status": "error"
        }
