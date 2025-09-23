"""Chunk Ingestion Script for Temporal Semantic Dev Graph

Phase 2: Ingests documents and code files, creating chunks for semantic linking.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from neo4j import Driver

from .chunkers import ChunkIngester

logger = logging.getLogger(__name__)


class ChunkIngestionService:
    """Service for ingesting chunks into the temporal semantic graph."""

    def __init__(self, driver: Driver, repo_path: str):
        self.driver = driver
        self.repo_root = Path(repo_path).resolve()
        self.ingester = ChunkIngester(driver, repo_path)

        self.category_extensions = {
            'documents': {'.md', '.rst', '.mdx', '.txt', '.adoc'},
            'code': {'.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.kt', '.go', '.rs', '.rb', '.php', '.c', '.cpp', '.cs', '.swift'},
            'config': {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf'},
            'data': {'.csv', '.tsv', '.jsonl', '.parquet', '.xlsx', '.xls'},
        }
        self.doc_extensions = sorted(self.category_extensions['documents'])
        self.code_extensions = sorted(self.category_extensions['code'])
        self.excluded_dir_names = {
            '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
            'build', 'dist', 'target', '.mypy_cache', '.pytest_cache', '.cursor', '.vscode', '.idea'
        }
        self.max_file_size_bytes = 2 * 1024 * 1024  # keep ingestion performant

    @staticmethod
    def _format_limit(limit: Optional[int]) -> str:
        if limit is None:
            return "no limit"
        if limit <= 0:
            return f"{limit} (skip)"
        return str(limit)

    def discover_documents(self) -> List[str]:
        """Discover document files within the repository."""
        return self.discover_all_files()['documents']

    def discover_code_files(self) -> List[str]:
        """Discover code files within the repository."""
        return self.discover_all_files()['code']

    def discover_all_files(self) -> Dict[str, List[str]]:
        """Discover all candidate files grouped by category."""
        inventory: Dict[str, List[str]] = {key: [] for key in self.category_extensions}
        inventory['other'] = []

        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if not self._should_skip_directory(d)]

            for name in files:
                abs_path = Path(root) / name
                relative = self._normalize_repo_relative_path(abs_path)
                if not relative:
                    continue
                if not self._should_include_file(abs_path):
                    continue

                category = self._categorize_file(abs_path)
                inventory.setdefault(category, []).append(relative)

        for key in inventory:
            inventory[key].sort()

        return inventory

    def ingest_all_chunks(
        self,
        include_docs: bool = True,
        include_code: bool = True,
        doc_limit: Optional[int] = None,
        code_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ingest all documents and code files, creating chunks."""
        stats: Dict[str, Any] = {
            'documents': self._build_empty_ingestion_stats(),
            'code_files': self._build_empty_ingestion_stats(),
            'discovery': {},
            'limits': {'doc_limit': doc_limit, 'code_limit': code_limit},
            'samples': {},
            'total_chunks': 0,
            'total_errors': 0,
        }

        inventory = self.discover_all_files()
        stats['discovery'] = {category: len(paths) for category, paths in inventory.items()}
        stats['samples'] = {
            'documents': inventory.get('documents', [])[:5],
            'code': inventory.get('code', [])[:5],
            'config': inventory.get('config', [])[:3],
            'data': inventory.get('data', [])[:3],
        }

        doc_candidates = inventory.get('documents', [])
        code_candidates = inventory.get('code', [])

        stats['documents']['discovered'] = len(doc_candidates)
        stats['code_files']['discovered'] = len(code_candidates)

        if include_docs:
            doc_selection, doc_skipped = self._apply_limit(doc_candidates, doc_limit)
        else:
            doc_selection, doc_skipped = [], len(doc_candidates)

        if include_code:
            code_selection, code_skipped = self._apply_limit(code_candidates, code_limit)
        else:
            code_selection, code_skipped = [], len(code_candidates)

        stats['documents']['selected'] = len(doc_selection)
        stats['documents']['skipped_due_to_limit'] = doc_skipped
        stats['code_files']['selected'] = len(code_selection)
        stats['code_files']['skipped_due_to_limit'] = code_skipped

        if include_docs and doc_selection:
            logger.info("Ingesting %d/%d documents (limit=%s)", len(doc_selection), len(doc_candidates), self._format_limit(doc_limit))
            doc_start = time.time()
            doc_result = self.ingester.ingest_documents(doc_selection)
            stats['documents'].update({
                'processed': doc_result.get('documents', 0),
                'chunks': doc_result.get('chunks', 0),
                'errors': doc_result.get('errors', 0),
                'failures': doc_result.get('failures', []),
                'duration': time.time() - doc_start,
            })
        else:
            stats['documents']['duration'] = 0.0
            if include_docs:
                logger.info("Skipping document ingestion (limit=%s)", self._format_limit(doc_limit))

        if include_code and code_selection:
            logger.info("Ingesting %d/%d code files (limit=%s)", len(code_selection), len(code_candidates), self._format_limit(code_limit))
            code_start = time.time()
            code_result = self.ingester.ingest_code_files(code_selection)
            stats['code_files'].update({
                'processed': code_result.get('files', 0),
                'chunks': code_result.get('chunks', 0),
                'errors': code_result.get('errors', 0),
                'failures': code_result.get('failures', []),
                'duration': time.time() - code_start,
            })
        else:
            stats['code_files']['duration'] = 0.0
            if include_code:
                logger.info("Skipping code ingestion (limit=%s)", self._format_limit(code_limit))

        stats['total_chunks'] = stats['documents']['chunks'] + stats['code_files']['chunks']
        stats['total_errors'] = stats['documents']['errors'] + stats['code_files']['errors']

        return stats

    def ingest_specific_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Ingest specific files, auto-detecting document vs code."""
        normalized_paths = [self._prepare_ingest_path(path) for path in file_paths]
        normalized_paths = [path for path in normalized_paths if path]

        documents: List[str] = []
        code_files: List[str] = []

        for path in normalized_paths:
            category = self._categorize_file(Path(path))
            if category == 'documents':
                documents.append(path)
            elif category == 'code':
                code_files.append(path)
            else:
                logger.info("Skipping %s (unsupported ingestion category: %s)", path, category)

        stats: Dict[str, Any] = {
            'documents': self._build_empty_ingestion_stats(),
            'code_files': self._build_empty_ingestion_stats(),
            'discovery': {'documents': len(documents), 'code': len(code_files)},
            'limits': {'doc_limit': None, 'code_limit': None},
            'samples': {
                'documents': documents[:5],
                'code': code_files[:5],
            },
            'total_chunks': 0,
            'total_errors': 0,
        }

        if documents:
            logger.info("Ingesting %d specific documents", len(documents))
            doc_start = time.time()
            doc_result = self.ingester.ingest_documents(documents)
            stats['documents'].update({
                'discovered': len(documents),
                'selected': len(documents),
                'processed': doc_result.get('documents', 0),
                'chunks': doc_result.get('chunks', 0),
                'errors': doc_result.get('errors', 0),
                'failures': doc_result.get('failures', []),
                'duration': time.time() - doc_start,
            })

        if code_files:
            logger.info("Ingesting %d specific code files", len(code_files))
            code_start = time.time()
            code_result = self.ingester.ingest_code_files(code_files)
            stats['code_files'].update({
                'discovered': len(code_files),
                'selected': len(code_files),
                'processed': code_result.get('files', 0),
                'chunks': code_result.get('chunks', 0),
                'errors': code_result.get('errors', 0),
                'failures': code_result.get('failures', []),
                'duration': time.time() - code_start,
            })

        stats['total_chunks'] = stats['documents']['chunks'] + stats['code_files']['chunks']
        stats['total_errors'] = stats['documents']['errors'] + stats['code_files']['errors']

        return stats

    def get_chunk_statistics(self) -> Dict[str, Any]:
        """Get statistics about existing chunks in the database."""
        with self.driver.session() as session:
            total_chunks = session.run("MATCH (ch:Chunk) RETURN count(ch) AS c").single()["c"]

            doc_chunks = session.run("MATCH (ch:Chunk {kind: 'doc'}) RETURN count(ch) AS c").single()["c"]
            code_chunks = session.run("MATCH (ch:Chunk {kind: 'code'}) RETURN count(ch) AS c").single()["c"]

            chunks_with_embeddings = session.run(
                "MATCH (ch:Chunk) WHERE ch.embedding IS NOT NULL RETURN count(ch) AS c"
            ).single()["c"]

            language_stats = session.run("""
                MATCH (ch:Chunk {kind: 'code'})-[:PART_OF]->(f:File)
                WHERE f.language IS NOT NULL
                RETURN f.language AS language, count(ch) AS count
                ORDER BY count DESC
            """).data()

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
                'file_type_distribution': file_type_stats,
            }

    def _build_empty_ingestion_stats(self) -> Dict[str, Any]:
        return {
            'discovered': 0,
            'selected': 0,
            'processed': 0,
            'chunks': 0,
            'errors': 0,
            'failures': [],
            'skipped_due_to_limit': 0,
            'duration': 0.0,
        }

    def _apply_limit(self, paths: List[str], limit: Optional[int]) -> Tuple[List[str], int]:
        if limit is None:
            return list(paths), 0
        if limit <= 0:
            return [], len(paths)
        trimmed = list(paths[:limit])
        return trimmed, max(len(paths) - limit, 0)

    def _should_skip_directory(self, dirname: str) -> bool:
        return dirname.lower() in self.excluded_dir_names

    def _should_include_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            if path.stat().st_size > self.max_file_size_bytes:
                logger.debug(
                    "Skipping %s because it exceeds %s bytes",
                    path,
                    self.max_file_size_bytes,
                )
                return False
        except OSError as exc:
            logger.debug("Skipping %s: %s", path, exc)
            return False
        return True

    def _categorize_file(self, file_ref: Path) -> str:
        path = file_ref if isinstance(file_ref, Path) else Path(file_ref)
        ext = path.suffix.lower()
        for category, extensions in self.category_extensions.items():
            if ext in extensions:
                return category
        return 'other'

    def _normalize_repo_relative_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repo_root).as_posix()
        except (ValueError, RuntimeError):
            logger.debug("Skipping %s because it is outside the repository", path)
            return ''

    def _prepare_ingest_path(self, raw_path: str) -> Optional[str]:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = (self.repo_root / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.exists() or not candidate.is_file():
            logger.warning("Skipping %s because it does not exist or is not a file", raw_path)
            return None

        try:
            return candidate.relative_to(self.repo_root).as_posix()
        except ValueError:
            logger.warning("Skipping %s because it is outside the repository", raw_path)
            return None

    def _is_document(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.category_extensions['documents']

    def _is_code_file(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in self.category_extensions['code']


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

    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password)
    )

    try:
        service = ChunkIngestionService(driver, args.repo_path)

        if args.files:
            stats = service.ingest_specific_files(args.files)
        else:
            stats = service.ingest_all_chunks(
                include_docs=not args.code_only,
                include_code=not args.docs_only,
                doc_limit=args.doc_limit,
                code_limit=args.code_limit
            )

        print()
        print("Ingestion completed!")
        print(f"Documents discovered: {stats['documents']['discovered']}")
        print(f"Documents processed: {stats['documents']['processed']}")
        print(f"Document chunks created: {stats['documents']['chunks']}")
        print(f"Document errors: {stats['documents']['errors']}")
        if stats['documents']['failures']:
            print("  Sample document failures:")
            for failure in stats['documents']['failures'][:5]:
                print(f"    {failure['path']}: {failure['error']}")

        print()
        print(f"Code files discovered: {stats['code_files']['discovered']}")
        print(f"Code files processed: {stats['code_files']['processed']}")
        print(f"Code chunks created: {stats['code_files']['chunks']}")
        print(f"Code errors: {stats['code_files']['errors']}")
        if stats['code_files']['failures']:
            print("  Sample code failures:")
            for failure in stats['code_files']['failures'][:5]:
                print(f"    {failure['path']}: {failure['error']}")

        print()
        print("Other discoveries: "
              f"config={stats['discovery'].get('config', 0)}, "
              f"data={stats['discovery'].get('data', 0)}, "
              f"other={stats['discovery'].get('other', 0)}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Errors: {stats['total_errors']}")

        chunk_stats = service.get_chunk_statistics()
        print()
        print("Chunk Statistics:")
        print(f"Total chunks in database: {chunk_stats['total_chunks']}")
        print(f"Document chunks: {chunk_stats['doc_chunks']}")
        print(f"Code chunks: {chunk_stats['code_chunks']}")
        print(f"Chunks with embeddings: {chunk_stats['chunks_with_embeddings']}")

        if chunk_stats['language_distribution']:
            print("Code chunks by language:")
            for lang in chunk_stats['language_distribution']:
                print(f"  {lang['language']}: {lang['count']}")


    finally:
        driver.close()


if __name__ == '__main__':
    main()



