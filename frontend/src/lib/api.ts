import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002',
  timeout: 10000,
});

export const gpuApi = axios.create();
export const mlApi = axios.create();

export async function ping() {
  return api.get('/health');
}

export async function getCollections(): Promise<string[]> {
  const { data } = await api.get('/api/v1/collections');
  return data;
}

export async function selectCollection(name: string) {
  await api.post('/api/v1/collections/select', { collection_name: name });
}

export async function deleteCollection(name: string) {
  await api.delete(`/api/v1/collections/${name}`);
}

export interface CollectionInfo {
  name: string;
  status: string;
  points_count: number;
  vectors_count: number;
  indexed_vectors_count: number;
  config: {
    vector_size?: number;
    distance?: string;
  };
  sample_points: Array<{
    id: string;
    filename: string;
    timestamp: string;
    has_thumbnail: boolean;
    has_caption: boolean;
  }>;
  is_active: boolean;
}

export async function getCollectionInfo(name: string): Promise<CollectionInfo> {
  const { data } = await api.get(`/api/v1/collections/${name}/info`);
  return data;
}

export async function mergeCollections(dest: string, sources: string[]) {
  await api.post('/api/v1/collections/merge', {
    dest_collection: dest,
    source_collections: sources,
  });
}

export async function startFindSimilar(collection: string) {
  await selectCollection(collection);
  const { data } = await api.post('/api/v1/duplicates/find-similar');
  return data;
}

export async function getCurationStatuses(): Promise<Record<string, string>> {
  const { data } = await api.get('/api/v1/duplicates/curation-status');
  return data;
}

export async function getRecentJobs(): Promise<Record<string, string>> {
  const { data } = await api.get('/api/v1/ingest/recent_jobs');
  return data;
}
