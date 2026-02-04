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
  snapshots?: EvolutionSnapshot[]; // All snapshots up to latest for accurate per-commit rendering
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
  // New data: structural subgraph scoped to the current commit
  subgraphData?: { nodes: any[]; edges: any[] };
  // Changed files in the current commit (paths)
  changedFiles?: string[];
}

export default function BiologicalEvolutionGraph({
  snapshot,
  snapshots,
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
  totalSnapshots = 1,
  subgraphData,
  changedFiles = []
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
    
    // Rebuild timeline every render, but preserve the full subgraph group for smooth updates
    timelineSvg.selectAll("*").remove();
    // Do NOT wipe the entire dendrogram SVG; we update its groups incrementally

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
        .text((snapshots && snapshots[i]?.commit_hash ? snapshots[i].commit_hash : snapshot.commit_hash).substring(0, isCurrentCommit ? 6 : 4));

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
    let dendrogramGroup = dendrogramSvg.select<SVGGElement>('g.dendrogram-panel');
    if (dendrogramGroup.empty()) {
      dendrogramGroup = dendrogramSvg.append('g').attr('class', 'dendrogram-panel');
    }
    dendrogramGroup.attr('transform', 'translate(30, 30)');
    // Clear previous frame content to avoid duplicate overlays
    dendrogramGroup.selectAll('*').remove();

    // Calculate dendrogram layout - use FULL available space
    const availableDendrogramWidth = dendrogramWidth - 60;
    const availableDendrogramHeight = dendrogramHeight - 60;
    
    console.log('Dendrogram panel dimensions:', {
      dendrogramWidth,
      dendrogramHeight,
      availableDendrogramWidth,
      availableDendrogramHeight
    });
    
    // === Structural Subgraph (Bottom) ===
    // Build a structural view similar to StructureAnalysisGraph but scoped to current commit
    // Create or select a persistent group for force-directed graph
    let graphRoot = dendrogramGroup.select<SVGGElement>('g.structural-subgraph-root');
    if (graphRoot.empty()) {
      graphRoot = dendrogramGroup.append('g').attr('class', 'structural-subgraph-root');
    }
    // Clear previous graph frame
    graphRoot.selectAll('*').remove();

    // Setup zoom container
    const zoomLayer = graphRoot.append('g').attr('class', 'zoom-layer');
    const graphLayer = zoomLayer.append('g').attr('class', 'graph-layer');
    
    const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.25, 3])
      .on('zoom', (event) => {
        graphLayer.attr('transform', event.transform.toString());
      });
    // Attach zoom to the embedded svg element (parent of dendrogramGroup)
    (dendrogramSvg as any).call?.(zoomBehavior as any);

    // Prepare nodes/edges from provided subgraph data
    const sgNodes: any[] = subgraphData?.nodes || [];
    const sgEdges: any[] = (subgraphData?.edges || []).map((e: any) => ({
      from: e.from || e.source,
      to: e.to || e.target,
      type: e.type || e.label || e.rel || 'RELATED',
      timestamp: (e as any).timestamp
    }));

    // Identify changed file nodes for this commit
    const filesSet = new Set<string>((changedFiles && changedFiles.length ? changedFiles : (snapshot.commit?.files_changed || [])) as string[]);
    const isFileNode = (n: any) => {
      const labels = Array.isArray(n.labels) ? n.labels : [n.labels];
      return labels.includes('File') || labels.includes('Document') || (n.properties?.path && typeof n.properties.path === 'string');
    };
    const nodeMatchesFile = (n: any) => {
      const idStr = `${n.id || ''}`;
      const path = n.properties?.path || idStr;
      for (const p of filesSet) {
        if (!p) continue;
        if (idStr.includes(p) || path === p || path?.endsWith(p.split('/').pop() || '')) return true;
      }
      return false;
    };

    // Try to find the current commit node in the subgraph
    const currentHash = (snapshots && snapshots[currentIndex]?.commit_hash) || snapshot.commit_hash;
    const isCommitNode = (n: any) => {
      const labels = Array.isArray(n.labels) ? n.labels : [n.labels];
      const hash = n.properties?.hash || '';
      return labels.includes('GitCommit') && (String(n.id).includes(currentHash) || hash === currentHash);
    };
    const commitNode = sgNodes.find(isCommitNode);

    // Build filtered ID set
    const filteredIdSet = new Set<string>();

    if (commitNode) {
      // BFS up to depth 2 from the commit node
      const adjacency = new Map<string, Set<string>>();
      const nodeById = new Map<string, any>();
      sgNodes.forEach(n => nodeById.set(n.id, n));
      sgEdges.forEach(e => {
        if (!adjacency.has(e.from)) adjacency.set(e.from, new Set());
        if (!adjacency.has(e.to)) adjacency.set(e.to, new Set());
        adjacency.get(e.from)!.add(e.to);
        adjacency.get(e.to)!.add(e.from);
      });
      const queue: Array<{ id: string; depth: number }> = [{ id: commitNode.id, depth: 0 }];
      filteredIdSet.add(commitNode.id);

      while (queue.length) {
        const { id, depth } = queue.shift()!;
        if (depth >= 1) continue; // at least one hop from commit
        const neighbors = adjacency.get(id) || new Set();
        neighbors.forEach(nb => {
          if (filteredIdSet.has(nb)) return;
          const nbNode = nodeById.get(nb);
          const nbLabels = Array.isArray(nbNode?.labels) ? nbNode.labels : [nbNode?.labels];
          // Exclude other commit nodes beyond the root commit
          if (depth >= 0 && nb !== commitNode.id && nbLabels?.includes('GitCommit')) return;
          filteredIdSet.add(nb);
          queue.push({ id: nb, depth: depth + 1 });
        });
      }
      // If changed files list is present, ensure they’re included
      sgNodes.forEach(n => { if (isFileNode(n) && nodeMatchesFile(n)) filteredIdSet.add(n.id); });
    } else {
      // Seed set based on changed files
      const seedNodes = sgNodes.filter((n) => isFileNode(n) && nodeMatchesFile(n));
      const seedIds = new Set(seedNodes.map(n => n.id));
      const neighborIds = new Set<string>();
      sgEdges.forEach(e => { if (seedIds.has(e.from)) neighborIds.add(e.to); if (seedIds.has(e.to)) neighborIds.add(e.from); });
      [...seedIds].forEach(id => filteredIdSet.add(id));
      [...neighborIds].forEach(id => filteredIdSet.add(id));
    }

    // Build filtered nodes/edges (bounded for readability)
    const filteredNodes = sgNodes.filter(n => filteredIdSet.has(n.id)).slice(0, 300);
    const allowedIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = sgEdges.filter(e => allowedIds.has(e.from) && allowedIds.has(e.to));

    // If nothing matched, fallback to showing a tiny commit->files sketch for current commit only
    if (filteredNodes.length === 0 && snapshot?.commit?.files_changed?.length) {
      const cx = 60;
      const cy = 60;
      const fallbackGroup = graphLayer.append('g').attr('transform', `translate(${cx},${cy})`);
      fallbackGroup.append('circle').attr('r', 10).attr('fill', '#8b5cf6');
      (snapshot.commit.files_changed || []).slice(0, 12).forEach((p, idx) => {
        const angle = (idx / 12) * Math.PI * 2;
        const x = Math.cos(angle) * 80;
        const y = Math.sin(angle) * 80;
        fallbackGroup.append('line').attr('x1', 0).attr('y1', 0).attr('x2', x).attr('y2', y).attr('stroke', '#94a3b8');
        fallbackGroup.append('circle').attr('cx', x).attr('cy', y).attr('r', 6).attr('fill', '#10b981').attr('stroke', '#fff');
      });
    } else {
      // Force-directed graph rendering
      const innerW = availableDendrogramWidth - 20;
      const innerH = availableDendrogramHeight - 60;

      const labelOf = (n: any) => {
        const labs = Array.isArray(n.labels) ? n.labels : [n.labels];
        return labs && labs.length ? labs[0] : (n.type || 'Node');
      };

      const isCommentPath = (p?: string) => {
        if (!p) return false;
        const lower = p.toLowerCase();
        return [
          '.md', '.mdx', '.markdown', '.rst', '.txt', '.adoc', '.asciidoc',
          '.org', '.rtf'
        ].some(ext => lower.endsWith(ext));
      };

      const nodeKind = (n: any): 'commit' | 'code' | 'comment' | 'other' => {
        const lab = labelOf(n);
        if (lab === 'GitCommit') return 'commit';
        if (lab === 'Document') return 'comment';
        if (lab === 'File') {
          const path = n.properties?.path || String(n.id);
          return isCommentPath(path) ? 'comment' : 'code';
        }
        return 'other';
      };

      const typeColors: Record<string, string> = {
        commit: '#6366f1',
        code: '#3b82f6',
        comment: '#10b981',
        other: '#a78bfa'
      };

      const edgeColors: Record<string, string> = {
        TOUCHED: '#60a5fa',
        CONTAINS_CHUNK: '#10b981',
        CONTAINS_DOC: '#8b5cf6',
        REFERENCES: '#f59e0b',
        PART_OF: '#94a3b8',
        IMPLEMENTS: '#06b6d4',
        EVOLVES_FROM: '#84cc16',
        REFACTORED_TO: '#f97316',
        DEPRECATED_BY: '#dc2626',
        MENTIONS: '#6366f1',
        RELATED: '#94a3b8'
      };

      // Initial positions (preserve if provided)
      filteredNodes.forEach((n, i) => {
        const hash = String(n.id).split('').reduce((a: number, b: string) => ((a << 5) - a) + b.charCodeAt(0) | 0, 0);
        if (typeof (n as any).x !== 'number') (n as any).x = Math.abs(hash % innerW);
        if (typeof (n as any).y !== 'number') (n as any).y = Math.abs((hash >> 8) % innerH);
        (n as any).fx = undefined;
        (n as any).fy = undefined;
      });

      const simulation = d3.forceSimulation(filteredNodes as any)
        .force('link', d3.forceLink(filteredEdges as any).id((d: any) => d.id).distance(40).strength(0.6))
        .force('charge', d3.forceManyBody().strength(-180))
        .force('center', d3.forceCenter(innerW / 2, innerH / 2))
        .force('collision', d3.forceCollide().radius(18));

      const links = graphLayer.append('g').attr('class', 'links')
        .selectAll('line').data(filteredEdges).enter().append('line')
        .attr('stroke', (d: any) => edgeColors[d.type] || '#cbd5e1')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 1.5);

      const nodes = graphLayer.append('g').attr('class', 'nodes')
        .selectAll('g').data(filteredNodes).enter().append('g').attr('class', 'node');

      nodes.append('circle')
        .attr('r', (d: any) => {
          const lab = labelOf(d);
          const kind = nodeKind(d);
          const base = kind === 'commit' ? 9 : kind === 'code' || kind === 'comment' ? 8 : 7;
          return base + Math.min(6, (d.size || 1) * 2);
        })
        .attr('fill', (d: any) => typeColors[nodeKind(d)] || '#9ca3af')
        .attr('stroke', (d: any) => {
          // Highlight changed files
          const isF = isFileNode(d) && nodeMatchesFile(d);
          if (commitNode && d.id === commitNode.id) return '#8b5cf6';
          return isF ? '#0ea5e9' : '#fff';
        })
        .attr('stroke-width', (d: any) => {
          if (commitNode && d.id === commitNode.id) return 3.5;
          return (isFileNode(d) && nodeMatchesFile(d)) ? 3 : 1.5;
        })
        .attr('opacity', 0.95);

      if (showLabels) {
        nodes.append('text')
          .attr('y', 2)
          .attr('text-anchor', 'middle')
          .attr('font-size', '9px')
          .attr('fill', '#111827')
          .text((d: any) => {
            const lab = labelOf(d);
            if (lab === 'File') {
              const p = d.properties?.path || d.id;
              return String(p).split('/').pop()?.slice(0, 14) || String(d.id).slice(0, 10);
            }
            if (lab === 'GitCommit') return String(d.properties?.hash || d.id).slice(0, 7);
            return String(d.id).slice(0, 10);
          });
      }

      // Drag interactions
      const drag = d3.drag<SVGGElement, any>()
        .on('start', (event, d: any) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d: any) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d: any) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; });
      nodes.call(drag as any);

      simulation.on('tick', () => {
        links
          .attr('x1', (d: any) => (d as any).source.x)
          .attr('y1', (d: any) => (d as any).source.y)
          .attr('x2', (d: any) => (d as any).target.x)
          .attr('y2', (d: any) => (d as any).target.y);
        nodes.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
      });

      // Legend
      const legend = graphRoot.append('g').attr('class', 'legend').attr('transform', `translate(${availableDendrogramWidth - 160}, 0)`);
      const entries = [ ['Commit', typeColors.commit], ['Code File', typeColors.code], ['Comment File', typeColors.comment] ] as Array<[string,string]>;
      entries.forEach(([key, color], i) => {
        const lg = legend.append('g').attr('transform', `translate(0, ${i * 18})`);
        lg.append('circle').attr('r', 6).attr('fill', color);
        lg.append('text').attr('x', 12).attr('y', 4).attr('font-size', '11px').attr('fill', '#1f2937').text(key);
      });

      const status = graphRoot.append('g').attr('transform', `translate(0, ${availableDendrogramHeight - 24})`);
      status.append('text').attr('font-size', '11px').attr('fill', '#6b7280')
        .text(`Commit ${currentHash.substring(0,7)} • Nodes: ${filteredNodes.length} • Edges: ${filteredEdges.length} • Changed files: ${filesSet.size}`);
    }

    // Create dendrograms for ALL commits up to current point (layered approach)
    const commitWidth = availableDendrogramWidth / Math.max(currentIndex + 1, 1);
    const minCommitWidth = 60; // allow many commits to be visible
    
    const renderMiniatures = false;
    for (let commitIdx = 0; commitIdx <= currentIndex && renderMiniatures; commitIdx++) {
      const actualCommitWidth = Math.max(commitWidth, minCommitWidth);
      const commitX = commitIdx * actualCommitWidth + actualCommitWidth / 2;
      const commitY = 50; // Position commits at top, let dendrograms grow downward
      const isCurrentCommit = commitIdx === currentIndex;
      
      // Determine the correct snapshot for this commit index
      const commitSnapshot: EvolutionSnapshot = (snapshots && snapshots[commitIdx]) ? snapshots[commitIdx] : snapshot;

      // Files visible at this commit with emphasis on files changed in this commit
      let commitFiles: FileNode[] = [];
      const changedSet = new Set<string>(commitSnapshot.commit.files_changed || []);
      const changedFiles = commitSnapshot.files.filter(f => changedSet.has(f.path));
      const contextFiles = commitSnapshot.files
        .filter(f => !changedSet.has(f.path))
        .slice(0, Math.max(4, 12 - changedFiles.length));
      commitFiles = [...changedFiles, ...contextFiles];
      
      // If still empty, fallback to first N files from this commit snapshot
      if (commitFiles.length === 0) {
        commitFiles = commitSnapshot.files.slice(0, Math.min(8, commitSnapshot.files.length));
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
        Math.max(actualCommitWidth, minCommitWidth) * 0.35,
        (availableDendrogramHeight - 120) * 0.65,
        dendrogramWidth * 0.2
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

      // Miniature subgraph for this commit: commit node linked to file nodes (size=LOC/size, color by type)
      const maxFilesPerCommit = 28;
      const gridCols = 7;
      const gridCell = Math.min(26, Math.max(18, (actualCommitWidth * 0.85) / gridCols));
      const commitToGridGap = 28;
      const filesToDraw = commitFiles.slice(0, maxFilesPerCommit);
      filesToDraw.forEach((file, idx) => {
        const row = Math.floor(idx / gridCols);
        const col = idx % gridCols;
        const gx = (col - (gridCols - 1) / 2) * gridCell;
        const gy = commitToGridGap + row * gridCell;

        const isDoc = (file as any).type === 'doc' || (file as any).type === 'document';
        const baseColor = isDoc ? fileTypeColors['doc'] : fileTypeColors['code'];
        const lines = (file as any).lines ?? (file as any).size ?? 0;
        const fallback = Math.max(1, (file.modifications || file.commit_count || 1));
        const r = Math.min(12, Math.max(5, lines > 0 ? Math.sqrt(lines) * 0.5 : 4 + Math.log2(fallback + 1) * 2));

        // link from commit to file
        commitDendrogramGroup.append('line')
          .attr('x1', 0)
          .attr('y1', 0)
          .attr('x2', gx)
          .attr('y2', gy)
          .attr('stroke', baseColor)
          .attr('stroke-width', 1.2)
          .attr('opacity', opacity * 0.55);

        const fg = commitDendrogramGroup.append('g')
          .attr('transform', `translate(${gx}, ${gy})`);

        const circle = fg.append('circle')
          .attr('r', r)
          .attr('fill', baseColor)
          .attr('stroke', 'white')
          .attr('stroke-width', 1.2)
          .attr('opacity', opacity * (file.status === 'deleted' ? 0.5 : 0.95));

        if (enableAnimation && isCurrentCommit) {
          circle.attr('r', 0)
            .transition().duration(300).delay(80 + idx * 15)
            .attr('r', r);
        }

        if (showLabels && r >= 8 && idx < 6) {
          const fileName = file.path.split('/').pop() || file.path;
          fg.append('text')
            .attr('y', r + 10)
            .attr('text-anchor', 'middle')
            .attr('font-size', '9px')
            .attr('fill', baseColor)
            .text(fileName.substring(0, 10));
        }
      });
    } // End of commit loop


    // No extra generation label overlay — keep canvas clean

  }, [mounted, snapshot, height, width, showLabels, enableAnimation, previousSnapshot, isPlaying, currentIndex, totalSnapshots, subgraphData, changedFiles]);

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
    <VStack spacing={4} align="stretch" bg="white" borderRadius="lg" p={6} boxShadow="sm">
      {/* Header with Controls (simplified) */}
      <HStack justify="space-between" align="center">
        <Heading size="md" color="purple.600">Structural Evolution</Heading>
        {(onPlayPause || onNext || onPrevious) && (
          <HStack spacing={2}>
            {onPrevious && (
              <Button onClick={onPrevious} size="sm" variant="outline" isDisabled={currentIndex === 0}>Previous</Button>
            )}
            {onPlayPause && (
              <Button onClick={onPlayPause} colorScheme="purple" size="sm">{isPlaying ? 'Pause' : 'Play'}</Button>
            )}
            {onNext && (
              <Button onClick={onNext} size="sm" variant="outline" isDisabled={currentIndex === totalSnapshots - 1}>Next</Button>
            )}
          </HStack>
        )}
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

        {/* Bottom Panel: Structural Subgraph */}
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
            Structural Evolution • Generation {currentIndex + 1}
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
