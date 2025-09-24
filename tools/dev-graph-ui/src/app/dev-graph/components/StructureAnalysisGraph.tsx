'use client';
import { Box, Button, HStack } from '@chakra-ui/react';
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
  selectedRelationType?: string;
  selectedSourceType?: string;
  selectedTargetType?: string;
  showClusters?: boolean;
  showLabels?: boolean;
  maxNodes?: number;
  useRealData?: boolean;
}

export default function StructureAnalysisGraph({
  metrics,
  height = 600,
  width = 1000,
  selectedRelationType = '',
  selectedSourceType = '',
  selectedTargetType = '',
  showClusters = true,
  showLabels = false,
  maxNodes = 1000,
  useRealData = false
}: StructureAnalysisGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);
  const [realData, setRealData] = useState<{nodes: any[], edges: any[]} | null>(null);
  const [showEdges, setShowEdges] = useState(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch real data when useRealData is true
  useEffect(() => {
    if (useRealData && mounted) {
      const fetchRealData = async () => {
        try {
          const response = await fetch(`${process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8000'}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}&include_counts=true`);
          const data = await response.json();
          setRealData({
            nodes: data.nodes || [],
            edges: data.edges || []
          });
        } catch (error) {
          console.error('Failed to fetch real graph data:', error);
        }
      };
      fetchRealData();
    }
  }, [useRealData, mounted, maxNodes]);

  useEffect(() => {
    if (!mounted || !svgRef.current || !metrics) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous content

    // Set up dimensions
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create main group with zoom behavior
    const g = svg
      .attr("width", width)
      .attr("height", height)
      .call(d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        })
      )
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Use real data if available, otherwise generate synthetic data
    let nodes, links;
    if (useRealData && realData) {
      nodes = realData.nodes.map((node: any) => ({
        id: String(node.id),
        // Prefer explicit type, otherwise use first label, fallback to 'Unknown'
        type: node.type || (Array.isArray(node.labels) ? node.labels[0] : node.labels) || 'Unknown',
        degree: 0, // Will be calculated below
        centrality: 0, // Will be calculated below
        isCentral: false, // Will be calculated below
        x: node.x || Math.random() * innerWidth,
        y: node.y || Math.random() * innerHeight
      }));
      
      const edges = (realData as any).edges || (realData as any).relations || [];
      links = edges.map((edge: any) => ({
        source: String(edge.from ?? edge.from_ ?? edge.source),
        target: String(edge.to ?? edge.target),
        type: edge.type || 'RELATES_TO'
      }));
      
      // Calculate degrees and centrality for real data
      const nodeDegrees = new Map<string, number>();
      links.forEach(link => {
        nodeDegrees.set(link.source, (nodeDegrees.get(link.source) || 0) + 1);
        nodeDegrees.set(link.target, (nodeDegrees.get(link.target) || 0) + 1);
      });
      
      nodes.forEach(node => {
        node.degree = nodeDegrees.get(node.id) || 0;
        node.centrality = node.degree / Math.max(1, nodes.length - 1);
        node.isCentral = node.degree > 5; // Consider nodes with degree > 5 as central
      });
    } else {
      // Generate synthetic data based on metrics
      nodes = generateSyntheticNodes(metrics, maxNodes);
      links = generateSyntheticLinks(nodes, metrics);
    }

    // Build node lookup
    const nodeById = new Map<string, any>();
    nodes.forEach((n: any) => nodeById.set(String(n.id), n));
    // Filter by relation and endpoint types
    let filteredLinks = links.filter((link: any) => {
      const s = nodeById.get(String(link.source));
      const t = nodeById.get(String(link.target));
      if (!s || !t) return false;
      if (selectedRelationType && String(link.type) !== selectedRelationType) return false;
      if (selectedSourceType && String(s.type) !== selectedSourceType) return false;
      if (selectedTargetType && String(t.type) !== selectedTargetType) return false;
      return true;
    });

    // Final safety pass to guarantee endpoints exist in node set
    const nodeIdSet = new Set(nodes.map((n: any) => String(n.id)));
    const safeLinks = filteredLinks.filter((l: any) => nodeIdSet.has(String(l.source)) && nodeIdSet.has(String(l.target)));
    // Keep nodes that participate in at least one safe link (or keep all if no links)
    const keepIds = new Set<string>();
    safeLinks.forEach((l: any) => { keepIds.add(String(l.source)); keepIds.add(String(l.target)); });
    const filteredNodes = nodes.filter((n: any) => keepIds.size === 0 || keepIds.has(String(n.id)));

    // Debug logging
    try {
      const nodeTypesSet = [...new Set(nodes.map((n: any) => n.type))];
      const relTypesSet = [...new Set(links.map((l: any) => l.type))];
      const safeRelTypesSet = [...new Set(safeLinks.map((l: any) => l.type))];
      console.log(`Filtering debug:`, {
        totalNodes: nodes.length,
        filteredNodes: filteredNodes.length,
        totalLinks: links.length,
        filteredLinks: filteredLinks.length,
        safeLinks: safeLinks.length,
        selectedRelationType,
        selectedSourceType,
        selectedTargetType,
        nodeTypes: nodeTypesSet,
        allRelTypes: relTypesSet,
        safeRelTypes: safeRelTypesSet
      });
    } catch (e) {
      console.error('Debug logging error:', e);
    }

    if (safeLinks.length === 0) {
      console.warn('StructureAnalysisGraph: no edges returned for current filters', {
        nodeCount: nodes.length,
        filteredNodes: filteredNodes.length,
        totalLinks: links.length,
        selectedRelationType,
        selectedSourceType,
        selectedTargetType,
      });
    }

    // If no nodes after filtering, show a message
    if (filteredNodes.length === 0) {
      g.append("text")
        .attr("x", innerWidth / 2)
        .attr("y", innerHeight / 2)
        .attr("text-anchor", "middle")
        .attr("font-size", "16px")
        .attr("fill", "#666")
        .text("No nodes match the current filter criteria");
      return;
    }

    // Create force simulation
    const simulation = d3.forceSimulation(filteredNodes)
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(innerWidth / 2, innerHeight / 2))
      .force("collision", d3.forceCollide().radius(20));

    // Only add link force if there are valid links
    if (safeLinks.length > 0) {
      simulation.force("link", d3.forceLink(safeLinks).id((d: any) => String(d.id)).distance(50));
    }

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
      .data(safeLinks)
      .enter().append("line")
      .attr("stroke", (d: any) => linkColorScale(d.type) || '#999')
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 1)
      .style("display", showEdges ? "block" : "none");

    // Create nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(filteredNodes)
      .enter().append("circle")
      .attr("r", (d: any) => Math.max(5, Math.min(20, (d.degree || 1) * 2 + 5)))
      .attr("fill", (d: any) => nodeColorScale(d.type) || "#999")
      .attr("stroke", (d: any) => d.isCentral ? "#ff6b6b" : "#fff")
      .attr("stroke-width", (d: any) => d.isCentral ? 3 : 1)
      .attr("opacity", 0.8)
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
          const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
          const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
          
          if (sourceId === d.id) connectedNodes.add(targetId);
          if (targetId === d.id) connectedNodes.add(sourceId);
        });

        node
          .attr("opacity", (n: any) => 
            n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3);

        link
          .attr("opacity", (l: any) => {
            const sourceId = typeof l.source === 'string' ? l.source : l.source?.id;
            const targetId = typeof l.target === 'string' ? l.target : l.target?.id;
            return sourceId === d.id || targetId === d.id ? 1 : 0.1;
          });

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

    // Start the simulation
    simulation.alpha(1).restart();

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

    // Add status indicator
    const statusGroup = g.append("g")
      .attr("class", "status")
      .attr("transform", `translate(20, 20)`);

    statusGroup.append("rect")
      .attr("width", 200)
      .attr("height", 40)
      .attr("fill", "rgba(255,255,255,0.9)")
      .attr("stroke", "#ddd")
      .attr("rx", 4);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 20)
      .attr("font-size", "12px")
      .attr("fill", "#333")
      .text(`Nodes: ${filteredNodes.length} | Links: ${filteredLinks.length}`);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 35)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(`From: ${selectedSourceType || 'All'} | To: ${selectedTargetType || 'All'} | Relation: ${selectedRelationType || 'All'}`);

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
    if (showClusters && filteredNodes.length > 0) {
      // Simple clustering visualization - draw circles around dense areas
      const clusters = identifyClusters(filteredNodes, filteredLinks);
      
      clusters.forEach((cluster, index) => {
        if (cluster.length > 1) { // Only show clusters with more than 1 node
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
        }
      });
    }

  }, [mounted, metrics, height, width, selectedSourceType, selectedTargetType, selectedRelationType, showClusters, showLabels, maxNodes, useRealData, realData, showEdges]);

  useEffect(() => {
    if (!svgRef.current) return;
    d3.select(svgRef.current)
      .selectAll('g.links line')
      .style('display', showEdges ? 'block' : 'none');
  }, [showEdges]);

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
        // Handle both string IDs and object references
        const sourceId = typeof link.source === 'string' ? link.source : link.source?.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target?.id;
        
        if (sourceId === nodeId && targetId && !visited.has(targetId)) {
          dfs(targetId, cluster);
        }
        if (targetId === nodeId && sourceId && !visited.has(sourceId)) {
          dfs(sourceId, cluster);
        }
      });
    };
    
    nodes.forEach(node => {
      if (!visited.has(node.id)) {
        const cluster = [];
        dfs(node.id, cluster);
        if (cluster.length > 1) { // Only show clusters with more than 1 node
          clusters.push(cluster);
        }
      }
    });
    
    return clusters;
  };

  if (!mounted || (useRealData && !realData)) {
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
        {useRealData ? 'Loading real graph data...' : 'Loading structure visualization...'}
      </Box>
    );
  }

  return (
    <Box position="relative" style={{ height, width, minHeight: height, minWidth: width }}>
      <Box position="absolute" top="12px" right="16px" zIndex={1}>
        <HStack spacing={2}>
          <Button size="xs" variant={showEdges ? 'solid' : 'outline'} onClick={() => setShowEdges(!showEdges)}>
            {showEdges ? 'Hide edges' : 'Show edges'}
          </Button>
        </HStack>
      </Box>
      <svg
        ref={svgRef}
        style={{
          height: '100%',
          width: '100%',
          minHeight: height,
          minWidth: width,
        }}
      />
    </Box>
  );
}
