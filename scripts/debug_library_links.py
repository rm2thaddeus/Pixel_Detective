#!/usr/bin/env python3
"""
Debug script to check library linking results
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

def debug_library_links():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    try:
        with driver.session() as session:
            # Check document-library mentions
            print("📄 Document-Library mentions:")
            result = session.run("""
                MATCH (d:Document)-[:MENTIONS_LIBRARY]->(l:Library) 
                RETURN d.path, l.name, count(*) as mentions 
                ORDER BY mentions DESC LIMIT 10
            """)
            for record in result:
                print(f"  {record['d.path']} -> {record['l.name']} ({record['mentions']} mentions)")
            
            # Check file-library usage
            print("\n📁 File-Library usage:")
            result = session.run("""
                MATCH (f:File)-[:USES_LIBRARY]->(l:Library) 
                RETURN f.path, l.name, count(*) as usage 
                ORDER BY usage DESC LIMIT 10
            """)
            for record in result:
                print(f"  {record['f.path']} -> {record['l.name']} ({record['usage']} usage)")
            
            # Check document-code bridges
            print("\n🌉 Document-Code bridges:")
            result = session.run("""
                MATCH (d:Document)-[:RELATES_TO]->(f:File) 
                WHERE d.path CONTAINS '.md' AND f.path CONTAINS '.py'
                RETURN d.path, f.path, count(*) as bridges 
                ORDER BY bridges DESC LIMIT 10
            """)
            for record in result:
                print(f"  {record['d.path']} -> {record['f.path']} ({record['bridges']} bridges)")
            
            # Check total counts
            print("\n📊 Total counts:")
            result = session.run("MATCH (l:Library) RETURN count(l) as total_libraries")
            print(f"  Total libraries: {result.single()['total_libraries']}")
            
            result = session.run("MATCH ()-[r:MENTIONS_LIBRARY]->() RETURN count(r) as total_mentions")
            print(f"  Total MENTIONS_LIBRARY: {result.single()['total_mentions']}")
            
            result = session.run("MATCH ()-[r:USES_LIBRARY]->() RETURN count(r) as total_usage")
            print(f"  Total USES_LIBRARY: {result.single()['total_usage']}")
            
            result = session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as total_bridges")
            print(f"  Total RELATES_TO: {result.single()['total_bridges']}")
            
    finally:
        driver.close()

if __name__ == "__main__":
    debug_library_links()
