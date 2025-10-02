// Worker Manager for handling web workers with fallbacks
// Provides a unified interface for running CPU-intensive tasks

import louvain from 'graphology-communities-louvain';
import forceAtlas2 from 'graphology-layout-forceatlas2';

export interface WorkerTask<TInput, TOutput> {
  input: TInput;
  onSuccess: (result: TOutput) => void;
  onError: (error: Error) => void;
}

export interface LouvainInput {
  nodes: Array<{ id: string; [key: string]: any }>;
  edges: Array<{ source: string; target: string; [key: string]: any }>;
  options?: {
    resolution?: number;
    randomWalk?: boolean;
  };
}

export interface LouvainOutput {
  communities: Record<string, number>;
  modularity: number;
  executionTime: number;
}

export interface LayoutInput {
  nodes: Array<{ id: string; x?: number; y?: number; [key: string]: any }>;
  edges: Array<{ source: string; target: string; [key: string]: any }>;
  options?: {
    iterations?: number;
    settings?: any;
  };
}

export interface LayoutOutput {
  positions: Record<string, { x: number; y: number }>;
  converged: boolean;
  iterations: number;
  executionTime: number;
}

class WorkerManager {
  private louvainWorker: Worker | null = null;
  private layoutWorker: Worker | null = null;
  private workerSupported: boolean;
  private taskQueue: Array<WorkerTask<any, any>> = [];
  private isProcessing = false;

  constructor() {
    this.workerSupported = typeof Worker !== 'undefined';
  }

  // Louvain community detection
  async runLouvain(input: LouvainInput): Promise<LouvainOutput> {
    if (!this.workerSupported || input.nodes.length < 200) {
      // Fallback to main thread for small graphs or unsupported browsers
      return this.runLouvainMainThread(input);
    }

    return new Promise((resolve, reject) => {
      const task: WorkerTask<LouvainInput, LouvainOutput> = {
        input,
        onSuccess: resolve,
        onError: reject,
      };

      this.taskQueue.push(task);
      this.processQueue();
    });
  }

  // ForceAtlas2 layout computation
  async runLayout(input: LayoutInput): Promise<LayoutOutput> {
    if (!this.workerSupported || input.nodes.length < 200) {
      // Fallback to main thread for small graphs or unsupported browsers
      return this.runLayoutMainThread(input);
    }

    return new Promise((resolve, reject) => {
      const task: WorkerTask<LayoutInput, LayoutOutput> = {
        input,
        onSuccess: resolve,
        onError: reject,
      };

      this.taskQueue.push(task);
      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.isProcessing || this.taskQueue.length === 0) return;

    this.isProcessing = true;

    while (this.taskQueue.length > 0) {
      const task = this.taskQueue.shift();
      if (!task) break;

      try {
        // Determine which worker to use based on task type
        if (this.isLouvainTask(task)) {
          await this.processLouvainTask(task);
        } else if (this.isLayoutTask(task)) {
          await this.processLayoutTask(task);
        }
      } catch (error) {
        task.onError(error instanceof Error ? error : new Error('Unknown worker error'));
      }
    }

    this.isProcessing = false;
  }

  private isLouvainTask(task: WorkerTask<any, any>): task is WorkerTask<LouvainInput, LouvainOutput> {
    return 'nodes' in task.input && 'edges' in task.input && !('x' in (task.input.nodes[0] || {}));
  }

  private isLayoutTask(task: WorkerTask<any, any>): task is WorkerTask<LayoutInput, LayoutOutput> {
    return 'nodes' in task.input && 'edges' in task.input && 'x' in (task.input.nodes[0] || {});
  }

  private async processLouvainTask(task: WorkerTask<LouvainInput, LouvainOutput>) {
    if (!this.louvainWorker) {
      this.louvainWorker = new Worker(new URL('../workers/louvain.worker.ts', import.meta.url));
    }

    const worker = this.louvainWorker;
    
    const handleMessage = (event: MessageEvent) => {
      worker.removeEventListener('message', handleMessage);
      worker.removeEventListener('error', handleError);
      
      if (event.data.error) {
        task.onError(new Error(event.data.error));
      } else {
        task.onSuccess(event.data);
      }
    };

    const handleError = (error: ErrorEvent) => {
      worker.removeEventListener('message', handleMessage);
      worker.removeEventListener('error', handleError);
      task.onError(new Error(error.message));
    };

    worker.addEventListener('message', handleMessage);
    worker.addEventListener('error', handleError);
    worker.postMessage(task.input);
  }

  private async processLayoutTask(task: WorkerTask<LayoutInput, LayoutOutput>) {
    if (!this.layoutWorker) {
      this.layoutWorker = new Worker(new URL('../workers/layout.worker.ts', import.meta.url));
    }

    const worker = this.layoutWorker;
    
    const handleMessage = (event: MessageEvent) => {
      worker.removeEventListener('message', handleMessage);
      worker.removeEventListener('error', handleError);
      
      if (event.data.error) {
        task.onError(new Error(event.data.error));
      } else {
        task.onSuccess(event.data);
      }
    };

    const handleError = (error: ErrorEvent) => {
      worker.removeEventListener('message', handleMessage);
      worker.removeEventListener('error', handleError);
      task.onError(new Error(error.message));
    };

    worker.addEventListener('message', handleMessage);
    worker.addEventListener('error', handleError);
    worker.postMessage(task.input);
  }

  // Main thread fallbacks
  private runLouvainMainThread(input: LouvainInput): LouvainOutput {
    const startTime = performance.now();
    
    try {
      // Create a simple graph structure
      const graph = {
        nodes: input.nodes.map(n => n.id),
        edges: input.edges.map(e => ({ source: e.source, target: e.target })),
      };
      
      const communities = louvain.assign(graph, {
        resolution: input.options?.resolution || 1.0,
        randomWalk: input.options?.randomWalk || false,
      });
      
      const executionTime = performance.now() - startTime;
      
      return {
        communities,
        modularity: louvain.modularity(graph, communities),
        executionTime,
      };
    } catch (error) {
      throw new Error(`Louvain main thread error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private runLayoutMainThread(input: LayoutInput): LayoutOutput {
    const startTime = performance.now();
    
    try {
      // Create a simple graph structure
      const graph = {
        nodes: input.nodes.map(n => ({
          id: n.id,
          x: n.x || 0,
          y: n.y || 0,
          size: n.size || 1,
        })),
        edges: input.edges.map(e => ({
          source: e.source,
          target: e.target,
          weight: e.weight || 1,
        })),
      };
      
      const iterations = input.options?.iterations || 100;
      const settings = {
        gravity: 1,
        scaling: 1,
        strongGravity: false,
        linLogMode: false,
        outboundAttractionDistribution: false,
        adjustSizes: false,
        edgeWeightInfluence: 0,
        slowDown: 1,
        ...input.options?.settings,
      };
      
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
      
      return {
        positions: result,
        converged: true,
        iterations,
        executionTime,
      };
    } catch (error) {
      throw new Error(`Layout main thread error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  // Cleanup workers
  destroy() {
    if (this.louvainWorker) {
      this.louvainWorker.terminate();
      this.louvainWorker = null;
    }
    if (this.layoutWorker) {
      this.layoutWorker.terminate();
      this.layoutWorker = null;
    }
    this.taskQueue = [];
  }
}

// Export singleton instance
export const workerManager = new WorkerManager();
