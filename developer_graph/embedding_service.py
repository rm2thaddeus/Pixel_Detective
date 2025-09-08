"""Embedding Service for Temporal Semantic Dev Graph

Phase 3: Generates embeddings for chunks using ML service or local models.
"""

import os
import time
import requests
from typing import List, Dict, Any, Optional
from neo4j import Driver
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for chunks."""
    
    def __init__(self, driver: Driver, ml_service_url: str = None):
        self.driver = driver
        self.ml_service_url = ml_service_url or os.environ.get("ML_SERVICE_URL", "http://localhost:8001")
        self.batch_size = int(os.environ.get("EMBED_BATCH_SIZE", "10"))
        self.max_retries = 3
        self.retry_delay = 1.0
        
    def generate_embeddings_for_chunks(self, chunk_ids: List[str] = None, 
                                     batch_size: int = None) -> Dict[str, int]:
        """Generate embeddings for chunks.
        
        Args:
            chunk_ids: Specific chunk IDs to process (None for all chunks without embeddings)
            batch_size: Override default batch size
            
        Returns:
            Statistics about embedding generation
        """
        if batch_size is None:
            batch_size = self.batch_size
            
        stats = {
            "total_chunks": 0,
            "processed_chunks": 0,
            "successful_embeddings": 0,
            "failed_embeddings": 0,
            "skipped_chunks": 0,
            "errors": []
        }
        
        try:
            # Get chunks that need embeddings
            chunks_to_process = self._get_chunks_for_embedding(chunk_ids)
            stats["total_chunks"] = len(chunks_to_process)
            
            if not chunks_to_process:
                logger.info("No chunks need embedding generation")
                return stats
            
            logger.info(f"Processing {len(chunks_to_process)} chunks for embedding generation")
            
            # Process in batches
            for i in range(0, len(chunks_to_process), batch_size):
                batch = chunks_to_process[i:i + batch_size]
                batch_stats = self._process_batch(batch)
                
                # Update overall stats
                stats["processed_chunks"] += batch_stats["processed"]
                stats["successful_embeddings"] += batch_stats["successful"]
                stats["failed_embeddings"] += batch_stats["failed"]
                stats["skipped_chunks"] += batch_stats["skipped"]
                stats["errors"].extend(batch_stats["errors"])
                
                # Log progress
                if (i + batch_size) % (batch_size * 10) == 0:
                    logger.info(f"Processed {i + batch_size}/{len(chunks_to_process)} chunks")
                
                # Small delay to avoid overwhelming the ML service
                time.sleep(0.1)
            
            logger.info(f"Embedding generation completed: {stats['successful_embeddings']} successful, {stats['failed_embeddings']} failed")
            
        except Exception as e:
            logger.exception("Error in embedding generation")
            stats["errors"].append(str(e))
            
        return stats
    
    def _get_chunks_for_embedding(self, chunk_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Get chunks that need embeddings."""
        with self.driver.session() as session:
            if chunk_ids:
                # Get specific chunks
                cypher = """
                    MATCH (ch:Chunk)
                    WHERE ch.id IN $chunk_ids AND ch.embedding IS NULL
                    RETURN ch.id as id, ch.text as text, ch.kind as kind
                    ORDER BY ch.id
                """
                result = session.run(cypher, chunk_ids=chunk_ids)
            else:
                # Get all chunks without embeddings
                cypher = """
                    MATCH (ch:Chunk)
                    WHERE ch.embedding IS NULL AND ch.text IS NOT NULL
                    RETURN ch.id as id, ch.text as text, ch.kind as kind
                    ORDER BY ch.id
                    LIMIT 1000
                """
                result = session.run(cypher)
            
            return [{"id": record["id"], "text": record["text"], "kind": record["kind"]} 
                   for record in result]
    
    def _process_batch(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process a batch of chunks for embedding generation."""
        batch_stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            # Prepare texts for embedding
            texts = []
            chunk_mapping = {}
            
            for chunk in chunks:
                text = chunk["text"]
                if not text or len(text.strip()) < 10:
                    batch_stats["skipped"] += 1
                    continue
                
                # Truncate very long texts (keep first 2000 chars)
                if len(text) > 2000:
                    text = text[:2000] + "..."
                
                texts.append(text)
                chunk_mapping[text] = chunk["id"]
            
            if not texts:
                return batch_stats
            
            # Generate embeddings
            embeddings = self._get_embeddings(texts)
            
            if embeddings:
                # Store embeddings in database
                self._store_embeddings(chunk_mapping, embeddings)
                batch_stats["successful"] = len(embeddings)
            else:
                batch_stats["failed"] = len(texts)
                batch_stats["errors"].append("Failed to get embeddings from ML service")
            
            batch_stats["processed"] = len(texts)
            
        except Exception as e:
            logger.exception(f"Error processing batch: {e}")
            batch_stats["failed"] = len(chunks)
            batch_stats["errors"].append(str(e))
        
        return batch_stats
    
    def _get_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Get embeddings from ML service or fallback to simple hash-based embeddings."""
        try:
            # Try ML service first
            if self.ml_service_url:
                response = requests.post(
                    f"{self.ml_service_url}/embed_text",
                    json={"texts": texts},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embeddings")
        except Exception as e:
            logger.warning(f"ML service unavailable: {e}")
        
        # Fallback: Generate simple hash-based embeddings
        logger.info("Using fallback hash-based embeddings")
        return self._generate_fallback_embeddings(texts)
    
    def _generate_fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate simple hash-based embeddings as fallback."""
        import hashlib
        import struct
        
        embeddings = []
        for text in texts:
            # Create a simple hash-based embedding
            hash_obj = hashlib.sha256(text.encode('utf-8'))
            hash_bytes = hash_obj.digest()
            
            # Convert to 512-dimensional vector (as expected by schema)
            embedding = []
            for i in range(0, len(hash_bytes), 4):
                if len(embedding) >= 512:
                    break
                # Use 4 bytes to create a float
                chunk = hash_bytes[i:i+4]
                if len(chunk) == 4:
                    # Convert to float and normalize
                    val = struct.unpack('>I', chunk)[0] / (2**32)
                    embedding.append(val)
            
            # Pad or truncate to exactly 512 dimensions
            while len(embedding) < 512:
                embedding.append(0.0)
            embedding = embedding[:512]
            
            embeddings.append(embedding)
        
        return embeddings
    
    def _store_embeddings(self, chunk_mapping: Dict[str, str], embeddings: List[List[float]]):
        """Store embeddings in the database."""
        with self.driver.session() as session:
            for text, embedding in zip(chunk_mapping.keys(), embeddings):
                chunk_id = chunk_mapping[text]
                session.run(
                    "MATCH (ch:Chunk {id: $chunk_id}) SET ch.embedding = $embedding",
                    chunk_id=chunk_id,
                    embedding=embedding
                )
    
    def get_embedding_statistics(self) -> Dict[str, int]:
        """Get statistics about chunk embeddings."""
        with self.driver.session() as session:
            total_chunks = session.run("MATCH (ch:Chunk) RETURN count(ch) as count").single()["count"]
            chunks_with_embeddings = session.run(
                "MATCH (ch:Chunk) WHERE ch.embedding IS NOT NULL RETURN count(ch) as count"
            ).single()["count"]
            
            return {
                "total_chunks": total_chunks,
                "chunks_with_embeddings": chunks_with_embeddings,
                "chunks_without_embeddings": total_chunks - chunks_with_embeddings,
                "embedding_percentage": round((chunks_with_embeddings / max(1, total_chunks)) * 100, 2)
            }
