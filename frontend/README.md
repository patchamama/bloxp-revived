# Bloxp Revived — Frontend

React 19 + TypeScript + Vite + Tailwind CSS v4 frontend for Bloxp Revived.

See the [root README](../README.md) for full project documentation.

## Development

```bash
npm install
npm run dev        # start dev server at http://localhost:5173
npm run build      # production build → dist/
npm run preview    # preview production build locally
npx tsc --noEmit   # type-check without emitting
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`.
