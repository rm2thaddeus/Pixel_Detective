'use client';

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Box, Text, VStack, HStack, Button, Slider, SliderTrack, SliderFilledTrack, SliderThumb } from '@chakra-ui/react';

interface Commit {
  hash: string;
  timestamp: string;
  message: string;
  author: string;
  files: FileChange[];
}

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  size: number;
  type: 'code' | 'document' | 'config' | 'other';
}

interface FileLifecycle {
  path: string;
  created_at: string;
  deleted_at?: string;
  modifications: number;
  current_size: number;
  type: 'code' | 'document' | 'config' | 'other';
  evolution_history: FileEvolution[];
}

interface FileEvolution {
  commit_hash: string;
  timestamp: string;
  action: 'created' | 'modified' | 'deleted';
  size: number;
  color: string;
}

interface TemporalEvolutionGraphProps {
  commits: Commit[];
  fileLifecycles: FileLifecycle[];
  currentTimeIndex: number;
  isPlaying: boolean;
  onTimeChange: (index: number) => void;
  width?: number;
  height?: number;
}

export default function TemporalEvolutionGraph({
  commits,
  fileLifecycles,
  currentTimeIndex,
  isPlaying,
  onTimeChange,
  width = 1200,
  height = 600,
}: TemporalEvolutionGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  // Debug logging
  useEffect(() => {
    console.log('TemporalEvolutionGraph: Props received', {
      commitsLength: commits.length,
      fileLifecyclesLength: fileLifecycles.length,
      currentTimeIndex,
      isPlaying,
      width,
      height
    });
  }, [commits, fileLifecycles, currentTimeIndex, isPlaying, width, height]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !svgRef.current || !commits.length || !fileLifecycles.length) {
      console.log('TemporalEvolutionGraph: Missing data', { 
        mounted, 
        commitsLength: commits.length, 
        fileLifecyclesLength: fileLifecycles.length 
      });
      return;
    }

    console.log('TemporalEvolutionGraph: Rendering with', { 
      commits: commits.length, 
      fileLifecycles: fileLifecycles.length,
      currentTimeIndex,
      isPlaying 
    });

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 20, right: 20, bottom: 60, left: 20 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const g = svg
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Color schemes for different file types
    const fileTypeColors = {
      code: '#3b82f6',
      document: '#10b981',
      config: '#f59e0b',
      other: '#6b7280'
    };

    // Get current commit and visible files
    const currentCommit = commits[currentTimeIndex];
    if (!currentCommit) {
      console.error('TemporalEvolutionGraph: No current commit found at index', currentTimeIndex);
      return;
    }

    const visibleFiles = fileLifecycles.filter(file => {
      try {
        const createdBefore = new Date(file.created_at) <= new Date(currentCommit.timestamp);
        const notDeletedYet = !file.deleted_at || new Date(file.deleted_at) > new Date(currentCommit.timestamp);
        return createdBefore && notDeletedYet;
      } catch (error) {
        console.warn('TemporalEvolutionGraph: Error filtering file', file.path, error);
        return false;
      }
    });

    console.log('TemporalEvolutionGraph: Visible files', visibleFiles.length);

    // Create commit backbone (vertical line)
    const commitX = innerWidth / 2;
    g.append("line")
      .attr("x1", commitX)
      .attr("y1", 0)
      .attr("x2", commitX)
      .attr("y2", innerHeight)
      .attr("stroke", "#8b5cf6")
      .attr("stroke-width", 3)
      .attr("opacity", 0.8);

    // Add commit node
    const commitNode = g.append("g")
      .attr("class", "commit-node")
      .attr("transform", `translate(${commitX}, ${innerHeight * 0.1})`);

    commitNode.append("circle")
      .attr("r", 15)
      .attr("fill", "#8b5cf6")
      .attr("stroke", "#fff")
      .attr("stroke-width", 2);

    // Pulsing animation for current commit
    if (isPlaying) {
      commitNode.select("circle")
        .transition()
        .duration(1000)
        .attr("r", 20)
        .transition()
        .duration(1000)
        .attr("r", 15)
        .on("end", function repeat() {
          if (isPlaying) {
            d3.select(this)
              .transition()
              .duration(1000)
              .attr("r", 20)
              .transition()
              .duration(1000)
              .attr("r", 15)
              .on("end", repeat);
          }
        });
    }

    // Add commit info
    commitNode.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", -25)
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .attr("fill", "#8b5cf6")
      .text(currentCommit.hash.substring(0, 8));

    commitNode.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", -10)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(new Date(currentCommit.timestamp).toLocaleDateString());

    // Create file dendrograms
    const fileSpacing = innerHeight / Math.max(visibleFiles.length, 1);
    
    visibleFiles.forEach((file, index) => {
      const fileY = innerHeight * 0.3 + (index * fileSpacing);
      const fileX = commitX + (index % 2 === 0 ? -100 : 100);
      
      const fileGroup = g.append("g")
        .attr("class", "file-group")
        .attr("transform", `translate(${fileX}, ${fileY})`);

      // Get file state at current commit
      const currentEvolution = file.evolution_history.find(ev => 
        ev.commit_hash === currentCommit.hash
      ) || file.evolution_history[file.evolution_history.length - 1];

      if (!currentEvolution) {
        console.warn('TemporalEvolutionGraph: No evolution data for file', file.path);
        return;
      }

      console.log('TemporalEvolutionGraph: File evolution', file.path, currentEvolution);

      // File node size based on current size and modifications
      const baseSize = Math.max(8, Math.min(25, Math.sqrt(currentEvolution.size) / 10));
      const modificationMultiplier = 1 + (file.modifications * 0.1);
      const nodeSize = baseSize * modificationMultiplier;

      // File node color based on type and modification count
      const baseColor = fileTypeColors[file.type];
      const modificationIntensity = Math.min(1, file.modifications / 10);
      const nodeColor = d3.interpolate(baseColor, '#ef4444')(modificationIntensity);

      // File node
      const fileNode = fileGroup.append("circle")
        .attr("r", nodeSize)
        .attr("fill", nodeColor)
        .attr("stroke", "#fff")
        .attr("stroke-width", 2)
        .attr("opacity", currentEvolution.action === 'deleted' ? 0.3 : 1);

      // Death animation for deleted files
      if (currentEvolution.action === 'deleted') {
        fileNode
          .transition()
          .duration(2000)
          .attr("r", nodeSize * 2)
          .attr("opacity", 0)
          .transition()
          .duration(500)
          .attr("r", 0);
      }

      // Growth animation for modified files
      if (currentEvolution.action === 'modified' && isPlaying) {
        fileNode
          .transition()
          .duration(500)
          .attr("r", nodeSize * 1.2)
          .transition()
          .duration(500)
          .attr("r", nodeSize);
      }

      // Connection line to commit
      g.append("line")
        .attr("x1", commitX)
        .attr("y1", innerHeight * 0.1)
        .attr("x2", fileX)
        .attr("y2", fileY)
        .attr("stroke", nodeColor)
        .attr("stroke-width", 2)
        .attr("opacity", 0.6);

      // File label
      fileGroup.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", nodeSize + 15)
        .attr("font-size", "10px")
        .attr("fill", "#333")
        .text(file.path.split('/').pop());

      // File stats
      fileGroup.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", nodeSize + 25)
        .attr("font-size", "8px")
        .attr("fill", "#666")
        .text(`${currentEvolution.size} bytes`);

      // Modification count indicator
      if (file.modifications > 0) {
        fileGroup.append("circle")
          .attr("cx", nodeSize * 0.7)
          .attr("cy", -nodeSize * 0.7)
          .attr("r", 6)
          .attr("fill", "#ef4444")
          .attr("stroke", "#fff")
          .attr("stroke-width", 1);

        fileGroup.append("text")
          .attr("x", nodeSize * 0.7)
          .attr("y", -nodeSize * 0.7)
          .attr("text-anchor", "middle")
          .attr("dy", "0.3em")
          .attr("font-size", "8px")
          .attr("fill", "#fff")
          .attr("font-weight", "bold")
          .text(file.modifications.toString());
      }
    });

    // Add timeline controls
    const controlsGroup = g.append("g")
      .attr("class", "timeline-controls")
      .attr("transform", `translate(0, ${innerHeight + 10})`);

    controlsGroup.append("text")
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .text(`Commit ${currentTimeIndex + 1} of ${commits.length}`);

    controlsGroup.append("text")
      .attr("x", 0)
      .attr("y", 15)
      .attr("font-size", "10px")
      .attr("fill", "#666")
      .text(`${visibleFiles.length} files visible`);

    // Add evolution legend
    const legendGroup = g.append("g")
      .attr("class", "evolution-legend")
      .attr("transform", `translate(${innerWidth - 150}, 10)`);

    const legendItems = [
      { color: fileTypeColors.code, label: 'Code' },
      { color: fileTypeColors.document, label: 'Document' },
      { color: fileTypeColors.config, label: 'Config' },
      { color: fileTypeColors.other, label: 'Other' }
    ];

    legendItems.forEach((item, index) => {
      const legendItem = legendGroup.append("g")
        .attr("transform", `translate(0, ${index * 20})`);

      legendItem.append("circle")
        .attr("r", 6)
        .attr("fill", item.color);

      legendItem.append("text")
        .attr("x", 15)
        .attr("y", 5)
        .attr("font-size", "10px")
        .text(item.label);
    });

  }, [mounted, commits, fileLifecycles, currentTimeIndex, isPlaying, width, height]);

  return (
    <VStack spacing={4} align="stretch">
      <Box>
        <Text fontSize="lg" fontWeight="bold" mb={2}>
          Codebase Evolution Timeline
        </Text>
        <Text fontSize="sm" color="gray.600" mb={4}>
          Watch your codebase evolve like a living organism. Each commit represents a generation, 
          files are organisms that grow, change, and die over time.
        </Text>
      </Box>

      <Box position="relative">
        <svg ref={svgRef} />
        
        {/* Timeline scrubber */}
        <Box mt={4}>
          <HStack spacing={4} align="center">
            <Text fontSize="sm" minW="60px">Timeline:</Text>
            <Slider
              value={currentTimeIndex}
              min={0}
              max={commits.length - 1}
              onChange={(value) => onTimeChange(value)}
              width="100%"
            >
              <SliderTrack>
                <SliderFilledTrack />
              </SliderTrack>
              <SliderThumb />
            </Slider>
            <Text fontSize="sm" minW="80px">
              {currentTimeIndex + 1} / {commits.length}
            </Text>
          </HStack>
        </Box>
      </Box>
    </VStack>
  );
}
