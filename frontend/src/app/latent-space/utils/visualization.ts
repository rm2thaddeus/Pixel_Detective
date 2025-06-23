import { UMAPPoint } from '../types/latent-space';

/**
 * Beautiful Color Palettes for Clustering Visualization
 * Inspired by modern data visualization best practices and accessibility
 */

// Modern categorical color palettes
export const COLOR_PALETTES = {
  // Viridis-inspired sequential palette (excellent for accessibility)
  viridis: [
    [68, 1, 84, 220],      // Deep purple
    [72, 35, 116, 220],    // Purple-blue
    [64, 67, 135, 220],    // Blue-purple
    [52, 94, 141, 220],    // Blue
    [41, 120, 142, 220],   // Teal-blue
    [32, 144, 140, 220],   // Teal
    [34, 167, 132, 220],   // Green-teal
    [68, 190, 112, 220],   // Green
    [121, 209, 81, 220],   // Yellow-green
    [189, 222, 38, 220],   // Yellow
  ],

  // Observable 10 - Modern and distinctive
  observable: [
    [79, 129, 189, 220],   // Blue
    [242, 142, 43, 220],   // Orange  
    [237, 101, 72, 220],   // Red
    [111, 207, 151, 220],  // Cyan
    [255, 184, 184, 220],  // Pink
    [176, 122, 161, 220],  // Purple
    [255, 157, 166, 220],  // Light blue
    [118, 183, 178, 220],  // Green
    [156, 117, 95, 220],   // Brown
    [186, 176, 172, 220],  // Gray
  ],

  // Retro Metro - Vibrant and engaging
  retroMetro: [
    [234, 85, 69, 220],    // Vibrant red
    [244, 106, 155, 220],  // Hot pink
    [239, 155, 32, 220],   // Orange
    [237, 191, 51, 220],   // Yellow
    [237, 225, 91, 220],   // Light yellow
    [189, 207, 50, 220],   // Lime green
    [135, 188, 69, 220],   // Green
    [39, 174, 239, 220],   // Sky blue
    [179, 61, 198, 220],   // Purple
    [255, 163, 0, 220],    // Bright orange
  ],

  // Dutch Field - Bold and modern
  dutchField: [
    [230, 0, 73, 220],     // Hot pink
    [11, 180, 255, 220],   // Sky blue
    [80, 233, 145, 220],   // Lime green
    [230, 216, 0, 220],    // Yellow
    [155, 25, 245, 220],   // Purple
    [255, 163, 0, 220],    // Orange
    [220, 10, 180, 220],   // Magenta
    [179, 212, 255, 220],  // Light blue
    [0, 191, 160, 220],    // Teal
    [255, 200, 87, 220],   // Light orange
  ],

  // River Nights - Sophisticated and deep
  riverNights: [
    [179, 0, 0, 220],      // Dark red
    [124, 17, 88, 220],    // Dark purple
    [68, 33, 175, 220],    // Blue-purple
    [26, 83, 255, 220],    // Blue
    [13, 136, 230, 220],   // Light blue
    [0, 183, 199, 220],    // Cyan
    [90, 212, 90, 220],    // Green
    [139, 224, 78, 220],   // Light green
    [235, 220, 120, 220],  // Yellow
    [255, 180, 100, 220],  // Orange
  ],

  // Spring Pastels - Gentle and approachable
  springPastels: [
    [253, 127, 111, 220],  // Soft coral
    [126, 176, 213, 220],  // Soft blue
    [178, 224, 97, 220],   // Soft green
    [189, 126, 190, 220],  // Soft purple
    [255, 181, 90, 220],   // Soft orange
    [255, 238, 101, 220],  // Soft yellow
    [190, 185, 219, 220],  // Lavender
    [253, 204, 229, 220],  // Pink
    [139, 211, 199, 220],  // Mint
    [255, 218, 185, 220],  // Peach
  ],

  // Scientific Journal Palettes
  nature: [
    [27, 158, 119, 220],   // Teal
    [217, 95, 2, 220],     // Orange
    [117, 112, 179, 220],  // Purple
    [231, 41, 138, 220],   // Pink
    [102, 166, 30, 220],   // Green
    [230, 171, 2, 220],    // Yellow
    [166, 118, 29, 220],   // Brown
    [102, 102, 102, 220],  // Gray
    [35, 139, 69, 220],    // Dark green
    [0, 116, 217, 220],    // Blue
  ],

  // 2025 Trend Colors - Contemporary and fresh
  trend2025: [
    [237, 234, 177, 220],  // Celestial Yellow
    [81, 44, 58, 220],     // Cherry Lacquer
    [113, 173, 186, 220],  // Retro Blue
    [255, 101, 79, 220],   // Neon Flare
    [76, 85, 120, 220],    // Future Dusk
    [255, 180, 162, 220],  // Warm coral
    [147, 197, 114, 220],  // Fresh green
    [204, 187, 225, 220],  // Soft lavender
    [255, 218, 121, 220],  // Golden yellow
    [108, 142, 191, 220],  // Dusty blue
  ]
} as const;

export type ColorPaletteName = keyof typeof COLOR_PALETTES;

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
 * Generate distinct colors for clusters using specified palette
 */
export function generateClusterColors(
  numClusters: number, 
  paletteName: ColorPaletteName = 'observable'
): [number, number, number, number][] {
  const palette = COLOR_PALETTES[paletteName];
  const colors: [number, number, number, number][] = [];
  
  for (let i = 0; i < numClusters; i++) {
    if (i < palette.length) {
      // Use predefined palette colors
      colors.push([...palette[i]] as [number, number, number, number]);
    } else {
      // Generate additional colors using golden ratio for larger datasets
      const goldenRatio = 0.618033988749895;
      const hue = ((i - palette.length) * goldenRatio) % 1;
      const saturation = 0.65 + (Math.sin(i * 2.1) * 0.15);
      const lightness = 0.55 + (Math.sin(i * 1.3) * 0.1);
    colors.push(hslToRgb(hue, saturation, lightness, 220));
    }
  }
  
  return colors;
}

/**
 * Get color for a specific cluster point with enhanced visual appeal
 */
export function getClusterColor(
  point: UMAPPoint, 
  totalClusters: number,
  paletteName: ColorPaletteName = 'observable'
): [number, number, number, number] {
  // Outliers get a distinct red color with transparency for visibility
  if (point.is_outlier === true || point.cluster_id === -1) {
    return [255, 87, 87, 220]; // Bright red with good visibility
  }
  
  // Unassigned points get a distinctive blue color (Observable blue)
  if (point.cluster_id === undefined || point.cluster_id === null) {
    return [79, 129, 189, 220]; // Observable blue - clearly visible
  }
  
  // Use the specified color palette
  const palette = COLOR_PALETTES[paletteName];
  const clusterIndex = point.cluster_id % palette.length;
  
  if (clusterIndex < palette.length) {
    return [...palette[clusterIndex]] as [number, number, number, number];
  }
  
  // Fallback for clusters beyond palette size
  const goldenRatio = 0.618033988749895;
  const hue = (point.cluster_id * goldenRatio) % 1;
  return hslToRgb(hue, 0.7, 0.6, 220);
}

/**
 * Get enhanced color with selection and hover states
 */
export function getEnhancedClusterColor(
  point: UMAPPoint,
  totalClusters: number,
  selectedClusterId: number | null = null,
  isHovered: boolean = false,
  paletteName: ColorPaletteName = 'observable'
): [number, number, number, number] {
  // Handle unassigned points (no cluster)
  if (point.cluster_id === undefined || point.cluster_id === null || point.cluster_id === -1) {
    if (point.is_outlier === true) {
      return [220, 53, 69, 255]; // Bootstrap danger red for outliers
    }
    // Use Observable blue for unassigned points (more visible than gray)
    return [79, 129, 189, 255]; // Observable blue - clearly visible
  }

  const palette = COLOR_PALETTES[paletteName];
  const baseColor = palette[point.cluster_id % palette.length];
  let color: [number, number, number, number] = [...baseColor, 255];

  // Selection state - brighter
  if (selectedClusterId !== null && point.cluster_id === selectedClusterId) {
    color = enhanceColorBrightness(color, 1.2);
  }

  // Hover state - even brighter with white stroke effect
  if (isHovered) {
    color = enhanceColorBrightness(color, 1.4);
  }

  // Outlier enhancement
  if (point.is_outlier === true) {
    color = mixColors(color, [255, 193, 7, 255], 0.3); // Mix with warning yellow
  }

  return color;
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
 * Calculate optimal viewport state for DeckGL with improved centering
 */
export function getOptimalViewState(points: UMAPPoint[]) {
  const bounds = calculateBounds(points, 0.15); // Slightly more padding
  const centerX = (bounds.minX + bounds.maxX) / 2;
  const centerY = (bounds.minY + bounds.maxY) / 2;
  
  // Calculate zoom to fit all points with some padding
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  const maxDimension = Math.max(width, height, 0.1);
  
  // Improved zoom calculation for better initial view
  const zoom = Math.log2(Math.min(600 / maxDimension, 12));
  
  return {
    longitude: centerX,
    latitude: centerY,
    zoom: Math.max(1, Math.min(zoom, 15)), // Better zoom range
    pitch: 0,
    bearing: 0,
  };
}

/**
 * Filter points based on viewport for performance optimization
 */
export function filterPointsInViewport(
  points: UMAPPoint[], 
  viewState: unknown, 
  margin: number = 0.2
): UMAPPoint[] {
  // For large datasets, we can implement viewport culling here
  // For now, return all points but this can be optimized later
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = { viewState, margin }; // Acknowledge unused parameters
  
  if (points.length < 1000) {
    return points;
  }

  // TODO: Implement actual viewport culling for large datasets
  return points;
}

/**
 * Debounce function for performance optimization
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
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
export function throttle<T extends (...args: unknown[]) => unknown>(
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
    if (point.is_outlier === true) {
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
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format duration in milliseconds to human readable
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

/**
 * Check if point is in viewport (for future optimization)
 */
export function isPointInViewport(
  point: UMAPPoint,
  viewState: unknown,
  margin: number = 0.1
): boolean {
  // Placeholder for viewport culling implementation
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = { point, viewState, margin }; // Acknowledge unused parameters
  return true;
}

/**
 * Get palette preview colors for UI selection
 */
export function getPalettePreview(paletteName: ColorPaletteName, count: number = 5): string[] {
  const palette = COLOR_PALETTES[paletteName];
  return palette.slice(0, count).map(color => 
    `rgb(${color[0]}, ${color[1]}, ${color[2]})`
  );
}

/**
 * Get palette description for UI
 */
export function getPaletteDescription(paletteName: ColorPaletteName): string {
  const descriptions: Record<ColorPaletteName, string> = {
    viridis: "Accessibility-friendly sequential palette, excellent for colorblind users",
    observable: "Modern and distinctive colors, balanced for professional use",
    retroMetro: "Vibrant and energetic palette, great for presentations and demos",
    dutchField: "Bold and contemporary colors with high contrast",
    riverNights: "Sophisticated deep hues for elegant, professional visualizations",
    springPastels: "Gentle and approachable colors, perfect for soft, friendly interfaces",
    nature: "Scientific journal inspired palette with natural, trustworthy colors",
    trend2025: "Contemporary 2025 trend colors, fresh and modern aesthetic"
  };
  
  return descriptions[paletteName] || "Custom color palette";
}

/**
 * Animation and transition utilities for smooth visual effects
 */
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function interpolateColor(
  color1: [number, number, number, number],
  color2: [number, number, number, number],
  factor: number
): [number, number, number, number] {
  const t = Math.max(0, Math.min(1, factor));
  return [
    Math.round(color1[0] + (color2[0] - color1[0]) * t),
    Math.round(color1[1] + (color2[1] - color1[1]) * t),
    Math.round(color1[2] + (color2[2] - color1[2]) * t),
    Math.round(color1[3] + (color2[3] - color1[3]) * t),
  ];
}

/**
 * Enhance color brightness by a factor
 */
export function enhanceColorBrightness(
  color: [number, number, number, number],
  factor: number
): [number, number, number, number] {
  return [
    Math.min(255, Math.round(color[0] * factor)),
    Math.min(255, Math.round(color[1] * factor)),
    Math.min(255, Math.round(color[2] * factor)),
    color[3]
  ];
}

/**
 * Mix two colors by a factor
 */
export function mixColors(
  color1: [number, number, number, number],
  color2: [number, number, number, number],
  factor: number
): [number, number, number, number] {
  return interpolateColor(color1, color2, factor);
}

/**
 * Create animated color transitions for cluster selections
 */
export function getAnimatedClusterColor(
  point: UMAPPoint,
  totalClusters: number,
  selectedClusterId: number | null = null,
  isHovered: boolean = false,
  animationProgress: number = 0,
  paletteName: ColorPaletteName = 'observable'
): [number, number, number, number] {
  const baseColor = getEnhancedClusterColor(point, totalClusters, selectedClusterId, isHovered, paletteName);
  
  if (animationProgress > 0 && (point.cluster_id === selectedClusterId || isHovered)) {
    const highlightColor: [number, number, number, number] = [255, 255, 255, 255];
    const easedProgress = easeInOutCubic(animationProgress);
    return interpolateColor(baseColor, highlightColor, easedProgress * 0.3);
  }
  
  return baseColor;
}

/**
 * Calculate cluster density for enhanced visualization
 */
export function calculateClusterDensity(
  points: UMAPPoint[],
  clusterId: number,
  radius: number = 1.0
): number {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = radius; // Acknowledge unused parameter
  
  const clusterPoints = points.filter(p => p.cluster_id === clusterId);
  if (clusterPoints.length <= 1) return 0;
  
  let totalDistance = 0;
  let pairCount = 0;
  
  for (let i = 0; i < clusterPoints.length; i++) {
    for (let j = i + 1; j < clusterPoints.length; j++) {
      const dx = clusterPoints[i].x - clusterPoints[j].x;
      const dy = clusterPoints[i].y - clusterPoints[j].y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      totalDistance += distance;
      pairCount++;
    }
  }
  
  const avgDistance = totalDistance / pairCount;
  return clusterPoints.length / (avgDistance * avgDistance * Math.PI);
}

/**
 * Generate cluster summary statistics for tooltips
 */
export function getClusterSummary(points: UMAPPoint[], clusterId: number): {
  size: number;
  density: number;
  centroid: { x: number; y: number };
  spread: number;
} {
  const clusterPoints = points.filter(p => p.cluster_id === clusterId);
  
  if (clusterPoints.length === 0) {
    return { size: 0, density: 0, centroid: { x: 0, y: 0 }, spread: 0 };
  }
  
  // Calculate centroid
  const centroid = {
    x: clusterPoints.reduce((sum, p) => sum + p.x, 0) / clusterPoints.length,
    y: clusterPoints.reduce((sum, p) => sum + p.y, 0) / clusterPoints.length,
  };
  
  // Calculate spread (standard deviation from centroid)
  const spread = Math.sqrt(
    clusterPoints.reduce((sum, p) => {
      const dx = p.x - centroid.x;
      const dy = p.y - centroid.y;
      return sum + (dx * dx + dy * dy);
    }, 0) / clusterPoints.length
  );
  
  const density = calculateClusterDensity(points, clusterId);
  
  return {
    size: clusterPoints.length,
    density,
    centroid,
    spread,
  };
}

/**
 * Enhanced palette descriptions with more detail
 */
export function getEnhancedPaletteDescription(paletteName: ColorPaletteName): {
  name: string;
  description: string;
  bestFor: string;
  accessibility: 'excellent' | 'good' | 'fair';
} {
  const descriptions = {
    viridis: {
      name: 'Viridis',
      description: 'Perceptually uniform sequential palette inspired by scientific visualization',
      bestFor: 'Accessibility-first applications, scientific data',
      accessibility: 'excellent' as const,
    },
    observable: {
      name: 'Observable',
      description: 'Modern categorical palette with high contrast and distinctiveness',
      bestFor: 'General purpose clustering, presentations',
      accessibility: 'good' as const,
    },
    retroMetro: {
      name: 'Retro Metro',
      description: 'Vibrant and energetic colors perfect for engaging visualizations',
      bestFor: 'Creative applications, marketing dashboards',
      accessibility: 'good' as const,
    },
    dutchField: {
      name: 'Dutch Field',
      description: 'Bold contemporary colors with strong visual impact',
      bestFor: 'Modern applications, bold presentations',
      accessibility: 'fair' as const,
    },
    riverNights: {
      name: 'River Nights',
      description: 'Sophisticated deep tones with elegant gradients',
      bestFor: 'Professional reports, dark themes',
      accessibility: 'good' as const,
    },
    springPastels: {
      name: 'Spring Pastels',
      description: 'Gentle, approachable colors that are easy on the eyes',
      bestFor: 'Healthcare, educational applications',
      accessibility: 'good' as const,
    },
    nature: {
      name: 'Nature',
      description: 'Scientific journal-inspired palette with natural tones',
      bestFor: 'Academic publications, research presentations',
      accessibility: 'excellent' as const,
    },
    trend2025: {
      name: 'Trend 2025',
      description: 'Contemporary colors reflecting current design trends',
      bestFor: 'Modern apps, trendy visualizations',
      accessibility: 'good' as const,
    },
  };
  
  return descriptions[paletteName];
} 