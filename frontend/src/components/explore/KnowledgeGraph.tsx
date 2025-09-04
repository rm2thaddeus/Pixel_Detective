"use client";

import React, { useEffect, useMemo, useRef } from 'react';
import Graph from 'graphology';
import Sigma from 'sigma';
import { Box, useColorModeValue } from '@chakra-ui/react';
import louvain from 'graphology-communities-louvain';
import { api } from '@/lib/api';

export function KnowledgeGraph({ clustering, focusMode }: { clustering: boolean; focusMode: boolean }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graph = useMemo(() => new Graph(), []);
  const bg = useColorModeValue('#ffffff', '#1A202C');

  useEffect(() => {
    let mounted = true;

    async function hydrate() {
      try {
        const [nodes, edges] = await Promise.all([
          api.get('/api/v1/dev-graph/nodes', { params: { limit: 300 } }).then((r) => r.data),
          api.get('/api/v1/dev-graph/relations', { params: { limit: 600 } }).then((r) => r.data),
        ]);
        if (!mounted) return;
        // Reset graph
        graph.clear();
        // Add nodes
        nodes.forEach((n: any) => {
          const id = String(n.id);
          if (!graph.hasNode(id)) graph.addNode(id, { label: n.type ? `${n.type}` : id, size: 3 });
        });
        // Add edges
        edges.forEach((e: any, i: number) => {
          const s = String(e.from);
          const t = String(e.to);
          if (graph.hasNode(s) && graph.hasNode(t)) {
            const eid = `e${i}-${s}-${t}`;
            if (!graph.hasEdge(s, t)) graph.addEdge(s, t, { label: e.type });
          }
        });

        // Community detection coloring
        if (clustering) {
          louvain.assign(graph, { resolution: 1.0 });
          graph.forEachNode((n, attrs) => {
            const comm = (attrs as any).community ?? 0;
            const palette = ['#3182CE', '#D69E2E', '#38A169', '#D53F8C', '#805AD5'];
            graph.setNodeAttribute(n, 'color', palette[Number(comm) % palette.length]);
          });
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
      renderer = new Sigma(graph, containerRef.current, { renderLabels: true });

      if (focusMode) {
        renderer.on('enterNode', ({ node }) => {
          const neighbors = new Set(graph.neighbors(node));
          graph.forEachNode((n) => {
            const isFocus = n === node || neighbors.has(n);
            graph.setNodeAttribute(n, 'hidden', !isFocus);
          });
          graph.forEachEdge((e, a, s, t) => {
            graph.setEdgeAttribute(e, 'hidden', !(s === node || t === node || (neighbors.has(s) && neighbors.has(t))));
          });
        });
        renderer.on('leaveNode', () => {
          graph.forEachNode((n) => graph.setNodeAttribute(n, 'hidden', false));
          graph.forEachEdge((e) => graph.setEdgeAttribute(e, 'hidden', false));
        });
      }
    }

    return () => {
      mounted = false;
      renderer?.kill();
    };
  }, [graph, clustering, focusMode]);

  return <Box ref={containerRef} h="600px" w="full" borderRadius="md" borderWidth="1px" bg={bg} />;
}
