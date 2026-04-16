# OrbitalWatch

3D globe that shows where satellites are and flags predicted close approaches between objects in Earth orbit. Uses public data from the U.S. government: orbital elements from CelesTrak and conjunction data messages (CDMs) from Space-Track.org.

Built with Next.js, CesiumJS, FastAPI, SGP4, TimescaleDB, and Redis.

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
SPACETRACK_USERNAME=your_username_here
SPACETRACK_PASSWORD=your_password_here
CELESTRAK_BASE_URL=https://celestrak.org
CORS_ORIGINS=http://localhost:3000
APP_ENV=development
```

Then run:

```
start.bat
```

This does everything: starts Docker (TimescaleDB + Redis), creates a Python venv, installs deps, loads satellite data on first run, starts the backend on :8000 and frontend on :3000, then opens your browser.

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

First-time data load (takes ~60s):

```bash
python init_db.py
python ingest_all.py        # TLEs from CelesTrak
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

The Cesium token is optional. Without it the globe uses built-in Natural Earth imagery. Get a free token at https://ion.cesium.com/tokens if you want higher-res tiles.

```bash
npm run dev
```

Open http://localhost:3000.

### Local environment variables

#### backend/.env

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://orbital:orbital_dev@localhost:5432/orbitalwatch` | asyncpg driver for the FastAPI async engine |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Position cache and stats cache |
| `SPACETRACK_USERNAME` | Yes | `your@email.com` | Space-Track.org login email |
| `SPACETRACK_PASSWORD` | Yes | `yourpassword` | Space-Track.org password |
| `CELESTRAK_BASE_URL` | No | `https://celestrak.org` | Defaults to celestrak.org |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed origins |
| `APP_ENV` | No | `development` | Not used functionally yet |

#### frontend/.env.local

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` | Backend URL the browser calls |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | No | `eyJhbGci...` | Optional, for Cesium Ion imagery |

---

## Hosted deployment (Vercel + Railway)

### Backend on Railway

1. Push this repo to GitHub
2. Go to https://railway.app, create a new project from your GitHub repo
3. Set the **root directory** to `backend`
4. Railway will detect the Dockerfile and build automatically
5. Add a **PostgreSQL** addon (Railway dashboard > New > Database > PostgreSQL)
6. Add a **Redis** addon (Railway dashboard > New > Database > Redis)
7. Set these environment variables in the Railway service settings:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Provided automatically by the PostgreSQL addon. Copy the `DATABASE_URL` from the addon's Variables tab. |
| `REDIS_URL` | Provided automatically by the Redis addon. Copy the `REDIS_URL` from the addon's Variables tab. |
| `SPACETRACK_USERNAME` | Your Space-Track.org email |
| `SPACETRACK_PASSWORD` | Your Space-Track.org password |
| `CORS_ORIGINS` | Your Vercel frontend URL, e.g. `https://orbital-watch.vercel.app` |
| `CELESTRAK_BASE_URL` | `https://celestrak.org` |
| `APP_ENV` | `production` |

8. Deploy. Railway gives you a public URL like `https://orbitalwatch-backend-production.up.railway.app`
9. After first deploy, trigger initial data load by running the ingestion scripts once. You can do this via Railway's shell (Settings > Shell):

```bash
python init_db.py
python ingest_all.py
python ingest_satcat.py
python ingest_cdms.py
```

The backend scheduler will keep data fresh after that.

### Frontend on Vercel

1. Go to https://vercel.com, import the same GitHub repo
2. Set the **root directory** to `frontend`
3. Framework preset: **Next.js** (auto-detected)
4. Set these environment variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Railway backend URL, e.g. `https://orbitalwatch-backend-production.up.railway.app` |
| `NEXT_PUBLIC_CESIUM_ION_TOKEN` | Optional. Free token from https://ion.cesium.com/tokens |

5. Deploy. Vercel handles the build and the `postinstall` script copies Cesium assets automatically.

---

## API

All endpoints are under `/api`. The backend also serves Swagger docs at `/docs`.

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
CelesTrak ──(TLE/OMM JSON)──> FastAPI backend ──> TimescaleDB
Space-Track ──(CDM REST API)──>     |                 |
                                    v                 |
                                  SGP4 ───> Redis     |
                                (propagation) (cache) |
                                    |                 |
                               Next.js frontend <────┘
                              (CesiumJS globe)
```

- **SGP4** (python-sgp4) propagates orbital elements into lat/lon/alt positions
- **TimescaleDB** stores GP elements and CDMs
- **Redis** caches the latest 5,000 positions (refreshed every 60s) and stats
- **CesiumJS** renders the 3D globe with satellite points, labels, and click interaction

---

## Ingestion scripts

Run these from the `backend/` directory with the venv activated.

| Script | What it does | Data source |
|--------|-------------|-------------|
| `python ingest_all.py` | Loads TLEs from 20 CelesTrak groups + CDMs from Space-Track | CelesTrak + Space-Track |
| `python ingest_tles.py [group]` | Loads one CelesTrak group (default: "active") | CelesTrak |
| `python ingest_cdms.py [days] [min_pc]` | Loads CDMs (default: 7 days, Pc > 1e-6) | Space-Track |
| `python ingest_satcat.py` | Updates object types (PAYLOAD/DEBRIS/ROCKET BODY) | Space-Track |
| `python init_db.py` | Creates database tables (run before first ingestion) | - |

---

## Project structure

```
OrbitalWatch/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + background scheduler
│   │   ├── config.py            # Environment-based settings
│   │   ├── database.py          # Async SQLAlchemy engine
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
│   ├── railway.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/page.tsx         # Main page layout
│   │   ├── components/
│   │   │   ├── Globe.tsx        # CesiumJS 3D globe
│   │   │   ├── ConjunctionFeed.tsx
│   │   │   ├── ConjunctionDetail.tsx
│   │   │   ├── SatellitePanel.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   └── StatsBar.tsx
│   │   ├── hooks/               # usePositions, useConjunctions
│   │   └── lib/                 # API client, TypeScript types
│   ├── scripts/copy-cesium.mjs  # Copies Cesium assets on npm install
│   ├── vercel.json
│   └── package.json
├── docker-compose.yml           # TimescaleDB + Redis for local dev
├── start.bat                    # One-click Windows launcher
└── stop.bat                     # Stops all services
```

---

## Notes

- The 5,000 object limit on the globe is a performance cap. The database holds 12,000+ satellites but WebGL slows down past ~5k rendered points. The limit is in the SQL query in `positions.py` and can be raised if your GPU handles it.
- CelesTrak rate-limits aggressive fetching. The ingestion scripts fetch from 20 small groups instead of the single "active" group to avoid 403s. There's a 2-second delay between group fetches.
- CDM data from `cdm_public` on Space-Track has fewer fields than the full `cdm` class (which requires operator privileges). The public class includes: CDM_ID, TCA, MIN_RNG (km), PC, SAT_1_ID, SAT_1_NAME, SAT1_OBJECT_TYPE, SAT_2_ID, SAT_2_NAME, SAT2_OBJECT_TYPE. No relative speed or covariance data.
- Object types (PAYLOAD, DEBRIS, ROCKET BODY) come from the SATCAT, not from CelesTrak. If you skip `ingest_satcat.py`, everything shows as UNKNOWN.
- This is not an operational tool. Don't use it for conjunction avoidance decisions. Operators have access to non-public data (owner/operator ephemeris, maneuver plans, covariance matrices) that changes risk assessments.

## License

MIT
