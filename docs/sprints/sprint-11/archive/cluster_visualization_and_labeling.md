# 📊 Cluster Discovery & Image Labelling Guide

> Beautiful • Functional • Insight-driven  
> Last updated: 2025-06-30

---

## 1. Current Workflow (v1)

### 1.1 Pipeline
1. **Embeddings** – every image is embedded into CLIP-space (or equivalent) by the *ML Inference* service.
2. **Dimensionality Reduction** – the *Latent-Space* page fetches a 2-D UMAP projection via `/umap/projection`.
3. **Clustering** – optional DBSCAN/HDBSCAN clustering is executed server-side; parameters are exposed via the *ClusteringControls* sidebar.
4. **Visualisation** – points are rendered in `UMAPScatterPlot` (Chakra + D3), coloured by cluster id.
5. **Exploration** – users hover / lasso to inspect thumbnails (tooltip overlay).
6. **Labelling** – selecting a cluster opens *ClusterLabelingPanel* where a textual label is applied; label is persisted via `/collections/{id}/labels`.

### 1.2 UI Building Blocks
| Component | Responsibility |
|-----------|----------------|
| `ClusteringControls` | tweak eps, minPts, minClusterSize, **re-run** clustering |
| `ClusterCardsPanel` | summary cards (size, exemplar thumbnails, label) |
| `UMAPScatterPlot` | WebGL scatter plot with zoom / pan / lasso |
| `ClusterLabelingPanel` | bulk labelling + label propagation |
| `StatsBar` | global metrics (clusters, unlabelled %) |

---

## 2. Alternative & Complementary Visualisations

| Idea | Why it might be useful | UX sketch |
|------|------------------------|-----------|
| **Image-driven Scatter Plot** | Replace circles with tiny blurred thumbnails – immediate visual context | On hover enlarge thumbnail, fade neighbours |
| **Density Heat-Map Overlay** | Quickly spot dense regions & outliers without running a clusterer | Semi-transparent kernel-density raster beneath points |
| **3-D Embedding (UMAP-3D or t-SNE-3D)** | Some clusters only separate in the 3rd dimension | Toggle button → OrbitControls + perspective camera |
| **Hierarchical Dendrogram** | See sub-cluster structure & choose cut-level interactively | Split right-pane; click branch ≙ selects subset |
| **Self-Organising Map Grid** | Maps 2-D latent space to grid where each cell shows prototypical image | Great for quick overviews; familiar to deep-learning crowd |
| **Time-Lapse Animation** | Animate point positions while interpolating UMAP epochs | Creates "formation" story; can be exported as gif |
| **Similarity Graph (Force-Directed)** | Visualise pairwise similarity graph instead of projection | Good for small datasets (<5k) |

### Interaction Enhancements
* **Magic-Lens** – circular lens that magnifies region & shows thumbnails only inside lens.
* **Brush + Details-On-Demand** – click-drag to brush, side-panel lists files with metadata.
* **Animated Transitions** – between clustering parameter changes or projection types (UMAP ↔ t-SNE) to preserve mental map.
* **Keyboard Shortcuts** – `R` reset view, `C` toggle cluster colours, `L` label selected.

---

## 3. Advanced Labelling Strategies

1. **Cluster-Level Bulk Labelling (current)** – quick but coarse.
2. **Active Learning Suggestions** – model predicts probable label ➜ user just approves / corrects.
3. **Few-Shot Refinement** – user labels a handful → fine-tune lightweight classifier, propagate to remaining images (flag low-confidence cases).
4. **BBox Heatmap** – inside scatter plot, show translucent bounding box whose colour represents majority label confidence.
5. **Semantic Search Assisted** – select some points, system retrieves semantically similar unlabeled images to accelerate labelling.
6. **Zero-Shot Label Templates** – leverage CLIP text-embeddings (`"a photo of {label}"`) to auto-assign probability per cluster.

---

## 4. Design Principles (aligned with project rules)

* **Minimalistic colour palette & compact layout** – matches user preference.
* **Performance first** – WebGL canvas for >50k points, lazy load thumbnails (`next/image`).
* **Hydration-safe** – projection canvas is wrapped in `ClientOnly` component.
* **Composable architecture** – follow *Component Composition Pattern*; each visualisation lives in its own folder `components/alternative-views/*`.
* **React Query everywhere** – all projection / clustering endpoints behind `useQuery`.
* **Accessibility** – high-contrast colour scheme; keyboard navigation for clusters list.

---

## 5. Implementation Roadmap (proposed)

| Phase | Scope | Est. Effort |
|-------|-------|-------------|
| 1 | Thumbnail scatter plot + hover enlarge | 1 day |
| 2 | Density heat-map overlay toggle | 0.5 day |
| 3 | 3-D embedding with Three.js | 2 days |
| 4 | Active-learning labelling loop (backend + UI) | 3–4 days |
| 5 | Polishing – animations, shortcuts, docs | 1 day |

---

## 6. References & Inspiration
* van der Maaten, *t-SNE* (2008)
* McInnes et al., *UMAP* (2020)
* Distill.pub – *Clustering Explained*
* "Embedding Projector" – TensorFlow .js

---

> **Next Step:** Pick one alternative view (e.g. thumbnail scatter) and spike a prototype behind a feature-flag.  
> Feedback loops with real users will guide which ideas graduate to production. 