#!/usr/bin/env python3
"""
Library Linker - Documentation-to-Code Relationship Builder

This script creates relationships between documentation and code by:
1. Extracting library/technology mentions from documentation
2. Mapping libraries to actual code files that use them
3. Creating MENTIONS_LIBRARY and USES_LIBRARY relationships

This bridges the gap between planning docs and implementation.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LibraryLinker:
    def __init__(self, driver):
        self.driver = driver
        
        # Library patterns to extract from docs and code
        self.library_patterns = {
            # Backend libraries
            'FastAPI': [r'FastAPI', r'fastapi'],
            'Neo4j': [r'Neo4j', r'neo4j'],
            'GitPython': [r'GitPython', r'gitpython'],
            'tenacity': [r'tenacity'],
            'python-dotenv': [r'python-dotenv', r'dotenv'],
            'Qdrant': [r'Qdrant', r'qdrant'],
            'pytest': [r'pytest'],
            'Docker': [r'Docker', r'docker'],
            'RAPIDS': [r'RAPIDS', r'rapids'],
            'Numba': [r'Numba', r'numba'],
            'CUDA': [r'CUDA', r'cuda'],
            
            # Frontend libraries
            'Next.js': [r'Next\.js', r'next\.js', r'NextJS', r'nextjs'],
            'React': [r'React', r'react'],
            'Chakra UI': [r'Chakra UI', r'chakra-ui', r'@chakra-ui'],
            'D3.js': [r'D3\.js', r'd3\.js', r'D3JS', r'd3js'],
            'WebGL': [r'WebGL', r'webgl'],
            'Deck.GL': [r'Deck\.GL', r'deck\.gl'],
            'React Query': [r'React Query', r'@tanstack/react-query'],
            'Framer Motion': [r'framer-motion'],
            'Graphology': [r'graphology'],
            'Sigma': [r'sigma'],
            
            # Infrastructure
            'Dockerfile': [r'Dockerfile'],
            'docker-compose': [r'docker-compose'],
        }
        
        # Import patterns for code files
        self.import_patterns = {
            'python': [
                r'import\s+(\w+)',
                r'from\s+(\w+)\s+import',
                r'from\s+(\w+\.\w+)\s+import'
            ],
            'typescript': [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\s+[\'"]([^\'"]+)[\'"]'
            ],
            'javascript': [
                r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\s+[\'"]([^\'"]+)[\'"]'
            ]
        }

    def extract_library_mentions_from_docs(self, docs_path: str) -> Dict[str, List[Tuple[str, str, int]]]:
        """Extract library mentions from documentation files."""
        mentions = {}
        
        for root, dirs, files in os.walk(docs_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, docs_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for library, patterns in self.library_patterns.items():
                            for pattern in patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    if library not in mentions:
                                        mentions[library] = []
                                    
                                    # Get context around the match
                                    start = max(0, match.start() - 50)
                                    end = min(len(content), match.end() + 50)
                                    context = content[start:end].strip()
                                    
                                    mentions[library].append((
                                        relative_path,
                                        context,
                                        match.start()
                                    ))
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
        
        # Also check for library mentions in code comments and docstrings
        for root, dirs, files in os.walk('.'):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git', 'cache']]
            
            for file in files:
                if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, '.')
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Look for library mentions in comments and docstrings
                        for library, patterns in self.library_patterns.items():
                            for pattern in patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE)
                                for match in matches:
                                    # Check if this is in a comment or docstring
                                    line_start = content.rfind('\n', 0, match.start()) + 1
                                    line = content[line_start:line_start + 100]
                                    
                                    if ('#' in line and line.find('#') < line.find(match.group())) or \
                                       ('"""' in line or "'''" in line):
                                        
                                        if library not in mentions:
                                            mentions[library] = []
                                        
                                        mentions[library].append((
                                            f"code_comment:{relative_path}",
                                            line.strip(),
                                            match.start()
                                        ))
                    except Exception as e:
                        pass  # Skip files that can't be read
        
        return mentions

    def extract_library_usage_from_code(self, code_path: str) -> Dict[str, List[str]]:
        """Extract library usage from code files."""
        usage = {}
        
        for root, dirs, files in os.walk(code_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git']]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, code_path)
                
                # Determine file type
                file_type = None
                if file.endswith('.py'):
                    file_type = 'python'
                elif file.endswith(('.ts', '.tsx')):
                    file_type = 'typescript'
                elif file.endswith(('.js', '.jsx')):
                    file_type = 'javascript'
                
                if file_type:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        for pattern in self.import_patterns[file_type]:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                library = match.group(1)
                                
                                # Map common import names to our library names
                                library_mapping = {
                                    'fastapi': 'FastAPI',
                                    'neo4j': 'Neo4j',
                                    'gitpython': 'GitPython',
                                    'tenacity': 'tenacity',
                                    'dotenv': 'python-dotenv',
                                    'qdrant_client': 'Qdrant',
                                    'pytest': 'pytest',
                                    'docker': 'Docker',
                                    'rapids': 'RAPIDS',
                                    'numba': 'Numba',
                                    'cuda': 'CUDA',
                                    'next': 'Next.js',
                                    'react': 'React',
                                    '@chakra-ui/react': 'Chakra UI',
                                    'd3': 'D3.js',
                                    'webgl': 'WebGL',
                                    'deck.gl': 'Deck.GL',
                                    '@tanstack/react-query': 'React Query',
                                    'framer-motion': 'Framer Motion',
                                    'graphology': 'Graphology',
                                    'sigma': 'Sigma',
                                    # Additional mappings
                                    'uvicorn': 'FastAPI',
                                    'pydantic': 'FastAPI',
                                    'requests': 'python-dotenv',
                                    'os': 'python-dotenv',
                                    'json': 'python-dotenv',
                                    're': 'python-dotenv',
                                    'pathlib': 'python-dotenv',
                                    'typing': 'python-dotenv',
                                    'collections': 'python-dotenv',
                                    'datetime': 'python-dotenv',
                                    'time': 'python-dotenv',
                                    'math': 'python-dotenv',
                                    'hashlib': 'python-dotenv',
                                    'subprocess': 'python-dotenv',
                                    'threading': 'python-dotenv',
                                    'concurrent': 'python-dotenv',
                                    'queue': 'python-dotenv',
                                    'asyncio': 'python-dotenv',
                                    'uuid': 'python-dotenv',
                                    'argparse': 'python-dotenv',
                                    'struct': 'python-dotenv',
                                    'defaultdict': 'python-dotenv',
                                    'dataclass': 'python-dotenv',
                                    'dataclasses': 'python-dotenv',
                                    'logging': 'python-dotenv',
                                    'sys': 'python-dotenv',
                                    'psutil': 'python-dotenv',
                                    'git': 'GitPython',
                                    'repo': 'GitPython',
                                    'repo_path': 'GitPython',
                                    'graph_database': 'Neo4j',
                                    'driver': 'Neo4j',
                                    'session': 'Neo4j',
                                    'transaction': 'Neo4j',
                                    'cypher': 'Neo4j',
                                    'bolt': 'Neo4j',
                                    'apoc': 'Neo4j'
                                }
                                
                                mapped_library = library_mapping.get(library.lower(), library)
                                
                                if mapped_library not in usage:
                                    usage[mapped_library] = []
                                
                                if relative_path not in usage[mapped_library]:
                                    usage[mapped_library].append(relative_path)
                                    
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
        
        return usage

    def create_library_nodes(self, libraries: Set[str]):
        """Create Library nodes in Neo4j."""
        with self.driver.session() as session:
            for library in libraries:
                session.run("""
                    MERGE (l:Library {name: $name})
                    SET l.type = 'library',
                        l.created_at = datetime()
                """, name=library)

    def create_document_library_relationships(self, mentions: Dict[str, List[Tuple[str, str, int]]]):
        """Create MENTIONS_LIBRARY relationships between documents and libraries."""
        with self.driver.session() as session:
            for library, mentions_list in mentions.items():
                for doc_path, context, position in mentions_list:
                    # Handle both regular docs and code comments
                    if doc_path.startswith('code_comment:'):
                        # For code comments, create a virtual document or link to the file
                        actual_path = doc_path.replace('code_comment:', '')
                        session.run("""
                            MATCH (f:File {path: $file_path})
                            MATCH (l:Library {name: $library})
                            MERGE (f)-[r:MENTIONS_LIBRARY]->(l)
                            ON CREATE SET r.context = $context,
                                          r.position = $position,
                                          r.weight = 1.0,
                                          r.created_at = datetime()
                            ON MATCH SET r.weight = r.weight + 1.0,
                                         r.last_seen = datetime()
                        """, file_path=actual_path, library=library, context=context, position=position)
                    else:
                        # For regular documents, try to find existing document or create one
                        session.run("""
                            MATCH (l:Library {name: $library})
                            MERGE (d:Document {path: $doc_path})
                            SET d.type = 'markdown',
                                d.last_modified = datetime()
                            MERGE (d)-[r:MENTIONS_LIBRARY]->(l)
                            ON CREATE SET r.context = $context,
                                          r.position = $position,
                                          r.weight = 1.0,
                                          r.created_at = datetime()
                            ON MATCH SET r.weight = r.weight + 1.0,
                                         r.last_seen = datetime()
                        """, doc_path=doc_path, library=library, context=context, position=position)

    def create_file_library_relationships(self, usage: Dict[str, List[str]]):
        """Create USES_LIBRARY relationships between files and libraries."""
        with self.driver.session() as session:
            for library, file_paths in usage.items():
                for file_path in file_paths:
                    # Find or create the file node
                    session.run("""
                        MATCH (f:File {path: $file_path})
                        MATCH (l:Library {name: $library})
                        MERGE (f)-[r:USES_LIBRARY]->(l)
                        ON CREATE SET r.weight = 1.0,
                                      r.created_at = datetime()
                        ON MATCH SET r.weight = r.weight + 1.0,
                                     r.last_seen = datetime()
                    """, file_path=file_path, library=library)

    def create_document_code_bridges(self):
        """Create RELATES_TO relationships between documents and code through shared libraries."""
        with self.driver.session() as session:
            # Create bridges between documents and files through shared libraries
            session.run("""
                MATCH (d:Document)-[:MENTIONS_LIBRARY]->(l:Library)<-[:USES_LIBRARY]-(f:File)
                MERGE (d)-[r:RELATES_TO]->(f)
                ON CREATE SET r.type = 'library_usage',
                              r.weight = 1.0,
                              r.created_at = datetime()
                ON MATCH SET r.weight = r.weight + 1.0,
                             r.last_seen = datetime()
            """)
            
            # Also create bridges between files that mention libraries in comments and other files using those libraries
            session.run("""
                MATCH (f1:File)-[:MENTIONS_LIBRARY]->(l:Library)<-[:USES_LIBRARY]-(f2:File)
                WHERE f1 <> f2
                MERGE (f1)-[r:RELATES_TO]->(f2)
                ON CREATE SET r.type = 'shared_library',
                              r.weight = 1.0,
                              r.created_at = datetime()
                ON MATCH SET r.weight = r.weight + 1.0,
                             r.last_seen = datetime()
            """)

    def run_analysis(self, docs_path: str, code_path: str):
        """Run the complete library linking analysis."""
        print("🔍 Extracting library mentions from documentation...")
        mentions = self.extract_library_mentions_from_docs(docs_path)
        print(f"Found {len(mentions)} libraries mentioned in docs")
        
        print("🔍 Extracting library usage from code...")
        usage = self.extract_library_usage_from_code(code_path)
        print(f"Found {len(usage)} libraries used in code")
        
        # Get all unique libraries
        all_libraries = set(mentions.keys()) | set(usage.keys())
        print(f"Total unique libraries: {len(all_libraries)}")
        
        print("📊 Creating Library nodes...")
        self.create_library_nodes(all_libraries)
        
        print("🔗 Creating document-library relationships...")
        self.create_document_library_relationships(mentions)
        
        print("🔗 Creating file-library relationships...")
        self.create_file_library_relationships(usage)
        
        print("🌉 Creating document-code bridges...")
        self.create_document_code_bridges()
        
        print("✅ Library linking analysis complete!")
        
        # Print summary
        with self.driver.session() as session:
            result = session.run("""
                MATCH (d:Document)-[:MENTIONS_LIBRARY]->(l:Library)
                RETURN count(DISTINCT d) as docs_with_libraries,
                       count(DISTINCT l) as libraries_mentioned,
                       count(*) as total_mentions
            """).single()
            
            print(f"📈 Results:")
            print(f"  - Documents with library mentions: {result['docs_with_libraries']}")
            print(f"  - Libraries mentioned: {result['libraries_mentioned']}")
            print(f"  - Total mentions: {result['total_mentions']}")
            
            result = session.run("""
                MATCH (f:File)-[:USES_LIBRARY]->(l:Library)
                RETURN count(DISTINCT f) as files_using_libraries,
                       count(DISTINCT l) as libraries_used,
                       count(*) as total_usage
            """).single()
            
            print(f"  - Files using libraries: {result['files_using_libraries']}")
            print(f"  - Libraries used: {result['libraries_used']}")
            print(f"  - Total usage: {result['total_usage']}")
            
            result = session.run("""
                MATCH (d:Document)-[:RELATES_TO]->(f:File)
                WHERE d.path CONTAINS '.md' AND f.path CONTAINS '.py'
                RETURN count(*) as doc_to_code_links
            """).single()
            
            print(f"  - Document-to-code links: {result['doc_to_code_links']}")

def main():
    # Initialize Neo4j connection
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        linker = LibraryLinker(driver)
        
        # Run analysis
        docs_path = "docs"
        code_path = "."
        
        linker.run_analysis(docs_path, code_path)
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()
