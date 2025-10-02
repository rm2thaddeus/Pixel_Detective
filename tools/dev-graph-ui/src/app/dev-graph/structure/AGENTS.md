# Structure View - Agent Guidelines

## Overview
The Structure View is the **primary feature** of the Dev Graph UI. It provides interactive exploration of the codebase's architectural patterns through dynamic filtering and graph visualization. Users can construct custom subgraphs by selecting node types and relationship types.

## Core Functionality

### 1. Dynamic Filter Panel
**Location:** `page.tsx:618-728`

Cascading filter system that adapts based on graph topology:

```
┌─────────────────────────────────────────────────────────┐
│  From Type         To Type           Relation Type       │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐       │
│  │ File      │ -> │ Chunk     │    │ CONTAINS_ │       │
│  │ (2461)    │    │ Document  │    │ _CHUNK    │       │
│  └───────────┘    │ Symbol    │    │ MENTIONS_ │       │
│                   └───────────┘    │ _FILE     │       │
│                                    └───────────┘       │
└─────────────────────────────────────────────────────────┘
        ↓                    ↓                 ↓
    Backend Query    Cypher: MATCH (File)-[CONTAINS_CHUNK]->(Chunk)
```

**Key Features:**
- **From Type:** Shows all node types in database
- **To Type:** Dynamically updates based on "From Type" selection (shows only connected types)
- **Relation Type:** Shows relationship types available in database
- **Active Filters Badge:** Visual feedback showing current filter state
- **Reset Filters:** Clears all selections and returns to default view

---

### 2. Graph Visualization
**Location:** `page.tsx:732-778`

Main canvas for displaying filtered subgraphs.

**Visual Hierarchy:**
```
┌─────────────────────────────────────────────┐
│ 🌐 Graph Visualization      [Export SVG]   │
├─────────────────────────────────────────────┤
│                                             │
│    ●────────●                               │
│    │        │                               │
│    ●   ●────●────●                          │
│    │   │    │    │                          │
│    ●───●────●────●                          │
│                                             │
│  [Hide edges] [Legend]                      │
└─────────────────────────────────────────────┘
```

**Controls:**
- **Export SVG:** Download visualization as SVG file
- **Hide edges:** Toggle edge visibility (useful for dense graphs)
- **Legend:** Shows node type color coding

**Positioning:** Graph placed **above** Cypher playground (user sees results first)

---

### 3. Cypher Playground
**Location:** `page.tsx:780-900`

Advanced query interface for power users.

**Features:**
- **Smart Suggestions:** Autocomplete based on node/relationship types
- **Preset Queries:** Common patterns (commits→files, requirements→implementations)
- **Result Export:** Download query results as JSON
- **Back to Structure:** Returns to filtered view from query results

**Presets (page.tsx:52-81):**
1. Recent commits touching files (25 results)
2. Requirements without implementations (25 results)
3. Documents and chunks (25 results)
4. All node types overview (15 each)
5. All relationship types overview (10 each)

---

## Implementation Deep-Dive

### Filter Cascade Logic

**Problem:** How do we show only valid "To Type" options based on "From Type" selection?

**Solution:** Query backend for actual relationship patterns.

**Code Flow (page.tsx:131-191):**

```typescript
// 1. User selects "From Type" (e.g., "File")
setSelectedSourceType("File");

// 2. useEffect triggers backend query
useEffect(() => {
  if (!selectedSourceType) return;
  
  // 3. Build query to find connected types
  const query = `
    MATCH (source:File)-[r]->(target)
    RETURN DISTINCT source, r, target
    LIMIT 1000
  `;
  
  // 4. Execute via Cypher endpoint
  const response = await fetch('/api/v1/dev-graph/graph/cypher', {
    method: 'POST',
    body: JSON.stringify({ query, max_nodes: 1000 })
  });
  
  const result = await response.json();
  
  // 5. Extract unique target types from returned nodes
  const targetTypes = new Set();
  result.nodes?.forEach(node => {
    const label = node.labels[0];
    if (label !== selectedSourceType) {  // Exclude source type
      targetTypes.add(label);
    }
  });
  
  // 6. Update "To Type" dropdown
  setAvailableTargetTypes(Array.from(targetTypes));
  
  console.log('Found connected types:', Array.from(targetTypes));
}, [selectedSourceType]);
```

**Key Points:**
- Query returns up to 1000 sample relationships
- Must return `source, r, target` (not just labels!)
- Filter out source types from results
- Update happens automatically on source change

**Console Output Example:**
```
Found 0 connected target types for Sprint: Array(6)
  ["GitCommit", "File", "Document", "Requirement", "Chunk", "Library"]
```

---

### Graph Data Fetching Strategy

**Problem:** How do we ensure filtered data is displayed without double-fetching?

**Solution:** Use conditional query strategy based on filter state.

**Code Flow (page.tsx:193-325):**

```typescript
useEffect(() => {
  // STEP 1: Determine if filters are active
  const hasFilters = selectedSourceType || selectedTargetType || selectedRelationType;
  
  if (hasFilters) {
    // STEP 2A: Build targeted Cypher query
    let query = 'MATCH (source)-[r]->(target)\nWHERE 1=1';
    if (selectedSourceType) query += `\nAND source:${selectedSourceType}`;
    if (selectedTargetType) query += `\nAND target:${selectedTargetType}`;
    if (selectedRelationType) query += `\nAND type(r) = '${selectedRelationType}'`;
    query += `\nRETURN source, r, target\nLIMIT ${maxNodes}`;
    
    console.log('Executing targeted query:', query);
    
    // STEP 2B: Execute query
    const response = await fetch('/api/v1/dev-graph/graph/cypher', {
      method: 'POST',
      body: JSON.stringify({ 
        query, 
        max_nodes: maxNodes, 
        max_relationships: maxNodes * 2 
      })
    });
    
    const result = await response.json();
    nodes = result.nodes;
    edges = result.relationships;
    
    // STEP 2C: Set as override data (prevents graph from refetching)
    setGraphOverride({ nodes, edges });
    
  } else {
    // STEP 3: No filters - use default subgraph API
    const subgraphUrl = `/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}`;
    const response = await fetch(subgraphUrl);
    const data = await response.json();
    nodes = data.nodes;
    edges = data.edges;
    
    // STEP 4: Clear override (let graph fetch its own data)
    setGraphOverride(null);
  }
  
}, [selectedSourceType, selectedTargetType, selectedRelationType, maxNodes]);
```

**Critical Decision Points:**
1. **With Filters:** Query backend directly → set as `graphOverride`
2. **Without Filters:** Let graph component fetch default view
3. **Override Data:** Prevents graph from refetching (the key fix!)

---

### The Override Pattern (CRITICAL)

**Problem:** Graph component has its own data-fetching logic. How do we inject pre-filtered data?

**Solution:** Use `overrideData` prop with coordinated `useRealData` flag.

**Parent Component Configuration (page.tsx:758-772):**

```typescript
<StructureAnalysisGraph
  metrics={metrics}
  height={600}
  width={1200}
  
  // KEY: Empty filter props when using overrideData
  selectedRelationType={graphOverride ? '' : selectedRelationType}
  selectedSourceType={graphOverride ? '' : selectedSourceType}
  selectedTargetType={graphOverride ? '' : selectedTargetType}
  
  // KEY: Disable built-in fetching when overriding
  useRealData={!graphOverride}
  
  // KEY: Provide pre-filtered data
  overrideData={graphOverride}
  
  maxNodes={maxNodes}
  onSvgReady={setSvgEl}
/>
```

**Why This Works:**
- `overrideData` takes precedence in component (checked first)
- `useRealData={false}` prevents component from fetching its own data
- Empty filter props prevent double-filtering in component
- Graph uses exactly the data we provide

**Component Side (StructureAnalysisGraph.tsx:128-153):**

```typescript
// Priority 1: Use overrideData if provided
if (overrideData && Array.isArray(overrideData.nodes)) {
  nodes = overrideData.nodes.map(node => ({
    id: String(node.id),
    type: node.type || node.labels[0],
    // ... other properties
  }));
  links = overrideData.edges.map(edge => ({
    source: String(edge.from),
    target: String(edge.to),
    type: edge.type
  }));
}
// Priority 2: Use realData if useRealData=true
else if (useRealData && realData) {
  // ... fetch from backend
}
// Priority 3: Generate synthetic data
else {
  // ... mock data
}
```

---

## State Management

### Component State Variables

**Filter State:**
```typescript
const [selectedSourceType, setSelectedSourceType] = useState('');
const [selectedTargetType, setSelectedTargetType] = useState('');
const [selectedRelationType, setSelectedRelationType] = useState('');
const [availableTargetTypes, setAvailableTargetTypes] = useState<string[]>([]);
const [availableRelationTypes, setAvailableRelationTypes] = useState<string[]>([]);
```

**Graph State:**
```typescript
const [metrics, setMetrics] = useState<StructureMetrics | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
const [graphOverride, setGraphOverride] = useState<{nodes: any[]; edges: any[]} | null>(null);
const [maxNodes, setMaxNodes] = useState(100);  // Start manageable
```

**Cypher State:**
```typescript
const [cypherQuery, setCypherQuery] = useState<string>(DEFAULT_CYPHER_QUERY);
const [cypherResult, setCypherResult] = useState<CypherQueryResult | null>(null);
const [cypherLoading, setCypherLoading] = useState(false);
const [cypherError, setCypherError] = useState<string | null>(null);
```

**UI State:**
```typescript
const [svgEl, setSvgEl] = useState<SVGSVGElement | null>(null);
const [highlightKind, setHighlightKind] = useState<'none' | 'by-type'>('none');
```

### State Update Triggers

**User Actions → State Changes:**
```
User selects "File" in From Type
  ↓
setSelectedSourceType("File")
  ↓
useEffect [selectedSourceType] fires
  ↓
Backend query: MATCH (File)-[r]->(target)
  ↓
setAvailableTargetTypes([...])
  ↓
Dropdown updates

User selects "Chunk" in To Type
  ↓
setSelectedTargetType("Chunk")
  ↓
useEffect [selectedSourceType, selectedTargetType] fires
  ↓
Backend query: MATCH (File)-[r]->(Chunk)
  ↓
setGraphOverride({ nodes, edges })
  ↓
Graph component re-renders with new data
```

---

## API Integration

### Endpoints Used

**1. Statistics Endpoint**
```typescript
GET /api/v1/dev-graph/stats

Response:
{
  summary: {
    total_nodes: 30822,
    total_relationships: 255389,
    recent_commits_7d: 45
  },
  node_types: [
    { type: "File", count: 2461, color: "blue" },
    { type: "Chunk", count: 13829, color: "green" }
  ],
  relationship_types: [
    { type: "CONTAINS_CHUNK", count: 16523, color: "purple" }
  ]
}
```

**Usage:** Populate filter dropdowns, show total counts

**2. Cypher Query Endpoint**
```typescript
POST /api/v1/dev-graph/graph/cypher

Request:
{
  query: "MATCH (n:File)-[r]->(m) RETURN n, r, m LIMIT 100",
  max_nodes: 100,
  max_relationships: 200,
  parameters: {}  // Optional
}

Response:
{
  nodes: [
    {
      id: "4:abc123:0",
      labels: ["File"],
      properties: { path: "src/app/page.tsx", ... },
      type: "File",
      display: "src/app/page.tsx"
    }
  ],
  relationships: [
    {
      id: "5:def456:0",
      from: "4:abc123:0",
      to: "4:xyz789:1",
      type: "CONTAINS_CHUNK",
      properties: {}
    }
  ],
  summary: {},
  warnings: []
}
```

**Usage:** Execute custom queries, filter-based queries

**3. Subgraph Endpoint**
```typescript
GET /api/v1/dev-graph/graph/subgraph?limit=100&types=File,Chunk

Response:
{
  nodes: [...],
  edges: [...],  // Note: "edges" not "relationships"
  total_nodes: 30822,
  total_relationships: 255389
}
```

**Usage:** Default view when no filters applied

---

## Common Issues & Debugging

### Issue: "No Connected Targets" Despite Good Data

**Symptoms:**
- Select "File" → "To Type" shows "No connected targets"
- Console shows: `Found 0 connected target types`
- Database has Files with relationships

**Debugging Steps:**

1. **Check Query Result:**
```typescript
console.log('Query result:', result);
console.log('Nodes count:', result.nodes?.length);
console.log('Sample node:', result.nodes?.[0]);
```

2. **Verify Node Structure:**
```typescript
result.nodes.forEach(node => {
  console.log('Node labels:', node.labels);
  console.log('Node type:', node.type);
});
```

3. **Common Causes:**
   - Query returns column data instead of Node objects
   - Query has wrong syntax (missing `RETURN n, r, m`)
   - Backend endpoint not accessible (CORS, network)
   - Node labels not properly extracted

**Fix:**
```typescript
// WRONG:
const query = `RETURN DISTINCT labels(target)`;

// CORRECT:
const query = `RETURN DISTINCT source, r, target`;
```

---

### Issue: Edges Not Visible in Graph

**Symptoms:**
- Console: `Query results: { totalNodes: 150, totalEdges: 200 }`
- Console: `StructureAnalysisGraph: no edges returned for current filters`
- Graph shows nodes but no lines

**Debugging Steps:**

1. **Check Override Data:**
```typescript
console.log('graphOverride:', graphOverride);
console.log('Edges in override:', graphOverride?.edges?.length);
```

2. **Check Component Props:**
```typescript
// In component
console.log('Received overrideData:', overrideData);
console.log('useRealData:', useRealData);
console.log('Filter props:', { selectedSourceType, selectedTargetType });
```

3. **Check Data Priority:**
```typescript
// In StructureAnalysisGraph
if (overrideData) {
  console.log('Using overrideData');
} else if (useRealData && realData) {
  console.log('Using realData');
} else {
  console.log('Using synthetic data');
}
```

**Fix:**
Ensure `useRealData={!graphOverride}` when passing `overrideData`.

---

### Issue: Performance Degradation with Large Graphs

**Symptoms:**
- Page freezes when selecting filters
- Browser "Page Unresponsive" warning
- CPU usage spikes to 100%

**Solutions:**

**1. Reduce maxNodes:**
```typescript
// Default: 100 (good for most queries)
// Dense graphs: 50
// Sparse graphs: 250
const [maxNodes, setMaxNodes] = useState(100);
```

**2. Limit Query Scope:**
```typescript
// Add more specific filters
WHERE source.path STARTS WITH 'src/app'
AND target.kind = 'component'
```

**3. Optimize D3 Force Simulation:**
```typescript
// In StructureAnalysisGraph.tsx
const simulation = d3.forceSimulation(nodes)
  .force("charge", d3.forceManyBody().strength(-300))  // Reduce iterations
  .force("center", d3.forceCenter(w/2, h/2))
  .stop();  // Run manually instead of auto

// Run limited iterations
for (let i = 0; i < 50; i++) simulation.tick();
```

**4. Debounce Filter Changes:**
```typescript
import { debounce } from 'lodash';

const debouncedFetch = useMemo(
  () => debounce((filters) => {
    // Fetch data
  }, 300),
  []
);
```

---

## Testing Strategy

### Unit Testing (Future)

```typescript
// structure/page.test.tsx
describe('StructureAnalysisPage', () => {
  it('updates To Type dropdown when From Type changes', async () => {
    const { getByLabelText, findByText } = render(<StructureAnalysisPage />);
    
    // Select From Type
    const fromSelect = getByLabelText('From Type');
    fireEvent.change(fromSelect, { target: { value: 'File' } });
    
    // Wait for API call
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/cypher'),
        expect.objectContaining({
          body: expect.stringContaining('MATCH (source:File)')
        })
      );
    });
    
    // Verify To Type updated
    const toSelect = getByLabelText('To Type');
    expect(toSelect).toContainHTML('Chunk');
    expect(toSelect).toContainHTML('Document');
  });
});
```

### Integration Testing

**Manual Test Scenarios:**

1. **Basic Filter Flow:**
   - [ ] Page loads with all node types in "From Type"
   - [ ] Select "File" → "To Type" populates
   - [ ] Select "Chunk" → Graph shows File→Chunk edges
   - [ ] Click "Reset Filters" → Clears all selections

2. **Edge Visibility:**
   - [ ] With filters: Edges visible
   - [ ] Without filters: Default view
   - [ ] Toggle "Hide edges" → Edges disappear/reappear

3. **Cypher Playground:**
   - [ ] Click preset → Query executes
   - [ ] Enter custom query → Results show
   - [ ] Invalid query → Error message
   - [ ] "Back to Structure" → Returns to filtered view

4. **Performance:**
   - [ ] 50 nodes: Instant (<100ms)
   - [ ] 100 nodes: Fast (<500ms)
   - [ ] 250 nodes: Acceptable (<2s)
   - [ ] 500+ nodes: Use with caution

---

## Future Enhancements

### Priority 1: Multi-Select Filters
```typescript
const [selectedSourceTypes, setSelectedSourceTypes] = useState<string[]>([]);

// Query: MATCH (source) WHERE source:File OR source:Document
```

### Priority 2: Path-Based Queries
```tsx
<PathQueryBuilder>
  <PathStep type="File" />
  <PathRelation type="CONTAINS_CHUNK" />
  <PathStep type="Chunk" />
  <PathRelation type="MENTIONS_SYMBOL" />
  <PathStep type="Symbol" />
</PathQueryBuilder>

// Generates: MATCH path = (File)-[:CONTAINS_CHUNK]->(Chunk)-[:MENTIONS_SYMBOL]->(Symbol)
```

### Priority 3: Saved Queries
```typescript
const savedQueries = [
  {
    name: "File Dependencies",
    filters: { from: "File", to: "File", rel: "DEPENDS_ON" }
  },
  {
    name: "Sprint Requirements",
    filters: { from: "Sprint", to: "Requirement", rel: "PART_OF" }
  }
];
```

### Priority 4: Export Functionality
```typescript
// Export filtered subgraph as JSON
const exportData = () => {
  const data = {
    nodes: graphOverride.nodes,
    edges: graphOverride.edges,
    filters: { selectedSourceType, selectedTargetType }
  };
  downloadJSON(data, 'structure-export.json');
};
```

---

## Related Files
- `page.tsx`: Main structure view component (1000+ lines)
- `../components/StructureAnalysisGraph.tsx`: D3 visualization component
- `../components/AGENTS.md`: Component-specific documentation
- `../welcome/page.tsx`: System health dashboard
- `../timeline/svg/page.tsx`: Temporal visualization

---

**Last Updated:** 2025-09-30  
**Author:** AI Agent (Claude)  
**Sprint:** 11  
**Status:** Production-ready
