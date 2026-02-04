'use client';
import { Box } from '@chakra-ui/react';
import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface SubgraphNode {
  id: string;
  labels: string;
  type?: string;
  x: number;
  y: number;
  size: number;
  properties?: any;
}

interface SubgraphEdge {
  from: string;
  to: string;
  type: string;
  timestamp: string;
  rid: string;
  properties: string;
}

interface SubgraphData {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
  pagination: any;
  performance: any;
}

interface Commit {
  hash: string;
  message: string;
  timestamp: string;
  author_name: string;
  author_email: string;
  files_changed: string[];
}

interface TemporalSubgraphProps {
  subgraphData: SubgraphData;
  currentTimeIndex: number;
  commits: Commit[];
  height?: number;
  width?: number;
  showLabels?: boolean;
  enableAnimation?: boolean;
}

export default function TemporalSubgraph({
  subgraphData,
  currentTimeIndex,
  commits,
  height = 700,
  width = 1200,
  showLabels = true,
  enableAnimation = false
}: TemporalSubgraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !svgRef.current || !subgraphData) return;


    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Set up dimensions
    const margin = { top: 40, right: 40, bottom: 40, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create main group with zoom
    const g = svg
      .attr("width", width)
      .attr("height", height)
      .call(d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 3])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        })
      )
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Beautiful color schemes
    const nodeTypeColors = {
      'GitCommit': '#4f46e5',
      'File': '#10b981',
      'Chunk': '#f59e0b',
      'Document': '#8b5cf6'
    };

    const edgeTypeColors = {
      'TOUCHED': '#3b82f6',
      'CONTAINS_CHUNK': '#10b981',
      'CONTAINS_DOC': '#8b5cf6',
      'REFERENCES': '#f59e0b',
      'PART_OF': '#ef4444',
      'IMPLEMENTS': '#06b6d4',
      'EVOLVES_FROM': '#84cc16',
      'REFACTORED_TO': '#f97316',
      'DEPRECATED_BY': '#dc2626',
      'MENTIONS': '#6366f1'
    };

    // Get current time point
    const currentCommit = commits[currentTimeIndex];
    const currentTimestamp = currentCommit?.timestamp;

    // Filter nodes and edges based on current time
    const visibleNodes = subgraphData.nodes.filter(node => {
      // Ensure node has valid ID
      if (!node.id) {
        console.warn('TemporalSubgraph: Found node without ID:', node);
        return false;
      }
      
      // Handle labels as array or string
      const nodeLabels = Array.isArray(node.labels) ? node.labels : [node.labels];
      const isCommit = nodeLabels.includes('GitCommit');
      
      if (isCommit) {
        // Show commits up to current time
        return commits.slice(0, currentTimeIndex + 1).some(commit => 
          node.id.includes(commit.hash) || node.properties?.hash === commit.hash
        );
      }
      return true; // Show all other nodes
    });

    const visibleEdges = subgraphData.edges.filter(edge => {
      // Ensure edge has valid from/to IDs
      if (!edge.from || !edge.to) {
        return false;
      }
      
      // Show edges that connect to visible nodes
      const fromVisible = visibleNodes.some(n => n.id === edge.from);
      const toVisible = visibleNodes.some(n => n.id === edge.to);
      return fromVisible && toVisible;
    });

    // Filter edges to only include those connecting visible nodes
    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    const validEdges = visibleEdges.filter(edge => {
      const hasFrom = visibleNodeIds.has(edge.from);
      const hasTo = visibleNodeIds.has(edge.to);
      return hasFrom && hasTo;
    });

    // Safety check - ensure we have valid data
    if (visibleNodes.length === 0) {
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight / 2)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .attr("fill", "#666")
        .text("No nodes available for current time point");
      return;
    }

    // Additional validation - ensure all nodes have valid IDs
    const validatedNodes = visibleNodes.filter(node => {
      if (!node.id || typeof node.id !== 'string') {
        return false;
      }
      return true;
    });

    // Additional validation - ensure all edges have valid source/target IDs
    const validatedEdges = validEdges.filter(edge => {
      if (!edge.from || !edge.to || typeof edge.from !== 'string' || typeof edge.to !== 'string') {
        return false;
      }
      
      // Ensure both source and target nodes exist
      const sourceExists = validatedNodes.some(n => n.id === edge.from);
      const targetExists = validatedNodes.some(n => n.id === edge.to);
      
      return sourceExists && targetExists;
    });

    // Create force simulation with validated data
    let simulation;
    try {
      simulation = d3.forceSimulation(validatedNodes)
        .force("link", validatedEdges.length > 0 ? d3.forceLink(validatedEdges).id((d: any) => d.id).distance(50) : null)
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(innerWidth / 2, innerHeight / 2))
        .force("collision", d3.forceCollide().radius(20));
      
    } catch (error) {
      console.error('TemporalSubgraph: Error creating force simulation:', error);
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight / 2)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .attr("fill", "#666")
        .text("Error creating visualization");
      return;
    }

    // Create links
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(validatedEdges)
      .enter().append("line")
      .attr("stroke", (d: any) => edgeTypeColors[d.type as keyof typeof edgeTypeColors] || '#999')
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    // Create nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(validatedNodes)
      .enter().append("g")
      .attr("class", "node")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended)
      );

    // Add node circles
    node.append("circle")
      .attr("r", (d: any) => Math.max(8, Math.min(25, d.size * 10)))
      .attr("fill", (d: any) => {
        const nodeLabels = Array.isArray(d.labels) ? d.labels : [d.labels];
        const primaryLabel = nodeLabels[0];
        return nodeTypeColors[primaryLabel as keyof typeof nodeTypeColors] || '#999';
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .attr("opacity", (d: any) => {
        // Fade out nodes that are not in current commit
        const nodeLabels = Array.isArray(d.labels) ? d.labels : [d.labels];
        if (nodeLabels.includes('File') && currentCommit) {
          const isInCurrentCommit = currentCommit.files_changed.some(file => 
            d.id.includes(file) || d.properties?.path === file
          );
          return isInCurrentCommit ? 1 : 0.3;
        }
        return 1;
      });

    // Add pulsing animation for current commit
    if (enableAnimation && currentCommit) {
      const currentCommitNode = validatedNodes.find(n => {
        const nodeLabels = Array.isArray(n.labels) ? n.labels : [n.labels];
        return nodeLabels.includes('GitCommit') && 
          (n.id.includes(currentCommit.hash) || n.properties?.hash === currentCommit.hash);
      });
      
      if (currentCommitNode) {
        const commitNode = node.filter((d: any) => d.id === currentCommitNode.id);
        commitNode.select("circle")
          .transition()
          .duration(1000)
          .attr("r", (d: any) => Math.max(8, Math.min(25, d.size * 10)) * 1.3)
          .transition()
          .duration(1000)
          .attr("r", (d: any) => Math.max(8, Math.min(25, d.size * 10)));
      }
    }

    // Add labels
    if (showLabels) {
      node.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("font-size", "10px")
        .attr("fill", "white")
        .attr("font-weight", "bold")
        .text((d: any) => {
          const nodeLabels = Array.isArray(d.labels) ? d.labels : [d.labels];
          const primaryLabel = nodeLabels[0];
          
          if (primaryLabel === 'GitCommit') {
            return d.id.substring(0, 7);
          } else if (primaryLabel === 'File') {
            const fileName = d.properties?.path || d.id;
            return fileName.split('/').pop()?.substring(0, 8) || d.id.substring(0, 8);
          }
          return d.id.substring(0, 8);
        });
    }

    // Add tooltips
    node
      .on("mouseover", function(event, d: any) {
        // Highlight connected nodes
        const connectedNodes = new Set();
        validatedEdges.forEach((edge: any) => {
          if (edge.from === d.id) connectedNodes.add(edge.to);
          if (edge.to === d.id) connectedNodes.add(edge.from);
        });

        node.select("circle")
          .attr("opacity", (n: any) => 
            n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3);

        link
          .attr("opacity", (l: any) => 
            l.from === d.id || l.to === d.id ? 1 : 0.1);

        // Show tooltip
        const tooltip = g.append("g")
          .attr("class", "tooltip")
          .attr("transform", `translate(${event.x + 10}, ${event.y - 10})`);

        tooltip.append("rect")
          .attr("width", 200)
          .attr("height", 60)
          .attr("fill", "rgba(0,0,0,0.8)")
          .attr("rx", 4);

        const nodeLabels = Array.isArray(d.labels) ? d.labels : [d.labels];
        const primaryLabel = nodeLabels[0];
        
        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 20)
          .attr("fill", "white")
          .attr("font-size", "12px")
          .text(`${primaryLabel}: ${d.id}`);

        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 35)
          .attr("fill", "white")
          .attr("font-size", "10px")
          .text(`Type: ${d.type || 'Unknown'}`);

        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 50)
          .attr("fill", "white")
          .attr("font-size", "10px")
          .text(`Size: ${d.size?.toFixed(2) || 'N/A'}`);
      })
      .on("mouseout", function() {
        // Reset opacity
        node.select("circle").attr("opacity", 1);
        link.attr("opacity", 0.6);
        
        // Remove tooltip
        g.selectAll(".tooltip").remove();
      });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node
        .attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Add legend
    const legend = g.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${innerWidth - 150}, 20)`);

    // Node type legend
    Object.entries(nodeTypeColors).forEach(([type, color], index) => {
      const legendItem = legend.append("g")
        .attr("transform", `translate(0, ${index * 20})`);

      legendItem.append("circle")
        .attr("r", 6)
        .attr("fill", color);

      legendItem.append("text")
        .attr("x", 15)
        .attr("y", 5)
        .attr("font-size", "12px")
        .attr("fill", "#2d3748")
        .text(type);
    });

    // Add status indicator
    const statusGroup = g.append("g")
      .attr("class", "status")
      .attr("transform", `translate(20, 20)`);

    statusGroup.append("rect")
      .attr("width", 200)
      .attr("height", 60)
      .attr("fill", "rgba(255,255,255,0.9)")
      .attr("stroke", "#ddd")
      .attr("rx", 4);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 20)
      .attr("font-size", "12px")
      .attr("fill", "#333")
      .text(`Nodes: ${validatedNodes.length} | Edges: ${validatedEdges.length}`);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 35)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(`Time: ${currentTimeIndex + 1}/${commits.length}`);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 50)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(`Commit: ${currentCommit?.hash?.substring(0, 8) || 'N/A'}`);

  }, [mounted, subgraphData, currentTimeIndex, commits, height, width, showLabels, enableAnimation]);

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
        Loading temporal subgraph...
      </Box>
    );
  }

  return (
    <Box style={{ height, width, minHeight: height, minWidth: width }}>
      <svg 
        ref={svgRef} 
        style={{ 
          height: '100%', 
          width: '100%', 
          minHeight: height, 
          minWidth: width,
          background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)'
        }} 
      />
    </Box>
  );
}
