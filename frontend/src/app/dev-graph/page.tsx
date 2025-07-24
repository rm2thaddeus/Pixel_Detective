'use client';
import dynamic from 'next/dynamic';
import { Box, Heading } from '@chakra-ui/react';
import { useEffect, useState } from 'react';

const ForceGraph = dynamic(() => import('react-force-graph').then(mod => mod.ForceGraph2D), { ssr: false });

export default function DevGraphPage() {
  const [data, setData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    fetch('/api/v1/dev-graph/nodes')
      .then(res => res.json())
      .then(nodes => {
        fetch('/api/v1/dev-graph/relations')
          .then(r => r.json())
          .then(links => setData({ nodes, links }));
      });
  }, []);

  return (
    <Box p={8} minH="100vh">
      <Heading mb={4}>Developer Graph</Heading>
      <ForceGraph graphData={data} height={600} width={800} />
    </Box>
  );
}
