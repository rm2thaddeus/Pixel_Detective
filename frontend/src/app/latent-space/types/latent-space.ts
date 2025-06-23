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

export interface ClusteringInfo {
  algorithm: string;
  n_clusters: number;
  silhouette_score?: number;
  n_outliers?: number;
  parameters: Record<string, unknown>;
}

export interface UMAPProjectionResponse {
  points: UMAPPoint[];
  collection: string;
  clustering_info?: ClusteringInfo;
}

export interface ClusteringRequest {
  algorithm: 'dbscan' | 'kmeans' | 'hierarchical';
  n_clusters?: number;
  eps?: number;
  min_samples?: number;
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