'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

type FileKind = 'code' | 'document' | 'config' | 'other';

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  size: number; // LOC after commit if available
  type: FileKind;
}

interface Commit {
  hash: string;
  timestamp: string;
  message: string;
  author: string;
  files: FileChange[];
}

interface ProgressiveStructureGraphProps {
  commits: Commit[];
  currentTimeIndex: number;
  width?: number;
  height?: number;
  maxNodes?: number;
  showFolderGroups?: boolean;
}

type NodeDatum = {
  id: string;
  nodeType: 'commit' | 'file' | 'folder';
  fileKind?: FileKind;
  radius: number;
  folderPath?: string;
  fileCount?: number;
};

type LinkDatum = {
  source: string;
  target: string;
  kind: 'chain' | 'touch';
};

const FILE_COLORS: Record<FileKind, string> = {
  code: '#3b82f6',
  document: '#10b981',
  config: '#f59e0b',
  other: '#6b7280',
};

export default function ProgressiveStructureGraph({
  commits,
  currentTimeIndex,
  width = 1200,
  height = 600,
  maxNodes = 100,
  showFolderGroups = true,
}: ProgressiveStructureGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<NodeDatum, undefined>>();

  // Helper function to extract folder path
  const getFolderPath = (filePath: string): string => {
    const parts = filePath.split('/');
    if (parts.length <= 1) return '/';
    return parts.slice(0, -1).join('/');
  };

  // Build nodes/links up to the current index with folder grouping and node limiting
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, NodeDatum>();
    const linkList: LinkDatum[] = [];
    const upto = Math.max(0, Math.min(currentTimeIndex, commits.length - 1));

    // Commit chain
    for (let i = 0; i <= upto; i++) {
      const c = commits[i];
      nodeMap.set(c.hash, { id: c.hash, nodeType: 'commit', radius: 12 });
      if (i > 0) {
        linkList.push({ source: commits[i - 1].hash, target: c.hash, kind: 'chain' });
      }
    }

    // Collect all files from all commits up to current index
    const allFiles = new Map<string, { file: FileChange; commits: Set<string> }>();
    
    for (let i = 0; i <= upto; i++) {
      const c = commits[i];
      for (const f of c.files || []) {
        if (!f.path) continue;
        if (!allFiles.has(f.path)) {
          allFiles.set(f.path, { file: f, commits: new Set() });
        }
        allFiles.get(f.path)!.commits.add(c.hash);
      }
    }

    // Apply node limiting and folder grouping
    const sortedFiles = Array.from(allFiles.entries())
      .sort(([,a], [,b]) => b.commits.size - a.commits.size) // Sort by frequency
      .slice(0, maxNodes - commits.length - 5); // Reserve space for commits and folders

    if (showFolderGroups) {
      // Group files by folder
      const folderMap = new Map<string, { files: FileChange[]; totalSize: number; fileTypes: Set<string> }>();
      
      for (const [, { file }] of sortedFiles) {
        const folderPath = getFolderPath(file.path);
        if (!folderMap.has(folderPath)) {
          folderMap.set(folderPath, { files: [], totalSize: 0, fileTypes: new Set() });
        }
        const folder = folderMap.get(folderPath)!;
        folder.files.push(file);
        folder.totalSize += file.size || 0;
        folder.fileTypes.add(file.type);
      }

      // Create folder nodes
      for (const [folderPath, folderData] of folderMap) {
        if (folderPath === '/') continue; // Skip root folder
        
        const folderId = `folder:${folderPath}`;
        const folderSize = Math.min(25, Math.max(8, Math.sqrt(folderData.totalSize) * 0.3 + folderData.files.length * 0.5));
        
        nodeMap.set(folderId, {
          id: folderId,
          nodeType: 'folder',
          radius: folderSize,
          folderPath,
          fileCount: folderData.files.length,
        });

        // Link current commit to folder
        if (upto >= 0) {
          linkList.push({ source: commits[upto].hash, target: folderId, kind: 'touch' });
        }
      }

      // Add individual files only for the most recent commit and most important files
      const recentCommitFiles = new Set(commits[upto]?.files?.map(f => f.path) || []);
      const importantFiles = sortedFiles.slice(0, Math.min(20, maxNodes / 5)); // Top 20 files or 1/5 of max nodes
      
      for (const [filePath, { file }] of sortedFiles) {
        const isRecentFile = recentCommitFiles.has(filePath);
        const isImportantFile = importantFiles.some(([path]) => path === filePath);
        
        if (isRecentFile || isImportantFile) {
          const kind: FileKind = file.type as FileKind;
          const loc = Math.max(0, file.size || 0);
          const r = Math.min(12, Math.max(4, loc > 0 ? Math.sqrt(loc) * 0.3 : 5));
          
          nodeMap.set(filePath, { 
            id: filePath, 
            nodeType: 'file', 
            fileKind: kind, 
            radius: r 
          });

          // Link to commit
          if (upto >= 0) {
            linkList.push({ source: commits[upto].hash, target: filePath, kind: 'touch' });
          }
        }
      }
    } else {
      // No folder grouping - just add files directly
      for (const [filePath, { file }] of sortedFiles) {
        const kind: FileKind = file.type as FileKind;
        const loc = Math.max(0, file.size || 0);
        const r = Math.min(12, Math.max(4, loc > 0 ? Math.sqrt(loc) * 0.3 : 5));
        
        nodeMap.set(filePath, { 
          id: filePath, 
          nodeType: 'file', 
          fileKind: kind, 
          radius: r 
        });

        // Link to commit
        if (upto >= 0) {
          linkList.push({ source: commits[upto].hash, target: filePath, kind: 'touch' });
        }
      }
    }

    return { 
      nodes: Array.from(nodeMap.values()).slice(0, maxNodes), // Hard limit
      links: linkList 
    };
  }, [commits, currentTimeIndex, maxNodes, showFolderGroups]);

  // Create once
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.attr('width', width).attr('height', height);
    svg.selectAll('*').remove();

    // Layers
    svg.append('g').attr('class', 'edges');
    svg.append('g').attr('class', 'nodes');

    // Optimized simulation with reduced forces for better performance
    simRef.current = d3
      .forceSimulation<NodeDatum>([])
      .force('link', d3.forceLink<NodeDatum, any>([]).id((d: any) => d.id).distance((l: any) => (l.kind === 'chain' ? 80 : 40)).strength((l: any) => (l.kind === 'chain' ? 0.8 : 0.3)))
      .force('charge', d3.forceManyBody<NodeDatum>().strength(-80))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<NodeDatum>().radius((d) => d.radius + 8))
      .alphaDecay(0.05) // Faster convergence
      .velocityDecay(0.4); // Reduce oscillation
  }, [width, height]);

  // Update on data changes
  useEffect(() => {
    const svg = d3.select(svgRef.current);
    const edgesLayer = svg.select<SVGGElement>('g.edges');
    const nodesLayer = svg.select<SVGGElement>('g.nodes');
    const sim = simRef.current!;

    const edgeKey = (d: any) => {
      const sid = typeof d.source === 'string' ? d.source : d.source?.id;
      const tid = typeof d.target === 'string' ? d.target : d.target?.id;
      return `${sid}|${tid}`;
    };

    // Data-join nodes FIRST so the forceLink id resolver can find them
    const nodeSel = nodesLayer.selectAll<SVGGElement, any>('g.node').data(nodes, (d: any) => d.id);
    const nodeEnter = nodeSel.enter().append('g').attr('class', 'node');
    nodeEnter
      .append('circle')
      .attr('r', 0)
      .attr('fill', (d: any) => {
        if (d.nodeType === 'commit') return '#8b5cf6';
        if (d.nodeType === 'folder') return '#f59e0b';
        return FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', (d: any) => d.nodeType === 'folder' ? 2.5 : 1.5)
      .transition()
      .duration(250)
      .attr('r', (d: any) => d.radius);
    
    // Add folder labels
    nodeEnter
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', (d: any) => d.nodeType === 'folder' ? '10px' : '0px')
      .attr('font-weight', 'bold')
      .attr('fill', '#fff')
      .text((d: any) => d.nodeType === 'folder' ? d.fileCount : '');
    
    nodeEnter.append('title').text((d: any) => {
      if (d.nodeType === 'folder') return `${d.folderPath} (${d.fileCount} files)`;
      return d.id;
    });

    nodeSel
      .select('circle')
      .attr('fill', (d: any) => {
        if (d.nodeType === 'commit') return '#8b5cf6';
        if (d.nodeType === 'folder') return '#f59e0b';
        return FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
      })
      .attr('r', (d: any) => d.radius);
    nodeSel.exit().remove();

    // Hook simulation nodes BEFORE assigning links
    sim.nodes(nodes as any).on('tick', ticked);

    // Data-join edges
    const edgeSel = edgesLayer.selectAll<SVGLineElement, any>('line').data(links, edgeKey);
    edgeSel.enter()
      .append('line')
      .attr('stroke', (d: any) => (d.kind === 'chain' ? '#8b5cf6' : '#cbd5e1'))
      .attr('stroke-width', (d: any) => (d.kind === 'chain' ? 2.5 : 1.3))
      .attr('opacity', (d: any) => (d.kind === 'chain' ? 0.9 : 0.6));
    edgeSel.attr('stroke', (d: any) => (d.kind === 'chain' ? '#8b5cf6' : '#cbd5e1'))
      .attr('stroke-width', (d: any) => (d.kind === 'chain' ? 2.5 : 1.3))
      .attr('opacity', (d: any) => (d.kind === 'chain' ? 0.9 : 0.6));
    edgeSel.exit().remove();

    // Hook simulation links AFTER nodes are registered
    const linkForce = sim.force('link') as d3.ForceLink<NodeDatum, any>;
    linkForce.links(links as any);
    sim.alpha(0.8).restart();

    function ticked() {
      edgesLayer
        .selectAll<SVGLineElement, any>('line')
        .attr('x1', (d: any) => (d.source.x as number))
        .attr('y1', (d: any) => (d.source.y as number))
        .attr('x2', (d: any) => (d.target.x as number))
        .attr('y2', (d: any) => (d.target.y as number));

      nodesLayer
        .selectAll<SVGGElement, any>('g.node')
        .attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
    }
  }, [nodes, links]);

  return <svg ref={svgRef} />;
}


