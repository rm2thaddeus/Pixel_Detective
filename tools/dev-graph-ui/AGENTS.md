# Dev Graph UI - Agent Guidelines

## Overview
The Dev Graph UI is a Next.js 15 frontend application for visualizing and interacting with the temporal semantic knowledge graph. It provides interactive visualizations, filtering capabilities, and analytics for exploring the codebase structure.

## Architecture

### Technology Stack
- **Framework**: Next.js 15 (App Router)
- **UI Library**: Chakra UI v3
- **Visualization**: D3.js v7
- **Language**: TypeScript
- **State Management**: React hooks + context

### Project Structure
```
tools/dev-graph-ui/
├── src/
│   ├── app/
│   │   ├── dev-graph/
│   │   │   ├── welcome/          # System health & quick stats
│   │   │   ├── timeline/         # Temporal visualization
│   │   │   ├── structure/        # Architectural analysis (MAIN FEATURE)
│   │   │   └── components/       # Shared visualization components
│   │   ├── layout.tsx            # Root layout with theme provider
│   │   └── page.tsx              # Landing page
│   └── lib/                      # Utilities and helpers
```

---

## Critical Patterns & Best Practices

### 1. **Backend-First Filtering (NOT Client-Side)**

**Problem:** Filtering large graphs (30k+ nodes) client-side is slow and incomplete.

**Solution:** Always query backend with targeted Cypher queries.

**✅ Correct Pattern:**
```typescript
// When filters change, build targeted Cypher query
const query = `
  MATCH (source:${sourceType})-[r]->(target:${targetType})
  WHERE type(r) = '${relationType}'
  RETURN source, r, target
  LIMIT ${maxNodes}
`;

const response = await fetch('/api/v1/dev-graph/graph/cypher', {
  method: 'POST',
  body: JSON.stringify({ query, max_nodes: maxNodes })
});

const result = await response.json();
const nodes = result.nodes;
const edges = result.relationships;  // Already filtered by backend!
```

**🚫 Anti-Pattern:**
```typescript
// DON'T: Fetch all data then filter client-side
const allData = await fetch('/api/v1/dev-graph/graph/subgraph?limit=20000');
const filtered = allData.nodes.filter(n => n.type === sourceType); // Too slow!
```

---

### 2. **Cascading Dropdowns with Dynamic Options**

**Problem:** Need to show only valid connections (e.g., "File connects to what?")

**Solution:** Query backend when first filter changes to populate second filter.

**Implementation (structure/page.tsx:133-191):**
```typescript
useEffect(() => {
  if (!selectedSourceType) {
    setAvailableTargetTypes([]);
    return;
  }

  // Query backend for connected types
  const query = `
    MATCH (source:${selectedSourceType})-[r]->(target)
    RETURN DISTINCT source, r, target
    LIMIT 1000
  `;
  
  const response = await fetch('/api/v1/dev-graph/graph/cypher', {
    method: 'POST',
    body: JSON.stringify({ query, max_nodes: 1000 })
  });
  
  const result = await response.json();
  
  // Extract unique target types (excluding source types)
  const targetTypes = new Set();
  result.nodes?.forEach(node => {
    if (node.labels[0] !== selectedSourceType) {
      targetTypes.add(node.labels[0]);
    }
  });
  
  setAvailableTargetTypes(Array.from(targetTypes));
}, [selectedSourceType]);
```

**Key Points:**
- Return actual nodes/relationships, not just labels
- Cypher endpoint only collects Node/Relationship objects from result
- Filter out source types from target dropdown
- Update available relationship types simultaneously

---

### 3. **The Double-Data-Fetching Bug (CRITICAL)**

**Problem:** Graph component was fetching its own data while parent also fetched data, causing filtered data to be ignored.

**Root Cause (StructureAnalysisGraph.tsx:78-100):**
```typescript
useEffect(() => {
  if (!(useRealData && mounted)) return;
  
  // BUG: Component fetches its own unfiltered data!
  const url = `${apiUrl}/api/v1/dev-graph/graph/subgraph?limit=${maxNodes}`;
  const response = await fetch(url);
  const data = await response.json();
  setRealData({ nodes: data.nodes, edges: data.edges });
}, [useRealData, mounted, maxNodes]);
```

**The Broken Flow:**
1. ✅ Parent fetches filtered data: `File → Document` relationships
2. ❌ Graph component ignores that and fetches unfiltered 100 nodes
3. ❌ Graph filters those 100 nodes client-side (too small sample!)
4. ❌ Result: No edges visible

**✅ Solution - Use OverrideData Pattern:**

**In Parent Component (structure/page.tsx:270-278):**
```typescript
// After fetching filtered data
if (selectedSourceType || selectedTargetType || selectedRelationType) {
  setGraphOverride({ 
    nodes: filteredNodes, 
    edges: filteredEdges 
  });
} else {
  setGraphOverride(null); // Let graph fetch default view
}
```

**Pass to Graph Component (structure/page.tsx:758-772):**
```typescript
<StructureAnalysisGraph
  selectedRelationType={graphOverride ? '' : selectedRelationType}
  selectedSourceType={graphOverride ? '' : selectedSourceType}
  selectedTargetType={graphOverride ? '' : selectedTargetType}
  useRealData={!graphOverride}        // Don't fetch when overriding
  overrideData={graphOverride}         // Use parent's filtered data
/>
```

**Key Principle:** When `overrideData` is provided, graph uses it directly without fetching or filtering.

---

### 4. **Cypher Query Endpoint Response Format**

**Critical Understanding:** The `/api/v1/dev-graph/graph/cypher` endpoint **only collects Node and Relationship objects** from query results.

**✅ Correct Query:**
```cypher
MATCH (source:File)-[r:CONTAINS_CHUNK]->(target:Chunk)
RETURN source, r, target  -- Returns Node, Relationship, Node objects
LIMIT 100
```

**Response Format:**
```typescript
{
  nodes: [
    { id: "123", labels: ["File"], properties: {...}, type: "File" },
    { id: "456", labels: ["Chunk"], properties: {...}, type: "Chunk" }
  ],
  relationships: [
    { id: "789", from: "123", to: "456", type: "CONTAINS_CHUNK", properties: {...} }
  ],
  summary: {...},
  warnings: []
}
```

**🚫 Wrong Query:**
```cypher
MATCH (source:File)-[r]->(target)
RETURN DISTINCT labels(target) as targetLabels, type(r) as relType  -- Returns scalars!
```

**Why Wrong:** Returns column data (strings), not Node/Relationship objects. The endpoint won't collect these into `nodes`/`relationships` arrays.

---

### 5. **UI Cleanup Best Practices**

**Problem:** Cluttered UI with unused features reduces usability.

**Solutions Applied:**

**Welcome Page (welcome/page.tsx):**
- ✅ Removed extensive quality indicators (took too much space)
- ✅ Removed node/relationship distribution charts (not actionable)
- ✅ Removed performance metrics (confusing, not useful)
- ✅ Kept: System health, quick stats, navigation cards

**Timeline Page (timeline/TimelineExperience.tsx):**
- ✅ Removed non-functional controls: `autoFit`, `labelThreshold`, `qualityLevel`
- ✅ Removed commented-out encodings: `sizeByLOC`, `colorByLOC`, `showFolderGroups`
- ✅ Kept: Working controls like `alwaysShowEdges`

**Structure Page (structure/page.tsx):**
- ✅ Removed ugly in-graph tooltip (StructureAnalysisGraph.tsx:233-252)
- ✅ Moved graph to top (main feature first)
- ✅ Made Cypher playground compact and collapsible
- ✅ Clear visual hierarchy

**Principle:** If a control doesn't work or doesn't provide value, remove it. Don't ship half-baked features.

---

## Development Workflow

### Adding New Graph Visualizations

1. **Start with Backend Query Design**
   ```typescript
   // Design your Cypher query first
   const query = `
     MATCH (a:NodeType1)-[r:REL_TYPE]->(b:NodeType2)
     WHERE condition
     RETURN a, r, b
     LIMIT ${maxNodes}
   `;
   ```

2. **Fetch Data in Parent Component**
   ```typescript
   const response = await fetch('/api/v1/dev-graph/graph/cypher', {
     method: 'POST',
     body: JSON.stringify({ query, max_nodes, max_relationships })
   });
   const data = await response.json();
   ```

3. **Pass as OverrideData**
   ```typescript
   setGraphOverride({ 
     nodes: data.nodes, 
     edges: data.relationships 
   });
   ```

4. **Configure Graph Component**
   ```typescript
   <StructureAnalysisGraph
     useRealData={false}
     overrideData={graphOverride}
     selectedSourceType=""  // No client filtering
     selectedTargetType=""
   />
   ```

### Adding New Filters

1. **Add State Variables**
   ```typescript
   const [filterValue, setFilterValue] = useState('');
   const [availableOptions, setAvailableOptions] = useState([]);
   ```

2. **Fetch Available Options from Backend**
   ```typescript
   useEffect(() => {
     const query = `MATCH (n:Type) RETURN DISTINCT n.property`;
     // Fetch and set availableOptions
   }, [dependentFilter]);
   ```

3. **Build Query with Filter**
   ```typescript
   let query = 'MATCH (n)-[r]->(m)\nWHERE 1=1';
   if (filterValue) query += `\nAND n.property = '${filterValue}'`;
   query += '\nRETURN n, r, m';
   ```

4. **Update Graph**
   - Fetch with new query
   - Set as overrideData
   - Graph automatically re-renders

---

## Common Issues & Solutions

### Issue: Filters Selected But No Edges Visible

**Symptoms:**
- Console shows "no edges returned for current filters"
- Nodes visible but disconnected
- Filter dropdowns populated correctly

**Root Cause:** Double-data-fetching (graph ignoring parent data)

**Solution:**
1. Check if `overrideData` is being passed to graph
2. Verify `useRealData={false}` when using overrideData
3. Ensure filter props (`selectedSourceType`, etc.) are empty strings when overriding
4. Check console for query results: `Query results: { totalNodes: X, totalEdges: Y }`

### Issue: Cascading Dropdown Shows "No Connected Targets"

**Symptoms:**
- Select first filter (e.g., "File")
- Second dropdown says "No connected targets"
- Database has 100% quality score

**Root Cause:** Query returns column data instead of Node objects

**Solution:**
```typescript
// WRONG: Returns scalars
RETURN DISTINCT labels(target) as targetLabels

// CORRECT: Returns Node objects
RETURN DISTINCT source, r, target
```

Then extract types from `result.nodes` array, not from column values.

### Issue: Graph Performance Degradation

**Symptoms:**
- Slow rendering
- Browser freezes
- High CPU usage

**Solutions:**
1. **Reduce `maxNodes` limit** (default: 100-250)
2. **Use more specific filters** (don't fetch all nodes)
3. **Limit relationship types** (fewer edge calculations)
4. **Disable force simulation** for very large graphs
5. **Implement pagination** for result sets >500 nodes

### Issue: Hydration Errors with Dark Mode

**Symptoms:**
- "Text content did not match" errors
- UI flickers on load
- Dark mode not persisting

**Solution:**
```tsx
// In app/layout.tsx
<html lang="en" suppressHydrationWarning>
  <head>
    <ColorModeScript initialColorMode="dark" />
  </head>
  <body>
    <ChakraProvider>
      {children}
    </ChakraProvider>
  </body>
</html>
```

Use `mounted` state for client-only components:
```tsx
const [mounted, setMounted] = useState(false);
useEffect(() => setMounted(true), []);

if (!mounted) return <Spinner />;
```

---

## Testing Guidelines

### Testing Filter Functionality

1. **Test Cascading Behavior:**
   - Select source type → verify target options update
   - Select target type → verify graph updates
   - Clear filters → verify reset to default view

2. **Test Edge Cases:**
   - No relationships exist between selected types
   - Very large result sets (>1000 nodes)
   - Rapid filter changes (debouncing)
   - Backend connection failure

3. **Test Performance:**
   - Time to first render
   - Filter response time
   - Graph re-render performance
   - Memory usage over time

### Manual Testing Checklist

- [ ] **Welcome Page:** System health loads, stats accurate, navigation works
- [ ] **Structure Page - Filters:**
  - [ ] "From Type" dropdown shows all node types
  - [ ] Selecting source updates "To Type" dropdown
  - [ ] Selecting target updates graph with edges
  - [ ] "Reset Filters" clears everything
- [ ] **Structure Page - Graph:**
  - [ ] Edges visible between filtered nodes
  - [ ] Zoom/pan works smoothly
  - [ ] Node colors match legend
  - [ ] "Hide edges" toggle works
- [ ] **Structure Page - Cypher:**
  - [ ] Custom queries execute successfully
  - [ ] Query results show in graph
  - [ ] "Back to Structure" returns to filtered view
  - [ ] Invalid queries show error messages
- [ ] **Timeline Page:** SVG renders, controls work
- [ ] **Dark Mode:** Toggles correctly, persists on refresh

---

## Performance Benchmarks

### Target Metrics (Development Build)
- **Initial Load:** <2 seconds
- **Filter Update:** <500ms
- **Graph Render (250 nodes):** <1 second
- **Cypher Query Execution:** <2 seconds
- **Memory Usage:** <200MB

### Optimization Strategies

1. **Backend Query Optimization:**
   - Use `LIMIT` clauses in all queries
   - Index frequently queried properties
   - Use relationship direction hints

2. **Frontend Rendering:**
   - Memoize expensive calculations with `useMemo`
   - Debounce filter inputs (300ms)
   - Use React.memo for pure components
   - Virtualize large lists (not implemented yet)

3. **Data Transfer:**
   - Minimize payload size (only needed properties)
   - Use HTTP compression
   - Consider WebSocket for real-time updates

---

## Future Improvements

### Priority 1: Enhanced Filtering
- [ ] Multi-select for node types
- [ ] Path-based queries ("Show me path from File to Sprint")
- [ ] Saved filter presets
- [ ] Filter templates for common queries

### Priority 2: Advanced Visualizations
- [ ] Force-directed layout improvements
- [ ] Hierarchical layouts (tree view)
- [ ] Timeline integration with structure view
- [ ] Animated graph transitions

### Priority 3: User Experience
- [ ] Tour/tutorial for first-time users
- [ ] Keyboard shortcuts
- [ ] Export functionality (PNG, SVG, JSON)
- [ ] Shareable URLs with filter state

### Priority 4: Performance
- [ ] Virtual scrolling for large node lists
- [ ] WebGL rendering for 1000+ nodes
- [ ] Progressive loading (load more on scroll)
- [ ] Background data prefetching

---

## Related Documentation
- `src/app/dev-graph/structure/AGENTS.md`: Structure view implementation details
- `src/app/dev-graph/components/AGENTS.md`: Visualization component patterns
- `../../developer_graph/AGENTS.md`: Backend API reference
- `../../developer_graph/routes/AGENTS.md`: Route handler documentation

---

**Last Updated:** 2025-09-30  
**Sprint:** 11  
**Status:** Production-ready with known limitations documented
