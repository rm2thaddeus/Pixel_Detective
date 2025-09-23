"""Chunk Ingestion Script for Temporal Semantic Dev Graph

Phase 2: Ingests documents and code files, creating chunks for semantic linking.
"""

import logging
import os
import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from concurrent.futures import ProcessPoolExecutor, as_completed

from neo4j import Driver

from .chunkers import ChunkIngester, MarkdownChunker, CodeChunker
from .ingestion_manifest import ManifestDiff, ManifestManager, ManifestSnapshot

logger = logging.getLogger(__name__)
def _render_document_chunks(task: Tuple[str, str]) -> Dict[str, Any]:
    """Worker helper to chunk a markdown document off the main process."""
    start_time = time.time()
    repo_root, relative_path = task
    normalized_path = Path(relative_path).as_posix()
    absolute = (Path(repo_root) / relative_path).resolve()
    try:
        content = absolute.read_text(encoding='utf-8')
    except Exception as exc:
        return {'document': None, 'error': str(exc), 'path': normalized_path}

    chunker = MarkdownChunker()
    chunks = chunker.chunk_document(normalized_path, content)
    for chunk in chunks:
        chunk.setdefault('content', chunk.get('text'))
        chunk.setdefault('requirements', [])
        chunk.setdefault('sprints', [])
        chunk.setdefault('embedding', chunk.get('embedding'))

    document = {
        'path': normalized_path,
        'title': Path(normalized_path).stem,
        'type': 'markdown',
        'uid': normalized_path,
        'extension': Path(normalized_path).suffix.lower(),
        'chunks': chunks,
        'duration': time.time() - start_time,
    }
    return {'document': document, 'error': None, 'path': normalized_path}


def _render_code_chunks(task: Tuple[str, str]) -> Dict[str, Any]:
    """Worker helper to chunk a code file off the main process."""
    start_time = time.time()
    repo_root, relative_path = task
    normalized_path = Path(relative_path).as_posix()
    absolute = (Path(repo_root) / relative_path).resolve()
    try:
        content = absolute.read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return {'file': None, 'error': str(exc), 'path': normalized_path}

    chunker = CodeChunker()
    language = chunker._detect_language(normalized_path)
    chunks = chunker.chunk_file(normalized_path, content, language)
    for chunk in chunks:
        chunk.setdefault('content', chunk.get('text'))
        chunk.setdefault('requirements', [])
        chunk.setdefault('symbol', chunk.get('symbol'))
        chunk.setdefault('symbol_type', chunk.get('symbol_type'))
        chunk.setdefault('embedding', chunk.get('embedding'))

    imports = _extract_code_imports(language, repo_root, absolute, normalized_path, content)
    payload = {
        'path': normalized_path,
        'language': language,
        'extension': Path(normalized_path).suffix.lower(),
        'chunks': chunks,
        'imports': imports,
        'duration': time.time() - start_time,
    }
    return {'file': payload, 'error': None, 'path': normalized_path}

_PY_IMPORT_RE = re.compile(r"^\s*import\s+([a-zA-Z_][\w\.]*)", re.MULTILINE)
_PY_FROM_RE = re.compile(r"^\s*from\s+([a-zA-Z_][\w\.]*)\s+import", re.MULTILINE)
_TS_IMPORT_RE = re.compile(r"""import\s+(?:[\w*\s{},]+?\s+from\s+)?['"]([^'"]+)['"]""")
_TS_REQUIRE_RE = re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)""")
_TS_EXTENSIONS = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs')


def _extract_code_imports(language: str, repo_root: str, absolute_path: Path, normalized_path: str, content: str) -> List[str]:
    repo_root_path = Path(repo_root).resolve()
    imports: Set[str] = set()

    if language == 'python':
        for module in _PY_IMPORT_RE.findall(content):
            imports.update(_resolve_python_module(repo_root_path, module))
        for module in _PY_FROM_RE.findall(content):
            imports.update(_resolve_python_module(repo_root_path, module))
    elif language in {'typescript', 'javascript'}:
        for source in _TS_IMPORT_RE.findall(content):
            imports.update(_resolve_ts_import(repo_root_path, absolute_path.parent, source))
        for source in _TS_REQUIRE_RE.findall(content):
            imports.update(_resolve_ts_import(repo_root_path, absolute_path.parent, source))

    imports.discard(normalized_path)
    return sorted(imports)


def _resolve_python_module(repo_root: Path, module: str) -> List[str]:
    module = module.strip()
    if not module or module.startswith('.'):
        return []

    parts = module.split('.')
    base_path = repo_root.joinpath(*parts)
    candidates: Set[str] = set()

    file_candidate = base_path.with_suffix('.py')
    if file_candidate.exists():
        rel = _relative_posix(file_candidate, repo_root)
        if rel:
            candidates.add(rel)

    init_candidate = base_path / '__init__.py'
    if init_candidate.exists():
        rel = _relative_posix(init_candidate, repo_root)
        if rel:
            candidates.add(rel)

    return sorted(candidates)


def _resolve_ts_import(repo_root: Path, current_dir: Path, source: str) -> List[str]:
    source = source.strip()
    if not source or not source.startswith('.'):
        return []

    base = (current_dir / source).resolve()
    candidates: Set[str] = set()

    possible_paths: List[Path] = []
    if base.suffix:
        possible_paths.append(base)
    else:
        for ext in _TS_EXTENSIONS:
            possible_paths.append(Path(str(base) + ext))
        if base.is_dir():
            for ext in _TS_EXTENSIONS:
                possible_paths.append(base / ('index' + ext))

    for candidate in possible_paths:
        if candidate.exists() and candidate.is_file():
            rel = _relative_posix(candidate, repo_root)
            if rel:
                candidates.add(rel)

    return sorted(candidates)


def _relative_posix(path: Path, repo_root: Path) -> Optional[str]:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return None




class ChunkIngestionService:
    """Service for ingesting chunks into the temporal semantic graph."""

    def __init__(self, driver: Driver, repo_path: str):
        self.driver = driver
        self.repo_root = Path(repo_path).resolve()
        self.ingester = ChunkIngester(driver, repo_path)
        self.manifest_manager = ManifestManager(repo_path)
        self.parallel_workers = max(2, min(8, (os.cpu_count() or 4)))
        self.chunk_batch_size = 800

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
        delta: bool = False,
        subpath: Optional[str] = None,
        manifest_manager: Optional[ManifestManager] = None,
        last_commit: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingest all documents and code files, creating chunks."""
        stats: Dict[str, Any] = {
            'documents': self._build_empty_ingestion_stats(),
            'code_files': self._build_empty_ingestion_stats(),
            'discovery': {},
            'limits': {
                'doc_limit': doc_limit,
                'code_limit': code_limit,
                'subpath': subpath,
                'delta': delta,
            },
            'samples': {},
            'total_chunks': 0,
            'total_errors': 0,
            'manifest': {
                'delta_mode': delta,
                'delta_applied': False,
                'added': 0,
                'modified': 0,
                'removed': 0,
                'unchanged': 0,
                'last_commit': last_commit,
                'snapshot_path': None,
            },
            'cleanup': {
                'paths_removed': 0,
                'documents_deleted': 0,
                'files_deleted': 0,
                'chunks_deleted': 0,
            },
        }
        stats['documents']['delta_filtered'] = 0
        stats['code_files']['delta_filtered'] = 0

        manager = manifest_manager or getattr(self, 'manifest_manager', None)
        manifest_snapshot: Optional[ManifestSnapshot] = None
        manifest_diff: Optional[ManifestDiff] = None

        inventory = self.discover_all_files()
        filtered_inventory: Dict[str, List[str]] = {
            category: list(paths)
            for category, paths in inventory.items()
        }

        if subpath:
            prefix = Path(subpath).as_posix().rstrip('/')
            if prefix:
                filtered_inventory = {
                    category: [path for path in paths if path.startswith(prefix)]
                    for category, paths in filtered_inventory.items()
                }

        stats['discovery'] = {category: len(paths) for category, paths in filtered_inventory.items()}
        stats['samples'] = {
            'documents': filtered_inventory.get('documents', [])[:5],
            'code': filtered_inventory.get('code', [])[:5],
            'config': filtered_inventory.get('config', [])[:3],
            'data': filtered_inventory.get('data', [])[:3],
        }

        doc_candidates = filtered_inventory.get('documents', [])
        code_candidates = filtered_inventory.get('code', [])
        stats['documents']['discovered'] = len(doc_candidates)
        stats['code_files']['discovered'] = len(code_candidates)

        if manager:
            try:
                manifest_snapshot = manager.build_snapshot(subpath=subpath, last_commit=last_commit)
                previous_snapshot = manager.load_previous()
                manifest_diff = ManifestManager.diff(previous_snapshot, manifest_snapshot)
                stats['manifest'].update({
                    'added': len(manifest_diff.added),
                    'modified': len(manifest_diff.modified),
                    'removed': len(manifest_diff.removed),
                    'unchanged': len(manifest_diff.unchanged),
                    'last_commit': manifest_snapshot.last_commit,
                    'snapshot_path': str(manager.storage_path),
                })
            except Exception as exc:
                logger.warning("Failed to build ingestion manifest: %s", exc)
                stats['manifest']['error'] = str(exc)
                manifest_snapshot = None
                manifest_diff = None

        if delta and manifest_diff:
            changed_paths = set(manifest_diff.touched)
            if include_docs:
                before = len(doc_candidates)
                doc_candidates = [path for path in doc_candidates if path in changed_paths]
                stats['documents']['delta_filtered'] = before - len(doc_candidates)
            else:
                doc_candidates = []
                stats['documents']['delta_filtered'] = 0
            if include_code:
                before = len(code_candidates)
                code_candidates = [path for path in code_candidates if path in changed_paths]
                stats['code_files']['delta_filtered'] = before - len(code_candidates)
            else:
                code_candidates = []
                stats['code_files']['delta_filtered'] = 0
            stats['manifest']['delta_applied'] = True
        else:
            stats['manifest']['delta_applied'] = False

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
            doc_start = time.time()
            doc_payloads, doc_failures = self._generate_document_payloads(doc_selection)
            if doc_failures:
                for failure in doc_failures:
                    logger.warning("Failed to chunk document %s: %s", failure['path'], failure['error'])
            self._write_document_batches(doc_payloads)
            stats['documents'].update({
                'processed': len(doc_payloads),
                'chunks': sum(len(doc.get('chunks', [])) for doc in doc_payloads),
                'errors': len(doc_failures),
                'failures': doc_failures,
                'duration': time.time() - doc_start,
            })
            stats['documents']['slowest'] = [
                {'path': doc.get('path'), 'duration': doc.get('duration', 0.0)}
                for doc in sorted(doc_payloads, key=lambda item: item.get('duration', 0.0), reverse=True)[:5]
            ]
        else:
            stats['documents']['duration'] = 0.0
            if include_docs:
                logger.info("Skipping document ingestion (no candidates after filtering)")

        if include_code and code_selection:
            code_start = time.time()
            code_payloads, code_failures = self._generate_code_payloads(code_selection)
            if code_failures:
                for failure in code_failures:
                    logger.warning("Failed to chunk code file %s: %s", failure['path'], failure['error'])
            self._write_code_batches(code_payloads)
            stats['code_files'].update({
                'processed': len(code_payloads),
                'chunks': sum(len(file.get('chunks', [])) for file in code_payloads),
                'errors': len(code_failures),
                'failures': code_failures,
                'duration': time.time() - code_start,
            })
        else:
            stats['code_files']['duration'] = 0.0
            if include_code:
                logger.info("Skipping code ingestion (no candidates after filtering)")

        stats['total_chunks'] = stats['documents']['chunks'] + stats['code_files']['chunks']
        stats['total_errors'] = stats['documents']['errors'] + stats['code_files']['errors']

        if manifest_diff and manifest_diff.removed:
            cleanup_summary = self._cleanup_removed_paths(manifest_diff.removed)
            cleanup_summary['paths_removed'] = len(manifest_diff.removed)
            stats['cleanup'].update(cleanup_summary)

        if manager and manifest_snapshot:
            try:
                manager.save_snapshot(manifest_snapshot)
            except Exception as exc:
                logger.warning("Failed to persist ingestion manifest: %s", exc)

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
        stats['slow_documents'] = stats['documents'].get('slowest', [])
        stats['slow_code'] = stats['code_files'].get('slowest', [])

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

    def _generate_document_payloads(self, doc_selection: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        payloads: List[Dict[str, Any]] = []
        failures: List[Dict[str, str]] = []
        if not doc_selection:
            return payloads, failures

        tasks = [(str(self.repo_root), path) for path in doc_selection]
        with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
            future_to_path = {executor.submit(_render_document_chunks, task): task[1] for task in tasks}
            for future in as_completed(future_to_path):
                path_hint = Path(future_to_path[future]).as_posix()
                try:
                    result = future.result()
                except Exception as exc:
                    failures.append({'path': path_hint, 'error': str(exc)})
                    continue

                if result.get('error'):
                    failures.append({'path': result.get('path', path_hint), 'error': result.get('error')})
                else:
                    payloads.append(result['document'])
        return payloads, failures


    def _write_document_batches(self, documents: List[Dict[str, Any]]) -> None:
        if not documents:
            return

        batch: List[Dict[str, Any]] = []
        chunk_budget = 0
        for document in documents:
            batch.append(document)
            chunk_budget += len(document.get('chunks', []))
            if chunk_budget >= self.chunk_batch_size:
                self._write_document_batch(batch)
                batch = []
                chunk_budget = 0

        if batch:
            self._write_document_batch(batch)


    def _write_document_batch(self, documents: List[Dict[str, Any]]) -> None:
        if not documents:
            return

        query = """
        UNWIND $documents AS doc
        MERGE (d:Document {path: doc.path})
        ON CREATE SET d.title = doc.title,
                      d.type = doc.type,
                      d.uid = doc.uid
        ON MATCH SET d.title = coalesce(d.title, doc.title),
                     d.type = coalesce(d.type, doc.type),
                     d.uid = coalesce(d.uid, doc.uid)
        MERGE (f:File {path: doc.path})
        SET f.is_doc = true,
            f.language = 'markdown',
            f.extension = doc.extension
        WITH doc, d, f
        UNWIND doc.chunks AS ch
        MERGE (c:Chunk {id: ch.id})
        ON CREATE SET
            c.kind = ch.kind,
            c.heading = ch.heading,
            c.section = ch.section,
            c.file_path = ch.file_path,
            c.span = ch.span,
            c.text = ch.text,
            c.content = ch.content,
            c.length = ch.length,
            c.uid = ch.uid,
            c.embedding = ch.embedding
        ON MATCH SET
            c.kind = coalesce(ch.kind, c.kind),
            c.heading = coalesce(ch.heading, c.heading),
            c.section = coalesce(ch.section, c.section),
            c.file_path = coalesce(ch.file_path, c.file_path),
            c.span = coalesce(ch.span, c.span),
            c.text = coalesce(ch.text, c.text),
            c.content = coalesce(ch.content, c.content),
            c.length = coalesce(ch.length, c.length),
            c.uid = coalesce(c.uid, ch.uid),
            c.embedding = coalesce(c.embedding, ch.embedding)
        MERGE (d)-[:CONTAINS_CHUNK]->(c)
        MERGE (c)-[:PART_OF]->(f)
        WITH c, ch
        FOREACH (req IN ch.requirements |
            MERGE (r:Requirement {id: req})
            MERGE (c)-[:MENTIONS]->(r)
        )
        """

        with self.driver.session() as session:
            session.execute_write(lambda tx: tx.run(query, documents=documents))


    def _generate_code_payloads(self, code_selection: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        payloads: List[Dict[str, Any]] = []
        failures: List[Dict[str, str]] = []
        if not code_selection:
            return payloads, failures

        tasks = [(str(self.repo_root), path) for path in code_selection]
        with ProcessPoolExecutor(max_workers=self.parallel_workers) as executor:
            future_to_path = {executor.submit(_render_code_chunks, task): task[1] for task in tasks}
            for future in as_completed(future_to_path):
                path_hint = Path(future_to_path[future]).as_posix()
                try:
                    result = future.result()
                except Exception as exc:
                    failures.append({'path': path_hint, 'error': str(exc)})
                    continue

                if result.get('error'):
                    failures.append({'path': result.get('path', path_hint), 'error': result.get('error')})
                else:
                    payloads.append(result['file'])
        return payloads, failures


    def _write_code_batches(self, files: List[Dict[str, Any]]) -> None:
        if not files:
            return

        batch: List[Dict[str, Any]] = []
        chunk_budget = 0
        for file_payload in files:
            batch.append(file_payload)
            chunk_budget += len(file_payload.get('chunks', []))
            if chunk_budget >= self.chunk_batch_size:
                self._write_code_batch(batch)
                batch = []
                chunk_budget = 0

        if batch:
            self._write_code_batch(batch)


    def _write_code_batch(self, files: List[Dict[str, Any]]) -> None:
        if not files:
            return

        query = """
        UNWIND $files AS file
        MERGE (f:File {path: file.path})
        SET f.language = file.language,
            f.is_code = true,
            f.extension = file.extension
        WITH file, f
        UNWIND file.chunks AS ch
        MERGE (c:Chunk {id: ch.id})
        ON CREATE SET
            c.kind = ch.kind,
            c.heading = ch.heading,
            c.section = ch.section,
            c.file_path = ch.file_path,
            c.span = ch.span,
            c.text = ch.text,
            c.content = ch.content,
            c.length = ch.length,
            c.uid = ch.uid,
            c.symbol = ch.symbol,
            c.symbol_type = ch.symbol_type,
            c.embedding = ch.embedding
        ON MATCH SET
            c.kind = coalesce(ch.kind, c.kind),
            c.heading = coalesce(ch.heading, c.heading),
            c.section = coalesce(ch.section, c.section),
            c.file_path = coalesce(ch.file_path, c.file_path),
            c.span = coalesce(ch.span, c.span),
            c.text = coalesce(ch.text, c.text),
            c.content = coalesce(ch.content, c.content),
            c.length = coalesce(ch.length, c.length),
            c.uid = coalesce(c.uid, ch.uid),
            c.symbol = coalesce(ch.symbol, c.symbol),
            c.symbol_type = coalesce(ch.symbol_type, c.symbol_type),
            c.embedding = coalesce(c.embedding, ch.embedding)
        MERGE (c)-[:PART_OF]->(f)
        WITH DISTINCT file, f
        UNWIND coalesce(file.imports, []) AS import_path
        MERGE (target:File {path: import_path})
        MERGE (f)-[:IMPORTS]->(target)
        """

        with self.driver.session() as session:
            session.execute_write(lambda tx: tx.run(query, files=files))

    def _cleanup_removed_paths(self, removed_paths: List[str]) -> Dict[str, int]:
        summary = {
            'documents_deleted': 0,
            'files_deleted': 0,
            'chunks_deleted': 0,
        }
        if not removed_paths:
            return summary

        with self.driver.session() as session:
            for repo_path in removed_paths:
                result = session.execute_write(self._delete_path_entities, repo_path)
                summary['documents_deleted'] += int(result.get('documents_deleted', 0) or 0)
                summary['files_deleted'] += int(result.get('files_deleted', 0) or 0)
                summary['chunks_deleted'] += int(result.get('chunks_deleted', 0) or 0)

        return summary


    def _delete_path_entities(self, tx, repo_path: str) -> Dict[str, int]:
        record = tx.run(
            """
            OPTIONAL MATCH (d:Document {path: $path})
            OPTIONAL MATCH (f:File {path: $path})
            WITH d, f
            OPTIONAL MATCH (d)-[:CONTAINS_CHUNK]->(doc_chunk:Chunk)
            WITH d, f, collect(DISTINCT doc_chunk) AS doc_chunks
            OPTIONAL MATCH (f)<-[:PART_OF]-(file_chunk:Chunk)
            WITH d, f, doc_chunks, collect(DISTINCT file_chunk) AS file_chunks
            WITH d, f,
                 [chunk IN doc_chunks WHERE chunk IS NOT NULL] + [chunk IN file_chunks WHERE chunk IS NOT NULL] AS chunk_candidates
            WITH d, f, chunk_candidates + [NULL] AS chunk_candidates
            UNWIND chunk_candidates AS candidate
            WITH d, f, collect(DISTINCT candidate) AS chunk_list
            WITH d, f, [chunk IN chunk_list WHERE chunk IS NOT NULL] AS chunk_list
            FOREACH (chunk IN chunk_list | DETACH DELETE chunk)
            FOREACH (node IN CASE WHEN d IS NULL THEN [] ELSE [d] END | DETACH DELETE node)
            FOREACH (node IN CASE WHEN f IS NULL THEN [] ELSE [f] END | DETACH DELETE node)
            RETURN
                CASE WHEN d IS NULL THEN 0 ELSE 1 END AS documents_deleted,
                CASE WHEN f IS NULL THEN 0 ELSE 1 END AS files_deleted,
                size(chunk_list) AS chunks_deleted
            """,
            path=repo_path,
        ).single()

        if not record:
            return {'documents_deleted': 0, 'files_deleted': 0, 'chunks_deleted': 0}

        return {
            'documents_deleted': int(record.get('documents_deleted', 0) or 0),
            'files_deleted': int(record.get('files_deleted', 0) or 0),
            'chunks_deleted': int(record.get('chunks_deleted', 0) or 0),
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
            'delta_filtered': 0,
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






