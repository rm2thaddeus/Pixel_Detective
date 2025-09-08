'use client';
import { Box, Text, VStack, HStack, Button, Heading } from '@chakra-ui/react';
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
  const timelineSvgRef = useRef<SVGSVGElement>(null);
  const dendrogramSvgRef = useRef<SVGSVGElement>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !timelineSvgRef.current || !dendrogramSvgRef.current || !snapshot) return;

    const timelineSvg = d3.select(timelineSvgRef.current);
    const dendrogramSvg = d3.select(dendrogramSvgRef.current);
    
    timelineSvg.selectAll("*").remove();
    dendrogramSvg.selectAll("*").remove();

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

    // Timeline dimensions (top panel)
    const timelineHeight = 120;
    const timelineWidth = width;
    
    // Dendrogram dimensions (bottom panel) - MASSIVE SPACE for downward growth
    const dendrogramHeight = height - 140; // Give maximum space to dendrograms (760px for 900px total)
    const dendrogramWidth = width;

    
    // === TIMELINE PANEL (Top) ===
    const timelineGroup = timelineSvg.append("g")
      .attr("class", "timeline-panel")
      .attr("transform", "translate(20, 20)");

    // Calculate timeline layout
    const availableTimelineWidth = timelineWidth - 40;
    const commitSpacing = Math.min(availableTimelineWidth / Math.max(totalSnapshots, 1), 80);
    
    // Timeline backbone
    timelineGroup.append("line")
      .attr("x1", 0)
      .attr("y1", 40)
      .attr("x2", commitSpacing * (currentIndex + 1))
      .attr("y2", 40)
      .attr("stroke", "#8b5cf6")
      .attr("stroke-width", 3)
      .attr("opacity", 0.6)
      .attr("stroke-linecap", "round");

    // Commit nodes in timeline
    for (let i = 0; i <= currentIndex; i++) {
      const commitX = i * commitSpacing;
      const isCurrentCommit = i === currentIndex;
      
      const commitNode = timelineGroup.append("g")
        .attr("transform", `translate(${commitX}, 40)`);

      // Commit circle
      const circle = commitNode.append("circle")
        .attr("r", isCurrentCommit ? 18 : 12)
        .attr("fill", isCurrentCommit ? "#8b5cf6" : "#a78bfa")
        .attr("stroke", "white")
        .attr("stroke-width", 2)
        .attr("opacity", isCurrentCommit ? 1 : 0.7);

      // Pulsing animation for current commit
      if (isCurrentCommit && enableAnimation && isPlaying) {
        circle
          .transition()
          .duration(1500)
          .attr("r", 22)
          .transition()
          .duration(1500)
          .attr("r", 18)
          .on("end", function repeat() {
            if (isPlaying) {
              d3.select(this)
                .transition()
                .duration(1500)
                .attr("r", 22)
                .transition()
                .duration(1500)
                .attr("r", 18)
                .on("end", repeat);
            }
          });
      }

      // Commit label
      commitNode.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .attr("font-size", isCurrentCommit ? "9px" : "7px")
        .attr("fill", "white")
        .attr("font-weight", "bold")
        .text(snapshot.commit_hash.substring(0, isCurrentCommit ? 6 : 4));

      // Generation number below
      if (showLabels) {
        commitNode.append("text")
          .attr("text-anchor", "middle")
          .attr("y", 30)
          .attr("font-size", "10px")
          .attr("fill", "#6b7280")
          .text(`G${i + 1}`);
      }
    }

    // === DENDROGRAM PANEL (Bottom) ===
    const dendrogramGroup = dendrogramSvg.append("g")
      .attr("class", "dendrogram-panel")
      .attr("transform", "translate(30, 30)");

    // Calculate dendrogram layout - use FULL available space
    const availableDendrogramWidth = dendrogramWidth - 60;
    const availableDendrogramHeight = dendrogramHeight - 60;
    
    console.log('Dendrogram panel dimensions:', {
      dendrogramWidth,
      dendrogramHeight,
      availableDendrogramWidth,
      availableDendrogramHeight
    });
    
    // Create dendrograms for ALL commits up to current point (layered approach)
    const commitWidth = availableDendrogramWidth / Math.max(currentIndex + 1, 1);
    const minCommitWidth = 120; // Minimum width per commit to ensure visibility
    
    for (let commitIdx = 0; commitIdx <= currentIndex; commitIdx++) {
      const actualCommitWidth = Math.max(commitWidth, minCommitWidth);
      const commitX = commitIdx * actualCommitWidth + actualCommitWidth / 2;
      const commitY = 50; // Position commits at top, let dendrograms grow downward
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
      
      // Create dendrogram branches for this commit - CONSTRAINED TO CANVAS
      const maxDendrogramRadius = Math.min(
        Math.max(commitWidth, minCommitWidth) * 0.3, // Smaller horizontal spread
        (availableDendrogramHeight - 100) * 0.6,     // Use 60% of available height
        dendrogramWidth * 0.15  // Constrain to 15% of canvas width
      );
      const dendrogramRadius = isCurrentCommit ? maxDendrogramRadius : maxDendrogramRadius * 0.8;
      const opacity = isCurrentCommit ? 1.0 : 0.4;
      
      // TIGHTER ANGLE SPREAD - keep within canvas bounds
      const branchAngles = typeOrder.map((_, i) => {
        // Start from 60° and spread to 120° (tighter downward arc)
        const startAngle = Math.PI * 0.33; // 60°
        const endAngle = Math.PI * 0.67;   // 120°
        return startAngle + (i / Math.max(typeOrder.length - 1, 1)) * (endAngle - startAngle);
      });
      
      console.log(`Commit ${commitIdx} dendrogram:`, {
        commitX,
        commitY,
        dendrogramRadius,
        maxDendrogramRadius,
        isCurrentCommit
      });
      
      // Create commit group in dendrogram panel
      const commitDendrogramGroup = dendrogramGroup.append("g")
        .attr("class", `commit-dendrogram-${commitIdx}`)
        .attr("transform", `translate(${commitX}, ${commitY})`);
      
      // Central commit node in dendrogram - LARGER
      commitDendrogramGroup.append("circle")
        .attr("r", isCurrentCommit ? 12 : 8)
        .attr("fill", isCurrentCommit ? "#8b5cf6" : "#a78bfa")
        .attr("stroke", "white")
        .attr("stroke-width", 2)
        .attr("opacity", opacity);

      // Create dendrogram branches for this commit - MUCH LARGER
      typeOrder.forEach((type, typeIndex) => {
        const typeFiles = filesByType.get(type) || [];
        if (typeFiles.length === 0) return;

        const branchAngle = branchAngles[typeIndex];
        const branchLength = Math.min(dendrogramRadius, 80 + typeFiles.length * 8); // Constrained branch length
        
        // Primary branch from commit to file type cluster
        const branchEndX = Math.cos(branchAngle) * branchLength;
        const branchEndY = Math.sin(branchAngle) * branchLength;

        console.log(`Branch ${type} for commit ${commitIdx}:`, {
          branchAngle,
          branchLength,
          branchEndX,
          branchEndY,
          fileCount: typeFiles.length
        });

        // Main dendrogram branch - THICKER
        const dendrogramBranch = commitDendrogramGroup.append("line")
          .attr("x1", 0)
          .attr("y1", 0)
          .attr("x2", branchEndX)
          .attr("y2", branchEndY)
          .attr("stroke", fileTypeColors[type] || fileTypeColors['code'])
          .attr("stroke-width", Math.max(2, Math.min(6, typeFiles.length + 2))) // THICKER branches
          .attr("opacity", opacity * 0.9)
          .attr("stroke-linecap", "round")
          .attr("class", `commit-${commitIdx}-branch-${type}`);

        // Animate branch growth only for current commit
        if (enableAnimation && isCurrentCommit) {
          dendrogramBranch
            .attr("x2", 0)
            .attr("y2", 0)
            .transition()
            .duration(800)
            .attr("x2", branchEndX)
            .attr("y2", branchEndY);
        }

        // Type label at branch end - LARGER and more visible
        if (showLabels && typeFiles.length > 0) {
          // Label background for better visibility
          commitDendrogramGroup.append("circle")
            .attr("cx", branchEndX)
            .attr("cy", branchEndY)
            .attr("r", 12)
            .attr("fill", "white")
            .attr("stroke", fileTypeColors[type] || fileTypeColors['code'])
            .attr("stroke-width", 2)
            .attr("opacity", opacity * 0.9);
          
          commitDendrogramGroup.append("text")
            .attr("x", branchEndX)
            .attr("y", branchEndY)
            .attr("font-size", "10px")
            .attr("font-weight", "bold")
            .attr("fill", fileTypeColors[type] || fileTypeColors['code'])
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .attr("opacity", opacity)
            .text(type.charAt(0).toUpperCase());
        }

        // Create file nodes along sub-branches from the main branch - SPREAD DOWNWARD
        typeFiles.forEach((file, fileIndex) => {
          const subBranchAngle = branchAngle + (fileIndex - typeFiles.length/2) * 0.3; // Spread files around main branch
          const subBranchLength = 20 + (fileIndex % 3) * 10; // Constrained sub-branches
          
          const fileX = branchEndX + Math.cos(subBranchAngle) * subBranchLength;
          const fileY = branchEndY + Math.sin(subBranchAngle) * subBranchLength;

          // Sub-branch to file - THICKER
          const subBranch = commitDendrogramGroup.append("line")
            .attr("x1", branchEndX)
            .attr("y1", branchEndY)
            .attr("x2", fileX)
            .attr("y2", fileY)
            .attr("stroke", fileTypeColors[type] || fileTypeColors['code'])
            .attr("stroke-width", isCurrentCommit ? 2.5 : 1.5) // THICKER sub-branches
            .attr("opacity", opacity * 0.7)
            .attr("class", `commit-${commitIdx}-file-branch`);

          // Animate sub-branch growth only for current commit
          if (enableAnimation && isCurrentCommit) {
            subBranch
              .attr("x2", branchEndX)
              .attr("y2", branchEndY)
              .transition()
              .delay(300 + fileIndex * 40)
              .duration(400)
              .attr("x2", fileX)
              .attr("y2", fileY);
          }

          // File node - MUCH LARGER
          const fileGroup = commitDendrogramGroup.append("g")
            .attr("class", `file-node commit-${commitIdx}`)
            .attr("transform", `translate(${fileX}, ${fileY})`);

          // Calculate file size - LARGER but constrained
          const baseSize = isCurrentCommit ? 8 : 6;
          const growthFactor = 1 + (file.modifications || file.commit_count) / maxModifications;
          const fileSize = Math.min(isCurrentCommit ? 15 : 12, Math.max(6, baseSize * Math.sqrt(growthFactor)));

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

          console.log(`File ${file.path}:`, {
            fileX,
            fileY,
            fileSize,
            fileColor,
            evolutionState
          });

          // File circle - MUCH LARGER and more prominent
          const fileCircle = fileGroup.append("circle")
            .attr("r", fileSize)
            .attr("fill", fileColor)
            .attr("stroke", "white")
            .attr("stroke-width", isCurrentCommit ? 3 : 2)
            .attr("opacity", (file.status === 'deleted' ? 0.6 : 0.95) * opacity)
            .attr("class", `file-circle-${evolutionState}`);
          
          // Add subtle shadow effect for depth
          fileGroup.append("circle")
            .attr("r", fileSize + 2)
            .attr("fill", "none")
            .attr("stroke", fileColor)
            .attr("stroke-width", 0.5)
            .attr("opacity", opacity * 0.3)
            .attr("stroke-dasharray", "2,2");

          // Animate file appearance only for current commit
          if (enableAnimation && isCurrentCommit) {
            fileCircle
              .attr("r", 0)
              .attr("opacity", 0)
              .transition()
              .delay(500 + fileIndex * 60)
              .duration(500)
              .attr("r", fileSize)
              .attr("opacity", (file.status === 'deleted' ? 0.5 : 0.9) * opacity)
              .ease(d3.easeBounce);
          }

          // File evolution animations (only for current commit)
          if (enableAnimation && isPlaying && isCurrentCommit) {
            if (evolutionState === 'growth') {
              fileCircle
                .transition()
                .duration(600)
                .attr("r", fileSize * 1.3)
                .transition()
                .duration(600)
                .attr("r", fileSize);
            } else if (evolutionState === 'death') {
              // Death explosion - smaller for compact layout
              for (let i = 0; i < 3; i++) {
                const angle = (i / 3) * 2 * Math.PI;
                const particle = fileGroup.append("circle")
                  .attr("r", 1)
                  .attr("fill", evolutionColors['death'])
                  .attr("opacity", 0.8 * opacity)
                  .transition()
                  .duration(600)
                  .attr("cx", Math.cos(angle) * 12)
                  .attr("cy", Math.sin(angle) * 12)
                  .attr("opacity", 0)
                  .attr("r", 0);
              }
            }
          }

          // File label - LARGER and more visible
          if (showLabels && fileIndex < 5 && fileSize > 8) {
            const fileName = file.path.split('/').pop() || file.path;
            
            // Background for label readability - LARGER
            fileGroup.append("rect")
              .attr("x", -25)
              .attr("y", fileSize + 8)
              .attr("width", 50)
              .attr("height", 14)
              .attr("fill", "white")
              .attr("stroke", fileColor)
              .attr("stroke-width", 1)
              .attr("rx", 3)
              .attr("opacity", opacity * 0.95);
            
            fileGroup.append("text")
              .attr("x", 0)
              .attr("y", fileSize + 16)
              .attr("font-size", "9px")
              .attr("fill", fileColor)
              .attr("text-anchor", "middle")
              .attr("font-weight", "bold")
              .attr("opacity", opacity)
              .text(fileName.length > 8 ? fileName.substring(0, 8) : fileName);
          }

          // Modification indicator - LARGER and more prominent
          if (file.modifications > 0 && fileSize > 8) {
            fileGroup.append("circle")
              .attr("cx", fileSize * 0.7)
              .attr("cy", -fileSize * 0.7)
              .attr("r", 6)
              .attr("fill", evolutionColors['mutation'])
              .attr("stroke", "white")
              .attr("stroke-width", 1.5)
              .attr("opacity", opacity);

            if (file.modifications <= 9) {
              fileGroup.append("text")
                .attr("x", fileSize * 0.7)
                .attr("y", -fileSize * 0.7)
                .attr("text-anchor", "middle")
                .attr("dy", "0.35em")
                .attr("font-size", "8px")
                .attr("fill", "white")
                .attr("font-weight", "bold")
                .attr("opacity", opacity)
                .text(file.modifications.toString());
            }
          }
        });
      });
    } // End of commit loop


    // Add generation label in dendrogram panel (bottom right)
    if (currentIndex >= 0) {
      dendrogramGroup.append("text")
        .attr("x", availableDendrogramWidth - 10)
        .attr("y", availableDendrogramHeight - 10)
        .attr("font-size", "11px")
        .attr("font-weight", "bold")
        .attr("fill", "#8b5cf6")
        .attr("text-anchor", "end")
        .attr("opacity", 0.7)
        .text(`Generation ${currentIndex + 1}`);
    }

  }, [mounted, snapshot, height, width, showLabels, enableAnimation, previousSnapshot, isPlaying, currentIndex, totalSnapshots]);

  if (!mounted) {
    return (
      <VStack spacing={6} align="stretch" bg="white" borderRadius="lg" p={6} boxShadow="sm">
        <Box 
          height={height} 
          width={width} 
          borderWidth="1px" 
          borderRadius="md" 
          display="flex" 
          alignItems="center" 
          justifyContent="center"
          bg="gray.50"
        >
          <VStack spacing={3}>
            <Text fontSize="lg" color="purple.600">🧬 Initializing Evolution Tree...</Text>
            <Text fontSize="sm" color="gray.600">Preparing temporal visualization</Text>
          </VStack>
        </Box>
      </VStack>
    );
  }

  return (
    <VStack spacing={6} align="stretch" bg="white" borderRadius="lg" p={6} boxShadow="sm">
      {/* Header with Controls */}
      <HStack justify="space-between" align="center">
        <VStack align="start" spacing={1}>
          <Heading size="md" color="purple.600">
            🧬 Codebase Evolution Tree
          </Heading>
          <Text fontSize="sm" color="gray.600">
            Temporal commit tree with file dendrograms showing project evolution
          </Text>
        </VStack>
        
        {/* Playback Controls */}
        {(onPlayPause || onNext || onPrevious) && (
          <HStack spacing={2}>
            {onPrevious && (
              <Button 
                onClick={onPrevious} 
                size="sm" 
                variant="outline"
                isDisabled={currentIndex === 0}
                leftIcon={<Text>⏮️</Text>}
              >
                Previous
              </Button>
            )}
            {onPlayPause && (
              <Button 
                onClick={onPlayPause} 
                colorScheme="purple" 
                size="sm"
                leftIcon={<Text>{isPlaying ? '⏸️' : '▶️'}</Text>}
              >
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
            )}
            {onNext && (
              <Button 
                onClick={onNext} 
                size="sm" 
                variant="outline"
                isDisabled={currentIndex === totalSnapshots - 1}
                rightIcon={<Text>⏭️</Text>}
              >
                Next
              </Button>
            )}
          </HStack>
        )}
      </HStack>

      {/* Progress and Stats */}
      <HStack justify="space-between" align="center" py={2} px={4} bg="gray.50" borderRadius="md">
        <HStack spacing={6}>
          <Text fontSize="sm" fontWeight="semibold">
            Generation {currentIndex + 1} of {totalSnapshots}
          </Text>
          <Text fontSize="sm" color="gray.600">
            🌳 {currentIndex + 1} Generations • 📁 {(currentIndex + 1) * 4} Branches
          </Text>
        </HStack>
        <HStack spacing={4}>
          <Text fontSize="xs" color="green.600">🌱 Active: {snapshot.files.filter(f => f.status === 'modified').length}</Text>
          <Text fontSize="xs" color="red.600">💀 Deleted: {snapshot.files.filter(f => f.status === 'deleted').length}</Text>
        </HStack>
      </HStack>

      {/* Two-Panel Layout */}
      <VStack spacing={4} align="stretch">
        {/* Top Panel: Commit Timeline */}
        <Box 
          height="120px"
          bg="white"
          border="1px solid"
          borderColor="gray.200"
          borderRadius="md"
          overflow="hidden"
          position="relative"
        >
          <Text 
            position="absolute" 
            top={2} 
            left={3} 
            fontSize="xs" 
            fontWeight="semibold" 
            color="gray.600"
            zIndex={10}
          >
            Commit Timeline
          </Text>
          <svg 
            ref={timelineSvgRef} 
            style={{ 
              width: '100%', 
              height: '100%',
              background: 'linear-gradient(90deg, #f8fafc 0%, #e2e8f0 100%)'
            }}
          />
        </Box>

        {/* Bottom Panel: Dendrograms - MASSIVE SPACE */}
        <Box 
          height={`${height - 140}px`}
          bg="white"
          border="1px solid"
          borderColor="gray.200"
          borderRadius="md"
          overflow="hidden"
          position="relative"
        >
          <Text 
            position="absolute" 
            top={2} 
            left={3} 
            fontSize="xs" 
            fontWeight="semibold" 
            color="gray.600"
            zIndex={10}
          >
            File Dendrograms • Generation {currentIndex + 1}
          </Text>
          <svg 
            ref={dendrogramSvgRef}
            style={{ 
              width: '100%', 
              height: '100%',
              background: 'radial-gradient(ellipse at center, #fafafa 0%, #f5f5f5 100%)'
            }}
          />
        </Box>
      </VStack>
    </VStack>
  );
}