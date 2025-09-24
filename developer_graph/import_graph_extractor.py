"""Import graph extraction service for Developer Graph."""

from __future__ import annotations

import ast
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from neo4j import Driver

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportHit:
    target: str
    module: Optional[str]
    symbol: Optional[str]
    line: Optional[int]


@dataclass
class ImportEdge:
    source: str
    target: str
    language: str
    modules: Set[str] = field(default_factory=set)
    symbols: Set[str] = field(default_factory=set)
    lines: Set[int] = field(default_factory=set)

    def add(self, module: Optional[str], symbol: Optional[str], line: Optional[int]) -> None:
        if module:
            self.modules.add(module)
        if symbol and symbol != "*":
            self.symbols.add(symbol)
        if line:
            self.lines.add(int(line))

    def to_payload(self) -> Dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "language": self.language,
            "modules": sorted(self.modules),
            "symbols": sorted(self.symbols),
            "lines": sorted(self.lines),
            "count": max(len(self.lines), len(self.modules), 1),
        }


class ImportGraphExtractor:
    """Parses repository code to populate (:File)-[:IMPORTS]->(:File) relationships."""

    SUPPORTED_LANGUAGES = {"python", "typescript", "javascript"}
    PYTHON_EXTENSIONS = (".py",)
    TS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")

    def __init__(self, driver: Driver, repo_path: str | Path, batch_size: int = 500):
        self.driver = driver
        self.repo_root = Path(repo_path).resolve()
        self.batch_size = batch_size
        self.logger = logger
        self._ts_import_pattern = re.compile(
            r"""
            import\s+(?:[^'"`]+?\s+from\s+)?["'`](?P<module>[^'"`]+)["'`]
            |require\(\s*["'`](?P<require>[^'"`]+)["'`]\s*\)
            |import\(\s*["'`](?P<dynamic>[^'"`]+)["'`]\s*\)
            """,
            re.MULTILINE | re.VERBOSE,
        )

    def refresh_import_graph(self, subpath: Optional[str] = None) -> Dict[str, object]:
        code_files = self._load_code_files(subpath=subpath)
        if not code_files:
            return {
                "files_considered": 0,
                "files_processed": 0,
                "files_with_imports": 0,
                "edges_resolved": 0,
                "import_statements": 0,
                "relationships_created": 0,
                "relationships_upserted": 0,
                "relationships_deleted": 0,
            }

        path_index = {item["path"] for item in code_files}
        python_index = self._build_python_module_index(code_files)
        edges: Dict[Tuple[str, str], ImportEdge] = {}
        processed_paths: Set[str] = set()
        files_with_imports = 0
        import_statements = 0
        failures: List[Dict[str, str]] = []

        self.logger.info("ImportGraphExtractor: scanning %d code files", len(code_files))

        for file_info in code_files:
            path = file_info["path"]
            language = (file_info.get("language") or self._infer_language(path)).lower()

            if language not in self.SUPPORTED_LANGUAGES:
                continue

            absolute_path = self.repo_root / path
            if not absolute_path.exists():
                failures.append({"path": path, "error": "missing-on-disk"})
                continue

            try:
                text = absolute_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                text = absolute_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                failures.append({"path": path, "error": str(exc)})
                self.logger.warning("ImportGraphExtractor: unable to read %s: %s", path, exc)
                continue

            if language == "python":
                hits = self._collect_python_imports(path, text, python_index)
            else:
                hits = self._collect_ts_imports(path, text, path_index)

            if hits is None:
                failures.append({"path": path, "error": "parse-error"})
                continue

            processed_paths.add(path)

            if hits:
                files_with_imports += 1

            for hit in hits:
                key = (path, hit.target)
                edge = edges.get(key)
                if edge is None:
                    edge = ImportEdge(source=path, target=hit.target, language=language)
                    edges[key] = edge
                edge.add(hit.module, hit.symbol, hit.line)
                import_statements += 1

        payloads = [edge.to_payload() for edge in edges.values()]
        write_stats = self._write_relationships(payloads, processed_paths)

        stats = {
            "files_considered": len(code_files),
            "files_processed": len(processed_paths),
            "files_with_imports": files_with_imports,
            "edges_resolved": len(payloads),
            "import_statements": import_statements,
            "relationships_created": write_stats["relationships_created"],
            "relationships_upserted": write_stats["relationships_upserted"],
            "relationships_deleted": write_stats["relationships_deleted"],
            "run_id": write_stats["run_id"],
        }

        if failures:
            stats["error_count"] = len(failures)
            stats["errors"] = failures[:10]

        self.logger.info(
            "ImportGraphExtractor: processed %d files, resolved %d import edges",
            stats["files_processed"],
            stats["edges_resolved"],
        )

        return stats

    def _load_code_files(self, subpath: Optional[str] = None) -> List[Dict[str, str]]:
        query = [
            "MATCH (f:File)",
            "WHERE coalesce(f.is_code, false)",
        ]
        params: Dict[str, object] = {}
        if subpath:
            normalized = subpath.replace("\\", "/").strip("/")
            query.append("AND f.path STARTS WITH $subpath")
            params["subpath"] = normalized
        query.append("RETURN f.path AS path, toLower(f.language) AS language, f.extension AS extension ORDER BY f.path")

        cypher = "\n".join(query)
        with self.driver.session() as session:
            result = session.run(cypher, **params)
            files: List[Dict[str, str]] = []
            for record in result:
                path = record.get("path")
                language = (record.get("language") or "").lower()
                extension = (record.get("extension") or "").lower()
                if isinstance(path, str):
                    files.append({"path": path, "language": language, "extension": extension})
            return files

    def _infer_language(self, path: str) -> str:
        suffix = Path(path).suffix.lower()
        if suffix in self.PYTHON_EXTENSIONS:
            return "python"
        if suffix in {".ts", ".tsx"}:
            return "typescript"
        if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
            return "javascript"
        return ""

    def _build_python_module_index(self, code_files: Sequence[Dict[str, str]]) -> Dict[str, str]:
        index: Dict[str, str] = {}
        for info in code_files:
            path = info["path"]
            if not any(path.endswith(ext) for ext in self.PYTHON_EXTENSIONS):
                continue
            module_name = self._python_module_name(path)
            if module_name:
                index[module_name] = path
                if path.endswith("__init__.py"):
                    index[f"{module_name}.__init__"] = path
        return index

    def _python_module_name(self, path: str) -> str:
        relative = Path(path)
        parts = list(relative.parts)
        if not parts:
            return ""
        if relative.name == "__init__.py":
            parts = parts[:-1]
        else:
            stem = parts[-1]
            if "." in stem:
                stem = stem.split(".", 1)[0]
            parts[-1] = stem
        return ".".join(part for part in parts if part)

    def _python_package_parts(self, path: str, module_name: str) -> List[str]:
        if not module_name:
            return []
        parts = module_name.split(".")
        if Path(path).name == "__init__.py":
            return parts
        if len(parts) <= 1:
            return []
        return parts[:-1]

    def _collect_python_imports(
        self,
        path: str,
        text: str,
        module_index: Dict[str, str],
    ) -> Optional[List[ImportHit]]:
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            self.logger.warning("ImportGraphExtractor: unable to parse %s: %s", path, exc)
            return None

        module_name = self._python_module_name(path)
        package_parts = self._python_package_parts(path, module_name)
        hits: List[ImportHit] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                line = getattr(node, "lineno", None)
                for alias in node.names:
                    target_path = self._resolve_python_module(module_index, alias.name)
                    if target_path:
                        hits.append(ImportHit(target=target_path, module=alias.name, symbol=None, line=line))
            elif isinstance(node, ast.ImportFrom):
                line = getattr(node, "lineno", None)
                base_module = self._resolve_python_from(package_parts, node.module, node.level or 0)
                for alias in node.names:
                    symbol = alias.name
                    candidates: List[Optional[str]] = []
                    if symbol == "*":
                        candidates.append(base_module)
                    else:
                        if base_module:
                            candidates.append(f"{base_module}.{symbol}")
                            candidates.append(base_module)
                        if node.module and (node.level or 0) == 0:
                            candidates.append(f"{node.module}.{symbol}")
                        candidates.append(symbol if (node.level or 0) == 0 else None)

                    resolved_path = None
                    chosen_module = None
                    seen_candidates: Set[str] = set()
                    for candidate in candidates:
                        if not candidate:
                            continue
                        if candidate in seen_candidates:
                            continue
                        seen_candidates.add(candidate)
                        match = module_index.get(candidate)
                        if match:
                            resolved_path = match
                            chosen_module = candidate
                            break

                    if not resolved_path and base_module:
                        resolved_path = module_index.get(base_module)
                        chosen_module = base_module if resolved_path else chosen_module

                    if resolved_path:
                        hits.append(
                            ImportHit(
                                target=resolved_path,
                                module=chosen_module or base_module or node.module,
                                symbol=None if symbol == "*" else symbol,
                                line=line,
                            )
                        )

        return hits

    def _resolve_python_module(self, module_index: Dict[str, str], module: Optional[str]) -> Optional[str]:
        if not module:
            return None
        if module in module_index:
            return module_index[module]
        search = module
        while "." in search:
            search = search.rsplit(".", 1)[0]
            if search in module_index:
                return module_index[search]
        return None

    def _resolve_python_from(
        self,
        package_parts: Sequence[str],
        module: Optional[str],
        level: int,
    ) -> Optional[str]:
        if level <= 0:
            return module
        base = list(package_parts)
        drop = max(level - 1, 0)
        if drop:
            if drop >= len(base):
                base = []
            else:
                base = base[: len(base) - drop]
        if module:
            base.extend(part for part in module.split(".") if part)
        if not base:
            return module
        return ".".join(base)

    def _collect_ts_imports(
        self,
        path: str,
        text: str,
        path_index: Set[str],
    ) -> List[ImportHit]:
        hits: List[ImportHit] = []
        for match in self._ts_import_pattern.finditer(text):
            module_value = match.group("module") or match.group("require") or match.group("dynamic")
            if not module_value:
                continue
            target = self._resolve_ts_target(path, module_value, path_index)
            if not target:
                continue
            line = text.count("\n", 0, match.start()) + 1
            hits.append(ImportHit(target=target, module=module_value, symbol=None, line=line))
        return hits

    def _resolve_ts_target(self, source_path: str, module_spec: str, path_index: Set[str]) -> Optional[str]:
        if module_spec.startswith("."):
            base_dir = (self.repo_root / source_path).parent
            candidates = self._ts_candidate_paths(base_dir, module_spec)
        elif module_spec.startswith("/"):
            candidates = self._ts_candidate_paths(self.repo_root, module_spec.lstrip("/"))
        else:
            return None

        for candidate in candidates:
            if not self._is_inside_repo(candidate):
                continue
            try:
                rel_path = candidate.relative_to(self.repo_root).as_posix()
            except ValueError:
                continue
            if rel_path in path_index:
                return rel_path
        return None

    def _ts_candidate_paths(self, base_dir: Path, module_spec: str) -> List[Path]:
        root = (base_dir / module_spec).resolve()
        candidates: List[Path] = []
        if root.suffix:
            candidates.append(root)
        else:
            for ext in self.TS_EXTENSIONS:
                candidates.append(Path(str(root) + ext))
            for ext in self.TS_EXTENSIONS:
                candidates.append(root / f"index{ext}")
        return candidates

    def _is_inside_repo(self, candidate: Path) -> bool:
        try:
            candidate.relative_to(self.repo_root)
            return True
        except ValueError:
            return False

    def _write_relationships(
        self,
        payloads: Sequence[Dict[str, object]],
        processed_paths: Set[str],
    ) -> Dict[str, int]:
        run_id = str(uuid.uuid4())
        relationships_created = 0
        relationships_upserted = 0

        with self.driver.session() as session:
            if payloads:
                for batch in self._batched(payloads, self.batch_size):
                    result = session.run(
                        """
                        UNWIND $rows AS row
                        MATCH (src:File {path: row.source})
                        MATCH (dst:File {path: row.target})
                        MERGE (src)-[rel:IMPORTS]->(dst)
                        ON CREATE SET
                            rel.created_at = datetime(),
                            rel.source = 'static-analysis'
                        SET rel.language = row.language,
                            rel.modules = row.modules,
                            rel.symbols = row.symbols,
                            rel.lines = row.lines,
                            rel.count = row.count,
                            rel.last_seen = datetime(),
                            rel.run_id = $run_id
                        """,
                        rows=list(batch),
                        run_id=run_id,
                    )
                    summary = result.consume()
                    relationships_created += summary.counters.relationships_created
                    relationships_upserted += len(batch)

            removed = 0
            if processed_paths:
                removal_result = session.run(
                    """
                    MATCH (src:File)-[rel:IMPORTS]->(dst:File)
                    WHERE src.path IN $paths AND (rel.run_id IS NULL OR rel.run_id <> $run_id)
                    WITH rel
                    DELETE rel
                    RETURN count(rel) AS removed
                    """,
                    paths=list(processed_paths),
                    run_id=run_id,
                )
                record = removal_result.single()
                if record:
                    removed = record.get("removed", 0) or 0

        return {
            "run_id": run_id,
            "relationships_created": relationships_created,
            "relationships_upserted": relationships_upserted,
            "relationships_deleted": removed,
        }

    @staticmethod
    def _batched(items: Sequence[Dict[str, object]], batch_size: int) -> Iterable[Sequence[Dict[str, object]]]:
        for start in range(0, len(items), batch_size):
            yield items[start : start + batch_size]
