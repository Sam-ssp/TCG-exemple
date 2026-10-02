# Plan: TCG Collection MVP

Jira: KAN-5. Deadline: 2026-10-08.

The full design (schema, API, pages, AI chat, tests) is in `docs/superpowers/specs/2026-10-02-tcg-collection-mvp-design.md`. This file records the data choices behind it and replaces the earlier `DATABASE_Plan.md`, which targeted PostgreSQL, GitHub Actions, a hosted database, prices and English.

## Data source

**TCGdex** (https://tcgdex.dev): free, no API key, MIT-licensed data, every physical set from Base Set to Mega Evolution. Pokemon TCG Pocket (series `tcgp`) is excluded.

- **French first.** Every card TCGdex has in French comes from `/v2/fr`: 20,039 cards.
- **English-only releases.** Sets and cards TCGdex only has in English (Gym Heroes, Team Rocket Returns, Legendary Treasures, missing promos...) come from `/v2/en`: 1,344 cards. They keep their English names and text, are labelled "Édition anglaise" in the app (`lang = 'en'` on cards and sets), and use the French rarity, type, stage and category values so the filters treat both alike.
- **Sub-sets belong to their main set.** TCGdex lists galleries and vaults as their own sets; the fetch files them under the set they belong to (`SUBSETS` in `scripts/fetch_catalog.py`): Galerie Galaroise in Zénith Suprême, the four Galeries de Dresseurs, both Coffres Étincelants, Collection Classique of Célébrations and of 30e Anniversaire (numbered CC001-CC030), Collection Zarbi in EX Forces Cachées, Radiant Collection in Legendary Treasures.
- Snapshot of 2026-10-02: 21,383 cards in 194 visible sets. Jumbo, W Promotional and Sample are announced by TCGdex without card data, so they stay hidden.

Not used:
- pokemontcg.io: English only, deprecated, offline from 2027-03-01.
- Paid sources (Scrydex, JustTCG): only needed for prices, which are out of scope.
- Pokécardex: has French scans for most cards, but its scans are community work and its staff require authorization for reuse (see "Image gaps" below).

## How the data gets into the app

- `backend/scripts/fetch_catalog.py` is run by a developer (`uv run python -m scripts.fetch_catalog` in `backend/`). It fetches series, sets and card details in French, then what French lacks in English, at 5 requests at a time with an identifying User-Agent, and writes `backend/data/catalog.json.gz` with a report of gaps. A full run is about 40,000 requests and 25 minutes; TCGdex publishes no rate limit.
- The snapshot is committed and copied into the Docker image. Its version is the fetch date and time. On start-up the backend creates the SQLite database if needed and loads the catalog when the version changed. User data is never touched by a catalog load, and catalog rows are never deleted.
- New set released: rerun the script, commit the snapshot, rebuild the image.

## Images

Only an image base URL is stored. The browser loads `{base}/low.webp` in grids and `{base}/high.webp` on the card page; TCGdex serves them with open CORS and a one-year cache. Images are never copied: the scans belong to The Pokemon Company and are not covered by TCGdex's license.

The French API omits the image of many cards. For those, the fetch tries in order: the French file at the card's path on TCGdex's CDN (galleries live under their main set's folder), the English scan from the English API, then the English file path.

### Image gaps (2026-10-02)

| French cards | Count |
|---|---|
| French scan | 17,507 |
| English scan shown instead | 1,413 |
| No image on TCGdex in any language | 1,119 |

Most gaps are in Diamant & Perle (754), Soleil et Lune promos and special sets (692), trainer kits (464), McDonald's collections (235) and L'appel des Légendes (106). 151 English-only cards also have no image. Cards without an image show a placeholder.

Remediation, in order:
1. Label English scans on French cards as such on the card page.
2. Ask Pokécardex for permission to show their watermarked scans as a fallback, with attribution and a link to their card page; if agreed, add a set-code mapping and an image source per card.
3. Report the gap list to TCGdex ("Missing Images" issue or their Ingest tool) so French scans land upstream and reach us on the next fetch.

Scraping or re-hosting Pokécardex scans without their agreement is ruled out.

## Not in the MVP

Prices and price history, languages other than French (and English for English-only releases), Japanese/Asian sets, scheduled syncs, hosting, real authentication.
