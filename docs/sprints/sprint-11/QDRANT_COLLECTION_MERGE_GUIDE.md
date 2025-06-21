# Qdrant Collection Merge & Incremental Ingestion Guide (Sprint 11)

> **Scope.**  This guide explains how to:
> 1.  Ingest images year-by-year into *isolated* Qdrant collections (e.g. `album_2017`, …, `album_2025`).
> 2.  Later **merge** (or *re-export + re-import*) any subset of those collections into a fresh **master** collection (`album_master`) **without touching the originals**.
> 3.  Keep the process idempotent so you can add new points at any time or rebuild the master from scratch.
>
> The workflow is 100 % compatible with the existing ingestion router (FastAPI) and with Qdrant ≥ 1.7 API.

---

## 1  Design Options

| Strategy | Storage Overhead | Pros | Cons |
|----------|-----------------|------|------|
| **A. Single Collection w/`year` Payload** | 0 × | • Simplest queries (`filter: {"year":2017}`)<br>• Zero copy<br>• Easy global search | • All vectors share one HNSW graph → rebuild required if you want vastly different hyper-params per year |
| **B. One Collection per Year + *Alias*‐Based "Union"** | 0 × | • Physical isolation; tune each index independently<br>• Instant *switch* via `swap_alias` | • Alias union is *atomic* rename, **not** logical union.  You still need *one* physical collection for search |
| **C. One Collection per Year → Periodic **Merge** into Master** (RECOMMENDED) | 1 × (master) | • Keep raw per-year sets + optimised consolidated index<br>• Master can be rebuilt offline, then atomically swapped in via alias | • Temporary extra storage while building master |

We adopt **Strategy C** because it gives us per-year isolation *and* a highly-optimised global index for cross-year clustering/search.

---

## 2  Incremental Ingestion Pattern

1.  User uploads images from year `YYYY`.
2.  Ingestion FastAPI router:
    ```python
    target_collection = f"album_{YYYY}"
    qdrant_client.upsert(collection_name=target_collection, points=points_batch)
    ```
3.  Collection settings (HNSW + quantisation) are created **once** per collection; subsequent upserts are cheap.
4.  ✅ **Idempotent**: if a `point_id` already exists it is overwritten.

---

## 3  Building / Updating the Master Collection

The master is (re)built on-demand by *copying* points from source collections via the **Scroll → Upsert** pattern.

### 3.1 Python Helper
```python
"""merge_collections.py – Copy points from many collections into a master one.
Run with:  python merge_collections.py album_master album_2017 album_2018 ..."""
import sys, uuid, tqdm
from qdrant_client import QdrantClient, models as qdr

DEST, *SOURCES = sys.argv[1:]
client = QdrantClient(host="localhost", port=6333)

# (Re)create destination collection – non-destructive to sources
if DEST in [c.name for c in client.get_collections().collections]:
    print(f"[i] Clearing existing {DEST} …")
    client.delete_collection(collection_name=DEST, wait=True)

print(f"[i] Creating {DEST} …")
client.recreate_collection(
    collection_name=DEST,
    vectors_config=qdr.VectorParams(size=512, distance="Cosine"),
    optimizers_config=qdr.OptimizersConfigDiff(memmap_threshold=20000),
)

BATCH = 1024
for src in SOURCES:
    print(f"[➜] Copying from {src}")
    scroll_cursor = None
    while True:
        points, scroll_cursor = client.scroll(
            collection_name=src,
            with_vectors=True,
            with_payload=True,
            limit=BATCH,
            offset=scroll_cursor,
        )
        if not points:
            break
        # Upsert into master; keep same IDs for traceability
        client.upsert(collection_name=DEST, points=points)
    print(f"    Done {src}")

print("[✓] Merge complete →", DEST)
```

### 3.2 Atomic *Swap* with Alias (Optional)
To swap the newly-built collection into production without downtime:
```bash
curl -X POST localhost:6333/aliases -H 'Content-Type: application/json' -d '{
  "actions": [
    {"create_alias": {"collection_name": "album_master_new", "alias_name": "album_master_tmp"}},
    {"swap_alias": {"alias_name": "album_master", "collection_name": "album_master_tmp"}}
  ]
}'
```
The old master remains untouched (for rollback) until you delete it manually.

---

## 4  Testing the Merge

1.  **Smoke test** total point count:
    ```python
    for c in ("album_2017", "album_2018", "album_master"):
        print(c, client.count(c).count)
    ```
2.  **Silhouette sanity-check** via GPU-UMAP micro-service:
    ```bash
    curl.exe -X POST http://localhost:8001/cluster ^
      -H "Content-Type: application/json" ^
      -d "{\"data\": <vectors>, \"algorithm\": \"hdbscan\"}"
    ```
3.  **Query both collections** and compare results for same query vector.

---

## 5  Why This Is Non-Destructive
* Source collections remain intact – only read operations performed.
* Destination is recreated from scratch each time; you can keep *N* historical masters for auditing.
* The alias swap makes the cut-over atomic; queries see either old or new master, never an inconsistent intermediate state.

---

## 6  Further Reading
* **Qdrant Snapshots API** – Off-cluster backups you can restore into a new collection.
* **Aliases API** – Atomic switch or blue-green deployments.
* **OptimisersConfig** – Tune memmap & payload indexing for very large datasets.
* Blog – "Merging billions of vectors in Qdrant using Scroll + Upsert" (2024-12). 