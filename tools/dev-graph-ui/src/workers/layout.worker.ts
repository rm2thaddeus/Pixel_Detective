// Web Worker for ForceAtlas2 layout computation
// Runs off the main thread to avoid blocking UI

import forceAtlas2 from 'graphology-layout-forceatlas2';

export interface LayoutWorkerInput {
  nodes: Array<{ id: string; x?: number; y?: number; [key: string]: any }>;
  edges: Array<{ source: string; target: string; [key: string]: any }>;
  options?: {
    iterations?: number;
    settings?: {
      gravity?: number;
      scaling?: number;
      strongGravity?: boolean;
      linLogMode?: boolean;
      outboundAttractionDistribution?: boolean;
      adjustSizes?: boolean;
      edgeWeightInfluence?: number;
      slowDown?: number;
    };
  };
}

export interface LayoutWorkerOutput {
  positions: Record<string, { x: number; y: number }>;
  converged: boolean;
  iterations: number;
  executionTime: number;
}

// Handle messages from main thread
self.onmessage = (event: MessageEvent<LayoutWorkerInput>) => {
  const startTime = performance.now();
  
  try {
    const { nodes, edges, options = {} } = event.data;
    
    // Create a simple graph structure for ForceAtlas2
    const graph = {
      nodes: nodes.map(n => ({
        id: n.id,
        x: n.x || 0,
        y: n.y || 0,
        size: n.size || 1,
      })),
      edges: edges.map(e => ({
        source: e.source,
        target: e.target,
        weight: e.weight || 1,
      })),
    };
    
    const iterations = options.iterations || 100;
    const settings = {
      gravity: 1,
      scaling: 1,
      strongGravity: false,
      linLogMode: false,
      outboundAttractionDistribution: false,
      adjustSizes: false,
      edgeWeightInfluence: 0,
      slowDown: 1,
      ...options.settings,
    };
    
    // Run ForceAtlas2 layout
    const positions = forceAtlas2(graph, {
      iterations,
      settings,
    });
    
    const executionTime = performance.now() - startTime;
    
    // Convert to the expected format
    const result: Record<string, { x: number; y: number }> = {};
    graph.nodes.forEach(node => {
      result[node.id] = {
        x: node.x,
        y: node.y,
      };
    });
    
    // Send result back to main thread
    self.postMessage({
      positions: result,
      converged: true, // ForceAtlas2 doesn't provide convergence info
      iterations,
      executionTime,
    } as LayoutWorkerOutput);
    
  } catch (error) {
    // Send error back to main thread
    self.postMessage({
      error: error instanceof Error ? error.message : 'Unknown error in layout worker',
      executionTime: performance.now() - startTime,
    });
  }
};

// Export for TypeScript
export {};
