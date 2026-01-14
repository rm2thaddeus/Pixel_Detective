---
name: pixel-detective-exports
description: Export Pixel Detective UMAP projections with HDBSCAN and manage Qdrant collections via the ingestion API. Use when the user asks for latent space exports, UMAP clustering assets, or collection operations (list/create/select/delete/merge).
---

# Pixel Detective Exports

Generate standalone exports (no UI) and manage collections for Pixel Detective.

## Requirements
- Ingestion API running on `http://localhost:8002`
- Qdrant running (Docker)
- GPU UMAP service on `http://localhost:8003` for HDBSCAN clustering

## Exports

### UMAP + HDBSCAN export (standalone)
- Script: `python skills/pixel-detective-exports/scripts/export_umap_hdbscan.py`
- Output default: `exports/pixel-detective/umap/umap_hdbscan_<collection>.json|csv|svg`
- Example:
  - `python skills/pixel-detective-exports/scripts/export_umap_hdbscan.py --collection my_collection --sample-size 2000`

### UMAP PDF report (all collections)
- Script: `python skills/pixel-detective-exports/scripts/export_umap_pdf.py`
- Output default: `exports/pixel-detective/umap/umap_cluster_report.pdf`
- Example:
  - `python skills/pixel-detective-exports/scripts/export_umap_pdf.py --sample-size 500 --title "Pixel Detective · UMAP Clusters"`

## Collection management

### Manage collections via API (Qdrant in Docker)
- Script: `python skills/pixel-detective-exports/scripts/manage_collections.py`
- Examples:
  - List: `python skills/pixel-detective-exports/scripts/manage_collections.py --action list`
  - Info: `python skills/pixel-detective-exports/scripts/manage_collections.py --action info --collection my_collection`
  - Create: `python skills/pixel-detective-exports/scripts/manage_collections.py --action create --collection my_collection --vector-size 512 --distance Cosine`
  - Select: `python skills/pixel-detective-exports/scripts/manage_collections.py --action select --collection my_collection`
  - Delete: `python skills/pixel-detective-exports/scripts/manage_collections.py --action delete --collection my_collection`
  - Merge: `python skills/pixel-detective-exports/scripts/manage_collections.py --action merge --dest merged_collection --sources a,b,c`

## Notes
- HDBSCAN clustering is performed by the GPU UMAP service; the ingestion service does not offer HDBSCAN.
- Collection operations go through the ingestion API, which talks to Qdrant in Docker.
- Use the start skill to bring up services:
  - `powershell -ExecutionPolicy Bypass -File skills\\start-pixel-detective\\scripts\\start_pixel_detective.ps1 -Mode backend -UseGpuUmap`
