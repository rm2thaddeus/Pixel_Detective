import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002",
  timeout: 10000,
});

export const mlApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_ML_API_URL || "http://localhost:8001",
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 404) {
      throw new Error("Resource not found");
    }
    if (error.response?.status >= 500) {
      throw new Error("Server error - please try again later");
    }
    throw error;
  },
);

export async function ping() {
  const { data } = await api.get("/health");
  return data;
}

export async function getCollections() {
  const { data } = await api.get("/api/v1/collections");
  return data as string[];
}

export async function selectCollection(collectionName: string) {
  const { data } = await api.post("/api/v1/collections/select", {
    collection_name: collectionName,
  });
  return data;
}

export async function deleteCollection(collectionName: string) {
  const { data } = await api.delete(`/api/v1/collections/${collectionName}`);
  return data;
}

export interface CollectionInfo {
  name: string;
  status: string;
  points_count: number;
  vectors_count: number;
  indexed_vectors_count: number;
  config: { vector_size?: number; distance?: string };
  sample_points: any[];
  is_active: boolean;
}

export async function getCollectionInfo(
  collectionName: string,
): Promise<CollectionInfo> {
  const { data } = await api.get(`/api/v1/collections/${collectionName}/info`);
  return data as CollectionInfo;
}

export async function mergeCollections(dest: string, sources: string[]) {
  const { data } = await api.post("/api/v1/collections/merge", {
    dest_collection: dest,
    source_collections: sources,
  });
  return data;
}

export async function archiveExact(filePaths: string[]) {
  const { data } = await api.post("/api/v1/duplicates/archive-exact", {
    file_paths: filePaths,
  });
  return data;
}

export interface FindSimilarTask {
  task_id: string;
  status: string;
  progress: number;
  total_points: number;
  processed_points: number;
  results: any[];
}

export async function startFindSimilar(
  threshold: number,
  limitPerImage: number,
) {
  const { data } = await api.post("/api/v1/duplicates/find-similar", {
    threshold,
    limit_per_image: limitPerImage,
  });
  return data as FindSimilarTask;
}

export async function getFindSimilarReport(taskId: string) {
  const { data } = await api.get(`/api/v1/duplicates/report/${taskId}`);
  return data as FindSimilarTask;
}

export async function archiveSelection(pointIds: string[]) {
  const { data } = await api.post("/api/v1/curation/archive-selection", {
    point_ids: pointIds,
  });
  return data;
}

export interface IngestStatus {
  status: string;
  message: string;
  progress: number;
  processed_files: number;
  cached_files: number;
  total_files: number;
  logs: string[];
  exact_duplicates: { file_path: string; existing_id: string }[];
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const { data } = await api.get(`/api/v1/ingest/status/${jobId}`);
  return data as IngestStatus;
}
