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
  onSvgReady?: (svg: SVGSVGElement | null) => void;
  overrideData?: { nodes: any[]; edges: any[] } | null;
  highlightFilter?: { kind: 'future-nodes' | 'future-relationships' | 'by-type'; value?: string } | null;
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
  useRealData = false,
  onSvgReady,
  overrideData = null,
  highlightFilter = null
}: StructureAnalysisGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);
  const [realData, setRealData] = useState<{nodes: any[], edges: any[]} | null>(null);
  const [showEdges, setShowEdges] = useState(true);
  const [localShowClusters, setLocalShowClusters] = useState(showClusters);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch real data when useRealData is true
  useEffect(() => {
    if (!(useRealData && mounted)) return;
    const controller = new AbortController();
    // Use direct API URL to avoid Next.js rewrite issues
    const apiUrl = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';
    const url = `${apiUrl}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}&include_counts=true`;
    (async () => {
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        setRealData({
          nodes: (data?.nodes ?? []).map((n: any) => ({ ...n, id: String(n.id) })),
          edges: data?.edges ?? []
        });
      } catch (error: any) {
        if (error?.name === 'AbortError') return;
        console.error('Failed to fetch real graph data:', error);
      }
    })();
    return () => controller.abort();
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

    // Use override data first, then real data if available, otherwise generate synthetic data
    let nodes, links;
    if (overrideData && Array.isArray(overrideData.nodes) && Array.isArray(overrideData.edges)) {
      nodes = (overrideData.nodes as any[]).map((node: any) => ({
        id: String(node.id),
        type: node.type || (Array.isArray(node.labels) ? node.labels[0] : node.labels) || 'Unknown',
        degree: 0,
        centrality: 0,
        isCentral: false,
        x: node.x || Math.random() * innerWidth,
        y: node.y || Math.random() * innerHeight
      }));
      const edges = (overrideData.edges as any[]);
      links = edges.map((edge: any) => ({
        source: String(edge.from ?? edge.source),
        target: String(edge.to ?? edge.target),
        type: edge.type || 'RELATES_TO'
      }));
      const nodeDegrees = new Map<string, number>();
      links.forEach((l: any) => {
        nodeDegrees.set(l.source, (nodeDegrees.get(l.source) || 0) + 1);
        nodeDegrees.set(l.target, (nodeDegrees.get(l.target) || 0) + 1);
      });
      nodes.forEach((n: any) => {
        n.degree = nodeDegrees.get(n.id) || 0;
        n.centrality = n.degree / Math.max(1, nodes.length - 1);
        n.isCentral = n.degree > 5;
      });
    } else if (useRealData && realData) {
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
    // Keep all nodes for now to debug edge rendering
    const filteredNodes = nodes;

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
        filteredLinks: filteredLinks.length,
        safeLinks: safeLinks.length,
        selectedRelationType,
        selectedSourceType,
        selectedTargetType,
        sampleLinks: links.slice(0, 3),
        sampleNodes: nodes.slice(0, 3)
      });
    } else {
      console.log('StructureAnalysisGraph: edges found', {
        safeLinks: safeLinks.length,
        sampleLinks: safeLinks.slice(0, 3),
        showEdges: showEdges
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
      .force("collision", d3.forceCollide().radius(20))
      .force("x", d3.forceX(innerWidth / 2).strength(0.1))
      .force("y", d3.forceY(innerHeight / 2).strength(0.1));

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

    // Debug: Log color scale information
    console.log('Color scales created', {
      nodeTypes: metrics.node_types.map(nt => nt.type),
      relationTypes: metrics.relation_types.map(rt => rt.type),
      linkColorScaleDomain: linkColorScale.domain()
    });

    // Create links
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(safeLinks)
      .enter().append("line")
      .attr("stroke", (d: any) => linkColorScale(d.type) || '#999')
      .attr("stroke-opacity", 0.8)
      .attr("stroke-width", 2)
      .style("display", showEdges ? "block" : "none");

    // Create nodes
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(filteredNodes)
      .enter().append("circle")
      .attr("r", (d: any) => Math.max(8, Math.min(25, (d.degree || 1) * 3 + 8)))
      .attr("fill", (d: any) => nodeColorScale(d.type) || "#999")
      .attr("stroke", (d: any) => {
        if (highlightFilter?.kind === 'by-type' && highlightFilter.value) {
          return String(d.type) === String(highlightFilter.value) ? "#f6e05e" : (d.isCentral ? "#ff6b6b" : "#fff");
        }
        return d.isCentral ? "#ff6b6b" : "#fff";
      })
      .attr("stroke-width", (d: any) => {
        if (highlightFilter?.kind === 'by-type' && highlightFilter.value) {
          return String(d.type) === String(highlightFilter.value) ? 4 : (d.isCentral ? 4 : 2);
        }
        return d.isCentral ? 4 : 2;
      })
      .attr("opacity", 0.9)
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add labels only when enabled (default off). Otherwise, show on hover.
    let labels: any = null;
    if (showLabels) {
      labels = g.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(filteredNodes)
        .enter().append("text")
        .text((d: any) => {
          // Show node type and a shortened ID
          const type = d.type || 'Unknown';
          const shortId = d.id.length > 8 ? d.id.substring(0, 8) + "..." : d.id;
          return `${type}: ${shortId}`;
        })
        .attr("font-size", "8px")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("fill", "#333")
        .attr("stroke", "white")
        .attr("stroke-width", 0.5);
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

        // On-demand label when labels are off
        if (!showLabels) {
          const hover = g.append('text')
            .attr('class', 'hover-label')
            .attr('x', (d as any).x)
            .attr('y', (d as any).y - 12)
            .attr('text-anchor', 'middle')
            .attr('font-size', '10px')
            .attr('fill', '#2d3748')
            .attr('stroke', 'white')
            .attr('stroke-width', 0.8)
            .text(() => {
              const type = (d as any).type || 'Unknown';
              const shortId = String((d as any).id).length > 12 ? String((d as any).id).substring(0, 12) + '…' : String((d as any).id);
              return `${type}: ${shortId}`;
            });
        }
      })
      .on("mouseout", function() {
        // Reset opacity
        node.attr("opacity", 1);
        link.attr("opacity", 0.6);
        
        // Remove tooltip
        g.selectAll(".tooltip").remove();
        g.selectAll('.hover-label').remove();
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
      // Keep hover label near node on tick
      g.selectAll('text.hover-label')
        .attr('x', (d: any) => d?.x)
        .attr('y', (d: any) => (d?.y ?? 0) - 12);
    });

    // Start the simulation with higher alpha for better spreading
    simulation.alpha(1).restart();
    
    // Let the simulation run longer to spread nodes better
    setTimeout(() => {
      simulation.alpha(0.3).restart();
    }, 2000);
    
    // Debug: Log simulation state
    console.log('Force simulation started', {
      nodeCount: filteredNodes.length,
      edgeCount: safeLinks.length,
      simulationAlpha: simulation.alpha(),
      nodePositions: filteredNodes.slice(0, 3).map(n => ({ id: n.id, x: n.x, y: n.y }))
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
      .text(`Nodes: ${filteredNodes.length} | Links: ${safeLinks.length} (${showEdges ? 'visible' : 'hidden'})`);

    statusGroup.append("text")
      .attr("x", 10)
      .attr("y", 35)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(`From: ${selectedSourceType || 'All'} | To: ${selectedTargetType || 'All'} | Relation: ${selectedRelationType || 'All'}`);

    // Add edge toggle button
    const toggleButton = statusGroup.append("rect")
      .attr("x", 10)
      .attr("y", 45)
      .attr("width", 80)
      .attr("height", 12)
      .attr("fill", showEdges ? "#4CAF50" : "#f44336")
      .attr("rx", 2)
      .style("cursor", "pointer")
      .on("click", function() {
        setShowEdges(!showEdges);
        link.style("display", showEdges ? "block" : "none");
        statusGroup.select("text").text(`Nodes: ${filteredNodes.length} | Links: ${safeLinks.length} (${showEdges ? 'visible' : 'hidden'})`);
      });

    statusGroup.append("text")
      .attr("x", 50)
      .attr("y", 54)
      .attr("font-size", "8px")
      .attr("fill", "white")
      .attr("text-anchor", "middle")
      .text(showEdges ? "Hide Edges" : "Show Edges");

    // Add cluster toggle button
    const clusterToggleButton = statusGroup.append("rect")
      .attr("x", 100)
      .attr("y", 45)
      .attr("width", 80)
      .attr("height", 12)
      .attr("fill", localShowClusters ? "#4CAF50" : "#f44336")
      .attr("rx", 2)
      .style("cursor", "pointer")
      .on("click", function() {
        setLocalShowClusters(!localShowClusters);
      });

    statusGroup.append("text")
      .attr("x", 140)
      .attr("y", 54)
      .attr("font-size", "8px")
      .attr("fill", "white")
      .attr("text-anchor", "middle")
      .text(localShowClusters ? "Hide Clusters" : "Show Clusters");

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

    // Add clustering visualization if enabled (much more subtle)
    if (localShowClusters && filteredNodes.length > 0) {
      // Simple clustering visualization - draw very subtle circles around dense areas
      const clusters = identifyClusters(filteredNodes, filteredLinks);
      
      clusters.forEach((cluster, index) => {
        if (cluster.length > 3) { // Only show clusters with more than 3 nodes
          const clusterGroup = g.append("g")
            .attr("class", "cluster")
            .attr("opacity", 0.1); // Much more subtle

          const centerX = d3.mean(cluster, (d: any) => d.x) || 0;
          const centerY = d3.mean(cluster, (d: any) => d.y) || 0;
          const radius = Math.max(50, d3.max(cluster, (d: any) => 
            Math.sqrt((d.x - centerX) ** 2 + (d.y - centerY) ** 2)) || 50);

          clusterGroup.append("circle")
            .attr("cx", centerX)
            .attr("cy", centerY)
            .attr("r", radius)
            .attr("fill", "none")
            .attr("stroke", `hsl(${index * 60}, 30%, 70%)`)
            .attr("stroke-width", 1)
            .attr("stroke-dasharray", "10,10");

          // Only show cluster labels for very large clusters
          if (cluster.length > 5) {
            clusterGroup.append("text")
              .attr("x", centerX)
              .attr("y", centerY - radius - 5)
              .attr("text-anchor", "middle")
              .attr("font-size", "10px")
              .attr("fill", `hsl(${index * 60}, 30%, 70%)`)
              .attr("opacity", 0.7)
              .text(`Cluster ${index + 1}`);
          }
        }
      });
    }

    // Notify parent with SVG element
    if (onSvgReady) {
      onSvgReady(svgRef.current);
    }

  }, [mounted, metrics, height, width, selectedSourceType, selectedTargetType, selectedRelationType, localShowClusters, showLabels, maxNodes, useRealData, realData, showEdges, overrideData, highlightFilter, onSvgReady]);

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
