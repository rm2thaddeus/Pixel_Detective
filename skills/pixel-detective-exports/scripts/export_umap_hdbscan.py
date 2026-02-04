import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests


def request_json(method: str, url: str, **kwargs) -> Any:
    resp = requests.request(method, url, timeout=60, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {resp.status_code} {resp.text}")
    return resp.json() if resp.text else {}


def ensure_health(api_base: str) -> None:
    request_json("GET", f"{api_base}/health")


def select_collection(api_base: str, collection: str) -> None:
    request_json("POST", f"{api_base}/api/v1/collections/select", json={"collection_name": collection})


def get_active_collection(api_base: str) -> Optional[str]:
    data = request_json("GET", f"{api_base}/api/v1/collections/active")
    return data.get("active_collection")


def fetch_projection(api_base: str, sample_size: int, full: bool) -> Dict[str, Any]:
    params = {"sample_size": sample_size}
    if full:
        params["full"] = "true"
    return request_json("GET", f"{api_base}/umap/projection", params=params)


def cluster_hdbscan(gpu_base: str, points: List[Dict[str, Any]], min_cluster_size: int) -> Dict[str, Any]:
    data = [[p["x"], p["y"]] for p in points]
    payload = {"data": data, "algorithm": "hdbscan", "min_cluster_size": min_cluster_size}
    return request_json("POST", f"{gpu_base}/umap/cluster", json=payload)


def render_svg(
    points: List[Dict[str, Any]],
    out_path: str,
    width: int,
    height: int,
    color_map: str,
    point_size: int,
    outlier_size: int,
    outlier_color: str,
) -> None:
    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(f"matplotlib required for SVG output: {exc}")

    xs = [p["x"] for p in points]
    ys = [p["y"] for p in points]
    labels = [p.get("cluster_id", -1) for p in points]
    unique_labels = sorted(set(labels))
    colors = matplotlib.colormaps.get_cmap(color_map)

    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")

    for idx, label in enumerate(unique_labels):
        mask = [l == label for l in labels]
        color = outlier_color if label == -1 else colors(idx)
        ax.scatter(
            [x for x, m in zip(xs, mask) if m],
            [y for y, m in zip(ys, mask) if m],
            s=outlier_size if label == -1 else point_size,
            c=[color],
            alpha=0.75 if label == -1 else 0.9,
            linewidths=0,
        )

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.savefig(out_path, format="svg", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_csv(points: List[Dict[str, Any]], out_path: str) -> None:
    fieldnames = ["id", "x", "y", "cluster_id", "is_outlier", "filename", "caption"]
    with open(out_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for p in points:
            writer.writerow({k: p.get(k) for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description="Export UMAP projection + HDBSCAN clustering.")
    parser.add_argument("--api", default="http://localhost:8002")
    parser.add_argument("--gpu-api", default="http://localhost:8003")
    parser.add_argument("--collection", default="")
    parser.add_argument("--sample-size", type=int, default=2000)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--min-cluster-size", type=int, default=5)
    parser.add_argument("--out-dir", default=os.path.join("exports", "pixel-detective", "umap"))
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--no-svg", action="store_true")
    parser.add_argument("--color-map", default="tab20")
    parser.add_argument("--point-size", type=int, default=18)
    parser.add_argument("--outlier-size", type=int, default=12)
    parser.add_argument("--outlier-color", default="#94a3b8")
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    gpu_base = args.gpu_api.rstrip("/")

    ensure_health(api_base)
    if args.collection:
        select_collection(api_base, args.collection)

    active = get_active_collection(api_base)
    if not active:
        raise RuntimeError("No active collection. Use --collection to select one.")

    projection = fetch_projection(api_base, args.sample_size, args.full)
    points = projection.get("points") or []
    if not points:
        raise RuntimeError("No UMAP points returned.")

    request_json("GET", f"{gpu_base}/health")
    cluster_info = cluster_hdbscan(gpu_base, points, args.min_cluster_size)

    labels = cluster_info.get("labels", [])
    for idx, point in enumerate(points):
        label = labels[idx] if idx < len(labels) else -1
        point["cluster_id"] = int(label)
        point["is_outlier"] = bool(label == -1)

    output = {
        "collection": active,
        "points": points,
        "clustering": {
            "algorithm": "hdbscan",
            "min_cluster_size": args.min_cluster_size,
            "clusters": cluster_info.get("clusters"),
            "silhouette_score": cluster_info.get("silhouette_score"),
        },
    }

    os.makedirs(args.out_dir, exist_ok=True)
    base_name = f"umap_hdbscan_{active}"
    json_path = os.path.join(args.out_dir, f"{base_name}.json")
    csv_path = os.path.join(args.out_dir, f"{base_name}.csv")
    svg_path = os.path.join(args.out_dir, f"{base_name}.svg")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    write_csv(points, csv_path)

    if not args.no_svg:
        render_svg(
            points,
            svg_path,
            args.width,
            args.height,
            args.color_map,
            args.point_size,
            args.outlier_size,
            args.outlier_color,
        )

    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    if not args.no_svg:
        print(f"Wrote {svg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
