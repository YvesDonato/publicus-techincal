# Publicus backend

The backend is a FastAPI app split by data section:

- `publicus_backend/routers/grants.py` exposes Grants and Contributions routes.
- `publicus_backend/routers/business_benefits.py` exposes Business Benefits Finder routes.
- `publicus_backend/routers/innovation.py` keeps the legacy `/api/innovation/*` alias for the frontend.
- `publicus_backend/services/grants.py` contains the Open Canada grants scraper and CLI logic.
- `publicus_backend/services/business_benefits.py` fetches and parses the latest Business Benefits Finder XLSX resource from Open Canada, and renders the official page when category labels are needed.

The grants scraper targets the public Grants and Contributions search page:

`https://search.open.canada.ca/grants/`

The page is server-rendered, but its network surface exposes useful raw endpoints:

- `GET https://open.canada.ca/data/api/3/action/package_show?id=432527ab-7aac-45b5-81d6-7597107a7013`
- `GET https://open.canada.ca/data/api/3/action/datastore_search?resource_id=1d15a62f-5656-49ad-8c88-f40ce689d831&limit=5000&offset=0`
- `POST https://search.open.canada.ca/grants/export/`
- `GET https://search.open.canada.ca/search-results/en/grants/<task-id>`
- Direct CSV resource URL discovered from `package_show`

The Business Benefits Finder route uses the Open Canada Business Benefits Finder dataset:

- `GET https://open.canada.ca/data/api/3/action/package_show?id=4e75337e-70d0-4ed7-92d1-3b85192ec6b1`
- Latest XLSX resource from that package, parsed with Python stdlib XML/ZIP tools.
- Category endpoints render the official Business Benefits Finder page with Chromium because the XLSX feed does not include category labels.

Run from the repository root:

```bash
nix develop
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
# or:
python backend/main.py
python backend/open_canada_grants_scraper.py discover
python backend/open_canada_grants_scraper.py dump --max-records 100 --output backend/data/grants.sample.jsonl
python backend/open_canada_grants_scraper.py dump --format csv --max-records 100 --output backend/data/grants.sample.csv
```

The full grants CSV is currently over 2 GB. Prefer `dump` for streaming JSONL/CSV from the CKAN datastore API, or use `download-csv` only when you explicitly want the full raw CSV file.

## FastAPI endpoints

Once the server is running, the interactive docs are available at:

`http://localhost:8000/docs`

Useful endpoints:

- `GET /health`
- `GET /api/grants/discover`
- `GET /api/grants?limit=10&offset=0`
- `GET /api/grants?year=2024&limit=25&sort=amount&include_total=false`
- `GET /api/grants/first/10`
- `GET /api/grants/by-calendar-year/2024?limit=10&order=desc`
- `GET /api/business-benefits/first/10`
- `GET /api/business-benefits/by-category?limit=10`
- `GET /api/business-benefits/by-category/Grants?limit=10`
- `GET /api/innovation/first/10`
- `GET /api/grants?q=Carleton%20University&limit=5`
- `GET /api/grants?filter=owner_org=casdo-ocena&limit=5`
- `GET /api/grants/by-reference/199-2019-2020-Q4-%20CSGC16725277`
- `GET /api/grants/csv-url`
- `POST /api/grants/export`

For frontend URL-backed filters, prefer the fast `/api/grants` query shape with `year`, `limit`, `sort`, and `include_total=false`. The calendar-year route still exists, but it does more CKAN offset work and is better suited for backend/API experiments than SSR page loads.
