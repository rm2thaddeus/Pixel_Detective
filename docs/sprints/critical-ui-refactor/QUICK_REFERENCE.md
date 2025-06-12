# Quick Reference (Critical UI Refactor)

## Running the App

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

- `NEXT_PUBLIC_API_URL` – Base URL for REST endpoints
- `NEXT_PUBLIC_SOCKET_URL` – Base URL for WebSocket connections

## Folder Structure

```
components/      # React components organized by feature
pages/           # Next.js pages and routing
lib/             # API and socket clients
store/           # Global state management (Zustand)
styles/          # Theme and global styles
utils/           # Utility functions
```

## Useful Commands

- `npm run lint` – Run ESLint checks
- `npm run test` – Execute unit and integration tests
- `npm run build` – Build for production
- `npm run start` – Start production server

## Key Resources

- **Tech Stack:** Next.js, React Query, Zustand, Chakra UI, Socket.IO, Plotly.js
- **Docs:** `docs/sprints/critical-ui-refactor/` for sprint details 