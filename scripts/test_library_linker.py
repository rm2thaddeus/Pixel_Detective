#!/usr/bin/env python3
"""
Test script for the Library Linker
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.library_linker import LibraryLinker
from neo4j import GraphDatabase
from dotenv import load_dotenv

def test_library_extraction():
    """Test library extraction from a sample document."""
    load_dotenv()
    
    # Initialize Neo4j connection
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        linker = LibraryLinker(driver)
        
        # Test with a small sample
        print("🧪 Testing library extraction...")
        
        # Test doc extraction
        mentions = linker.extract_library_mentions_from_docs("docs/sprints/sprint-11")
        print(f"Found mentions: {list(mentions.keys())}")
        
        # Test code extraction
        usage = linker.extract_library_usage_from_code("developer_graph")
        print(f"Found usage: {list(usage.keys())}")
        
        print("✅ Test completed successfully!")
        
    finally:
        driver.close()

if __name__ == "__main__":
    test_library_extraction()
