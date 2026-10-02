# DATABASE_Plan: Pokémon TCG card database

> Jira: **KAN-5**. Plan for storing every physical Pokémon TCG card, from Base Set (1999) to the latest expansion, choosing data sources, and keeping the data up to date.
>
> Stack: Next.js (frontend) → FastAPI (Python backend) → PostgreSQL.
> Research and QA date: 2026-10-01. Facts marked *(verified)* were checked against the live systems on that date. The rest comes from documentation and should be rechecked before relying on it.

---

## 1. Scope

| In scope | Out of scope (for now) |
|---|---|
| Every physical TCG set: Base, Gym, Neo, e-Card, EX, DP, Platinum, HGSS, BW, XY, SM, SWSH, SV, Mega Evolution, promos, trainer kits, McDonald's, etc. | **Pokémon TCG Pocket** (a digital game; TCGdex series id `tcgp`, 15 sets / 2,480 cards: filter it out) |
| Card metadata: name, HP, types, attacks, abilities, rarity, illustrator, regulation mark, legality, variants | Japanese-only/Asian sets (TCGdex keeps them separately in `data-asia`; they can be added later) |
| Card images (small + high resolution), set logos and symbols, shown via TCGdex URLs | Graded-card prices (PSA/BGS/CGC) |
| Market prices (Cardmarket EUR, TCGplayer USD) and a limited price history | Deck lists, tournament results |
| Languages: **English** first, **French** second | Other languages (TCGdex supports 10+; the schema already allows them) |

Size *(verified)*:

| Language | Sets (incl. Pocket) | Cards (incl. Pocket) | Physical only (excl. Pocket) |
|---|---|---|---|
| English | 220 | 23,770 | **205 sets / ~21,300 cards** |
| French | 202 | — | — |

French is mostly a subset of English, **but 3 sets exist only in French**: `2013bw`, `2018sm-fr`, `2019sm-fr`.

---

## 2. Data source evaluation

| Source | Cost / access | Coverage | Prices | Status (Oct 2026) | Verdict |
|---|---|---|---|---|---|
| **[TCGdex](https://tcgdex.dev)**, self-hosted Docker image `tcgdex/server` | Free, open source (MIT), no API key | All series from Base to Mega Evolution, 10+ languages | **Yes** *(verified)*: the server itself downloads Cardmarket's public price guide and TCGplayer data (via TCGCSV) at start-up and every 24 hours | Active; the `edge` image is rebuilt from `master` (last build observed 2026-09-30) | ✅ **Primary source: catalog and prices** |
| TCGdex public API (`api.tcgdex.net/v2`) | Free, no key, no published rate limit (*"please be considerate"*) | Same | Same | Active | ⚠️ Development and spot checks only. Production syncs don't need it. |
| [pokemontcg.io](https://pokemontcg.io) (Pokémon TCG API v2) | Free, but new sign-ups are closed | English only | TCGplayer/Cardmarket snapshots | **Deprecated, goes offline 2027-03-01** | ❌ Don't build on it |
| [PokemonTCG/pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data) | Free JSON files | English only | No | **Deprecated**: will no longer receive new sets | ⚠️ One-off cross-check only |
| [Scrydex](https://scrydex.com) (successor to pokemontcg.io) | Paid. Third-party sources disagree on whether there is a free tier (one reports plans from ~$29/month), so check before deciding. | Pokémon + other TCGs | Yes, plus price history, graded prices, population reports | Active | 💰 Upgrade path |
| TCGplayer API / Cardmarket API | Restricted: TCGplayer is reported to no longer grant new developer keys, and Cardmarket's API is for approved sellers (not verified first-hand) | Prices | Yes | Restricted | ❌ Not needed: their data reaches us through TCGdex (section 8 covers the rights) |
| JustTCG, PriceCharting | Free tier / paid | Prices only | Yes (by condition; PriceCharting includes graded) | Active | 💰 Optional licensed price source |
| Scraping Bulbapedia / official card database | Free, but fragile and against the spirit of the sites' terms | Very complete | No | — | ❌ Avoid |

### Recommendation

1. **TCGdex is the single source of truth, run as our own Docker container.** The `tcgdex/server:edge` image (~450 MB) contains the whole card database. On start-up it loads current prices *(verified)*:
   - **Cardmarket:** the public daily price guide from `downloads.s3.cardmarket.com`
   - **TCGplayer:** data from `tcgcsv.com`, a daily mirror of TCGplayer's API. This requires the `TCGCSV_USER_AGENT` environment variable; without it, TCGplayer prices are silently missing *(verified)*.

   Our jobs therefore send **no requests to `api.tcgdex.net`**, which removes the rate-limit concern entirely. The only outside downloads are the one image pull and one price fetch per run that the container makes itself.
2. **Mirror the data into our own PostgreSQL.** The website reads only our database, which gives fast search, independence from TCGdex uptime, and our own price history. This is also what TCGdex's FAQ asks bulk users to do: *"cache responses locally rather than fetching the same data repeatedly"*.
3. **Paid upgrade path:** Scrydex or JustTCG, only if the project needs graded prices, long price history, or **price data with clear redistribution rights** (section 8).

---

## 3. Architecture

```
 ┌───────────────────────────────┐   pulls at start-up:            ┌──────────────────────────┐
 │ TCGdex container (ephemeral)  │◀── Cardmarket price guide (S3)  │ assets.tcgdex.net        │
 │ tcgdex/server:edge  :3000     │◀── tcgcsv.com (TCGplayer data)  │ (card images, CDN)       │
 └──────────────┬────────────────┘                                 └────────────▲─────────────┘
                │ localhost HTTP (~6 ms/req)                                    │ <img> from browser
 ┌──────────────▼────────────────┐                                              │
 │ Ingestion job (Python)        │  GitHub Actions cron                         │
 │ catalog sync · price snapshot │                                              │
 └──────────────┬────────────────┘                                              │
                │ upserts                                                       │
 ┌──────────────▼────────────────┐        ┌──────────────┐                      │
 │ PostgreSQL ◀── FastAPI        │◀───────│  Next.js     │──────────────────────┘
 │            /cards /sets /search│        │  (frontend)  │
 └───────────────────────────────┘        └──────────────┘
```

- The **ingestion job** lives in the backend codebase (for example `backend/ingest/`) and shares the SQLAlchemy models with FastAPI.
- The **TCGdex container only runs during a job.** It is a `services:` container in the GitHub Actions workflow, so there is no server to maintain.
- **Images:**
  - **Store only the image URLs, not the files.** URLs are built as `{image}/{quality}.{ext}`, for example `https://assets.tcgdex.net/en/swsh/swsh3/136/low.webp`. Per TCGdex's guidance, use `webp`, `low` (245×337) in grids, and `high` (600×825) only on the detail page.
  - **Hotlinking is technically supported** *(verified)*: any `Referer` is accepted, the files send `Access-Control-Allow-Origin: *`, and they are cached for 1 year (`immutable`). Browsers therefore download each image only once.
  - **We do not copy the images into our own storage.** The card scans are © The Pokémon Company and are not covered by TCGdex's MIT license (section 8).
  - Render them with a plain `<img loading="lazy">` or `next/image` with `unoptimized`. That way the Next.js server keeps no copies. Show a placeholder if an image fails to load.

---

## 4. Database schema (PostgreSQL)

Design principles:
- **Use TCGdex IDs as natural keys** (`swsh3`, `swsh3-136`). They were observed to be identical across languages *(verified on samples)*, which makes upserts trivial. TCGdex does not document them as permanent, so the catalog sync must handle a renamed ID: the "missing" flag plus manual review (section 6) covers this.
- **Split language-neutral data from localized data.** HP, types, rarity and illustrator are shared; name, attack text and image URL vary per language.
- **Store rarely-queried nested structures (attacks, abilities, weaknesses) as `JSONB`.** Columns we filter on stay as real columns.
- **Store prices as an append-only time series, writing a row only when the price changed** (section 6).

> The SQL below has been run successfully on PostgreSQL 16, including `REFRESH MATERIALIZED VIEW CONCURRENTLY`.

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name search
CREATE EXTENSION IF NOT EXISTS unaccent;  -- "Pokemon" matches "Pokémon"

-- ── Catalog ────────────────────────────────────────────────
CREATE TABLE series (
    id            TEXT PRIMARY KEY,            -- 'swsh'
    name_en       TEXT,                        -- nullable: a series could exist in FR only
    name_fr       TEXT,
    logo_url      TEXT,
    release_order INT,                         -- for chronological sorting
    is_digital    BOOLEAN NOT NULL DEFAULT FALSE  -- TRUE for 'tcgp' (TCG Pocket), excluded from the site
);

CREATE TABLE sets (
    id                 TEXT PRIMARY KEY,       -- 'swsh3'
    series_id          TEXT NOT NULL REFERENCES series(id),
    release_date       DATE,                   -- from GET /sets/{id} (not in the /sets list)
    card_count_official INT,
    card_count_total    INT,
    symbol_url         TEXT,
    legal_standard     BOOLEAN,
    legal_expanded     BOOLEAN,
    missing_upstream   BOOLEAN NOT NULL DEFAULT FALSE,  -- no hard deletes (section 6)
    synced_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE set_localizations (
    set_id    TEXT REFERENCES sets(id) ON DELETE CASCADE,
    lang      TEXT NOT NULL,                   -- 'en', 'fr'
    name      TEXT NOT NULL,                   -- 'Darkness Ablaze' / 'Ténèbres Embrasées'
    logo_url  TEXT,
    PRIMARY KEY (set_id, lang)
);

CREATE TABLE cards (
    id               TEXT PRIMARY KEY,         -- 'swsh3-136' (may contain '?' / '!': 'exu-?')
    set_id           TEXT NOT NULL REFERENCES sets(id),
    local_id         TEXT NOT NULL,            -- '136', 'TG01', 'SV001' (not always numeric)
    category         TEXT NOT NULL,            -- 'Pokemon' | 'Trainer' | 'Energy'
    hp               INT,
    types            TEXT[],                   -- {'Colorless'}
    stage            TEXT,                     -- 'Basic', 'Stage1', ...
    evolve_from      TEXT,
    dex_ids          INT[],                    -- national Pokédex numbers
    rarity           TEXT,
    illustrator      TEXT,
    regulation_mark  TEXT,                     -- 'D', 'G', ...
    retreat          INT,
    weaknesses       JSONB,
    resistances      JSONB,
    trainer_type     TEXT,
    energy_type      TEXT,
    legal_standard   BOOLEAN,
    legal_expanded   BOOLEAN,
    tcgdex_updated_at TIMESTAMPTZ,             -- card.updated → change detection
    missing_upstream BOOLEAN NOT NULL DEFAULT FALSE,
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (set_id, local_id)
);

CREATE TABLE card_localizations (
    card_id     TEXT REFERENCES cards(id) ON DELETE CASCADE,
    lang        TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,                          -- flavor text
    attacks     JSONB,                         -- [{cost, name, effect, damage}]
    abilities   JSONB,
    effect      TEXT,                          -- Trainer/Energy rules text
    image_base  TEXT,                          -- 'https://assets.tcgdex.net/en/swsh/swsh3/136'
    PRIMARY KEY (card_id, lang)
);

-- Natural key (card_id, type): TCGdex's variantId is not documented as stable.
CREATE TABLE card_variants (
    card_id               TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    type                  TEXT NOT NULL,       -- 'normal' | 'reverse' | 'holo' | 'firstEdition' | 'wPromo'
    tcgdex_variant_id     TEXT,                -- informational only
    cardmarket_product_id INT,
    tcgplayer_product_id  INT,
    PRIMARY KEY (card_id, type)
);

-- ── Prices ─────────────────────────────────────────────────
-- TCGdex returns prices per card and marketplace, with sub-keys per finish:
--   TCGplayer: 'normal', 'holofoil', 'reverse-holofoil', '1st-edition-holofoil', ...
--   Cardmarket: base fields + '-holo' fields. Cardmarket's '-holo' means the *foil printing*
--   (reverse holo on modern sets), so it is stored as finish = 'foil', not 'holo'.
-- A row is written only when a value differs from the card's previous row (change-only).
CREATE TABLE price_snapshots (
    card_id      TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    source       TEXT NOT NULL,                -- 'cardmarket' | 'tcgplayer'
    finish       TEXT NOT NULL,                -- 'normal' | 'foil' | 'holofoil' | 'reverse-holofoil' | ...
    captured_on  DATE NOT NULL,
    currency     CHAR(3) NOT NULL,             -- 'EUR' | 'USD'
    market       NUMERIC(10,2),                -- TCGplayer marketPrice / Cardmarket trend
    low          NUMERIC(10,2),
    mid          NUMERIC(10,2),                -- TCGplayer only
    high         NUMERIC(10,2),                -- TCGplayer only
    avg7         NUMERIC(10,2),                -- Cardmarket only
    avg30        NUMERIC(10,2),                -- Cardmarket only
    source_updated_at TIMESTAMPTZ,             -- pricing.<source>.updated
    PRIMARY KEY (card_id, source, finish, captured_on)
);

-- Weekly roll-up for history older than 90 days (retention job, section 6)
CREATE TABLE price_weekly (
    card_id     TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    finish      TEXT NOT NULL,
    week_start  DATE NOT NULL,                 -- Monday
    currency    CHAR(3) NOT NULL,
    market_avg  NUMERIC(10,2),
    low_min     NUMERIC(10,2),
    PRIMARY KEY (card_id, source, finish, week_start)
);

-- Latest price per card/source/finish, for fast card pages
CREATE MATERIALIZED VIEW latest_prices AS
SELECT DISTINCT ON (card_id, source, finish) *
FROM price_snapshots
ORDER BY card_id, source, finish, captured_on DESC;

-- Required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_latest_prices_key ON latest_prices (card_id, source, finish);

-- ── Operations ─────────────────────────────────────────────
CREATE TABLE sync_runs (
    id            BIGSERIAL PRIMARY KEY,
    job           TEXT NOT NULL,               -- 'backfill' | 'daily_sync' | 'retention'
    tcgdex_image  TEXT,                        -- image digest used, for reproducibility
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'running',  -- running | success | failed | aborted
    items_seen    INT DEFAULT 0,
    items_changed INT DEFAULT 0,
    error         TEXT
);

-- Local corrections that survive re-syncs (use sparingly; fix upstream in TCGdex first)
CREATE TABLE card_overrides (
    card_id  TEXT REFERENCES cards(id) ON DELETE CASCADE,
    field    TEXT NOT NULL,
    value    JSONB NOT NULL,
    reason   TEXT,
    PRIMARY KEY (card_id, field)
);

-- ── Indexes ────────────────────────────────────────────────
CREATE INDEX idx_cards_set           ON cards (set_id);
CREATE INDEX idx_cards_types         ON cards USING GIN (types);
CREATE INDEX idx_cards_rarity        ON cards (rarity);
CREATE INDEX idx_cards_dex           ON cards USING GIN (dex_ids);
CREATE INDEX idx_loc_name_trgm       ON card_localizations USING GIN (name gin_trgm_ops);
CREATE INDEX idx_prices_date         ON price_snapshots (captured_on);  -- retention job
```

Migrations are managed with **Alembic**.

---

## 5. Ingestion: initial backfill

The backfill runs against the local container, for example `docker run -p 3000:3000 -e TCGCSV_USER_AGENT="TCG-exemple (+https://github.com/Sam-ssp/TCG-exemple)" tcgdex/server:edge`, with base URL `http://localhost:3000`.

- **Wait for readiness, not just the port.** The server answers HTTP before its prices are loaded. Poll a known card until `pricing.cardmarket` **and** `pricing.tcgplayer` are present, or watch the logs for `loaded cardmarket datas` / `loaded TCGPlayer datas`, before starting.
- **Responses are compressed:** use an HTTP client that decompresses automatically (`httpx` does).

The TCGdex v2 traversal order:

1. `GET /v2/{lang}/series`: upsert `series`, and set `is_digital = TRUE` for `tcgp`.
2. `GET /v2/{lang}/series/{id}`: list each series' sets.
3. `GET /v2/{lang}/sets/{id}`: upsert the set (with `releaseDate`) plus its card list.
4. `GET /v2/{lang}/cards/{id}`: full card details, `variants_detailed` and `pricing`. Upsert `cards`, `card_localizations` and `card_variants`, and write the first `price_snapshots` rows.

Runtime: about 21,300 English cards plus the French ones, at about 6 ms per local request *(verified)*. That is **a few minutes**, not hours.

Implementation notes:
- **Python with `httpx.AsyncClient`**, at moderate concurrency (the container defaults to one worker per CPU thread; `MAX_WORKERS=2` is enough).
- **Language passes:** the `en` pass writes the language-neutral columns. The `fr` pass writes localizations, **and also creates the set and card rows if they don't exist yet** (`ON CONFLICT DO NOTHING`), because of the 3 sets that exist only in French.
- **IDs can contain `?` and `!`** (`exu-?`). Store them exactly as returned, and URL-encode them when building request paths and site URLs.
- **Validate the payload shape** with Pydantic models before writing anything. The `edge` image follows TCGdex `master`, so a format change must abort the run, not corrupt the database.
- **Count check:** after each set, check that the number of cards listed equals `cardCount.total` *(verified to match on samples from Base to Mega Evolution)*, and log mismatches.
- Some cards have **no price** (older EX / full-art cards, regional exclusives, brand-new releases). Treat `pricing` as optional everywhere.

---

## 6. Keeping the data up to date

**One daily job** (GitHub Actions cron, around **21:30 UTC**):

1. **Start the latest image.** `docker pull tcgdex/server:edge` (new sets arrive through this image), start the container, and wait for prices to load. Record the image digest in `sync_runs`.
   - Why 21:30 UTC: TCGplayer data via TCGCSV was observed updated at ~20:05 UTC, and Cardmarket's guide updates once a day.
2. **Catalog sync.** Diff the set and card lists against the database.
   - **New** sets and cards: insert them.
   - **Changed** cards (`updated` newer than `tcgdex_updated_at`): upsert. This picks up errata, rotation (`legal_standard`) and new French translations.
   - Cards or sets **missing upstream**: flag them with `missing_upstream = TRUE`. **Never hard-delete** them.
3. **Price snapshot** for every physical card. Write a row only if any value differs from the latest stored row (change-only). Then run `REFRESH MATERIALIZED VIEW CONCURRENTLY latest_prices`.
4. **Guards.** Abort *before writing* if:
   - payload validation fails
   - the card count drops by more than 1%
   - more than 20% of cards lose their prices (a sign an upstream price download failed)

Whole run: about 10–15 minutes, mostly the image pull and price loading.

**Weekly job:** a retention step. Daily rows older than 90 days are rolled up into `price_weekly` and then deleted.

**Backups:**
- Use the managed database's own backups. Check the chosen plan's retention: free tiers have little or none.
- If needed, add a `pg_dump` to *private* storage (for example a private bucket).
- **Do not upload dumps as GitHub Actions artifacts:** this repo is **public** *(verified)*, and artifacts of public repos can be downloaded by any signed-in GitHub user. Today the data is all public anyway, but this matters once user accounts or collections exist.

### Scheduling (GitHub Actions)

- The `DATABASE_URL` is a repo **secret**, never committed. Connect through the database's **connection pooler** (Actions runners have changing IPs).
- **Known limits:**
  - scheduled runs can start late
  - jobs are capped at 6 hours (not an issue here)
  - **in public repos, scheduled workflows are disabled automatically after 60 days without repository activity**
- **Later:** move the job to the backend host's cron if needed.

### Monitoring and data quality

- Every run writes a row to `sync_runs`. `/admin/health` shows the last successful run per job. It must not expose secrets, and if it shows more than run dates and statuses, protect it.
- **Alerting needs an outside watcher.** A disabled or never-started workflow sends no failure email, and an endpoint can't alert by itself. Use a free dead-man's-switch service (e.g. healthchecks.io): the job pings it on success, and the service emails us if no ping arrives within 26 hours. GitHub's failure email covers runs that start and then fail.
- **Data errors:** contribute fixes upstream to `tcgdex/cards-database`. Use `card_overrides` only for urgent local fixes. The ingester applies overrides after each upsert.

### Storage budget

Each price row is roughly 170 bytes including its index. Prices are the only growing data:

| Scenario | Daily volume | Storage |
|---|---|---|
| Naive daily snapshot of everything (not used) | ~21,300 cards × ~3 source/finish rows ≈ **64,000 rows/day** | ~1 GB after 90 days: too big for free tiers (Supabase free = 500 MB) |
| **Change-only snapshots** (recommended) | Most of the catalog (vintage and bulk cards) is expected to change only occasionally. *Measure the real change rate in the first two weeks.* | Expected to fit comfortably |
| Fallback if the measured rate is too high | Snapshot daily only for sets released in the last 12 months, weekly for everything else | Fits the free tier |

---

## 7. Hosting options

| Environment | Option |
|---|---|
| Local dev | `docker compose` with `postgres:16` and `tcgdex/server:edge` |
| Production DB | **Supabase** or **Neon** (both managed Postgres, both work with SQLAlchemy and Alembic) |
| Images | Not hosted by us (sections 3 and 8) |

On free tiers, check the plan's rules for **inactivity pausing** and **backups** before choosing. Supabase free projects are paused after a period of inactivity; check whether direct database connections from the daily job count as activity.

---

## 8. Authorization: what we may store and show

*This is a practical assessment for a student project, not legal advice.*

| Data | Owner / license | May we store it? | May we show it publicly? | Conditions |
|---|---|---|---|---|
| Card **metadata compilation** from TCGdex (structure, IDs, set lists, variants) | TCGdex, **MIT License** | ✅ Yes | ✅ Yes | Keep the MIT notice ("Copyright (c) 2021 TCGdex") in `THIRD_PARTY_NOTICES.md` and on the site's credits page |
| Card **text, names, artwork, images** | © Nintendo / Creatures / GAME FREAK / The Pokémon Company. TCGdex's MIT license **cannot** grant rights TCGdex doesn't own. | ⚠️ Text: as part of the catalog. **Image files: no, store URLs only.** | ⚠️ **Tolerated, not authorized.** Pokémon's legal page grants nothing beyond *"personal, noncommercial home use"*. Card databases and fan sites operate under the company's tolerance. | Non-commercial only; no ads or sales; footer disclaimer: *"Pokémon and all related names and images are trademarks/© of Nintendo, Creatures, GAME FREAK and The Pokémon Company. This site is not affiliated with, endorsed or sponsored by them."*; remove content promptly on request |
| **Cardmarket prices** (public daily price guide, fetched by the TCGdex container) | Cardmarket (Sammelkartenmarkt GmbH, EU) | ⚠️ Cardmarket made the guide downloadable *"for all of our users"* but **states no usage terms**. As an EU database, it may also be covered by the EU database right (*sui generis*), which restricts extracting substantial parts. | ⚠️ Gray area: reasonable for a non-commercial demo | Attribute ("Prices: Cardmarket"), show the date, link to the product page, keep history limited, **never offer a bulk export or public price API** |
| **TCGplayer prices** (via tcgcsv.com, fetched by the TCGdex container) | TCGplayer (data); TCGCSV is a third-party mirror with no formal terms, which asks for an identifying User-Agent and polite rates | ⚠️ Same gray area; TCGplayer's own terms apply to its data | ⚠️ Same | Attribute ("Prices: TCGplayer"), set `TCGCSV_USER_AGENT` to identify us, **one download per day** (what the container does) |
| Deprecated pokemontcg.io data | Pokémon TCG API terms | Not used | — | — |

**Bottom line:**
- For a **non-commercial educational/demo site**, the plan is reasonable. The metadata is properly licensed (MIT). Images are shown the way every fan database shows them. Prices are used in a limited way, with attribution.
- For a **commercial product** it is **not** enough. That would need a licensed price feed, and card images would remain a risk that can't be removed: Pokémon IP is not licensable for a hobby project.
- Settle the price and image questions with the course or teacher before making the site publicly indexable.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| TCGdex project stops or the image changes format | Our DB mirror keeps the site working; Pydantic validation aborts bad runs; image digest recorded so a known-good one can be pinned; the source code is MIT and can be built ourselves |
| An upstream price download fails (Cardmarket S3 or TCGCSV) | Readiness check requires both sources; "more than 20% of prices lost" guard; prices are simply kept from the previous day |
| Bad upstream data overwrites good data | Validation, count guard, `missing_upstream` instead of deletes, backups |
| Price table exceeds free tier | Change-only snapshots, 90-day retention plus weekly roll-up, fallback tiering (section 6) |
| Images depend on assets.tcgdex.net uptime | Placeholder on error; browsers cache images for 1 year; no re-hosting without permission |
| Takedown request from a rights holder | Non-commercial scope, disclaimers, attribution; images and prices can be switched off by config without touching the catalog |
| Scheduled workflow silently disabled or never runs | Dead-man's-switch ping (healthchecks.io) alerts after 26 hours without a successful run |
| Free-tier DB paused or lost | Check the plan's pausing and backup rules; private `pg_dump` |

---

## 10. Next steps (proposed tickets)

1. **Scaffold backend:** FastAPI + SQLAlchemy + Alembic, plus a `docker compose` with `postgres:16` and `tcgdex/server:edge`.
2. **Initial migration** with the section 4 schema.
3. **Ingester:** backfill (EN, then FR, including FR-only sets) with readiness wait, Pydantic validation and count checks.
4. **Daily sync workflow** (GitHub Actions): pull the image, run the catalog sync and change-only price snapshot, apply the guards, ping healthchecks.io.
5. **Read API:** `GET /sets`, `GET /sets/{id}`, `GET /cards/{id}`, `GET /cards?q=&type=&rarity=&set=`.
6. **Weekly retention job**, plus `/admin/health`.
7. **Compliance:** `THIRD_PARTY_NOTICES.md`, footer disclaimer, price attribution and links, config switches for images and prices, and a check with the course about public indexing.

---

## Sources

- TCGdex: <https://tcgdex.dev>; FAQ (no key, no hard rate limit, "please be considerate", cache locally): <https://tcgdex.dev/faq>; image assets: <https://tcgdex.dev/assets>
- TCGdex cards database (MIT, `docker-compose.yml` using `tcgdex/server:edge`): <https://github.com/tcgdex/cards-database>
- Self-hosted server behaviour (price providers, 24-hour refresh, `TCGCSV_USER_AGENT`): observed by running `tcgdex/server:edge` (image built 2026-09-30) on 2026-10-01
- Cardmarket price guide download announcement: <https://news.cardmarket.com/en/Magic/were-making-the-price-guide-and-product-catalogue-available-for-download>
- TCGCSV FAQ: <https://tcgcsv.com/faq>
- Pokémon legal information: <https://www.pokemon.com/us/legal/>
- GitHub Actions scheduled workflows: <https://docs.github.com/actions/using-workflows/events-that-trigger-workflows#schedule>
- Pokémon TCG API deprecation notice: <https://pokemontcg.io>, <https://docs.pokemontcg.io>
- pokemon-tcg-data deprecation: <https://github.com/PokemonTCG/pokemon-tcg-data>
- Scrydex FAQ: <https://scrydex.com/faq>
- API comparisons: <https://www.scrapingbee.com/blog/pokemon-card-api/>, <https://cardgrader.ai/blog/tcgplayer-api-alternatives>
