'use client';

import React, { useEffect, useMemo, useRef } from 'react';
import * as d3 from 'd3';

type FileKind = 'code' | 'document' | 'config' | 'other';

interface FileChange {
  path: string;
  action: 'created' | 'modified' | 'deleted';
  size: number; // LOC after commit if available
  lines_after?: number;
  loc?: number;
  additions?: number;
  deletions?: number;
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
  resetToken?: number;
  maxNodes?: number;
  showFolderGroups?: boolean;
  focusedView?: boolean;
  // Range of commits to visualize (inclusive indices in commits array)
  rangeStartIndex?: number;
  rangeEndIndex?: number;
  // Encodings and interactions
  sizeByLOC?: boolean;
  enableZoom?: boolean;
  // New coloring controls
  colorMode?: 'folder' | 'type' | 'commit-flow' | 'activity' | 'none';
  highlightDocs?: boolean;
  edgeEmphasis?: number; // 0..1 controls edge visibility
}

type NodeDatum = {
  id: string;
  nodeType: 'commit' | 'file' | 'folder';
  fileKind?: FileKind;
  radius: number;
  folderPath?: string;
  fileCount?: number;
  loc?: number; // lines of code associated (commit total, file size, or folder aggregate)
  filesTouched?: number;
  touchCount?: number; // how many commits touched this file (for activity coloring)
};

type LinkDatum = {
  source: string;
  target: string;
  kind: 'chain' | 'touch';
};

const FILE_COLORS: Record<FileKind, string> = {
  code: '#3b82f6',      // Blue for code
  document: '#f59e0b',   // Orange for documents  
  config: '#8b5cf6',     // Purple for config
  other: '#6b7280',      // Gray for other
};

export default function ProgressiveStructureGraph({
  commits,
  currentTimeIndex,
  width = 1200,
  height = 600,
  resetToken,
  maxNodes = 100,
  showFolderGroups = true,
  focusedView = true,
  rangeStartIndex,
  rangeEndIndex,
  sizeByLOC = true,
  enableZoom = true,
  colorMode = 'folder',
  highlightDocs = true,
  edgeEmphasis = 0.4,
}: ProgressiveStructureGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simRef = useRef<d3.Simulation<NodeDatum, undefined>>();

  // Helper function to extract folder path
  const getFolderPath = (filePath: string): string => {
    const parts = filePath.split('/');
    if (parts.length <= 1) return '/';
    return parts.slice(0, -1).join('/');
  };
  // Top-level folder (used for coloring)
  const getTopLevelFolder = (filePath: string): string => {
    const normalized = filePath.replace(/\\/g, '/');
    const idx = normalized.indexOf('/');
    return idx === -1 ? normalized : normalized.slice(0, idx);
  };

  // Build nodes/links up to the current index with folder grouping and node limiting
  const { nodes, links } = useMemo(() => {
    const nodeMap = new Map<string, NodeDatum>();
    const linkList: LinkDatum[] = [];
    const startIndex = Math.max(0, Math.min(rangeStartIndex ?? 0, commits.length - 1));
    const upto = Math.max(startIndex, Math.min(currentTimeIndex, commits.length - 1));
    
    console.log('ProgressiveStructureGraph: Building graph', {
      totalCommits: commits.length,
      currentTimeIndex,
      startIndex,
      upto,
      showingCommits: `${startIndex + 1} to ${upto + 1}`,
      firstCommit: commits[startIndex]?.hash?.substring(0, 8),
      lastCommit: commits[upto]?.hash?.substring(0, 8),
      sampleFile: commits[upto]?.files?.[0],
      locDataAvailable: commits[upto]?.files?.some(f => f.loc !== undefined || f.lines_after !== undefined)
    });

    // Commit chain
    for (let i = startIndex; i <= upto; i++) {
      const c = commits[i];
      const totalLoc = (c.files || []).reduce((sum, f) => {
        // Prioritize lines_after, then loc, then size as fallback
        const loc = f.lines_after ?? f.loc ?? f.size ?? 0;
        return sum + Math.max(0, loc);
      }, 0);
      const rCommit = sizeByLOC ? Math.min(20, Math.max(8, Math.sqrt(totalLoc) * 0.2 + 8)) : 12;
      nodeMap.set(c.hash, { id: c.hash, nodeType: 'commit', radius: rCommit, loc: totalLoc, filesTouched: c.files?.length || 0 });
      if (i > startIndex) {
        linkList.push({ source: commits[i - 1].hash, target: c.hash, kind: 'chain' });
      }
    }

    // Collect all files from all commits up to current index
    const allFiles = new Map<string, { file: FileChange; commits: Set<string> }>();
    
    for (let i = startIndex; i <= upto; i++) {
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
    const sortedAll = Array.from(allFiles.entries()).sort(([,a], [,b]) => b.commits.size - a.commits.size);
    // Always prioritize document nodes so sprint docs are visible and never collapsed
    const docEntries = sortedAll.filter(([, { file }]) => (file.type as FileKind) === 'document');
    const nonDocEntries = sortedAll.filter(([, { file }]) => (file.type as FileKind) !== 'document');
    const budgetForFiles = Math.max(0, maxNodes - commits.length - 5); // Reserve space for commits and folders
    const sortedFiles = [...docEntries, ...nonDocEntries].slice(0, budgetForFiles);

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
        folder.totalSize += file.lines_after ?? file.loc ?? file.size ?? 0;
        folder.fileTypes.add(file.type);
      }

      // Create folder nodes
      for (const [folderPath, folderData] of folderMap) {
        if (folderPath === '/') continue; // Skip root folder
        
        const folderId = `folder:${folderPath}`;
        const folderSize = Math.min(28, Math.max(8, Math.sqrt(folderData.totalSize) * 0.25 + folderData.files.length * 0.4));
        
        nodeMap.set(folderId, {
          id: folderId,
          nodeType: 'folder',
          radius: sizeByLOC ? folderSize : 12,
          folderPath,
          fileCount: folderData.files.length,
          loc: folderData.totalSize,
        });

        // Link all commits that touch files in this folder
        for (let i = startIndex; i <= upto; i++) {
          const commitFiles = new Set(commits[i]?.files?.map(f => f.path) || []);
          const hasFilesInFolder = Array.from(folderData.files).some(f => commitFiles.has(f.path));
          if (hasFilesInFolder) {
            linkList.push({ source: commits[i].hash, target: folderId, kind: 'touch' });
          }
        }
      }

      // Add individual files only for the most recent commit and most important files
      const recentCommitFiles = new Set(commits[upto]?.files?.map(f => f.path) || []);
      const importantFiles = sortedFiles.slice(0, Math.min(20, maxNodes / 5)); // Top 20 files or 1/5 of max nodes
      
      for (const [filePath, { file, commits: fileCommits }] of sortedFiles as any) {
        const isRecentFile = recentCommitFiles.has(filePath);
        const isImportantFile = importantFiles.some(([path]) => path === filePath);
        
        if (isRecentFile || isImportantFile) {
          const kind: FileKind = file.type as FileKind;
          const loc = Math.max(0, file.lines_after ?? file.loc ?? file.size ?? 0);
          const r = sizeByLOC ? Math.min(16, Math.max(4, loc > 0 ? Math.sqrt(loc) * 0.3 : 6)) : 8;
          
          nodeMap.set(filePath, { 
            id: filePath, 
            nodeType: 'file', 
            fileKind: kind, 
            radius: r,
            loc,
            folderPath: getTopLevelFolder(file.path),
            touchCount: (fileCommits?.size as number) || 0,
          });

          // Link to all commits that touch this file
          for (let i = startIndex; i <= upto; i++) {
            const commitFiles = new Set(commits[i]?.files?.map(f => f.path) || []);
            if (commitFiles.has(filePath)) {
              linkList.push({ source: commits[i].hash, target: filePath, kind: 'touch' });
            }
          }
        }
      }
    } else {
      // No folder grouping - just add files directly
      for (const [filePath, { file, commits: fileCommits }] of sortedFiles as any) {
        const kind: FileKind = file.type as FileKind;
        const loc = Math.max(0, file.lines_after ?? file.loc ?? file.size ?? 0);
        const r = sizeByLOC ? Math.min(16, Math.max(4, loc > 0 ? Math.sqrt(loc) * 0.3 : 6)) : 8;
        
        nodeMap.set(filePath, { 
          id: filePath, 
          nodeType: 'file', 
          fileKind: kind, 
          radius: r,
          loc,
          folderPath: getTopLevelFolder(file.path),
          touchCount: (fileCommits?.size as number) || 0,
        });

        // Link to all commits that touch this file
        for (let i = startIndex; i <= upto; i++) {
          const commitFiles = new Set(commits[i]?.files?.map(f => f.path) || []);
          if (commitFiles.has(filePath)) {
            linkList.push({ source: commits[i].hash, target: filePath, kind: 'touch' });
          }
        }
      }
    }

    // Build final node set ensuring all commits and all documents are kept
    const allNodes = Array.from(nodeMap.values());
    const commitNodes = allNodes.filter(n => n.nodeType === 'commit');
    const docNodes = allNodes.filter(n => n.nodeType === 'file' && n.fileKind === 'document');
    const mustKeepIds = new Set<string>([...commitNodes, ...docNodes].map(n => n.id));
    const others = allNodes.filter(n => !mustKeepIds.has(n.id));

    const finalNodes: NodeDatum[] = [];
    // Always include commits and documents first
    finalNodes.push(...commitNodes, ...docNodes);
    // Fill the remaining budget with other nodes (folders, files)
    for (const n of others) {
      if (finalNodes.length >= Math.max(maxNodes, finalNodes.length)) break; // ensure we never drop must-keep set
      finalNodes.push(n);
    }

    // Filter links to those whose endpoints are present
    const allowed = new Set(finalNodes.map(n => n.id));
    const finalLinks = linkList.filter(l => allowed.has(l.source as any) && allowed.has(l.target as any));

    return { 
      nodes: finalNodes,
      links: finalLinks 
    };
  }, [commits, currentTimeIndex, maxNodes, showFolderGroups, rangeStartIndex, sizeByLOC]);

  // Create once
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.attr('width', width).attr('height', height);
    svg.selectAll('*').remove();
    
    // Add dark background
    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', '#1a202c') // Dark gray background
      .attr('rx', 8)
      .attr('ry', 8);

    // Root container to enable zoom/pan on groups
    const root = svg.append('g').attr('class', 'root');
    // Layers
    root.append('g').attr('class', 'edges');
    root.append('g').attr('class', 'nodes');

    // Zoom/pan
    if (enableZoom) {
      const zoomed = (event: any) => {
        root.attr('transform', event.transform);
      };
      svg.call(
        d3
          .zoom<SVGSVGElement, unknown>()
          .extent([[0, 0], [width, height]])
          .scaleExtent([0.2, 4])
          .on('zoom', zoomed)
      );
    }

    // Enhanced simulation with better organization and less tangling
    simRef.current = d3
      .forceSimulation<NodeDatum>([])
      .force('link', d3.forceLink<NodeDatum, any>([]).id((d: any) => d.id).distance((l: any) => {
        if (l.kind === 'chain') return 120; // Commit chain spacing
        if (l.kind === 'touch') return 60;  // File/commit connections
        return 40;
      }).strength((l: any) => {
        if (l.kind === 'chain') return 0.9; // Strong commit chain
        if (l.kind === 'touch') return 0.4; // Moderate file connections
        return 0.2;
      }))
      .force('charge', d3.forceManyBody<NodeDatum>().strength((d: any) => {
        if (d.nodeType === 'commit') return -200; // Strong repulsion for commits
        if (d.nodeType === 'folder') return -150; // Medium repulsion for folders
        return -100; // Weak repulsion for files
      }))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<NodeDatum>().radius((d) => d.radius + 12))
      .force('x', d3.forceX<NodeDatum>((d: any) => {
        // Organize commits horizontally by time
        if (d.nodeType === 'commit') {
          const commitIndex = commits.findIndex(c => c.hash === d.id);
          return (commitIndex / Math.max(1, commits.length - 1)) * width;
        }
        return width / 2;
      }).strength(0.3))
      .force('y', d3.forceY<NodeDatum>((d: any) => {
        // Organize files/folders vertically by type
        if (d.nodeType === 'folder') return height * 0.3; // Top area for folders
        if (d.nodeType === 'file') return height * 0.7;   // Bottom area for files
        return height / 2; // Center for commits
      }).strength(0.2))
      .alphaDecay(0.05) // Faster convergence
      .velocityDecay(0.4); // Reduce oscillation
  }, [width, height]);

  // Reset zoom/simulation on external reset triggers
  useEffect(() => {
    if (resetToken === undefined) return;
    const svg = d3.select(svgRef.current);
    svg.select('g.root').attr('transform', null);
    if (simRef.current) {
      simRef.current.alpha(1).restart();
    }
  }, [resetToken]);

  // Update on data changes - only when nodes/links actually change
  useEffect(() => {
    if (!svgRef.current || !simRef.current) return;
    
    const svg = d3.select(svgRef.current);
    const edgesLayer = svg.select<SVGGElement>('g.edges');
    const nodesLayer = svg.select<SVGGElement>('g.nodes');
    const sim = simRef.current;

    // Color helpers
    const folderDomains = new Set<string>();
    nodes.forEach((n: any) => { if (n.nodeType === 'file' && n.folderPath) folderDomains.add(n.folderPath); });
    const folderColor = d3.scaleOrdinal<string, string>(d3.schemeTableau10).domain(Array.from(folderDomains));
    const activityDomain = d3.extent(nodes.filter((n: any) => n.nodeType === 'file').map((n: any) => n.touchCount || 0)) as [number, number];
    const activityColor = d3.scaleSequential(d3.interpolatePlasma).domain([activityDomain?.[0] ?? 0, activityDomain?.[1] ?? 1]);
    const commitFlowColor = d3.scaleSequential(d3.interpolateTurbo).domain([0, Math.max(1, commits.length - 1)]);
    const complement = (hex: string): string => {
      try {
        const c = d3.color(hex);
        if (!c) return '#ffffff';
        const hsl = d3.hsl(c);
        hsl.h = (hsl.h + 180) % 360;
        hsl.s = Math.min(1, hsl.s * 0.9);
        hsl.l = Math.min(0.9, 1 - hsl.l * 0.6);
        return hsl.formatHex();
      } catch {
        return '#ffffff';
      }
    };

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
        if (d.nodeType === 'commit') {
          const idx = Math.max(0, commits.findIndex(c => c.hash === d.id));
          return colorMode === 'commit-flow' ? commitFlowColor(idx) : '#8b5cf6';
        }
        if (d.nodeType === 'folder') {
          if (colorMode === 'folder' || colorMode === 'commit-flow' || colorMode === 'activity') return folderColor((d.folderPath || 'folders') as string);
          if (colorMode === 'none') return '#a98a2b';
          return '#f59e0b';
        }
        // file nodes
        switch (colorMode) {
          case 'folder':
          case 'commit-flow':
            return folderColor((d.folderPath || 'files') as string);
          case 'type':
            return FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
          case 'activity':
            return activityColor(d.touchCount || 0) as string;
          case 'none':
          default:
            return '#6b7280';
        }
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', (d: any) => d.nodeType === 'folder' ? 2.5 : 1.5)
      .transition()
      .duration(250)
      .attr('r', (d: any) => d.radius);

    // Document highlight ring with complementary color
    nodeEnter
      .filter((d: any) => highlightDocs && d.nodeType === 'file' && d.fileKind === 'document')
      .append('circle')
      .attr('class', 'doc-ring')
      .attr('fill', 'none')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9)
      .attr('r', (d: any) => d.radius + 3)
      .attr('stroke', (d: any) => {
        let base = '#888';
        if (colorMode === 'type') base = FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
        else if (colorMode === 'activity') base = activityColor(d.touchCount || 0) as string;
        else base = folderColor((d.folderPath || 'docs') as string);
        return complement(base);
      });
    
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
      if (d.nodeType === 'folder') return `${d.folderPath} (${d.fileCount} files, ${d.loc || 0} LOC)`;
      if (d.nodeType === 'commit') return `${d.id} â€” Files: ${d.filesTouched || 0}, LOC: ${d.loc || 0}`;
      return `${d.id} â€” LOC: ${d.loc || 0}`;
    });

    nodeSel
      .select('circle')
      .attr('fill', (d: any) => {
        if (d.nodeType === 'commit') {
          const idx = Math.max(0, commits.findIndex(c => c.hash === d.id));
          return colorMode === 'commit-flow' ? commitFlowColor(idx) : '#8b5cf6';
        }
        if (d.nodeType === 'folder') {
          if (colorMode === 'folder' || colorMode === 'commit-flow' || colorMode === 'activity') return folderColor((d.folderPath || 'folders') as string);
          if (colorMode === 'none') return '#a98a2b';
          return '#f59e0b';
        }
        switch (colorMode) {
          case 'folder':
          case 'commit-flow':
            return folderColor((d.folderPath || 'files') as string);
          case 'type':
            return FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
          case 'activity':
            return activityColor(d.touchCount || 0) as string;
          case 'none':
          default:
            return '#6b7280';
        }
      })
      .attr('r', (d: any) => d.radius)
      .attr('opacity', (d: any) => {
        if (!focusedView) return 1.0; // Show all nodes in full view
        
        // Highlight current commit and its related files in focused view
        if (d.nodeType === 'commit') {
          const commitIndex = commits.findIndex(c => c.hash === d.id);
          if (commitIndex === currentTimeIndex) return 1.0; // Current commit fully visible
          if (Math.abs(commitIndex - currentTimeIndex) <= 2) return 0.8; // Nearby commits
          return 0.3; // Distant commits more transparent
        }
        // Files and folders: highlight if they're in the current commit
        if (currentTimeIndex >= 0 && currentTimeIndex < commits.length) {
          const currentCommitFiles = new Set(commits[currentTimeIndex]?.files?.map(f => f.path) || []);
          const isInCurrentCommit = currentCommitFiles.has(d.id) || 
            (d.nodeType === 'folder' && Array.from(d.files || []).some((f: any) => currentCommitFiles.has(f.path)));
          return isInCurrentCommit ? 1.0 : 0.2; // Current commit files fully visible, others very subtle
        }
        return 0.6;
      });

    // Ensure/update document ring per node
    (nodeSel as any).each(function(d: any) {
      const g = d3.select(this);
      let ring = g.select<SVGCircleElement>('circle.doc-ring');
      const isDoc = highlightDocs && d.nodeType === 'file' && d.fileKind === 'document';
      if (isDoc) {
        if (ring.empty()) {
          ring = g.append('circle').attr('class', 'doc-ring');
        }
        let base = '#888';
        if (colorMode === 'type') base = FILE_COLORS[d.fileKind as FileKind] || '#6b7280';
        else if (colorMode === 'activity') base = activityColor(d.touchCount || 0) as string;
        else base = folderColor((d.folderPath || 'docs') as string);
        ring
          .attr('fill', 'none')
          .attr('stroke-width', 2)
          .attr('opacity', 0.9)
          .attr('r', d.radius + 3)
          .attr('stroke', complement(base));
      } else if (!ring.empty()) {
        ring.remove();
      }
    });
    nodeSel.exit().remove();

    // Hook simulation nodes BEFORE assigning links
    sim.nodes(nodes as any).on('tick', ticked);

    // Data-join edges
    const edgeSel = edgesLayer.selectAll<SVGLineElement, any>('line').data(links, edgeKey);
    const chainOpacity = (0.3 + 0.7 * Math.max(0, Math.min(1, edgeEmphasis))) * (focusedView ? 1 : 0.9);
    const fileOpacity = (0.02 + 0.28 * Math.max(0, Math.min(1, edgeEmphasis))) * (focusedView ? 1 : 1.2);
    const chainWidth = 1 + 2 * Math.max(0, Math.min(1, edgeEmphasis));
    const fileWidth = 0.4 + 0.8 * Math.max(0, Math.min(1, edgeEmphasis));

    edgeSel.enter()
      .append('line')
      .attr('stroke', (d: any) => {
        if (d.kind === 'chain') return '#8b5cf6'; // Purple for commit chain
        return '#4a5568'; // Darker gray for file connections
      })
      .attr('stroke-width', (d: any) => {
        if (d.kind === 'chain') return chainWidth;
        return fileWidth;
      })
      .attr('opacity', (d: any) => {
        if (d.kind === 'chain') return chainOpacity;
        return fileOpacity;
      })
      .attr('stroke-dasharray', (d: any) => (d.kind === 'chain' ? 'none' : '4,4'));
    edgeSel.attr('stroke', (d: any) => {
        if (d.kind === 'chain') return '#8b5cf6';
        return '#4a5568';
      })
      .attr('stroke-width', (d: any) => {
        if (d.kind === 'chain') return chainWidth;
        return fileWidth;
      })
      .attr('opacity', (d: any) => {
        if (d.kind === 'chain') return chainOpacity;
        return fileOpacity;
      })
      .attr('stroke-dasharray', (d: any) => (d.kind === 'chain' ? 'none' : '4,4'));
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
  }, [nodes, links, colorMode, highlightDocs, edgeEmphasis, focusedView, commits, currentTimeIndex]);

  return <svg ref={svgRef} />;
}


