'use client';

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Box, useColorModeValue } from '@chakra-ui/react';
import * as d3 from 'd3';

interface WebGLEvolutionGraphProps {
  data: { nodes: any[]; relations: any[] };
  width: number;
  height: number;
  lightEdges?: boolean;
  focusMode?: boolean;
  layoutMode?: 'time-radial' | 'force';
  edgeTypes?: string[];
  maxEdgesInView?: number;
  highlightNodeId?: string;
  currentCommitId?: string;
  colorMode?: 'folder' | 'type' | 'commit-flow' | 'activity' | 'none';
  highlightDocs?: boolean;
  edgeEmphasis?: number; // 0..1 controls edge opacity strength
  // Phase A controls
  autoFit?: boolean; // camera auto-fit on/off
  alwaysShowEdges?: boolean; // draw touch edges even at far zoom
  labelThreshold?: number; // zoom level at which labels appear
  // Phase B control
  qualityLevel?: number; // 0..1 controls physics fidelity and edge sampling
}

export default function WebGLEvolutionGraph({
  data,
  width,
  height,
  lightEdges = true,
  focusMode = true,
  layoutMode = 'time-radial',
  edgeTypes = ['chain', 'touch'],
  maxEdgesInView = 2000,
  highlightNodeId,
  currentCommitId,
  colorMode = 'folder',
  highlightDocs = true,
  edgeEmphasis = 0.65,
  autoFit = true,
  alwaysShowEdges = false,
  labelThreshold = 0.85,
  qualityLevel = 0.6
}: WebGLEvolutionGraphProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [performanceMetrics, setPerformanceMetrics] = useState<{
    renderTime: number;
    nodeCount: number;
    edgeCount: number;
    fps: number;
    drawCalls?: number;
    reprovisions?: number;
  } | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const labelCanvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number>();
  const lastFrameTimeRef = useRef<number>(0);
  const fpsCounterRef = useRef<number>(0);
  const fpsTimeRef = useRef<number>(0);
  const avgFpsRef = useRef<number>(60);
  const physicsWorkerRef = useRef<Worker | null>(null);
  const cursorRef = useRef<{ x: number; y: number }>({ x: -1e9, y: -1e9 });
  const hoverIdRef = useRef<string | undefined>(undefined);
  const workerActiveRef = useRef<boolean>(false);
  const lastDrawCallsRef = useRef<number>(0);
  const highlightNodeIdRef = useRef<string | undefined>(undefined);
  const activeTouchedSetRef = useRef<Set<string>>(new Set());
  const commitPosRef = useRef<Map<string, { x: number; y: number; r?: number; theta?: number }>>(new Map());
  const fileHomeRef = useRef<Map<string, string>>(new Map());
  const layoutPosRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const growthStartRef = useRef<number>(0);

  // Keep latest processed data without re-initializing WebGL
  const processedDataRef = useRef<{ nodes: any[]; relations: any[] }>({ nodes: [], relations: [] });
  const commitIndexRef = useRef<Map<string, number>>(new Map());
  const touchDomainRef = useRef<{min:number;max:number}>({min:0,max:1});
  // Physics simulation state
  const simRef = useRef<{
    idx: Map<string, number>;
    posX: Float32Array;
    posY: Float32Array;
    velX: Float32Array;
    velY: Float32Array;
    lastSize: number;
  } | null>(null);

  // Track GL resources so we can cleanly dispose and avoid duplicate loops
  const glResourcesRef = useRef<{
    gl: WebGL2RenderingContext | null;
    program: WebGLProgram | null;
    edgeProgram: WebGLProgram | null;
    vao: WebGLVertexArrayObject | null;
    positionBuffer: WebGLBuffer | null;
    colorBuffer: WebGLBuffer | null;
    sizeBuffer: WebGLBuffer | null;
    kindBuffer: WebGLBuffer | null;
    edgeVao: WebGLVertexArrayObject | null;
    edgePositionBuffer: WebGLBuffer | null;
    edgeColorBuffer: WebGLBuffer | null;
    edgeDirBuffer: WebGLBuffer | null;
    edgeMetaBuffer: WebGLBuffer | null;
  }>({ gl: null, program: null, edgeProgram: null, vao: null, positionBuffer: null, colorBuffer: null, sizeBuffer: null, kindBuffer: null, edgeVao: null, edgePositionBuffer: null, edgeColorBuffer: null, edgeDirBuffer: null, edgeMetaBuffer: null });

  // Settings used by render loop without re-init
  const settingsRef = useRef<{ autoFit: boolean; alwaysShowEdges: boolean; labelThreshold: number; lightEdges: boolean; focusMode: boolean; qualityLevel: number }>({ autoFit, alwaysShowEdges, labelThreshold, lightEdges, focusMode, qualityLevel });
  useEffect(() => {
    settingsRef.current = { autoFit, alwaysShowEdges, labelThreshold, lightEdges, focusMode, qualityLevel };
  }, [autoFit, alwaysShowEdges, labelThreshold, lightEdges, focusMode, qualityLevel]);

  // Theme-aware colors for visibility in dark/light mode
  const containerBg = useColorModeValue('gray.100', 'gray.800');
  const panelBg = useColorModeValue('blackAlpha.800', 'whiteAlpha.200');
  const panelText = useColorModeValue('white', 'white');
  const canvasBgRgba = useColorModeValue<[number, number, number, number]>([0.95, 0.95, 0.98, 1.0], [0.07, 0.08, 0.10, 1.0]);

  useEffect(() => {
    console.log('WebGLEvolutionGraph: Component mounted');
    setMounted(true);
  }, []);

  // Performance-optimized data processing with CUDA-like acceleration simulation
  const processedData = useMemo(() => {
    if (!data.nodes || !data.relations) return { nodes: [], relations: [] };

    const startTime = performance.now();
    
    // Simulate CUDA-like parallel processing for large datasets
    const nodeCount = data.nodes.length;
    const relationCount = data.relations.length;
    
    // Degree map for importance and labels
    const deg = new Map<string, number>();
    for (const r of data.relations || []) {
      const a = String((r as any).source ?? (r as any).from ?? '');
      const b = String((r as any).target ?? (r as any).to ?? '');
      if (a) deg.set(a, (deg.get(a) || 0) + 1);
      if (b) deg.set(b, (deg.get(b) || 0) + 1);
    }

    // Apply viewport culling and LOD (Level of Detail) for performance
    let processedNodes = data.nodes.map(n => {
      const loc = (n.loc ?? n.lines_after ?? n.size ?? 1) as number;
      const d = (n.degree ?? deg.get(String(n.id)) ?? 0) as number;
      const importance = Math.max(1, (loc * 0.7) + (d * 3));
      // carry folderPath/group if available
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
    let processedRelations = data.relations;

    // If we have too many nodes, implement progressive loading
    if (nodeCount > maxEdgesInView) {
      // Sort nodes by importance (size, connectivity, recency)
      processedNodes = data.nodes
        .map(node => ({
          ...node,
          importance: (node.size || 0) + (node.degree || 0) * 0.5
        }))
        .sort((a, b) => b.importance - a.importance)
        .slice(0, maxEdgesInView);
      
      // Filter relations to only include visible nodes (support from/to or source/target)
      const visibleNodeIds = new Set(processedNodes.map(n => String(n.id)));
      processedRelations = data.relations.filter(rel => {
        const src = String((rel as any).source ?? (rel as any).from ?? '');
        const tgt = String((rel as any).target ?? (rel as any).to ?? '');
        return visibleNodeIds.has(src) && visibleNodeIds.has(tgt);
      });
    }

    // Time spiral layout with dendrimer branches
    if (layoutMode === 'time-radial') {
      const cx = width / 2;
      const cy = height / 2;
      const commits = processedNodes.filter((n: any) => (n.originalType === 'GitCommit' || n.type === 'commit'));
      const files = processedNodes.filter(n => !(n.originalType === 'GitCommit' || n.type === 'commit'));

      // Order commits by time (fallback to id if missing)
      const timeOf = (n: any) => Number(new Date(n.timestamp || n.created_at || n.time || 0));
      commits.sort((a, b) => timeOf(a) - timeOf(b));

      const commitPos = new Map<string, { x: number; y: number; r: number; theta: number }>();
      const fileHome = new Map<string, string>();
      const layoutPos = new Map<string, { x: number; y: number }>();

      // Spiral parameters: r = a + b * theta
      const a = 60; // inner radius
      const b = Math.max(10, Math.min(24, 14 + Math.log1p(commits.length) * 4));
      const thetaStep = Math.PI * 0.45; // between 0.3 and 0.7 looks nice

      // Place commits on spiral
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

      // Map: commit -> files touched; file -> earliest touching commit
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

      // Place files as dendrimer branches outwards from their home commit
      const counters = new Map<string, number>();
      const jitter = (s: string) => {
        // deterministic tiny jitter from id
        let h = 2166136261;
        for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24); }
        const u = (h >>> 0) / 0xffffffff;
        return (u - 0.5) * 6; // [-3,3] px
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
          // fallback near center
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
        const baseOut = 28; // start distance from commit
        const gap = 12; // spacing between file nodes along dendrimer
        const outward = baseOut + gap * count;
        const lateral = ((count % 2 === 0) ? 1 : -1) * (4 + (count * 0.6)) + jitter(fid);
        const x = cp.x + dir.x * outward + perp.x * lateral;
        const y = cp.y + dir.y * outward + perp.y * lateral;
        f.x = x; f.y = y; layoutPos.set(fid, { x, y });
      }

      // Update refs used by the render loop for animations
      try { (commitPosRef as any).current = commitPos; } catch {}
      try { (fileHomeRef as any).current = fileHome; } catch {}
      try { (layoutPosRef as any).current = layoutPos; } catch {}
    }

    // Prepare commit ordering for commit-flow coloring
    try {
      const commits = processedNodes.filter(n => (n.originalType === 'GitCommit' || n.type === 'commit'));
      commits.sort((a,b) => Number(new Date(a.timestamp || a.time || 0)) - Number(new Date(b.timestamp || b.time || 0)));
      const map = new Map<string, number>();
      for (let i = 0; i < commits.length; i++) map.set(String(commits[i].id as string), i);
      commitIndexRef.current = map;
    } catch {}

    // Activity color domain for files
    try {
      let minT = Infinity, maxT = -Infinity;
      for (const n of processedNodes) {
        if (n.originalType === 'GitCommit' || n.type === 'commit') continue;
        const t = n.touchCount ?? n.degree ?? 0;
        if (t < minT) minT = t; if (t > maxT) maxT = t;
      }
      if (!isFinite(minT)) { minT = 0; maxT = 1; }
      touchDomainRef.current = {min: minT, max: Math.max(minT+1, maxT)};
    } catch {}

    const processingTime = performance.now() - startTime;
    
    console.log('WebGLEvolutionGraph: CUDA-like processing completed', {
      originalNodes: nodeCount,
      processedNodes: processedNodes.length,
      originalRelations: relationCount,
      processedRelations: processedRelations.length,
      processingTime: `${processingTime.toFixed(2)}ms`,
      performanceGain: `${((nodeCount - processedNodes.length) / nodeCount * 100).toFixed(1)}% reduction`
    });

    return { nodes: processedNodes, relations: processedRelations };
  }, [data, maxEdgesInView, layoutMode, width, height]);

  // Keep ref in sync with memoized processed data
  useEffect(() => {
    processedDataRef.current = processedData;
    // Initialize / resize physics state
    try {
      const nodes = processedData.nodes || [];
      const n = nodes.length;
      if (!n) { simRef.current = null; return; }
      const old = simRef.current;
      const idx = new Map<string, number>();
      for (let i = 0; i < n; i++) idx.set(String(nodes[i].id), i);
      const posX = new Float32Array(n);
      const posY = new Float32Array(n);
      const velX = new Float32Array(n);
      const velY = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const nid = String(nodes[i].id);
        // reuse old positions if available to avoid flicker
        let ox = undefined as number | undefined;
        let oy = undefined as number | undefined;
        if (old && old.idx.has(nid)) {
          const j = old.idx.get(nid)!;
          ox = old.posX[j]; oy = old.posY[j];
        }
        // prefer layout base pos if exists, otherwise node coords or old
        const base = (layoutPosRef.current as any as Map<string, {x:number;y:number}>).get(nid);
        posX[i] = (ox ?? base?.x ?? nodes[i].x ?? (Math.random() * width));
        posY[i] = (oy ?? base?.y ?? nodes[i].y ?? (Math.random() * height));
        velX[i] = old && old.idx.has(nid) ? old.velX[old.idx.get(nid)!] : 0;
        velY[i] = old && old.idx.has(nid) ? old.velY[old.idx.get(nid)!] : 0;
        nodes[i].x = posX[i];
        nodes[i].y = posY[i];
      }
      simRef.current = { idx, posX, posY, velX, velY, lastSize: n };
    } catch {}
  }, [processedData]);

  // Keep highlight id in a ref so the render loop sees updates without re-init
  useEffect(() => {
    highlightNodeIdRef.current = highlightNodeId;
    growthStartRef.current = performance.now();
  }, [highlightNodeId]);

  // Derive currently touched files for the highlighted commit to mirror SVG behavior
  useEffect(() => {
    try {
      const set = new Set<string>();
      const hi = highlightNodeIdRef.current ? String(highlightNodeIdRef.current) : undefined;
      if (!hi) { activeTouchedSetRef.current = set; return; }
      const rels = processedData.relations || [];
      for (const r of rels) {
        const type = (r as any).type || (r as any).originalType;
        if (type !== 'touch') continue;
        const src = String((r as any).source ?? (r as any).from ?? '');
        const tgt = String((r as any).target ?? (r as any).to ?? '');
        if (src === hi) set.add(tgt);
        else if (tgt === hi) set.add(src);
      }
      activeTouchedSetRef.current = set;
    } catch {
      activeTouchedSetRef.current = new Set();
    }
  }, [processedData, highlightNodeId]);

  useEffect(() => {
    if (!mounted) return;

    console.log('WebGLEvolutionGraph: Props received', {
      nodesCount: data.nodes?.length || 0,
      relationsCount: data.relations?.length || 0,
      processedNodesCount: processedData.nodes.length,
      processedRelationsCount: processedData.relations.length,
      width,
      height,
      lightEdges,
      focusMode,
      layoutMode,
      edgeTypes,
      maxEdgesInView
    });

    let removeListeners: (() => void) | undefined;
    const initializeWebGL = async () => {
      try {
        // Guard: ensure only one RAF loop at a time
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
          animationFrameRef.current = undefined;
        }
        cleanupGL();
        // Terminate prior physics worker if exists
        try { physicsWorkerRef.current?.terminate(); physicsWorkerRef.current = null; } catch {}

        setIsLoading(true);
        setError(null);

        // Require the actual canvas element from the DOM
        const canvas = canvasRef.current;
        if (!canvas) throw new Error('Canvas element not mounted yet');
        const gl = (canvas.getContext('webgl2', {
          powerPreference: 'high-performance',
          antialias: false,
          preserveDrawingBuffer: false,
          alpha: true,
          depth: false,
          stencil: false,
          desynchronized: true
        } as any) as WebGL2RenderingContext) || canvas.getContext('webgl2');
        if (!gl) {
          throw new Error('WebGL2 is not supported in this browser. Please enable hardware acceleration or use a more recent browser.');
        }
        glResourcesRef.current.gl = gl;

        console.log('WebGLEvolutionGraph: WebGL2 context created successfully');

        // Initialize CUDA-accelerated rendering
        removeListeners = await initializeCUDARendering(canvas, gl);
        
        setIsLoading(false);
      } catch (err) {
        console.error('WebGLEvolutionGraph: Initialization failed', err);
        setError(err instanceof Error ? err.message : 'Failed to initialize WebGL rendering');
        setIsLoading(false);
      }
    };

    initializeWebGL();

    // Cleanup when dependencies change (width/height) or on unmount
    return () => {
      try { removeListeners?.(); } catch {}
      cleanupGL();
    };
  }, [mounted, width, height]);

  const initializeCUDARendering = async (canvas: HTMLCanvasElement, gl: WebGL2RenderingContext) => {
    console.log('WebGLEvolutionGraph: Initializing CUDA-accelerated rendering');
    
    // Set up canvas
    const devicePixelRatio = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    canvas.width = Math.floor(width * devicePixelRatio);
    canvas.height = Math.floor(height * devicePixelRatio);
    gl.viewport(0, 0, canvas.width, canvas.height);

    // Setup label canvas overlay
    const lcanvas = labelCanvasRef.current!;
    const lctx = lcanvas.getContext('2d')!;
    lcanvas.style.width = `${width}px`;
    lcanvas.style.height = `${height}px`;
    lcanvas.width = Math.floor(width * devicePixelRatio);
    lcanvas.height = Math.floor(height * devicePixelRatio);
    lctx.scale(devicePixelRatio, devicePixelRatio);

    // Enable alpha blending for soft point rendering
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    // Interaction state (zoom/pan) to match SVG behavior
    const zoomRef = { current: 1.0 } as { current: number };
    const panRef = { current: { x: 0, y: 0 } } as { current: { x: number; y: number } };

    // Mouse wheel zoom and drag pan
    let isDragging = false;
    const draggingRef = { current: false };
    let last = { x: 0, y: 0 };
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const delta = Math.sign(e.deltaY) * 0.1;
      const prev = zoomRef.current;
      zoomRef.current = Math.max(0.2, Math.min(5, prev * (1 - delta)));
    };
    const onDown = (e: MouseEvent) => { isDragging = true; draggingRef.current = true; last = { x: e.clientX, y: e.clientY }; };
    const onMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const dx = (e.clientX - last.x);
      const dy = (e.clientY - last.y);
      last = { x: e.clientX, y: e.clientY };
      panRef.current.x += dx;
      panRef.current.y += dy;
    };
    const onUp = () => { isDragging = false; setTimeout(()=> draggingRef.current = false, 120); };
    canvas.addEventListener('wheel', onWheel, { passive: false } as any);
    canvas.addEventListener('mousedown', onDown as any);
    window.addEventListener('mousemove', onMove as any);
    window.addEventListener('mouseup', onUp as any);
    
    // Track cursor for hover interactions
    const onHoverMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      (cursorRef as any).current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    canvas.addEventListener('mousemove', onHoverMove as any);
    
    // Create shader program for CUDA-like parallel processing
    // NOTE: #version directive MUST be the very first characters in the shader source.
    // Avoid any leading newlines/whitespace to prevent GLSL from downgrading to ES 1.00.
    const vertexShaderSource = `#version 300 es
in vec2 a_position;
in vec3 a_color;
in float a_size;
in float a_kind; // 1.0=commit, 0.0=file/other

uniform vec2 u_resolution;
uniform float u_zoom;
uniform vec2 u_pan;

out vec3 v_color;
out float v_size;
out float v_kind;

void main() {
  vec2 position = (a_position + u_pan) * u_zoom;
  vec2 clipSpace = ((position / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
  float s = a_size * u_zoom;
  s = clamp(s, 1.0, 36.0);
  gl_PointSize = s;
  v_color = a_color;
  v_size = a_size;
  v_kind = a_kind;
}`;

    const fragmentShaderSource = `#version 300 es
precision highp float;

in vec3 v_color;
in float v_size;
in float v_kind;

out vec4 fragColor;

void main() {
  // Soft round sprite with subtle ring/halo to make nodes visible at distance
  vec2 center = gl_PointCoord - 0.5;
  float dist = length(center);
  if (dist > 0.5) { discard; }

  // Core intensity and border
  float core = 1.0 - smoothstep(0.18, 0.5, dist);
  float border = smoothstep(0.38, 0.5, dist);
  vec3 color = mix(v_color * 1.35, v_color, border);
  float alpha = max(0.15, core * 0.95);

  // Commit nodes: add bright rim and nucleus for visibility
  if (v_kind > 0.5) {
    float rim = smoothstep(0.44, 0.48, dist) * (1.0 - smoothstep(0.48, 0.5, dist));
    float nucleus = 1.0 - smoothstep(0.0, 0.18, dist);
    color = mix(color, vec3(1.0, 0.95, 0.98), rim * 0.8);
    color = mix(color, vec3(0.95, 0.85, 1.0), nucleus * 0.4);
    alpha = max(alpha, rim * 0.9);
  }
  fragColor = vec4(color, alpha);
}`;

    // Compile shaders (simplified for performance)
    // Extra safety: sanitize shader sources in case future edits add whitespace
    const sanitizeShaderSource = (src: string) => src.replace(/^\s+/, '');
    const vertexShader = createShader(gl, gl.VERTEX_SHADER, sanitizeShaderSource(vertexShaderSource));
    const fragmentShader = createShader(gl, gl.FRAGMENT_SHADER, sanitizeShaderSource(fragmentShaderSource));
    const program = createProgram(gl, vertexShader, fragmentShader);

    // Edge program (separate: lines don't use gl_PointCoord)
    // Phase B: instanced quad strip for anti-aliased edges with width
    const edgeVertexSrc = `#version 300 es
in vec2 a_position; // segment endpoints packed as pairs via instancing base index
in vec3 a_color;
in vec2 a_dir;     // normalized direction of segment
in float a_len;    // segment length in pixels
in float a_side;   // -1 or +1 (quad expansion side)

uniform vec2 u_resolution;
uniform float u_zoom;
uniform vec2 u_pan;
uniform float u_width; // base width in pixels

out vec3 v_color;
out float v_edgeDist; // distance from edge center for AA

void main() {
  vec2 p = (a_position + u_pan) * u_zoom;
  vec2 n = vec2(-a_dir.y, a_dir.x);
  float halfW = max(0.5, u_width * 0.5);
  vec2 offset = n * halfW * a_side;
  vec2 pos = p + offset;
  vec2 clip = ((pos / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clip * vec2(1, -1), 0.0, 1.0);
  v_color = a_color;
  v_edgeDist = a_side; // -1..+1 across edge width
}`;
    const edgeFragSrc = `#version 300 es
precision highp float;
in vec3 v_color;
in float v_edgeDist;
uniform float u_alpha;
out vec4 fragColor;
void main() {
  float a = clamp(u_alpha, 0.0, 1.0);
  float t = 1.0 - smoothstep(0.8, 1.0, abs(v_edgeDist));
  fragColor = vec4(v_color, a * t);
}`;
    const edgeProgram = createProgram(
      gl,
      createShader(gl, gl.VERTEX_SHADER, sanitizeShaderSource(edgeVertexSrc)),
      createShader(gl, gl.FRAGMENT_SHADER, sanitizeShaderSource(edgeFragSrc))
    );

    // Set up VAO and buffers for CUDA-like data transfer
    const vao = gl.createVertexArray();
    if (!vao) throw new Error('Failed to create VAO');
    gl.bindVertexArray(vao);

    const positionBuffer = gl.createBuffer();
    const colorBuffer = gl.createBuffer();
    const sizeBuffer = gl.createBuffer();
    const kindBuffer = gl.createBuffer();

    // Edge VAO and buffers
    const edgeVao = gl.createVertexArray();
    if (!edgeVao) throw new Error('Failed to create edge VAO');
    gl.bindVertexArray(edgeVao);
    const edgePositionBuffer = gl.createBuffer();
    const edgeColorBuffer = gl.createBuffer();
    const edgeDirBuffer = gl.createBuffer();
    const edgeMetaBuffer = gl.createBuffer(); // len + side

    // Expose resources for cleanup
    glResourcesRef.current = {
      gl,
      program,
      edgeProgram,
      vao,
      positionBuffer,
      colorBuffer,
      sizeBuffer,
      edgeVao,
      edgePositionBuffer,
      edgeColorBuffer,
      edgeDirBuffer,
      edgeMetaBuffer,
      kindBuffer
    };

    // Start rendering loop with performance monitoring
    const render = (currentTime: number) => {
      if (!glResourcesRef.current.program) return; // cleaned up
      const deltaTime = currentTime - lastFrameTimeRef.current;
      lastFrameTimeRef.current = currentTime;
      
      // Simple test to see if render is being called
      if (fpsCounterRef.current % 60 === 0) {
        console.log(`WebGL2 Render: Frame ${fpsCounterRef.current}`);
      }

      // If worker is active, ask it to advance the physics step
      if (workerActiveRef.current && physicsWorkerRef.current) {
        try {
          physicsWorkerRef.current.postMessage({ type: 'step', dt: deltaTime, now: currentTime });
        } catch {}
      }

      // Update FPS counter
      fpsCounterRef.current++;
      if (fpsTimeRef.current === 0) {
        fpsTimeRef.current = currentTime;
      }
      if (currentTime - fpsTimeRef.current >= 1000) {
        const fps = Math.round((fpsCounterRef.current * 1000) / (currentTime - fpsTimeRef.current));
        fpsTimeRef.current = currentTime;
        fpsCounterRef.current = 0;
        
        const fpsVal = fps;
        avgFpsRef.current = avgFpsRef.current * 0.8 + fps * 0.2;
        setPerformanceMetrics({
          renderTime: deltaTime,
          nodeCount: processedDataRef.current.nodes.length,
          edgeCount: processedDataRef.current.relations.length,
          fps: fpsVal
        });
      }

      // Clear canvas with a visible background for debugging
      gl.clearColor(0.2, 0.2, 0.4, 1.0); // Dark blue background
      gl.clear(gl.COLOR_BUFFER_BIT);
      let drawCalls = 0;

      // Growth factor for stop-motion-like branching when commit changes
      const hiId = highlightNodeIdRef.current ? String(highlightNodeIdRef.current) : undefined;
      const hoverEdgeId = (hoverIdRef as any)?.current ? String((hoverIdRef as any).current) : undefined;
      const focusEdgeId = hoverEdgeId || hiId;
      const growT = (() => {
        const start = growthStartRef.current || currentTime;
        const t = Math.min(1, (currentTime - start) / 600);
        return isFinite(t) ? t : 1;
      })();

      // Physics step (CPU, sampled; keeps structure organic without blocking). Skipped when worker is active.
      try {
        if (!workerActiveRef.current) {
          const sim = simRef.current;
          const data = processedDataRef.current;
          if (sim && data.nodes && data.nodes.length === sim.lastSize) {
            const fx = new Float32Array(sim.lastSize);
            const fy = new Float32Array(sim.lastSize);
            const nodes = data.nodes;
            const edges = data.relations || [];
            const dt = Math.min(0.033, deltaTime / 1000);
            const kSpring = 0.003 * (0.7 + settingsRef.current.qualityLevel * 0.6);
            const kAnchor = 0.0;
            const damp = 0.85 + settingsRef.current.qualityLevel * 0.1;
            const step = edges.length > 6000 ? (settingsRef.current.qualityLevel > 0.66 ? 1 : 2) : 1;
            for (let i = 0; i < edges.length; i += step) {
              const e = edges[i];
              const aId = String((e as any).source ?? (e as any).from);
              const bId = String((e as any).target ?? (e as any).to);
              const a = sim.idx.get(aId); const b = sim.idx.get(bId);
              if (a === undefined || b === undefined) continue;
              const dx = sim.posX[b] - sim.posX[a];
              const dy = sim.posY[b] - sim.posY[a];
              const dist = Math.hypot(dx, dy) + 1e-3;
              const type = (e as any).type || (e as any).originalType;
              const rest = type === 'chain' ? 64 : 48;
              const f = kSpring * (dist - rest);
              const fxv = (dx / dist) * f; const fyv = (dy / dist) * f;
              fx[a] += fxv; fy[a] += fyv; fx[b] -= fxv; fy[b] -= fyv;
            }
            const base = (layoutPosRef.current as any as Map<string, {x:number;y:number}>);
            for (let i = 0; i < nodes.length; i++) {
              const id = String(nodes[i].id);
              const p = base.get(id);
              if (!p) continue;
              fx[i] += (p.x - sim.posX[i]) * kAnchor;
              fy[i] += (p.y - sim.posY[i]) * kAnchor;
            }
            const N = nodes.length;
            const pairsBase = Math.min(300, N * 2);
            const pairs = Math.round(pairsBase * (0.5 + settingsRef.current.qualityLevel));
            const kRep = 1200.0;
            for (let n = 0; n < pairs; n++) {
              const i = (Math.random() * N) | 0;
              const j = (Math.random() * N) | 0;
              if (i === j) continue;
              const dx = sim.posX[j] - sim.posX[i];
              const dy = sim.posY[j] - sim.posY[i];
              const d2 = dx*dx + dy*dy + 25.0;
              const inv = 1.0 / d2; const rep = kRep * inv;
              const fxv = dx * rep; const fyv = dy * rep;
              fx[i] -= fxv; fy[i] -= fyv; fx[j] += fxv; fy[j] += fyv;
            }
            for (let i = 0; i < nodes.length; i++) {
              sim.velX[i] = (sim.velX[i] + fx[i]) * damp;
              sim.velY[i] = (sim.velY[i] + fy[i]) * damp;
              sim.posX[i] += sim.velX[i] * dt * 60.0;
              sim.posY[i] += sim.velY[i] * dt * 60.0;
              nodes[i].x = sim.posX[i];
              nodes[i].y = sim.posY[i];
            }
          }
        }
      } catch {}

      // Store draw call estimate for metrics panel
      lastDrawCallsRef.current = drawCalls;

      // Auto-fit camera to organism while not dragging
      try {
        if (settingsRef.current.autoFit && !draggingRef.current) {
          const data = processedDataRef.current;
          const nodes = data.nodes || [];
          if (nodes.length > 0) {
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            for (let i = 0; i < nodes.length; i++) {
              const x = nodes[i].x as number; const y = nodes[i].y as number;
              if (!isFinite(x) || !isFinite(y)) continue;
              if (x < minX) minX = x; if (x > maxX) maxX = x;
              if (y < minY) minY = y; if (y > maxY) maxY = y;
            }
            if (isFinite(minX) && isFinite(maxX)) {
              const W = gl.drawingBufferWidth, H = gl.drawingBufferHeight;
              const pad = 1.15; // padding factor
              const bw = Math.max(50, (maxX - minX));
              const bh = Math.max(50, (maxY - minY));
              const sx = W / (bw * pad);
              const sy = H / (bh * pad);
              const targetZoom = Math.max(0.2, Math.min(3.5, Math.min(sx, sy)));
              const cx = (minX + maxX) * 0.5; const cy = (minY + maxY) * 0.5;
              // Smoothly follow (lerp)
              zoomRef.current = zoomRef.current * 0.92 + targetZoom * 0.08;
              panRef.current.x = panRef.current.x * 0.90 + ((W*0.5/zoomRef.current) - cx) * 0.10;
              panRef.current.y = panRef.current.y * 0.90 + ((H*0.5/zoomRef.current) - cy) * 0.10;
            }
          }
        }
      } catch {}

      // LoD auto-tuning factors (based on avg FPS)
      const fpsNow = avgFpsRef.current || 60;
      const edgeSampleStep = fpsNow < 40 ? 3 : (fpsNow < 52 ? 2 : 1);
      // reserved for future size/alpha scaling
      // const lodFactor = fpsNow < 40 ? 0.55 : (fpsNow < 55 ? 0.75 : 1.0);

      // Draw edges (skip on very far zoom for clarity)
      if (processedDataRef.current.relations.length > 0) {
        const zoomNow = zoomRef.current;
        // FPS-aware LoD threshold for edges
        const fpsNow = (avgFpsRef.current || 60);
        let lodZoom = 0.35;
        if (fpsNow < 50) lodZoom *= 1.35; // stricter when fps drops
        if (fpsNow < 40) lodZoom *= 1.6;
        if (fpsNow > 58) lodZoom *= 0.9; // relax slightly when very smooth
        if (zoomNow < lodZoom && !settingsRef.current.alwaysShowEdges) {
          // Far out: draw only the commit chain as a spine
          const nodeIndex = new Map<string, { x: number; y: number }>();
          for (const n of processedDataRef.current.nodes) {
            if (n && n.id !== undefined) nodeIndex.set(String(n.id), { x: Number(n.x) || 0, y: Number(n.y) || 0 });
          }
          const edges = processedDataRef.current.relations.filter((e:any)=> (e.type||e.originalType)==='chain');
          const positions: number[] = [];
          const colors: number[] = [];
          for (let i = 0; i < edges.length; i++) {
            const e = edges[i];
            const fromId = String(e.source ?? e.from);
            const toId = String(e.target ?? e.to);
            const a = nodeIndex.get(fromId); const b = nodeIndex.get(toId);
            if (!a || !b) continue;
            positions.push(a.x, a.y, b.x, b.y);
            const c: [number,number,number] = [0.80, 0.64, 0.98];
            colors.push(...c, ...c);
          }
          if (positions.length > 0) {
            gl.useProgram(edgeProgram);
            gl.bindVertexArray(edgeVao);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgePositionBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);
            const ep = gl.getAttribLocation(edgeProgram, 'a_position');
            gl.enableVertexAttribArray(ep);
            gl.vertexAttribPointer(ep, 2, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgeColorBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
            const ec = gl.getAttribLocation(edgeProgram, 'a_color');
            gl.enableVertexAttribArray(ec);
            gl.vertexAttribPointer(ec, 3, gl.FLOAT, false, 0, 0);
            const resU = gl.getUniformLocation(edgeProgram, 'u_resolution');
            const zoomU = gl.getUniformLocation(edgeProgram, 'u_zoom');
            const panU = gl.getUniformLocation(edgeProgram, 'u_pan');
            const alphaU = gl.getUniformLocation(edgeProgram, 'u_alpha');
            gl.uniform2f(resU, gl.drawingBufferWidth, gl.drawingBufferHeight);
            gl.uniform1f(zoomU, zoomNow);
            gl.uniform2f(panU, panRef.current.x, panRef.current.y);
          // Dynamic alpha scaled by observed FPS (keep clarity when slow by dimming edges)
          const fpsScale = Math.max(0.6, Math.min(1.2, (avgFpsRef.current || 60) / 60));
          const baseAlpha = Math.min(0.85, 0.25 + zoomNow * 0.7) * edgeEmphasis * fpsScale;
            gl.uniform1f(alphaU, baseAlpha);
            gl.drawArrays(gl.LINES, 0, positions.length / 2);
            drawCalls += 1;
          }
        } else {
          // Use current simulated positions for drawing
          const nodeIndex = new Map<string, { x: number; y: number }>();
          const nodeById = new Map<string, any>();
          for (const n of processedDataRef.current.nodes) {
            if (n && n.id !== undefined) {
              nodeIndex.set(String(n.id), { x: Number(n.x) || 0, y: Number(n.y) || 0 });
              nodeById.set(String(n.id), n);
            }
          }
          // Build edge quads (two vertices per endpoint times 2 sides)
          const edges = processedDataRef.current.relations;
          const posFocus: number[] = [];
          const colFocus: number[] = [];
          const dirFocus: number[] = [];
          const metaFocus: number[] = [];
          const posOther: number[] = [];
          const colOther: number[] = [];
          const dirOther: number[] = [];
          const metaOther: number[] = [];
          const hi = focusEdgeId;
          const strideOther = fpsNow < 40 ? 4 : (fpsNow < 50 ? 2 : 1);
          for (let i = 0; i < edges.length; i++) {
            const e = edges[i];
            const fromId = String(e.source ?? e.from);
            const toId = String(e.target ?? e.to);
            let a = nodeIndex.get(fromId);
            let b = nodeIndex.get(toId);
            if (!a || !b) continue;
            // If growth animation and this edge is the highlighted commit's touch, move far endpoint
            const type = (e as any).type || (e as any).originalType;
            if (hi && type === 'touch') {
              // Prefer current commit simulated position
              let cpos = nodeIndex.get(hi);
              if (!cpos) cpos = commitPosRef.current.get(hi);
              if (cpos) {
                if (fromId === hi) {
                const base = (layoutPosRef.current as any as Map<string, {x:number;y:number}>).get(toId) || nodeIndex.get(toId)!;
                  b = { x: cpos.x + (base.x - cpos.x) * growT, y: cpos.y + (base.y - cpos.y) * growT };
                } else if (toId === hi) {
                const base = (layoutPosRef.current as any as Map<string, {x:number;y:number}>).get(fromId) || nodeIndex.get(fromId)!;
                  a = { x: cpos.x + (base.x - cpos.x) * growT, y: cpos.y + (base.y - cpos.y) * growT };
                }
              }
            }
            // If focus mode: de-emphasize edges not touching the highlighted commit
            const connectedToHighlight = hi && (fromId === hi || toId === hi);
            const isOtherHidden = (settingsRef.current.focusMode && hi && !connectedToHighlight && !settingsRef.current.lightEdges);
            if (isOtherHidden) continue;
            if (!connectedToHighlight && strideOther > 1 && (i % strideOther) !== 0) continue;
            const isChain = (e.type === 'chain');
            // Color chain edges constant; touch edges inherit file color
            let base: [number,number,number] = isChain ? [0.80, 0.64, 0.98] : [0.29,0.33,0.40];
            if (!isChain) {
              const fileNode = nodeById.get(toId) || nodeById.get(fromId);
              if (fileNode && !(fileNode.originalType === 'GitCommit' || fileNode.type === 'commit')) {
                base = colorForNode(fileNode);
              }
            }
            const alphaBoost = connectedToHighlight ? 0.35 : (focusMode && hi ? -0.25 : 0.0);
            const c: [number, number, number] = [
              Math.min(1, base[0] + alphaBoost),
              Math.min(1, base[1] + alphaBoost),
              Math.min(1, base[2] + alphaBoost)
            ];
            // Curvature: quadratic control point seeded by id pair
            const key = fromId < toId ? fromId + '|' + toId : toId + '|' + fromId;
            const h = hashIdx(key);
            const s = ((h % 1000) / 1000) * 2 - 1; // [-1,1]
            const dx0 = b.x - a.x; const dy0 = b.y - a.y;
            const len0 = Math.max(1e-3, Math.hypot(dx0, dy0));
            const ux0 = dx0 / len0; const uy0 = dy0 / len0;
            const nx0 = -uy0, ny0 = ux0;
            const bend = (12 + Math.min(28, len0 * 0.12)) * s; // scaled by length
            const cxp = (a.x + b.x) * 0.5 + nx0 * bend;
            const cyp = (a.y + b.y) * 0.5 + ny0 * bend;
            const segments = Math.max(1, Math.min(6, Math.round((len0 / 100) * (0.6 + settingsRef.current.qualityLevel) + 1)));
            const pushQuad = (P: number[], C: number[], D: number[], M: number[], ax: number, ay: number, bx: number, by: number) => {
              const dx = bx - ax; const dy = by - ay;
              const len = Math.max(1e-3, Math.hypot(dx, dy));
              const ux = dx / len; const uy = dy / len;
              const ax_l = -1, ax_r = +1, bx_l = -1, bx_r = +1;
              // corners: A_left, A_right, B_left, B_right
              const pushVert = (x: number, y: number, side: number) => {
                P.push(x, y);
                C.push(...c);
                D.push(ux, uy);
                M.push(len, side);
              };
              // tri 1: A_l, A_r, B_l
              pushVert(ax, ay, ax_l);
              pushVert(ax, ay, ax_r);
              pushVert(bx, by, bx_l);
              // tri 2: A_r, B_r, B_l
              pushVert(ax, ay, ax_r);
              pushVert(bx, by, bx_r);
              pushVert(bx, by, bx_l);
            };
            let prevx = a.x, prevy = a.y;
            for (let sidx = 1; sidx <= segments; sidx++) {
              const t0 = (sidx - 1) / segments;
              const t1 = sidx / segments;
              const qx0 = (1 - t0) * (1 - t0) * a.x + 2 * (1 - t0) * t0 * cxp + t0 * t0 * b.x;
              const qy0 = (1 - t0) * (1 - t0) * a.y + 2 * (1 - t0) * t0 * cyp + t0 * t0 * b.y;
              const qx1 = (1 - t1) * (1 - t1) * a.x + 2 * (1 - t1) * t1 * cxp + t1 * t1 * b.x;
              const qy1 = (1 - t1) * (1 - t1) * a.y + 2 * (1 - t1) * t1 * cyp + t1 * t1 * b.y;
              if (connectedToHighlight) pushQuad(posFocus, colFocus, dirFocus, metaFocus, qx0, qy0, qx1, qy1);
              else if ((i % edgeSampleStep) === 0) pushQuad(posOther, colOther, dirOther, metaOther, qx0, qy0, qx1, qy1);
              prevx = qx1; prevy = qy1;
            }
          }
          const drawBatch = (positions: number[], colors: number[], dirs: number[], metas: number[], alpha: number, widthPx: number) => {
            gl.useProgram(edgeProgram);
            gl.bindVertexArray(edgeVao);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgePositionBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);
            const ep = gl.getAttribLocation(edgeProgram, 'a_position');
            gl.enableVertexAttribArray(ep);
            gl.vertexAttribPointer(ep, 2, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgeColorBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
            const ec = gl.getAttribLocation(edgeProgram, 'a_color');
            gl.enableVertexAttribArray(ec);
            gl.vertexAttribPointer(ec, 3, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgeDirBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(dirs), gl.DYNAMIC_DRAW);
            const ed = gl.getAttribLocation(edgeProgram, 'a_dir');
            gl.enableVertexAttribArray(ed);
            gl.vertexAttribPointer(ed, 2, gl.FLOAT, false, 0, 0);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgeMetaBuffer!);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(metas), gl.DYNAMIC_DRAW);
            const el = gl.getAttribLocation(edgeProgram, 'a_len');
            const es = gl.getAttribLocation(edgeProgram, 'a_side');
            gl.enableVertexAttribArray(el);
            gl.vertexAttribPointer(el, 1, gl.FLOAT, false, 8, 0);
            gl.enableVertexAttribArray(es);
            gl.vertexAttribPointer(es, 1, gl.FLOAT, false, 8, 4);
            const resU = gl.getUniformLocation(edgeProgram, 'u_resolution');
            const zoomU = gl.getUniformLocation(edgeProgram, 'u_zoom');
            const panU = gl.getUniformLocation(edgeProgram, 'u_pan');
            const alphaU = gl.getUniformLocation(edgeProgram, 'u_alpha');
            const widthU = gl.getUniformLocation(edgeProgram, 'u_width');
            gl.uniform2f(resU, gl.drawingBufferWidth, gl.drawingBufferHeight);
            gl.uniform1f(zoomU, zoomNow);
            gl.uniform2f(panU, panRef.current.x, panRef.current.y);
            gl.uniform1f(alphaU, alpha);
            gl.uniform1f(widthU, widthPx);
            gl.drawArrays(gl.TRIANGLES, 0, positions.length / 2);
            drawCalls += 1;
          };
          const fpsScale2 = Math.max(0.6, Math.min(1.2, (avgFpsRef.current || 60) / 60));
          const baseAlpha = Math.min(0.9, 0.25 + zoomNow * 0.7) * edgeEmphasis * fpsScale2;
          const widthBase = 0.8 + 1.2 * Math.max(0, Math.min(1, edgeEmphasis));
          const widthFocus = widthBase * 1.35;
          if (posOther.length > 0) drawBatch(posOther, colOther, dirOther, metaOther, Math.max(0.05, baseAlpha * 0.6), widthBase);
          if (posFocus.length > 0) drawBatch(posFocus, colFocus, dirFocus, metaFocus, Math.min(1.0, baseAlpha * 1.25), widthFocus);
        }
      }

      // Render nodes with CUDA-like parallel processing
      gl.bindVertexArray(vao);
      const nodesToRender = processedDataRef.current.nodes;
      renderNodes(gl, program, nodesToRender, positionBuffer!, colorBuffer!, sizeBuffer!, zoomRef, panRef, hiId, growT);
      drawCalls += 1;

      // Continue animation loop
      animationFrameRef.current = requestAnimationFrame(render);

      // 2D overlay labels and rings for readability (throttled)
      try {
        const ctx = lctx;
        const W = width; const H = height;
        // Throttle overlay updates to ~12 fps unless zoom/commit changed
        const overlayBudgetMs = 80;
        (render as any)._overlayLast = (render as any)._overlayLast ?? 0;
        (render as any)._lastZoom = (render as any)._lastZoom ?? 0;
        const needUpdate = (currentTime - (render as any)._overlayLast) > overlayBudgetMs || Math.abs((render as any)._lastZoom - zoomRef.current) > 0.05;
        if (!needUpdate) {
          animationFrameRef.current = requestAnimationFrame(render);
          return;
        }
        (render as any)._overlayLast = currentTime;
        (render as any)._lastZoom = zoomRef.current;
        ctx.clearRect(0, 0, W, H);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const zoom = zoomRef.current;
        const pan = panRef.current;
        const showLabels = zoom >= (settingsRef.current.labelThreshold ?? 0.85); // label threshold
        const nodes = processedDataRef.current.nodes;
        const cursor = (cursorRef as any).current || { x: -1e9, y: -1e9 };

        // Folder concave hulls (folder mode only)
        if (colorMode === 'folder' && nodes && nodes.length > 0) {
          const groups = new Map<string, Array<{x:number;y:number}>>();
          for (let i = 0; i < nodes.length; i++) {
            const n = nodes[i];
            const isCommit = (n.originalType === 'GitCommit' || n.type === 'commit');
            if (isCommit) continue;
            const x = (Number(n.x) + pan.x) * zoom; const y = (Number(n.y) + pan.y) * zoom;
            if (x < -40 || y < -40 || x > W + 40 || y > H + 40) continue;
            const f = String(n.folderPath || 'files');
            if (!groups.has(f)) groups.set(f, []);
            groups.get(f)!.push({ x, y });
          }
          const drawBlob = (pts: Array<{x:number;y:number}>, color: [number,number,number]) => {
            if (pts.length < 3) return;
            let cx = 0, cy = 0; for (const p of pts){ cx += p.x; cy += p.y; } cx/=pts.length; cy/=pts.length;
            const bins = 28;
            const rays: Array<{x:number;y:number;r:number}> = new Array(bins).fill(0).map(()=>({x:cx,y:cy,r:0}));
            for (const p of pts) {
              const a = Math.atan2(p.y - cy, p.x - cx);
              const u = (a < 0 ? a + Math.PI*2 : a) / (Math.PI*2);
              const bi = Math.min(bins-1, Math.max(0, Math.floor(u * bins)));
              const r = Math.hypot(p.x - cx, p.y - cy);
              if (r > rays[bi].r) { rays[bi].r = r; rays[bi].x = p.x; rays[bi].y = p.y; }
            }
            ctx.beginPath();
            for (let i=0;i<bins;i++){
              const cur = rays[i]; const nxt = rays[(i+1)%bins];
              if (i===0) ctx.moveTo(cur.x, cur.y);
              const mx = (cur.x + nxt.x) * 0.5; const my = (cur.y + nxt.y) * 0.5;
              ctx.quadraticCurveTo(cur.x, cur.y, mx, my);
            }
            const fill = `rgba(${Math.round(color[0]*255)},${Math.round(color[1]*255)},${Math.round(color[2]*255)},0.08)`;
            const stroke = `rgba(${Math.round(color[0]*255)},${Math.round(color[1]*255)},${Math.round(color[2]*255)},0.18)`;
            ctx.fillStyle = fill; ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.fill(); ctx.stroke();
          };
          for (const [folder, pts] of groups.entries()){
            const rgb = folderPalette[hashIdx(folder) % folderPalette.length];
            drawBlob(pts, rgb);
          }
        }

        // Hover detection
        let hovered: any = undefined; let hoveredDist = 1e9;
        for (let i = 0; i < nodes.length; i++) {
          const n = nodes[i];
          const isCommit = (n.originalType === 'GitCommit' || n.type === 'commit');
          const size = isCommit ? Math.max(10, Math.min(26, 9 + Math.sqrt(n.importance || 1) * 1.6)) : Math.max(6, Math.min(18, 5 + Math.sqrt(n.importance || 1) * 1.1));
          const x = (Number(n.x) + pan.x) * zoom; const y = (Number(n.y) + pan.y) * zoom;
          const dx = x - cursor.x; const dy = y - cursor.y; const d = Math.hypot(dx, dy);
          const hitR = Math.max(12, size * 0.65);
          if (d < hitR && d < hoveredDist) { hovered = n; hoveredDist = d; }
        }
        (hoverIdRef as any).current = hovered ? String(hovered.id) : undefined;

        // Tooltip
        if (hovered) {
          const isCommit = (hovered.originalType === 'GitCommit' || hovered.type === 'commit');
          const title = isCommit ? String(hovered.id).slice(0, 7) : String(hovered.label || hovered.id).split('/').pop()?.slice(0, 42) || String(hovered.id).slice(0, 42);
          const detail = isCommit ? `files: ${hovered.filesTouched ?? 0}` : `touches: ${hovered.touchCount ?? 0}`;
          const text = `${title}  —  ${detail}`;
          ctx.font = `12px Inter, system-ui, sans-serif`;
          const tw = Math.min(260, Math.max(60, ctx.measureText(text).width + 16));
          const th = 22; const pad = 8;
          let tx = cursor.x + 14; let ty = cursor.y - 10 - th;
          if (tx + tw > W - 6) tx = W - tw - 6;
          if (ty < 6) ty = cursor.y + 14;
          ctx.fillStyle = 'rgba(0,0,0,0.65)'; ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.rect(tx, ty, tw, th); ctx.fill(); ctx.stroke();
          ctx.fillStyle = 'rgba(255,255,255,0.95)';
          ctx.fillText(text, tx + pad, ty + th/2 + 1);
        }
      } catch {}
    };

    // Start the render loop
    lastFrameTimeRef.current = performance.now();
    fpsTimeRef.current = lastFrameTimeRef.current;
    fpsCounterRef.current = 0;
    animationFrameRef.current = requestAnimationFrame(render);
    
    console.log('WebGLEvolutionGraph: CUDA-accelerated rendering initialized');
    console.log('WebGLEvolutionGraph: Render loop started');

    // Handle context loss gracefully
    const onContextLost = (ev: Event) => {
      ev.preventDefault();
      console.warn('WebGL context lost');
      cleanupGL();
    };
    const onContextRestored = () => {
      console.info('WebGL context restored');
      // Reinitialize on restore
      initializeCUDARendering(canvas, gl).catch(console.error);
    };
    canvas.addEventListener('webglcontextlost', onContextLost as any, false);
    canvas.addEventListener('webglcontextrestored', onContextRestored as any, false);

    // Cleanup listeners when we rebuild
    return () => {
      canvas.removeEventListener('wheel', onWheel as any);
      canvas.removeEventListener('mousedown', onDown as any);
      window.removeEventListener('mousemove', onMove as any);
      window.removeEventListener('mouseup', onUp as any);
      canvas.removeEventListener('mousemove', onHoverMove as any);
      canvas.removeEventListener('webglcontextlost', onContextLost as any, false);
      canvas.removeEventListener('webglcontextrestored', onContextRestored as any, false);
    };
  };

  // Offload physics to a Web Worker for larger graphs or higher quality
  useEffect(() => {
    const data = processedDataRef.current;
    const sim = simRef.current;
    if (!data || !sim || !data.nodes?.length) return;

    const shouldUseWorker = () => {
      const count = data.nodes.length;
      const q = settingsRef.current.qualityLevel ?? 0.6;
      return count >= 600 || q >= 0.7;
    };

    // Build compact edges mapped to indices once per data change
    const edges = (data.relations || []).map((e: any) => {
      const aId = String(e.source ?? e.from);
      const bId = String(e.target ?? e.to);
      const ai = sim.idx.get(aId);
      const bi = sim.idx.get(bId);
      if (ai === undefined || bi === undefined) return null;
      const isChain = (e.type === 'chain');
      return { ai, bi, rest: isChain ? 64 : 48 } as { ai: number; bi: number; rest: number };
    }).filter(Boolean) as { ai: number; bi: number; rest: number }[];

    const createPhysicsWorker = () => {
      const src = `
        let posX, posY, velX, velY;
        let edgesAI, edgesBI, edgesRest;
        let N = 0; let quality = 0.6; let lastPost = 0;
        function stepOnce(dt){
          if (!N) return;
          const fx = new Float32Array(N), fy = new Float32Array(N);
          const damp = 0.85 + quality * 0.1;
          const kSpring = 0.003 * (0.7 + quality * 0.6);
          const kRep = 1200.0;
          const E = edgesAI.length; const skip = E > 6000 ? (quality > 0.66 ? 1 : 2) : 1;
          for (let i = 0; i < E; i += skip){
            const a = edgesAI[i]|0, b = edgesBI[i]|0; const rest = edgesRest[i]||48;
            const dx = posX[b] - posX[a]; const dy = posY[b] - posY[a];
            const dist = Math.hypot(dx, dy) + 1e-3; const f = kSpring * (dist - rest);
            const fxv = (dx / dist) * f; const fyv = (dy / dist) * f;
            fx[a] += fxv; fy[a] += fyv; fx[b] -= fxv; fy[b] -= fyv;
          }
          const pairsBase = Math.min(300, N * 2); const pairs = Math.round(pairsBase * (0.5 + quality));
          for (let n=0;n<pairs;n++){
            const i = (Math.random()*N)|0, j = (Math.random()*N)|0; if (i===j) continue;
            const dx = posX[j] - posX[i], dy = posY[j] - posY[i];
            const d2 = dx*dx + dy*dy + 25.0; const inv = 1.0/d2; const rep = 1200.0 * inv;
            const fxv = dx * rep, fyv = dy * rep;
            fx[i] -= fxv; fy[i] -= fyv; fx[j] += fxv; fy[j] += fyv;
          }
          for (let i=0;i<N;i++){
            velX[i] = (velX[i] + fx[i]) * damp;
            velY[i] = (velY[i] + fy[i]) * damp;
            posX[i] += velX[i] * dt * 60.0;
            posY[i] += velY[i] * dt * 60.0;
          }
        }
        onmessage = (e)=>{
          const m = e.data || {};
          if (m.type==='init'){
            posX = new Float32Array(m.posX); posY = new Float32Array(m.posY);
            velX = new Float32Array(m.velX); velY = new Float32Array(m.velY);
            edgesAI = new Uint32Array(m.edgesAI); edgesBI = new Uint32Array(m.edgesBI); edgesRest = new Float32Array(m.edgesRest);
            N = posX.length; quality = m.quality ?? 0.6; postMessage({type:'ready'});
          } else if (m.type==='settings'){
            quality = m.quality ?? quality;
          } else if (m.type==='step'){
            const now = m.now || (performance && performance.now ? performance.now() : Date.now());
            const dt = Math.min(0.033, (m.dt||16)/1000);
            stepOnce(dt);
            if ((now - lastPost) > (quality > 0.7 ? 80 : 140)){
              lastPost = now;
              const outX = posX.slice(0), outY = posY.slice(0);
              postMessage({ type: 'positions', posX: outX.buffer, posY: outY.buffer }, [outX.buffer, outY.buffer]);
            }
          }
        };
      `;
      const blob = new Blob([src], { type: 'text/javascript' });
      return new Worker(URL.createObjectURL(blob));
    };

    const startWorker = () => {
      if (!shouldUseWorker()) {
        try { physicsWorkerRef.current?.terminate(); } catch {}
        physicsWorkerRef.current = null;
        workerActiveRef.current = false;
        return;
      }
      try { physicsWorkerRef.current?.terminate(); } catch {}
      const w = createPhysicsWorker();
      physicsWorkerRef.current = w;
      workerActiveRef.current = true;
      const E = edges.length;
      const ai = new Uint32Array(E), bi = new Uint32Array(E); const rest = new Float32Array(E);
      for (let i=0;i<E;i++){ ai[i] = edges[i].ai; bi[i] = edges[i].bi; rest[i] = edges[i].rest; }
      w.postMessage({
        type: 'init',
        posX: sim.posX.buffer, posY: sim.posY.buffer,
        velX: sim.velX.buffer, velY: sim.velY.buffer,
        edgesAI: ai.buffer, edgesBI: bi.buffer, edgesRest: rest.buffer,
        quality: settingsRef.current.qualityLevel ?? 0.6
      }, [sim.posX.buffer, sim.posY.buffer, sim.velX.buffer, sim.velY.buffer, ai.buffer, bi.buffer, rest.buffer]);
      w.onmessage = (ev: any) => {
        const msg = ev.data || {};
        if (msg.type === 'positions'){
          try {
            const px = new Float32Array(msg.posX); const py = new Float32Array(msg.posY);
            if (simRef.current && px.length === simRef.current.lastSize){
              simRef.current.posX = px; simRef.current.posY = py;
              const nodes = processedDataRef.current.nodes;
              for (let i=0;i<nodes.length;i++){ nodes[i].x = px[i]; nodes[i].y = py[i]; }
            }
          } catch {}
        }
      };
    };

    startWorker();
    return () => {
      try { physicsWorkerRef.current?.terminate(); } catch {}
      physicsWorkerRef.current = null;
      workerActiveRef.current = false;
    };
  }, [processedData.nodes?.length, processedData.relations?.length, qualityLevel]);
  // Shared color functions for both nodes and edges
  const commitColor: [number, number, number] = [0.74, 0.58, 0.98];
  const folderPalette: Array<[number, number, number]> = [
    [0.24, 0.72, 0.55], // teal
    [0.20, 0.63, 0.96], // blue
    [0.34, 0.86, 0.56], // green
    [0.99, 0.77, 0.36], // orange
    [0.93, 0.49, 0.72], // pink
    [0.52, 0.53, 0.98], // indigo
  ];
  const hashIdx = (s: string) => { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); };
  const interpolateStops = (stops: [number,number,number][], t: number) => {
    if (stops.length === 0) return [1,1,1] as [number,number,number];
    if (stops.length === 1) return stops[0];
    const u = Math.max(0, Math.min(1, t));
    const pos = u * (stops.length - 1);
    const i = Math.floor(pos);
    const f = pos - i;
    const a = stops[i]; const b = stops[Math.min(stops.length-1,i+1)];
    return [a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f] as [number,number,number];
  };
  const turbo: [number,number,number][] = [
    [0.19,0.07,0.23],[0.19,0.17,0.55],[0.13,0.37,0.88],[0.20,0.63,0.96],[0.29,0.80,0.64],[0.73,0.93,0.27],[1.00,0.78,0.00],[0.87,0.25,0.00]
  ];
  const plasma: [number,number,number][] = [
    [0.05,0.03,0.53],[0.28,0.00,0.70],[0.50,0.00,0.66],[0.70,0.10,0.48],[0.87,0.27,0.30],[0.98,0.49,0.12],[0.96,0.73,0.01]
  ];
  const fileTypeColor = (n: any): [number,number,number] => {
    const path: string = n.path || n.id || '';
    const lower = String(path).toLowerCase();
    const isDoc = n.originalType === 'Document' || /\.(md|rst|txt|doc|docx|pdf)$/.test(lower);
    const isConfig = /\.(ya?ml|json|toml|ini|cfg|conf)$/.test(lower);
    if (isDoc) return [0.96,0.62,0.05]; // orange
    if (isConfig) return [0.55,0.36,0.96]; // purple
    return [0.23,0.51,0.96]; // blue for code
  };
  const folderColor = (n: any): [number,number,number] => folderPalette[hashIdx(String(n.folderPath||'files')) % folderPalette.length];
  const activityColor = (n: any): [number,number,number] => {
    const d = touchDomainRef.current; const t = n.touchCount ?? n.degree ?? 0;
    const u = (t - d.min) / (d.max - d.min);
    return interpolateStops(plasma, isFinite(u) ? Math.max(0, Math.min(1, u)) : 0);
  };
  const commitFlowColor = (n: any): [number,number,number] => {
    const idx = commitIndexRef.current.get(String(n.id)) ?? 0;
    const total = Math.max(1, commitIndexRef.current.size-1);
    const t = Math.max(0, Math.min(1, idx/total));
    return interpolateStops(turbo, t);
  };
  const colorForNode = (n: any): [number,number,number] => {
    const isCommit = (n.originalType === 'GitCommit' || n.type === 'commit');
    if (isCommit) {
      return colorMode === 'commit-flow' ? commitFlowColor(n) : commitColor;
    }
    switch (colorMode) {
      case 'type': return fileTypeColor(n);
      case 'activity': return activityColor(n);
      case 'none': return [0.75,0.75,0.75];
      case 'commit-flow':
      case 'folder':
      default: return folderColor(n);
    }
  };

  const renderNodes = (
    gl: WebGL2RenderingContext,
    program: WebGLProgram,
    nodes: any[],
    positionBuffer: WebGLBuffer,
    colorBuffer: WebGLBuffer,
    sizeBuffer: WebGLBuffer,
    zoomRef?: { current: number },
    panRef?: { current: { x: number; y: number } },
    hiId?: string,
    growT?: number
  ) => {
    if (nodes.length === 0) return;

    // Prepare data for GPU (CUDA-like data transfer)
    const positions = new Float32Array(nodes.length * 2);
    const colors = new Float32Array(nodes.length * 3);
    const sizes = new Float32Array(nodes.length);
    const kinds = new Float32Array(nodes.length);

    nodes.forEach((node, i) => {
      // Use provided positions; fallback stays deterministic to avoid flicker
      let nx = (typeof node.x === 'number') ? node.x : (i % 2 === 0 ? (i * 13 % width) : (i * 7 % width));
      let ny = (typeof node.y === 'number') ? node.y : (i % 3 === 0 ? (i * 11 % height) : (i * 5 % height));
      
      // Ensure nodes are positioned within canvas bounds
      nx = Math.max(50, Math.min(width - 50, nx));
      ny = Math.max(50, Math.min(height - 50, ny));

      // Animated growth for files of the current commit
      const idStr = String(node.id);
      if (hiId && growT !== undefined && fileHomeRef.current.get(idStr) === hiId) {
        const cpos = commitPosRef.current.get(hiId);
        const base = (layoutPosRef.current as any as Map<string, {x:number;y:number}>).get(idStr);
        if (cpos && base) {
          nx = cpos.x + (base.x - cpos.x) * Math.max(0, Math.min(1, growT));
          ny = cpos.y + (base.y - cpos.y) * Math.max(0, Math.min(1, growT));
        }
      }
      positions[i * 2] = nx;
      positions[i * 2 + 1] = ny;
      
      // Color by type and folder group with highlight boost
      const isCommit = (node.originalType === 'GitCommit' || node.type === 'commit');
      const isHighlight = !!(highlightNodeIdRef.current && idStr === String(highlightNodeIdRef.current));
      const isHover = !!((hoverIdRef as any)?.current && String((hoverIdRef as any).current) === idStr);
      const isTouched = activeTouchedSetRef.current.has(idStr);
      let baseColor = colorForNode(node);
      const boost = isHighlight || isHover ? 0.55 : isTouched ? 0.25 : 0.0;
      colors[i * 3] = Math.min(1, baseColor[0] + boost);
      colors[i * 3 + 1] = Math.min(1, baseColor[1] + boost);
      colors[i * 3 + 2] = Math.min(1, baseColor[2] + boost);

      const importance = typeof node.importance === 'number' ? node.importance : 1;
      const baseSize = Math.max(3.5, Math.min(24, (isCommit ? 12.5 : 6) + Math.sqrt(importance) * (isCommit ? 2.6 : 1.7)));
      sizes[i] = (isHighlight || isHover) ? baseSize * 1.8 : isTouched ? baseSize * 1.35 : baseSize;
      kinds[i] = isCommit ? 1.0 : 0.0;
    });

    // Upload data to GPU buffers
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.DYNAMIC_DRAW);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, colors, gl.DYNAMIC_DRAW);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, sizeBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, sizes, gl.DYNAMIC_DRAW);
    
    const kindBuffer = glResourcesRef.current.kindBuffer!;
    gl.bindBuffer(gl.ARRAY_BUFFER, kindBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, kinds, gl.DYNAMIC_DRAW);

    // Set up attributes and uniforms
    gl.useProgram(program);
    
    const positionAttribute = gl.getAttribLocation(program, 'a_position');
    const colorAttribute = gl.getAttribLocation(program, 'a_color');
    const sizeAttribute = gl.getAttribLocation(program, 'a_size');
    const kindAttribute = gl.getAttribLocation(program, 'a_kind');
    
    gl.enableVertexAttribArray(positionAttribute);
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.vertexAttribPointer(positionAttribute, 2, gl.FLOAT, false, 0, 0);
    
    gl.enableVertexAttribArray(colorAttribute);
    gl.bindBuffer(gl.ARRAY_BUFFER, colorBuffer);
    gl.vertexAttribPointer(colorAttribute, 3, gl.FLOAT, false, 0, 0);
    
    gl.enableVertexAttribArray(sizeAttribute);
    gl.bindBuffer(gl.ARRAY_BUFFER, sizeBuffer);
    gl.vertexAttribPointer(sizeAttribute, 1, gl.FLOAT, false, 0, 0);

    gl.enableVertexAttribArray(kindAttribute);
    gl.bindBuffer(gl.ARRAY_BUFFER, kindBuffer);
    gl.vertexAttribPointer(kindAttribute, 1, gl.FLOAT, false, 0, 0);

    // Set uniforms
    const resolutionUniform = gl.getUniformLocation(program, 'u_resolution');
    const zoomUniform = gl.getUniformLocation(program, 'u_zoom');
    const panUniform = gl.getUniformLocation(program, 'u_pan');
    
    gl.uniform2f(resolutionUniform, gl.drawingBufferWidth, gl.drawingBufferHeight);
    gl.uniform1f(zoomUniform, zoomRef?.current ?? 1.0);
    const panX = panRef?.current?.x ?? 0;
    const panY = panRef?.current?.y ?? 0;
    gl.uniform2f(panUniform, panX, panY);

    // Render points (CUDA-like parallel execution)
    gl.drawArrays(gl.POINTS, 0, nodes.length);
  };

  // Helper functions for WebGL
  const createShader = (gl: WebGL2RenderingContext, type: number, source: string): WebGLShader => {
    const shader = gl.createShader(type);
    if (!shader) throw new Error('Failed to create shader');
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compilation failed: ${error}`);
    }
    return shader;
  };

  const createProgram = (gl: WebGL2RenderingContext, vertexShader: WebGLShader, fragmentShader: WebGLShader): WebGLProgram => {
    const program = gl.createProgram();
    if (!program) throw new Error('Failed to create program');
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`Program linking failed: ${error}`);
    }
    return program;
  };

  // Cleanup helpers and on unmount
  const cleanupGL = () => {
    // Stop RAF if running
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = undefined;
    }
    try { physicsWorkerRef.current?.terminate(); physicsWorkerRef.current = null; } catch {}
    const res = glResourcesRef.current;
    if (res.gl) {
      const gl = res.gl;
      if (res.positionBuffer) gl.deleteBuffer(res.positionBuffer);
      if (res.colorBuffer) gl.deleteBuffer(res.colorBuffer);
      if (res.sizeBuffer) gl.deleteBuffer(res.sizeBuffer);
      if (res.kindBuffer) gl.deleteBuffer(res.kindBuffer);
      if (res.edgePositionBuffer) gl.deleteBuffer(res.edgePositionBuffer);
      if (res.edgeColorBuffer) gl.deleteBuffer(res.edgeColorBuffer);
      if (res.vao) gl.deleteVertexArray(res.vao);
      if (res.edgeVao) gl.deleteVertexArray(res.edgeVao as any);
      if (res.program) gl.deleteProgram(res.program);
      if (res.edgeProgram) gl.deleteProgram(res.edgeProgram as any);
    }
    glResourcesRef.current = { gl: res.gl, program: null, edgeProgram: null, vao: null, positionBuffer: null, colorBuffer: null, sizeBuffer: null, kindBuffer: null, edgeVao: null, edgePositionBuffer: null, edgeColorBuffer: null, edgeDirBuffer: null, edgeMetaBuffer: null } as any;
  };

  useEffect(() => {
    return () => {
      cleanupGL();
    };
  }, []);

  if (!mounted) {
    return (
      <Box 
        height={height} 
        width={width} 
        borderWidth="1px" 
        borderRadius="md" 
        display="flex" 
        alignItems="center" 
        justifyContent="center"
        bg="gray.50"
      >
        Initializing CUDA-accelerated WebGL renderer...
      </Box>
    );
  }

  return (
    <Box 
      ref={containerRef}
      height={height} 
      width={width} 
      borderWidth="1px" 
      borderRadius="md"
      position="relative"
      overflow="hidden"
      bg={containerBg}
    >
      {/* CUDA-accelerated WebGL Canvas */}
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
      />
      {/* 2D overlay for labels/rings */}
      <canvas
        ref={labelCanvasRef}
        width={width}
        height={height}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none'
        }}
      />
      
      {/* Loading overlay (keeps canvas mounted) */}
      {isLoading && (
        <Box 
          position="absolute"
          inset={0}
          display="flex"
          alignItems="center"
          justifyContent="center"
          bg="blackAlpha.400"
          color={panelText}
          fontSize="sm"
        >
          Loading CUDA-accelerated visualization...
        </Box>
      )}

      {/* Error overlay (keeps canvas mounted) */}
      {error && (
        <Box 
          position="absolute"
          inset={0}
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          bg="red.800"
          color="white"
          p={4}
          textAlign="center"
        >
          <Box fontWeight="bold" mb={2}>CUDA WebGL Rendering Error</Box>
          <Box fontSize="sm">{error}</Box>
          <Box mt={2} fontSize="xs">
            Data available: {data.nodes?.length || 0} nodes, {data.relations?.length || 0} relations
          </Box>
        </Box>
      )}
      
      {/* Performance Metrics Overlay */}
      {performanceMetrics && (
        <Box
          position="absolute"
          top={2}
          right={2}
          bg={panelBg}
          color={panelText}
          p={2}
          borderRadius="md"
          fontSize="xs"
          fontFamily="mono"
        >
          <Box fontWeight="bold" mb={1}>🚀 CUDA Performance</Box>
          <Box>FPS: {performanceMetrics.fps}</Box>
          <Box>Nodes: {performanceMetrics.nodeCount}</Box>
          <Box>Edges: {performanceMetrics.edgeCount}</Box>
          <Box>Render: {performanceMetrics.renderTime.toFixed(1)}ms</Box>
          <Box>Draw calls: {lastDrawCallsRef.current}</Box>
        </Box>
      )}

      {/* Data Processing Info */}
      <Box
        position="absolute"
        bottom={2}
        left={2}
        bg={panelBg}
        color={panelText}
        p={2}
        borderRadius="md"
        fontSize="xs"
        fontFamily="mono"
      >
        <Box fontWeight="bold" mb={1}>⚡ CUDA Acceleration</Box>
        <Box>Mode: {layoutMode}</Box>
        <Box>Edges: {edgeTypes.join(', ')}</Box>
        <Box>Max: {maxEdgesInView}</Box>
        <Box>Optimized: {processedData.nodes.length < data.nodes.length ? 'Yes' : 'No'}</Box>
      </Box>
    </Box>
  );
}
