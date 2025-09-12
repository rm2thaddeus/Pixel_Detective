#!/usr/bin/env python3

from developer_graph.app_state import driver

def main() -> None:
	with driver.session() as session:
		# Counts
		doc_count = session.run("MATCH (d:Document) RETURN count(d) AS c").single()["c"]
		titled_count = session.run("MATCH (d:Document) WHERE d.title IS NOT NULL RETURN count(d) AS c").single()["c"]
		chunk_links = session.run("MATCH (d:Document)-[:CONTAINS_CHUNK]->(:Chunk) RETURN count(*) AS c").single()["c"]

		# README variants (sample)
		readmes = session.run(
			"""
			MATCH (d:Document)
			WHERE d.path CONTAINS 'README.md'
			RETURN d.path AS path, d.title AS title
			ORDER BY path
			LIMIT 20
			"""
		).data()

		# Path normalization checks
		contains_colon = session.run("MATCH (d:Document) WHERE d.path CONTAINS ':' RETURN count(d) AS c").single()["c"]
		contains_backslash = session.run("MATCH (d:Document) WHERE d.path CONTAINS '\\\\' RETURN count(d) AS c").single()["c"]

		# Chunk->Document path consistency
		mismatched = session.run(
			"""
			MATCH (d:Document)-[:CONTAINS_CHUNK]->(c:Chunk)
			WHERE c.doc_path <> d.path
			RETURN count(*) AS c
			"""
		).single()["c"]

		print("=== Document Ingestion Verification ===")
		print(f"Documents: {doc_count}")
		print(f"With Title: {titled_count}")
		print(f"Chunk Links: {chunk_links}")
		print(f"Paths with colon (should be 0): {contains_colon}")
		print(f"Paths with backslash (should be 0): {contains_backslash}")
		print(f"Chunk->Document path mismatches (should be 0): {mismatched}\n")

		if readmes:
			print("Sample README documents:")
			for row in readmes:
				print(f"- {row['path']} | {row.get('title')}")
		else:
			print("No README.md documents found.")

if __name__ == "__main__":
	main()
