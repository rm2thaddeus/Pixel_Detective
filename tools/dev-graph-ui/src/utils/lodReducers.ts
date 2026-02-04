// Level of Detail (LoD) reducers for graph visualization
// Provides different levels of detail based on zoom level and viewport

export interface LoDConfig {
  zoomLevel: number;
  viewportWidth: number;
  viewportHeight: number;
  nodeCount: number;
  edgeCount: number;
}

export interface LoDResult {
  showLabels: boolean;
  showEdges: boolean;
  showEdgeLabels: boolean;
  showNodeDetails: boolean;
  maxNodes: number;
  maxEdges: number;
  labelThreshold: number;
  edgeThreshold: number;
}

export interface Node {
  id: string;
  label?: string;
  size?: number;
  x?: number;
  y?: number;
  type?: string;
  [key: string]: any;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type?: string;
  [key: string]: any;
}

// Calculate LoD based on zoom level and data size
export function calculateLoD(config: LoDConfig): LoDResult {
  const { zoomLevel, viewportWidth, viewportHeight, nodeCount, edgeCount } = config;
  
  // Base thresholds
  const baseNodeThreshold = 1000;
  const baseEdgeThreshold = 2000;
  const baseLabelThreshold = 0.5; // zoom level threshold for showing labels
  const baseEdgeLabelThreshold = 0.7; // zoom level threshold for showing edge labels
  
  // Calculate viewport area
  const viewportArea = viewportWidth * viewportHeight;
  const baseViewportArea = 1920 * 1080; // Reference viewport size
  const viewportScale = viewportArea / baseViewportArea;
  
  // Adjust thresholds based on viewport size
  const adjustedNodeThreshold = Math.floor(baseNodeThreshold * viewportScale);
  const adjustedEdgeThreshold = Math.floor(baseEdgeThreshold * viewportScale);
  
  // Calculate zoom-based visibility
  const showLabels = zoomLevel >= baseLabelThreshold;
  const showEdgeLabels = zoomLevel >= baseEdgeLabelThreshold;
  const showEdges = zoomLevel >= 0.3; // Always show edges at reasonable zoom levels
  const showNodeDetails = zoomLevel >= 0.8; // Show detailed node info at high zoom
  
  // Calculate max elements based on performance
  const maxNodes = Math.min(
    nodeCount,
    Math.floor(adjustedNodeThreshold * (1 + zoomLevel * 0.5)) // Allow more nodes at higher zoom
  );
  const maxEdges = Math.min(
    edgeCount,
    Math.floor(adjustedEdgeThreshold * (1 + zoomLevel * 0.3)) // Allow more edges at higher zoom
  );
  
  return {
    showLabels,
    showEdges,
    showEdgeLabels,
    showNodeDetails,
    maxNodes,
    maxEdges,
    labelThreshold: baseLabelThreshold,
    edgeThreshold: baseEdgeLabelThreshold,
  };
}

// Filter nodes based on LoD
export function filterNodesByLoD(nodes: Node[], lod: LoDResult): Node[] {
  if (nodes.length <= lod.maxNodes) {
    return nodes;
  }
  
  // Priority-based filtering:
  // 1. Keep nodes with higher degree (more connections)
  // 2. Keep nodes with larger size
  // 3. Keep nodes with specific types (sprints, documents)
  // 4. Keep nodes in the center of the viewport
  
  const nodeMap = new Map(nodes.map(node => [node.id, node]));
  const nodeDegrees = new Map<string, number>();
  
  // Calculate node degrees (simplified - would need edge data in real implementation)
  nodes.forEach(node => {
    nodeDegrees.set(node.id, 0);
  });
  
  // Sort by priority
  const sortedNodes = [...nodes].sort((a, b) => {
    const aDegree = nodeDegrees.get(a.id) || 0;
    const bDegree = nodeDegrees.get(b.id) || 0;
    const aSize = a.size || 1;
    const bSize = b.size || 1;
    
    // Priority order: degree, size, type importance
    const aTypePriority = getTypePriority(a.type);
    const bTypePriority = getTypePriority(b.type);
    
    if (aDegree !== bDegree) return bDegree - aDegree;
    if (aSize !== bSize) return bSize - aSize;
    return bTypePriority - aTypePriority;
  });
  
  return sortedNodes.slice(0, lod.maxNodes);
}

// Filter edges based on LoD
export function filterEdgesByLoD(edges: Edge[], lod: LoDResult): Edge[] {
  if (edges.length <= lod.maxEdges) {
    return edges;
  }
  
  // Priority-based filtering:
  // 1. Keep edges between visible nodes
  // 2. Keep edges with higher importance (specific types)
  // 3. Keep edges with labels
  
  const sortedEdges = [...edges].sort((a, b) => {
    const aTypePriority = getEdgeTypePriority(a.type);
    const bTypePriority = getEdgeTypePriority(b.type);
    const aHasLabel = !!a.label;
    const bHasLabel = !!b.label;
    
    if (aTypePriority !== bTypePriority) return bTypePriority - aTypePriority;
    if (aHasLabel !== bHasLabel) return aHasLabel ? -1 : 1;
    return 0;
  });
  
  return sortedEdges.slice(0, lod.maxEdges);
}

// Get node type priority for filtering
function getTypePriority(type?: string): number {
  if (!type) return 0;
  
  const priorities: Record<string, number> = {
    'sprint': 10,
    'document': 8,
    'requirement': 7,
    'chunk': 6,
    'file': 5,
    'commit': 4,
    'author': 3,
    'tag': 2,
    'other': 1,
  };
  
  return priorities[type.toLowerCase()] || 0;
}

// Get edge type priority for filtering
function getEdgeTypePriority(type?: string): number {
  if (!type) return 0;
  
  const priorities: Record<string, number> = {
    'CONTAINS_DOC': 10,
    'CONTAINS_CHUNK': 9,
    'MENTIONS': 8,
    'IMPLEMENTS': 7,
    'REFERENCES': 6,
    'MODIFIES': 5,
    'AUTHORED_BY': 4,
    'COMMITTED_IN': 3,
    'TAGGED_WITH': 2,
    'other': 1,
  };
  
  return priorities[type] || 0;
}

// Reduce label complexity based on zoom level
export function reduceLabelComplexity(labels: string[], zoomLevel: number): string[] {
  if (zoomLevel >= 0.8) {
    return labels; // Show full labels at high zoom
  }
  
  if (zoomLevel >= 0.5) {
    return labels.map(label => {
      if (label.length > 20) {
        return label.substring(0, 17) + '...';
      }
      return label;
    });
  }
  
  if (zoomLevel >= 0.3) {
    return labels.map(label => {
      if (label.length > 10) {
        return label.substring(0, 7) + '...';
      }
      return label;
    });
  }
  
  // Very low zoom - show only first few characters
  return labels.map(label => {
    if (label.length > 5) {
      return label.substring(0, 2) + '...';
    }
    return label;
  });
}

// Calculate optimal node size based on zoom level
export function calculateNodeSize(baseSize: number, zoomLevel: number): number {
  const minSize = 2;
  const maxSize = 20;
  
  // Scale size with zoom level
  const scaledSize = baseSize * (0.5 + zoomLevel * 0.5);
  
  return Math.max(minSize, Math.min(maxSize, scaledSize));
}

// Calculate optimal edge width based on zoom level
export function calculateEdgeWidth(baseWidth: number, zoomLevel: number): number {
  const minWidth = 0.5;
  const maxWidth = 3;
  
  // Scale width with zoom level
  const scaledWidth = baseWidth * (0.3 + zoomLevel * 0.7);
  
  return Math.max(minWidth, Math.min(maxWidth, scaledWidth));
}

// Get color intensity based on zoom level
export function calculateColorIntensity(baseIntensity: number, zoomLevel: number): number {
  // Increase color intensity at higher zoom levels
  return Math.min(1, baseIntensity * (0.5 + zoomLevel * 0.5));
}
