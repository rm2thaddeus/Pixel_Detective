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

interface AdvancedPhysicsSimulationProps {
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
  clusterId: string;
  energy: number;
  lastCommitId: string;
}

interface PhysicsCommit {
  id: string;
  x: number;
  y: number;
  files: PhysicsFile[];
  isActive: boolean;
  node: CommitNode;
  clusterRadius: number;
  energy: number;
}

export default function AdvancedPhysicsSimulation({
  commits,
  currentIndex,
  height,
  width,
  isPlaying,
  onTimeChange
}: AdvancedPhysicsSimulationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [physicsCommits, setPhysicsCommits] = useState<PhysicsCommit[]>([]);
  const [stats, setStats] = useState({
    totalFiles: 0,
    activeFiles: 0,
    deletedFiles: 0,
    currentGeneration: 0,
    clusters: 0,
    energy: 0
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

  // Advanced physics constants
  const GRAVITY = 0.02;
  const SPRING_FORCE = 0.12;
  const DAMPING = 0.92;
  const REPULSION_FORCE = 0.8;
  const CLUSTER_FORCE = 0.15;
  const MAX_VELOCITY = 3;

  useEffect(() => {
    if (!canvasRef.current || commits.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Initialize advanced physics objects - FOCUS ON EVOLUTION STORY
    const newPhysicsCommits: PhysicsCommit[] = [];
    
    // Show only recent commits for better focus
    const maxVisibleCommits = Math.min(6, commits.length);
    const startCommitIndex = Math.max(0, commits.length - maxVisibleCommits);
    const visibleCommits = commits.slice(startCommitIndex);
    
    visibleCommits.forEach((commit, localIndex) => {
      const commitIndex = startCommitIndex + localIndex;
      
      // Position commits in a timeline with better spacing
      const commitX = 100 + (localIndex * (width - 200) / Math.max(visibleCommits.length - 1, 1));
      const commitY = 80;
      
      // Only show files from the most recent 4 commits
      const shouldShowFiles = localIndex >= visibleCommits.length - 4;
      
      // Create file objects with advanced clustering
      const physicsFiles: PhysicsFile[] = shouldShowFiles ? commit.files.slice(0, 20).map((file, fileIndex) => {
        // Create organized cluster patterns
        const clusterRadius = 50 + (fileIndex % 4) * 20;
        const clusterAngle = (fileIndex / Math.max(commit.files.length - 1, 1)) * Math.PI * 1.4 + Math.PI * 0.3;
        
        const fileX = commitX + Math.cos(clusterAngle) * clusterRadius;
        const fileY = commitY + Math.sin(clusterAngle) * clusterRadius + 60;

        const fileSize = Math.max(8, Math.min(18, 8 + file.modifications * 1.2));
        const color = file.status === 'deleted' ? statusColors.deleted : fileTypeColors[file.type];

        return {
          id: file.id,
          x: fileX,
          y: fileY,
          vx: 0,
          vy: 0,
          size: fileSize,
          color: color,
          node: file,
          commitId: commit.id,
          age: 0,
          maxAge: 800 + Math.random() * 400,
          isAlive: true,
          targetX: fileX,
          targetY: fileY,
          clusterId: commit.id,
          energy: 0,
          lastCommitId: commit.id
        };
      }) : [];

      newPhysicsCommits.push({
        id: commit.id,
        x: commitX,
        y: commitY,
        files: physicsFiles,
        isActive: commitIndex <= currentIndex,
        node: commit,
        clusterRadius: 60,
        energy: 0
      });
    });

    setPhysicsCommits(newPhysicsCommits);

    // Advanced animation loop with better physics
    const animate = () => {
      if (!ctx) return;

      // Clear canvas with gradient background
      const gradient = ctx.createLinearGradient(0, 0, 0, height);
      gradient.addColorStop(0, '#f8fafc');
      gradient.addColorStop(1, '#e2e8f0');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Draw commit timeline with connections
      newPhysicsCommits.forEach((commit, index) => {
        const isCurrentCommit = index === newPhysicsCommits.length - 1;
        const isRecentCommit = index >= newPhysicsCommits.length - 3;
        
        // Draw connection line to next commit
        if (index < newPhysicsCommits.length - 1) {
          const nextCommit = newPhysicsCommits[index + 1];
          ctx.strokeStyle = '#cbd5e0';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(commit.x, commit.y);
          ctx.lineTo(nextCommit.x, nextCommit.y);
          ctx.stroke();
        }
        
        // Draw commit node with energy-based pulsing
        const commitSize = isCurrentCommit ? 25 : isRecentCommit ? 20 : 15;
        const commitOpacity = isCurrentCommit ? 1.0 : isRecentCommit ? 0.9 : 0.7;
        
        ctx.globalAlpha = commitOpacity;
        
        // Pulsing effect for current commit
        if (isCurrentCommit) {
          const pulseSize = commitSize + Math.sin(Date.now() * 0.003) * 3;
          ctx.fillStyle = '#805ad5';
          ctx.strokeStyle = '#553c9a';
          ctx.lineWidth = 4;
          ctx.beginPath();
          ctx.arc(commit.x, commit.y, pulseSize, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
        } else {
          ctx.fillStyle = commit.isActive ? '#805ad5' : '#a0aec0';
          ctx.strokeStyle = commit.isActive ? '#553c9a' : '#718096';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.arc(commit.x, commit.y, commitSize, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
        }

        // Draw commit label
        ctx.fillStyle = '#2d3748';
        ctx.font = isCurrentCommit ? 'bold 16px Arial' : '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`G${commits.indexOf(commit.node) + 1}`, commit.x, commit.y + 5);
      });

      // Advanced file physics with clustering
      newPhysicsCommits.forEach(commit => {
        commit.files.forEach(file => {
          if (!file.isAlive) return;

          // Update physics with advanced forces
          file.age++;
          
          // Apply gravity
          file.vy += GRAVITY;
          
          // Apply spring force towards target (clustering)
          const springForce = SPRING_FORCE;
          file.vx += (file.targetX - file.x) * springForce;
          file.vy += (file.targetY - file.y) * springForce;
          
          // Apply repulsion from other files in same cluster
          commit.files.forEach(otherFile => {
            if (otherFile.id !== file.id && otherFile.isAlive) {
              const dx = file.x - otherFile.x;
              const dy = file.y - otherFile.y;
              const distance = Math.sqrt(dx * dx + dy * dy);
              const minDistance = file.size + otherFile.size + 5;
              
              if (distance < minDistance && distance > 0) {
                const force = REPULSION_FORCE / (distance * distance);
                file.vx += (dx / distance) * force;
                file.vy += (dy / distance) * force;
              }
            }
          });
          
          // Apply cluster cohesion force
          const clusterForce = CLUSTER_FORCE;
          file.vx += (commit.x - file.x) * clusterForce * 0.1;
          file.vy += (commit.y + 60 - file.y) * clusterForce * 0.1;
          
          // Apply damping
          file.vx *= DAMPING;
          file.vy *= DAMPING;
          
          // Limit velocity
          const speed = Math.sqrt(file.vx * file.vx + file.vy * file.vy);
          if (speed > MAX_VELOCITY) {
            file.vx = (file.vx / speed) * MAX_VELOCITY;
            file.vy = (file.vy / speed) * MAX_VELOCITY;
          }
          
          // Update position
          file.x += file.vx;
          file.y += file.vy;
          
          // Soft boundary collision
          if (file.x < file.size) {
            file.x = file.size;
            file.vx = Math.abs(file.vx) * 0.3;
          }
          if (file.x > width - file.size) {
            file.x = width - file.size;
            file.vx = -Math.abs(file.vx) * 0.3;
          }
          if (file.y < file.size + 120) {
            file.y = file.size + 120;
            file.vy = Math.abs(file.vy) * 0.3;
          }
          if (file.y > height - file.size - 30) {
            file.y = height - file.size - 30;
            file.vy = -Math.abs(file.vy) * 0.3;
          }

          // Calculate energy for visual effects
          file.energy = Math.sqrt(file.vx * file.vx + file.vy * file.vy);

          // Fade out old files
          let alpha = 1;
          if (file.age > file.maxAge * 0.9) {
            alpha = 1 - (file.age - file.maxAge * 0.9) / (file.maxAge * 0.1);
          }

          // Draw file circle with energy-based effects
          ctx.globalAlpha = alpha;
          
          // Energy-based glow effect
          if (file.energy > 0.5) {
            ctx.shadowColor = file.color;
            ctx.shadowBlur = file.energy * 3;
          } else {
            ctx.shadowBlur = 0;
          }
          
          ctx.fillStyle = file.color;
          ctx.strokeStyle = file.node.status === 'deleted' ? '#e53e3e' : 'white';
          ctx.lineWidth = file.node.status === 'deleted' ? 4 : 2;
          ctx.beginPath();
          ctx.arc(file.x, file.y, file.size, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
          
          // Reset shadow
          ctx.shadowBlur = 0;

          // Draw modification count with better visibility
          if (file.node.modifications > 0 && file.size > 12) {
            ctx.fillStyle = 'white';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(file.node.modifications.toString(), file.x, file.y + 3);
          }

          // Draw file name only for important files
          if (file.size > 16) {
            const fileName = file.node.path.split('/').pop() || file.node.path;
            ctx.fillStyle = '#2d3748';
            ctx.font = 'bold 10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(fileName.substring(0, 12), file.x, file.y + file.size + 18);
          }

          // Remove very old files
          if (file.age > file.maxAge) {
            file.isAlive = false;
          }
        });
      });

      // Reset alpha
      ctx.globalAlpha = 1;

      // Update stats
      const visibleFiles = newPhysicsCommits
        .filter(c => c.isActive)
        .flatMap(c => c.files)
        .filter(f => f.isAlive);
      
      const totalEnergy = visibleFiles.reduce((sum, f) => sum + f.energy, 0);
      const clusterCount = newPhysicsCommits.filter(c => c.isActive && c.files.some(f => f.isAlive)).length;
      
      setStats({
        totalFiles: commits.flatMap(c => c.files).length,
        activeFiles: visibleFiles.length,
        deletedFiles: visibleFiles.filter(f => f.node.status === 'deleted').length,
        currentGeneration: currentIndex + 1,
        clusters: clusterCount,
        energy: Math.round(totalEnergy * 10) / 10
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
    <VStack spacing={4} h="full">
      {/* Header */}
      <Box w="full" p={4} bg="white" borderRadius="md" border="1px solid" borderColor="gray.200">
        <HStack justify="space-between" align="center">
          <VStack align="start" spacing={1}>
            <Text fontSize="lg" fontWeight="bold" color="gray.700">
              Advanced Physics Evolution
            </Text>
            <Text fontSize="sm" color="gray.500">
              Watch your codebase evolve through advanced physics • Generation {stats.currentGeneration}
            </Text>
          </VStack>
          
          <HStack spacing={4}>
            <Badge colorScheme="blue" fontSize="sm">
              {stats.activeFiles} Active
            </Badge>
            <Badge colorScheme="red" fontSize="sm">
              {stats.deletedFiles} Deleted
            </Badge>
            <Badge colorScheme="purple" fontSize="sm">
              {stats.clusters} Clusters
            </Badge>
            <Badge colorScheme="green" fontSize="sm">
              {stats.energy} Energy
            </Badge>
          </HStack>
        </HStack>
      </Box>

      {/* Physics Canvas */}
      <Box 
        flex="1" 
        w="full" 
        bg="white" 
        borderRadius="md" 
        border="1px solid" 
        borderColor="gray.200"
        overflow="hidden"
        position="relative"
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
          p={3}
          borderRadius="md"
          fontSize="xs"
          maxW="200px"
        >
          <Text fontWeight="bold">Advanced Physics Features:</Text>
          <Text>• Files cluster around commits</Text>
          <Text>• Repulsion keeps files separated</Text>
          <Text>• Energy-based visual effects</Text>
          <Text>• Pulsing current generation</Text>
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
