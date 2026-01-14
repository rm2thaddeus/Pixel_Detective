import argparse
import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


def request_json(method: str, url: str, **kwargs) -> Any:
    resp = requests.request(method, url, timeout=60, **kwargs)
    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: {resp.status_code} {resp.text}")
    return resp.json() if resp.text else {}


def ensure_health(api_base: str) -> None:
    request_json("GET", f"{api_base}/health")


def list_collections(api_base: str) -> List[str]:
    return request_json("GET", f"{api_base}/api/v1/collections")

def list_collections_qdrant(qdrant_base: str) -> List[str]:
    data = request_json("GET", f"{qdrant_base}/collections")
    collections = data.get("result", {}).get("collections", [])
    return [c.get("name") for c in collections if c.get("name")]


def select_collection(api_base: str, collection: str) -> None:
    request_json("POST", f"{api_base}/api/v1/collections/select", json={"collection_name": collection})


def fetch_projection(api_base: str, sample_size: int, full: bool) -> Dict[str, Any]:
    params = {"sample_size": sample_size}
    if full:
        params["full"] = "true"
    return request_json("GET", f"{api_base}/umap/projection", params=params)


def build_cluster_payload(
    algorithm: str,
    data: List[List[float]],
    min_cluster_size: int,
    eps: Optional[float],
    min_samples: Optional[int],
    n_clusters: Optional[int],
) -> Dict[str, Any]:
    algo = algorithm.lower()
    payload: Dict[str, Any] = {"data": data, "algorithm": algo}
    if algo == "hdbscan":
        payload["min_cluster_size"] = min_cluster_size
    elif algo == "dbscan":
        if eps is not None:
            payload["eps"] = eps
        if min_samples is not None:
            payload["min_samples"] = min_samples
    elif algo in {"kmeans", "hierarchical"}:
        if n_clusters is not None:
            payload["n_clusters"] = n_clusters
    return payload


def cluster_points(
    gpu_base: str,
    points: List[Dict[str, Any]],
    algorithm: str,
    min_cluster_size: int,
    eps: Optional[float],
    min_samples: Optional[int],
    n_clusters: Optional[int],
) -> Dict[str, Any]:
    data = [[p["x"], p["y"]] for p in points]
    payload = build_cluster_payload(algorithm, data, min_cluster_size, eps, min_samples, n_clusters)
    return request_json("POST", f"{gpu_base}/umap/cluster", json=payload)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


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
    import matplotlib
    import matplotlib.pyplot as plt

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


def build_html(title: str, collections: List[Dict[str, Any]]) -> str:
    cards_html = []
    for collection in collections:
        header = f"""
        <section class="collection">
          <div class="collection-header">
            <h2>{collection["name"]}</h2>
            <p>{collection["summary"]}</p>
          </div>
          <div class="cluster-grid">
        """
        cards = []
        for item in collection["points"]:
            thumb = item.get("thumbnail_base64")
            img_tag = ""
            if thumb:
                img_tag = f'<img src="data:image/jpeg;base64,{thumb}" alt="thumbnail" />'
            cluster_text = f'Cluster {item["cluster_id"]}'
            if item["cluster_id"] == -1:
                cluster_text = "Outlier"
            cards.append(f"""
              <div class="card">
                <div class="thumb">{img_tag}</div>
                <div class="meta">
                  <div class="filename">{item.get("filename","")}</div>
                  <div class="caption">{item.get("caption","")}</div>
                  <div class="cluster">{cluster_text} - size {item.get("cluster_size", 0)}</div>
                </div>
              </div>
            """)
        footer = "</div></section>"
        cards_html.append(header + "".join(cards) + footer)

    content = "\n".join(cards_html)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    :root {{
      --bg: #0b1220;
      --panel: #111a2d;
      --ink: #e2e8f0;
      --muted: #94a3b8;
      --accent: #22d3ee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      padding: 32px 48px 8px 48px;
    }}
    header h1 {{
      margin: 0 0 4px 0;
      font-size: 28px;
      letter-spacing: 0.4px;
    }}
    header p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .collection {{
      padding: 18px 48px 12px 48px;
    }}
    .collection-header {{
      margin-bottom: 12px;
    }}
    .collection-header h2 {{
      margin: 0 0 4px 0;
      font-size: 20px;
    }}
    .collection-header p {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .cluster-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 12px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 10px;
      padding: 10px;
      display: grid;
      gap: 8px;
    }}
    .thumb {{
      height: 140px;
      border-radius: 8px;
      background: #0f172a;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }}
    .thumb img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .filename {{
      font-size: 12px;
      color: var(--accent);
      word-break: break-all;
    }}
    .caption {{
      font-size: 12px;
      color: var(--ink);
    }}
    .cluster {{
      font-size: 11px;
      color: var(--muted);
    }}
  </style>
  <title>{title}</title>
  </head>
  <body>
    <header>
      <h1>{title}</h1>
      <p>Generated {now} - UMAP + HDBSCAN summary per image</p>
    </header>
    {content}
  </body>
</html>
    """


def export_pdf(html_path: str, pdf_path: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(f"file:///{html_path}")
        page.emulate_media(media="screen")
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Export UMAP + HDBSCAN for all collections into a PDF.")
    parser.add_argument("--api", default="http://localhost:8002")
    parser.add_argument("--gpu-api", default="http://localhost:8003")
    parser.add_argument("--qdrant", default="http://localhost:6333")
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--cluster-algorithm", default="hdbscan")
    parser.add_argument("--min-cluster-size", type=int, default=5)
    parser.add_argument("--eps", type=float, default=None)
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--n-clusters", type=int, default=None)
    parser.add_argument("--out-dir", default=os.path.join("exports", "pixel-detective", "umap"))
    parser.add_argument("--title", default="Pixel Detective - UMAP Cluster Summary")
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--color-map", default="tab20")
    parser.add_argument("--point-size", type=int, default=18)
    parser.add_argument("--outlier-size", type=int, default=12)
    parser.add_argument("--outlier-color", default="#94a3b8")
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    gpu_base = args.gpu_api.rstrip("/")
    qdrant_base = args.qdrant.rstrip("/")
    ensure_health(api_base)
    request_json("GET", f"{gpu_base}/health")

    collections = list_collections(api_base)
    if not collections:
        collections = list_collections_qdrant(qdrant_base)
    if not collections:
        raise RuntimeError("No collections found.")

    os.makedirs(args.out_dir, exist_ok=True)
    rendered_collections = []

    for collection in collections:
        select_collection(api_base, collection)
        try:
            projection = fetch_projection(api_base, args.sample_size, args.full)
        except RuntimeError as exc:
            message = str(exc)
            if "Collection is empty" in message or "404" in message:
                continue
            raise
        points = projection.get("points") or []
        if not points:
            continue

        cluster_info = cluster_points(
            gpu_base,
            points,
            args.cluster_algorithm,
            args.min_cluster_size,
            args.eps,
            args.min_samples,
            args.n_clusters,
        )
        labels = cluster_info.get("labels", [])

        cluster_sizes: Dict[int, int] = {}
        for label in labels:
            cluster_sizes[int(label)] = cluster_sizes.get(int(label), 0) + 1

        for idx, point in enumerate(points):
            label = int(labels[idx]) if idx < len(labels) else -1
            point["cluster_id"] = label
            point["is_outlier"] = bool(label == -1)
            point["cluster_size"] = cluster_sizes.get(label, 0)

        payload = {
            "collection": collection,
            "points": points,
            "clustering": {
                "algorithm": args.cluster_algorithm,
                "min_cluster_size": args.min_cluster_size,
                "eps": args.eps,
                "min_samples": args.min_samples,
                "n_clusters": args.n_clusters,
                "clusters": cluster_info.get("clusters"),
                "silhouette_score": cluster_info.get("silhouette_score"),
            },
        }

        base_name = f"umap_hdbscan_{collection}"
        write_json(os.path.join(args.out_dir, f"{base_name}.json"), payload)
        render_svg(
            points,
            os.path.join(args.out_dir, f"{base_name}.svg"),
            args.width,
            args.height,
            args.color_map,
            args.point_size,
            args.outlier_size,
            args.outlier_color,
        )

        summary = f"{len(points)} points - {len(cluster_sizes)} clusters ({args.cluster_algorithm})"
        rendered_collections.append({"name": collection, "points": points, "summary": summary})

    html = build_html(args.title, rendered_collections)
    html_path = os.path.join(args.out_dir, "umap_cluster_report.html")
    pdf_path = os.path.join(args.out_dir, "umap_cluster_report.pdf")

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html)
    export_pdf(os.path.abspath(html_path), pdf_path)

    print(f"Wrote {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
