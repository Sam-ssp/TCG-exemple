# Plan: TCG Collection MVP

Jira: KAN-5. Deadline: 2026-10-08.

The full design (schema, API, pages, AI chat, tests) is in `docs/superpowers/specs/2026-10-02-tcg-collection-mvp-design.md`. This file records the data choices behind it and replaces the earlier `DATABASE_Plan.md`, which targeted PostgreSQL, GitHub Actions, a hosted database, prices and English.

## Data source

**TCGdex** (https://tcgdex.dev), French catalog (`/v2/fr`): free, no API key, MIT-licensed data, every physical set from Base Set to Mega Evolution. Last count (2026-10-01): 202 French sets including Pokemon TCG Pocket (series `tcgp`), which is excluded. The French card count and image coverage are measured by the fetch script's report.

Not used:
- pokemontcg.io: English only, deprecated, offline from 2027-03-01.
- Paid sources (Scrydex, JustTCG): only needed for prices, which are out of scope.

## How the data gets into the app

- `backend/scripts/fetch_catalog.py` is run by a developer. It fetches the catalog once (detail requests are needed for rarity, illustrator and Pokedex numbers), at low concurrency as TCGdex asks, and writes `backend/data/catalog.json.gz`.
- The snapshot is committed and copied into the Docker image. On start-up the backend creates the SQLite database if needed and loads the catalog when its version changed. User data is never touched by a catalog load, and catalog rows are never deleted.
- New set released: rerun the script, commit the snapshot, rebuild the image.

## Images

Only the TCGdex image base URL is stored. The browser loads `{base}/low.webp` in grids and `{base}/high.webp` on the card page; TCGdex serves them with open CORS and a one-year cache. Images are never copied: the scans belong to The Pokemon Company and are not covered by TCGdex's license. Cards without an image show a placeholder.

## Not in the MVP

Prices and price history, languages other than French, Japanese/Asian sets, scheduled syncs, hosting, real authentication.
