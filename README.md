# TCG-exemple

A local web app to browse every physical Pokemon TCG card in French, manage a collection and lists, and use an AI assistant. Built as a course project, due October 8, 2026.

## Run

Requires Docker. For the AI assistant, add a `.env` file at the project root containing `OPENROUTER_API_KEY=...`; without it everything else works.

- Mac / Linux: `./scripts/start.sh`, stop with `./scripts/stop.sh`
- Windows: `powershell -File scripts/start.ps1`, stop with `powershell -File scripts/stop.ps1`

Open http://localhost:8000 and sign in with `user` / `user`.

## Data

Card data: TCGdex French catalog (20,039 cards), completed with the 1,344 cards and sets TCGdex only has in English, labelled "Édition anglaise", snapshot in `backend/data/catalog.json.gz` (see `THIRD_PARTY_NOTICES.md`). Refresh it with `cd backend && uv run python -m scripts.fetch_catalog`, then rebuild.

Design and plan: `docs/`.
