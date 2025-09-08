import { useInfiniteQuery, useQuery } from '@tanstack/react-query';

export interface WindowedSubgraphParams {
  fromTimestamp?: string;
  toTimestamp?: string;
  nodeTypes?: string[];
  limit?: number;
  includeCounts?: boolean;
}

export interface KeysetCursor {
  last_ts: string;
  last_commit: string;
  rel_type?: string;
}

export interface WindowedSubgraphResponse {
  nodes: any[];
  edges: any[];
  pagination: {
    total_nodes: number | null;
    total_edges: number | null;
    returned_nodes: number;
    returned_edges: number;
    limit: number;
    cursor: KeysetCursor | null;
    next_cursor: KeysetCursor | null;
    has_more: boolean;
  };
  performance: {
    query_time_ms: number;
    cache_hit: boolean;
    filters: {
      from_timestamp?: string;
      to_timestamp?: string;
      node_types?: string[];
    };
  };
}

export interface CommitsBucketsResponse {
  buckets: Array<{
    bucket: string;
    commit_count: number;
    file_changes: number;
    granularity: string;
  }>;
  performance: {
    query_time_ms: number;
    total_buckets: number;
  };
}

export interface AnalyticsResponse {
  activity: {
    commits_per_day: number;
    files_changed_per_day: number;
    authors_per_day: number;
    peak_activity: { timestamp: string; count: number };
    trends: Array<{ date: string; value: number }>;
  };
  graph: {
    total_nodes: number;
    total_edges: number;
    node_types: Record<string, number>;
    edge_types: Record<string, number>;
    complexity_metrics: {
      clustering_coefficient: number;
      average_path_length: number;
      modularity: number;
    };
  };
  traceability: {
    implemented_requirements: number;
    unimplemented_requirements: number;
    avg_files_per_requirement: number;
    coverage_percentage: number;
  };
}

export interface TelemetryResponse {
  avg_query_time_ms: number;
  cache_hit_rate: number;
  memory_usage_mb: number;
  active_connections: number;
  uptime_seconds: number;
}

export function useWindowedSubgraph(params: WindowedSubgraphParams = {}) {
  const { fromTimestamp, toTimestamp, nodeTypes, limit = 250, includeCounts = false } = params;
  
  return useInfiniteQuery({
    queryKey: ['dev-graph', 'windowed-subgraph', fromTimestamp, toTimestamp, nodeTypes, limit, includeCounts],
    queryFn: async ({ pageParam = null }) => {
      const searchParams = new URLSearchParams();
      
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      if (nodeTypes && nodeTypes.length > 0) searchParams.set('types', nodeTypes.join(','));
      if (limit) searchParams.set('limit', limit.toString());
      if (includeCounts !== undefined) searchParams.set('include_counts', includeCounts.toString());
      
      // Keyset pagination with cursor
      if (pageParam) {
        const cursor = JSON.parse(pageParam) as KeysetCursor;
        searchParams.set('cursor', JSON.stringify(cursor));
      }
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/graph/subgraph?${searchParams.toString()}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch windowed subgraph: ${response.statusText}`);
      }
      
      return response.json() as Promise<WindowedSubgraphResponse>;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination?.next_cursor) {
        return JSON.stringify(lastPage.pagination.next_cursor);
      }
      return undefined;
    },
    staleTime: 30_000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useCommitsBuckets(
  granularity: 'day' | 'week' = 'day',
  fromTimestamp?: string,
  toTimestamp?: string,
  limit: number = 1000
) {
  return useInfiniteQuery({
    queryKey: ['dev-graph', 'commits-buckets', granularity, fromTimestamp, toTimestamp, limit],
    queryFn: async ({ pageParam = 0 }) => {
      const searchParams = new URLSearchParams();
      
      searchParams.set('granularity', granularity);
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      if (limit) searchParams.set('limit', limit.toString());
      if (pageParam) searchParams.set('offset', pageParam.toString());
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/commits/buckets?${searchParams.toString()}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch commits buckets: ${response.statusText}`);
      }
      
      return response.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      // If the API returns pagination info, use it
      if (lastPage.pagination && lastPage.pagination.has_more) {
        return lastPage.pagination.offset + lastPage.pagination.limit;
      }
      // Otherwise, use simple offset-based pagination
      return allPages.length * limit < (lastPage.total_count || 10000) ? allPages.length * limit : undefined;
    },
    staleTime: 60_000, // 1 minute
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

// Fetch Sprint hierarchical subgraph: Sprint->Docs->Chunks->Requirements
export function useSprintSubgraph(number?: string) {
  return useInfiniteQuery({
    queryKey: ['dev-graph', 'sprint-subgraph', number],
    queryFn: async ({ pageParam = 0 }) => {
      if (!number) return { nodes: [], edges: [] };
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/sprints/${number}/subgraph`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch sprint subgraph');
      return res.json();
    },
    initialPageParam: 0,
    getNextPageParam: () => undefined,
    enabled: !!number,
    staleTime: 60_000,
  });
}

// Analytics hooks
export function useAnalytics(fromTimestamp?: string, toTimestamp?: string) {
  return useQuery({
    queryKey: ['dev-graph', 'analytics', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/analytics?${searchParams.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch analytics: ${response.statusText}`);
      }
      return response.json() as Promise<AnalyticsResponse>;
    },
    staleTime: 60_000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useActivityAnalytics(fromTimestamp?: string, toTimestamp?: string) {
  return useQuery({
    queryKey: ['dev-graph', 'analytics', 'activity', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/analytics/activity?${searchParams.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch activity analytics: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 60_000,
    gcTime: 5 * 60 * 1000,
  });
}

export function useGraphAnalytics(timestamp?: string) {
  return useQuery({
    queryKey: ['dev-graph', 'analytics', 'graph', timestamp],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (timestamp) searchParams.set('timestamp', timestamp);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/analytics/graph?${searchParams.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch graph analytics: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 60_000,
    gcTime: 5 * 60 * 1000,
  });
}

export function useTraceabilityAnalytics(fromTimestamp?: string, toTimestamp?: string) {
  return useQuery({
    queryKey: ['dev-graph', 'analytics', 'traceability', fromTimestamp, toTimestamp],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/analytics/traceability?${searchParams.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch traceability analytics: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 60_000,
    gcTime: 5 * 60 * 1000,
  });
}

// Telemetry hook
export function useTelemetry() {
  return useQuery({
    queryKey: ['dev-graph', 'telemetry'],
    queryFn: async () => {
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/metrics`;
      const response = await fetch(url);
      if (!response.ok) {
        // Fallback to health endpoint if metrics not available
        const healthUrl = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/health`;
        const healthResponse = await fetch(healthUrl);
        if (!healthResponse.ok) {
          throw new Error(`Failed to fetch telemetry: ${response.statusText}`);
        }
        const healthData = await healthResponse.json();
        return {
          avg_query_time_ms: healthData.avg_query_time_ms || 0,
          cache_hit_rate: healthData.cache_hit_rate || 0,
          memory_usage_mb: healthData.memory_usage_mb || 0,
          active_connections: healthData.active_connections || 0,
          uptime_seconds: healthData.uptime_seconds || 0,
        } as TelemetryResponse;
      }
      return response.json() as Promise<TelemetryResponse>;
    },
    staleTime: 30_000, // 30 seconds
    gcTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 30_000, // Refetch every 30 seconds
  });
}

// Full-text search hook
export function useFullTextSearch(query: string, label?: string) {
  return useQuery({
    queryKey: ['dev-graph', 'search', 'fulltext', query, label],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      searchParams.set('q', query);
      if (label) searchParams.set('label', label);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/search/fulltext?${searchParams.toString()}`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to search: ${response.statusText}`);
      }
      return response.json();
    },
    enabled: query.length > 0,
    staleTime: 30_000,
    gcTime: 2 * 60 * 1000,
  });
}
