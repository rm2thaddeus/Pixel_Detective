# Frontend Development - Agent Guidelines

## 🎯 **Overview**

This document provides comprehensive guidelines for AI agents working on the **Pixel Detective frontend**. The frontend is a Next.js 14 application using React 18, Chakra UI, and React Query.

---

## 🏗️ **Frontend Architecture**

### **Technology Stack**

```
Frontend Stack
├── Framework: Next.js 14 (App Router)
├── UI Library: Chakra UI 2
├── State Management:
│   ├── React Query (server state)
│   └── Zustand (UI state)
├── Visualization: DeckGL + WebGL2
├── HTTP Client: Axios
├── Language: TypeScript
└── Styling: Chakra UI + CSS Modules
```

### **Directory Structure**

```
frontend/src/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # Root layout with providers
│   ├── page.tsx             # Home dashboard
│   ├── collections/         # Collection management
│   ├── search/              # Search interface
│   ├── latent-space/        # UMAP visualization
│   └── logs/                # Job tracking
│
├── components/              # Reusable components
│   ├── ui/                  # Design system components
│   ├── AddImagesModal.tsx   # File upload
│   ├── CollectionModal.tsx  # Collection creation
│   └── SearchInput.tsx      # Search interface
│
├── hooks/                   # Custom React hooks
│   └── useSearch.ts         # Search logic
│
├── lib/                     # Utilities
│   ├── api.ts               # Axios client
│   └── polyfills.ts         # Browser compatibility
│
└── store/                   # Zustand stores
    └── useStore.ts          # Global UI state
```

---

## 📚 **Documentation Structure**

### **Primary Documents**
- **ARCHITECTURE.md** - System architecture and data flow
- **DEVELOPER_ROADMAP.md** - Outstanding tasks
- **This file (AGENTS.md)** - Agent development guidelines

### **Cursor Rules** (`.cursor/rules/frontend/`)
- `frontend-development-index.mdc` - Master index
- `component-architecture-patterns.mdc` - Component design
- `nextjs-hydration-prevention.mdc` - Hydration issues (CRITICAL)
- `react-query-api-integration.mdc` - API patterns (MANDATORY)
- `ux-workflow-patterns.mdc` - User experience
- `nextjs-performance-optimization.mdc` - Performance

---

## 🚀 **Getting Started**

### **Step 1: Understand the Page You're Working On**

| Route | Purpose | Key Components |
|-------|---------|----------------|
| `/` | Home dashboard | SystemStatusSidebar, SetupProgress |
| `/collections` | Manage collections | CollectionCard, CollectionModal |
| `/search` | Search images | SearchInput, SearchResultsGrid |
| `/latent-space` | UMAP visualization | UMAPScatterPlot, ClusteringControls |
| `/logs/[jobId]` | Job tracking | LiveLogsSection, ProgressBar |

### **Step 2: Follow React Patterns**

#### **Component Structure**
```tsx
// ✅ STANDARD PATTERN: Use this template
'use client'

import { useState, useEffect } from 'react'
import { Box, VStack, Text } from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'

export default function MyPage() {
  // 1. Data fetching with React Query
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-data'],
    queryFn: async () => {
      const response = await api.get('/api/v1/my-data')
      return response.data
    }
  })
  
  // 2. Local UI state
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  
  // 3. Early returns for loading/error states
  if (isLoading) return <LoadingSkeleton />
  if (error) return <ErrorBoundary error={error} />
  
  // 4. Main render
  return (
    <Box>
      <PageHeader />
      <PageContent data={data} />
    </Box>
  )
}

// 5. Extract sub-components
function PageHeader() { /* ... */ }
function PageContent({ data }: Props) { /* ... */ }
```

---

## 🔧 **Development Patterns**

### **1. React Query for Server State (MANDATORY)**

✅ **ALWAYS use React Query** for API calls - never manual `useEffect`:

```tsx
// ✅ CORRECT: React Query pattern
function MyComponent() {
  const { data, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => api.get('/api/v1/collections')
  })
  
  return <div>{/* Use data */}</div>
}

// ❌ FORBIDDEN: Manual useEffect
function BadComponent() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  
  useEffect(() => {
    setLoading(true)
    api.get('/api/v1/collections').then(setData).finally(() => setLoading(false))
  }, [])
  
  return <div>{/* DON'T DO THIS */}</div>
}
```

### **2. Hydration-Safe Patterns (CRITICAL)**

✅ **Use mounted state** for client-only features:

```tsx
// ✅ CORRECT: Mounted state pattern
function ClientOnlyComponent() {
  const [mounted, setMounted] = useState(false)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  if (!mounted) {
    return <div>Loading...</div>  // Server-safe fallback
  }
  
  return (
    <div>
      {window.innerWidth}  {/* Safe to use browser APIs now */}
    </div>
  )
}

// ❌ FORBIDDEN: Direct browser API access
function BadComponent() {
  return <div>{window.innerWidth}</div>  // Hydration error!
}
```

### **3. Component Composition**

✅ **Break down large components** (keep under 200 lines):

```tsx
// ✅ CORRECT: Composed components
export default function SearchPage() {
  return (
    <Container maxW="6xl" p={6}>
      <VStack spacing={8}>
        <SearchInterface />
        <SearchResults />
      </VStack>
    </Container>
  )
}

function SearchInterface() {
  const { query, handleSearch } = useSearch()
  return <SearchInput query={query} onSearch={handleSearch} />
}

function SearchResults() {
  const { results, isLoading } = useSearchResults()
  return <ResultsGrid results={results} loading={isLoading} />
}
```

### **4. Chakra UI Patterns**

```tsx
// ✅ Use semantic tokens for theme consistency
<Box bg="card-bg" borderColor="card-border" color="text-primary">
  <Text>Content</Text>
</Box>

// ✅ Responsive design with breakpoints
<Stack
  direction={{ base: 'column', md: 'row' }}
  spacing={{ base: 4, md: 8 }}
  p={{ base: 4, md: 8 }}
>
  <Box>Content</Box>
</Stack>
```

### **5. Error Handling**

```tsx
// ✅ Error boundaries for components
<ErrorBoundary
  fallback={<ErrorFallback />}
  onError={(error) => {
    console.error('Component error:', error)
    toast({ title: 'Error', description: error.message, status: 'error' })
  }}
>
  <RiskyComponent />
</ErrorBoundary>

// ✅ Query error handling
const { data, error } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
  onError: (error) => {
    toast({
      title: 'Failed to load data',
      description: error.message,
      status: 'error'
    })
  }
})
```

---

## 📋 **Common Development Tasks**

### **Adding a New Page**

1. **Create page file**: `src/app/new-page/page.tsx`
2. **Add 'use client'** if using hooks/state
3. **Set up data fetching** with React Query
4. **Create layout structure** with Chakra UI
5. **Add navigation link** in Header/Sidebar
6. **Test responsive design** on mobile

### **Creating a New Component**

1. **Start with function component**
2. **Define TypeScript interfaces** for props
3. **Extract logic to custom hooks** if complex
4. **Use Chakra UI components** for styling
5. **Keep under 200 lines** - extract sub-components
6. **Add error boundaries** for risky operations

### **Integrating a New API Endpoint**

1. **Add to api.ts**:
```typescript
export async function fetchNewData(): Promise<NewData> {
  const response = await api.get('/api/v1/new-endpoint')
  return response.data
}
```

2. **Create custom hook**:
```typescript
export function useNewData() {
  return useQuery({
    queryKey: ['new-data'],
    queryFn: fetchNewData
  })
}
```

3. **Use in component**:
```tsx
function MyComponent() {
  const { data, isLoading } = useNewData()
  // Component logic
}
```

### **Working with Latent Space Visualization**

The latent space page uses DeckGL for high-performance WebGL rendering:

**Key Files:**
- `app/latent-space/page.tsx` - Main page logic
- `components/UMAPScatterPlot.tsx` - DeckGL visualization
- `hooks/useUMAP.ts` - UMAP data fetching
- `hooks/useStreamingUMAP.ts` - Streaming for large datasets
- `utils/visualization.ts` - Color palettes and helpers

**When modifying:**
- Mind the node budget (adaptive LOD)
- Test with large datasets (10K+ points)
- Ensure 60 FPS performance
- Check mobile performance

---

## 🐛 **Debugging Guide**

### **Hydration Errors**

**Symptoms**: Console warnings about server/client HTML mismatch

**Fix Steps:**
1. **Clear Next.js cache**: `rm -rf .next`
2. **Identify browser API usage**: Search for `window`, `localStorage`, `document`
3. **Apply mounted pattern**: Wrap in mounted state check
4. **Test in production build**: `npm run build && npm start`

**See:** `.cursor/rules/frontend/nextjs-hydration-prevention.mdc`

### **API Integration Issues**

**Symptoms**: Failed API calls, CORS errors, timeout

**Debug Steps:**
1. **Check backend is running**: `curl http://localhost:8002/health`
2. **Verify API_URL**: Check `.env.local`
3. **Test endpoint directly**: Use Postman or curl
4. **Check React Query DevTools**: Inspect query state
5. **Review network tab**: Check request/response

### **Performance Issues**

**Symptoms**: Slow rendering, memory leaks, laggy UI

**Debug Steps:**
1. **React DevTools Profiler**: Find expensive re-renders
2. **Check component size**: Large components cause issues
3. **Review useMemo/useCallback**: Missing memoization
4. **Test with production build**: `npm run build`
5. **Lighthouse audit**: Check Core Web Vitals

---

## ⚠️ **Critical Warnings**

### **Never Do These**

❌ **Use browser APIs in render** - Causes hydration errors  
❌ **Manual useEffect for API calls** - Use React Query  
❌ **God components over 300 lines** - Break them down  
❌ **Inline styles** - Use Chakra UI props  
❌ **Direct DOM manipulation** - Use React patterns  
❌ **Skip error handling** - Always handle loading/error states  

### **Always Do These**

✅ **'use client' for interactive components** - Required for App Router  
✅ **React Query for all API calls** - No exceptions  
✅ **Chakra UI components** - Don't reinvent the wheel  
✅ **TypeScript strict mode** - Full type safety  
✅ **Responsive design** - Test on mobile  
✅ **Accessibility** - ARIA labels, keyboard navigation  

---

## 📊 **Performance Targets**

### **Page Load Performance**
- **First Contentful Paint**: < 1.5s
- **Largest Contentful Paint**: < 2.5s
- **Time to Interactive**: < 3.5s
- **Cumulative Layout Shift**: < 0.1

### **Component Performance**
- **Search results grid**: < 500ms for 20 images
- **Collection list**: < 300ms to render
- **UMAP visualization**: 60 FPS for 1K points
- **Image modal**: < 300ms to open

### **Network Performance**
- **Thumbnail loading**: < 200ms per image
- **API calls**: < 500ms average response
- **Search queries**: < 1s total time
- **Background polling**: 2s interval for jobs

---

## 🧪 **Testing Strategy**

### **Component Tests**
```bash
# Run component tests
npm test

# Watch mode
npm test -- --watch
```

### **E2E Tests**
```bash
# Playwright tests (when implemented)
npm run test:e2e
```

### **Performance Audit**
```bash
# Lighthouse audit
npm run build
npm start
# Then run Lighthouse in Chrome DevTools
```

---

## 📖 **Code Style Standards**

### **TypeScript Style**
- Strict mode enabled
- Interfaces for all props
- Type imports/exports
- No `any` types (use `unknown`)

### **React Style**
- Function components only
- Hooks for all state/effects
- Props destructuring
- Early returns for loading/error

### **File Naming**
- Components: PascalCase (`SearchInput.tsx`)
- Hooks: camelCase with 'use' prefix (`useSearch.ts`)
- Utilities: camelCase (`visualization.ts`)
- Pages: lowercase (`page.tsx`)

---

## 🎯 **Success Criteria**

An AI agent is successful when:

✅ **Code Quality**: Follows React/Next.js best practices  
✅ **Performance**: Meets Lighthouse targets  
✅ **Accessibility**: WCAG AA compliance  
✅ **Responsive**: Works on all screen sizes  
✅ **Testing**: Components have adequate coverage  
✅ **UX**: Intuitive and user-friendly  

---

## 📞 **Getting Help**

### **Where to Look**

1. **ARCHITECTURE.md** - System architecture
2. **Cursor Rules** - Detailed patterns and anti-patterns
3. **Component Code** - Examples of patterns
4. **Next.js Docs** - Framework-specific features
5. **Chakra UI Docs** - Component library

### **Common Issues Solutions**

| Issue | Solution Document |
|-------|------------------|
| Hydration errors | `.cursor/rules/frontend/nextjs-hydration-prevention.mdc` |
| API integration | `.cursor/rules/frontend/react-query-api-integration.mdc` |
| Large components | `.cursor/rules/frontend/component-architecture-patterns.mdc` |
| UX workflows | `.cursor/rules/frontend/ux-workflow-patterns.mdc` |
| Performance | `.cursor/rules/frontend/nextjs-performance-optimization.mdc` |

---

**Last Updated**: Sprint 11 (September 2025)  
**Version**: 2.0  
**Status**: Production Guidelines

**🎨 Modern UI | ⚡ High Performance | ♿ Accessible**

