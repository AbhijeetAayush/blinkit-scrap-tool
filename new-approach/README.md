# New-approach harvest stack

Greenfield Blinkit harvest: Playwright + Bright Data/Oxylabs proxy, Postgres, Redis ARQ.
Old `apps/web` and `services/workers` are untouched.

## Quick start

### 1. Backend (Docker)

```bash
cd new-approach
# edit .env — set PROXY_PROVIDER=brightdata (or none/oxylabs) and credentials
docker compose up --build
```

Services: Postgres `:5432`, Redis `:6379`, API `:8000`, Worker (Playwright).

Health: http://localhost:8000/health

### 2. Frontend (host, not Docker)

```bash
cd new-approach/frontend
npm install
npm run dev
```

Open http://localhost:3000 — register → Setup → Runs → Shelf.

### Proxy env

```bash
PROXY_PROVIDER=none          # direct Playwright (local proof)
# or
PROXY_PROVIDER=brightdata
BRIGHTDATA_CUSTOMER=...
BRIGHTDATA_ZONE=...
BRIGHTDATA_PASSWORD=...
BRIGHTDATA_ENDPOINT=brd.superproxy.io:44445
BRIGHTDATA_COUNTRY=in

# or
PROXY_PROVIDER=oxylabs
OXYLABS_USERNAME=...
OXYLABS_PASSWORD=...
```

Switch vendors by changing `.env` and restarting the worker — no code changes.

### Add a platform later

1. `backend/app/platforms/zepto/{constants,browser,parser,catalog}.py`
2. Register in `platforms/registry.py`
3. Frontend platform select gets it via `known_ids()`

## API

Base: `/api/v1` — auth, keywords, locations, runs, shelf. See OpenAPI at http://localhost:8000/docs
