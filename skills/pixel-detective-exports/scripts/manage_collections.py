import argparse
import json
from typing import Any, Dict, List

import requests


def request_json(method: str, url: str, **kwargs) -> Any:
    resp = requests.request(method, url, timeout=60, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {resp.status_code} {resp.text}")
    return resp.json() if resp.text else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Qdrant collections via ingestion API.")
    parser.add_argument("--api", default="http://localhost:8002")
    parser.add_argument("--action", required=True, choices=[
        "list", "info", "create", "delete", "select", "active", "merge", "from-selection"
    ])
    parser.add_argument("--collection", default="")
    parser.add_argument("--vector-size", type=int, default=512)
    parser.add_argument("--distance", default="Cosine")
    parser.add_argument("--sources", default="")
    parser.add_argument("--dest", default="")
    parser.add_argument("--point-ids", default="")
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    action = args.action

    if action == "list":
        data = request_json("GET", f"{api_base}/api/v1/collections")
    elif action == "info":
        if not args.collection:
            raise RuntimeError("--collection is required for info")
        data = request_json("GET", f"{api_base}/api/v1/collections/{args.collection}/info")
    elif action == "create":
        if not args.collection:
            raise RuntimeError("--collection is required for create")
        payload = {
            "collection_name": args.collection,
            "vector_size": args.vector_size,
            "distance": args.distance,
        }
        data = request_json("POST", f"{api_base}/api/v1/collections", json=payload)
    elif action == "delete":
        if not args.collection:
            raise RuntimeError("--collection is required for delete")
        data = request_json("DELETE", f"{api_base}/api/v1/collections/{args.collection}")
    elif action == "select":
        if not args.collection:
            raise RuntimeError("--collection is required for select")
        data = request_json("POST", f"{api_base}/api/v1/collections/select", json={"collection_name": args.collection})
    elif action == "active":
        data = request_json("GET", f"{api_base}/api/v1/collections/active")
    elif action == "merge":
        if not args.dest or not args.sources:
            raise RuntimeError("--dest and --sources are required for merge")
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
        payload = {"dest_collection": args.dest, "source_collections": sources}
        data = request_json("POST", f"{api_base}/api/v1/collections/merge", json=payload)
    elif action == "from-selection":
        if not args.dest or not args.collection or not args.point_ids:
            raise RuntimeError("--dest, --collection, and --point-ids are required for from-selection")
        ids = [p.strip() for p in args.point_ids.split(",") if p.strip()]
        payload = {
            "new_collection_name": args.dest,
            "source_collection": args.collection,
            "point_ids": ids,
        }
        data = request_json("POST", f"{api_base}/api/v1/collections/from_selection", json=payload)
    else:
        raise RuntimeError(f"Unsupported action: {action}")

    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
