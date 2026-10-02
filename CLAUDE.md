# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

TCG-exemple is a trading card game (TCG) example website. It is being built in place of the course's "prelegal" website project. Target completion date: **October 8, 2026**.

## Commands

Backend (from `backend/`, needs uv):
- Install: `uv sync`
- Dev server: `uv run uvicorn --factory app.main:create_app --reload --port 8000` (load `../.env` for the AI chat)
- Tests: `uv run pytest`; single test: `uv run pytest tests/test_catalog.py::test_filters -v`
- Refresh card data: `uv run python -m scripts.fetch_catalog`

Frontend (from `frontend/`):
- Install: `npm ci`
- Dev server: `npm run dev` (http://localhost:3000, proxies `/api` to :8000)
- Build: `npm run build` (static export to `out/`); lint: `npm run lint`
- Tests: `npm test`; single file: `npx vitest run lib/explorer.test.ts`

Whole app: `./scripts/start.sh` / `./scripts/stop.sh` (Windows: `scripts/start.ps1` / `stop.ps1`), http://localhost:8000.

## Architecture

- `backend/app/catalog.py` and `collection.py` hold all data logic on SQLite; both the REST routes (`main.py`) and the AI tools (`tools.py`) call them.
- `db.py` creates the database and loads the catalog snapshot `backend/data/catalog.json.gz` when its version changes. Catalog rows are never deleted.
- `scripts/fetch_catalog.py` builds the snapshot from TCGdex: French first, English-only sets and cards added with `lang = 'en'` (labelled "Édition anglaise"), sub-sets (galleries, vaults) filed under their main set via `SUBSETS`, missing French images filled from TCGdex files then English scans. Data choices and image gaps: `docs/PLAN.md`.
- `chat.py` runs the OpenRouter tool loop and returns `{reponse, actions}`; the frontend applies `naviguer` (change URL) and `rafraichir` (refetch) actions.
- The frontend is a Next.js 16 static export served by FastAPI at `/` (read `frontend/AGENTS.md`: Next 16 docs are in `node_modules/next/dist/docs/`). The explorer's state lives in the URL (`lib/explorer.ts`). Styles are plain CSS tokens in `app/globals.css`.
- Design spec: `docs/superpowers/specs/2026-10-02-tcg-collection-mvp-design.md`.
