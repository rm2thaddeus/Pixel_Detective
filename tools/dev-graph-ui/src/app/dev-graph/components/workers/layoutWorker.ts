// Web worker to preprocess graph data: compute degrees, filter nodes, and apply time-radial layout
// This mirrors logic previously run on the main thread in WebGLEvolutionGraph.

export interface LayoutWorkerInput {
  nodes: any[];
  relations: any[];
  maxEdgesInView: number;
  layoutMode: 'time-radial' | 'force';
  width: number;
  height: number;
}

export interface LayoutWorkerOutput {
  nodes: any[];
  relations: any[];
  commitPos: Record<string, { x: number; y: number; r?: number; theta?: number }>;
  fileHome: Record<string, string>;
  layoutPos: Record<string, { x: number; y: number }>;
  commitIndex: Record<string, number>;
  touchDomain: { min: number; max: number };
}

self.onmessage = (event: MessageEvent<LayoutWorkerInput>) => {
  const { nodes = [], relations = [], maxEdgesInView, layoutMode, width, height } = event.data;

  const deg = new Map<string, number>();
  for (const r of relations) {
    const a = String((r as any).source ?? (r as any).from ?? '');
    const b = String((r as any).target ?? (r as any).to ?? '');
    if (a) deg.set(a, (deg.get(a) || 0) + 1);
    if (b) deg.set(b, (deg.get(b) || 0) + 1);
  }

  let processedNodes = nodes.map(n => {
    const loc = (n.loc ?? n.lines_after ?? n.size ?? 1) as number;
    const d = (n.degree ?? deg.get(String(n.id)) ?? 0) as number;
    const importance = Math.max(1, (loc * 0.7) + (d * 3));
    let folderPath = n.folderPath;
    if (!folderPath && typeof n.path === 'string') {
      const norm = (n.path as string).replace(/\\/g, '/');
      const idx = norm.indexOf('/');
      folderPath = idx === -1 ? norm : norm.slice(0, idx);
    }
    const filesTouched = (n.filesTouched ?? n.files_count ?? 0) as number;
    const touchCount = (n.touchCount ?? n.touches ?? d ?? 0) as number;
    return { ...n, importance, folderPath, degree: d, filesTouched, touchCount };
  });
  let processedRelations = relations;

  const nodeCount = nodes.length;
  if (nodeCount > maxEdgesInView) {
    processedNodes = nodes
      .map(node => ({
        ...node,
        importance: (node.size || 0) + (node.degree || 0) * 0.5,
      }))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, maxEdgesInView);

    const visibleNodeIds = new Set(processedNodes.map(n => String(n.id)));
    processedRelations = relations.filter(rel => {
      const src = String((rel as any).source ?? (rel as any).from ?? '');
      const tgt = String((rel as any).target ?? (rel as any).to ?? '');
      return visibleNodeIds.has(src) && visibleNodeIds.has(tgt);
    });
  }

  const commitPos = new Map<string, { x: number; y: number; r: number; theta: number }>();
  const fileHome = new Map<string, string>();
  const layoutPos = new Map<string, { x: number; y: number }>();

  if (layoutMode === 'time-radial') {
    const cx = width / 2;
    const cy = height / 2;
    const commits = processedNodes.filter((n: any) => (n.originalType === 'GitCommit' || n.type === 'commit'));
    const files = processedNodes.filter(n => !(n.originalType === 'GitCommit' || n.type === 'commit'));

    const timeOf = (n: any) => Number(new Date(n.timestamp || n.created_at || n.time || 0));
    commits.sort((a, b) => timeOf(a) - timeOf(b));

    const a = 60;
    const b = Math.max(10, Math.min(24, 14 + Math.log1p(commits.length) * 4));
    const thetaStep = Math.PI * 0.45;

    for (let i = 0; i < commits.length; i++) {
      const c = commits[i];
      const theta = i * thetaStep;
      const r = a + b * theta;
      const x = cx + r * Math.cos(theta);
      const y = cy + r * Math.sin(theta);
      c.x = x; c.y = y;
      commitPos.set(String(c.id), { x, y, r, theta });
      layoutPos.set(String(c.id), { x, y });
    }

    const rels = processedRelations || [];
    const byCommit = new Map<string, Set<string>>();
    for (const r of rels) {
      const type = (r as any).type || (r as any).originalType;
      if (type !== 'touch') continue;
      const src = String((r as any).source ?? (r as any).from ?? '');
      const tgt = String((r as any).target ?? (r as any).to ?? '');
      const isSrcCommit = commitPos.has(src);
      const commitId = isSrcCommit ? src : (commitPos.has(tgt) ? tgt : '');
      const fileId = isSrcCommit ? tgt : src;
      if (!commitId || !fileId) continue;
      if (!byCommit.has(commitId)) byCommit.set(commitId, new Set());
      byCommit.get(commitId)!.add(fileId);
      if (!fileHome.has(fileId)) fileHome.set(fileId, commitId);
    }

    const counters = new Map<string, number>();
    const jitter = (s: string) => {
      let h = 2166136261;
      for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24); }
      const u = (h >>> 0) / 0xffffffff;
      return (u - 0.5) * 6;
    };

    for (const f of files) {
      const fid = String(f.id);
      const home = fileHome.get(fid);
      let cp: { x: number; y: number; r: number; theta: number } | undefined;
      if (home) {
        cp = commitPos.get(home);
      } else {
        cp = undefined;
      }
      if (!cp) {
        const x = cx + jitter(fid);
        const y = cy + jitter(fid + 'y');
        f.x = x; f.y = y; layoutPos.set(fid, { x, y });
        continue;
      }
      const homeKey = String(home ?? '');
      const count = (counters.get(homeKey) || 0);
      counters.set(homeKey, count + 1);
      const dir = { x: Math.cos(cp.theta), y: Math.sin(cp.theta) };
      const perp = { x: -dir.y, y: dir.x };
      const baseOut = 28;
      const gap = 12;
      const outward = baseOut + gap * count;
      const lateral = ((count % 2 === 0) ? 1 : -1) * (4 + (count * 0.6)) + jitter(fid);
      const x = cp.x + dir.x * outward + perp.x * lateral;
      const y = cp.y + dir.y * outward + perp.y * lateral;
      f.x = x; f.y = y; layoutPos.set(fid, { x, y });
    }
  }

  const commitIndex = new Map<string, number>();
  try {
    const commits = processedNodes.filter(n => (n.originalType === 'GitCommit' || n.type === 'commit'));
    commits.sort((a, b) => Number(new Date(a.timestamp || a.time || 0)) - Number(new Date(b.timestamp || b.time || 0)));
    for (let i = 0; i < commits.length; i++) commitIndex.set(String(commits[i].id as string), i);
  } catch {}

  let minT = Infinity, maxT = -Infinity;
  try {
    for (const n of processedNodes) {
      if (n.originalType === 'GitCommit' || n.type === 'commit') continue;
      const t = n.touchCount ?? n.degree ?? 0;
      if (t < minT) minT = t; if (t > maxT) maxT = t;
    }
    if (!isFinite(minT)) { minT = 0; maxT = 1; }
  } catch { minT = 0; maxT = 1; }

  const output: LayoutWorkerOutput = {
    nodes: processedNodes,
    relations: processedRelations,
    commitPos: Object.fromEntries(commitPos),
    fileHome: Object.fromEntries(fileHome),
    layoutPos: Object.fromEntries(layoutPos),
    commitIndex: Object.fromEntries(commitIndex),
    touchDomain: { min: minT, max: Math.max(minT + 1, maxT) },
  };

  (self as any).postMessage(output);
};

export {};
