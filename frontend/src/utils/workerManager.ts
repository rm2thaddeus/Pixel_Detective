// Worker manager for handling web workers in the knowledge graph
// Provides a clean interface for communicating with workers

export interface WorkerManager {
  detectCommunities: (nodes: any[], edges: any[], resolution?: number) => Promise<{ [nodeId: string]: number }>;
  computeLayout: (nodes: any[], edges: any[], iterations?: number, settings?: any) => Promise<{ [nodeId: string]: { x: number; y: number } }>;
  terminate: () => void;
}

class WorkerManagerImpl implements WorkerManager {
  private louvainWorker: Worker | null = null;
  private layoutWorker: Worker | null = null;
  private workerPromises: Map<string, { resolve: Function; reject: Function }> = new Map();

  constructor() {
    this.initializeWorkers();
  }

  private initializeWorkers() {
    try {
      // Initialize Louvain worker
      this.louvainWorker = new Worker(new URL('../workers/louvain.worker.ts', import.meta.url));
      this.louvainWorker.onmessage = (event) => {
        this.handleWorkerMessage('louvain', event);
      };
      this.louvainWorker.onerror = (error) => {
        console.error('Louvain worker error:', error);
        this.rejectWorkerPromise('louvain', error);
      };

      // Initialize layout worker
      this.layoutWorker = new Worker(new URL('../workers/layout.worker.ts', import.meta.url));
      this.layoutWorker.onmessage = (event) => {
        this.handleWorkerMessage('layout', event);
      };
      this.layoutWorker.onerror = (error) => {
        console.error('Layout worker error:', error);
        this.rejectWorkerPromise('layout', error);
      };
    } catch (error) {
      console.warn('Failed to initialize workers, falling back to main thread:', error);
    }
  }

  private handleWorkerMessage(workerType: string, event: MessageEvent) {
    const { type, payload } = event.data;
    const promiseKey = `${workerType}-${type}`;
    
    if (this.workerPromises.has(promiseKey)) {
      const { resolve } = this.workerPromises.get(promiseKey)!;
      this.workerPromises.delete(promiseKey);
      resolve(payload);
    }
  }

  private rejectWorkerPromise(workerType: string, error: any) {
    // Reject all pending promises for this worker
    for (const [key, { reject }] of this.workerPromises.entries()) {
      if (key.startsWith(workerType)) {
        this.workerPromises.delete(key);
        reject(error);
      }
    }
  }

  async detectCommunities(nodes: any[], edges: any[], resolution: number = 1.0): Promise<{ [nodeId: string]: number }> {
    if (!this.louvainWorker) {
      // Fallback to main thread if worker is not available
      return this.detectCommunitiesMainThread(nodes, edges, resolution);
    }

    return new Promise((resolve, reject) => {
      const promiseKey = 'louvain-COMMUNITIES_DETECTED';
      this.workerPromises.set(promiseKey, { resolve, reject });

      this.louvainWorker!.postMessage({
        type: 'DETECT_COMMUNITIES',
        payload: { nodes, edges, resolution }
      });

      // Timeout after 10 seconds
      setTimeout(() => {
        if (this.workerPromises.has(promiseKey)) {
          this.workerPromises.delete(promiseKey);
          reject(new Error('Community detection timeout'));
        }
      }, 10000);
    });
  }

  async computeLayout(nodes: any[], edges: any[], iterations: number = 100, settings: any = {}): Promise<{ [nodeId: string]: { x: number; y: number } }> {
    if (!this.layoutWorker) {
      // Fallback to main thread if worker is not available
      return this.computeLayoutMainThread(nodes, edges, iterations, settings);
    }

    return new Promise((resolve, reject) => {
      const promiseKey = 'layout-LAYOUT_COMPUTED';
      this.workerPromises.set(promiseKey, { resolve, reject });

      this.layoutWorker!.postMessage({
        type: 'COMPUTE_LAYOUT',
        payload: { nodes, edges, iterations, settings }
      });

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.workerPromises.has(promiseKey)) {
          this.workerPromises.delete(promiseKey);
          reject(new Error('Layout computation timeout'));
        }
      }, 30000);
    });
  }

  // Fallback methods for main thread execution
  private async detectCommunitiesMainThread(nodes: any[], edges: any[], resolution: number): Promise<{ [nodeId: string]: number }> {
    try {
      const Graph = require('graphology');
      const louvain = require('graphology-communities-louvain');
      
      const graph = new Graph();
      
      // Add nodes
      nodes.forEach(node => {
        graph.addNode(node.id, node);
      });
      
      // Add edges
      edges.forEach(edge => {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, edge);
        }
      });
      
      // Run Louvain algorithm
      louvain.assign(graph, { resolution });
      
      // Extract communities
      const communities: { [nodeId: string]: number } = {};
      graph.forEachNode((nodeId, attributes) => {
        communities[nodeId] = (attributes as any).community || 0;
      });
      
      return communities;
    } catch (error) {
      console.error('Error in main thread community detection:', error);
      return {};
    }
  }

  private async computeLayoutMainThread(nodes: any[], edges: any[], iterations: number, settings: any): Promise<{ [nodeId: string]: { x: number; y: number } }> {
    try {
      const Graph = require('graphology');
      const forceAtlas2 = require('graphology-layout-forceatlas2');
      
      const graph = new Graph();
      
      // Add nodes
      nodes.forEach(node => {
        const attrs: any = { ...node };
        if (typeof node.x === 'number' && typeof node.y === 'number') {
          attrs.x = node.x;
          attrs.y = node.y;
        }
        graph.addNode(node.id, attrs);
      });
      
      // Add edges
      edges.forEach(edge => {
        if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
          graph.addEdge(edge.source, edge.target, edge);
        }
      });
      
      // Run ForceAtlas2 layout
      forceAtlas2(graph, {
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
      const positions: { [nodeId: string]: { x: number; y: number } } = {};
      graph.forEachNode((nodeId, attributes) => {
        const attrs = attributes as any;
        if (typeof attrs.x === 'number' && typeof attrs.y === 'number') {
          positions[nodeId] = { x: attrs.x, y: attrs.y };
        }
      });
      
      return positions;
    } catch (error) {
      console.error('Error in main thread layout computation:', error);
      return {};
    }
  }

  terminate() {
    if (this.louvainWorker) {
      this.louvainWorker.terminate();
      this.louvainWorker = null;
    }
    if (this.layoutWorker) {
      this.layoutWorker.terminate();
      this.layoutWorker = null;
    }
    this.workerPromises.clear();
  }
}

// Export singleton instance
export const workerManager = new WorkerManagerImpl();
