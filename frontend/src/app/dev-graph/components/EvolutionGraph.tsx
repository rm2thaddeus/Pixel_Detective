'use client';

import { Box } from '@chakra-ui/react';
import { useEffect, useMemo, useRef, useState } from 'react';

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
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [libraries, setLibraries] = useState<{
    Graph: any;
    Sigma: any;
    louvain: any;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<any | null>(null);
  const hoveredNodeRef = useRef<string | null>(null);

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
        console.error('Failed to load graph libraries:', err);
        setError('Failed to load graph visualization libraries');
        setIsLoading(false);
      }
    };

    loadLibraries();
    
    return () => {
      isMounted = false;
    };
  }, [mounted]);

  // Create graph data
  const graph = useMemo(() => {
    if (!mounted || isLoading || error || !libraries) return null;
    
    console.log('Creating graph with data:', { 
      nodesCount: data.nodes?.length || 0, 
      relationsCount: data.relations?.length || 0,
      sampleNode: data.nodes?.[0],
      sampleNodeCoords: data.nodes?.[0] ? {
        x: data.nodes[0].x,
        y: data.nodes[0].y,
        xType: typeof data.nodes[0].x,
        yType: typeof data.nodes[0].y,
        xValid: typeof data.nodes[0].x === 'number' && !isNaN(data.nodes[0].x),
        yValid: typeof data.nodes[0].y === 'number' && !isNaN(data.nodes[0].y)
      } : null
    });
    
    try {
      const { Graph } = libraries;
      const g = new Graph();
      
      // Add nodes (coordinates should already be provided in data)
      for (const n of data.nodes || []) {
        if (!g.hasNode(n.id)) {
          // Validate coordinates before adding node
          const x = typeof n.x === 'number' && isFinite(n.x) ? n.x : 0;
          const y = typeof n.y === 'number' && isFinite(n.y) ? n.y : 0;
          const size = typeof n.size === 'number' && isFinite(n.size) && n.size > 0 ? n.size : 1;
          
          if (!isFinite(x) || !isFinite(y)) {
            console.error(`Skipping node ${n.id} with invalid coordinates: x=${n.x}, y=${n.y}`);
            continue;
          }
          
          // Create node attributes, ensuring no conflicting properties
          const nodeAttrs = {
            label: String(n.id),
            // Store original type in a custom property, not nodeType (which Sigma uses for rendering)
            originalType: n.type || 'Unknown',
            color:
              n.type === 'Requirement' ? '#2b8a3e' :
              n.type === 'File' ? '#1c7ed6' :
              n.type === 'Sprint' ? '#e67700' :
              n.type === 'GitCommit' ? '#9f7aea' : '#888',
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
      
      // Add edges
      for (const e of data.relations || []) {
        if (!g.hasNode(e.from) || !g.hasNode(e.to)) continue;
        
        // Create edge attributes, ensuring no conflicting properties
        const edgeAttrs = {
          label: e.type,
          // Store original type in a custom property, not type (which Sigma uses for rendering)
          originalType: e.type,
          color:
            e.type === 'PART_OF' ? '#888' :
            e.type === 'EVOLVES_FROM' ? '#2b8a3e' :
            e.type === 'REFERENCES' ? '#1c7ed6' :
            e.type === 'DEPENDS_ON' ? '#e67700' : '#999',
          timestamp: e.timestamp,
          // Include other properties but exclude problematic ones
          ...Object.fromEntries(
            Object.entries(e).filter(([key]) => 
              !['type', 'from', 'to'].includes(key)
            )
          )
        };
        
        g.addEdge(e.from, e.to, edgeAttrs);
      }
      
      // Apply force-directed layout to improve node positioning
      if (g.order > 0) {
        try {
          // Simple force-directed layout
          const iterations = 100;
          const k = Math.sqrt((1000 * 1000) / g.order);
          
          for (let i = 0; i < iterations; i++) {
            g.forEachNode((node: string) => {
              let fx = 0, fy = 0;
              
              // Repulsion from other nodes
              g.forEachNode((otherNode: string) => {
                if (node === otherNode) return;
                const dx = g.getNodeAttribute(node, 'x') - g.getNodeAttribute(otherNode, 'x');
                const dy = g.getNodeAttribute(node, 'y') - g.getNodeAttribute(otherNode, 'y');
                const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = (k * k) / distance;
                fx += (dx / distance) * force;
                fy += (dy / distance) * force;
              });
              
              // Attraction from connected nodes
              g.forEachNeighbor(node, (neighbor: string) => {
                const dx = g.getNodeAttribute(neighbor, 'x') - g.getNodeAttribute(node, 'x');
                const dy = g.getNodeAttribute(neighbor, 'y') - g.getNodeAttribute(node, 'y');
                const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = (distance * distance) / k;
                fx += (dx / distance) * force;
                fy += (dy / distance) * force;
              });
              
              // Update position with bounds checking
              const currentX = g.getNodeAttribute(node, 'x');
              const currentY = g.getNodeAttribute(node, 'y');
              const newX = currentX + fx * 0.1;
              const newY = currentY + fy * 0.1;
              
              // Ensure coordinates are valid numbers within reasonable bounds
              if (isFinite(newX) && isFinite(newY) && 
                  newX >= -10000 && newX <= 10000 && 
                  newY >= -10000 && newY <= 10000) {
                g.setNodeAttribute(node, 'x', newX);
                g.setNodeAttribute(node, 'y', newY);
              } else {
                // Reset to original position if calculation went wrong
                console.warn(`Invalid coordinates calculated for node ${node}, resetting to original position`);
                g.setNodeAttribute(node, 'x', currentX);
                g.setNodeAttribute(node, 'y', currentY);
              }
            });
          }
        } catch (err) {
          console.warn('Layout algorithm failed:', err);
        }
      }
      
      // Optional Louvain clustering
      if (enableClustering && g.order > 0 && libraries.louvain) {
        try {
          libraries.louvain.assign(g, { resolution: 1 });
          g.forEachNode((node: string, attrs: any) => {
            const community = attrs.community;
            const colorPalette = ['#2b8a3e', '#1c7ed6', '#e67700', '#845ef7', '#099268', '#c92a2a'];
            const color = colorPalette[Math.abs((community ?? 0) % colorPalette.length)];
            g.setNodeAttribute(node, 'color', color);
          });
        } catch (err) {
          console.warn('Louvain clustering failed:', err);
        }
      }
      
      // Final check - ensure graph is valid for Sigma
      if (g.order === 0) {
        console.warn('Graph has no nodes, returning null');
        return null;
      }
      
      console.log('Graph created successfully:', { 
        nodes: g.order, 
        edges: g.size,
        sampleNode: g.nodes().slice(0, 1).map(node => ({
          id: node,
          attrs: g.getNodeAttributes(node)
        }))
      });
      
      return g;
    } catch (err) {
      console.error('Failed to create graph:', err);
      return null;
    }
  }, [data, enableClustering, mounted, isLoading, error, libraries]);

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
      
      console.log('Initializing Sigma with graph:', { nodes: graph.order, edges: graph.size });
      
      // Final safety check for coordinates
      let invalidNodes: string[] = [];
      graph.forEachNode((node: string) => {
        const attrs = graph.getNodeAttributes(node);
        if (typeof attrs.x !== 'number' || isNaN(attrs.x) || typeof attrs.y !== 'number' || isNaN(attrs.y)) {
          invalidNodes.push(node);
          console.error(`Invalid coordinates for node ${node}:`, attrs);
        }
      });
      
      if (invalidNodes.length > 0) {
        console.error(`Found ${invalidNodes.length} nodes with invalid coordinates, aborting Sigma initialization`);
        return;
      }
      
      // Initialize Sigma with default configuration
      const sigma = new Sigma(graph, containerRef.current, {
        allowInvalidContainer: false,
        renderLabels: true,
        labelDensity: 0.07,
        labelGridCellSize: 100,
        labelRenderedSizeThreshold: 14,
        enableEdgeHoverEvents: true,
        zIndex: true,
        // Sigma v3 uses default rendering - no need to configure nodeProgramClasses or edgeProgramClasses
        // All nodes will use the default circle program, all edges will use the default line program
      });

      // Hover/selection reducers to reduce clutter
      sigma.setSetting('nodeReducer', (n: string, attrs: any) => {
        const res: any = { ...attrs };
        // Hide labels by default; show on hover
        if (hoveredNodeRef.current === n) {
          res.label = attrs.label || String(n);
        } else {
          res.label = undefined;
        }
        return res;
      });
      
      sigma.setSetting('edgeReducer', (e: string, attrs: any) => {
        const res: any = { ...attrs };
        return res;
      });

      // Forward node click
      sigma.on('clickNode', ({ node }: { node: string }) => {
        const attrs = graph.getNodeAttributes(node);
        onNodeClick && onNodeClick({ id: node, ...attrs });
      });
      
      sigma.on('enterNode', ({ node }: { node: string }) => {
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
    } catch (err) {
      console.error('Failed to initialize Sigma:', err);
    }
  }, [graph, onNodeClick, mounted, isLoading, error, libraries]);

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
    handler();
    
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
    <Box style={{ height, width }}>
      <div ref={containerRef} style={{ height: '100%', width: '100%' }} />
    </Box>
  );
}

export default EvolutionGraph;

