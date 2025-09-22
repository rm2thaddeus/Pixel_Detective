"""Chunk Ingestion Script for Temporal Semantic Dev Graph

Phase 2: Ingests documents and code files, creating chunks for semantic linking.
"""

import os
import glob
import fnmatch
from pathlib import Path
from typing import List, Dict, Any, Generator
from neo4j import Driver

from .chunkers import ChunkIngester, MarkdownChunker, CodeChunker


class ChunkIngestionService:
    """Service for ingesting chunks into the temporal semantic graph."""
    
    def __init__(self, driver: Driver, repo_path: str):
        self.driver = driver
        self.repo_path = repo_path
        self.ingester = ChunkIngester(driver, repo_path)
        
        # Configuration - Phase 0: Use extensions instead of glob patterns
        self.doc_extensions = ['.md', '.rst']
        self.code_extensions = ['.py', '.ts', '.tsx', '.js', '.jsx']
        self.exclude_patterns = [
            '**/node_modules/**',
            '**/__pycache__/**',
            '**/.git/**',
            '**/venv/**',
            '**/.venv/**',
            '**/env/**',
            '**/build/**',
            '**/dist/**',
            '**/target/**'
        ]
    
    def discover_documents(self) -> List[str]:
        """Discover markdown documents in the repository using streaming approach."""
        documents = list(self._stream_file_discovery(self.doc_extensions))
        return sorted(documents)
    
    def discover_code_files(self) -> List[str]:
        """Discover code files in the repository using streaming approach."""
        code_files = list(self._stream_file_discovery(self.code_extensions))
        return sorted(code_files)
    
    def _stream_file_discovery(self, extensions: List[str]) -> Generator[str, None, None]:
        """Stream file discovery to reduce memory footprint for large repositories.
        
        Phase 0 Performance Fix: Replace multiple recursive glob passes with 
        streaming os.walk approach.
        """
        for root, dirs, files in os.walk(self.repo_path):
            # Filter directories to exclude based on patterns
            dirs[:] = [d for d in dirs if not self._should_exclude_directory(d)]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check if file has matching extension
                if any(file.endswith(ext) for ext in extensions):
                    if self._should_include_file(file_path):
                        yield file_path
    
    def _should_include_file(self, file_path: str) -> bool:
        """Check if file should be included based on exclude patterns."""
        rel_path = os.path.relpath(file_path, self.repo_path)
        
        for exclude_pattern in self.exclude_patterns:
            if self._matches_pattern(rel_path, exclude_pattern):
                return False
        
        # Check file size (skip very large files)
        try:
            if os.path.getsize(file_path) > 1024 * 1024:  # 1MB
                return False
        except OSError:
            return False
        
        return True
    
    def _should_exclude_directory(self, dir_name: str) -> bool:
        """Check if directory should be excluded based on exclude patterns."""
        for exclude_pattern in self.exclude_patterns:
            # Extract the directory name part from the pattern
            # e.g., "**/node_modules/**" -> "node_modules"
            pattern_parts = exclude_pattern.split('/')
            for part in pattern_parts:
                if part and '*' not in part:  # Found a literal directory name
                    if dir_name == part:
                        return True
                # Skip glob patterns like "**" as they match everything
        return False
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for exclude patterns."""
        return fnmatch.fnmatch(path, pattern)
    
    def ingest_all_chunks(self, 
                         include_docs: bool = True, 
                         include_code: bool = True,
                         doc_limit: int = None,
                         code_limit: int = None) -> Dict[str, Any]:
        """Ingest all documents and code files, creating chunks.
        
        Args:
            include_docs: Whether to ingest documents
            include_code: Whether to ingest code files
            doc_limit: Maximum number of documents to process
            code_limit: Maximum number of code files to process
            
        Returns:
            Dictionary with ingestion statistics
        """
        stats = {
            'documents': {'processed': 0, 'chunks': 0, 'errors': 0},
            'code_files': {'processed': 0, 'chunks': 0, 'errors': 0},
            'total_chunks': 0,
            'total_errors': 0
        }
        
        if include_docs:
            print("Discovering documents...")
            documents = self.discover_documents()
            # Remove artificial limits - process ALL documents
            print(f"Found {len(documents)} documents to process")
            
            if documents:
                print("Ingesting documents...")
                doc_stats = self.ingester.ingest_documents(documents)
                stats['documents'] = doc_stats
                stats['total_chunks'] += doc_stats['chunks']
                stats['total_errors'] += doc_stats['errors']
        
        if include_code:
            print("Discovering code files...")
            code_files = self.discover_code_files()
            # Remove artificial limits - process ALL code files
            print(f"Found {len(code_files)} code files to process")
            
            if code_files:
                print("Ingesting code files...")
                code_stats = self.ingester.ingest_code_files(code_files)
                stats['code_files'] = code_stats
                stats['total_chunks'] += code_stats['chunks']
                stats['total_errors'] += code_stats['errors']
        
        return stats
    
    def ingest_specific_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Ingest specific files, auto-detecting document vs code."""
        stats = {
            'documents': {'processed': 0, 'chunks': 0, 'errors': 0},
            'code_files': {'processed': 0, 'chunks': 0, 'errors': 0},
            'total_chunks': 0,
            'total_errors': 0
        }
        
        documents = []
        code_files = []
        
        for file_path in file_paths:
            if self._is_document(file_path):
                documents.append(file_path)
            elif self._is_code_file(file_path):
                code_files.append(file_path)
        
        if documents:
            print(f"Ingesting {len(documents)} documents...")
            doc_stats = self.ingester.ingest_documents(documents)
            stats['documents'] = doc_stats
            stats['total_chunks'] += doc_stats['chunks']
            stats['total_errors'] += doc_stats['errors']
        
        if code_files:
            print(f"Ingesting {len(code_files)} code files...")
            code_stats = self.ingester.ingest_code_files(code_files)
            stats['code_files'] = code_stats
            stats['total_chunks'] += code_stats['chunks']
            stats['total_errors'] += code_stats['errors']
        
        return stats
    
    def _is_document(self, file_path: str) -> bool:
        """Check if file is a document based on extension."""
        doc_extensions = {'.md', '.rst', '.txt'}
        return Path(file_path).suffix.lower() in doc_extensions
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file based on extension."""
        code_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.cpp', '.c', '.h'}
        return Path(file_path).suffix.lower() in code_extensions
    
    def get_chunk_statistics(self) -> Dict[str, Any]:
        """Get statistics about existing chunks in the database."""
        with self.driver.session() as session:
            # Total chunks
            total_chunks = session.run("MATCH (ch:Chunk) RETURN count(ch) AS c").single()["c"]
            
            # Chunks by kind
            doc_chunks = session.run("MATCH (ch:Chunk {kind: 'doc'}) RETURN count(ch) AS c").single()["c"]
            code_chunks = session.run("MATCH (ch:Chunk {kind: 'code'}) RETURN count(ch) AS c").single()["c"]
            
            # Chunks with embeddings
            chunks_with_embeddings = session.run(
                "MATCH (ch:Chunk) WHERE ch.embedding IS NOT NULL RETURN count(ch) AS c"
            ).single()["c"]
            
            # Chunks by language (for code chunks)
            language_stats = session.run("""
                MATCH (ch:Chunk {kind: 'code'})-[:PART_OF]->(f:File)
                WHERE f.language IS NOT NULL
                RETURN f.language AS language, count(ch) AS count
                ORDER BY count DESC
            """).data()
            
            # Chunks by file type
            file_type_stats = session.run("""
                MATCH (ch:Chunk {kind: 'doc'})-[:CONTAINS_CHUNK]->(d:Document)
                RETURN d.type AS type, count(ch) AS count
                ORDER BY count DESC
            """).data()
            
            return {
                'total_chunks': total_chunks,
                'doc_chunks': doc_chunks,
                'code_chunks': code_chunks,
                'chunks_with_embeddings': chunks_with_embeddings,
                'language_distribution': language_stats,
                'file_type_distribution': file_type_stats
            }


def main():
    """CLI for chunk ingestion."""
    import argparse
    from neo4j import GraphDatabase
    
    parser = argparse.ArgumentParser(description='Ingest chunks for temporal semantic graph')
    parser.add_argument('--repo-path', required=True, help='Path to repository')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')
    parser.add_argument('--neo4j-user', default='neo4j', help='Neo4j username')
    parser.add_argument('--neo4j-password', help='Neo4j password')
    parser.add_argument('--doc-limit', type=int, help='Limit number of documents')
    parser.add_argument('--code-limit', type=int, help='Limit number of code files')
    parser.add_argument('--docs-only', action='store_true', help='Only ingest documents')
    parser.add_argument('--code-only', action='store_true', help='Only ingest code files')
    parser.add_argument('--files', nargs='+', help='Specific files to ingest')
    
    args = parser.parse_args()
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password)
    )
    
    try:
        # Create ingestion service
        service = ChunkIngestionService(driver, args.repo_path)
        
        if args.files:
            # Ingest specific files
            stats = service.ingest_specific_files(args.files)
        else:
            # Ingest all files
            stats = service.ingest_all_chunks(
                include_docs=not args.code_only,
                include_code=not args.docs_only,
                doc_limit=args.doc_limit,
                code_limit=args.code_limit
            )
        
        print("\nIngestion completed!")
        print(f"Documents processed: {stats['documents']['processed']}")
        print(f"Document chunks created: {stats['documents']['chunks']}")
        print(f"Code files processed: {stats['code_files']['processed']}")
        print(f"Code chunks created: {stats['code_files']['chunks']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Errors: {stats['total_errors']}")
        
        # Show chunk statistics
        chunk_stats = service.get_chunk_statistics()
        print(f"\nChunk Statistics:")
        print(f"Total chunks in database: {chunk_stats['total_chunks']}")
        print(f"Document chunks: {chunk_stats['doc_chunks']}")
        print(f"Code chunks: {chunk_stats['code_chunks']}")
        print(f"Chunks with embeddings: {chunk_stats['chunks_with_embeddings']}")
        
        if chunk_stats['language_distribution']:
            print(f"\nCode chunks by language:")
            for lang in chunk_stats['language_distribution']:
                print(f"  {lang['language']}: {lang['count']}")
    
    finally:
        driver.close()


if __name__ == '__main__':
    main()
