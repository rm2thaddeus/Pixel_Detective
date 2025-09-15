interface WorkerRequest {
  type: 'PROCESS';
  payload: {
    nodes: any[];
    relations: any[];
    minDegree?: number;
    iterations?: number;
  };
}

interface WorkerResponse {
  type: 'RESULT';
  payload: {
    nodes: any[];
    relations: any[];
  };
}

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const { nodes, relations, minDegree = 0, iterations = 100 } = event.data.payload;

  // compute degree map
  const degree = new Map<string, number>();
  for (const r of relations || []) {
    const a = String((r as any).source ?? (r as any).from ?? (r as any).a ?? '');
    const b = String((r as any).target ?? (r as any).to ?? (r as any).b ?? '');
    if (a) degree.set(a, (degree.get(a) || 0) + 1);
    if (b) degree.set(b, (degree.get(b) || 0) + 1);
  }

  // filter nodes by degree
  const filteredNodes = nodes
    .filter(n => (degree.get(String(n.id)) || 0) >= minDegree)
    .map(n => ({ ...n, degree: degree.get(String(n.id)) || 0 }));

  const visible = new Set(filteredNodes.map(n => String(n.id)));
  const filteredRelations = relations.filter(r => {
    const a = String((r as any).source ?? (r as any).from ?? (r as any).a ?? '');
    const b = String((r as any).target ?? (r as any).to ?? (r as any).b ?? '');
    return visible.has(a) && visible.has(b);
  });

  try {
    const Graph = require('graphology');
    const forceAtlas2 = require('graphology-layout-forceatlas2');
    const graph = new Graph();

    filteredNodes.forEach(n => {
      graph.addNode(String(n.id), n);
    });
    filteredRelations.forEach(e => {
      const s = String((e as any).source ?? (e as any).from ?? (e as any).a ?? '');
      const t = String((e as any).target ?? (e as any).to ?? (e as any).b ?? '');
      if (graph.hasNode(s) && graph.hasNode(t)) {
        graph.addEdge(s, t, e);
      }
    });

    forceAtlas2.assign(graph, { iterations });

    const nodesWithPos = filteredNodes.map(n => {
      const attrs = graph.getNodeAttributes(String(n.id)) as any;
      return { ...n, x: attrs.x, y: attrs.y };
    });

    const response: WorkerResponse = {
      type: 'RESULT',
      payload: { nodes: nodesWithPos, relations: filteredRelations }
    };
    (self as any).postMessage(response);
  } catch (err) {
    const response: WorkerResponse = {
      type: 'RESULT',
      payload: { nodes: filteredNodes, relations: filteredRelations }
    };
    (self as any).postMessage(response);
  }
};

export {};
