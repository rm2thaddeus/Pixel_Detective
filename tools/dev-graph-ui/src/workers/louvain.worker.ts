// Web Worker for Louvain community detection
// Runs off the main thread to avoid blocking UI

import louvain from 'graphology-communities-louvain';

export interface LouvainWorkerInput {
  nodes: Array<{ id: string; [key: string]: any }>;
  edges: Array<{ source: string; target: string; [key: string]: any }>;
  options?: {
    resolution?: number;
    randomWalk?: boolean;
  };
}

export interface LouvainWorkerOutput {
  communities: Record<string, number>;
  modularity: number;
  executionTime: number;
}

// Handle messages from main thread
self.onmessage = (event: MessageEvent<LouvainWorkerInput>) => {
  const startTime = performance.now();
  
  try {
    const { nodes, edges, options = {} } = event.data;
    
    // Create a simple graph structure for louvain
    const graph = {
      nodes: nodes.map(n => n.id),
      edges: edges.map(e => ({ source: e.source, target: e.target })),
      // Add any additional properties needed
    };
    
    // Run Louvain algorithm
    const result = louvain.assign(graph, {
      resolution: options.resolution || 1.0,
      randomWalk: options.randomWalk || false,
    });
    
    const executionTime = performance.now() - startTime;
    
    // Send result back to main thread
    self.postMessage({
      communities: result,
      modularity: louvain.modularity(graph, result),
      executionTime,
    } as LouvainWorkerOutput);
    
  } catch (error) {
    // Send error back to main thread
    self.postMessage({
      error: error instanceof Error ? error.message : 'Unknown error in Louvain worker',
      executionTime: performance.now() - startTime,
    });
  }
};

// Export for TypeScript
export {};
