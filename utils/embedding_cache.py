import sqlite3
import pickle
import sys
import os
from utils.duplicate_detector import compute_sha256

class EmbeddingCache:
    def __init__(self, db_path="embedding_cache.sqlite"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (hash TEXT PRIMARY KEY, embedding BLOB)"
        )

    def get(self, hash_):
        cur = self.conn.execute("SELECT embedding FROM cache WHERE hash=?", (hash_,))
        row = cur.fetchone()
        if row:
            return pickle.loads(row[0])
        return None

    def set(self, hash_, embedding):
        emb_blob = pickle.dumps(embedding)
        self.conn.execute(
            "INSERT OR REPLACE INTO cache (hash, embedding) VALUES (?, ?)",
            (hash_, emb_blob),
        )
        self.conn.commit()

    def clear(self):
        self.conn.execute("DELETE FROM cache")
        self.conn.commit()

    def inspect(self, limit=10):
        cur = self.conn.execute("SELECT hash FROM cache LIMIT ?", (limit,))
        return [row[0] for row in cur.fetchall()]

_cache_instance = None

def get_cache(db_path="embedding_cache.sqlite"):
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = EmbeddingCache(db_path)
    return _cache_instance

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Embedding Cache Utility")
    parser.add_argument("--db", type=str, default="embedding_cache.sqlite", help="Path to cache DB file")
    parser.add_argument("--clear", action="store_true", help="Clear the cache")
    parser.add_argument("--inspect", action="store_true", help="List hashes in the cache")
    parser.add_argument("--limit", type=int, default=10, help="Limit for inspect")
    args = parser.parse_args()

    cache = EmbeddingCache(args.db)
    if args.clear:
        cache.clear()
        print(f"Cache at {args.db} cleared.")
    elif args.inspect:
        hashes = cache.inspect(args.limit)
        if hashes:
            print(f"First {len(hashes)} hashes in cache:")
            for h in hashes:
                print(h)
        else:
            print("Cache is empty.")
    else:
        parser.print_help() 