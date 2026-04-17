# OrbitalWatch

3D globe that shows where satellites are right now and flags predicted close approaches between objects in Earth orbit. All data comes from public U.S. government sources: orbital elements from CelesTrak, conjunction data messages (CDMs) from Space-Track.org.

Stack: Next.js 16, CesiumJS, FastAPI, python-sgp4, PostgreSQL (or TimescaleDB), Redis.

## What it does

The globe renders up to 5,000 satellites on a CesiumJS 3D Earth, color-coded by type: blue for payloads, yellow for rocket bodies, red for debris, gray for unknown.

A sidebar lists predicted close approaches sorted by collision probability (Pc). Color bands go green below 1e-5, yellow up to 1e-4, orange up to 1e-3, and red above that.

Clicking a conjunction opens a detail view with miss distance, Pc, relative speed, and a plain-language summary. Clicking a satellite on the globe opens a panel with its orbital elements (inclination, eccentricity, apogee/perigee) and recent conjunctions. The search bar accepts a name ("ISS", "STARLINK-1234") or a NORAD catalog number.

The top bar tracks total object count, active conjunctions in the next 7 days, and how stale the data is.

Data refreshes automatically. Positions recompute every 60 seconds. TLEs, CDMs, and SATCAT object types refresh every 4 hours.

## Data sources

| Source | What | Auth |
|--------|------|------|
| [CelesTrak](https://celestrak.org) | GP/TLE orbital elements, ~12k objects | None |
| [Space-Track.org](https://www.space-track.org) | CDMs, SATCAT (object types) | Free account |

Register for Space-Track at https://www.space-track.org/auth/createAccount. It takes about a minute.

## Local setup

You need Docker Desktop, Python 3.11+, Node.js 18+, and a Space-Track.org account.

### Quick start on Windows

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

Then run `start.bat`. It brings up Docker (TimescaleDB + Redis), creates a Python venv, installs dependencies, loads satellite data on first run, starts the backend on port 8000 and the frontend on port 3000, and opens the browser.

To shut down: `stop.bat`.

### Manual start on any OS

Start the database and cache:

```bash
docker compose up -d
```

Set up the backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit with your Space-Track credentials
```

Load initial data. This takes about a minute total:

```bash
python init_db.py
python ingest_all.py
python ingest_satcat.py
python ingest_cdms.py
```

Start the API:

```bash
uvicorn app.main:app --port 8000
```

Set up the frontend:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CESIUM_ION_TOKEN=
```

The Ion token is optional. Without one, the globe uses the default Natural Earth imagery, which is fine for development. Higher-resolution tiles need a free token from https://ion.cesium.com/tokens.

Then:

```bash
npm run dev
```

Open http://localhost:3000.

### Local environment variables

`backend/.env`:

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://orbital:orbital_dev@localhost:5432/orbitalwatch` | `postgres://` and `postgresql://` URLs get rewritten to asyncpg automatically |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Position cache and stats cache |
| `SPACETRACK_USERNAME` | Yes | `your@email.com` | The email you registered with at Space-Track.org |
| `SPACETRACK_PASSWORD` | Yes | `yourpassword` | Space-Track.org password |
| `CELESTRAK_BASE_URL` | No | `https://celestrak.org` | Defaults to celestrak.org |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated origins. Must include scheme, no trailing slash. |
| `APP_ENV` | No | `development` | Informational |

`frontend/.env.local`:

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend URL the browser calls. No trailing slash. |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | No | `eyJhbGci...` | Cesium Ion token for higher-res imagery |

## Hosted deployment on Vercel and Railway

Frontend goes to Vercel. Backend goes to Railway. PostgreSQL (or TimescaleDB) and Redis run as Railway addons.

### Backend on Railway

1. Push the repo to GitHub (or fork this one).
2. Go to https://railway.app, create a new project from your GitHub repo.
3. In the service Railway creates, open Settings > Source and set **Root Directory** to `backend`. Railway detects the Dockerfile and builds automatically.
4. Add a database. Two options work:
   - Standard Postgres (recommended): Railway dashboard > + New > Database > PostgreSQL. The app detects missing TimescaleDB and falls back to plain Postgres.
   - TimescaleDB template (optional): Railway dashboard > + New > Template > search for "TimescaleDB".
5. Add Redis: + New > Database > Redis.
6. In the backend service's Variables tab, set these. Use Railway's reference syntax for the database URLs so they stay in sync with the addons:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (or `${{TimescaleDB.DATABASE_URL}}` if using the template) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `SPACETRACK_USERNAME` | Your Space-Track.org email |
| `SPACETRACK_PASSWORD` | Your Space-Track.org password |
| `CORS_ORIGINS` | Your Vercel URL, e.g. `https://orbital-watch.vercel.app`. Must include `https://`, no trailing slash. Comma-separate if you have multiple (preview deploys, custom domain). |
| `CELESTRAK_BASE_URL` | `https://celestrak.org` |
| `APP_ENV` | `production` |

7. In Settings > Networking, click **Generate Domain** to get a public URL like `https://orbitalwatch-production.up.railway.app`. Save it for the Vercel config.
8. Deploy. Tables get created on startup. The `/` healthcheck goes green within 30 seconds.
9. The database starts empty. Load data once using the Railway CLI:

```bash
npm i -g @railway/cli
railway login
railway link           # pick your project and backend service
railway ssh
python ingest_all.py
python ingest_satcat.py
python ingest_cdms.py
```

Railway's web shell works too (backend service > ⋯ menu > Shell).

After that, the scheduler handles refresh. Don't run these again unless you wipe the database.

Two notes on the database choice. Plain Postgres doesn't have the `timescaledb` extension, so the app logs a one-line notice on startup and keeps working with standard Postgres tables. The `timescaledb` hypertable features aren't used yet, so the two options behave identically for now.

### Frontend on Vercel

1. Go to https://vercel.com, import the same GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Next.js (detected automatically).
4. Environment variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL, e.g. `https://orbitalwatch-production.up.railway.app`. No trailing slash. |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | Optional. Free token from https://ion.cesium.com/tokens. |

5. Deploy. `npm install` runs, which triggers the `postinstall` script to copy Cesium widget CSS into `public/cesium/`. Then `next build`. Cesium itself loads from jsdelivr at runtime, not from the bundle.

Once deployed, open the Vercel URL. The globe renders, the stats bar shows object counts, and the conjunction feed populates within a few seconds.

### Things that went wrong during deployment

I hit all of these. Documenting them so you don't have to.

**No conjunctions, globe shows 0 objects, stats say "Never":**
Ingestion scripts haven't run on Railway yet. See step 9 above.

**Browser console shows "blocked by CORS policy":**
`CORS_ORIGINS` on Railway doesn't match your Vercel origin exactly. The match is literal. Include `https://`, leave off the trailing slash, and comma-separate if you have multiple Vercel URLs.

**404s on API calls with double slashes in the path like `//api/positions`:**
`NEXT_PUBLIC_API_URL` on Vercel has a trailing slash. Remove it. The frontend also strips trailing slashes defensively now, so rebuilding after the fix resolves it.

**Vercel build fails with "Octal escape sequences are not allowed in template strings":**
This was a Turbopack issue with Cesium's bundled chunks. It's fixed. Cesium now loads from jsdelivr at runtime instead of getting bundled. If you still see this, make sure you're on `main` at commit `c4b4077` or later.

**CelesTrak returns 403 during ingestion:**
Rate limit. `ingest_all.py` hits 20 small groups with a 2-second delay between each to stay under it, but restarting repeatedly can still trigger it. Wait 15 minutes.

**Railway Postgres doesn't have the `timescaledb` extension:**
Expected. The app catches the error on startup, logs a single line, and keeps working on plain Postgres.

## API

Endpoints are under `/api`. Swagger docs live at `/docs`.

| Route | Method | Returns |
|-------|--------|---------|
| `/api/positions?limit=2000&object_type=PAYLOAD` | GET | Lat/lon/alt for tracked satellites |
| `/api/positions/{norad_id}/trail` | GET | 60 points along a satellite's orbit, 30 min before and after now |
| `/api/conjunctions?min_pc=1e-5&days=7` | GET | CDMs sorted by collision probability |
| `/api/conjunctions/{cdm_id}` | GET | Full CDM record with readable risk summary |
| `/api/satellites/search?q=ISS` | GET | Name or NORAD ID search with conjunction counts |
| `/api/satellites/{norad_id}` | GET | Orbital elements and active conjunction count |
| `/api/satellites/{norad_id}/conjunctions?days=90` | GET | CDMs involving this satellite |
| `/api/stats` | GET | Object count, active conjunctions, data freshness |

## Architecture

```
CelesTrak ──(TLE/OMM JSON)──┐
Space-Track ──(CDMs, SATCAT)┤
                            v
                   FastAPI backend ───> PostgreSQL (or TimescaleDB)
                     (Python)                │
                         │                   │
                     SGP4 prop ───> Redis ───┤
                     (5k sats/60s) (cache)   │
                         │                   │
                         v                   │
                   Next.js frontend <────────┘
                  (CesiumJS from CDN)
                         │
                    Vercel edge
```

python-sgp4 propagates orbital elements into lat/lon/alt positions.

CesiumJS loads from `cdn.jsdelivr.net/npm/cesium@1.140/Build/Cesium/Cesium.js` at runtime, not from the bundle. This sidesteps a Next.js 16 / Turbopack issue where Cesium's chunks use octal escape sequences in template literals, which ES module strict mode forbids.

Redis caches the latest 5,000 precomputed positions (refreshed every 60s) and the stats response.

The FastAPI app has a built-in background scheduler. No Celery. It handles position precomputation and the 4-hour TLE/CDM/SATCAT refresh loop.

## Ingestion scripts

Run from the `backend/` directory with the venv activated. Locally, or via `railway ssh` in production.

| Script | What it does | Data source |
|--------|-------------|-------------|
| `python init_db.py` | Creates database tables. The ingestion scripts call this automatically, but it's safe to run on its own. | — |
| `python ingest_all.py` | Loads TLEs from 20 CelesTrak groups, then CDMs from Space-Track | CelesTrak + Space-Track |
| `python ingest_tles.py [group]` | Loads one CelesTrak group (default: `active`) | CelesTrak |
| `python ingest_cdms.py [days] [min_pc]` | Loads CDMs (default: 7 days ahead, Pc > 1e-6) | Space-Track |
| `python ingest_satcat.py` | Updates object types (PAYLOAD, DEBRIS, ROCKET BODY) for all known satellites | Space-Track |

## Project structure

```
OrbitalWatch/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + background scheduler
│   │   ├── config.py            # Settings, URL normalizer
│   │   ├── database.py          # Async SQLAlchemy engine, optional TimescaleDB
│   │   ├── models.py            # gp_elements + cdm tables
│   │   ├── schemas.py           # Pydantic models
│   │   ├── routers/             # API endpoints
│   │   │   ├── positions.py
│   │   │   ├── conjunctions.py
│   │   │   ├── satellites.py
│   │   │   └── stats.py
│   │   └── services/            # Data fetching and processing
│   │       ├── propagator.py    # SGP4 (TLE + OMM)
│   │       ├── tle_ingest.py    # CelesTrak GP fetching
│   │       ├── cdm_ingest.py    # Space-Track CDM fetching
│   │       ├── satcat_ingest.py # Space-Track SATCAT (object types)
│   │       └── cache.py         # Redis helpers
│   ├── Dockerfile
│   ├── railway.toml
│   ├── requirements.txt
│   ├── init_db.py
│   ├── ingest_all.py
│   ├── ingest_tles.py
│   ├── ingest_cdms.py
│   └── ingest_satcat.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── Globe.tsx        # CesiumJS globe, loads Cesium from CDN
│   │   │   ├── ConjunctionFeed.tsx
│   │   │   ├── ConjunctionDetail.tsx
│   │   │   ├── SatellitePanel.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   └── StatsBar.tsx
│   │   ├── hooks/               # usePositions, useConjunctions
│   │   └── lib/                 # API client (strips trailing slashes), types
│   ├── scripts/copy-cesium.mjs  # Copies Cesium widget CSS on npm install
│   ├── vercel.json
│   ├── next.config.ts
│   └── package.json
├── docker-compose.yml           # TimescaleDB + Redis for local dev
├── start.bat                    # One-click Windows launcher
├── stop.bat                     # Stops all services
└── README.md
```

## Notes

The 5,000 object cap on the globe is a performance limit. The database holds 12,000+ satellites, but WebGL drops frames past about 5k rendered points. The cap lives in the SQL query inside `backend/app/routers/positions.py` and can be raised if the GPU handles it.

CelesTrak rate-limits aggressive fetching. The ingestion scripts pull 20 small groups with a 2-second delay between each instead of the single `active` group, which is more likely to 403. I still managed to trigger the rate limit during testing; waiting 15 minutes fixes it.

CDM data from the public `cdm_public` endpoint has fewer fields than the full `cdm` class (which needs operator privileges). The public class gives you `CDM_ID`, `TCA`, `MIN_RNG` (in km, not meters), `PC`, `SAT_1_ID`, `SAT_1_NAME`, `SAT1_OBJECT_TYPE`, `SAT_2_ID`, `SAT_2_NAME`, `SAT2_OBJECT_TYPE`. No relative velocity, no covariance matrix.

Object types (PAYLOAD, DEBRIS, ROCKET BODY) come from the SATCAT, not from CelesTrak. Skip `ingest_satcat.py` and everything shows as UNKNOWN, which means the filter buttons don't split anything out.

CesiumJS loads from a CDN at runtime. That avoids a Next.js 16 / Turbopack issue where Cesium's bundled chunks use octal escape sequences in template literals, which ES module strict mode rejects. The alternative was forking Cesium or downgrading Next.

Don't use this as an operational tool. Real satellite operators use data this repo doesn't have access to: owner/operator ephemeris, planned maneuvers, covariance matrices from the full CDM class. Risk assessments change substantially with that data.

## License

MIT
