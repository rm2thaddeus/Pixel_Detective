"""Chunk Ingestion Script for Temporal Semantic Dev Graph

Phase 2: Ingests documents and code files, creating chunks for semantic linking.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any
from neo4j import Driver

from .chunkers import ChunkIngester, MarkdownChunker, CodeChunker


class ChunkIngestionService:
    """Service for ingesting chunks into the temporal semantic graph."""
    
    def __init__(self, driver: Driver, repo_path: str):
        self.driver = driver
        self.repo_path = repo_path
        self.ingester = ChunkIngester(driver, repo_path)
        
        # Configuration
        self.doc_patterns = [
            'docs/**/*.md',
            'docs/**/*.rst',
            '*.md',
            'README.md',
            'CHANGELOG.md',
            'CONTRIBUTING.md'
        ]
        self.code_patterns = [
            '**/*.py',
            '**/*.ts',
            '**/*.tsx',
            '**/*.js',
            '**/*.jsx'
        ]
        self.exclude_patterns = [
            '**/node_modules/**',
            '**/__pycache__/**',
            '**/.git/**',
            '**/venv/**',
            '**/env/**',
            '**/build/**',
            '**/dist/**',
            '**/target/**'
        ]
    
    def discover_documents(self) -> List[str]:
        """Discover markdown documents in the repository."""
        documents = []
        
        for pattern in self.doc_patterns:
            matches = glob.glob(os.path.join(self.repo_path, pattern), recursive=True)
            for match in matches:
                if self._should_include_file(match):
                    documents.append(match)
        
        return sorted(list(set(documents)))
    
    def discover_code_files(self) -> List[str]:
        """Discover code files in the repository."""
        code_files = []
        
        for pattern in self.code_patterns:
            matches = glob.glob(os.path.join(self.repo_path, pattern), recursive=True)
            for match in matches:
                if self._should_include_file(match):
                    code_files.append(match)
        
        return sorted(list(set(code_files)))
    
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
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Simple pattern matching for exclude patterns."""
        import fnmatch
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
            if doc_limit:
                documents = documents[:doc_limit]
            
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
            if code_limit:
                code_files = code_files[:code_limit]
            
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
