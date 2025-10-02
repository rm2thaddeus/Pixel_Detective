"""
Code Symbol Extractor for Enhanced Connectivity.

This module extracts code symbols (classes, functions, methods) from the
repository, stores them as first-class graph entities, and links them to
planning documentation and library usage signals.
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from neo4j import Driver

logger = logging.getLogger(__name__)


@dataclass
class SymbolRecord:
    symbol_id: str
    name: str
    qualified_name: str
    kind: str
    file_path: str
    language: str
    line_number: int
    signature: str
    parent: Optional[str] = None
    docstring: Optional[str] = None
    doc_preview: Optional[str] = None
    decorators: Sequence[str] = field(default_factory=list)
    bases: Sequence[str] = field(default_factory=list)
    interfaces: Sequence[str] = field(default_factory=list)
    return_type: Optional[str] = None
    is_async: bool = False
    exported: Optional[bool] = None

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["decorators"] = list(data.get("decorators") or [])
        data["bases"] = list(data.get("bases") or [])
        data["interfaces"] = list(data.get("interfaces") or [])
        return data


def _batched(items: Sequence, batch_size: int) -> Iterable[Sequence]:
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def _escape_fulltext_term(term: str) -> str:
    """Escape special characters in fulltext search terms."""
    # Escape Lucene special characters
    special_chars = ['+', '-', '&', '|', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
    escaped = term
    for char in special_chars:
        escaped = escaped.replace(char, f'\\{char}')
    return escaped


class CodeSymbolExtractor:
    "Extracts code symbols and creates enhanced connectivity edges."

    FILE_EXTENSIONS = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
    }

    def __init__(self, driver: Driver, repo_path: Union[str, Path], batch_size: int = 200):
        self.driver = driver
        self.repo_root = Path(repo_path).resolve()
        self.batch_size = batch_size
        self.logger = logger

        base_aliases = {
            "fastapi": "FastAPI",
            "starlette": "FastAPI",
            "neo4j": "Neo4j",
            "neo4j-driver": "Neo4j",
            "pydantic": "Pydantic",
            "uvicorn": "Uvicorn",
            "pytest": "pytest",
            "gitpython": "GitPython",
            "tenacity": "tenacity",
            "python-dotenv": "python-dotenv",
            "@chakra-ui": "Chakra UI",
            "@chakra-ui/react": "Chakra UI",
            "react": "React",
            "next": "Next.js",
            "next/router": "Next.js",
            "next/head": "Next.js",
            "d3": "D3.js",
            "d3-scale": "D3.js",
            "three": "Three.js",
            "graphology": "Graphology",
            "@tanstack/react-query": "React Query",
            "deck.gl": "Deck.GL",
            "framer-motion": "Framer Motion",
            "axios": "Axios",
            "lodash": "Lodash",
        }
        self.library_aliases: Dict[str, str] = {alias.lower(): canonical for alias, canonical in base_aliases.items()}

        base_doc_terms = {
            "FastAPI": ["FastAPI", "Fast API"],
            "Neo4j": ["Neo4j", "Neo4j Aura"],
            "Pydantic": ["Pydantic"],
            "Uvicorn": ["Uvicorn"],
            "Next.js": ["Next.js", "Nextjs", "Next JS"],
            "React": ["React"],
            "Chakra UI": ["Chakra UI", "chakra-ui"],
            "D3.js": ["D3.js", "D3"],
            "WebGL": ["WebGL"],
            "Graphology": ["Graphology"],
            "Deck.GL": ["Deck.GL", "deck.gl"],
            "React Query": ["React Query", "@tanstack/react-query"],
            "Framer Motion": ["Framer Motion", "framer-motion"],
            "Axios": ["Axios"],
            "Lodash": ["Lodash"],
        }
        self.doc_library_terms: Dict[str, Set[str]] = {name: set(terms) for name, terms in base_doc_terms.items()}
        self.manifest_aliases: Dict[str, str] = {}
        self._manifest_alias_signature: Optional[int] = None
        self._doc_terms_signature: Optional[int] = None

        self.ts_import_pattern = re.compile(
            r"import\s+(?:.+?\s+from\s+)?['\"](?P<module>[^'\"]+)['\"]|"
            r"require\(\s*['\"](?P<require>[^'\"]+)['\"]\s*\)|"
            r"import\(\s*['\"](?P<dynamic>[^'\"]+)['\"]\s*\)",
            re.MULTILINE,
        )
        self.ts_class_pattern = re.compile(
            r"(?P<export>export\s+)?class\s+(?P<name>[A-Za-z_][\w]*)\s*(?:extends\s+(?P<extends>[^{\s]+))?\s*(?:implements\s+(?P<implements>[^\{]+))?\s*\{",
            re.MULTILINE,
        )
        self.ts_interface_pattern = re.compile(
            r"(?P<export>export\s+)?interface\s+(?P<name>[A-Za-z_][\w]*)\s*(?:extends\s+(?P<extends>[^\{]+))?\s*\{",
            re.MULTILINE,
        )
        self.ts_function_pattern = re.compile(
            r"(?P<export>export\s+)?function\s+(?P<name>[A-Za-z_][\w]*)\s*(?P<signature>\([^\)]*\))",
            re.MULTILINE,
        )
        self.ts_arrow_function_pattern = re.compile(
            r"(?P<export>export\s+)?const\s+(?P<name>[A-Za-z_][\w]*)\s*=\s*(?:async\s+)?(?P<signature>\([^\)]*\)|[A-Za-z_][\w]*)\s*=>",
            re.MULTILINE,
        )
        self.ts_default_function_pattern = re.compile(
            r"export\s+default\s+function\s+(?P<name>[A-Za-z_][\w]*)?\s*(?P<signature>\([^\)]*\))",
            re.MULTILINE,
        )

    def _collect_manifest_entries(self) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        package_json = self.repo_root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception as exc:
                self.logger.warning("Failed to parse package.json: %s", exc)
            else:
                for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    section_data = data.get(section) or {}
                    if isinstance(section_data, dict):
                        for name, version in section_data.items():
                            if not isinstance(name, str):
                                continue
                            entries.append({
                                "package": name,
                                "version": str(version) if version is not None else None,
                                "source": "package.json",
                                "section": section,
                                "language": "javascript",
                            })
        requirements = self.repo_root / "requirements.txt"
        if requirements.exists():
            try:
                for raw_line in requirements.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = re.match(r"([A-Za-z0-9_.-]+)", line)
                    if not match:
                        continue
                    name = match.group(1)
                    remainder = line[len(name):].strip()
                    version = remainder or None
                    entries.append({
                        "package": name,
                        "version": version,
                        "source": "requirements.txt",
                        "section": "default",
                        "language": "python",
                    })
            except Exception as exc:
                self.logger.warning("Failed to parse requirements.txt: %s", exc)
        return entries

    def _generate_module_candidates(self, module: str) -> List[str]:
        if not module:
            return []
        module = module.strip()
        lowered = module.lower()
        if not lowered or lowered.startswith(('.', '/', '#')):
            return []
        candidates: List[str] = []

        def add(value: str) -> None:
            value = value.strip()
            if value and value not in candidates:
                candidates.append(value)

        add(lowered)
        if lowered.startswith('@'):
            parts = lowered.split('/')
            if len(parts) >= 2:
                add('/'.join(parts[:2]))
        else:
            if '/' in lowered:
                add(lowered.split('/')[0])
        if '.' in lowered:
            add(lowered.split('.')[0])
        return candidates

    def _canonicalize_library_name(self, package: str) -> Tuple[str, str]:
        slug = package.strip()
        slug_lower = slug.lower()
        canonical = self.library_aliases.get(slug_lower)
        if not canonical:
            if slug_lower.startswith('@'):
                canonical = slug
            elif '-' in slug or '_' in slug:
                canonical = slug.replace('-', ' ').replace('_', ' ').title()
            else:
                canonical = slug.capitalize()
        return canonical, slug_lower

    @staticmethod
    def _build_doc_terms(package: str, canonical: str) -> Set[str]:
        terms: Set[str] = {canonical}
        candidates = {
            package,
            package.replace('-', ' '),
            package.replace('_', ' '),
            package.replace('@', ''),
        }
        for value in candidates:
            value = value.strip()
            if value:
                terms.add(value)
        return terms

    def _enrich_manifest_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        alias_map: Dict[str, str] = {}
        doc_terms = {name: set(terms) for name, terms in self.doc_library_terms.items()}
        source_counter: Counter[str] = Counter()
        language_counter: Counter[str] = Counter()

        for entry in entries:
            canonical, slug = self._canonicalize_library_name(entry["package"])
            entry["display_name"] = canonical
            entry["slug"] = slug
            for candidate in self._generate_module_candidates(entry["package"]) + [slug]:
                alias_map[candidate] = canonical
            doc_terms.setdefault(canonical, set()).update(self._build_doc_terms(entry["package"], canonical))
            source_counter[entry["source"]] += 1
            if entry.get("language"):
                language_counter[entry["language"]] += 1

        alias_signature = hash(tuple(sorted(alias_map.items())))
        doc_signature = hash(tuple(sorted((library, tuple(sorted(terms))) for library, terms in doc_terms.items())))

        manifest_alias_changed = alias_signature != self._manifest_alias_signature
        doc_terms_changed = doc_signature != self._doc_terms_signature

        self._manifest_alias_signature = alias_signature
        self._doc_terms_signature = doc_signature
        self.manifest_aliases = alias_map
        self.doc_library_terms = doc_terms

        return {
            "manifest_entries": len(entries),
            "manifest_sources": dict(source_counter),
            "manifest_languages": dict(language_counter),
            "manifest_alias_changed": manifest_alias_changed,
            "doc_terms_changed": doc_terms_changed,
        }

    def _upsert_manifest_libraries(self, entries: List[Dict[str, Any]]) -> Dict[str, int]:
        if not entries:
            return {"manifest_libraries_seeded": 0, "manifest_entries": 0, "manifest_aliases_tracked": len(self.manifest_aliases)}
        stats = {"manifest_libraries_seeded": 0}
        payload = [
            {
                "name": entry["display_name"],
                "slug": entry["slug"],
                "version": entry.get("version"),
                "source": entry.get("source"),
                "section": entry.get("section"),
                "language": entry.get("language"),
            }
            for entry in entries
        ]
        with self.driver.session() as session:
            for batch in _batched(payload, self.batch_size):
                result = session.run(
                    """
                    UNWIND $batch AS library
                    MERGE (lib:Library {name: library.name})
                    ON CREATE SET
                        lib.created_at = datetime(),
                        lib.slug = library.slug,
                        lib.language = library.language,
                        lib.latest_version = library.version,
                        lib.manifest_sources = CASE WHEN library.source IS NULL THEN [] ELSE [library.source] END,
                        lib.manifest_sections = CASE WHEN library.section IS NULL THEN [] ELSE [library.section] END
                    WITH lib, library, coalesce(lib.manifest_sources, []) AS existing_sources, coalesce(lib.manifest_sections, []) AS existing_sections
                    SET lib.slug = coalesce(lib.slug, library.slug),
                        lib.language = coalesce(lib.language, library.language),
                        lib.latest_version = CASE WHEN library.version IS NOT NULL THEN library.version ELSE lib.latest_version END,
                        lib.manifest_sources = CASE
                            WHEN library.source IS NULL OR library.source IN existing_sources THEN existing_sources
                            ELSE existing_sources + library.source
                        END,
                        lib.manifest_sections = CASE
                            WHEN library.section IS NULL OR library.section IN existing_sections THEN existing_sections
                            ELSE existing_sections + library.section
                        END,
                        lib.last_manifest_seen = datetime()
                    RETURN count(lib) AS upserts
                    """,
                    batch=list(batch),
                )
                record = result.single()
                if record:
                    stats["manifest_libraries_seeded"] += int(record["upserts"] or 0)
        stats["manifest_entries"] = len(entries)
        stats["manifest_aliases_tracked"] = len(self.manifest_aliases)
        return stats

    def run_enhanced_connectivity(
        self,
        code_files: List[Union[str, Dict[str, Optional[str]]]],
        force_doc_refresh: bool = False,
    ) -> Dict[str, object]:
        manifest_entries = self._collect_manifest_entries()
        manifest_summary = self._enrich_manifest_entries(manifest_entries)
        manifest_stats = self._upsert_manifest_libraries(manifest_entries)
        manifest_stats.setdefault("manifest_aliases_tracked", len(self.manifest_aliases))
        doc_refresh_needed = force_doc_refresh or manifest_summary.get("doc_terms_changed", False)

        if not code_files:
            self.logger.info("No code files available for symbol extraction")
            result = {
                "files_processed": 0,
                "files_skipped": 0,
                "total_candidates": 0,
                "symbols_extracted": 0,
                "symbol_types": {},
                "library_usage_files": 0,
                "library_usage_total": 0,
                "doc_symbol_links_created": 0,
                "doc_symbol_rollups": 0,
                "co_occurrence_edges": 0,
                "library_doc_mentions": 0,
                "library_file_links": 0,
                "library_bridges": 0,
                "nodes_created": 0,
                "relationships_created": 0,
                "symbols_deleted": 0,
                "files_with_symbol_updates": 0,
                "errors": [],
            }
            result.update(manifest_summary)
            result.update(manifest_stats)
            result.setdefault("manifest_aliases_tracked", len(self.manifest_aliases))
            result["doc_library_refresh"] = doc_refresh_needed
            return result

        seen_paths: Set[str] = set()
        processed_symbols: List[SymbolRecord] = []
        symbol_type_counts: Counter[str] = Counter()
        library_usage: Dict[str, Counter[str]] = defaultdict(Counter)
        file_symbol_map: Dict[str, List[str]] = {}
        file_hash_updates: Dict[str, str] = {}
        files_processed = 0
        files_skipped = 0
        errors: List[Dict[str, str]] = []

        for entry in code_files:
            if isinstance(entry, str):
                rel_path = entry
                existing_hash = None
            else:
                rel_path = entry.get("path") if isinstance(entry, dict) else None
                existing_hash = entry.get("symbol_hash") if isinstance(entry, dict) else None
            if not rel_path:
                continue
            rel_path = rel_path.replace("\\", "/")
            if rel_path in seen_paths:
                continue
            seen_paths.add(rel_path)

            abs_path = (self.repo_root / rel_path).resolve()
            try:
                abs_path.relative_to(self.repo_root)
            except ValueError:
                errors.append({"path": rel_path, "error": "outside repository root"})
                continue
            if not abs_path.exists():
                errors.append({"path": rel_path, "error": "file missing on disk"})
                continue

            try:
                raw = abs_path.read_bytes()
            except OSError as exc:
                errors.append({"path": rel_path, "error": str(exc)})
                continue

            current_hash = hashlib.sha1(raw).hexdigest()
            if existing_hash and existing_hash == current_hash:
                files_skipped += 1
                continue

            extension = abs_path.suffix.lower()
            language = self.FILE_EXTENSIONS.get(extension)
            if not language:
                files_skipped += 1
                continue

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="ignore")

            relative_path = self._normalise_path(abs_path)
            if language == "python":
                symbols, libs = self._extract_python_symbols(relative_path, text)
            else:
                symbols, libs = self._extract_typescript_symbols(relative_path, text, language)

            file_symbol_map[relative_path] = [symbol.symbol_id for symbol in symbols]
            if symbols:
                processed_symbols.extend(symbols)
                symbol_type_counts.update(symbol.kind for symbol in symbols)
            if libs:
                library_usage[relative_path].update(libs)
            file_hash_updates[relative_path] = current_hash
            files_processed += 1

        upsert_stats = self._upsert_symbols(processed_symbols, file_symbol_map, file_hash_updates)

        doc_links = 0
        doc_rollup = 0
        if processed_symbols or force_doc_refresh:
            doc_links = self._link_symbols_to_docs(processed_symbols, force_full_refresh=force_doc_refresh)
            doc_rollup = self._rollup_document_symbol_links()

        co_occurrence_edges = self._create_co_occurrence_relationships()
        library_stats = self._create_library_relationships(library_usage, doc_refresh_needed)

        self.logger.info(
            "Enhanced connectivity processed %d/%d files, extracted %d symbols",
            files_processed,
            len(seen_paths),
            len(processed_symbols),
        )

        result = {
            "files_processed": files_processed,
            "files_skipped": files_skipped,
            "total_candidates": len(seen_paths),
            "symbols_extracted": len(processed_symbols),
            "symbol_types": dict(symbol_type_counts),
            "library_usage_files": len(library_usage),
            "library_usage_total": sum(sum(counter.values()) for counter in library_usage.values()),
            "doc_symbol_links_created": doc_links,
            "doc_symbol_rollups": doc_rollup,
            "co_occurrence_edges": co_occurrence_edges,
            "library_doc_mentions": library_stats.get("doc_mentions", 0),
            "library_file_links": library_stats.get("file_links", 0),
            "library_bridges": library_stats.get("bridges", 0),
            "nodes_created": upsert_stats.get("nodes_created", 0),
            "relationships_created": upsert_stats.get("relationships_created", 0),
            "symbols_deleted": upsert_stats.get("symbols_deleted", 0),
            "files_with_symbol_updates": len(file_symbol_map),
            "errors": errors[:20],
        }
        result.update(manifest_summary)
        result.update(manifest_stats)
        result.setdefault("manifest_aliases_tracked", len(self.manifest_aliases))
        result["doc_library_refresh"] = doc_refresh_needed
        return result
    def _upsert_symbols(
        self,
        symbols: List[SymbolRecord],
        file_symbol_map: Dict[str, List[str]],
        file_hash_updates: Dict[str, str],
    ) -> Dict[str, int]:
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "symbols_deleted": 0,
        }
        symbol_dicts = [symbol.to_dict() for symbol in symbols]
        if symbol_dicts:
            with self.driver.session() as session:
                for batch in _batched(symbol_dicts, self.batch_size):
                    result = session.run(
                        """
                        UNWIND $symbols AS symbol
                        MERGE (s:Symbol {symbol_id: symbol.symbol_id})
                        ON CREATE SET s.created_at = datetime()
                        SET s.name = symbol.name,
                            s.qualified_name = symbol.qualified_name,
                            s.kind = symbol.kind,
                            s.language = symbol.language,
                            s.file_path = symbol.file_path,
                            s.line_number = symbol.line_number,
                            s.signature = symbol.signature,
                            s.parent = symbol.parent,
                            s.docstring = symbol.docstring,
                            s.doc_preview = symbol.doc_preview,
                            s.decorators = symbol.decorators,
                            s.bases = symbol.bases,
                            s.interfaces = symbol.interfaces,
                            s.return_type = symbol.return_type,
                            s.is_async = symbol.is_async,
                            s.exported = symbol.exported,
                            s.updated_at = datetime()
                        MERGE (f:File {path: symbol.file_path})
                        ON CREATE SET f.created_at = datetime()
                        MERGE (s)-[rel:DEFINED_IN]->(f)
                        ON CREATE SET rel.created_at = datetime()
                        SET rel.last_seen = datetime()
                        """,
                        symbols=list(batch),
                    )
                    summary = result.consume()
                    stats["nodes_created"] += summary.counters.nodes_created
                    stats["relationships_created"] += summary.counters.relationships_created

        stale_payload = [
            {"file_path": path, "symbol_ids": ids}
            for path, ids in file_symbol_map.items()
        ]
        if stale_payload:
            with self.driver.session() as session:
                for batch in _batched(stale_payload, self.batch_size):
                    result = session.run(
                        """
                        UNWIND $batch AS file
                        MATCH (s:Symbol {file_path: file.file_path})
                        WHERE NOT s.symbol_id IN file.symbol_ids
                        WITH collect(id(s)) AS symbol_ids
                        UNWIND symbol_ids AS sid
                        MATCH (obsolete) WHERE id(obsolete) = sid
                        DETACH DELETE obsolete
                        RETURN count(sid) AS removed
                        """,
                        batch=list(batch),
                    )
                    record = result.single()
                    if record and record["removed"]:
                        stats["symbols_deleted"] += int(record["removed"])

        if file_hash_updates:
            updates_payload = [
                {"file_path": path, "hash": hash_value}
                for path, hash_value in file_hash_updates.items()
            ]
            with self.driver.session() as session:
                for batch in _batched(updates_payload, self.batch_size):
                    session.run(
                        """
                        UNWIND $batch AS file
                        MERGE (f:File {path: file.file_path})
                        SET f.symbol_hash = file.hash,
                            f.symbol_last_indexed_at = datetime()
                        """,
                        batch=list(batch),
                    )

        return stats

    def _extract_python_symbols(self, file_path: str, source: str) -> Tuple[List[SymbolRecord], Counter[str]]:
        symbols: List[SymbolRecord] = []
        libraries: Counter[str] = Counter()
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            self.logger.debug("Failed to parse %s: %s", file_path, exc)
            return symbols, libraries

        for module in self._collect_python_imports(tree):
            library = self._map_library(module)
            if library:
                libraries[library] += 1

        definition_stack: List[Tuple[str, str]] = []

        def visit(node: ast.AST) -> None:
            if isinstance(node, ast.ClassDef):
                definition_stack.append((node.name, "class"))
                qualified = ".".join(name for name, _ in definition_stack)
                docstring = ast.get_docstring(node)
                decorators = []
                for dec in getattr(node, "decorator_list", []):
                    value = self._unparse(dec)
                    if value:
                        decorators.append(value)
                bases = []
                for base in node.bases:
                    value = self._unparse(base)
                    if value:
                        bases.append(value)
                record = SymbolRecord(
                    symbol_id=self._build_symbol_id(file_path, "class", qualified),
                    name=node.name,
                    qualified_name=qualified,
                    kind="class",
                    file_path=file_path,
                    language="python",
                    line_number=getattr(node, "lineno", 0),
                    signature="",
                    parent=definition_stack[-2][0] if len(definition_stack) > 1 and definition_stack[-2][1] == "class" else None,
                    docstring=docstring,
                    doc_preview=self._preview(docstring),
                    decorators=decorators,
                    bases=bases,
                )
                symbols.append(record)
                for child in node.body:
                    visit(child)
                definition_stack.pop()
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parent_name = definition_stack[-1][0] if definition_stack else None
                parent_type = definition_stack[-1][1] if definition_stack else None
                qualified_segments = [name for name, _ in definition_stack] + [node.name]
                qualified = ".".join(qualified_segments)
                docstring = ast.get_docstring(node)
                decorators = []
                for dec in getattr(node, "decorator_list", []):
                    value = self._unparse(dec)
                    if value:
                        decorators.append(value)
                return_type = self._unparse(getattr(node, "returns", None))
                record = SymbolRecord(
                    symbol_id=self._build_symbol_id(file_path, "method" if parent_type == "class" else "function", qualified),
                    name=node.name,
                    qualified_name=qualified,
                    kind="method" if parent_type == "class" else "function",
                    file_path=file_path,
                    language="python",
                    line_number=getattr(node, "lineno", 0),
                    signature=self._format_python_signature(node.args),
                    parent=parent_name if parent_type == "class" else None,
                    docstring=docstring,
                    doc_preview=self._preview(docstring),
                    decorators=decorators,
                    return_type=return_type,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )
                symbols.append(record)
                definition_stack.append((node.name, "function"))
                for child in node.body:
                    visit(child)
                definition_stack.pop()
            else:
                for child in ast.iter_child_nodes(node):
                    visit(child)

        visit(tree)
        return symbols, libraries

    def _collect_python_imports(self, tree: ast.AST) -> Set[str]:
        modules: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules
    def _extract_typescript_symbols(self, file_path: str, source: str, language: str) -> Tuple[List[SymbolRecord], Counter[str]]:
        symbols: List[SymbolRecord] = []
        libraries: Counter[str] = Counter()

        for match in self.ts_import_pattern.finditer(source):
            module = None
            try:
                module = match.group("module")
            except IndexError:
                pass
            if not module:
                try:
                    module = match.group("require")
                except IndexError:
                    pass
            if not module:
                continue
            library = self._map_library(module)
            if library:
                libraries[library] += 1

        seen: Set[Tuple[str, str]] = set()
        for pattern, kind in (
            (self.ts_class_pattern, "class"),
            (self.ts_interface_pattern, "interface"),
        ):
            for match in pattern.finditer(source):
                name = match.group("name")
                if not name:
                    continue
                key = (kind, name)
                if key in seen:
                    continue
                seen.add(key)
                extends = match.group("extends")
                implements_raw = match.group("implements") if "implements" in match.groupdict() and match.group("implements") else None
                implements = [item.strip() for item in implements_raw.split(",")] if implements_raw else []
                bases = [extends.strip()] if extends else []
                record = SymbolRecord(
                    symbol_id=self._build_symbol_id(file_path, kind, name),
                    name=name,
                    qualified_name=name,
                    kind=kind,
                    file_path=file_path,
                    language=language,
                    line_number=self._line_number(source, match.start("name")),
                    signature="",
                    bases=bases,
                    interfaces=implements,
                    exported=bool(match.group("export")),
                )
                symbols.append(record)

        for match in self.ts_function_pattern.finditer(source):
            name = match.group("name")
            if not name:
                continue
            key = ("function", name)
            if key in seen:
                continue
            seen.add(key)
            signature = match.group("signature") or "()"
            record = SymbolRecord(
                symbol_id=self._build_symbol_id(file_path, "function", name),
                name=name,
                qualified_name=name,
                kind="function",
                file_path=file_path,
                language=language,
                line_number=self._line_number(source, match.start("name")),
                signature=signature,
                exported=bool(match.group("export")),
            )
            symbols.append(record)

        for match in self.ts_arrow_function_pattern.finditer(source):
            name = match.group("name")
            if not name:
                continue
            key = ("function", name)
            if key in seen:
                continue
            seen.add(key)
            signature = match.group("signature") or "()"
            if not signature.startswith("("):
                signature = f"({signature})"
            record = SymbolRecord(
                symbol_id=self._build_symbol_id(file_path, "function", name),
                name=name,
                qualified_name=name,
                kind="function",
                file_path=file_path,
                language=language,
                line_number=self._line_number(source, match.start("name")),
                signature=signature,
                exported=bool(match.group("export")),
            )
            symbols.append(record)

        for match in self.ts_default_function_pattern.finditer(source):
            name = match.group("name") or "default"
            key = ("function", name)
            if key in seen:
                continue
            seen.add(key)
            signature = match.group("signature") or "()"
            record = SymbolRecord(
                symbol_id=self._build_symbol_id(file_path, "function", name),
                name=name,
                qualified_name=name,
                kind="function",
                file_path=file_path,
                language=language,
                line_number=self._line_number(source, match.start()),
                signature=signature,
                exported=True,
            )
            symbols.append(record)

        return symbols, libraries

    def _link_symbols_to_docs(
        self,
        symbols: Iterable[SymbolRecord],
        force_full_refresh: bool = False,
    ) -> int:
        if force_full_refresh:
            symbol_terms = self._load_all_symbol_terms()
        else:
            symbol_terms = self._build_symbol_search_terms(symbols)
        if not symbol_terms:
            return 0
        total = 0
        with self.driver.session() as session:
            for batch in _batched(symbol_terms, self.batch_size):
                # Escape terms for fulltext search
                escaped_batch = [
                    {**symbol, "escaped_term": _escape_fulltext_term(symbol["term"])}
                    for symbol in batch
                ]
                result = session.run(
                    """
                    UNWIND $symbols AS symbol
                    MATCH (s:Symbol {symbol_id: symbol.symbol_id})
                    CALL db.index.fulltext.queryNodes('chunk_fulltext', symbol.escaped_term) YIELD node, score
                    WHERE coalesce(node.kind, 'doc') IN ['doc', 'document', 'markdown']
                    WITH node, s, score, symbol.term AS term
                    ORDER BY score DESC
                    WITH DISTINCT node, s, collect(score)[0] AS best_score, term
                    MERGE (node)-[rel:MENTIONS_SYMBOL]->(s)
                    ON CREATE SET rel.created_at = datetime(), rel.term = term
                    SET rel.last_seen = datetime(), rel.score = best_score
                    RETURN count(rel) AS relationships
                    """,
                    symbols=escaped_batch,
                )
                record = result.single()
                if record and record["relationships"]:
                    total += int(record["relationships"])
        return total

    def _rollup_document_symbol_links(self) -> int:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (doc:Document)-[:CONTAINS_CHUNK]->(chunk:Chunk)-[:MENTIONS_SYMBOL]->(symbol:Symbol)
                WITH doc, symbol, count(chunk) AS occurrences
                MERGE (doc)-[rel:MENTIONS_SYMBOL]->(symbol)
                ON CREATE SET rel.created_at = datetime()
                SET rel.last_seen = datetime(), rel.occurrences = occurrences
                RETURN count(rel) AS relationships
                """
            )
            record = result.single()
            return int(record["relationships"]) if record else 0

    def _create_co_occurrence_relationships(self) -> int:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:GitCommit)-[:TOUCHED]->(f1:File)
                MATCH (c)-[:TOUCHED]->(f2:File)
                WHERE f1.path < f2.path
                WITH f1, f2, count(DISTINCT c) AS weight
                WHERE weight > 1
                MERGE (f1)-[rel:CO_OCCURS_WITH]->(f2)
                ON CREATE SET rel.created_at = datetime()
                SET rel.weight = weight,
                    rel.last_seen = datetime()
                RETURN count(rel) AS relationships
                """
            )
            record = result.single()
            return int(record["relationships"]) if record else 0

    def _create_library_relationships(
        self,
        library_usage: Dict[str, Counter[str]],
        refresh_docs: bool,
    ) -> Dict[str, int]:
        stats = {"doc_mentions": 0, "file_links": 0, "bridges": 0}
        usage_payload = [
            {"file_path": file_path, "library": library, "count": int(count)}
            for file_path, counter in library_usage.items()
            for library, count in counter.items()
        ]

        with self.driver.session() as session:
            if usage_payload:
                for batch in _batched(usage_payload, self.batch_size):
                    result = session.run(
                        """
                        UNWIND $batch AS usage
                        MERGE (lib:Library {name: usage.library})
                        ON CREATE SET lib.created_at = datetime()
                        MERGE (f:File {path: usage.file_path})
                        SET f.last_library_scan = datetime()
                        MERGE (f)-[rel:USES_LIBRARY]->(lib)
                        ON CREATE SET rel.created_at = datetime(), rel.source = 'import'
                        SET rel.count = usage.count,
                            rel.last_seen = datetime()
                        RETURN count(rel) AS relationships
                        """,
                        batch=list(batch),
                    )
                    record = result.single()
                    if record and record["relationships"]:
                        stats["file_links"] += int(record["relationships"])

                removal_payload = [
                    {"file_path": file_path, "libraries": list(counter.keys())}
                    for file_path, counter in library_usage.items()
                ]
                for batch in _batched(removal_payload, self.batch_size):
                    session.run(
                        """
                        UNWIND $batch AS file
                        MATCH (f:File {path: file.file_path})-[rel:USES_LIBRARY]->(lib:Library)
                        WHERE NOT lib.name IN file.libraries
                        DELETE rel
                        """,
                        batch=list(batch),
                    )

            refresh_doc_mentions = refresh_docs
            if not refresh_doc_mentions:
                record = session.run(
                    "MATCH (:Library)<-[:MENTIONS_LIBRARY]-(:Chunk) RETURN count(*) AS mentions"
                ).single()
                refresh_doc_mentions = record and record["mentions"] == 0

            if refresh_doc_mentions:
                doc_terms = [
                    {"library": library, "term": term}
                    for library, terms in self.doc_library_terms.items()
                    for term in terms
                ]
                if doc_terms:
                    # Escape terms for fulltext search
                    escaped_terms = [
                        {**term, "escaped_term": _escape_fulltext_term(term["term"])}
                        for term in doc_terms
                    ]
                    result = session.run(
                        """
                        UNWIND $terms AS item
                        CALL db.index.fulltext.queryNodes('chunk_fulltext', item.escaped_term) YIELD node, score
                        WHERE coalesce(node.kind, 'doc') IN ['doc', 'document', 'markdown']
                        WITH node, item.library AS library, score, item.term AS term
                        ORDER BY score DESC
                        WITH DISTINCT node, library, collect(score)[0] AS best_score, term
                        MERGE (lib:Library {name: library})
                        ON CREATE SET lib.created_at = datetime()
                        MERGE (node)-[rel:MENTIONS_LIBRARY]->(lib)
                        ON CREATE SET rel.created_at = datetime(), rel.term = term
                        SET rel.last_seen = datetime(), rel.score = best_score
                        RETURN count(rel) AS relationships
                        """,
                        terms=escaped_terms,
                    )
                    record = result.single()
                    if record and record["relationships"]:
                        stats["doc_mentions"] += int(record["relationships"])

            if usage_payload or refresh_doc_mentions:
                result = session.run(
                    """
                    MATCH (chunk:Chunk)-[:MENTIONS_LIBRARY]->(lib:Library)<-[:USES_LIBRARY]-(file:File)
                    WHERE chunk.kind IN ['doc', 'document', 'markdown']
                    WITH DISTINCT chunk, lib, file
                    MERGE (chunk)-[rel:RELATES_TO {via: 'library', library: lib.name}]->(file)
                    ON CREATE SET rel.created_at = datetime()
                    SET rel.last_seen = datetime()
                    RETURN count(rel) AS relationships
                    """
                )
                record = result.single()
                if record and record["relationships"]:
                    stats["bridges"] = int(record["relationships"])

        return stats

    def _load_all_symbol_terms(self) -> List[Dict[str, str]]:
        with self.driver.session() as session:
            records = session.run(
                "MATCH (s:Symbol) RETURN s.symbol_id AS symbol_id, s.name AS name, s.qualified_name AS qualified_name"
            )
            terms: List[Dict[str, str]] = []
            for record in records:
                terms.extend(
                    self._build_symbol_terms_from_values(
                        record["symbol_id"],
                        record.get("name"),
                        record.get("qualified_name"),
                    )
                )
            return terms

    def _build_symbol_search_terms(self, symbols: Iterable[SymbolRecord]) -> List[Dict[str, str]]:
        terms: List[Dict[str, str]] = []
        for record in symbols:
            terms.extend(self._build_symbol_terms_from_values(record.symbol_id, record.name, record.qualified_name))
        return terms

    def _build_symbol_terms_from_values(
        self,
        symbol_id: str,
        name: Optional[str],
        qualified_name: Optional[str],
    ) -> List[Dict[str, str]]:
        values: List[str] = []
        if name:
            values.append(name)
        if qualified_name and qualified_name != name:
            values.append(qualified_name)
        terms: List[Dict[str, str]] = []
        seen: Set[Tuple[str, str]] = set()
        for value in values:
            normalized = value.strip()
            if len(normalized) < 3:
                continue
            key = (symbol_id, normalized.lower())
            if key in seen:
                continue
            seen.add(key)
            query = normalized if " " not in normalized else f"\"{normalized}\""
            terms.append({"symbol_id": symbol_id, "term": query})
        return terms

    def _map_library(self, module: str) -> Optional[str]:
        for candidate in self._generate_module_candidates(module):
            if candidate in self.library_aliases:
                return self.library_aliases[candidate]
            if candidate in self.manifest_aliases:
                return self.manifest_aliases[candidate]
        return None

    def _format_python_signature(self, args: ast.arguments) -> str:
        parts: List[str] = [arg.arg for arg in args.args]
        if getattr(args, "vararg", None):
            parts.append(f"*{args.vararg.arg}")
        elif getattr(args, "kwonlyargs", None):
            parts.append("*")
        for arg in getattr(args, "kwonlyargs", []):
            parts.append(arg.arg)
        if getattr(args, "kwarg", None):
            parts.append(f"**{args.kwarg.arg}")
        return "(" + ", ".join(parts) + ")"

    def _unparse(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                value = self._unparse(node.value)
                return f"{value}.{node.attr}" if value else node.attr
            if isinstance(node, ast.Constant):
                return repr(node.value)
            return None

    def _preview(self, text: Optional[str], max_length: int = 160) -> Optional[str]:
        if not text:
            return None
        preview = text.strip().splitlines()[0].strip()
        if len(preview) > max_length:
            preview = preview[: max_length - 3] + "..."
        return preview

    def _normalise_path(self, path: Path) -> str:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(self.repo_root)
        except ValueError:
            relative = resolved
        return relative.as_posix()

    def _line_number(self, source: str, index: int) -> int:
        return source.count("\n", 0, index) + 1

    def _build_symbol_id(self, file_path: str, kind: str, qualified_name: str) -> str:
        return f"{file_path}::{kind}::{qualified_name}"







