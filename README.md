# Publicus Technical

Publicus is currently a Nix-backed SvelteKit + FastAPI workspace for exploring Canadian public funding data. The backend wraps Open Canada data sources, and the frontend presents the records in a FundRadar-style funding discovery UI.

## Current State

- Nix flake and direnv are set up at the repository root.
- The frontend is a SvelteKit app in `frontend/`.
- The backend is a multi-file FastAPI package in `backend/publicus_backend/`.
- Grants and Contributions data is pulled from Open Canada's CKAN APIs.
- Business Benefits Finder data is pulled from the latest Open Canada XLSX resource.
- The frontend has routes for a landing page, dashboard, grant browsing, business benefits, live views, persona pages, matches, and settings.
- Dashboard data loading supports URL-backed filters such as `source`, `year`, `count`, and `sort`.

## Project Layout

```text
.
├── .envrc
├── flake.nix
├── backend/
│   ├── main.py
│   ├── open_canada_grants_scraper.py
│   ├── pyproject.toml
│   └── publicus_backend/
│       ├── app.py
│       ├── routers/
│       │   ├── business_benefits.py
│       │   ├── grants.py
│       │   └── health.py
│       └── services/
│           ├── business_benefits.py
│           └── grants.py
└── frontend/
    ├── package.json
    └── src/
        ├── lib/server/
        │   ├── dashboard-data.ts
        │   └── live-view-data.ts
        └── routes/
            ├── +page.svelte
            ├── dashboard/
            ├── grants-contributions/
            ├── business-benefits-finder/
            ├── live-view/
            ├── persona/
            └── settings/
```

## Development Setup

Enter the dev shell:

```bash
direnv allow .
# or
nix develop
```

The flake dev shell provides:

- Node.js 22
- Python 3.13
- uv
- FastAPI, Uvicorn, Pydantic, HTTPX, pytest
- Chromium on Linux for Business Benefits Finder category scraping
- direnv, git, nil, and nixfmt

Install frontend dependencies when needed:

```bash
npm --prefix frontend install
```

Run the backend:

```bash
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Run the frontend:

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

## Backend

The FastAPI app is created in `backend/publicus_backend/app.py`.

Main sections:

- `routers/grants.py`: Grants and Contributions API routes.
- `routers/business_benefits.py`: Business Benefits Finder API routes.
- `routers/innovation.py`: legacy alias for `/api/innovation/*`.
- `services/grants.py`: Open Canada grants scraper, CKAN helpers, export helpers, and CLI.
- `services/business_benefits.py`: Open Canada Business Benefits Finder XLSX parser and category scraping logic.

Useful endpoints:

```text
GET  /health
GET  /api/grants
GET  /api/grants/discover
GET  /api/grants/first/{count}
GET  /api/grants/by-calendar-year/{year}
GET  /api/grants/by-reference/{ref_number}
GET  /api/grants/csv-url
POST /api/grants/export
GET  /api/business-benefits/first/{count}
GET  /api/business-benefits/by-category
GET  /api/business-benefits/by-category/{category}
GET  /api/innovation/first/{count}
```

Fast grant query example:

```bash
curl -G 'http://127.0.0.1:8000/api/grants' \
  --data-urlencode 'year=2024' \
  --data-urlencode 'limit=25' \
  --data-urlencode 'sort=amount' \
  --data-urlencode 'include_total=false'
```

Direct Open Canada grant lookup example:

```bash
curl -G 'https://open.canada.ca/data/api/3/action/datastore_search' \
  --data-urlencode 'resource_id=1d15a62f-5656-49ad-8c88-f40ce689d831' \
  --data-urlencode 'limit=1' \
  --data-urlencode 'filters={"ref_number":"199-2019-2020-Q4- CSGC16725277"}'
```

## Data Flow

### Grants

The grants scraper targets:

```text
https://search.open.canada.ca/grants/
```

The site itself is rendered as a web search page, but the raw data comes from Open Canada's CKAN API:

```text
https://open.canada.ca/data/api/3/action/package_show?id=432527ab-7aac-45b5-81d6-7597107a7013
https://open.canada.ca/data/api/3/action/datastore_search
```

The backend uses `package_show` to discover the dataset resources and `datastore_search` to fetch JSON records by resource id. The main grants resource id is:

```text
1d15a62f-5656-49ad-8c88-f40ce689d831
```

For frontend filters, `/api/grants` supports:

- `limit`
- `offset`
- `year`
- `sort=score|amount|newest`
- `include_total=false` for faster filtered SSR responses
- `q`
- repeated `filter=key=value`

### Business Benefits Finder

Business Benefits Finder uses this Open Canada package:

```text
https://open.canada.ca/data/api/3/action/package_show?id=4e75337e-70d0-4ed7-92d1-3b85192ec6b1
```

The backend picks the latest XLSX resource, downloads it, and parses the spreadsheet with Python stdlib ZIP/XML tools. Category routes use Chromium because the XLSX feed does not include the category labels exposed by the official rendered page.

## Frontend

The root route is a landing page. The active data views live under:

```text
/dashboard
/grants-contributions
/business-benefits-finder
/live-view
/persona
/persona/matches
/settings
```

The dashboard server loader reads URL search params and calls the backend accordingly:

```text
/dashboard?source=grants&year=2024&count=25&sort=amount
/dashboard?source=innovation&count=25&sort=newest
```

The SvelteKit server-side data helpers live in:

- `frontend/src/lib/server/dashboard-data.ts`
- `frontend/src/lib/server/live-view-data.ts`

Some frontend views render immediately from SSR metadata and then hydrate records through the local backend/cache helpers in the browser.

## Scraper CLI

The grants scraper can be run directly:

```bash
python backend/open_canada_grants_scraper.py discover
python backend/open_canada_grants_scraper.py dump --max-records 100 --output backend/data/grants.sample.jsonl
python backend/open_canada_grants_scraper.py dump --format csv --max-records 100 --output backend/data/grants.sample.csv
```

The full grants CSV is over 2 GB, so prefer the streaming datastore dump commands unless the raw CSV is explicitly needed.

## Verification

Useful checks:

```bash
nix develop -c npm --prefix frontend run check
nix develop -c npm --prefix frontend run build
nix develop -c python -m compileall backend/publicus_backend
nix flake check
```

The most recent verification pass completed successfully with the commands above.

## Notes

- This is still an active technical workspace, not a production deployment.
- There is no database yet; records are fetched from public Open Canada sources.
- There is no authentication yet.
- `BACKEND_API_URL` can be set for the SvelteKit server if the FastAPI backend is not running at `http://127.0.0.1:8000`.
