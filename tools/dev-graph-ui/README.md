# Dev Graph UI - Interactive Code Evolution Visualization

A Next.js application for visualizing code evolution through interactive timelines, graphs, and analytics. Features both SVG and WebGL rendering engines for different performance and detail requirements.

## Features

### 🎬 Interactive Timeline
- **Dual Rendering Engines**: Switch between SVG (detailed) and WebGL (performance) modes
- **Real-time Progression**: Play/pause timeline with visual commit highlighting
- **Adaptive Performance**: Automatic node budget adjustment based on device capabilities
- **Range Selection**: Focus on specific commit ranges with live filtering

### 📊 Graph Visualizations
- **Biological Evolution Graph**: Code as living organisms with growth patterns
- **Progressive Structure Graph**: Detailed file relationships and dependencies
- **WebGL Evolution Graph**: CUDA-accelerated rendering for large datasets (2000+ nodes)

### 🔍 Analytics & Insights
- **Sprint Mapping**: Connect commits to development sprints
- **File Lifecycle Tracking**: Monitor file creation, modification, and deletion
- **Performance Metrics**: Real-time FPS, render times, and node counts

## Getting Started

### Prerequisites
- Node.js 18+ (required for WebGL features)
- Backend API running on `http://localhost:8080` (see main project setup)

### Installation

```bash
cd tools/dev-graph-ui
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the application.

### Key Pages

- **Timeline**: `/dev-graph/timeline` - Interactive commit progression with dual rendering
- **Complex Graph**: `/dev-graph/complex` - Comprehensive graph visualization
- **Sprint Analytics**: `/dev-graph/sprints` - Sprint-based analysis and mapping

## Architecture

### Rendering Engines

| Engine | Use Case | Performance | Features |
|--------|----------|-------------|----------|
| **SVG** | Analysis, debugging | ~100-500 nodes | Full interactivity, labels, tooltips |
| **WebGL** | Overview, progression | ~2000+ nodes | GPU acceleration, real-time updates |

### Core Components

- `WebGLEvolutionGraph.tsx` - CUDA-accelerated WebGL2 timeline renderer
- `ProgressiveStructureGraph.tsx` - SVG-based detailed visualization
- `BiologicalEvolutionGraph.tsx` - Code evolution as biological organisms
- `TimelinePage.tsx` - Main timeline interface with dual engine switching

### Performance Features

- **Adaptive Node Budgets**: Automatically adjusts based on device memory and CPU cores
- **Progressive Loading**: Time-based filtering with efficient data structures
- **Resource Management**: Proper WebGL context lifecycle and cleanup
- **Real-time Updates**: Reactive data flow without re-initialization

## Configuration

### Environment Variables

```bash
NEXT_PUBLIC_DEV_GRAPH_API_URL=http://localhost:8080  # Backend API URL
```

### Performance Tuning

The application automatically detects device capabilities and adjusts:
- Node limits based on available memory
- Rendering quality based on CPU cores
- Viewport-based scaling factors

Manual overrides available in the UI controls.

## API Integration

The frontend consumes these backend endpoints:
- `GET /api/v1/dev-graph/evolution/timeline` - Timeline data with commit progression
- `GET /api/v1/dev-graph/subgraph/by-commits` - Commit-scoped subgraph data
- `GET /api/v1/dev-graph/commits/buckets` - Commit density analytics
- `GET /api/v1/dev-graph/sprints/{number}/subgraph` - Sprint hierarchy data

## Development

### Project Structure

```
src/
├── app/
│   └── dev-graph/
│       ├── timeline/          # Interactive timeline page
│       ├── complex/           # Complex graph visualization
│       └── sprints/           # Sprint analytics
├── components/
│   ├── WebGLEvolutionGraph.tsx    # WebGL renderer
│   ├── ProgressiveStructureGraph.tsx  # SVG renderer
│   └── BiologicalEvolutionGraph.tsx   # Evolution visualization
└── hooks/                     # Custom React hooks
```

### Adding New Visualizations

1. Create component in `src/components/`
2. Add page route in `src/app/dev-graph/`
3. Implement data fetching hooks in `src/hooks/`
4. Add navigation links in main layout

## Deployment

### Vercel (Recommended)

```bash
npm run build
# Deploy to Vercel
```

### Docker

```bash
docker build -t dev-graph-ui .
docker run -p 3000:3000 dev-graph-ui
```

## Troubleshooting

### WebGL Issues
- Ensure Node.js 18+ for proper WebGL support
- Check browser WebGL2 compatibility
- Verify GPU drivers are up to date

### Performance Issues
- Reduce node limits in UI controls
- Switch to SVG mode for detailed analysis
- Check browser memory usage

### API Connection
- Verify backend is running on correct port
- Check CORS settings in backend configuration
- Ensure environment variables are set correctly

## Contributing

1. Follow Next.js best practices
2. Maintain TypeScript strict mode
3. Add proper error boundaries for WebGL components
4. Test both rendering engines when making changes
5. Update performance budgets when adding features

## License

Part of the Vibe Coding project. See main project license for details.
