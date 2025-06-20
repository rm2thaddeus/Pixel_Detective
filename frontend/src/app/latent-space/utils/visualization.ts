import { UMAPPoint } from '../types/latent-space';

/**
 * Convert HSL color to RGB array
 */
export function hslToRgb(h: number, s: number, l: number, a: number = 255): [number, number, number, number] {
  let r, g, b;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }

  return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255), a];
}

/**
 * Generate distinct colors for clusters using golden ratio
 */
export function generateClusterColors(numClusters: number): [number, number, number, number][] {
  const colors: [number, number, number, number][] = [];
  const goldenRatio = 0.618033988749895;
  
  for (let i = 0; i < numClusters; i++) {
    const hue = (i * goldenRatio) % 1;
    const saturation = 0.7 + (Math.sin(i * 2.3) * 0.2); // Vary saturation slightly
    const lightness = 0.5 + (Math.sin(i * 1.7) * 0.15); // Vary lightness slightly
    colors.push(hslToRgb(hue, saturation, lightness, 220));
  }
  
  return colors;
}

/**
 * Get color for a specific cluster point
 */
export function getClusterColor(point: UMAPPoint, totalClusters: number): [number, number, number, number] {
  // Outliers get a distinct red color with transparency
  if (point.is_outlier || point.cluster_id === -1) {
    return [255, 107, 107, 180]; // Red with transparency
  }
  
  // Unassigned points get grey
  if (point.cluster_id === undefined || point.cluster_id === null) {
    return [150, 150, 150, 200]; // Grey
  }
  
  // Generate distinct colors for clusters using HSL color space
  const hue = (point.cluster_id / Math.max(1, totalClusters - 1)) * 0.85; // Use 85% of hue spectrum to avoid red
  return hslToRgb(hue, 0.7, 0.6, 220);
}

/**
 * Calculate bounds for points with padding
 */
export function calculateBounds(points: UMAPPoint[], padding: number = 0.1) {
  if (points.length === 0) return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
  
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  
  points.forEach(point => {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  });
  
  // Add padding
  const xRange = maxX - minX;
  const yRange = maxY - minY;
  const xPadding = xRange * padding;
  const yPadding = yRange * padding;
  
  return {
    minX: minX - xPadding,
    maxX: maxX + xPadding,
    minY: minY - yPadding,
    maxY: maxY + yPadding,
  };
}

/**
 * Calculate optimal viewport state for DeckGL
 */
export function getOptimalViewState(points: UMAPPoint[]) {
  const bounds = calculateBounds(points);
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  
  // Calculate zoom to fit all points with some padding
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const maxDimension = Math.max(width, height, 0.1); // Avoid division by zero
  
  // Base zoom calculation with better scaling
  const zoom = Math.log2(Math.min(400 / maxDimension, 10));
  
  return {
    longitude: centerX,
    latitude: centerY,
    zoom: Math.max(0, Math.min(zoom, 15)), // Clamp zoom between 0 and 15
    pitch: 0,
    bearing: 0,
  };
}

/**
 * Filter points based on viewport for performance optimization
 */
export function filterPointsInViewport(
  points: UMAPPoint[], 
  viewState: any, 
  margin: number = 0.2
): UMAPPoint[] {
  // For large datasets, we can implement viewport culling here
  // For now, return all points but this can be optimized later
  if (points.length < 1000) {
    return points;
  }

  // TODO: Implement actual viewport culling for large datasets
  // This would calculate which points are visible and return only those
  return points;
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Throttle function for performance optimization
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Calculate statistics for clustering analysis
 */
export function calculateClusterStatistics(points: UMAPPoint[]) {
  const clusterCounts: Record<number, number> = {};
  let outlierCount = 0;
  let assignedCount = 0;

  points.forEach(point => {
    if (point.is_outlier) {
      outlierCount++;
    } else if (point.cluster_id !== undefined && point.cluster_id !== null && point.cluster_id !== -1) {
      clusterCounts[point.cluster_id] = (clusterCounts[point.cluster_id] || 0) + 1;
      assignedCount++;
    }
  });

  const clusterIds = Object.keys(clusterCounts).map(Number).sort((a, b) => a - b);
  const averageClusterSize = clusterIds.length > 0 ? assignedCount / clusterIds.length : 0;
  const largestCluster = Math.max(...Object.values(clusterCounts), 0);
  const smallestCluster = Math.min(...Object.values(clusterCounts), 0);

  return {
    totalPoints: points.length,
    totalClusters: clusterIds.length,
    assignedPoints: assignedCount,
    outlierPoints: outlierCount,
    unassignedPoints: points.length - assignedCount - outlierCount,
    averageClusterSize: Math.round(averageClusterSize * 100) / 100,
    largestClusterSize: largestCluster,
    smallestClusterSize: smallestCluster,
    clusterCounts,
    clusterIds,
  };
}

/**
 * Format numbers for display
 */
export function formatNumber(num: number, decimals: number = 2): string {
  return Number(num.toFixed(decimals)).toString();
}

/**
 * Format duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
}

/**
 * Check if a point is in the current viewport (for optimization)
 */
export function isPointInViewport(
  point: UMAPPoint,
  viewState: any,
  margin: number = 0.1
): boolean {
  // Simple bounding box check - can be improved with actual projection
  const { longitude, latitude, zoom } = viewState;
  const scale = Math.pow(2, zoom);
  const viewWidth = 2 / scale;
  const viewHeight = 2 / scale;
  
  const minX = longitude - viewWidth / 2 - margin;
  const maxX = longitude + viewWidth / 2 + margin;
  const minY = latitude - viewHeight / 2 - margin;
  const maxY = latitude + viewHeight / 2 + margin;
  
  return point.x >= minX && point.x <= maxX && point.y >= minY && point.y <= maxY;
} 