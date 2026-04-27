# Repository Guidelines

## Project Structure & Module Organization

This repository contains a SvelteKit frontend, FastAPI backend, Nix development shell, and Supabase migrations.

- `frontend/src/routes`: SvelteKit pages and API endpoints. Dashboard routes live under `frontend/src/routes/dashboard`.
- `frontend/src/lib`: shared Svelte components plus client/server utilities.
- `frontend/static`: static browser assets.
- `backend/publicus_backend`: FastAPI application code, split into `routers`, `services`, `schemas`, and `core`.
- `backend/data`: local backend data files, if generated or cached.
- `supabase/migrations`: database migrations.
- `flake.nix`: reproducible dev shell, build, formatter, and package definitions.

## Build, Test, and Development Commands

Use the Nix shell for consistent Node, Python, uv, Chromium, and formatter versions.

- `direnv allow .`: load the flake shell automatically.
- `nix develop`: enter the development shell manually.
- `npm --prefix frontend install`: install frontend dependencies.
- `npm --prefix frontend run dev -- --host 0.0.0.0`: run SvelteKit locally.
- `uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload`: run the FastAPI backend.
- `npm --prefix frontend run check`: run SvelteKit sync and type diagnostics.
- `npm --prefix frontend run build`: build the production frontend.
- `python -m compileall backend/publicus_backend`: quick backend syntax check.
- `pytest backend`: run backend tests when test files are present.
- `nix fmt`: format Nix files.

## Coding Style & Naming Conventions

Use TypeScript for frontend logic and Python 3.13 for backend logic. Keep Svelte components in PascalCase, route files named by SvelteKit convention (`+page.svelte`, `+server.ts`, `+page.server.ts`), Python modules in `snake_case`, and FastAPI routers grouped by domain. Prefer small service functions in `backend/publicus_backend/services` and thin routers in `backend/publicus_backend/routers`.

## Testing Guidelines

Frontend changes should pass `npm --prefix frontend run check` and `npm --prefix frontend run build`. Backend changes should pass `python -m compileall backend/publicus_backend`; add `pytest` tests under `backend/tests` or near the relevant backend package when behavior becomes non-trivial. Name tests `test_<feature>.py`.

## Commit & Pull Request Guidelines

Recent history uses concise messages such as `feat: add authenticated funding dashboard and matching workflows`. Prefer Conventional Commit prefixes like `feat:`, `fix:`, `chore:`, and `docs:`. Pull requests should include a short summary, verification commands run, linked issue or context, and screenshots for visible UI changes.

## Security & Configuration Tips

Do not commit secrets or local `.env` values. Supabase keys and service configuration should come from environment variables. Keep generated build folders, caches, and virtual environments out of commits unless explicitly required.
