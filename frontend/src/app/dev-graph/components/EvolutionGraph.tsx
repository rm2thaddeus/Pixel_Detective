'use client';

import dynamic from 'next/dynamic';
import { Box } from '@chakra-ui/react';
import { useMemo } from 'react';

const ForceGraph2D = dynamic<any>(() => import('react-force-graph-2d'), { ssr: false });

export type GraphData = { nodes: any[]; links: any[] };

export function EvolutionGraph({
  data,
  height = 600,
  width = 1000,
  onNodeClick,
  currentTimestamp,
  timeRange,
}: {
  data: GraphData;
  height?: number;
  width?: number;
  onNodeClick?: (node: any) => void;
  currentTimestamp?: string;
  timeRange?: { start: string; end: string };
}) {
  // Time-aware node styling
  const timeAwareData = useMemo(() => {
    if (!currentTimestamp || !timeRange) return data;

    const currentTime = new Date(currentTimestamp).getTime();
    const startTime = new Date(timeRange.start).getTime();
    const endTime = new Date(timeRange.end).getTime();
    
    // Calculate time position (0 = start, 1 = end)
    const timePosition = Math.max(0, Math.min(1, (currentTime - startTime) / (endTime - startTime)));

    return {
      ...data,
      nodes: data.nodes.map(node => ({
        ...node,
        // Add time-aware properties for styling
        timePosition,
        isActive: true, // All nodes are active in current implementation
      })),
      links: data.links.map(link => ({
        ...link,
        // Add time-aware properties for styling
        timePosition,
        isActive: true, // All links are active in current implementation
      }))
    };
  }, [data, currentTimestamp, timeRange]);

  return (
    <Box>
      <ForceGraph2D
        graphData={timeAwareData}
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
        // Time-aware node styling
        nodeRelSize={6}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.id || 'Unknown';
          const fontSize = 12/globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

          // Time-aware opacity
          const opacity = timeRange && currentTimestamp ? 0.8 : 1.0;
          
          ctx.fillStyle = `rgba(255, 255, 255, ${opacity})`;
          ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = `rgba(0, 0, 0, ${opacity})`;
          ctx.fillText(label, node.x, node.y);

          // Draw node circle
          ctx.beginPath();
          ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
          ctx.fillStyle = `rgba(43, 138, 62, ${opacity})`;
          ctx.fill();
        }}
        // Time-aware link styling
        linkWidth={(link: any) => {
          // Thinner links when time-aware filtering is active
          console.log('Link width for:', link.type); // Use link to avoid warning
          return timeRange && currentTimestamp ? 1 : 2;
        }}
        linkOpacity={(link: any) => {
          // Reduce opacity when time-aware filtering is active
          console.log('Link opacity for:', link.type); // Use link to avoid warning
          return timeRange && currentTimestamp ? 0.6 : 1.0;
        }}
      />
    </Box>
  );
}

export default EvolutionGraph;


