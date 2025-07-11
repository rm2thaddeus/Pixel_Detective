export interface UMAPPoint {
  id: string;
  x: number;
  y: number;
  cluster_id?: number | null;
  is_outlier?: boolean;
  thumbnail_base64?: string;
  filename?: string;
  caption?: string;
}

export interface ClusterInfo {
  id: number;
  label?: string; // User-defined label
  point_count: number;
}

export interface ClusterSummary {
  size: number;
  centroid: [number, number];
  hull: [number, number][] | null; // Convex hull polygon in 2-D, null if not enough points
}

export interface ClusteringInfo {
  algorithm: string;
  n_clusters: number;
  silhouette_score?: number;
  n_outliers?: number;
  parameters: Record<string, any>;
  clusters?: Record<number, ClusterSummary>; // NEW – per-cluster metadata from backend
}

export interface UMAPProjectionResponse {
  points: UMAPPoint[];
  collection: string;
  clustering_info?: ClusteringInfo;
}

export interface ClusteringRequest {
  algorithm: 'dbscan' | 'kmeans' | 'hierarchical' | 'hdbscan';
  n_clusters?: number;
  eps?: number;
  min_samples?: number;
  min_cluster_size?: number;
}

export interface ViewportTransform {
  x: number;
  y: number;
  scale: number;
}

export interface ClusterLabelRequest {
  cluster_id: number;
  label: string;
} 