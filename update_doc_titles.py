#!/usr/bin/env python3

from pathlib import Path
from developer_graph.app_state import driver

REPO_ROOT = Path(__file__).resolve().parent


def extract_title(content: str, filename: str) -> str:
	lines = content.split('\n')
	for line in lines:
		ls = line.strip()
		if ls.startswith('# '):
			return ls[2:].strip()
		if ls.startswith('## '):
			return ls[3:].strip()
	# Fallback to filename
	return Path(filename).stem.replace('_', ' ').replace('-', ' ').title()


def main() -> None:
	updated = 0
	errors = 0
	with driver.session() as session:
		rows = session.run(
			"""
			MATCH (d:Document)
			RETURN d.path AS path
			"""
		).data()
		for row in rows:
			rel = row['path']
			fs_path = REPO_ROOT / Path(rel)
			try:
				text = fs_path.read_text(encoding='utf-8', errors='ignore')
				title = extract_title(text, fs_path.name)
				session.run(
					"MATCH (d:Document {path: $p}) SET d.title = $t",
					p=rel, t=title
				)
				updated += 1
			except Exception:
				errors += 1
	print(f"Titles updated: {updated}, errors: {errors}")


if __name__ == '__main__':
	main()
