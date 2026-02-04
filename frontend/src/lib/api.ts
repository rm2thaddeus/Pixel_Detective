import axios from 'axios';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002',
  timeout: 10000,
});

export const gpuApi = axios.create();

export const mlApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_ML_API_URL || 'http://localhost:8001',
  timeout: 10000,
});

// Dev Graph API client removed - Dev Graph is now a separate application
// If Dev Graph integration is needed, use the standalone Dev Graph UI at port 3001

// export const devGraphApi = axios.create({
//   baseURL: process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080',
//   timeout: 10000,
// });

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 404) {
      throw new Error('Resource not found');
    }
    if (error.response?.status >= 500) {
      throw new Error('Server error - please try again later');
    }
    throw error;
  },
);

export async function ping() {
  const { data } = await api.get('/health');
  return data;
}

export async function getCollections(): Promise<string[]> {
  const { data } = await api.get('/api/v1/collections');
  return data;
}

export async function selectCollection(collectionName: string) {
  const { data } = await api.post('/api/v1/collections/select', {
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
  const { data } = await api.post('/api/v1/collections/merge', {
    dest_collection: dest,
    source_collections: sources,
  });
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

export async function archiveExact(filePaths: string[]) {
  const { data } = await api.post('/api/v1/duplicates/archive-exact', {
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
  const { data } = await api.post('/api/v1/duplicates/find-similar', {
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
  const { data } = await api.post('/api/v1/curation/archive-selection', {
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
  /**
   * Error strings collected during ingestion.  Present when individual
   * files failed or the job aborted early.  Exposed so the Logs page can
   * surface them to the user.
   */
  errors?: string[];
  exact_duplicates: { file_path: string; existing_id: string }[];
}

export async function getIngestStatus(jobId: string): Promise<IngestStatus> {
  const { data } = await api.get(`/api/v1/ingest/status/${jobId}`);
  return data as IngestStatus;
}

// ---------------------------------------------------------------------------
// Ingestion – archive *all* exact-duplicate files for a running/completed job
// ---------------------------------------------------------------------------
// This hits the new backend endpoint that moves every file listed in
// `job_status[job_id]['exact_duplicates']` to a `duplicates_archive` folder,
// pruning the list as it succeeds so the call can be repeated safely.
export async function archiveAllDuplicates(jobId: string) {
  const res = await api.post(`/api/v1/ingest/archive_duplicates/${jobId}`);
  return res.data; // Returns updated JobResponse – the UI will refetch status
}

// -------------------------------
// Developer Graph / Exploration
// -------------------------------
export interface EvolutionEvent {
  id: string;
  type: 'commit' | 'requirement' | 'file' | 'note';
  timestamp: string;
  label: string;
}

export interface EvolutionSnapshot {
  nodes: Array<{ id: string; label?: string; x?: number; y?: number; size?: number; color?: string }>;
  edges: Array<{ id: string; source: string; target: string; label?: string; color?: string }>;
}

export interface FeatureEvolutionResponse {
  feature: string;
  events: EvolutionEvent[];
  snapshots?: Record<string, EvolutionSnapshot>;
}

// Dev Graph integration removed - use standalone Dev Graph app at port 3001
export async function fetchFeatureEvolution(feature: string): Promise<FeatureEvolutionResponse> {
  // This functionality is available in the Dev Graph standalone application
  return { feature, events: [] };
}

export interface FailureAnalysisResponse {
  patterns: Array<{ id: string; label: string; severity: 'low' | 'medium' | 'high' }>;
  insights: string[];
  recommendations: string[];
}

export async function analyzeFailurePatterns(_feature: string): Promise<FailureAnalysisResponse> {
  // Synthesize analysis from available analytics endpoints
  const [graphResp, activityResp] = await Promise.all([
    api.get(`/api/v1/analytics/graph`).then(r => r.data).catch(() => null),
    api.get(`/api/v1/analytics/activity`).then(r => r.data).catch(() => null),
  ]);
  const patterns: FailureAnalysisResponse['patterns'] = [];
  const insights: string[] = [];
  const recommendations: string[] = [];

  if (graphResp?.edges?.TOUCHED && graphResp?.nodes?.files) {
    const churn = graphResp.edges.TOUCHED / Math.max(1, graphResp.nodes.files);
    if (churn > 5) patterns.push({ id: 'p-churn', label: 'High file churn', severity: 'high' });
    if (churn > 2) insights.push('Elevated churn suggests instability in file-level changes.');
  }
  if (activityResp?.unique_authors && activityResp?.commit_count) {
    const authors = activityResp.unique_authors;
    const commits = activityResp.commit_count;
    if (authors > 5 && commits < 20) patterns.push({ id: 'p-busfactor', label: 'Many authors, low throughput', severity: 'medium' });
  }
  if (!patterns.length) patterns.push({ id: 'p-none', label: 'No obvious failure patterns detected', severity: 'low' });
  if (!insights.length) insights.push('Consider adding domain-specific checks to improve analysis.');
  recommendations.push('Add guardrail tests around critical modules');
  recommendations.push('Stabilize dependencies and monitor regressions');

  return { patterns, insights, recommendations };
}

export interface ArchitectureInsightsResponse {
  dependencies: Array<{ source: string; target: string; weight?: number }>;
  bottlenecks: Array<{ id: string; label: string; metric: string; value: number }>;
  overview?: Record<string, unknown>;
}

// Dev Graph integration removed - use standalone Dev Graph app at port 3001
export async function generateArchitectureInsights(): Promise<ArchitectureInsightsResponse> {
  // This functionality is available in the Dev Graph standalone application
  return { dependencies: [], bottlenecks: [], overview: {} };
}

export interface KnowledgeSearchResult {
  id: string;
  type: string;
  title: string;
  snippet?: string;
}

// Dev Graph integration removed - use standalone Dev Graph app at port 3001
export async function searchKnowledge(query: string): Promise<KnowledgeSearchResult[]> {
  // This functionality is available in the Dev Graph standalone application
  return [];
}
