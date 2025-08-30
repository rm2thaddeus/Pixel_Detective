'use client';

import dynamic from 'next/dynamic';
import { Box } from '@chakra-ui/react';

const ForceGraph2D = dynamic<any>(() => import('react-force-graph-2d'), { ssr: false });

export type GraphData = { nodes: any[]; links: any[] };

export function EvolutionGraph({
  data,
  height = 600,
  width = 1000,
  onNodeClick,
}: {
  data: GraphData;
  height?: number;
  width?: number;
  onNodeClick?: (node: any) => void;
}) {
  return (
    <Box>
      <ForceGraph2D
        graphData={data}
        height={height}
        width={width}
        nodeId="id"
        linkSource="from"
        linkTarget="to"
        nodeLabel={(n: any) => `${n.id}\n${n.type ?? ''}`}
        linkLabel={(l: any) => l.type}
        nodeAutoColorBy={(n: any) => n.type ?? 'Unknown'}
        linkColor={(l: any) => (
          l.type === 'PART_OF' ? '#888' :
          l.type === 'EVOLVES_FROM' ? '#2b8a3e' :
          l.type === 'REFERENCES' ? '#1c7ed6' :
          l.type === 'DEPENDS_ON' ? '#e67700' : '#999'
        )}
        onNodeClick={onNodeClick}
      />
    </Box>
  );
}

export default EvolutionGraph;


