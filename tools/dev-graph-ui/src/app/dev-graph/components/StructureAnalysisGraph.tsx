'use client';
import { Box } from '@chakra-ui/react';
import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface NodeType {
  type: string;
  count: number;
  color: string;
}

interface RelationType {
  type: string;
  count: number;
  color: string;
}

interface CentralNode {
  id: string;
  type: string;
  centrality: number;
  degree: number;
}

interface StructureMetrics {
  total_nodes: number;
  total_relations: number;
  node_types: NodeType[];
  relation_types: RelationType[];
  clustering_coefficient: number;
  average_path_length: number;
  density: number;
  modularity: number;
  central_nodes: CentralNode[];
}

interface StructureAnalysisGraphProps {
  metrics: StructureMetrics;
  height?: number;
  width?: number;
  selectedNodeType?: string;
  selectedRelationType?: string;
  showClusters?: boolean;
  showLabels?: boolean;
  maxNodes?: number;
}

export default function StructureAnalysisGraph({
  metrics,
  height = 600,
  width = 1000,
  selectedNodeType = '',
  selectedRelationType = '',
  showClusters = true,
  showLabels = false,
  maxNodes = 1000
}: StructureAnalysisGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !svgRef.current || !metrics) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous content

    // Set up dimensions
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create main group
    const g = svg
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Generate synthetic data based on metrics
    const nodes = generateSyntheticNodes(metrics, maxNodes);
    const links = generateSyntheticLinks(nodes, metrics);

    // Filter data based on selections
    const filteredNodes = selectedNodeType 
      ? nodes.filter(d => d.type === selectedNodeType)
      : nodes;
    
    const filteredLinks = selectedRelationType
      ? links.filter(d => d.type === selectedRelationType)
      : links;

    // Create force simulation
    const simulation = d3.forceSimulation(filteredNodes)
      .force("link", d3.forceLink(filteredLinks).id((d: any) => d.id).distance(50))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(innerWidth / 2, innerHeight / 2))
      .force("collision", d3.forceCollide().radius(20));

    // Color scales
    const nodeColorScale = d3.scaleOrdinal()
      .domain(metrics.node_types.map(nt => nt.type))
      .range(metrics.node_types.map(nt => nt.color));

    const linkColorScale = d3.scaleOrdinal()
      .domain(metrics.relation_types.map(rt => rt.type))
      .range(metrics.relation_types.map(rt => rt.color));

    // Create links
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(filteredLinks)
      .enter().append("line")
      .attr("stroke", (d: any) => linkColorScale(d.type))
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1);

    // Create nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(filteredNodes)
      .enter().append("circle")
      .attr("r", (d: any) => Math.max(3, Math.min(15, d.degree / 2)))
      .attr("fill", (d: any) => nodeColorScale(d.type))
      .attr("stroke", (d: any) => d.isCentral ? "#ff6b6b" : "#fff")
      .attr("stroke-width", (d: any) => d.isCentral ? 3 : 1)
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add labels if enabled
    let labels: any = null;
    if (showLabels) {
      labels = g.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(filteredNodes)
        .enter().append("text")
        .text((d: any) => d.id.length > 15 ? d.id.substring(0, 15) + "..." : d.id)
        .attr("font-size", "10px")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em");
    }

    // Add tooltips
    node
      .on("mouseover", function(event, d: any) {
        // Highlight connected nodes
        const connectedNodes = new Set();
        filteredLinks.forEach((link: any) => {
          if (link.source.id === d.id) connectedNodes.add(link.target.id);
          if (link.target.id === d.id) connectedNodes.add(link.source.id);
        });

        node
          .attr("opacity", (n: any) => 
            n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3);

        link
          .attr("opacity", (l: any) => 
            l.source.id === d.id || l.target.id === d.id ? 1 : 0.1);

        // Show tooltip
        const tooltip = g.append("g")
          .attr("class", "tooltip")
          .attr("transform", `translate(${event.x + 10}, ${event.y - 10})`);

        tooltip.append("rect")
          .attr("width", 200)
          .attr("height", 60)
          .attr("fill", "rgba(0,0,0,0.8)")
          .attr("rx", 4);

        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 20)
          .attr("fill", "white")
          .attr("font-size", "12px")
          .text(`Node: ${d.id}`);

        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 35)
          .attr("fill", "white")
          .attr("font-size", "10px")
          .text(`Type: ${d.type} | Degree: ${d.degree}`);

        tooltip.append("text")
          .attr("x", 10)
          .attr("y", 50)
          .attr("fill", "white")
          .attr("font-size", "10px")
          .text(`Centrality: ${d.centrality?.toFixed(2) || 'N/A'}`);
      })
      .on("mouseout", function() {
        // Reset opacity
        node.attr("opacity", 1);
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
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);

      if (labels) {
        labels
          .attr("x", (d: any) => d.x)
          .attr("y", (d: any) => d.y);
      }
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
    metrics.node_types.forEach((nodeType, index) => {
      const legendItem = legend.append("g")
        .attr("transform", `translate(0, ${index * 20})`);

      legendItem.append("circle")
        .attr("r", 6)
        .attr("fill", nodeColorScale(nodeType.type));

      legendItem.append("text")
        .attr("x", 15)
        .attr("y", 5)
        .attr("font-size", "12px")
        .attr("fill", "#2d3748")
        .text(`${nodeType.type} (${nodeType.count})`);
    });

    // Add clustering visualization if enabled
    if (showClusters) {
      // Simple clustering visualization - draw circles around dense areas
      const clusters = identifyClusters(filteredNodes, filteredLinks);
      
      clusters.forEach((cluster, index) => {
        const clusterGroup = g.append("g")
          .attr("class", "cluster")
          .attr("opacity", 0.3);

        const centerX = d3.mean(cluster, (d: any) => d.x) || 0;
        const centerY = d3.mean(cluster, (d: any) => d.y) || 0;
        const radius = Math.max(50, d3.max(cluster, (d: any) => 
          Math.sqrt((d.x - centerX) ** 2 + (d.y - centerY) ** 2)) || 50);

        clusterGroup.append("circle")
          .attr("cx", centerX)
          .attr("cy", centerY)
          .attr("r", radius)
          .attr("fill", "none")
          .attr("stroke", `hsl(${index * 60}, 70%, 50%)`)
          .attr("stroke-width", 2)
          .attr("stroke-dasharray", "5,5");

        clusterGroup.append("text")
          .attr("x", centerX)
          .attr("y", centerY - radius - 10)
          .attr("text-anchor", "middle")
          .attr("font-size", "12px")
          .attr("fill", `hsl(${index * 60}, 70%, 50%)`)
          .text(`Cluster ${index + 1}`);
      });
    }

  }, [mounted, metrics, height, width, selectedNodeType, selectedRelationType, showClusters, showLabels, maxNodes]);

  // Generate synthetic nodes based on metrics
  const generateSyntheticNodes = (metrics: StructureMetrics, maxNodes: number) => {
    const nodes = [];
    const centralNodeIds = new Set(metrics.central_nodes.map(n => n.id));
    
    for (let i = 0; i < Math.min(metrics.total_nodes, maxNodes); i++) {
      const nodeType = metrics.node_types[Math.floor(Math.random() * metrics.node_types.length)];
      const isCentral = centralNodeIds.has(`node-${i}`);
      
      nodes.push({
        id: `node-${i}`,
        type: nodeType.type,
        degree: isCentral ? Math.floor(Math.random() * 20) + 10 : Math.floor(Math.random() * 10),
        centrality: isCentral ? Math.random() * 0.8 + 0.2 : Math.random() * 0.2,
        isCentral,
        x: Math.random() * 800 + 100,
        y: Math.random() * 500 + 100
      });
    }
    
    return nodes;
  };

  // Generate synthetic links based on nodes and metrics
  const generateSyntheticLinks = (nodes: any[], metrics: StructureMetrics) => {
    const links = [];
    const linkCount = Math.min(metrics.total_relations, nodes.length * 2);
    
    for (let i = 0; i < linkCount; i++) {
      const source = nodes[Math.floor(Math.random() * nodes.length)];
      const target = nodes[Math.floor(Math.random() * nodes.length)];
      
      if (source.id !== target.id) {
        const relationType = metrics.relation_types[Math.floor(Math.random() * metrics.relation_types.length)];
        links.push({
          source: source.id,
          target: target.id,
          type: relationType.type
        });
      }
    }
    
    return links;
  };

  // Simple clustering algorithm
  const identifyClusters = (nodes: any[], links: any[]) => {
    const clusters = [];
    const visited = new Set();
    
    const dfs = (nodeId: string, cluster: any[]) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      
      const node = nodes.find(n => n.id === nodeId);
      if (node) cluster.push(node);
      
      // Find connected nodes
      links.forEach(link => {
        if (link.source === nodeId && !visited.has(link.target)) {
          dfs(link.target, cluster);
        }
        if (link.target === nodeId && !visited.has(link.source)) {
          dfs(link.source, cluster);
        }
      });
    };
    
    nodes.forEach(node => {
      if (!visited.has(node.id)) {
        const cluster = [];
        dfs(node.id, cluster);
        if (cluster.length > 2) { // Only show clusters with more than 2 nodes
          clusters.push(cluster);
        }
      }
    });
    
    return clusters;
  };

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
        Loading structure visualization...
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
          minWidth: width 
        }} 
      />
    </Box>
  );
}
