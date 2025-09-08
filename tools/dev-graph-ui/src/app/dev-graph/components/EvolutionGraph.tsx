'use client';

import { Box } from '@chakra-ui/react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { calculateLoD, filterNodesByLoD, filterEdgesByLoD, reduceLabelComplexity, calculateNodeSize, calculateEdgeWidth, calculateColorIntensity } from '../../../utils/lodReducers';

export type GraphData = { nodes: any[]; relations: any[] };

export function EvolutionGraph({
  data,
  height = 600,
  width = 1000,
  onNodeClick,
  currentTimestamp,
  timeRange,
  enableClustering = false,
  showOnlyViewport = false,
  onViewportChange,
  lightEdges = true,
  labelZoomThreshold = 1.2,
  focusMode = true,
  enablePhysics = false,
  physicsAttraction = 0.02,
  physicsRepulsion = 1200,
  physicsFriction = 0.85,
  layoutMode = 'force',
  edgeTypes = ['TOUCHED','PART_OF','EVOLVES_FROM','REFERENCES','DEPENDS_ON','MENTIONS','CONTAINS_CHUNK','CONTAINS_DOC'],
  maxEdgesInView = 2000,
  layoutSeed,
  focusNodeId,
}: {
  data: GraphData;
  height?: number;
  width?: number;
  onNodeClick?: (node: any) => void;
  currentTimestamp?: string;
  timeRange?: { start: string; end: string };
  enableClustering?: boolean;
  showOnlyViewport?: boolean;
  onViewportChange?: (bounds: { x: number; y: number; width: number; height: number; zoom: number }) => void;
  lightEdges?: boolean;
  labelZoomThreshold?: number;
  focusMode?: boolean;
  enablePhysics?: boolean;
  physicsAttraction?: number;
  physicsRepulsion?: number;
  physicsFriction?: number;
  layoutMode?: 'force' | 'time-radial';
  edgeTypes?: string[];
  maxEdgesInView?: number;
  layoutSeed?: number;
  focusNodeId?: string;
}) {
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Debug logging toggle (set NEXT_PUBLIC_DEV_GRAPH_DEBUG=1 or true)
  const DEBUG = (process?.env?.NEXT_PUBLIC_DEV_GRAPH_DEBUG === '1' || process?.env?.NEXT_PUBLIC_DEV_GRAPH_DEBUG === 'true');
  // Apply client-side layout only up to this many nodes
  const LAYOUT_MAX_NODES = 400;
  const [libraries, setLibraries] = useState<{
    Graph: any;
    Sigma: any;
    louvain: any;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<any | null>(null);
  const hoveredNodeRef = useRef<string | null>(null);
  const neighborSetRef = useRef<Set<string> | null>(null);
  const zoomRef = useRef<number>(1);
  const animRef = useRef<number | null>(null);
  const draggingRef = useRef<Set<string>>(new Set());
  
  // LoD state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [viewportBounds, setViewportBounds] = useState({ x: 0, y: 0, width, height });
  // Allow physics on moderately large graphs (sampling keeps it performant)
  const PHYSICS_NODE_THRESHOLD = 1200;

  useEffect(() => {
    setMounted(true);
  }, []);

  // Load libraries when mounted
  useEffect(() => {
    if (!mounted) return;

    let isMounted = true;
    
    const loadLibraries = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Load libraries sequentially to avoid potential conflicts
        const graphology = await import('graphology');
        const sigma = await import('sigma');
        const louvain = await import('graphology-communities-louvain');
        
        if (!isMounted) return;
        
        // Store libraries in state
        setLibraries({
          Graph: graphology.default,
          Sigma: sigma.default || sigma.Sigma, // Handle different export patterns
          louvain: louvain.default
        });
        
        setIsLoading(false);
      } catch (err) {
        if (!isMounted) return;
        if (DEBUG) console.error('Failed to load graph libraries:', err);
        setError('Failed to load graph visualization libraries');
        setIsLoading(false);
      }
    };

    loadLibraries();
    
    return () => {
      isMounted = false;
    };
  }, [mounted]);

  // Deterministic RNG
  const rng = useMemo(() => {
    let s = typeof layoutSeed === 'number' ? layoutSeed : 42;
    return () => {
      // xorshift32
      s ^= s << 13; s ^= s >>> 17; s ^= s << 5; 
      return ((s >>> 0) / 0xffffffff);
    };
  }, [layoutSeed]);

  // Coordinate cache for reuse across minor filter changes (by node id)
  const coordCacheRef = useRef<Map<string, { x: number; y: number }>>(new Map());

  // Apply LoD filtering
  const lodData = useMemo(() => {
    if (!data.nodes || !data.relations) return data;
    
    const lodConfig = {
      zoomLevel,
      viewportWidth: viewportBounds.width,
      viewportHeight: viewportBounds.height,
      nodeCount: data.nodes.length,
      edgeCount: data.relations.length,
    };
    
    const lod = calculateLoD(lodConfig);
    
    // Filter nodes and edges based on LoD
    const filteredNodes = filterNodesByLoD(data.nodes, lod);
    const filteredEdges = filterEdgesByLoD(data.relations, lod);
    
    // Apply label complexity reduction
    const processedNodes = filteredNodes.map(node => ({
      ...node,
      label: node.label ? reduceLabelComplexity([node.label], zoomLevel)[0] : node.label,
      size: calculateNodeSize(node.size || 5, zoomLevel),
    }));
    
    const processedEdges = filteredEdges.map(edge => ({
      ...edge,
      label: edge.label ? reduceLabelComplexity([edge.label], zoomLevel)[0] : edge.label,
      width: calculateEdgeWidth(edge.width || 1, zoomLevel),
    }));
    
    return {
      nodes: processedNodes,
      relations: processedEdges,
      lod,
    };
  }, [data, zoomLevel, viewportBounds]);

  // Create graph data
  const graph = useMemo(() => {
    if (!mounted || isLoading || error || !libraries) return null;
    
    const { nodes, relations } = lodData;
    
          if (DEBUG) console.log('Creating graph with data:', { 
        nodesCount: nodes?.length || 0, 
        relationsCount: relations?.length || 0,
        layoutMode,
        sampleNode: nodes?.[0],
        sampleNodeCoords: nodes?.[0] ? {
          x: nodes[0].x,
          y: nodes[0].y,
          xType: typeof nodes[0].x,
          yType: typeof nodes[0].y,
          xValid: typeof nodes[0].x === 'number' && !isNaN(nodes[0].x),
          yValid: typeof nodes[0].y === 'number' && !isNaN(nodes[0].y)
        } : null
      });
    
    try {
      const { Graph } = libraries;
      const g = new Graph();
      
      // Add nodes (coordinates reused or derived deterministically)
      for (const n of nodes || []) {
        if (!g.hasNode(n.id)) {
          // Pull from cache first
          let cached = coordCacheRef.current.get(String(n.id));
          let x = typeof n.x === 'number' && isFinite(n.x) ? n.x : (cached?.x ?? NaN);
          let y = typeof n.y === 'number' && isFinite(n.y) ? n.y : (cached?.y ?? NaN);
          // If still missing, generate deterministic pseudo-random coordinates based on id and seed
          if (!isFinite(x) || !isFinite(y)) {
            // Hash id to a stable number, then mix with rng for seed determinism
            const idStr = String(n.id);
            let h = 2166136261;
            for (let i = 0; i < idStr.length; i++) {
              h ^= idStr.charCodeAt(i);
              h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
            }
            // Generate angle and radius deterministically
            const angle = (h % 360) * (Math.PI / 180);
            const radius = 200 + Math.floor(rng() * 300);
            x = Math.cos(angle) * radius;
            y = Math.sin(angle) * radius;
          }
          // Save to cache
          coordCacheRef.current.set(String(n.id), { x, y });
          const size = typeof n.size === 'number' && isFinite(n.size) && n.size > 0 ? n.size : 1;
          
          if (!isFinite(x) || !isFinite(y)) {
            if (DEBUG) console.error(`Skipping node ${n.id} with invalid coordinates: x=${n.x}, y=${n.y}`);
            continue;
          }
          
          // Derive a stable type for coloring
          const inferredType = (() => {
            if (n.type) return n.type;
            const labels = Array.isArray((n as any).labels) ? (n as any).labels as string[] : [];
            if (labels.includes('File')) return 'File';
            if (labels.includes('GitCommit') || labels.includes('Commit')) return 'GitCommit';
            if (labels.includes('Requirement')) return 'Requirement';
            if (labels.includes('Sprint')) return 'Sprint';
            if (labels.includes('Document') || labels.includes('Doc')) return 'Document';
            return 'Unknown';
          })();

          // Create node attributes, ensuring no conflicting properties
          // Base color by type (used temporarily; final color set after degree mapping)
          const nodeColor =
            inferredType === 'Requirement' ? '#2b8a3e' :
            inferredType === 'File' ? '#1c7ed6' :
            inferredType === 'Sprint' ? '#e67700' :
            inferredType === 'GitCommit' ? '#9f7aea' : '#888';
            
          const nodeAttrs = {
            label: String(n.id),
            // Set the node type for Sigma.js rendering
            type: 'circle',
            // Store original type in a custom property
            originalType: inferredType,
            color: nodeColor,
            originalColor: nodeColor, // Store original color for focus mode restoration
            x,
            y,
            size,
            // Include other properties but exclude problematic ones
            ...Object.fromEntries(
              Object.entries(n).filter(([key]) => 
                !['x', 'y', 'size', 'type', 'nodeType'].includes(key)
              )
            )
          };
          
          g.addNode(n.id, nodeAttrs);
        }
      }
      
      // Add edges (filter by selected types)
      for (const e of relations || []) {
        if (Array.isArray(edgeTypes) && edgeTypes.length > 0 && !edgeTypes.includes(e.type)) continue;
        if (!g.hasNode(e.from) || !g.hasNode(e.to)) continue;
        
        // Create edge attributes, ensuring no conflicting properties
        const edgeColor = 
          e.type === 'TOUCHED' ? '#ff6b6b' :
          e.type === 'PART_OF' ? '#888' :
          e.type === 'EVOLVES_FROM' ? '#2b8a3e' :
          e.type === 'REFERENCES' ? '#1c7ed6' :
          e.type === 'DEPENDS_ON' ? '#e67700' :
          e.type === 'MENTIONS' ? '#9c88ff' :
          e.type === 'CONTAINS_CHUNK' ? '#51cf66' :
          e.type === 'CONTAINS_DOC' ? '#ffd43b' : '#999';
          
        const edgeAttrs = {
          label: e.type,
          // Set the edge type for Sigma.js rendering
          type: 'line',
          // Store original type in a custom property
          originalType: e.type,
          color: edgeColor,
          originalColor: edgeColor, // Store original color for restoration
          size: 0.8, // Default edge size
          timestamp: e.timestamp,
          // Include other properties but exclude problematic ones
          ...Object.fromEntries(
            Object.entries(e).filter(([key]) => 
              !['type', 'from', 'to'].includes(key)
            )
          )
        };
        
        // Cap total edges progressively
        if (typeof maxEdgesInView === 'number' && g.size >= maxEdgesInView) break;
        try { g.addEdge(e.from, e.to, edgeAttrs); } catch {}
      }
      
      // Layout selection
      if (layoutMode === 'time-radial' && g.order > 0) {
        if (DEBUG) console.log('Applying time-radial layout to graph with', g.order, 'nodes');
        // Evolutionary tree layout: first commit at center, subsequent commits spiral outward
        try {
          // Collect all nodes with timestamps and sort by time
          const nodesWithTime: Array<{node: string, attrs: any, timestamp: number}> = [];
          g.forEachNode((node: string, attrs: any) => {
            const t = Number(new Date(attrs.timestamp || attrs.created_at || attrs.time || 0));
            if (isFinite(t)) {
              nodesWithTime.push({node, attrs, timestamp: t});
            }
          });
          
          // Sort by timestamp (earliest first)
          nodesWithTime.sort((a, b) => a.timestamp - b.timestamp);
          
          if (nodesWithTime.length === 0) {
            if (DEBUG) console.warn('No nodes with timestamps found for time-radial layout, falling back to force layout');
            // Fall through to force layout
          } else {
            // First commit (origin) at center
            const origin = nodesWithTime[0];
            g.setNodeAttribute(origin.node, 'x', 0);
            g.setNodeAttribute(origin.node, 'y', 0);
            
            if (nodesWithTime.length === 1) {
              if (DEBUG) console.log('Only one node with timestamp, positioned at center');
              // Continue processing other nodes
            } else {
            
            // Calculate time range for distance scaling
            const minTime = origin.timestamp;
            const maxTime = nodesWithTime[nodesWithTime.length - 1].timestamp;
            const totalSpan = Math.max(1, maxTime - minTime);
            
            // Time binning for radial layers (e.g., 6 bins)
            const BIN_COUNT = 6;
            const binSize = Math.ceil(totalSpan / BIN_COUNT);
            const binOf = (t: number) => Math.min(BIN_COUNT - 1, Math.floor((t - minTime) / binSize));

            // Polar parameters
            const baseRadius = 80;
            const layerRadius = 120; // distance between rings
            
            // Angle assignment by stable hash to keep communities apart-ish
            const angleForNode = (id: string) => {
              let h = 0;
              for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
              const u = ((h >>> 0) / 0xffffffff);
              return u * 2 * Math.PI;
            };

            // Position nodes by time bin (radius) and stable angle (type/community hash)
            for (let i = 0; i < nodesWithTime.length; i++) {
              const { node, timestamp, attrs } = nodesWithTime[i];
              const b = binOf(timestamp);
              const r = baseRadius + b * layerRadius;
              const a = angleForNode(String(node));
              const jitter = (rng() - 0.5) * (layerRadius * 0.2);
              const x = Math.cos(a) * r + jitter;
              const y = Math.sin(a) * r + jitter;
              g.setNodeAttribute(node, 'x', x);
              g.setNodeAttribute(node, 'y', y);
            }
            
            }
            
            // Position non-timestamp nodes around the spiral (for both single and multiple timestamp nodes)
            const nonTimestampNodes: string[] = [];
            g.forEachNode((node: string, attrs: any) => {
              const t = Number(new Date(attrs.timestamp || attrs.created_at || attrs.time || 0));
              if (!isFinite(t)) {
                nonTimestampNodes.push(node);
              }
            });
            
            // Position non-timestamp nodes in a ring around the spiral
            if (nonTimestampNodes.length > 0) {
              const ringRadius = baseRadius + BIN_COUNT * layerRadius + 80;
              const angleStep = (2 * Math.PI) / nonTimestampNodes.length;
              
              nonTimestampNodes.forEach((node, index) => {
                const angle = index * angleStep;
                const x = Math.cos(angle) * ringRadius;
                const y = Math.sin(angle) * ringRadius;
                g.setNodeAttribute(node, 'x', x);
                g.setNodeAttribute(node, 'y', y);
              });
            }
            
            if (DEBUG) console.log(`Evolutionary tree layout: ${nodesWithTime.length} timestamped nodes positioned in spiral, ${nonTimestampNodes.length} other nodes positioned in ring`);
            // Don't return here - let the graph continue to be processed for rendering
          }
        } catch (err) {
          if (DEBUG) console.warn('Evolutionary tree layout failed, falling back to force:', err);
        }
      } else if (g.order > 0 && g.order <= LAYOUT_MAX_NODES) {
        try {
          // Optimized force-directed layout with early termination
          const iterations = Math.min(80, Math.max(20, Math.floor(2000 / g.order)));
          const k = Math.sqrt((1000 * 1000) / g.order);
          const damping = 0.9;
          let maxMovement = 0;
          
          for (let i = 0; i < iterations; i++) {
            maxMovement = 0;
            
            g.forEachNode((node: string) => {
              let fx = 0, fy = 0;
              
              // Repulsion from other nodes (sampled for performance)
              const nodes = g.nodes();
              const sampleSize = Math.min(nodes.length, 50); // Sample up to 50 nodes for repulsion
              for (let j = 0; j < sampleSize; j++) {
                const otherNode = nodes[Math.floor(rng() * nodes.length)];
                if (node === otherNode) continue;
                
                const dx = g.getNodeAttribute(node, 'x') - g.getNodeAttribute(otherNode, 'x');
                const dy = g.getNodeAttribute(node, 'y') - g.getNodeAttribute(otherNode, 'y');
                const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = (k * k) / distance;
                fx += (dx / distance) * force;
                fy += (dy / distance) * force;
              }
              
              // Attraction from connected nodes
              g.forEachNeighbor(node, (neighbor: string) => {
                const dx = g.getNodeAttribute(neighbor, 'x') - g.getNodeAttribute(node, 'x');
                const dy = g.getNodeAttribute(neighbor, 'y') - g.getNodeAttribute(node, 'y');
                const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = (distance * distance) / k;
                fx += (dx / distance) * force;
                fy += (dy / distance) * force;
              });
              
              // Update position with bounds checking and damping
              const currentX = g.getNodeAttribute(node, 'x');
              const currentY = g.getNodeAttribute(node, 'y');
              const newX = currentX + fx * 0.1 * damping;
              const newY = currentY + fy * 0.1 * damping;
              
              // Track maximum movement for early termination
              const movement = Math.sqrt((newX - currentX) ** 2 + (newY - currentY) ** 2);
              maxMovement = Math.max(maxMovement, movement);
              
              // Ensure coordinates are valid numbers within reasonable bounds
              if (isFinite(newX) && isFinite(newY) && 
                  newX >= -10000 && newX <= 10000 && 
                  newY >= -10000 && newY <= 10000) {
                g.setNodeAttribute(node, 'x', newX);
                g.setNodeAttribute(node, 'y', newY);
              } else {
                // Reset to original position if calculation went wrong
                if (DEBUG) console.warn(`Invalid coordinates calculated for node ${node}, resetting to original position`);
                g.setNodeAttribute(node, 'x', currentX);
                g.setNodeAttribute(node, 'y', currentY);
              }
            });
            
            // Early termination if layout has converged
            if (maxMovement < 0.1) {
              if (DEBUG) console.info(`Layout converged after ${i + 1} iterations`);
              break;
            }
          }
        } catch (err) {
          if (DEBUG) console.warn('Layout algorithm failed:', err);
        }
      } else if (g.order > LAYOUT_MAX_NODES) {
        // Too many nodes for client-side layout; rely on incoming coordinates
        if (DEBUG) console.info(`Skipping layout for ${g.order} nodes (> ${LAYOUT_MAX_NODES})`);
      }
      
      // Optional Louvain clustering
      if (enableClustering && g.order > 0 && g.order <= LAYOUT_MAX_NODES && libraries.louvain) {
        try {
          libraries.louvain.assign(g, { resolution: 1 });
          // Keep community assignments available on nodes (coloring set below by degree)
        } catch (err) {
          if (DEBUG) console.warn('Louvain clustering failed:', err);
        }
      }

      // Helper: interpolate between hex colors using piecewise stops
      function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
      function hexToRgb(hex: string) {
        const h = hex.replace('#', '');
        const bigint = parseInt(h, 16);
        return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
      }
      function rgbToHex(r: number, g: number, b: number) {
        const toHex = (v: number) => v.toString(16).padStart(2, '0');
        return `#${toHex(Math.max(0, Math.min(255, Math.round(r))))}${toHex(Math.max(0, Math.min(255, Math.round(g))))}${toHex(Math.max(0, Math.min(255, Math.round(b))))}`;
      }
      function interpolateStops(stops: string[], t: number) {
        if (stops.length === 0) return '#888888';
        if (stops.length === 1) return stops[0];
        const clamped = Math.max(0, Math.min(1, t));
        const pos = clamped * (stops.length - 1);
        const i = Math.floor(pos);
        const frac = pos - i;
        const c1 = hexToRgb(stops[i]);
        const c2 = hexToRgb(stops[Math.min(stops.length - 1, i + 1)]);
        const r = lerp(c1.r, c2.r, frac);
        const g2 = lerp(c1.g, c2.g, frac);
        const b = lerp(c1.b, c2.b, frac);
        return rgbToHex(r, g2, b);
      }

      // Compute degree-based sizing and coloring
      try {
        let minDeg = Infinity, maxDeg = -Infinity;
        g.forEachNode((node: string) => {
          const d = g.degree(node) ?? 0;
          if (d < minDeg) minDeg = d;
          if (d > maxDeg) maxDeg = d;
        });
        if (!isFinite(minDeg)) { minDeg = 0; maxDeg = 0; }

        const minSize = 2;
        const maxSize = 10;
        const palette = ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725']; // Viridis stops

        g.forEachNode((node: string, attrs: any) => {
          const d = g.degree(node) ?? 0;
          const t = maxDeg > 0 ? Math.log1p(d) / Math.log1p(maxDeg) : 0; // log scale for stability
          const size = minSize + (maxSize - minSize) * t;
          const color = interpolateStops(palette, t);
          g.setNodeAttribute(node, 'size', size);
          g.setNodeAttribute(node, 'degree', d);
          g.setNodeAttribute(node, 'color', color);
          g.setNodeAttribute(node, 'originalColor', color);
        });
      } catch (err) {
        if (DEBUG) console.warn('Degree sizing/coloring failed:', err);
      }
      
      // Final check - ensure graph is valid for Sigma
      if (g.order === 0) {
        console.warn('Graph has no nodes, returning null');
        return null;
      }
      
      if (DEBUG) console.log('Graph created successfully:', { 
        nodes: g.order, 
        edges: g.size,
        layoutMode,
        sampleNode: g.nodes().slice(0, 1).map(node => ({
          id: node,
          attrs: g.getNodeAttributes(node)
        }))
      });
      
      return g;
    } catch (err) {
      if (DEBUG) console.error('Failed to create graph:', err);
      return null;
    }
  }, [data, enableClustering, mounted, isLoading, error, libraries, layoutMode, edgeTypes, maxEdgesInView, rng]);

  // Sigma initialization effect
  useEffect(() => {
    if (!containerRef.current || !mounted || !graph || isLoading || error || !libraries) return;

    // Destroy previous instance if any
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    try {
      const { Sigma } = libraries;
      
      if (DEBUG) console.log('Initializing Sigma with graph:', { nodes: graph.order, edges: graph.size });
      
      // Final safety check for coordinates
      let invalidNodes: string[] = [];
      graph.forEachNode((node: string) => {
        const attrs = graph.getNodeAttributes(node);
        if (typeof attrs.x !== 'number' || isNaN(attrs.x) || typeof attrs.y !== 'number' || isNaN(attrs.y)) {
          invalidNodes.push(node);
          if (DEBUG) console.error(`Invalid coordinates for node ${node}:`, attrs);
        }
      });
      
      if (invalidNodes.length > 0) {
        if (DEBUG) console.error(`Found ${invalidNodes.length} nodes with invalid coordinates, aborting Sigma initialization`);
        return;
      }
      
      // Initialize Sigma with optimized configuration for performance
      const sigma = new Sigma(graph, containerRef.current, {
        allowInvalidContainer: true, // Allow container without proper dimensions initially
        renderLabels: true,
        labelDensity: 0.05, // Reduced for better performance
        labelGridCellSize: 80, // Smaller grid for better performance
        labelRenderedSizeThreshold: 16, // Higher threshold to reduce label rendering
        enableEdgeHoverEvents: true,
        zIndex: true,
        // Enable dragging and other interactions
        enableNodeDrag: true,
        enableNodeHover: true,
        // Performance optimizations
        hideEdgesOnMove: true, // Hide edges while moving for better performance
        hideLabelsOnMove: true, // Hide labels while moving for better performance
        // Sigma v3 uses default programs automatically
        // No need to explicitly configure nodeProgramClasses or edgeProgramClasses
      });

      // Add zoom event handlers for LoD
      sigma.on('camera.updated', () => {
        const camera = sigma.getCamera();
        const newZoomLevel = camera.ratio;
        setZoomLevel(newZoomLevel);
        zoomRef.current = newZoomLevel;
        
        // Update viewport bounds
        const viewport = sigma.getBoundingBox();
        setViewportBounds({
          x: viewport.x[0],
          y: viewport.y[0],
          width: viewport.x[1] - viewport.x[0],
          height: viewport.y[1] - viewport.y[0],
        });
      });

      // Reducers: progressive labels/edges and focus mode dimming, time range fading
      sigma.setSetting('nodeReducer', (n: string, attrs: any) => {
        const res: any = { ...attrs };
        const isHovered = hoveredNodeRef.current === n;
        const zoom = zoomRef.current;
        const showByZoom = zoom >= (labelZoomThreshold ?? 1.2);
        
        // Labels: show on hover or when sufficiently zoomed
        res.label = (isHovered || showByZoom) ? (attrs.label || String(n)) : undefined;
        
        // Time mode fade outside selected time range
        if (layoutMode === 'time-radial' && timeRange && (attrs.timestamp || attrs.created_at)) {
          const t = Number(new Date(attrs.timestamp || attrs.created_at));
          const start = Number(new Date(timeRange.start));
          const end = Number(new Date(timeRange.end));
          if (isFinite(t) && isFinite(start) && isFinite(end) && (t < start || t > end)) {
            res.color = '#dddddd';
            res.size = Math.max(0.5, (attrs.size || 1) * 0.7);
          }
        }

        // Focus mode: dim non-neighbors when hovering a node
        if (focusMode && hoveredNodeRef.current && neighborSetRef.current) {
          if (!neighborSetRef.current.has(n) && hoveredNodeRef.current !== n) {
            res.color = '#cccccc';
            res.size = Math.max(0.5, (attrs.size || 1) * 0.7);
          } else {
            // Restore original color and size for focused nodes
            res.color = attrs.originalColor || attrs.color;
            res.size = attrs.size || 1;
          }
        } else {
          // Ensure original colors are preserved when not in focus mode
          res.color = attrs.originalColor || attrs.color;
        }
        
        // If focusNodeId provided, softly emphasize its neighborhood
        if (focusNodeId && sigma.getGraph) {
          const gref = sigma.getGraph();
          const isFocus = n === focusNodeId;
          if (!isFocus) {
            const neigh = new Set<string>();
            try { gref.forEachNeighbor(focusNodeId, (m: string) => neigh.add(m)); } catch {}
            if (!neigh.has(n)) {
              res.color = '#d0d0d0';
              res.size = Math.max(0.5, (attrs.size || 1) * 0.8);
            }
          }
        }

        return res;
      });

      sigma.setSetting('edgeReducer', (e: string, attrs: any) => {
        const res: any = { ...attrs };
        const zoom = zoomRef.current;
        
        // Hide edges at very low zoom to reduce clutter
        if (zoom < 0.7) {
          res.hidden = true;
          return res;
        }
        
        // Light edges mode and density-aware throttling
        if (lightEdges) {
          // Zoom-aware opacity and thickness
          const opacity = Math.max(0.25, Math.min(1, (zoom - 0.6)));
          res.color = `rgba(170,170,170,${opacity.toFixed(2)})`;
          const base = attrs.size ?? 0.8;
          res.size = Math.max(0.3, base * (zoom < 1 ? 0.7 : zoom < 1.5 ? 0.9 : 1.1));
          // Hide a portion of edges when graph is dense
          try {
            const gref = sigma.getGraph();
            if (gref && gref.size > maxEdgesInView) {
              // Probabilistically hide edges based on seed
              if (rng() < 0.5) res.hidden = true;
            }
          } catch {}
        } else {
          // Restore original edge color when not in light mode
          res.color = attrs.originalColor || attrs.color;
          res.size = attrs.size || 0.8;
        }
        
        // Focus mode: dim edges not connected to hovered node
        if (focusMode && hoveredNodeRef.current) {
          const [source, target] = sigma.getGraph().extremities(e);
          if (source !== hoveredNodeRef.current && target !== hoveredNodeRef.current) {
            res.color = '#dddddd';
            res.size = Math.max(0.2, (res.size || 0.8) * 0.5);
          } else {
            // Restore original color for edges connected to focused node
            res.color = lightEdges ? '#aaaaaa' : (attrs.originalColor || attrs.color);
            res.size = lightEdges ? Math.max(0.4, (attrs.size ?? 0.8) * 0.8) : (attrs.size || 0.8);
          }
        }
        
        return res;
      });

      // Forward node click
      sigma.on('clickNode', ({ node }: { node: string }) => {
        const attrs = graph.getNodeAttributes(node);
        onNodeClick && onNodeClick({ id: node, ...attrs });
      });
      
      sigma.on('enterNode', ({ node }: { node: string }) => {
        hoveredNodeRef.current = String(node);
        // Build neighbor set for focus mode dimming
        const neigh = new Set<string>();
        sigma.getGraph().forEachNeighbor(node, (nn: string) => neigh.add(String(nn)));
        neigh.add(String(node));
        neighborSetRef.current = neigh;
        sigma.refresh();
      });
      
      sigma.on('leaveNode', () => {
        hoveredNodeRef.current = null;
        neighborSetRef.current = null;
        sigma.refresh();
      });

      // Add drag events for better user feedback
      sigma.on('downNode', ({ node }: { node: string }) => {
        // Node is being dragged
        if (DEBUG) console.log('Dragging node:', node);
        draggingRef.current.add(String(node));
        // Mark node fixed during drag
        try { graph.setNodeAttribute(node, 'fixed', true); } catch {}
      });

      sigma.on('upNode', ({ node }: { node: string }) => {
        // Node drag ended
        if (DEBUG) console.log('Finished dragging node:', node);
        draggingRef.current.delete(String(node));
        // Release node back to simulation
        try { graph.setNodeAttribute(node, 'fixed', false); } catch {}
      });

      // Track zoom level
      const camera = sigma.getCamera();
      const onCam = () => {
        const { ratio } = camera.getState();
        zoomRef.current = 1 / ratio;
        sigma.refresh();
      };
      camera.on('updated', onCam);

      sigmaRef.current = sigma;

      // Force resize after a short delay to ensure container is properly sized
      setTimeout(() => {
        if (sigma && containerRef.current) {
          sigma.resize();
        }
      }, 100);

      // Add ResizeObserver to handle dynamic container resizing
      const resizeObserver = new ResizeObserver(() => {
        if (sigma && containerRef.current) {
          sigma.resize();
        }
      });
      
      if (containerRef.current) {
        resizeObserver.observe(containerRef.current);
      }

      return () => {
        camera.off('updated', onCam);
        resizeObserver.disconnect();
        sigma.kill();
        sigmaRef.current = null;
      };
    } catch (err) {
      if (DEBUG) console.error('Failed to initialize Sigma:', err);
    }
  }, [graph, onNodeClick, mounted, isLoading, error, libraries, focusNodeId, timeRange, layoutMode, lightEdges, maxEdgesInView, rng, labelZoomThreshold, focusMode]);

  // Time-aware styling hook (placeholder for future opacity modulation)
  useEffect(() => {
    if (!sigmaRef.current) return;
    // Example: could adjust rendering based on currentTimestamp/timeRange
  }, [currentTimestamp, timeRange]);

  // Simple physics simulation loop (attraction on edges + global repulsion)
  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma || !graph || !enablePhysics) return;
    if (graph.order > PHYSICS_NODE_THRESHOLD) return; // Skip very large graphs

    let running = true;

    const step = () => {
      if (!running) return;
      try {
        // Precompute positions
        const positions = new Map<string, { x: number; y: number }>();
        graph.forEachNode((n: string, attrs: any) => {
          positions.set(n, { x: attrs.x as number, y: attrs.y as number });
        });

        // Forces accumulator
        const forces = new Map<string, { fx: number; fy: number }>();
        graph.forEachNode((n: string) => forces.set(n, { fx: 0, fy: 0 }));

        // Edge attraction (springs)
        graph.forEachEdge((e: string, attr: any, src: string, tgt: string) => {
          const ps = positions.get(src)!;
          const pt = positions.get(tgt)!;
          const dx = pt.x - ps.x;
          const dy = pt.y - ps.y;
          const dist = Math.max(0.01, Math.hypot(dx, dy));
          const k = physicsAttraction; // spring constant
          const f = k * (dist - 60); // rest length ~60
          const fx = (dx / dist) * f;
          const fy = (dy / dist) * f;
          const fs = forces.get(src)!; fs.fx += fx; fs.fy += fy;
          const ft = forces.get(tgt)!; ft.fx -= fx; ft.fy -= fy;
        });

        // Global repulsion (sampled to reduce cost)
        const nodes = graph.nodes();
        for (let i = 0; i < nodes.length; i++) {
          const ni = nodes[i];
          const pi = positions.get(ni)!;
          for (let j = i + 1; j < nodes.length; j += 2) { // sample every other pair
            const nj = nodes[j];
            const pj = positions.get(nj)!;
            const dx = pj.x - pi.x;
            const dy = pj.y - pi.y;
            const dist2 = dx * dx + dy * dy + 0.01;
            const inv = 1 / dist2;
            const rep = physicsRepulsion * inv;
            const fx = dx * rep;
            const fy = dy * rep;
            const fi = forces.get(ni)!; fi.fx -= fx; fi.fy -= fy;
            const fj = forces.get(nj)!; fj.fx += fx; fj.fy += fy;
          }
        }

        // Integrate
        graph.forEachNode((n: string, attrs: any) => {
          if (attrs.fixed || draggingRef.current.has(String(n))) return;
          const f = forces.get(n)!;
          const nx = (attrs.x as number) + f.fx * (1 - (1 - physicsFriction));
          const ny = (attrs.y as number) + f.fy * (1 - (1 - physicsFriction));
          if (isFinite(nx) && isFinite(ny)) {
            graph.setNodeAttribute(n, 'x', Math.max(-20000, Math.min(20000, nx)));
            graph.setNodeAttribute(n, 'y', Math.max(-20000, Math.min(20000, ny)));
          }
        });

        sigma.refresh();
      } catch (e) {
        if (DEBUG) console.warn('Physics step error', e);
      }
      animRef.current = requestAnimationFrame(step);
    };

    animRef.current = requestAnimationFrame(step);
    return () => {
      running = false;
      if (animRef.current) cancelAnimationFrame(animRef.current);
      animRef.current = null;
    };
  }, [enablePhysics, physicsAttraction, physicsRepulsion, physicsFriction, graph]);

  // Optional: viewport-only filtering (client-side)
  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma) return;
    
    if (!showOnlyViewport) {
      sigma.setSetting('nodeReducer', (n: string, attrs: any) => {
        const res: any = { ...attrs };
        if (hoveredNodeRef.current === n) res.label = attrs.label || String(n);
        else res.label = undefined;
        return res;
      });
      sigma.refresh();
      return;
    }
    
    const camera = sigma.getCamera();
    const isInView = (x: number, y: number) => {
      const { width: W, height: H } = sigma.getDimensions();
      const p = sigma.graphToViewport({ x, y });
      return p.x >= 0 && p.y >= 0 && p.x <= W && p.y <= H;
    };
    
    sigma.setSetting('nodeReducer', (n: string, attrs: any) => {
      const res: any = { ...attrs };
      const pos = sigma.getGraph().getNodeAttributes(n);
      const show = typeof pos.x === 'number' && typeof pos.y === 'number' ? isInView(pos.x, pos.y) : true;
      res.hidden = !show;
      if (hoveredNodeRef.current === n && show) res.label = attrs.label || String(n);
      else res.label = undefined;
      return res;
    });
    
    const onCamera = () => sigma.refresh();
    camera.on('updated', onCamera);
    sigma.refresh();
    
    return () => {
      camera.off('updated', onCamera);
    };
  }, [showOnlyViewport]);

  // Emit viewport changes upstream (for auto-loading)
  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma || !onViewportChange) return;
    
    const camera = sigma.getCamera();
    const handler = () => {
      const { x, y, ratio } = camera.getState();
      const { width, height } = sigma.getDimensions();
      onViewportChange({ x, y, width, height, zoom: 1 / ratio });
    };
    
    camera.on('updated', handler);
    // Don't call handler immediately to prevent initial trigger
    
    return () => camera.off('updated', handler);
  }, [onViewportChange]);

  // Don't render anything until mounted (client-side only)
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
      >
        Loading graph visualization...
      </Box>
    );
  }

  // Show loading state while libraries are loading
  if (isLoading) {
    return (
      <Box 
        height={height} 
        width={width} 
        borderWidth="1px" 
        borderRadius="md" 
        display="flex" 
        alignItems="center" 
        justifyContent="center"
      >
        Loading graph libraries...
      </Box>
    );
  }

  // Show error state if libraries failed to load
  if (error) {
    return (
      <Box 
        height={height} 
        width={width} 
        borderWidth="1px" 
        borderRadius="md" 
        display="flex" 
        alignItems="center" 
        justifyContent="center"
        color="red.500"
      >
        {error}
      </Box>
    );
  }

  return (
    <Box style={{ height, width, minHeight: height, minWidth: width }}>
      <div 
        ref={containerRef} 
        style={{ 
          height: '100%', 
          width: '100%', 
          minHeight: height, 
          minWidth: width,
          position: 'relative'
        }} 
      />
    </Box>
  );
}

export default EvolutionGraph;
