# WiseMarket: frontend

Mobile-first **React 19 + Vite** progressive web app for [WiseMarket](../../README.md).

## Run it

```bash
npm install
npm run dev        # http://localhost:5173
```

The dev server forwards `/api/*` to the FastAPI backend on `http://localhost:8000` (see `vite.config.js`), so start the backend first. To point at another backend, set `VITE_API_URL`:

```bash
VITE_API_URL=https://your-api.example.com npm run build
```

| Command | What it does |
|---|---|
| `npm run dev` | Development server with hot reload |
| `npm run lint` | ESLint (React + hooks rules) |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the production build locally |

## Structure

```
src/
├── api/client.js        all backend calls in one place
├── pages/               one file per screen (Home, Search, Product, Basket, Scan,
│                        Chat, StoreMap, Profile, Settings, Onboarding, RecipeView)
├── components/          BottomNav, ProductCard, PriceBar
├── hooks/               useBasket (basket in localStorage), useTracking
└── data/                recipes and seasonal produce (static)
public/
├── manifest.json, sw.js PWA install + offline shell
```

## Notes

- **No account needed.** Language, theme, dietary preferences and the basket are stored in `localStorage` on the device.
- **4 languages:** English, Deutsch, Français, Italiano.
- **Barcode scanning** uses `@zxing/library` with the device camera. Products can also be opened by typing a GTIN.
- **Voice input** (search and chat) uses the browser's Web Speech API, where available.
- **Nearby stores** queries the public OpenStreetMap Overpass API directly from the browser.

Screens and what each one does: [docs/APP_GUIDE.md](../../docs/APP_GUIDE.md).
