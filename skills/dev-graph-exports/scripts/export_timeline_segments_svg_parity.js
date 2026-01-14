const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { createRequire } = require('module');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const uiNodeModules = path.join(repoRoot, 'tools', 'dev-graph-ui', 'node_modules');
const requireFromUi = createRequire(path.join(uiNodeModules, 'noop.js'));

const d3 = requireFromUi('d3');
const { JSDOM } = requireFromUi('jsdom');
const { Resvg } = requireFromUi('@resvg/resvg-js');

const BG = '#1a202c';
const FILE_COLORS = {
  code: '#3b82f6',
  document: '#f59e0b',
  config: '#8b5cf6',
  other: '#6b7280',
};

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}: ${res.status}`);
  }
  const text = await res.text();
  return JSON.parse(text);
}

function getFolderPath(filePath) {
  const parts = filePath.split('/');
  if (parts.length <= 1) return '/';
  return parts.slice(0, -1).join('/');
}

function getTopLevelFolder(filePath) {
  const normalized = filePath.replace(/\\/g, '/');
  const idx = normalized.indexOf('/');
  return idx === -1 ? normalized : normalized.slice(0, idx);
}

function buildGraph(commits, currentTimeIndex, config, prevPositions) {
  const nodeMap = new Map();
  const linkList = [];
  const startIndex = Math.max(0, Math.min(config.rangeStartIndex ?? 0, commits.length - 1));
  const upto = Math.max(startIndex, Math.min(currentTimeIndex, commits.length - 1));

  for (let i = startIndex; i <= upto; i += 1) {
    const c = commits[i];
    const totalLoc = (c.files || []).reduce((sum, f) => {
      const loc = f.lines_after ?? f.loc ?? f.size ?? 0;
      return sum + Math.max(0, loc);
    }, 0);
    const rCommit = config.sizeByLOC ? Math.min(20, Math.max(8, Math.sqrt(totalLoc) * 0.2 + 8)) : 12;
    nodeMap.set(c.hash, { id: c.hash, nodeType: 'commit', radius: rCommit, loc: totalLoc, filesTouched: (c.files || []).length });
    if (i > startIndex) {
      linkList.push({ source: commits[i - 1].hash, target: c.hash, kind: 'chain' });
    }
  }

  const allFiles = new Map();
  for (let i = startIndex; i <= upto; i += 1) {
    const c = commits[i];
    for (const f of c.files || []) {
      if (!f.path) continue;
      if (!allFiles.has(f.path)) {
        allFiles.set(f.path, { file: f, commits: new Set() });
      }
      allFiles.get(f.path).commits.add(c.hash);
    }
  }

  const sortedAll = Array.from(allFiles.entries()).sort((a, b) => b[1].commits.size - a[1].commits.size);
  const docEntries = sortedAll.filter((entry) => (entry[1].file.type === 'document'));
  const nonDocEntries = sortedAll.filter((entry) => (entry[1].file.type !== 'document'));
  const budgetForFiles = Math.max(0, config.maxNodes - commits.length - 5);
  const sortedFiles = docEntries.concat(nonDocEntries).slice(0, budgetForFiles);

  if (config.showFolderGroups) {
    const folderMap = new Map();
    for (const [, { file }] of sortedFiles) {
      const folderPath = getFolderPath(file.path);
      if (!folderMap.has(folderPath)) {
        folderMap.set(folderPath, { files: [], totalSize: 0 });
      }
      const folder = folderMap.get(folderPath);
      folder.files.push(file);
      folder.totalSize += file.lines_after ?? file.loc ?? file.size ?? 0;
    }

    for (const [folderPath, folderData] of folderMap) {
      if (folderPath === '/') continue;
      const folderId = `folder:${folderPath}`;
      const folderSize = Math.min(28, Math.max(8, Math.sqrt(folderData.totalSize) * 0.25 + folderData.files.length * 0.4));
      nodeMap.set(folderId, {
        id: folderId,
        nodeType: 'folder',
        radius: config.sizeByLOC ? folderSize : 12,
        folderPath,
        fileCount: folderData.files.length,
        loc: folderData.totalSize,
      });

      for (let i = startIndex; i <= upto; i += 1) {
        const commitFiles = new Set((commits[i]?.files || []).map((f) => f.path));
        const hasFiles = folderData.files.some((f) => commitFiles.has(f.path));
        if (hasFiles) {
          linkList.push({ source: commits[i].hash, target: folderId, kind: 'touch' });
        }
      }
    }

    const recentCommitFiles = new Set((commits[upto]?.files || []).map((f) => f.path));
    const importantFiles = sortedFiles.slice(0, Math.min(20, Math.floor(config.maxNodes / 5)));

    for (const [filePath, { file, commits: fileCommits }] of sortedFiles) {
      const isRecent = recentCommitFiles.has(filePath);
      const isImportant = importantFiles.some((entry) => entry[0] === filePath);
      if (isRecent || isImportant) {
        const loc = Math.max(0, file.lines_after ?? file.loc ?? file.size ?? 0);
        const r = config.sizeByLOC ? Math.min(16, Math.max(4, loc > 0 ? Math.sqrt(loc) * 0.3 : 6)) : 8;
        nodeMap.set(filePath, {
          id: filePath,
          nodeType: 'file',
          fileKind: file.type,
          radius: r,
          loc,
          folderPath: getTopLevelFolder(file.path),
          touchCount: fileCommits.size,
        });

        for (let i = startIndex; i <= upto; i += 1) {
          const commitFiles = new Set((commits[i]?.files || []).map((f) => f.path));
          if (commitFiles.has(filePath)) {
            linkList.push({ source: commits[i].hash, target: filePath, kind: 'touch' });
          }
        }
      }
    }
  }

  const allNodes = Array.from(nodeMap.values());
  const commitNodes = allNodes.filter((n) => n.nodeType === 'commit');
  const docNodes = allNodes.filter((n) => n.nodeType === 'file' && n.fileKind === 'document');
  const mustKeep = new Set(commitNodes.concat(docNodes).map((n) => n.id));
  const others = allNodes.filter((n) => !mustKeep.has(n.id));

  const finalNodes = commitNodes.concat(docNodes);
  for (const n of others) {
    if (finalNodes.length >= Math.max(config.maxNodes, finalNodes.length)) break;
    finalNodes.push(n);
  }

  const allowed = new Set(finalNodes.map((n) => n.id));
  const finalLinks = linkList.filter((l) => allowed.has(l.source) && allowed.has(l.target));

  for (const node of finalNodes) {
    const prev = prevPositions.get(node.id);
    if (prev) {
      node.x = prev.x;
      node.y = prev.y;
    }
  }

  return { nodes: finalNodes, links: finalLinks, startIndex, upto };
}

function computeColors(nodes, commits, config) {
  const folderDomains = new Set();
  nodes.forEach((n) => { if (n.nodeType === 'file' && n.folderPath) folderDomains.add(n.folderPath); });
  const folderColor = d3.scaleOrdinal(d3.schemeSet3 || d3.schemeTableau10).domain(Array.from(folderDomains));
  const activityDomain = d3.extent(nodes.filter((n) => n.nodeType === 'file').map((n) => n.touchCount || 0));
  const activityColor = d3.scaleSequential(d3.interpolatePlasma).domain([activityDomain[0] || 0, activityDomain[1] || 1]);
  const commitFlowColor = d3.scaleSequential(d3.interpolateTurbo).domain([0, Math.max(1, commits.length - 1)]);

  return { folderColor, activityColor, commitFlowColor };
}

function nodeFill(d, colors, commits, config) {
  if (d.nodeType === 'commit') {
    const idx = Math.max(0, commits.findIndex((c) => c.hash === d.id));
    return config.colorMode === 'commit-flow' ? colors.commitFlowColor(idx) : '#8b5cf6';
  }
  if (d.nodeType === 'folder') {
    if (['folder', 'commit-flow', 'activity'].includes(config.colorMode)) return colors.folderColor(d.folderPath || 'folders');
    if (config.colorMode === 'none') return '#a98a2b';
    return '#f59e0b';
  }
  if (config.colorMode === 'type') return FILE_COLORS[d.fileKind] || '#6b7280';
  if (config.colorMode === 'activity') return colors.activityColor(d.touchCount || 0);
  if (['folder', 'commit-flow'].includes(config.colorMode)) return colors.folderColor(d.folderPath || 'files');
  return '#6b7280';
}

function complement(hex) {
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
}

function renderSvg(commits, graph, config, prevPositions) {
  const dom = new JSDOM('<!doctype html><html><body></body></html>');
  const body = d3.select(dom.window.document.body);
  const svg = body.append('svg');
  svg.attr('width', config.width).attr('height', config.height);
  svg.attr('xmlns', 'http://www.w3.org/2000/svg');
  svg.append('rect')
    .attr('width', config.width)
    .attr('height', config.height)
    .attr('fill', BG)
    .attr('rx', 8)
    .attr('ry', 8);

  const rotator = svg.append('g').attr('class', 'rotator');
  const root = rotator.append('g').attr('class', 'root');
  const edgesLayer = root.append('g').attr('class', 'edges');
  const nodesLayer = root.append('g').attr('class', 'nodes');

  const sim = d3.forceSimulation(graph.nodes)
    .force('link', d3.forceLink(graph.links).id((d) => d.id).distance((l) => {
      if (l.kind === 'chain') return 120;
      if (l.kind === 'touch') return 60;
      return 40;
    }).strength((l) => {
      if (l.kind === 'chain') return 0.9;
      if (l.kind === 'touch') return 0.4;
      return 0.2;
    }))
    .force('charge', d3.forceManyBody().strength((d) => {
      if (d.nodeType === 'commit') return -200;
      if (d.nodeType === 'folder') return -150;
      return -100;
    }))
    .force('center', d3.forceCenter(config.width / 2, config.height / 2))
    .force('collision', d3.forceCollide().radius((d) => d.radius + 12))
    .force('x', d3.forceX((d) => {
      if (d.nodeType === 'commit') {
        const commitIndex = commits.findIndex((c) => c.hash === d.id);
        return (commitIndex / Math.max(1, commits.length - 1)) * config.width;
      }
      return config.width / 2;
    }).strength(0.3))
    .force('y', d3.forceY((d) => {
      if (d.nodeType === 'folder') return config.height * 0.3;
      if (d.nodeType === 'file') return config.height * 0.7;
      return config.height / 2;
    }).strength(0.2))
    .alphaDecay(0.05)
    .velocityDecay(0.4);

  sim.stop();
  for (let i = 0; i < 150; i += 1) {
    sim.tick();
  }

  for (const node of graph.nodes) {
    prevPositions.set(node.id, { x: node.x, y: node.y });
  }

  const colors = computeColors(graph.nodes, commits, config);
  const currentCommitFiles = new Set((commits[graph.upto]?.files || []).map((f) => f.path));

  const chainOpacity = (0.3 + 0.7 * Math.max(0, Math.min(1, config.edgeEmphasis))) * (config.focusedView ? 1 : 0.9);
  const fileOpacity = (0.02 + 0.28 * Math.max(0, Math.min(1, config.edgeEmphasis))) * (config.focusedView ? 1 : 1.2);
  const chainWidth = 1 + 2 * Math.max(0, Math.min(1, config.edgeEmphasis));
  const fileWidth = 0.4 + 0.8 * Math.max(0, Math.min(1, config.edgeEmphasis));

  edgesLayer.selectAll('line')
    .data(graph.links)
    .enter()
    .append('line')
    .attr('x1', (d) => d.source.x)
    .attr('y1', (d) => d.source.y)
    .attr('x2', (d) => d.target.x)
    .attr('y2', (d) => d.target.y)
    .attr('stroke', (d) => d.kind === 'chain' ? '#8b5cf6' : '#4a5568')
    .attr('stroke-width', (d) => d.kind === 'chain' ? chainWidth : fileWidth)
    .attr('opacity', (d) => d.kind === 'chain' ? chainOpacity : fileOpacity)
    .attr('stroke-dasharray', (d) => d.kind === 'chain' ? 'none' : '4,4');

  const nodeSel = nodesLayer.selectAll('g.node')
    .data(graph.nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', (d) => `translate(${d.x}, ${d.y})`);

  nodeSel.append('circle')
    .attr('r', (d) => d.radius)
    .attr('fill', (d) => nodeFill(d, colors, commits, config))
    .attr('stroke', '#fff')
    .attr('stroke-width', (d) => d.nodeType === 'folder' ? 2.5 : 1.5)
    .attr('opacity', (d) => {
      if (!config.focusedView) return 1.0;
      if (d.nodeType === 'commit') {
        const commitIndex = commits.findIndex((c) => c.hash === d.id);
        if (commitIndex === graph.upto) return 1.0;
        if (Math.abs(commitIndex - graph.upto) <= 2) return 0.8;
        return 0.3;
      }
      if (graph.upto >= 0 && graph.upto < commits.length) {
        const isInCurrent = currentCommitFiles.has(d.id);
        return isInCurrent ? 1.0 : 0.2;
      }
      return 0.6;
    });

  if (config.highlightDocs) {
    nodeSel.filter((d) => d.nodeType === 'file' && d.fileKind === 'document')
      .append('circle')
      .attr('class', 'doc-ring')
      .attr('fill', 'none')
      .attr('stroke-width', 2)
      .attr('opacity', 0.9)
      .attr('r', (d) => d.radius + 3)
      .attr('stroke', (d) => complement(nodeFill(d, colors, commits, config)));
  }

  nodeSel.filter((d) => d.nodeType === 'folder')
    .append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('font-size', '10px')
    .attr('font-weight', 'bold')
    .attr('fill', '#fff')
    .text((d) => d.fileCount || '');

  return svg.node().outerHTML;
}

function rasterizeSvg(svgText, pngPath, width) {
  const resvg = new Resvg(svgText, { fitTo: { mode: 'width', value: width } });
  const pngData = resvg.render().asPng();
  fs.writeFileSync(pngPath, pngData);
}

function runFfmpeg(pattern, output, fps) {
  const args = ['-y', '-framerate', String(fps), '-i', pattern, '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output];
  const res = spawnSync('ffmpeg', args, { stdio: 'inherit' });
  if (res.status !== 0) throw new Error('ffmpeg failed');
}

function runGif(pattern, output) {
  const args = ['-y', '-framerate', '6', '-i', pattern, '-vf', 'fps=10,scale=960:-1:flags=lanczos', output];
  const res = spawnSync('ffmpeg', args, { stdio: 'inherit' });
  if (res.status !== 0) throw new Error('ffmpeg gif failed');
}

function ensureDeps() {
  const missing = [];
  try { requireFromUi('d3'); } catch { missing.push('d3'); }
  try { requireFromUi('jsdom'); } catch { missing.push('jsdom'); }
  try { requireFromUi('@resvg/resvg-js'); } catch { missing.push('@resvg/resvg-js'); }
  if (missing.length) {
    throw new Error(`Missing dependencies in tools/dev-graph-ui/node_modules: ${missing.join(', ')}`);
  }
}

async function main() {
  ensureDeps();
  const api = process.argv.includes('--api') ? process.argv[process.argv.indexOf('--api') + 1] : 'http://localhost:8080';
  const outputDir = process.argv.includes('--output-dir') ? process.argv[process.argv.indexOf('--output-dir') + 1] : path.join(repoRoot, 'exports', 'dev-graph');
  const limit = process.argv.includes('--limit') ? parseInt(process.argv[process.argv.indexOf('--limit') + 1], 10) : 5000;
  const maxFiles = process.argv.includes('--max-files') ? parseInt(process.argv[process.argv.indexOf('--max-files') + 1], 10) : 50;
  const fps = process.argv.includes('--fps') ? parseInt(process.argv[process.argv.indexOf('--fps') + 1], 10) : 6;

  const data = await fetchJson(`${api.replace(/\/$/, '')}/api/v1/dev-graph/evolution/timeline?limit=${limit}&max_files_per_commit=${maxFiles}`);
  const commits = data.commits || [];
  if (!commits.length) throw new Error('No commits returned');

  const config = {
    width: 1200,
    height: 600,
    maxNodes: 100,
    showFolderGroups: true,
    focusedView: true,
    sizeByLOC: true,
    colorMode: 'folder',
    highlightDocs: true,
    edgeEmphasis: 0.4,
    rangeStartIndex: 0,
  };

  const ranges = [
    { start: 0, end: Math.min(69, commits.length - 1), label: 'commits-1-70' },
    { start: 69, end: Math.min(199, commits.length - 1), label: 'commits-70-200' },
  ];
  if (commits.length > 199) ranges.push({ start: 199, end: commits.length - 1, label: 'commits-200-plus' });

  fs.mkdirSync(outputDir, { recursive: true });
  const prevPositions = new Map();

  for (const segment of ranges) {
    const frameDir = path.join(outputDir, 'timeline-frames', segment.label);
    const rasterDir = path.join(frameDir, '_raster');
    fs.mkdirSync(frameDir, { recursive: true });
    fs.mkdirSync(rasterDir, { recursive: true });

    for (let idx = segment.start; idx <= segment.end; idx += 1) {
      const graph = buildGraph(commits, idx, config, prevPositions);
      const svgText = renderSvg(commits, graph, config, prevPositions);
      const frameIndex = idx - segment.start + 1;
      const svgPath = path.join(frameDir, `frame_${String(frameIndex).padStart(4, '0')}.svg`);
      const pngPath = path.join(rasterDir, `frame_${String(frameIndex).padStart(4, '0')}.png`);
      fs.writeFileSync(svgPath, svgText, 'utf8');
      rasterizeSvg(svgText, pngPath, config.width);
    }

    runFfmpeg(path.join(rasterDir, 'frame_%04d.png'), path.join(outputDir, `timeline-${segment.label}.mp4`), fps);
    runGif(path.join(rasterDir, 'frame_%04d.png'), path.join(outputDir, `timeline-${segment.label}.gif`));

    fs.readdirSync(rasterDir).forEach((file) => fs.unlinkSync(path.join(rasterDir, file)));
    fs.rmdirSync(rasterDir);
  }

  console.log('SVG parity timeline exports complete.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
