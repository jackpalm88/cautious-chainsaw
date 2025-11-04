# FinAgent UI Frontend

This Vite + React application powers the FinAgent control center. You can run it in two different modes:

- **Live mode** – expects the Flask Socket.IO backend from `docs/UI_QUICK_START_GUIDE.md` to be running on `http://localhost:5000`.
- **Preview (mock) mode** – streams generated market data so you can explore the UI without starting the backend.

## Setup

```bash
cd frontend
npm install
```

## Available scripts

| Command | Description |
| ------- | ----------- |
| `npm run dev` | Start Vite dev server against the live backend. |
| `npm run dev:mock` | Start Vite dev server with mock preview data (no backend needed). |
| `npm run build` | Type-check and generate a production build. |
| `npm run preview` | Preview the production build against the live backend. |
| `npm run preview:mock` | Preview the production build with mock data. |

Mock mode is powered by `VITE_USE_MOCK_STREAM=true`, which you can also set manually in your environment.

## Preview checklist

1. Want an instant preview? Run `npm run dev:mock` and open the printed URL.
2. Ready for end-to-end validation? Start the Flask Socket.IO service described in `UI_QUICK_START_GUIDE.md`, then run `npm run dev`.
3. Sharing a build? Execute `npm run build && npm run preview:mock` to serve the compiled assets with generated data.
