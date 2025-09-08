'use client';
import { Box, Text, VStack, HStack, Button } from '@chakra-ui/react';
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
  modifications: number;
}

interface CommitNode {
  hash: string;
  message: string;
  timestamp: string;
  author_name: string;
  files_changed: string[];
  x: number;
  y: number;
}

interface EvolutionSnapshot {
  timestamp: string;
  commit_hash: string;
  files: FileNode[];
  branches: string[];
  active_developers: string[];
  commit: CommitNode;
}

interface BiologicalEvolutionGraphProps {
  snapshot: EvolutionSnapshot;
  height?: number;
  width?: number;
  showLabels?: boolean;
  enableAnimation?: boolean;
  previousSnapshot?: EvolutionSnapshot;
  onPlayPause?: () => void;
  onNext?: () => void;
  onPrevious?: () => void;
  isPlaying?: boolean;
  currentIndex?: number;
  totalSnapshots?: number;
}

export default function BiologicalEvolutionGraph({
  snapshot,
  height = 800,
  width = 1200,
  showLabels = true,
  enableAnimation = true,
  previousSnapshot,
  onPlayPause,
  onNext,
  onPrevious,
  isPlaying = false,
  currentIndex = 0,
  totalSnapshots = 1
}: BiologicalEvolutionGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !svgRef.current || !snapshot) return;

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

    // Enhanced color schemes for biological evolution
    const fileTypeColors: Record<string, string> = {
      'code': '#3b82f6',      // Vibrant blue for code organisms
      'doc': '#10b981',       // Green for documentation
      'config': '#f59e0b',    // Amber for configuration
      'test': '#8b5cf6'       // Purple for tests
    };

    const statusColors: Record<string, string> = {
      'alive': '#10b981',     // Healthy green for living files
      'modified': '#3b82f6',  // Blue for actively changing files
      'deleted': '#ef4444'    // Red for dying/dead files
    };

    // Evolution state colors
    const evolutionColors: Record<string, string> = {
      'birth': '#22c55e',     // Bright green for newly created files
      'growth': '#3b82f6',    // Blue for growing files
      'mutation': '#f59e0b',  // Orange for significant changes
      'death': '#ef4444'      // Red for deletion
    };

    // Create evolutionary backbone (tree of life structure)
    const backboneX = innerWidth / 2;
    const backboneY = 50;
    const branchLength = 150;
    
    // Create commit tree backbone - show progression of commits over time
    const commitTreeGroup = g.append("g")
      .attr("class", "commit-tree")
      .attr("transform", `translate(50, 50)`);

    // Draw the main timeline backbone (horizontal for temporal progression)
    const timelineLength = innerWidth - 100;
    const commitSpacing = Math.min(timelineLength / Math.max(totalSnapshots, 1), 150);
    
    // Main timeline trunk
    commitTreeGroup.append("line")
      .attr("x1", 0)
      .attr("y1", 50)
      .attr("x2", commitSpacing * (currentIndex + 1))
      .attr("y2", 50)
      .attr("stroke", "#8b5cf6")
      .attr("stroke-width", 4)
      .attr("opacity", 0.8)
      .attr("stroke-linecap", "round");

    // Draw all commit nodes up to current point (showing evolution history)
    for (let i = 0; i <= currentIndex; i++) {
      const commitX = i * commitSpacing;
      const commitY = 50;
      const isCurrentCommit = i === currentIndex;
      
      const commitNodeGroup = commitTreeGroup.append("g")
        .attr("class", `commit-node-${i}`)
        .attr("transform", `translate(${commitX}, ${commitY})`);

      // Commit node circle
      const commitCircle = commitNodeGroup.append("circle")
        .attr("r", isCurrentCommit ? 25 : 18)
        .attr("fill", isCurrentCommit ? "#8b5cf6" : "#6366f1")
        .attr("stroke", "#fff")
        .attr("stroke-width", 3)
        .attr("opacity", isCurrentCommit ? 1 : 0.7);

      // Add pulsing animation for current commit
      if (isCurrentCommit && enableAnimation && isPlaying) {
        commitCircle
          .transition()
          .duration(1000)
          .attr("r", 30)
          .transition()
          .duration(1000)
          .attr("r", 25)
          .on("end", function repeat() {
            if (isPlaying) {
              d3.select(this)
                .transition()
                .duration(1000)
                .attr("r", 30)
                .transition()
                .duration(1000)
                .attr("r", 25)
                .on("end", repeat);
            }
          });
      }

      // Commit hash
      commitNodeGroup.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("font-size", isCurrentCommit ? "11px" : "9px")
        .attr("fill", "white")
        .attr("font-weight", "bold")
        .text(snapshot.commit_hash.substring(0, isCurrentCommit ? 7 : 5));

      // Commit metadata (only for current commit to avoid clutter)
      if (isCurrentCommit && showLabels) {
        commitNodeGroup.append("text")
          .attr("x", 0)
          .attr("y", -35)
          .attr("font-size", "12px")
          .attr("fill", "#8b5cf6")
          .attr("font-weight", "bold")
          .attr("text-anchor", "middle")
          .text(`Generation ${currentIndex + 1}`);

        commitNodeGroup.append("text")
          .attr("x", 0)
          .attr("y", 45)
          .attr("font-size", "10px")
          .attr("fill", "#666")
          .attr("text-anchor", "middle")
          .text(snapshot.commit.message.substring(0, 20) + "...");
      }
    }

    // Create dendrograms for ALL commits up to current point (layered approach)
    for (let commitIdx = 0; commitIdx <= currentIndex; commitIdx++) {
      const commitX = 50 + (commitIdx * commitSpacing);
      const commitY = 150; // Base Y position for dendrograms
      const isCurrentCommit = commitIdx === currentIndex;
      
      // Get files for this specific commit (simulated - in real app this would come from commit data)
      let commitFiles: FileNode[] = [];
      
      if (commitIdx === currentIndex) {
        // For current commit, use actual snapshot data
        commitFiles = snapshot.files.filter(file => {
          return snapshot.commit.files_changed.includes(file.path);
        }).slice(0, 8); // Limit for visibility
        
        if (commitFiles.length === 0) {
          commitFiles = [...snapshot.files.slice(0, Math.min(6, snapshot.files.length))];
        }
      } else {
        // For previous commits, show a subset of files (simulated evolution)
        const fileCount = Math.max(2, Math.min(6, Math.floor(Math.random() * 6) + 2));
        commitFiles = snapshot.files.slice(0, fileCount).map((file, idx) => ({
          ...file,
          id: `${file.id}_${commitIdx}_${idx}`,
          path: `${file.path.split('.')[0]}_v${commitIdx}.${file.path.split('.')[1] || 'txt'}`,
          status: Math.random() > 0.8 ? 'modified' : 'alive' as any,
          modifications: Math.floor(Math.random() * 3)
        }));
      }
      
      // Ensure we have some files to show
      if (commitFiles.length === 0) {
        const now = new Date().toISOString();
        commitFiles = [
          { id: `demo1_${commitIdx}`, path: `src/main_v${commitIdx}.py`, type: 'code', status: 'alive', modifications: 1, size: 1024, commit_count: 1, created_at: now, last_modified: now },
          { id: `demo2_${commitIdx}`, path: `docs/readme_v${commitIdx}.md`, type: 'doc', status: 'alive', modifications: 0, size: 512, commit_count: 1, created_at: now, last_modified: now }
        ] as FileNode[];
      }
      
      const maxModifications = Math.max(...commitFiles.map(f => f.modifications || f.commit_count), 1);
      
      // Group files by type for this commit's dendrogram
      const filesByType = d3.group(commitFiles, d => d.type as 'code' | 'doc' | 'config' | 'test');
      const typeOrder: ('code' | 'doc' | 'config' | 'test')[] = ['code', 'doc', 'config', 'test'];
      
      // Create dendrogram branches for this commit
      const dendrogramRadius = isCurrentCommit ? 120 : 80; // Current commit has larger dendrograms
      const opacity = isCurrentCommit ? 1.0 : 0.4; // Previous commits are more transparent
      const branchAngles = typeOrder.map((_, i) => (i / typeOrder.length) * 2 * Math.PI - Math.PI/2);

      // Create dendrogram branches for this commit
      typeOrder.forEach((type, typeIndex) => {
        const typeFiles = filesByType.get(type) || [];
        if (typeFiles.length === 0) return;

        const branchAngle = branchAngles[typeIndex];
        const branchLength = Math.min(dendrogramRadius, 80 + typeFiles.length * 8);
        
        // Primary branch from commit to file type cluster
        const branchEndX = commitX + Math.cos(branchAngle) * branchLength;
        const branchEndY = commitY + Math.sin(branchAngle) * branchLength;

        // Main dendrogram branch
        const dendrogramBranch = g.append("line")
          .attr("x1", commitX)
          .attr("y1", commitY)
          .attr("x2", branchEndX)
          .attr("y2", branchEndY)
          .attr("stroke", fileTypeColors[type] || fileTypeColors['code'])
          .attr("stroke-width", Math.max(1, Math.min(4, typeFiles.length)))
          .attr("opacity", opacity * 0.8)
          .attr("stroke-linecap", "round")
          .attr("class", `commit-${commitIdx}-branch-${type}`);

        // Animate branch growth only for current commit
        if (enableAnimation && isCurrentCommit) {
          dendrogramBranch
            .attr("x2", commitX)
            .attr("y2", commitY)
            .transition()
            .duration(800)
            .attr("x2", branchEndX)
            .attr("y2", branchEndY);
        }

        // Type label at branch end (only for current commit to avoid clutter)
        if (showLabels && isCurrentCommit) {
          g.append("text")
            .attr("x", branchEndX)
            .attr("y", branchEndY - 8)
            .attr("font-size", "10px")
            .attr("font-weight", "bold")
            .attr("fill", fileTypeColors[type] || fileTypeColors['code'])
            .attr("text-anchor", "middle")
            .attr("opacity", opacity)
            .text(type.toUpperCase());
        }

        // Create file nodes along sub-branches from the main branch
        typeFiles.forEach((file, fileIndex) => {
          const subBranchAngle = branchAngle + (fileIndex - typeFiles.length/2) * 0.4; // Spread files around main branch
          const subBranchLength = 25 + (fileIndex % 3) * 10; // Varied lengths
          
          const fileX = branchEndX + Math.cos(subBranchAngle) * subBranchLength;
          const fileY = branchEndY + Math.sin(subBranchAngle) * subBranchLength;

          // Sub-branch to file
          const subBranch = g.append("line")
            .attr("x1", branchEndX)
            .attr("y1", branchEndY)
            .attr("x2", fileX)
            .attr("y2", fileY)
            .attr("stroke", fileTypeColors[type] || fileTypeColors['code'])
            .attr("stroke-width", isCurrentCommit ? 2 : 1)
            .attr("opacity", opacity * 0.6)
            .attr("class", `commit-${commitIdx}-file-branch`);

          // Animate sub-branch growth only for current commit
          if (enableAnimation && isCurrentCommit) {
            subBranch
              .attr("x2", branchEndX)
              .attr("y2", branchEndY)
              .transition()
              .delay(300 + fileIndex * 50)
              .duration(400)
              .attr("x2", fileX)
              .attr("y2", fileY);
          }

          // File node
          const fileGroup = g.append("g")
            .attr("class", `file-node commit-${commitIdx}`)
            .attr("transform", `translate(${fileX}, ${fileY})`);

          // Calculate file size based on modifications and importance
          const baseSize = isCurrentCommit ? 7 : 5;
          const growthFactor = 1 + (file.modifications || file.commit_count) / maxModifications;
          const fileSize = Math.min(isCurrentCommit ? 15 : 10, Math.max(4, baseSize * Math.sqrt(growthFactor)));

          // Determine file evolution state and color
          let fileColor = fileTypeColors[type] || fileTypeColors['code'];
          let evolutionState = 'alive';
          
          if (file.status === 'deleted') {
            evolutionState = 'death';
            fileColor = evolutionColors['death'];
          } else if (file.status === 'modified') {
            evolutionState = 'growth';
            fileColor = evolutionColors['growth'];
          } else if (previousSnapshot && !previousSnapshot.files.find(f => f.path === file.path)) {
            evolutionState = 'birth';
            fileColor = evolutionColors['birth'];
          }

          // File circle
          const fileCircle = fileGroup.append("circle")
            .attr("r", fileSize)
            .attr("fill", fileColor)
            .attr("stroke", "#fff")
            .attr("stroke-width", isCurrentCommit ? 2 : 1)
            .attr("opacity", (file.status === 'deleted' ? 0.3 : 0.7) * opacity)
            .attr("class", `file-circle-${evolutionState}`);

          // Animate file appearance only for current commit
          if (enableAnimation && isCurrentCommit) {
            fileCircle
              .attr("r", 0)
              .attr("opacity", 0)
              .transition()
              .delay(600 + fileIndex * 80)
              .duration(600)
              .attr("r", fileSize)
              .attr("opacity", (file.status === 'deleted' ? 0.3 : 0.7) * opacity)
              .ease(d3.easeBounce);
          }

          // File evolution animations (only for current commit)
          if (enableAnimation && isPlaying && isCurrentCommit) {
            if (evolutionState === 'growth') {
              fileCircle
                .transition()
                .duration(800)
                .attr("r", fileSize * 1.2)
                .transition()
                .duration(800)
                .attr("r", fileSize);
            } else if (evolutionState === 'death') {
              // Death explosion
              for (let i = 0; i < 4; i++) {
                const angle = (i / 4) * 2 * Math.PI;
                const particle = fileGroup.append("circle")
                  .attr("r", 1)
                  .attr("fill", evolutionColors['death'])
                  .attr("opacity", 0.8 * opacity)
                  .transition()
                  .duration(800)
                  .attr("cx", Math.cos(angle) * 20)
                  .attr("cy", Math.sin(angle) * 20)
                  .attr("opacity", 0)
                  .attr("r", 0);
              }
            }
          }

          // File label (only for current commit and important files)
          if (showLabels && isCurrentCommit && fileIndex < 3) {
            const fileName = file.path.split('/').pop() || file.path;
            fileGroup.append("text")
              .attr("x", 0)
              .attr("y", fileSize + 10)
              .attr("font-size", "7px")
              .attr("fill", "#333")
              .attr("text-anchor", "middle")
              .attr("opacity", opacity)
              .text(fileName.length > 6 ? fileName.substring(0, 6) + "..." : fileName);
          }

          // Modification indicator (only for current commit)
          if (file.modifications > 0 && isCurrentCommit) {
            fileGroup.append("circle")
              .attr("cx", fileSize * 0.6)
              .attr("cy", -fileSize * 0.6)
              .attr("r", 3)
              .attr("fill", evolutionColors['mutation'])
              .attr("stroke", "#fff")
              .attr("stroke-width", 1)
              .attr("opacity", opacity);

            fileGroup.append("text")
              .attr("x", fileSize * 0.6)
              .attr("y", -fileSize * 0.6)
              .attr("text-anchor", "middle")
              .attr("dy", "0.3em")
              .attr("font-size", "5px")
              .attr("fill", "#fff")
              .attr("font-weight", "bold")
              .attr("opacity", opacity)
              .text(file.modifications > 9 ? "9+" : file.modifications.toString());
          }
        });
      });
    } // End of commit loop

    // Add evolutionary timeline
    const timelineGroup = g.append("g")
      .attr("class", "evolution-timeline")
      .attr("transform", `translate(0, ${innerHeight - 40})`);

    // Timeline background
    timelineGroup.append("rect")
      .attr("x", 0)
      .attr("y", -10)
      .attr("width", innerWidth)
      .attr("height", 20)
      .attr("fill", "#f8fafc")
      .attr("stroke", "#e2e8f0")
      .attr("stroke-width", 1)
      .attr("rx", 10);

    // Progress indicator
    if (totalSnapshots > 1) {
      const progressWidth = (innerWidth * (currentIndex + 1)) / totalSnapshots;
      timelineGroup.append("rect")
        .attr("x", 0)
        .attr("y", -10)
        .attr("width", progressWidth)
        .attr("height", 20)
        .attr("fill", "#8b5cf6")
        .attr("opacity", 0.3)
        .attr("rx", 10);
    }

    // Evolutionary moment marker
    timelineGroup.append("text")
      .attr("x", innerWidth / 2)
      .attr("y", 25)
      .attr("font-size", "11px")
      .attr("fill", "#666")
      .attr("text-anchor", "middle")
      .text(`Evolution Point: ${new Date(snapshot.timestamp).toLocaleDateString()} • Generation ${currentIndex + 1}/${totalSnapshots}`);

    // Add ecosystem statistics
    const ecosystemGroup = g.append("g")
      .attr("class", "ecosystem-stats")
      .attr("transform", `translate(${innerWidth - 220}, 20)`);

    // Background panel (larger to accommodate more stats)
    ecosystemGroup.append("rect")
      .attr("x", -10)
      .attr("y", -10)
      .attr("width", 200)
      .attr("height", 130)
      .attr("fill", "#f8fafc")
      .attr("stroke", "#e2e8f0")
      .attr("stroke-width", 1)
      .attr("rx", 8)
      .attr("opacity", 0.95);

    // Title
    ecosystemGroup.append("text")
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .attr("fill", "#2d3748")
      .text("🧬 Ecosystem Status");

    const stats = [
      { label: "🌳 Tree Generations", value: currentIndex + 1, color: "#8b5cf6" },
      { label: "📁 Total Branches", value: (currentIndex + 1) * 4, color: "#3b82f6" },
      { label: "🌱 Active Files", value: snapshot.files.filter(f => f.status === 'modified').length, color: "#10b981" },
      { label: "💀 Extinct Files", value: snapshot.files.filter(f => f.status === 'deleted').length, color: "#ef4444" },
      { label: "👨‍🔬 Contributors", value: snapshot.active_developers.length, color: "#6366f1" }
    ];

    stats.forEach((stat, index) => {
      const statGroup = ecosystemGroup.append("g")
        .attr("transform", `translate(0, ${(index + 1) * 18})`);

      statGroup.append("text")
        .attr("font-size", "10px")
        .attr("fill", stat.color)
        .attr("font-weight", "500")
        .text(`${stat.label}: ${stat.value}`);
    });
    
    // Add commit tree explanation
    ecosystemGroup.append("text")
      .attr("x", 0)
      .attr("y", 120)
      .attr("font-size", "8px")
      .attr("fill", "#9ca3af")
      .attr("font-style", "italic")
      .text("Layered dendrograms show evolution over time");

  }, [mounted, snapshot, height, width, showLabels, enableAnimation, previousSnapshot, isPlaying, currentIndex, totalSnapshots]);

  if (!mounted) {
    return (
      <VStack spacing={4}>
      <Box 
        height={height} 
        width={width} 
        borderWidth="1px" 
        borderRadius="md" 
        display="flex" 
        alignItems="center" 
        justifyContent="center"
          bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
          color="white"
      >
          <VStack spacing={3}>
            <Text fontSize="lg">🧬 Initializing Evolution...</Text>
            <Text fontSize="sm" opacity={0.8}>Preparing biological visualization</Text>
          </VStack>
      </Box>
      </VStack>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Evolution Header */}
      <Box>
        <Text fontSize="lg" fontWeight="bold" color="#8b5cf6" mb={2}>
          🧬 Codebase Evolution Timeline
        </Text>
        <Text fontSize="sm" color="gray.600" mb={2}>
          Watch your codebase evolve through a temporal commit tree. Each commit node grows dendrograms 
          showing the files that were changed, creating a living history of your project's evolution.
        </Text>
        <Text fontSize="xs" color="gray.500" fontStyle="italic" mb={4}>
          🌳 Each generation adds a new commit node to the tree, with file dendrograms showing what changed.
        </Text>
      </Box>

      {/* Playback Controls */}
      {(onPlayPause || onNext || onPrevious) && (
        <HStack spacing={4} justify="center" py={2}>
          {onPrevious && (
            <Button 
              onClick={onPrevious} 
              size="sm" 
              variant="outline"
              isDisabled={currentIndex === 0}
            >
              ⏮️ Previous Generation
            </Button>
          )}
          {onPlayPause && (
            <Button 
              onClick={onPlayPause} 
              colorScheme="purple" 
              size="sm"
            >
              {isPlaying ? '⏸️ Pause Evolution' : '▶️ Play Evolution'}
            </Button>
          )}
          {onNext && (
            <Button 
              onClick={onNext} 
              size="sm" 
              variant="outline"
              isDisabled={currentIndex === totalSnapshots - 1}
            >
              Next Generation ⏭️
            </Button>
          )}
        </HStack>
      )}

      {/* Evolution Visualization */}
      <Box 
        style={{ height, width, minHeight: height, minWidth: width }}
        border="1px solid"
        borderColor="gray.200"
        borderRadius="md"
        overflow="hidden"
        bg="linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        position="relative"
      >
      <svg 
        ref={svgRef} 
        style={{ 
          height: '100%', 
          width: '100%', 
          minHeight: height, 
            minWidth: width,
            background: 'radial-gradient(ellipse at center, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)'
          }} 
        />
        
        {/* Evolution Status Overlay */}
        <Box
          position="absolute"
          top={2}
          left={2}
          bg="rgba(255,255,255,0.9)"
          px={3}
          py={1}
          borderRadius="md"
          fontSize="xs"
          fontWeight="bold"
          color="purple.600"
        >
          {isPlaying ? '🔄 Evolution in Progress...' : '⏸️ Evolution Paused'}
        </Box>
    </Box>
    </VStack>
  );
}