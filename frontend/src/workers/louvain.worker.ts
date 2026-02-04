// Web Worker for Louvain community detection
// This runs the CPU-intensive community detection off the main thread

import louvain from 'graphology-communities-louvain';

// Message types
interface WorkerMessage {
  type: 'DETECT_COMMUNITIES';
  payload: {
    nodes: Array<{ id: string; [key: string]: any }>;
    edges: Array<{ source: string; target: string; [key: string]: any }>;
    resolution?: number;
  };
}

interface WorkerResponse {
  type: 'COMMUNITIES_DETECTED';
  payload: {
    communities: { [nodeId: string]: number };
  };
}

// Handle messages from main thread
self.onmessage = (event: MessageEvent<WorkerMessage>) => {
  const { type, payload } = event.data;
  
  if (type === 'DETECT_COMMUNITIES') {
    try {
      // Create a temporary graph for community detection
      const Graph = require('graphology');
      const graph = new Graph();
      
      // Add nodes
      payload.nodes.forEach(node => {
        graph.addNode(node.id, node);
      });
      
      // Add edges
      payload.edges.forEach(edge => {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, edge);
        }
      });
      
      // Run Louvain algorithm
      const resolution = payload.resolution || 1.0;
      louvain.assign(graph, { resolution });
      
      // Extract communities
      const communities: { [nodeId: string]: number } = {};
      graph.forEachNode((nodeId, attributes) => {
        communities[nodeId] = (attributes as any).community || 0;
      });
      
      // Send result back to main thread
      const response: WorkerResponse = {
        type: 'COMMUNITIES_DETECTED',
        payload: { communities }
      };
      
      self.postMessage(response);
    } catch (error) {
      console.error('Error in Louvain worker:', error);
      // Send empty result on error
      const response: WorkerResponse = {
        type: 'COMMUNITIES_DETECTED',
        payload: { communities: {} }
      };
      self.postMessage(response);
    }
  }
};

// Export for TypeScript
export {};
