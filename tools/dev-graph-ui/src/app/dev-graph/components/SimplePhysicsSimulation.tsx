'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Box, Text, VStack, HStack, Badge, Button, useColorModeValue } from '@chakra-ui/react';

interface FileNode {
  id: string;
  path: string;
  type: 'code' | 'doc' | 'config' | 'test';
  status: 'active' | 'modified' | 'deleted' | 'new';
  modifications: number;
  commit_count: number;
  created_at: string;
  last_modified: string;
}

interface CommitNode {
  id: string;
  message: string;
  timestamp: string;
  files: FileNode[];
}

interface SimplePhysicsSimulationProps {
  commits: CommitNode[];
  currentIndex: number;
  height: number;
  width: number;
  isPlaying: boolean;
  onTimeChange?: (index: number) => void;
}

interface PhysicsFile {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  color: string;
  node: FileNode;
  commitId: string;
  age: number;
  maxAge: number;
  isAlive: boolean;
  targetX: number;
  targetY: number;
}

interface PhysicsCommit {
  id: string;
  x: number;
  y: number;
  files: PhysicsFile[];
  isActive: boolean;
  node: CommitNode;
}

export default function SimplePhysicsSimulation({
  commits,
  currentIndex,
  height,
  width,
  isPlaying,
  onTimeChange
}: SimplePhysicsSimulationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [physicsCommits, setPhysicsCommits] = useState<PhysicsCommit[]>([]);
  const [stats, setStats] = useState({
    totalFiles: 0,
    activeFiles: 0,
    deletedFiles: 0,
    currentGeneration: 0
  });

  // Color scheme for different file types and states
  const fileTypeColors = {
    code: '#3182ce',
    doc: '#38a169', 
    config: '#d69e2e',
    test: '#805ad5'
  };

  const statusColors = {
    active: '#48bb78',
    modified: '#ed8936',
    deleted: '#f56565',
    new: '#4299e1'
  };

  useEffect(() => {
    if (!canvasRef.current || commits.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Initialize physics objects - FOCUS ON EVOLUTION STORY
    const newPhysicsCommits: PhysicsCommit[] = [];
    
    // Only show the most recent commits to reduce clutter
    const maxVisibleCommits = Math.min(8, commits.length);
    const startCommitIndex = Math.max(0, commits.length - maxVisibleCommits);
    const visibleCommits = commits.slice(startCommitIndex);
    
    visibleCommits.forEach((commit, localIndex) => {
      const commitIndex = startCommitIndex + localIndex;
      
      // Position commits in a timeline across the top
      const commitX = 80 + (localIndex * (width - 160) / Math.max(visibleCommits.length - 1, 1));
      const commitY = 60;
      
      // Only show files from the most recent 3 commits to reduce clutter
      const shouldShowFiles = localIndex >= visibleCommits.length - 3;
      
      // Create file objects for this commit - BETTER CLUSTERING
      const physicsFiles: PhysicsFile[] = shouldShowFiles ? commit.files.slice(0, 15).map((file, fileIndex) => {
        // Create a more organized cluster pattern
        const clusterRadius = 40 + (fileIndex % 3) * 15; // Different cluster sizes
        const clusterAngle = (fileIndex / Math.max(commit.files.length - 1, 1)) * Math.PI * 1.2 + Math.PI * 0.4; // Wider spread
        
        const fileX = commitX + Math.cos(clusterAngle) * clusterRadius;
        const fileY = commitY + Math.sin(clusterAngle) * clusterRadius + 40;

        const fileSize = Math.max(6, Math.min(16, 6 + file.modifications * 1.5));
        const color = file.status === 'deleted' ? statusColors.deleted : fileTypeColors[file.type];

        return {
          id: file.id,
          x: fileX,
          y: fileY,
          vx: (Math.random() - 0.5) * 2, // Start with some movement
          vy: (Math.random() - 0.5) * 2,
          size: fileSize,
          color: color,
          node: file,
          commitId: commit.id,
          age: 0,
          maxAge: 600 + Math.random() * 400, // Longer lifespan
          isAlive: true,
          targetX: fileX,
          targetY: fileY
        };
      }) : [];

      newPhysicsCommits.push({
        id: commit.id,
        x: commitX,
        y: commitY,
        files: physicsFiles,
        isActive: commitIndex <= currentIndex,
        node: commit
      });
    });

    setPhysicsCommits(newPhysicsCommits);

    // Animation loop
    const animate = () => {
      if (!ctx) return;

      // Clear canvas
      ctx.fillStyle = '#f7fafc';
      ctx.fillRect(0, 0, width, height);

        // Update and draw commits - BETTER VISUAL HIERARCHY
        newPhysicsCommits.forEach((commit, index) => {
          const isCurrentCommit = index === newPhysicsCommits.length - 1;
          const isRecentCommit = index >= newPhysicsCommits.length - 3;
          
          // Draw commit node with size based on importance
          const commitSize = isCurrentCommit ? 20 : isRecentCommit ? 15 : 12;
          const commitOpacity = isCurrentCommit ? 1.0 : isRecentCommit ? 0.8 : 0.6;
          
          ctx.globalAlpha = commitOpacity;
          ctx.fillStyle = commit.isActive ? '#805ad5' : '#a0aec0';
          ctx.strokeStyle = commit.isActive ? '#553c9a' : '#718096';
          ctx.lineWidth = isCurrentCommit ? 4 : 2;
          ctx.beginPath();
          ctx.arc(commit.x, commit.y, commitSize, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();

          // Draw commit label with better visibility
          ctx.fillStyle = '#2d3748';
          ctx.font = isCurrentCommit ? 'bold 14px Arial' : '12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText(`G${commits.indexOf(commit.node) + 1}`, commit.x, commit.y + 4);
          
          // Draw connection line to next commit
          if (index < newPhysicsCommits.length - 1) {
            const nextCommit = newPhysicsCommits[index + 1];
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(commit.x + commitSize, commit.y);
            ctx.lineTo(nextCommit.x - nextCommit.files.length > 0 ? 15 : 12, nextCommit.y);
            ctx.stroke();
          }

        // Update and draw files - BETTER EVOLUTION STORY
        commit.files.forEach(file => {
          if (!file.isAlive) return;

          // Update physics - GENTLER MOVEMENT
          file.age++;
          
          // Apply gentle gravity
          file.vy += 0.03;
          
          // Apply spring force towards target for clustering
          const springForce = 0.06;
          file.vx += (file.targetX - file.x) * springForce;
          file.vy += (file.targetY - file.y) * springForce;
          
          // Apply repulsion from other files to prevent overcrowding
          commit.files.forEach(otherFile => {
            if (otherFile.id !== file.id && otherFile.isAlive) {
              const dx = file.x - otherFile.x;
              const dy = file.y - otherFile.y;
              const distance = Math.sqrt(dx * dx + dy * dy);
              const minDistance = file.size + otherFile.size + 8;
              
              if (distance < minDistance && distance > 0) {
                const force = 0.5 / (distance * distance);
                file.vx += (dx / distance) * force;
                file.vy += (dy / distance) * force;
              }
            }
          });
          
          // Apply damping
          file.vx *= 0.96;
          file.vy *= 0.96;
          
          // Update position
          file.x += file.vx;
          file.y += file.vy;
          
          // Better boundary collision - use more space
          if (file.x < file.size) {
            file.x = file.size;
            file.vx = Math.abs(file.vx) * 0.7;
          }
          if (file.x > width - file.size) {
            file.x = width - file.size;
            file.vx = -Math.abs(file.vx) * 0.7;
          }
          if (file.y < file.size + 120) {
            file.y = file.size + 120;
            file.vy = Math.abs(file.vy) * 0.7;
          }
          if (file.y > height - file.size - 20) {
            file.y = height - file.size - 20;
            file.vy = -Math.abs(file.vy) * 0.7;
          }

          // Fade out old files more gradually
          let alpha = 1;
          if (file.age > file.maxAge * 0.9) {
            alpha = 1 - (file.age - file.maxAge * 0.9) / (file.maxAge * 0.1);
          }

          // Draw file circle with movement-based effects
          ctx.globalAlpha = alpha;
          
          // Add subtle glow for moving files
          const speed = Math.sqrt(file.vx * file.vx + file.vy * file.vy);
          if (speed > 0.5) {
            ctx.shadowColor = file.color;
            ctx.shadowBlur = speed * 2;
          } else {
            ctx.shadowBlur = 0;
          }
          
          ctx.fillStyle = file.color;
          ctx.strokeStyle = file.node.status === 'deleted' ? '#e53e3e' : 'white';
          ctx.lineWidth = file.node.status === 'deleted' ? 3 : 2;
          ctx.beginPath();
          ctx.arc(file.x, file.y, file.size, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
          
          // Reset shadow
          ctx.shadowBlur = 0;

          // Draw modification count only for larger files
          if (file.node.modifications > 0 && file.size > 10) {
            ctx.fillStyle = 'white';
            ctx.font = 'bold 9px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(file.node.modifications.toString(), file.x, file.y + 3);
          }

          // Draw file name only for the largest files to reduce clutter
          if (file.size > 14) {
            const fileName = file.node.path.split('/').pop() || file.node.path;
            ctx.fillStyle = '#2d3748';
            ctx.font = 'bold 9px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(fileName.substring(0, 10), file.x, file.y + file.size + 15);
          }

          // Remove very old files
          if (file.age > file.maxAge) {
            file.isAlive = false;
          }
        });
      });

      // Reset alpha
      ctx.globalAlpha = 1;

      // Update stats - FOCUS ON VISIBLE FILES
      const visibleFiles = newPhysicsCommits
        .filter(c => c.isActive)
        .flatMap(c => c.files)
        .filter(f => f.isAlive);
      
      setStats({
        totalFiles: commits.flatMap(c => c.files).length,
        activeFiles: visibleFiles.length,
        deletedFiles: visibleFiles.filter(f => f.node.status === 'deleted').length,
        currentGeneration: currentIndex + 1
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    // Cleanup
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [commits, currentIndex, height, width]);

  // Update active commits when currentIndex changes
  useEffect(() => {
    setPhysicsCommits(prev => 
      prev.map((commit, index) => ({
        ...commit,
        isActive: index <= currentIndex
      }))
    );
  }, [currentIndex]);

  return (
    <VStack spacing={4} align="stretch">
      {/* Header */}
      <Box w="full" p={4} bg="white" borderRadius="md" border="1px solid" borderColor="gray.200">
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Text fontSize="lg" fontWeight="bold" color="gray.700">
              Simple Physics Evolution
            </Text>
            <Text fontSize="sm" color="gray.500">
              Watch your codebase evolve through simple physics • Generation {stats.currentGeneration}
            </Text>
          </VStack>
          
          <HStack spacing={4}>
            <Badge colorScheme="blue" fontSize="sm">
              {stats.activeFiles} Active Files
            </Badge>
            <Badge colorScheme="red" fontSize="sm">
              {stats.deletedFiles} Deleted
            </Badge>
            <Badge colorScheme="green" fontSize="sm">
              {stats.totalFiles} Total
            </Badge>
          </HStack>
        </HStack>
      </Box>

      {/* Physics Canvas */}
      <Box 
        w="full" 
        bg="white" 
        borderRadius="md" 
        border="1px solid" 
        borderColor="gray.200"
        overflow="hidden"
        position="relative"
        h={`${height}px`}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            display: 'block'
          }}
        />
        
        {/* Overlay Instructions */}
        <Box
          position="absolute"
          top={4}
          right={4}
          bg="blackAlpha.700"
          color="white"
          p={2}
          borderRadius="md"
          fontSize="xs"
        >
          <Text>Files bounce and move with simple physics</Text>
          <Text>Watch them evolve over time!</Text>
        </Box>
      </Box>

      {/* Legend */}
      <Box w="full" p={3} bg="gray.50" borderRadius="md">
        <HStack spacing={6} justify="center">
          <HStack spacing={2}>
            <Box w={3} h={3} bg={fileTypeColors.code} borderRadius="full" />
            <Text fontSize="sm">Code Files</Text>
          </HStack>
          <HStack spacing={2}>
            <Box w={3} h={3} bg={fileTypeColors.doc} borderRadius="full" />
            <Text fontSize="sm">Documentation</Text>
          </HStack>
          <HStack spacing={2}>
            <Box w={3} h={3} bg={fileTypeColors.config} borderRadius="full" />
            <Text fontSize="sm">Configuration</Text>
          </HStack>
          <HStack spacing={2}>
            <Box w={3} h={3} bg={fileTypeColors.test} borderRadius="full" />
            <Text fontSize="sm">Tests</Text>
          </HStack>
          <HStack spacing={2}>
            <Box w={3} h={3} bg={statusColors.deleted} borderRadius="full" />
            <Text fontSize="sm">Deleted</Text>
          </HStack>
        </HStack>
      </Box>
    </VStack>
  );
}
