import { useInfiniteQuery } from '@tanstack/react-query';

export interface WindowedSubgraphParams {
  fromTimestamp?: string;
  toTimestamp?: string;
  nodeTypes?: string[];
  limit?: number;
}

export interface WindowedSubgraphResponse {
  nodes: any[];
  edges: any[];
  pagination: {
    total_nodes: number;
    total_edges: number;
    returned_nodes: number;
    returned_edges: number;
    limit: number;
    offset: number;
    next_cursor: string | null;
    has_more: boolean;
  };
  performance: {
    query_time_ms: number;
    filters: {
      from_timestamp?: string;
      to_timestamp?: string;
      node_types?: string[];
    };
  };
}

export function useWindowedSubgraph(params: WindowedSubgraphParams = {}) {
  const { fromTimestamp, toTimestamp, nodeTypes, limit = 1000 } = params;
  
  return useInfiniteQuery({
    queryKey: ['dev-graph', 'windowed-subgraph', fromTimestamp, toTimestamp, nodeTypes, limit],
    queryFn: async ({ pageParam = null }) => {
      const searchParams = new URLSearchParams();
      
      if (fromTimestamp) searchParams.set('from_timestamp', fromTimestamp);
      if (toTimestamp) searchParams.set('to_timestamp', toTimestamp);
      if (nodeTypes && nodeTypes.length > 0) searchParams.set('types', nodeTypes.join(','));
      if (limit) searchParams.set('limit', limit.toString());
      if (pageParam) searchParams.set('cursor', pageParam);
      
      const url = `${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080'}/api/v1/dev-graph/graph/subgraph?${searchParams.toString()}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch windowed subgraph: ${response.statusText}`);
      }
      
      return response.json() as Promise<WindowedSubgraphResponse>;
    },
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.pagination.next_cursor,
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
