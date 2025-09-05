'use client';
import { Box } from '@chakra-ui/react';
import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

interface FileNode {
  id: string;
  path: string;
  type: 'code' | 'doc' | 'config' | 'test';
  created_at: string;
  deleted_at?: string;
  last_modified: string;
  size: number;
  commit_count: number;
  status: 'alive' | 'deleted' | 'modified';
}

interface EvolutionSnapshot {
  timestamp: string;
  commit_hash: string;
  files: FileNode[];
  branches: string[];
  active_developers: string[];
}

interface BiologicalEvolutionGraphProps {
  snapshot: EvolutionSnapshot;
  height?: number;
  width?: number;
  showLabels?: boolean;
  enableAnimation?: boolean;
}

export default function BiologicalEvolutionGraph({
  snapshot,
  height = 600,
  width = 1000,
  showLabels = true,
  enableAnimation = false
}: BiologicalEvolutionGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !svgRef.current || !snapshot) return;

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

    // Color scheme for biological metaphor
    const colorScale = d3.scaleOrdinal()
      .domain(['code', 'doc', 'config', 'test'])
      .range(['#3182ce', '#38a169', '#d69e2e', '#805ad5']);

    const statusColorScale = d3.scaleOrdinal()
      .domain(['alive', 'modified', 'deleted'])
      .range(['#48bb78', '#3182ce', '#e53e3e']);

    // Create radial layout for evolutionary tree
    const centerX = innerWidth / 2;
    const centerY = innerHeight / 2;
    const maxRadius = Math.min(innerWidth, innerHeight) / 2 - 50;

    // Group files by type for better organization
    const filesByType = d3.group(snapshot.files, d => d.type);
    const typeOrder = ['code', 'doc', 'config', 'test'];
    
    let angleOffset = 0;
    const angleStep = (2 * Math.PI) / snapshot.files.length;

    // Create evolutionary tree structure
    filesByType.forEach((files, type) => {
      const typeAngleStep = (2 * Math.PI) / files.length;
      
      files.forEach((file, index) => {
        // Calculate position in evolutionary tree
        const angle = angleOffset + (index * typeAngleStep);
        const radius = Math.min(maxRadius, 50 + (file.commit_count * 20));
        
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;

        // Create file node (organism)
        const nodeGroup = g.append("g")
          .attr("class", "file-node")
          .attr("transform", `translate(${x}, ${y})`);

        // Main circle (organism body)
        const nodeCircle = nodeGroup.append("circle")
          .attr("r", Math.max(4, Math.min(12, file.size / 100)))
          .attr("fill", colorScale(file.type))
          .attr("stroke", statusColorScale(file.status))
          .attr("stroke-width", file.status === 'modified' ? 3 : 1)
          .attr("opacity", file.status === 'deleted' ? 0.5 : 1);

        // Add pulsing animation for alive files
        if (file.status === 'alive' && enableAnimation) {
          nodeCircle
            .transition()
            .duration(2000)
            .ease(d3.easeSinInOut)
            .attr("r", Math.max(4, Math.min(12, file.size / 100)) * 1.2)
            .transition()
            .duration(2000)
            .ease(d3.easeSinInOut)
            .attr("r", Math.max(4, Math.min(12, file.size / 100)));
        }

        // Add file type indicator (small inner circle)
        nodeGroup.append("circle")
          .attr("r", 2)
          .attr("fill", "white")
          .attr("opacity", 0.8);

        // Add labels if enabled
        if (showLabels) {
          const label = nodeGroup.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "1.2em")
            .attr("font-size", "10px")
            .attr("fill", "#666")
            .text(file.path.split('/').pop() || file.id);

          // Truncate long labels
          if (label.node() && label.node().getComputedTextLength() > 60) {
            const text = label.text();
            const truncated = text.substring(0, 15) + '...';
            label.text(truncated);
          }
        }

        // Add tooltip on hover
        nodeGroup
          .on("mouseover", function(event) {
            d3.select(this).select("circle")
              .transition()
              .duration(200)
              .attr("r", Math.max(4, Math.min(12, file.size / 100)) * 1.5)
              .attr("stroke-width", 3);

            // Show tooltip
            const tooltip = g.append("g")
              .attr("class", "tooltip")
              .attr("transform", `translate(${x + 20}, ${y - 20})`);

            tooltip.append("rect")
              .attr("width", 200)
              .attr("height", 80)
              .attr("fill", "rgba(0,0,0,0.8)")
              .attr("rx", 4);

            tooltip.append("text")
              .attr("x", 10)
              .attr("y", 20)
              .attr("fill", "white")
              .attr("font-size", "12px")
              .text(`File: ${file.path}`);

            tooltip.append("text")
              .attr("x", 10)
              .attr("y", 35)
              .attr("fill", "white")
              .attr("font-size", "10px")
              .text(`Type: ${file.type} | Status: ${file.status}`);

            tooltip.append("text")
              .attr("x", 10)
              .attr("y", 50)
              .attr("fill", "white")
              .attr("font-size", "10px")
              .text(`Commits: ${file.commit_count} | Size: ${Math.round(file.size)}`);

            tooltip.append("text")
              .attr("x", 10)
              .attr("y", 65)
              .attr("fill", "white")
              .attr("font-size", "10px")
              .text(`Modified: ${new Date(file.last_modified).toLocaleDateString()}`);
          })
          .on("mouseout", function() {
            d3.select(this).select("circle")
              .transition()
              .duration(200)
              .attr("r", Math.max(4, Math.min(12, file.size / 100)))
              .attr("stroke-width", file.status === 'modified' ? 3 : 1);

            // Remove tooltip
            g.selectAll(".tooltip").remove();
          });
      });

      angleOffset += files.length * typeAngleStep;
    });

    // Add evolutionary tree trunk (main branch)
    g.append("line")
      .attr("x1", centerX)
      .attr("y1", centerY + maxRadius + 20)
      .attr("x2", centerX)
      .attr("y2", centerY + maxRadius + 40)
      .attr("stroke", "#8b4513")
      .attr("stroke-width", 8);

    // Add tree roots
    for (let i = 0; i < 3; i++) {
      const rootAngle = (i * 2 * Math.PI) / 3;
      const rootLength = 30;
      g.append("line")
        .attr("x1", centerX)
        .attr("y1", centerY + maxRadius + 40)
        .attr("x2", centerX + Math.cos(rootAngle) * rootLength)
        .attr("y2", centerY + maxRadius + 40 + Math.sin(rootAngle) * rootLength)
        .attr("stroke", "#8b4513")
        .attr("stroke-width", 4);
    }

    // Add generation indicator
    g.append("text")
      .attr("x", centerX)
      .attr("y", centerY + maxRadius + 60)
      .attr("text-anchor", "middle")
      .attr("font-size", "14px")
      .attr("font-weight", "bold")
      .attr("fill", "#2d3748")
      .text(`Generation: ${snapshot.commit_hash.substring(0, 8)}`);

    // Add timestamp
    g.append("text")
      .attr("x", centerX)
      .attr("y", centerY + maxRadius + 80)
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .attr("fill", "#666")
      .text(new Date(snapshot.timestamp).toLocaleString());

    // Add legend
    const legend = g.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(${innerWidth - 150}, 20)`);

    const legendItems = [
      { type: 'code', label: 'Code Files', color: '#3182ce' },
      { type: 'doc', label: 'Documentation', color: '#38a169' },
      { type: 'config', label: 'Configuration', color: '#d69e2e' },
      { type: 'test', label: 'Tests', color: '#805ad5' }
    ];

    legendItems.forEach((item, index) => {
      const legendItem = legend.append("g")
        .attr("transform", `translate(0, ${index * 20})`);

      legendItem.append("circle")
        .attr("r", 6)
        .attr("fill", item.color);

      legendItem.append("text")
        .attr("x", 15)
        .attr("y", 5)
        .attr("font-size", "12px")
        .attr("fill", "#2d3748")
        .text(item.label);
    });

    // Add status legend
    const statusLegend = g.append("g")
      .attr("class", "status-legend")
      .attr("transform", `translate(20, 20)`);

    const statusItems = [
      { status: 'alive', label: 'Alive', color: '#48bb78' },
      { status: 'modified', label: 'Evolved', color: '#3182ce' },
      { status: 'deleted', label: 'Extinct', color: '#e53e3e' }
    ];

    statusItems.forEach((item, index) => {
      const statusItem = statusLegend.append("g")
        .attr("transform", `translate(0, ${index * 20})`);

      statusItem.append("circle")
        .attr("r", 6)
        .attr("fill", "white")
        .attr("stroke", item.color)
        .attr("stroke-width", 2);

      statusItem.append("text")
        .attr("x", 15)
        .attr("y", 5)
        .attr("font-size", "12px")
        .attr("fill", "#2d3748")
        .text(item.label);
    });

  }, [mounted, snapshot, height, width, showLabels, enableAnimation]);

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
        Loading evolution visualization...
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
