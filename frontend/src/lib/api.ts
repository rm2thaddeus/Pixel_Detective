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

export const devGraphApi = axios.create({
  baseURL: process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080',
  timeout: 10000,
});

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

export async function fetchFeatureEvolution(feature: string): Promise<FeatureEvolutionResponse> {
  // If it looks like a requirement ID, use the dedicated evolution endpoint
  const isReq = /^(FR-|NFR-)/i.test(feature);
  try {
    if (isReq) {
      const { data } = await devGraphApi.get(`/api/v1/dev-graph/evolution/requirement/${encodeURIComponent(feature)}`);
      // Expect data to contain a list of events with timestamps or commits; normalize
      const events: EvolutionEvent[] = (data?.events || data || []).map((e: any, i: number) => ({
        id: String(e.id ?? e.hash ?? i),
        type: (e.type ?? 'commit') as EvolutionEvent['type'],
        timestamp: String(e.timestamp ?? e.date ?? new Date().toISOString()),
        label: String(e.label ?? e.message ?? e.summary ?? 'Event'),
      }));
      return { feature, events };
    }

    // Otherwise, build a generic timeline from commit buckets for context
    const { data: buckets } = await devGraphApi.get(`/api/v1/dev-graph/commits/buckets`, { params: { granularity: 'day', limit: 60 } });
    const events: EvolutionEvent[] = (buckets?.buckets || buckets || []).map((b: any, i: number) => ({
      id: `bucket-${i}`,
      type: 'commit',
      timestamp: String(b.timestamp ?? b.date ?? new Date().toISOString()),
      label: `Commits: ${b.count ?? b.commits ?? 0}`,
    }));
    return { feature, events };
  } catch (err) {
    // As a last resort, return an empty, valid shape
    return { feature, events: [] };
  }
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

export async function generateArchitectureInsights(): Promise<ArchitectureInsightsResponse> {
  const [rels, metrics] = await Promise.all([
    devGraphApi.get(`/api/v1/dev-graph/relations`, { params: { limit: 200 } }).then(r => r.data).catch(() => []),
    api.get(`/api/v1/analytics/graph`).then(r => r.data).catch(() => null),
  ]);
  const dependencies = (rels as any[]).slice(0, 200).map((r) => ({ source: r.from, target: r.to, weight: 1 }));
  const bottlenecks: ArchitectureInsightsResponse['bottlenecks'] = [];
  if (metrics?.edges?.TOUCHED != null) bottlenecks.push({ id: 'b-touched', label: 'File changes', metric: 'count', value: metrics.edges.TOUCHED });
  if (metrics?.nodes?.commits != null) bottlenecks.push({ id: 'b-commits', label: 'Commits', metric: 'count', value: metrics.nodes.commits });
  return { dependencies, bottlenecks, overview: metrics ?? {} };
}

export interface KnowledgeSearchResult {
  id: string;
  type: string;
  title: string;
  snippet?: string;
}

export async function searchKnowledge(query: string): Promise<KnowledgeSearchResult[]> {
  try {
    const { data } = await devGraphApi.get(`/api/v1/dev-graph/search`, { params: { q: query } });
    return data as KnowledgeSearchResult[];
  } catch (err) {
    // Simple mock results
    return [
      { id: 'k1', type: 'requirement', title: `Spec related to ${query}`, snippet: 'High-level description...' },
      { id: 'k2', type: 'commit', title: `Commit touching ${query}`, snippet: 'Refactor and fixes...' },
    ];
  }
}
