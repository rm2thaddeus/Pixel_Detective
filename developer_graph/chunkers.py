"""Chunkers for Temporal Semantic Dev Graph

Phase 2: Document and code chunking for semantic linking.
"""

import logging
import os
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MarkdownChunker:
    """Chunks Markdown documents by H2/H3 headings for semantic linking."""
    
    def __init__(self, min_chunk_length: int = 50):
        self.min_chunk_length = min_chunk_length
        self.requirement_pattern = re.compile(r'((?:FR|NFR)-\d{2}-\d{2})', re.IGNORECASE)
        self.sprint_pattern = re.compile(r'sprint-(\d+)', re.IGNORECASE)
    
    def chunk_document(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Chunk a Markdown document into sections based on H2/H3 headings.
        
        Args:
            file_path: Path to the document
            content: Raw markdown content
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_heading = None
        current_section = None
        chunk_ordinal = 0
        
        for line_num, line in enumerate(lines):
            # Check for H2 or H3 headings
            if line.startswith('## ') and not line.startswith('### '):
                # H2 heading - start new section
                if current_chunk and len('\n'.join(current_chunk).strip()) >= self.min_chunk_length:
                    chunk = self._create_chunk(
                        file_path, current_chunk, current_heading, current_section, 
                        chunk_ordinal, line_num
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_ordinal += 1
                
                current_section = line[3:].strip()
                current_heading = current_section
                current_chunk = [line]
                
            elif line.startswith('### '):
                # H3 heading - start new subsection
                if current_chunk and len('\n'.join(current_chunk).strip()) >= self.min_chunk_length:
                    chunk = self._create_chunk(
                        file_path, current_chunk, current_heading, current_section,
                        chunk_ordinal, line_num
                    )
                    if chunk:
                        chunks.append(chunk)
                        chunk_ordinal += 1
                
                current_heading = line[4:].strip()
                current_chunk = [line]
                
            else:
                current_chunk.append(line)
        
        # Process final chunk
        if current_chunk and len('\n'.join(current_chunk).strip()) >= self.min_chunk_length:
            chunk = self._create_chunk(
                file_path, current_chunk, current_heading, current_section,
                chunk_ordinal, len(lines)
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, file_path: str, lines: List[str], heading: Optional[str], 
                     section: Optional[str], ordinal: int, line_num: int) -> Optional[Dict[str, Any]]:
        """Create a chunk dictionary from lines."""
        text = '\n'.join(lines).strip()
        if not text or len(text) < self.min_chunk_length:
            return None
        
        # Generate stable chunk ID
        chunk_id = f"{file_path}#{ordinal}"
        
        # Extract requirement and sprint references
        requirements = self.requirement_pattern.findall(text)
        sprints = self.sprint_pattern.findall(text)
        
        # Requirements are already full IDs from the regex
        
        return {
            'id': chunk_id,
            'kind': 'doc',
            'heading': heading,
            'section': section,
            'file_path': file_path,
            'span': f"1:{line_num}",
            'text': text,
            'content': text,
            'length': len(text),
            'uid': chunk_id,
            'requirements': requirements,
            'sprints': sprints
        }


class CodeChunker:
    """Chunks code files by functions/methods with sliding window fallback."""
    
    def __init__(self, min_chunk_length: int = 50, max_chunk_length: int = 2000, 
                 overlap_lines: int = 20):
        self.min_chunk_length = min_chunk_length
        self.max_chunk_length = max_chunk_length
        self.overlap_lines = overlap_lines
        
        # Language-specific patterns
        self.patterns = {
            'python': {
                'function': re.compile(r'^def\s+(\w+)\s*\(', re.MULTILINE),
                'class': re.compile(r'^class\s+(\w+)', re.MULTILINE),
                'method': re.compile(r'^\s+def\s+(\w+)\s*\(', re.MULTILINE),
            },
            'typescript': {
                'function': re.compile(r'^(export\s+)?(async\s+)?function\s+(\w+)\s*\(', re.MULTILINE),
                'method': re.compile(r'^\s*(public|private|protected)?\s*(async\s+)?(\w+)\s*\(', re.MULTILINE),
                'class': re.compile(r'^(export\s+)?class\s+(\w+)', re.MULTILINE),
            },
            'javascript': {
                'function': re.compile(r'^(export\s+)?(async\s+)?function\s+(\w+)\s*\(', re.MULTILINE),
                'method': re.compile(r'^\s*(async\s+)?(\w+)\s*\(', re.MULTILINE),
                'class': re.compile(r'^(export\s+)?class\s+(\w+)', re.MULTILINE),
            }
        }
    
    def chunk_file(self, file_path: str, content: str, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Chunk a code file into functions/methods or sliding windows.
        
        Args:
            file_path: Path to the file
            content: Raw file content
            language: Programming language (auto-detected if None)
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not language:
            language = self._detect_language(file_path)
        
        chunks = []
        lines = content.split('\n')
        
        if language in self.patterns:
            # Try function/method-based chunking first
            function_chunks = self._chunk_by_functions(file_path, lines, language)
            if function_chunks:
                chunks.extend(function_chunks)
            
            # Fill gaps with sliding window
            covered_lines = set()
            for chunk in function_chunks:
                start, end = self._parse_span(chunk['span'])
                covered_lines.update(range(start, end))
            
            sliding_chunks = self._chunk_sliding_window(file_path, lines, covered_lines)
            chunks.extend(sliding_chunks)
        else:
            # Fallback to sliding window for unsupported languages
            chunks = self._chunk_sliding_window(file_path, lines, set())
        
        return chunks
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
        }
        return language_map.get(ext, 'unknown')
    
    def _chunk_by_functions(self, file_path: str, lines: List[str], language: str) -> List[Dict[str, Any]]:
        """Chunk by functions/methods/classes."""
        chunks = []
        patterns = self.patterns[language]
        content = '\n'.join(lines)
        
        # Find all function/method/class definitions
        all_matches = []
        for pattern_type, pattern in patterns.items():
            for match in pattern.finditer(content):
                all_matches.append((match.start(), match.end(), pattern_type, match.group()))
        
        # Sort by position
        all_matches.sort(key=lambda x: x[0])
        
        for i, (start, end, pattern_type, match_text) in enumerate(all_matches):
            # Find the end of this function/class
            start_line = content[:start].count('\n')
            end_line = self._find_function_end(lines, start_line, language)
            
            if end_line > start_line:
                chunk_lines = lines[start_line:end_line]
                text = '\n'.join(chunk_lines)
                
                if len(text) >= self.min_chunk_length:
                    chunk_id = f"{file_path}#{start_line}:{end_line}"
                    chunks.append({
                        'id': chunk_id,
                        'kind': 'code',
                        'heading': match_text.strip(),
                        'section': pattern_type,
                        'file_path': file_path,
                        'span': f"{start_line}:{end_line}",
                        'text': text,
                        'content': text,
                        'length': len(text),
                        'uid': chunk_id,
                        'symbol': match_text.strip(),
                        'symbol_type': pattern_type
                    })
        
        return chunks
    
    def _find_function_end(self, lines: List[str], start_line: int, language: str) -> int:
        """Find the end line of a function/class definition."""
        if language == 'python':
            return self._find_python_function_end(lines, start_line)
        elif language in ['typescript', 'javascript']:
            return self._find_js_function_end(lines, start_line)
        else:
            # Fallback: find next function or end of file
            for i in range(start_line + 1, len(lines)):
                line = lines[i].strip()
                if line and not line.startswith(' ') and not line.startswith('\t'):
                    return i
            return len(lines)
    
    def _find_python_function_end(self, lines: List[str], start_line: int) -> int:
        """Find end of Python function using indentation."""
        if start_line >= len(lines):
            return start_line
        
        # Get base indentation
        base_line = lines[start_line]
        base_indent = len(base_line) - len(base_line.lstrip())
        
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if not line.strip():  # Empty line
                continue
            
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent and line.strip():
                return i
        
        return len(lines)
    
    def _find_js_function_end(self, lines: List[str], start_line: int) -> int:
        """Find end of JavaScript/TypeScript function using braces."""
        brace_count = 0
        in_function = False
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    in_function = True
                elif char == '}':
                    brace_count -= 1
                    if in_function and brace_count == 0:
                        return i + 1
        
        return len(lines)
    
    def _chunk_sliding_window(self, file_path: str, lines: List[str], 
                            covered_lines: set) -> List[Dict[str, Any]]:
        """Create chunks using sliding window for uncovered lines."""
        chunks = []
        i = 0
        
        while i < len(lines):
            if i in covered_lines:
                i += 1
                continue
            
            # Find window end - use character count for max_chunk_length
            # Convert max_chunk_length from characters to approximate lines
            max_lines = min(self.max_chunk_length // 50, len(lines))  # Assume ~50 chars per line
            end = min(i + max_lines, len(lines))
            
            # Try to end at a natural boundary (empty line, comment, etc.)
            for j in range(end - 1, i + 1, -1):  # Start from i+1 to avoid infinite loop
                line = lines[j].strip()
                if not line or line.startswith('#') or line.startswith('//'):
                    end = j + 1
                    break
            
            # Check if we have enough content
            if end - i >= 1:  # At least one line
                chunk_lines = lines[i:end]
                text = '\n'.join(chunk_lines)
                
                # Check for actual text length
                if len(text.strip()) >= self.min_chunk_length:
                    chunk_id = f"{file_path}#{i}:{end}"
                    chunks.append({
                        'id': chunk_id,
                        'kind': 'code',
                        'heading': None,
                        'section': 'sliding_window',
                        'file_path': file_path,
                        'span': f"{i}:{end}",
                        'text': text,
                        'content': text,
                        'length': len(text),
                        'uid': chunk_id,
                        'symbol': None,
                        'symbol_type': 'sliding_window'
                    })
            
            # Move window with overlap
            i = max(i + 1, end - self.overlap_lines)
        
        return chunks
    
    def _parse_span(self, span: str) -> Tuple[int, int]:
        """Parse span string like '1:10' into start, end line numbers."""
        try:
            start, end = map(int, span.split(':'))
            return start, end
        except (ValueError, IndexError):
            return 0, 0


class ChunkIngester:
    """Ingests chunks into Neo4j using the temporal semantic schema."""
    
    def __init__(self, driver, repo_path: str):
        self.driver = driver
        self.repo_path = repo_path
        self.markdown_chunker = MarkdownChunker()
        self.code_chunker = CodeChunker()
        self._repo_root = Path(self.repo_path).resolve()

    def _resolve_path(self, file_path: str) -> Path:
        """Return absolute Path for a repository-relative or absolute path."""
        path = Path(file_path)
        if not path.is_absolute():
            path = (self._repo_root / path).resolve()
        else:
            path = path.resolve()
        return path

    def _normalize_repo_path(self, path: Path) -> str:
        """Return repository-relative POSIX path for storage in Neo4j."""
        try:
            return path.resolve().relative_to(self._repo_root).as_posix()
        except ValueError:
            return path.resolve().as_posix()
    
    def ingest_documents(self, doc_paths: List[str]) -> Dict[str, int]:
        """Ingest markdown documents and create chunks."""
        stats = {'documents': 0, 'chunks': 0, 'errors': 0, 'failures': []}

        with self.driver.session() as session:
            for doc_path in doc_paths:
                try:
                    abs_path = self._resolve_path(doc_path)
                    with abs_path.open('r', encoding='utf-8') as stream:
                        content = stream.read()

                    normalized_path = self._normalize_repo_path(abs_path)

                    document = {
                        'path': normalized_path,
                        'title': Path(normalized_path).stem,
                        'type': 'markdown',
                        'uid': normalized_path
                    }
                    session.execute_write(self._merge_document, document)
                    session.execute_write(
                        self._merge_file,
                        {'path': normalized_path, 'language': 'markdown'}
                    )
                    stats['documents'] += 1

                    chunks = self.markdown_chunker.chunk_document(normalized_path, content)

                    for chunk in chunks:
                        session.execute_write(self._merge_chunk, chunk)
                        stats['chunks'] += 1

                        session.execute_write(
                            self._relate_document_contains_chunk,
                            normalized_path,
                            chunk['id']
                        )
                        session.execute_write(
                            self._relate_chunk_part_of_file,
                            chunk['id'],
                            normalized_path
                        )

                        for req_id in chunk.get('requirements', []):
                            session.execute_write(
                                self._relate_chunk_mentions_requirement,
                                chunk['id'],
                                req_id
                            )
                except Exception as exc:
                    logger.warning("Error processing document %s: %s", doc_path, exc)
                    stats['errors'] += 1
                    stats['failures'].append({'path': str(doc_path), 'error': str(exc)})

        return stats

    def ingest_code_files(self, file_paths: List[str]) -> Dict[str, int]:
        """Ingest code files and create chunks."""
        stats = {'files': 0, 'chunks': 0, 'errors': 0, 'failures': []}

        with self.driver.session() as session:
            for file_path in file_paths:
                try:
                    abs_path = self._resolve_path(file_path)
                    with abs_path.open('r', encoding='utf-8') as stream:
                        content = stream.read()

                    normalized_path = self._normalize_repo_path(abs_path)
                    language = self.code_chunker._detect_language(normalized_path)

                    session.execute_write(
                        self._update_file_language,
                        normalized_path,
                        language
                    )
                    stats['files'] += 1

                    chunks = self.code_chunker.chunk_file(normalized_path, content, language)

                    for chunk in chunks:
                        session.execute_write(self._merge_chunk, chunk)
                        stats['chunks'] += 1

                        session.execute_write(
                            self._relate_chunk_part_of_file,
                            chunk['id'],
                            normalized_path
                        )
                except Exception as exc:
                    logger.warning("Error processing file %s: %s", file_path, exc)
                    stats['errors'] += 1
                    stats['failures'].append({'path': str(file_path), 'error': str(exc)})

        return stats

    def _merge_document(self, tx, document: Dict[str, Any]):
        """Merge document node."""
        from .schema.temporal_schema import merge_document
        merge_document(tx, document)
    
    def _merge_file(self, tx, file_info: Dict[str, Any]):
        """Merge file node referenced by chunks."""
        from .schema.temporal_schema import merge_file
        merge_file(tx, file_info)

    def _merge_chunk(self, tx, chunk: Dict[str, Any]):
        """Merge chunk node."""
        from .schema.temporal_schema import merge_chunk
        merge_chunk(tx, chunk)
    
    def _relate_document_contains_chunk(self, tx, doc_path: str, chunk_id: str):
        """Create CONTAINS_CHUNK relationship."""
        from .schema.temporal_schema import relate_document_contains_chunk
        relate_document_contains_chunk(tx, doc_path, chunk_id)
    
    def _relate_chunk_part_of_file(self, tx, chunk_id: str, file_path: str):
        """Create PART_OF relationship."""
        from .schema.temporal_schema import relate_chunk_part_of_file
        relate_chunk_part_of_file(tx, chunk_id, file_path)
    
    def _relate_chunk_mentions_requirement(self, tx, chunk_id: str, req_id: str):
        """Create MENTIONS relationship between chunk and requirement."""
        tx.run(
            """
            MATCH (ch:Chunk {id: $chunk_id})
            MERGE (r:Requirement {id: $req_id})
            MERGE (ch)-[:MENTIONS]->(r)
            """,
            chunk_id=chunk_id,
            req_id=req_id
        )
    
    def _update_file_language(self, tx, file_path: str, language: str):
        """Update file node with language information."""
        tx.run(
            """
            MERGE (f:File {path: $path})
            SET f.language = $language, f.is_code = true
            """,
            path=file_path,
            language=language
        )

