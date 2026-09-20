# FinPilot — "Vantage Finance" UI (mockup build)

React 18 + Vite, 5 routed screens, mock data only (no backend calls).

## Run
```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build -> dist/
```

## Structure
- `src/data/mock.js` — ALL rendered data lives here (API-shaped objects; swap for real responses later)
- `src/components/Shell.jsx` — sidebar + topbar layout shell
- `src/components/ui.jsx` — icons, Donut, AreaChart, Gauge, illustrations, Pill
- `src/screens/` — Dashboard.jsx, Chat.jsx, MonthlySummary.jsx, Upload.jsx, Transactions.jsx
- `src/index.css` — design system (cream bg #F7F4EE, terracotta #D97B3F, Fraunces serif + Inter)

Routing uses HashRouter so the static build works when served from any path.
