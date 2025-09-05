// Web Worker for ForceAtlas2 layout computation
// This runs the CPU-intensive layout algorithm off the main thread

// Message types
interface WorkerMessage {
  type: 'COMPUTE_LAYOUT';
  payload: {
    nodes: Array<{ id: string; x?: number; y?: number; [key: string]: any }>;
    edges: Array<{ source: string; target: string; [key: string]: any }>;
    iterations?: number;
    settings?: {
      gravity?: number;
      scaling?: number;
      linLog?: boolean;
      barnesHut?: boolean;
    };
  };
}

interface WorkerResponse {
  type: 'LAYOUT_COMPUTED';
  payload: {
    positions: { [nodeId: string]: { x: number; y: number } };
    converged: boolean;
  };
}

// Handle messages from main thread
self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  const { type, payload } = event.data;
  
  if (type === 'COMPUTE_LAYOUT') {
    try {
      // Create a temporary graph for layout computation
      const Graph = require('graphology');
      const forceAtlas2 = require('graphology-layout-forceatlas2');
      
      const graph = new Graph();
      
      // Add nodes with existing positions if available
      payload.nodes.forEach(node => {
        const attrs: any = { ...node };
        if (typeof node.x === 'number' && typeof node.y === 'number') {
          attrs.x = node.x;
          attrs.y = node.y;
        }
        graph.addNode(node.id, attrs);
      });
      
      // Add edges
      payload.edges.forEach(edge => {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, edge);
        }
      });
      
      // Run ForceAtlas2 layout
      const iterations = payload.iterations || 100;
      const settings = payload.settings || {};
      
      const positions = forceAtlas2(graph, {
        iterations,
        settings: {
          gravity: settings.gravity || 1,
          scaling: settings.scaling || 1,
          linLog: settings.linLog || false,
          barnesHut: settings.barnesHut || false,
          ...settings
        }
      });
      
      // Extract positions
      const result: { [nodeId: string]: { x: number; y: number } } = {};
      graph.forEachNode((nodeId, attributes) => {
        const attrs = attributes as any;
        if (typeof attrs.x === 'number' && typeof attrs.y === 'number') {
          result[nodeId] = { x: attrs.x, y: attrs.y };
        }
      });
      
      // Check if layout converged (simplified check)
      const converged = iterations >= 50; // Assume converged after minimum iterations
      
      // Send result back to main thread
      const response: WorkerResponse = {
        type: 'LAYOUT_COMPUTED',
        payload: { positions: result, converged }
      };
      
      self.postMessage(response);
    } catch (error) {
      console.error('Error in layout worker:', error);
      // Send empty result on error
      const response: WorkerResponse = {
        type: 'LAYOUT_COMPUTED',
        payload: { positions: {}, converged: false }
      };
      self.postMessage(response);
    }
  }
};

// Export for TypeScript
export {};
