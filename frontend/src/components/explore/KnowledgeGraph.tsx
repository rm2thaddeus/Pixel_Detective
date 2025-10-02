"use client";

import React, { useEffect, useMemo, useRef } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { Box, useColorModeValue } from '@chakra-ui/react';
import { api, devGraphApi } from '@/lib/api';
import { workerManager } from '@/utils/workerManager';

export function KnowledgeGraph({ clustering, focusMode }: { clustering: boolean; focusMode: boolean }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graph = useMemo(() => new Graph(), []);
  const bg = useColorModeValue('#ffffff', '#1A202C');

  useEffect(() => {
    let mounted = true;

    async function hydrate() {
      try {
        // Progressive hydration with smaller initial page
        const initialLimit = 250;
        let sub = await devGraphApi
          .get('/api/v1/dev-graph/graph/subgraph', {
            params: {
              limit: initialLimit,
              include_counts: false, // Skip counts for faster initial load
              // Optionally pass types/time bounds here
            },
          })
          .then((r) => r.data);
        
        if (!mounted) return;
        
        // Reset graph
        graph.clear();
        
        // Helper function to add nodes in batches
        const addNodesBatch = (nodes: any[]) => {
          return new Promise<void>((resolve) => {
            const batchSize = 200;
            let index = 0;
            
            const processBatch = () => {
              const endIndex = Math.min(index + batchSize, nodes.length);
              for (let i = index; i < endIndex; i++) {
                const n = nodes[i];
                const id = String(n.id);
                if (graph.hasNode(id)) continue;
                const label = n.label || n.type || (n.labels && n.labels[0]) || id;
                const size = Number(n.size ?? 1.2);
                const attrs: any = { label, size };
                if (typeof n.x === 'number' && typeof n.y === 'number') {
                  attrs.x = n.x;
                  attrs.y = n.y;
                }
                graph.addNode(id, attrs);
              }
              index = endIndex;
              
              if (index < nodes.length) {
                // Use requestIdleCallback for non-blocking processing
                if (window.requestIdleCallback) {
                  window.requestIdleCallback(processBatch);
                } else {
                  setTimeout(processBatch, 0);
                }
              } else {
                resolve();
              }
            };
            
            processBatch();
          });
        };
        
        // Helper function to add edges in batches
        const addEdgesBatch = (edges: any[]) => {
          return new Promise<void>((resolve) => {
            const batchSize = 200;
            let index = 0;
            
            const processBatch = () => {
              const endIndex = Math.min(index + batchSize, edges.length);
              for (let i = index; i < endIndex; i++) {
                const e = edges[i];
                const s = String(e.from ?? e.source ?? e.a);
                const t = String(e.to ?? e.target ?? e.b);
                if (!graph.hasNode(s) || !graph.hasNode(t)) continue;
                const eid = `e${i}-${s}-${t}`;
                if (!graph.hasEdge(s, t)) graph.addEdge(s, t, { label: e.type || e.rel_type || '' });
              }
              index = endIndex;
              
              if (index < edges.length) {
                if (window.requestIdleCallback) {
                  window.requestIdleCallback(processBatch);
                } else {
                  setTimeout(processBatch, 0);
                }
              } else {
                resolve();
              }
            };
            
            processBatch();
          });
        };
        
        // Process initial page
        const nodes = sub?.nodes ?? [];
        const edges = sub?.edges ?? sub?.links ?? [];
        
        await addNodesBatch(nodes);
        await addEdgesBatch(edges);
        
        // Continue with pagination if there are more pages
        while (sub?.pagination?.has_more && mounted) {
          sub = await devGraphApi
            .get('/api/v1/dev-graph/graph/subgraph', {
              params: {
                limit: initialLimit,
                include_counts: false,
                cursor: sub.pagination.next_cursor,
              },
            })
            .then((r) => r.data);
          
          if (!mounted) break;
          
          const moreNodes = sub?.nodes ?? [];
          const moreEdges = sub?.edges ?? sub?.links ?? [];
          
          await addNodesBatch(moreNodes);
          await addEdgesBatch(moreEdges);
        }

        // Community detection coloring using web worker
        if (clustering) {
          try {
            // Prepare data for worker
            const nodes = graph.mapNodes((nodeId, attributes) => ({
              id: nodeId,
              ...attributes
            }));
            
            const edges = graph.mapEdges((edgeId, attributes, source, target) => ({
              source,
              target,
              ...attributes
            }));
            
            // Use worker for community detection
            const communities = await workerManager.detectCommunities(nodes, edges, 1.0);
            
            // Apply community colors in batches
            const palette = ['#3182CE', '#D69E2E', '#38A169', '#D53F8C', '#805AD5'];
            const nodeIds = Object.keys(communities);
            const batchSize = 200;
            
            for (let i = 0; i < nodeIds.length; i += batchSize) {
              const batch = nodeIds.slice(i, i + batchSize);
              
              if (window.requestIdleCallback) {
                await new Promise(resolve => {
                  window.requestIdleCallback(() => {
                    batch.forEach(nodeId => {
                      const comm = communities[nodeId] ?? 0;
                      graph.setNodeAttribute(nodeId, 'color', palette[Number(comm) % palette.length]);
                    });
                    resolve(undefined);
                  });
                });
              } else {
                batch.forEach(nodeId => {
                  const comm = communities[nodeId] ?? 0;
                  graph.setNodeAttribute(nodeId, 'color', palette[Number(comm) % palette.length]);
                });
              }
            }
          } catch (error) {
            console.error('Error in community detection:', error);
            // Fallback to default color
            graph.forEachNode((n) => graph.setNodeAttribute(n, 'color', '#3182CE'));
          }
        } else {
          graph.forEachNode((n) => graph.setNodeAttribute(n, 'color', '#3182CE'));
        }
      } catch (e) {
        // leave graph empty on error
      }
    }

    hydrate();

    let renderer: Sigma | undefined;
    if (containerRef.current) {
      // Limit label rendering for performance - only show labels on hover or for small graphs
      const nodeCount = graph.order;
      const shouldRenderLabels = nodeCount <= 1000;
      
      renderer = new Sigma(graph, containerRef.current, { 
        renderLabels: shouldRenderLabels,
        // Additional performance optimizations
        hideEdgesOnMove: true,
        hideLabelsOnMove: true,
        enableEdgeEvents: false, // Disable edge events for better performance
        defaultNodeColor: '#3182CE',
        defaultEdgeColor: '#A0AEC0'
      });

      if (focusMode) {
        let focusUpdateScheduled = false;
        
        const updateFocusMode = (node: string) => {
          if (focusUpdateScheduled) return;
          focusUpdateScheduled = true;
          
          requestAnimationFrame(() => {
            const neighbors = new Set(graph.neighbors(node));
            
            // Use batch operations for better performance
            graph.startBatch();
            
            graph.forEachNode((n) => {
              const isFocus = n === node || neighbors.has(n);
              graph.setNodeAttribute(n, 'hidden', !isFocus);
            });
            
            graph.forEachEdge((e, a, s, t) => {
              graph.setEdgeAttribute(e, 'hidden', !(s === node || t === node || (neighbors.has(s) && neighbors.has(t))));
            });
            
            graph.endBatch();
            focusUpdateScheduled = false;
          });
        };
        
        const clearFocusMode = () => {
          if (focusUpdateScheduled) return;
          focusUpdateScheduled = true;
          
          requestAnimationFrame(() => {
            graph.startBatch();
            graph.forEachNode((n) => graph.setNodeAttribute(n, 'hidden', false));
            graph.forEachEdge((e) => graph.setEdgeAttribute(e, 'hidden', false));
            graph.endBatch();
            focusUpdateScheduled = false;
          });
        };
        
        renderer.on('enterNode', ({ node }) => updateFocusMode(node));
        renderer.on('leaveNode', clearFocusMode);
      }
    }

    return () => {
      mounted = false;
      renderer?.kill();
      // Clean up workers when component unmounts
      workerManager.terminate();
    };
  }, [graph, clustering, focusMode]);

  return <Box ref={containerRef} h="600px" w="full" borderRadius="md" borderWidth="1px" bg={bg} />;
}
