# Technical Implementation Plan (Critical UI Refactor)

## Technology Stack

- **Framework:** Next.js (TypeScript)
- **State Management:** Zustand (or Redux Toolkit)
- **UI Library:** Chakra UI (or Tailwind CSS + Headless UI)
- **Data Fetching:** React Query (TanStack Query)
- **Real-time:** WebSockets (Socket.IO)
- **Visualization:** Plotly.js or D3.js
- **Image Upload:** React Dropzone

## Project Structure

```
frontend/
├── components/
│   ├── Home/
│   ├── Tabs/
│   ├── SearchTab/
│   ├── GuessingGameTab/
│   ├── VisualizationTab/
│   ├── AddImagesTab/
│   └── UI/  # Shared UI elements (buttons, modals, loaders)
├── pages/
│   ├── index.tsx
│   └── _app.tsx
├── lib/
│   ├── api.ts       # REST API clients
│   └── socket.ts    # WebSocket client setup
├── store/
│   └── store.ts     # Global state with Zustand
├── styles/
│   └── theme.ts     # Chakra UI theme or Tailwind config
└── utils/
    └── helpers.ts   # Shared utility functions
```

## Implementation Steps

1. **Initialize Next.js App** with TypeScript support.
2. **Configure UI Library** (Chakra UI/Tailwind CSS) and set up global theme.
3. **Integrate React Query**: Initialize `QueryClient` and provider in `_app.tsx`.
4. **Setup Global State**: Create Zustand store for shared state (current collection, user preferences).
5. **Scaffold Pages & Navigation**: Implement layout with tabs for each major feature.
6. **Home Screen**: Build status ping, open/create collection UI, and log viewer.
7. **Search Tab**: Connect to REST endpoint for search; implement UI for prompt, upload, and results.
8. **WebSocket Integration**: Implement client in `socket.ts`, connect to backend logs channel.
9. **Real-time Log Component**: Create UI component to stream and display logs.
10. **AI Guessing Game Tab**: Fetch random image; display AI predictions; optional user interaction.
11. **Visualization Tab**: Integrate Plotly.js/D3.js for 2D embeddings; add hover/click handlers.
12. **Add Images Tab**: Use React Dropzone for folder selection; trigger ingestion via REST/WebSocket.
13. **Testing & Linting**: Set up ESLint, Prettier, and basic unit tests with Jest/React Testing Library.
14. **Deployment Setup**: Configure Vercel or similar for preview and production deployments.

## Milestones

- **Week 1**: Project scaffold, UI library setup, Home & Search Tabs
- **Week 2**: Real-time logs, AI Guessing, Visualization, Add Images, QA & Deployment 