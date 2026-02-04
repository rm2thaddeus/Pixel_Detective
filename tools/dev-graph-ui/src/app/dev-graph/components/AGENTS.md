# Dev Graph Components - Agent Guidelines

## Overview
This directory contains reusable visualization components for the Dev Graph UI. The primary component is `StructureAnalysisGraph`, a D3-based force-directed graph renderer with filtering and interaction capabilities.

---

## StructureAnalysisGraph Component

### Purpose
Renders interactive force-directed graph visualizations of code structure relationships. Supports filtering by node/relationship types, zooming, panning, and edge toggling.

**File:** `StructureAnalysisGraph.tsx` (730 lines)

### Component API

```typescript
interface StructureAnalysisGraphProps {
  // Data source configuration
  metrics: StructureMetrics;              // Graph metrics (node counts, edge counts)
  useRealData?: boolean;                  // Fetch real data from backend
  overrideData?: {                        // Pre-filtered data (takes precedence)
    nodes: any[];
    edges: any[];
  } | null;
  
  // Filtering
  selectedRelationType?: string;          // Filter by relationship type
  selectedSourceType?: string;            // Filter by source node type
  selectedTargetType?: string;            // Filter by target node type
  highlightFilter?: {                     // Visual highlighting
    kind: 'future-nodes' | 'future-relationships' | 'by-type';
    value?: string;
  } | null;
  
  // Layout configuration
  height?: number;                        // Canvas height (default: 600)
  width?: number;                         // Canvas width (default: 1000)
  maxNodes?: number;                      // Node limit (default: 20000)
  
  // Display options
  showClusters?: boolean;                 // Show clustering visualization
  showLabels?: boolean;                   // Show node labels
  
  // Callbacks
  onSvgReady?: (svg: SVGSVGElement | null) => void;  // For export functionality
}
```

### Usage Patterns

**Pattern 1: Default View (Component Fetches Data)**
```tsx
<StructureAnalysisGraph
  metrics={metrics}
  useRealData={true}
  maxNodes={100}
  selectedSourceType=""
  selectedTargetType=""
/>
```
Component will fetch from `/api/v1/dev-graph/graph/subgraph` and display default view.

**Pattern 2: Pre-Filtered Data (Recommended)**
```tsx
// Parent component queries backend
const query = `MATCH (File)-[r]->(Chunk) RETURN File, r, Chunk LIMIT 100`;
const result = await fetch('/api/v1/dev-graph/graph/cypher', {
  method: 'POST',
  body: JSON.stringify({ query, max_nodes: 100 })
});
const data = await result.json();

// Pass to component
<StructureAnalysisGraph
  metrics={metrics}
  useRealData={false}                    // Don't fetch
  overrideData={{                        // Use this instead
    nodes: data.nodes,
    edges: data.relationships
  }}
  selectedSourceType=""                  // No client-side filtering
  selectedTargetType=""
/>
```
Component uses provided data directly without fetching or filtering.

**Pattern 3: Synthetic Data (Testing)**
```tsx
<StructureAnalysisGraph
  metrics={mockMetrics}
  useRealData={false}
  overrideData={null}
/>
```
Component generates synthetic data based on metrics.

---

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  StructureAnalysisGraph Component                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Data Source Priority (line 128-189):                    │
│     ┌──────────────────────────────────────┐               │
│     │ if (overrideData)                    │ ← Priority 1  │
│     │   → Use provided nodes/edges         │               │
│     ├──────────────────────────────────────┤               │
│     │ else if (useRealData && realData)    │ ← Priority 2  │
│     │   → Use fetched data from backend    │               │
│     ├──────────────────────────────────────┤               │
│     │ else                                 │ ← Priority 3  │
│     │   → Generate synthetic data          │               │
│     └──────────────────────────────────────┘               │
│                                                              │
│  2. Client-Side Filtering (line 195-203):                   │
│     ┌──────────────────────────────────────┐               │
│     │ Filter links by:                     │               │
│     │  - selectedRelationType              │               │
│     │  - selectedSourceType (from node)    │               │
│     │  - selectedTargetType (to node)      │               │
│     └──────────────────────────────────────┘               │
│     ⚠️ WARNING: Only use when NOT using overrideData!      │
│                                                              │
│  3. Safety Pass (line 206-209):                             │
│     ┌──────────────────────────────────────┐               │
│     │ Ensure both endpoints exist in nodes │               │
│     │ Filter out orphaned edges            │               │
│     └──────────────────────────────────────┘               │
│                                                              │
│  4. D3 Rendering (line 267-580):                            │
│     ┌──────────────────────────────────────┐               │
│     │ Create force simulation              │               │
│     │ Render links (lines)                 │               │
│     │ Render nodes (circles)               │               │
│     │ Add zoom/pan behavior                │               │
│     │ Add hover interactions               │               │
│     └──────────────────────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Critical Implementation Details

#### 1. Data Fetching Hook (Line 79-100)

```typescript
useEffect(() => {
  if (!(useRealData && mounted)) return;
  
  const controller = new AbortController();
  const apiUrl = process.env.NEXT_PUBLIC_DEV_GRAPH_API_URL || 'http://localhost:8080';
  const url = `${apiUrl}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}&include_counts=true`;
  
  (async () => {
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      
      setRealData({
        nodes: (data?.nodes ?? []).map((n: any) => ({ ...n, id: String(n.id) })),
        edges: data?.edges ?? []
      });
    } catch (error: any) {
      if (error?.name === 'AbortError') return;
      console.error('Failed to fetch real graph data:', error);
    }
  })();
  
  return () => controller.abort();  // Cleanup
}, [useRealData, mounted, maxNodes]);
```

**Key Points:**
- Only runs when `useRealData={true}` and component is mounted
- Uses AbortController for cleanup (prevents memory leaks)
- Normalizes node IDs to strings (Neo4j returns various ID formats)
- Falls back gracefully on errors

**⚠️ CRITICAL:** When parent provides `overrideData`, set `useRealData={false}` to prevent double-fetching!

---

#### 2. Data Normalization (Line 128-189)

**OverrideData Path (Line 128-153):**
```typescript
if (overrideData && Array.isArray(overrideData.nodes)) {
  nodes = (overrideData.nodes as any[]).map((node: any) => ({
    id: String(node.id),                                   // Normalize ID
    type: node.type || node.labels?.[0] || 'Unknown',     // Extract type
    degree: 0,                                             // Calculate below
    centrality: 0,
    isCentral: false,
    x: node.x || Math.random() * innerWidth,              // Initial position
    y: node.y || Math.random() * innerHeight
  }));
  
  const edges = (overrideData.edges as any[]);
  links = edges.map((edge: any) => ({
    source: String(edge.from ?? edge.source),             // Handle both formats
    target: String(edge.to ?? edge.target),
    type: edge.type || 'RELATES_TO'
  }));
  
  // Calculate node degrees (connectivity)
  const nodeDegrees = new Map<string, number>();
  links.forEach((l: any) => {
    nodeDegrees.set(l.source, (nodeDegrees.get(l.source) || 0) + 1);
    nodeDegrees.set(l.target, (nodeDegrees.get(l.target) || 0) + 1);
  });
  
  nodes.forEach((n: any) => {
    n.degree = nodeDegrees.get(n.id) || 0;
    n.centrality = n.degree / Math.max(1, nodes.length - 1);
    n.isCentral = n.degree > 5;
  });
}
```

**Key Transformations:**
- **ID Normalization:** Always convert to string (Neo4j uses element_id, legacy id, etc.)
- **Type Extraction:** Try `type` field, then `labels[0]`, fallback to 'Unknown'
- **Edge Format:** Handle both `{from, to}` and `{source, target}` formats
- **Degree Calculation:** Count incoming + outgoing edges per node
- **Centrality:** Normalized degree (0-1 scale)

---

#### 3. Client-Side Filtering (Line 195-209)

```typescript
// Build node lookup map
const nodeById = new Map<string, any>();
nodes.forEach((n: any) => nodeById.set(String(n.id), n));

// Filter links by relationship type and endpoint types
let filteredLinks = links.filter((link: any) => {
  const s = nodeById.get(String(link.source));
  const t = nodeById.get(String(link.target));
  if (!s || !t) return false;  // Skip if endpoint missing
  
  // Filter by relationship type
  if (selectedRelationType && String(link.type) !== selectedRelationType) return false;
  
  // Filter by source node type
  if (selectedSourceType && String(s.type) !== selectedSourceType) return false;
  
  // Filter by target node type
  if (selectedTargetType && String(t.type) !== selectedTargetType) return false;
  
  return true;
});

// Safety pass: Ensure both endpoints exist in node set
const nodeIdSet = new Set(nodes.map((n: any) => String(n.id)));
const safeLinks = filteredLinks.filter((l: any) => 
  nodeIdSet.has(String(l.source)) && nodeIdSet.has(String(l.target))
);
```

**⚠️ WARNING:** This filtering is ONLY appropriate when:
1. Component is fetching its own data (`useRealData={true}`)
2. No `overrideData` is provided
3. Parent wants component to handle filtering

**When using `overrideData`:**
- Set filter props to empty strings: `selectedSourceType=""`
- Data is already filtered by parent
- Skip client-side filtering to avoid double-filtering

---

#### 4. D3 Force Simulation (Line 267-340)

```typescript
// Create force simulation
const simulation = d3.forceSimulation(filteredNodes)
  .force("charge", d3.forceManyBody().strength(-300))        // Node repulsion
  .force("center", d3.forceCenter(innerWidth / 2, innerHeight / 2))  // Centering
  .force("link", d3.forceLink(safeLinks)                     // Link attraction
    .id((d: any) => d.id)
    .distance(80)
  )
  .force("collision", d3.forceCollide().radius(20));         // Collision avoidance

// Render links (edges)
const link = g.append("g")
  .selectAll("line")
  .data(safeLinks)
  .join("line")
  .attr("stroke", "#999")
  .attr("stroke-opacity", 0.6)
  .attr("stroke-width", (d: any) => Math.sqrt(d.value || 1))
  .style("display", showEdges ? "block" : "none");

// Color scale for node types
const nodeTypes = [...new Set(filteredNodes.map((n: any) => n.type))];
const colorScale = d3.scaleOrdinal()
  .domain(nodeTypes)
  .range(d3.schemeCategory10);

// Render nodes (circles)
const node = g.append("g")
  .selectAll("circle")
  .data(filteredNodes)
  .join("circle")
  .attr("r", (d: any) => (d.isCentral ? 12 : 8))            // Central nodes larger
  .attr("fill", (d: any) => colorScale(d.type))
  .attr("stroke", "#fff")
  .attr("stroke-width", 2)
  .call(drag(simulation));                                   // Enable dragging

// Update positions on each simulation tick
simulation.on("tick", () => {
  link
    .attr("x1", (d: any) => d.source.x)
    .attr("y1", (d: any) => d.source.y)
    .attr("x2", (d: any) => d.target.x)
    .attr("y2", (d: any) => d.target.y);

  node
    .attr("cx", (d: any) => d.x)
    .attr("cy", (d: any) => d.y);
});
```

**Force Explanations:**
- **charge (-300):** Nodes repel each other (negative = repulsion)
- **center:** Pulls graph toward canvas center
- **link:** Attracts connected nodes (distance: 80px ideal)
- **collision:** Prevents nodes from overlapping (radius: 20px buffer)

**Performance Tuning:**
- **<100 nodes:** Default settings work well
- **100-250 nodes:** Increase charge strength to -400
- **250-500 nodes:** Reduce link distance to 60, limit ticks
- **500+ nodes:** Consider disabling force simulation, use static layout

---

#### 5. Interaction Handlers (Line 450-550)

**Zoom & Pan:**
```typescript
const zoom = d3.zoom()
  .scaleExtent([0.1, 10])           // Min/max zoom levels
  .on("zoom", (event) => {
    g.attr("transform", event.transform);
  });

svg.call(zoom);
```

**Drag Nodes:**
```typescript
function drag(simulation: any) {
  function dragstarted(event: any) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event: any) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event: any) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;  // Release fixed position
    event.subject.fy = null;
  }

  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}
```

**Hover Effects (Line 484-540):**
```typescript
node
  .on("mouseover", function(event, d) {
    // Dim other nodes
    node.attr("opacity", (n: any) => n.id === d.id ? 1 : 0.3);
    
    // Highlight connected links
    link.attr("opacity", (l: any) => 
      l.source.id === d.id || l.target.id === d.id ? 1 : 0.1
    );
    
    // Show hover label
    g.append('text')
      .attr('class', 'hover-label')
      .attr('x', event.x + 15)
      .attr('y', event.y - 10)
      .attr('fill', 'white')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text(`${d.type}: ${d.id}`);
  })
  .on("mouseout", function() {
    // Reset opacity
    node.attr("opacity", 1);
    link.attr("opacity", 0.6);
    
    // Remove hover label
    g.selectAll('.hover-label').remove();
  });
```

---

### Common Issues & Solutions

#### Issue: Edges Not Rendering

**Symptoms:**
- Console: `StructureAnalysisGraph: no edges returned for current filters`
- Nodes visible, no lines
- `safeLinks.length === 0`

**Debugging:**
```typescript
// Add debug logging (line 216-228)
console.log('Filtering debug:', {
  totalNodes: nodes.length,
  totalLinks: links.length,
  filteredLinks: filteredLinks.length,
  safeLinks: safeLinks.length,
  selectedRelationType,
  selectedSourceType,
  selectedTargetType,
  sampleLinks: links.slice(0, 3),
  nodeTypes: [...new Set(nodes.map(n => n.type))]
});
```

**Common Causes:**
1. **Double-filtering:** Parent filtered + component filtered = no matches
2. **Type mismatch:** `node.type !== node.labels[0]`
3. **String conversion:** `edge.from` is number, `node.id` is string
4. **Orphaned edges:** Edge references node not in `nodes` array

**Fix:**
```typescript
// When using overrideData, disable client filtering
<StructureAnalysisGraph
  overrideData={data}
  selectedSourceType=""     // Empty = no filtering
  selectedTargetType=""
  selectedRelationType=""
/>
```

---

#### Issue: Performance Degradation with Large Graphs

**Symptoms:**
- Slow rendering (>5 seconds)
- Browser freezes
- CPU at 100%

**Solutions:**

**1. Limit Simulation Iterations:**
```typescript
const simulation = d3.forceSimulation(nodes)
  .force(...)
  .stop();  // Don't auto-run

// Run fixed iterations
for (let i = 0; i < 100; i++) {
  simulation.tick();
}

// Then render static positions (no animation)
```

**2. Reduce Visual Complexity:**
```typescript
// Smaller nodes
.attr("r", 5)  // Instead of 8-12

// Thinner edges
.attr("stroke-width", 1)  // Instead of calculated

// No hover effects
// Comment out .on("mouseover", ...)
```

**3. Use Canvas Instead of SVG:**
```typescript
// For 500+ nodes, switch to canvas rendering
const canvas = d3.select(canvasRef.current);
const context = canvas.node().getContext('2d');

simulation.on("tick", () => {
  context.clearRect(0, 0, width, height);
  
  // Draw links
  links.forEach(link => {
    context.beginPath();
    context.moveTo(link.source.x, link.source.y);
    context.lineTo(link.target.x, link.target.y);
    context.stroke();
  });
  
  // Draw nodes
  nodes.forEach(node => {
    context.beginPath();
    context.arc(node.x, node.y, 5, 0, 2 * Math.PI);
    context.fill();
  });
});
```

---

#### Issue: Hydration Mismatch

**Symptoms:**
- "Text content did not match" error
- Component renders twice
- Inconsistent initial state

**Solution:**
```typescript
const [mounted, setMounted] = useState(false);

useEffect(() => {
  setMounted(true);
}, []);

if (!mounted) {
  return <Spinner />;  // Show loading on server
}

// Only render D3 on client
```

---

### Testing Guidelines

**Unit Tests (Future):**
```typescript
describe('StructureAnalysisGraph', () => {
  it('uses overrideData when provided', () => {
    const mockData = {
      nodes: [{ id: '1', labels: ['File'] }],
      edges: [{ from: '1', to: '2', type: 'CONTAINS' }]
    };
    
    const { container } = render(
      <StructureAnalysisGraph
        metrics={mockMetrics}
        overrideData={mockData}
        useRealData={true}  // Should be ignored
      />
    );
    
    // Verify no API call made
    expect(fetch).not.toHaveBeenCalled();
    
    // Verify nodes rendered
    expect(container.querySelectorAll('circle').length).toBe(1);
  });
});
```

**Visual Regression Tests:**
- Screenshot with 50 nodes, 100 edges
- Screenshot with filters applied
- Screenshot with dense graph (200+ nodes)
- Compare against baseline images

---

## Other Components

### TimelineExperience Component
**File:** `../timeline/TimelineExperience.tsx`

**Purpose:** SVG-based timeline visualization of git commits over time.

**Key Features:**
- Timeline scrubber for date range selection
- Folder filtering
- Pattern-based search
- Currently has unused controls that were removed

**Cleanup Applied:**
- Removed: `autoFit`, `labelThreshold`, `qualityLevel` (non-functional)
- Kept: `alwaysShowEdges` (works)

---

## Best Practices Summary

### ✅ DO:
- Use `overrideData` for pre-filtered data
- Set `useRealData={false}` when using `overrideData`
- Clear filter props (`selectedSourceType=""`) when using `overrideData`
- Normalize IDs to strings
- Handle both `{from, to}` and `{source, target}` edge formats
- Add extensive console logging during development
- Limit `maxNodes` to 100-250 for good performance
- Use AbortController for async operations
- Test with production builds (hydration issues)

### 🚫 DON'T:
- Don't rely on client-side filtering for large graphs
- Don't pass both `overrideData` and filter props
- Don't fetch data in component when parent already fetched
- Don't assume node ID format (could be string, number, or element_id)
- Don't render 500+ nodes without performance optimizations
- Don't use window/DOM APIs in render phase (SSR issues)
- Don't remove cleanup functions from useEffect hooks

---

## Related Documentation
- `../structure/AGENTS.md`: Structure view page implementation
- `../AGENTS.md`: Overall UI architecture
- `../../../../developer_graph/AGENTS.md`: Backend API reference

---

**Last Updated:** 2025-09-30  
**Sprint:** 11  
**Status:** Production-ready with documented limitations
