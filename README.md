# TCG-exemple

A local web app to browse every physical Pokemon TCG card in French, manage a collection and lists, and use an AI assistant. Built as a course project, due October 8, 2026.

## Run

Requires Docker and a `.env` file at the project root containing `OPENROUTER_API_KEY=...`.

- Mac / Linux: `./scripts/start.sh`, stop with `./scripts/stop.sh`
- Windows: `powershell -File scripts/start.ps1`, stop with `powershell -File scripts/stop.ps1`

Open http://localhost:8000 and sign in with `user` / `user`.

## Data

Card data: TCGdex French catalog (20,039 cards, 187 sets), snapshot in `backend/data/catalog.json.gz` (see `THIRD_PARTY_NOTICES.md`). Refresh it with `cd backend && uv run python -m scripts.fetch_catalog`, then rebuild.

Design and plan: `docs/`.
