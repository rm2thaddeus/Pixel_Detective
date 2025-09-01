'use client';

import { Box } from '@chakra-ui/react';
import { useEffect, useMemo, useRef } from 'react';
import Graph from 'graphology';
import louvain from 'graphology-communities-louvain';
import { Sigma } from 'sigma';

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
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const hoveredNodeRef = useRef<string | null>(null);

  const graph = useMemo(() => {
    const g = new Graph();
    // Add nodes
    for (const n of data.nodes || []) {
      if (!g.hasNode(n.id)) {
        g.addNode(n.id, {
          label: String(n.id),
          type: n.type || 'Unknown',
          color:
            n.type === 'Requirement' ? '#2b8a3e' :
            n.type === 'File' ? '#1c7ed6' :
            n.type === 'Sprint' ? '#e67700' : '#888',
          ...n,
        });
      }
    }
    // Add edges
    let edgeIndex = 0;
    for (const e of data.relations || []) {
      const edgeId = `${e.type}-${edgeIndex++}`;
      if (!g.hasNode(e.from) || !g.hasNode(e.to)) continue;
      g.addEdge(e.from, e.to, {
        label: e.type,
        type: e.type,
        color:
          e.type === 'PART_OF' ? '#888' :
          e.type === 'EVOLVES_FROM' ? '#2b8a3e' :
          e.type === 'REFERENCES' ? '#1c7ed6' :
          e.type === 'DEPENDS_ON' ? '#e67700' : '#999',
        timestamp: e.timestamp,
        ...e,
      });
    }
    // Optional Louvain clustering to color communities
    if (enableClustering && g.order > 0) {
      try {
        louvain.assign(g, { resolution: 1 });
        g.forEachNode((node, attrs) => {
          const community = (attrs as any).community;
          const colorPalette = ['#2b8a3e', '#1c7ed6', '#e67700', '#845ef7', '#099268', '#c92a2a'];
          const color = colorPalette[Math.abs((community ?? 0) % colorPalette.length)];
          g.setNodeAttribute(node, 'color', color);
        });
      } catch {}
    }
    return g;
  }, [data, enableClustering]);

  useEffect(() => {
    if (!containerRef.current) return;

    // Destroy previous instance if any
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
    }

    // Initialize Sigma
    const sigma = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: false,
      renderLabels: true,
      labelDensity: 0.07,
      labelGridCellSize: 100,
      labelRenderedSizeThreshold: 14,
      enableEdgeHoverEvents: true,
      zIndex: true,
    } as any);

    // Hover/selection reducers to reduce clutter
    sigma.setSetting('nodeReducer', (n, attrs) => {
      const res: any = { ...attrs };
      // Hide labels by default; show on hover
      if (hoveredNodeRef.current === n) {
        res.label = attrs.label || String(n);
      } else {
        res.label = undefined;
      }
      return res;
    });
    sigma.setSetting('edgeReducer', (e, attrs) => {
      const res: any = { ...attrs };
      return res;
    });

    // Forward node click
    sigma.on('clickNode', ({ node }) => {
      const attrs = graph.getNodeAttributes(node);
      onNodeClick && onNodeClick({ id: node, ...attrs });
    });
    sigma.on('enterNode', ({ node }) => {
      hoveredNodeRef.current = String(node);
      sigma.refresh();
    });
    sigma.on('leaveNode', () => {
      hoveredNodeRef.current = null;
      sigma.refresh();
    });

    sigmaRef.current = sigma;
    return () => {
      sigma.kill();
      sigmaRef.current = null;
    };
  }, [graph, onNodeClick]);

  // Time-aware styling hook (placeholder for future opacity modulation)
  useEffect(() => {
    if (!sigmaRef.current) return;
    // Example: could adjust rendering based on currentTimestamp/timeRange
  }, [currentTimestamp, timeRange]);

  // Optional: viewport-only filtering (client-side)
  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma) return;
    if (!showOnlyViewport) {
      sigma.setSetting('nodeReducer', (n, attrs) => {
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
    sigma.setSetting('nodeReducer', (n, attrs) => {
      const res: any = { ...attrs };
      const pos = sigma.getGraph().getNodeAttributes(n) as any;
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
      const { x, y, angle, ratio } = camera.getState();
      const { width, height } = sigma.getDimensions();
      onViewportChange({ x, y, width, height, zoom: 1 / ratio });
    };
    camera.on('updated', handler);
    handler();
    return () => camera.off('updated', handler);
  }, [onViewportChange]);

  return (
    <Box style={{ height, width }}>
      <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
    </Box>
  );
}

export default EvolutionGraph;

