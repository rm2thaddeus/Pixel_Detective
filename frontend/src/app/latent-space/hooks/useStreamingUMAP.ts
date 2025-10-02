'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gpuApi } from '@/lib/api';
import { UMAPPoint, ClusteringInfo } from '../types/latent-space';

// Types for streaming operations
export interface StreamingUMAPRequest {
  data: number[][];
  n_components?: number;
  n_neighbors?: number;
  min_dist?: number;
  metric?: string;
  random_state?: number;
}

export interface StreamingClusterRequest {
  data: number[][];
  algorithm: string;
  n_clusters?: number;
  eps?: number;
  min_samples?: number;
  min_cluster_size?: number;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  total_points: number;
  processed_points: number;
  current_chunk: number;
  total_chunks: number;
  progress_percentage: number;
  estimated_completion?: number;
  processing_time: number;
  result?: any;
  error?: string;
}

export interface JobStartResponse {
  job_id: string;
  status: string;
  message: string;
  total_points: number;
  estimated_chunks: number;
}

// Polling interval for job status (in milliseconds)
const POLLING_INTERVAL = 1000; // 1 second

export function useStreamingUMAP() {
  const [activeJobs, setActiveJobs] = useState<Map<string, JobStatus>>(new Map());
  const queryClient = useQueryClient();

  // Start streaming UMAP job
  const startUMAPJob = useMutation({
    mutationFn: async (request: StreamingUMAPRequest): Promise<JobStartResponse> => {
      const response = await gpuApi.post('/umap/streaming/umap', request);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id !== 'immediate') {
        // Add job to active jobs for polling
        setActiveJobs(prev => new Map(prev).set(data.job_id, {
          job_id: data.job_id,
          status: 'pending',
          total_points: data.total_points,
          processed_points: 0,
          current_chunk: 0,
          total_chunks: data.estimated_chunks,
          progress_percentage: 0,
          processing_time: 0
        }));
      }
    },
    onError: (error) => {
      console.error('Failed to start UMAP job:', error);
    }
  });

  // Start streaming clustering job
  const startClusteringJob = useMutation({
    mutationFn: async (request: StreamingClusterRequest): Promise<JobStartResponse> => {
      const response = await gpuApi.post('/umap/streaming/cluster', request);
      return response.data;
    },
    onSuccess: (data) => {
      if (data.job_id !== 'immediate') {
        // Add job to active jobs for polling
        setActiveJobs(prev => new Map(prev).set(data.job_id, {
          job_id: data.job_id,
          status: 'pending',
          total_points: data.total_points,
          processed_points: 0,
          current_chunk: 0,
          total_chunks: data.estimated_chunks,
          progress_percentage: 0,
          processing_time: 0
        }));
      }
    },
    onError: (error) => {
      console.error('Failed to start clustering job:', error);
    }
  });

  // Poll job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await gpuApi.get(`/umap/streaming/status/${jobId}`);
      const status: JobStatus = response.data;
      
      setActiveJobs(prev => {
        const newMap = new Map(prev);
        newMap.set(jobId, status);
        
        // Remove completed/failed jobs after a delay
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          setTimeout(() => {
            setActiveJobs(current => {
              const updated = new Map(current);
              updated.delete(jobId);
              return updated;
            });
          }, 5000); // Remove after 5 seconds
        }
        
        return newMap;
      });
      
      return status;
    } catch (error) {
      console.error(`Failed to poll job status for ${jobId}:`, error);
      return null;
    }
  }, []);

  // Cancel job
  const cancelJob = useMutation({
    mutationFn: async (jobId: string) => {
      const response = await gpuApi.delete(`/umap/streaming/cancel/${jobId}`);
      return response.data;
    },
    onSuccess: (data, jobId) => {
      console.log(`Job ${jobId} cancelled:`, data.message);
      // Update job status to cancelled
      setActiveJobs(prev => {
        const newMap = new Map(prev);
        const job = newMap.get(jobId);
        if (job) {
          newMap.set(jobId, { ...job, status: 'cancelled' });
        }
        return newMap;
      });
    },
    onError: (error) => {
      console.error('Failed to cancel job:', error);
    }
  });

  // Poll active jobs
  useEffect(() => {
    if (activeJobs.size === 0) return;

    const interval = setInterval(() => {
      activeJobs.forEach((job, jobId) => {
        if (job.status === 'pending' || job.status === 'processing') {
          pollJobStatus(jobId);
        }
      });
    }, POLLING_INTERVAL);

    return () => clearInterval(interval);
  }, [activeJobs, pollJobStatus]);

  // Get all active jobs
  const getActiveJobs = useCallback(() => {
    return Array.from(activeJobs.values());
  }, [activeJobs]);

  // Get specific job status
  const getJobStatus = useCallback((jobId: string) => {
    return activeJobs.get(jobId);
  }, [activeJobs]);

  // Check if any jobs are currently processing
  const hasActiveJobs = useCallback(() => {
    return Array.from(activeJobs.values()).some(job => 
      job.status === 'pending' || job.status === 'processing'
    );
  }, [activeJobs]);

  // Get overall progress for all active jobs
  const getOverallProgress = useCallback(() => {
    const jobs = Array.from(activeJobs.values());
    if (jobs.length === 0) return 0;
    
    const totalProgress = jobs.reduce((sum, job) => sum + job.progress_percentage, 0);
    return totalProgress / jobs.length;
  }, [activeJobs]);

  return {
    // Mutations
    startUMAPJob,
    startClusteringJob,
    cancelJob,
    
    // Job management
    activeJobs: getActiveJobs(),
    getJobStatus,
    hasActiveJobs,
    getOverallProgress,
    
    // Loading states
    isStartingUMAP: startUMAPJob.isPending,
    isStartingClustering: startClusteringJob.isPending,
    isCancelling: cancelJob.isPending,
    
    // Error states
    umapError: startUMAPJob.error,
    clusteringError: startClusteringJob.error,
    cancelError: cancelJob.error
  };
}

// Hook for handling UMAP results with streaming
export function useStreamingUMAPResults() {
  const [results, setResults] = useState<{
    points: UMAPPoint[];
    clustering_info?: ClusteringInfo;
  } | null>(null);

  const updateResults = useCallback((newResults: any) => {
    setResults(newResults);
  }, []);

  const clearResults = useCallback(() => {
    setResults(null);
  }, []);

  return {
    results,
    updateResults,
    clearResults
  };
}

// Utility function to convert UMAP embeddings to points
export function convertEmbeddingsToPoints(
  embeddings: number[][], 
  originalPoints: UMAPPoint[]
): UMAPPoint[] {
  return embeddings.map((embedding, index) => ({
    ...originalPoints[index],
    x: embedding[0],
    y: embedding[1]
  }));
}

// Utility function to apply clustering results to points
export function applyClusteringToPoints(
  points: UMAPPoint[],
  labels: number[],
  clusters: Record<string, any>
): { points: UMAPPoint[], clustering_info: ClusteringInfo } {
  const updatedPoints = points.map((point, index) => ({
    ...point,
    cluster_id: labels[index],
    is_outlier: labels[index] === -1
  }));

  const clustering_info: ClusteringInfo = {
    algorithm: 'streaming', // This will be updated by the caller
    n_clusters: Object.keys(clusters).length,
    silhouette_score: undefined, // Will be provided by the backend
    n_outliers: labels.filter(l => l === -1).length,
    parameters: {},
    clusters
  };

  return { points: updatedPoints, clustering_info };
} 