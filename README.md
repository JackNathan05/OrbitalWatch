# OrbitalWatch

3D globe that shows where satellites are and flags predicted close approaches between objects in Earth orbit. Uses public data from the U.S. government: orbital elements from CelesTrak and conjunction data messages (CDMs) from Space-Track.org.

Built with Next.js 16, CesiumJS, FastAPI, SGP4, PostgreSQL (or TimescaleDB), and Redis.

---

## What it does

- **Globe** renders up to 5,000 satellites on a CesiumJS 3D Earth, color-coded by type (payload, rocket body, debris, unknown)
- **Conjunction feed** lists predicted close approaches sorted by collision probability (Pc), with color bands: green (< 1e-5), yellow (1e-5 to 1e-4), orange (1e-4 to 1e-3), red (> 1e-3)
- **Detail view** for each conjunction shows miss distance, Pc, relative speed, and a plain-language summary
- **Satellite panel** shows orbital elements (inclination, eccentricity, apogee/perigee) and recent conjunctions for any selected object
- **Search** by name ("ISS", "STARLINK-1234") or NORAD catalog number
- **Stats bar** shows total tracked objects, active conjunctions in the next 7 days, and when data was last refreshed

Data refreshes automatically: positions every 60 seconds, TLEs/CDMs/SATCAT every 4 hours.

---

## Data sources

| Source | What | Auth |
|--------|------|------|
| [CelesTrak](https://celestrak.org) | GP/TLE orbital elements (~12k objects) | None |
| [Space-Track.org](https://www.space-track.org) | CDMs (conjunction messages), SATCAT (object types) | Free account |

Register for Space-Track at https://www.space-track.org/auth/createAccount (instant, free).

---

## Local setup

### Requirements

- Docker Desktop
- Python 3.11+
- Node.js 18+
- A Space-Track.org account

### Quick start (Windows)

```
git clone https://github.com/JackNathan05/OrbitalWatch.git
cd OrbitalWatch
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://orbital:orbital_dev@localhost:5432/orbitalwatch
REDIS_URL=redis://localhost:6379/0
SPACETRACK_USERNAME=your@email.com
SPACETRACK_PASSWORD=your_password
CELESTRAK_BASE_URL=https://celestrak.org
CORS_ORIGINS=http://localhost:3000
APP_ENV=development
```

Then run:

```
start.bat
```

This starts Docker (TimescaleDB + Redis), creates a Python venv, installs deps, loads satellite data on first run, starts the backend on :8000 and frontend on :3000, then opens your browser.

To stop: run `stop.bat`.

### Manual start (any OS)

**1. Database + cache:**

```bash
docker compose up -d
```

**2. Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit with your Space-Track credentials
```

First-time data load (takes ~60s total):

```bash
python init_db.py
python ingest_all.py        # TLEs from CelesTrak (~12k objects)
python ingest_satcat.py     # object types from Space-Track
python ingest_cdms.py       # conjunction messages from Space-Track
```

Start the server:

```bash
uvicorn app.main:app --port 8000
```

**3. Frontend:**

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CESIUM_ION_TOKEN=
```

The Cesium token is optional. Without it the globe uses the default Natural Earth imagery (fine for development). Get a free token at https://ion.cesium.com/tokens for higher-res tiles.

```bash
npm run dev
```

Open http://localhost:3000.

### Local environment variables

#### backend/.env

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://orbital:orbital_dev@localhost:5432/orbitalwatch` | Any `postgres://` / `postgresql://` URL also works — it gets converted to asyncpg automatically |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Position cache and stats cache |
| `SPACETRACK_USERNAME` | Yes | `your@email.com` | Space-Track.org login email (the address you registered with) |
| `SPACETRACK_PASSWORD` | Yes | `yourpassword` | Space-Track.org password |
| `CELESTRAK_BASE_URL` | No | `https://celestrak.org` | Defaults to celestrak.org |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated origins, **must include scheme (`https://`) and no trailing slash** |
| `APP_ENV` | No | `development` | Informational only |

#### frontend/.env.local

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend URL the browser calls. **No trailing slash.** |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | No | `eyJhbGci...` | Optional Cesium Ion token for higher-res imagery |

---

## Hosted deployment (Vercel + Railway)

The frontend is a Next.js app (deploys to Vercel). The backend is a Dockerized FastAPI server (deploys to Railway). The database (PostgreSQL or TimescaleDB) and Redis run as Railway addons.

### Backend on Railway

1. Push this repo to GitHub (or fork it)
2. Go to https://railway.app → **New Project** → **Deploy from GitHub repo** → pick your fork
3. In the service that Railway creates, go to **Settings → Source** and set **Root Directory** to `backend`. Railway will detect the Dockerfile and build automatically.
4. Add a database addon — two options:
   - **Standard Postgres** (default): Railway dashboard → **+ New** → **Database** → **PostgreSQL**. Works fine. The app detects missing TimescaleDB and falls back to plain Postgres automatically.
   - **TimescaleDB** (optional, better on huge datasets): Railway dashboard → **+ New** → **Template** → search "TimescaleDB" → deploy.
5. Add a **Redis** addon: Railway dashboard → **+ New** → **Database** → **Redis**
6. In your backend service → **Variables** tab, set these. For `DATABASE_URL` and `REDIS_URL`, use Railway's reference variables so they stay in sync with the addons:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (or `${{TimescaleDB.DATABASE_URL}}` if using the template) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `SPACETRACK_USERNAME` | Your Space-Track.org email |
| `SPACETRACK_PASSWORD` | Your Space-Track.org password |
| `CORS_ORIGINS` | Your Vercel frontend URL, e.g. `https://orbital-watch.vercel.app`. **Must include `https://` and no trailing slash.** Comma-separate if you have multiple URLs (preview deploys, custom domain, etc.). |
| `CELESTRAK_BASE_URL` | `https://celestrak.org` |
| `APP_ENV` | `production` |

7. In your backend service → **Settings → Networking**, click **Generate Domain** to get a public URL like `https://orbitalwatch-production.up.railway.app`. Save this — you'll need it for the Vercel config.
8. Deploy. Tables are created automatically on startup. The `/` healthcheck should go green within 30 seconds.
9. After the first deploy, the database is empty. Load the initial data once. Install the Railway CLI (`npm i -g @railway/cli`), then:

```bash
railway login
railway link           # pick your project and backend service
railway ssh            # open a shell in the deployed container
python ingest_all.py
python ingest_satcat.py
python ingest_cdms.py
```

You can also use Railway's web-based shell (backend service → **⋯ menu → Shell**).

The backend's built-in scheduler refreshes all data every 4 hours after that — no need to rerun these scripts unless the DB is wiped.

**Notes:**
- On plain Postgres, the `timescaledb` extension isn't available. The app logs a one-line notice on startup and keeps working with standard Postgres. The `timescaledb` hypertable features aren't used yet, so there's no functional difference.
- If you used the TimescaleDB template, the extension installs automatically.

### Frontend on Vercel

1. Go to https://vercel.com → **Add New → Project** → import the same GitHub repo
2. Set **Root Directory** to `frontend`
3. Framework preset: **Next.js** (auto-detected)
4. Set these environment variables (all apply to Production, Preview, and Development):

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL, e.g. `https://orbitalwatch-production.up.railway.app`. **No trailing slash.** |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | Optional. Free token from https://ion.cesium.com/tokens |

5. Deploy. The build runs `npm install` (which triggers `postinstall` → copies Cesium CSS assets), then `next build`. Cesium itself is loaded from jsdelivr at runtime.
6. Once deployed, visit your Vercel URL. The globe should render, the stats bar should show object counts, and the conjunction feed should populate within a few seconds.

### Common deployment gotchas

**"No conjunctions found" / globe shows 0 objects / stats say "Never":**
The ingestion scripts haven't run. See step 9 under Railway above.

**Browser console: "blocked by CORS policy":**
`CORS_ORIGINS` on Railway doesn't match your Vercel URL exactly. The origin must include `https://` and have no trailing slash. If Vercel generates multiple URLs (preview URLs, aliases, custom domains), comma-separate them in `CORS_ORIGINS`.

**404s on `/api/...` requests with double slashes like `//api/positions`:**
`NEXT_PUBLIC_API_URL` on Vercel has a trailing slash. Remove it. The frontend also strips trailing slashes defensively, so redeploying after the fix resolves this.

**Railway backend crashes with `DATABASE_URL not set` or similar:**
The Postgres/Redis addons aren't linked, or the reference variables (`${{Postgres.DATABASE_URL}}`) are typed wrong. Use Railway's variable picker UI — don't hand-type the reference syntax.

**Vercel build fails with "Octal escape sequences are not allowed":**
This was a Turbopack issue with Cesium's bundled chunks. It's fixed — Cesium now loads from jsdelivr CDN at runtime instead of being bundled. If you see this error, make sure you're building from `main` (commit `c4b4077` or later).

**CelesTrak returns 403 on ingestion:**
You're being rate-limited. The `ingest_all.py` script hits 20 small groups with 2-second delays to avoid this, but restarting repeatedly can still trigger the limit. Wait 15 minutes and try again.

---

## API

All endpoints are under `/api`. The backend also serves auto-generated Swagger docs at `/docs`.

| Route | Method | Returns |
|-------|--------|---------|
| `/api/positions?limit=2000&object_type=PAYLOAD` | GET | Lat/lon/alt for tracked satellites |
| `/api/positions/{norad_id}/trail` | GET | 60 points along a satellite's orbit (30 min before/after now) |
| `/api/conjunctions?min_pc=1e-5&days=7` | GET | CDMs sorted by collision probability |
| `/api/conjunctions/{cdm_id}` | GET | Full CDM record with readable risk summary |
| `/api/satellites/search?q=ISS` | GET | Name or NORAD ID search with conjunction counts |
| `/api/satellites/{norad_id}` | GET | Orbital elements and active conjunction count |
| `/api/satellites/{norad_id}/conjunctions?days=90` | GET | CDMs involving this satellite |
| `/api/stats` | GET | Object count, active conjunctions, data freshness |

---

## Architecture

```
CelesTrak ──(TLE/OMM JSON)──┐
Space-Track ──(CDMs, SATCAT)─┤
                             v
                    FastAPI backend ──> PostgreSQL (or TimescaleDB)
                       (Python)              │
                           │                 │
                       SGP4 prop ──> Redis  ─┤
                       (5k sats/60s) (cache) │
                           │                 │
                           v                 │
                    Next.js frontend <───────┘
                   (CesiumJS from CDN)
                        │
                    Vercel edge
```

- **SGP4** (python-sgp4) propagates orbital elements into lat/lon/alt positions
- **CesiumJS** is loaded from jsdelivr CDN at runtime (not bundled — avoids Next.js 16 / Turbopack strict-mode issues with Cesium's chunks)
- **Redis** caches the latest 5,000 precomputed positions (refreshed every 60s) and stats
- The FastAPI app has a built-in background scheduler (no Celery) — handles position precomputation and periodic TLE/CDM/SATCAT refresh

---

## Ingestion scripts

Run from the `backend/` directory with the venv activated. Locally, or via `railway ssh` in production.

| Script | What it does | Data source |
|--------|-------------|-------------|
| `python init_db.py` | Creates database tables. Called automatically by the scripts below but safe to run directly. | — |
| `python ingest_all.py` | Loads TLEs from 20 CelesTrak groups + CDMs from Space-Track | CelesTrak + Space-Track |
| `python ingest_tles.py [group]` | Loads one CelesTrak group (default: `active`) | CelesTrak |
| `python ingest_cdms.py [days] [min_pc]` | Loads CDMs (default: 7 days, Pc > 1e-6) | Space-Track |
| `python ingest_satcat.py` | Updates object types (PAYLOAD / DEBRIS / ROCKET BODY) for all satellites | Space-Track |

---

## Project structure

```
OrbitalWatch/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + background scheduler
│   │   ├── config.py            # Environment-based settings, URL normalizer
│   │   ├── database.py          # Async SQLAlchemy engine, optional TimescaleDB
│   │   ├── models.py            # gp_elements + cdm tables
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── routers/             # API endpoints
│   │   │   ├── positions.py     # /api/positions, /api/positions/{id}/trail
│   │   │   ├── conjunctions.py  # /api/conjunctions
│   │   │   ├── satellites.py    # /api/satellites
│   │   │   └── stats.py         # /api/stats
│   │   └── services/            # Data fetching and processing
│   │       ├── propagator.py    # SGP4 orbit propagation (TLE + OMM)
│   │       ├── tle_ingest.py    # CelesTrak GP fetching
│   │       ├── cdm_ingest.py    # Space-Track CDM fetching
│   │       ├── satcat_ingest.py # Space-Track SATCAT (object types)
│   │       └── cache.py         # Redis helpers
│   ├── Dockerfile               # For Railway deployment
│   ├── railway.toml             # Railway build config
│   ├── requirements.txt
│   ├── init_db.py
│   ├── ingest_all.py
│   ├── ingest_tles.py
│   ├── ingest_cdms.py
│   └── ingest_satcat.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Main page layout
│   │   │   └── layout.tsx       # Root layout + metadata
│   │   ├── components/
│   │   │   ├── Globe.tsx        # CesiumJS 3D globe (loads Cesium from CDN)
│   │   │   ├── ConjunctionFeed.tsx
│   │   │   ├── ConjunctionDetail.tsx
│   │   │   ├── SatellitePanel.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   └── StatsBar.tsx
│   │   ├── hooks/               # usePositions, useConjunctions
│   │   └── lib/                 # API client (strips trailing slashes), TypeScript types
│   ├── scripts/copy-cesium.mjs  # Copies Cesium widget CSS on npm install
│   ├── vercel.json              # Vercel build config
│   ├── next.config.ts
│   └── package.json
├── docker-compose.yml           # TimescaleDB + Redis for local dev
├── start.bat                    # One-click Windows launcher
├── stop.bat                     # Stops all services
└── README.md
```

---

## Notes

- The 5,000 object limit on the globe is a performance cap. The database holds 12,000+ satellites, but WebGL slows down past ~5k rendered points. The limit is in the SQL query in `backend/app/routers/positions.py` and can be raised if your GPU handles it.
- CelesTrak rate-limits aggressive fetching. The ingestion scripts fetch from 20 small groups instead of the single "active" group to avoid 403s. There's a 2-second delay between group fetches.
- CDM data from the public `cdm_public` endpoint on Space-Track has fewer fields than the full `cdm` class (which requires operator privileges). The public class provides: `CDM_ID`, `TCA`, `MIN_RNG` (km), `PC`, `SAT_1_ID`, `SAT_1_NAME`, `SAT1_OBJECT_TYPE`, `SAT_2_ID`, `SAT_2_NAME`, `SAT2_OBJECT_TYPE`. No relative speed or covariance data.
- Object types (PAYLOAD, DEBRIS, ROCKET BODY) come from the SATCAT, not from CelesTrak. If you skip `ingest_satcat.py`, everything shows as UNKNOWN and the filter buttons won't split properly.
- CesiumJS is loaded from `cdn.jsdelivr.net/npm/cesium@1.140/Build/Cesium/Cesium.js` at runtime. This sidesteps a Next.js 16 / Turbopack issue where Cesium's bundled chunks use octal escape sequences in template literals, which ES module strict mode forbids.
- This is not an operational tool. Don't use it for conjunction avoidance decisions. Real operators have access to non-public data (owner/operator ephemeris, maneuver plans, covariance matrices) that significantly changes risk assessments.

## License

MIT
