# DATABASE_Plan: Pokémon TCG card database

> Jira: **KAN-5**. Plan for storing every physical Pokémon TCG card, from Base Set (1999) to the latest expansion, choosing data sources, and keeping the data up to date.
>
> Stack: Next.js (frontend) → FastAPI (Python backend) → PostgreSQL.
> Research date: 2026-10-01.

---

## 1. Scope

| In scope | Out of scope (for now) |
|---|---|
| Every physical TCG set: Base, Gym, Neo, e-Card, EX, DP, Platinum, HGSS, BW, XY, SM, SWSH, SV, Mega Evolution, promos, trainer kits, McDonald's, etc. | **Pokémon TCG Pocket** (a digital game, listed as a separate series in TCGdex: filter it out) |
| Card metadata: name, HP, types, attacks, abilities, rarity, illustrator, regulation mark, legality, variants | Japanese-only/Asian sets (TCGdex covers them separately in `data-asia`, so they can be added later) |
| Card images (small + high resolution), set logos and symbols | Graded-card prices (PSA/BGS/CGC) |
| Market prices (Cardmarket EUR, TCGplayer USD) and price history | Deck lists, tournament results |
| Languages: **English** first, **French** second | Other languages (TCGdex supports 10+; the schema already allows them) |

Approximate size measured on the live TCGdex API: **220 English sets / ~23,800 English cards** (including Pocket), and **202 French sets**.

---

## 2. Data source evaluation

| Source | Cost / access | Coverage | Prices | Status (Oct 2026) | Verdict |
|---|---|---|---|---|---|
| **[TCGdex](https://tcgdex.dev)** (`api.tcgdex.net/v2`) | Free, no API key, open source (MIT) | All series from Base to Mega Evolution, 10+ languages | **Yes**: Cardmarket (EUR) + TCGplayer (USD), per variant, refreshed daily | Active, frequent commits | ✅ **Primary source** |
| [tcgdex/cards-database](https://github.com/tcgdex/cards-database) (GitHub) | Free, MIT | Same data as the API, as source files | No (prices are added at API level) | Active; ships a `docker-compose.yml` to self-host the API | ✅ **Catalog source** (self-hosted, so no load on the public API) |
| [pokemontcg.io](https://pokemontcg.io) (Pokémon TCG API v2) | Free, but new sign-ups are closed | English only | TCGplayer/Cardmarket snapshots | **Deprecated, goes offline 2027-03-01** | ❌ Don't build on it |
| [PokemonTCG/pokemon-tcg-data](https://github.com/PokemonTCG/pokemon-tcg-data) | Free JSON files | English only | No | **Deprecated**: will no longer receive new sets | ⚠️ One-off cross-check only |
| [Scrydex](https://scrydex.com) (successor to pokemontcg.io) | Paid (plans reported from ~$29/month; check current pricing) | Pokémon + other TCGs | Yes, plus price history, graded prices, population reports | Active | 💰 Upgrade path if we need graded or historical prices |
| TCGplayer API / Cardmarket API | Restricted: TCGplayer is no longer issuing new developer keys; Cardmarket API access is for approved sellers | Prices only | Yes (first-hand) | Restricted | ❌ Not available to us; TCGdex already relays both |
| JustTCG, PriceCharting | Free tier / paid | Prices only | Yes (by condition; PriceCharting includes graded) | Active | 💰 Optional extra price source later |
| Scraping Bulbapedia / official card database | Free, but fragile and against the spirit of the sites' terms | Very complete | No | — | ❌ Avoid |

### Recommendation

1. **TCGdex is the single source of truth for the catalog and prices.** It is free, open source, multilingual (French included) and current: it already has `me05 Pitch Black` and `30th Celebration`. Each card also embeds daily Cardmarket and TCGplayer prices *per variant* (normal / reverse / holo), along with their product IDs.
2. **Mirror TCGdex into our own PostgreSQL** rather than calling it from the browser at runtime. That gives us fast search, independence from TCGdex uptime and our own price history. TCGdex's FAQ asks exactly this of bulk users: *"cache responses locally rather than fetching the same data repeatedly"*.
3. **Load the catalog from a self-hosted TCGdex, not the public API.** The ingester runs the `cards-database` repo's Docker image (or a local clone of it) and reads card data from `localhost`. The full backfill and the weekly sync then put **zero load** on `api.tcgdex.net`. The public API is used only for what the repo does not contain: **daily prices** (see section 6 for how we keep that volume low). The ingester only needs a configurable base URL.
4. **Paid upgrade path:** Scrydex (or JustTCG), only if the project needs graded prices, long price history, or **price data with clear redistribution rights** (see section 8).

---

## 3. Architecture

```
                   ┌──────────────────────────┐
                   │  TCGdex self-hosted      │  catalog (Docker, from cards-database)
                   │  api.tcgdex.net          │  prices only (throttled, cached)
                   └────────────┬─────────────┘
                                │ HTTP
                   ┌────────────▼─────────────┐
                   │  Ingestion worker (Py)   │  scheduled jobs (cron / GitHub Actions)
                   │  backfill · sync · prices│
                   └────────────┬─────────────┘
                                │ upserts
┌──────────────┐   ┌────────────▼─────────────┐
│  Next.js     │──▶│  FastAPI  ──▶ PostgreSQL │
│  (frontend)  │   │  /cards /sets /search    │
└──────────────┘   └──────────────────────────┘
        │
        └──▶ card images: loaded by the browser from assets.tcgdex.net
```

- The **ingestion worker** lives in the backend codebase (for example `backend/ingest/`) and shares the SQLAlchemy models with FastAPI.
- The **frontend never talks to TCGdex directly.** It only calls our FastAPI.
- **Images:**
  - **Store only the image URLs, not the image files.** URLs are built as `{image}/{quality}.{ext}`, for example `https://assets.tcgdex.net/en/swsh/swsh3/136/low.webp`. Per TCGdex's guidance, use `webp`, `low` (245×337) in grids, and `high` (600×825) only on the card detail page.
  - **We do not copy the images into our own storage.** The card scans are © The Pokémon Company and are not covered by TCGdex's MIT license (section 8). Re-hosting them would mean redistributing copyrighted images ourselves. Copying them to a CDN is a later option *only* if the project gets explicit permission or switches to a licensed source.
  - Render them with `next/image` and `unoptimized`, or a plain `<img loading="lazy">`. This avoids keeping server-side copies, and lazy loading keeps the bandwidth we pull from TCGdex low.

---

## 4. Database schema (PostgreSQL)

Design principles:
- **Use TCGdex IDs as natural keys** (`swsh3`, `swsh3-136`). They are stable and the same across languages, which makes upserts trivial.
- **Split language-neutral data from localized data.** HP, types, rarity and illustrator are shared; name, attack text and image URL vary per language.
- **Store rarely-queried nested structures (attacks, abilities, weaknesses) as `JSONB`.** Columns we filter on (types, rarity, HP, regulation mark, legality) stay as real columns.
- **Store prices as an append-only time series**, separate from the catalog.

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name search
CREATE EXTENSION IF NOT EXISTS unaccent;  -- "Pokemon" matches "Pokémon"

-- ── Catalog ────────────────────────────────────────────────
CREATE TABLE series (
    id            TEXT PRIMARY KEY,            -- 'swsh'
    name_en       TEXT NOT NULL,
    name_fr       TEXT,
    logo_url      TEXT,
    release_order INT,                         -- for chronological sorting
    is_digital    BOOLEAN NOT NULL DEFAULT FALSE  -- TRUE for TCG Pocket (excluded from the site)
);

CREATE TABLE sets (
    id                 TEXT PRIMARY KEY,       -- 'swsh3'
    series_id          TEXT NOT NULL REFERENCES series(id),
    release_date       DATE,
    card_count_official INT,
    card_count_total    INT,
    symbol_url         TEXT,
    legal_standard     BOOLEAN,
    legal_expanded     BOOLEAN,
    tcgdex_updated_at  TIMESTAMPTZ,
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
    id               TEXT PRIMARY KEY,         -- 'swsh3-136'
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
    trainer_type     TEXT,                     -- for Trainer cards
    energy_type      TEXT,                     -- for Energy cards
    legal_standard   BOOLEAN,
    legal_expanded   BOOLEAN,
    tcgdex_updated_at TIMESTAMPTZ,             -- card.updated from TCGdex → change detection
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

-- Natural key (card_id, type): TCGdex's variantId is not documented as stable, so we don't key on it.
CREATE TABLE card_variants (
    card_id               TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    type                  TEXT NOT NULL,       -- 'normal' | 'reverse' | 'holo' | 'firstEdition' | 'wPromo'
    tcgdex_variant_id     TEXT,                -- informational only
    cardmarket_product_id INT,
    tcgplayer_product_id  INT,
    PRIMARY KEY (card_id, type)
);

-- ── Prices (time series) ───────────────────────────────────
-- TCGdex returns prices per *card and marketplace*, with sub-keys per finish
-- (TCGplayer: 'normal', 'reverse-holofoil', 'holofoil', ...; Cardmarket: base vs '-holo' fields),
-- so prices are keyed by card + source + finish rather than by variant row.
CREATE TABLE price_snapshots (
    card_id      TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    source       TEXT NOT NULL,                -- 'cardmarket' | 'tcgplayer'
    finish       TEXT NOT NULL,                -- 'normal' | 'holo' | 'reverse-holofoil' | ...
    captured_on  DATE NOT NULL,                -- one row per card/source/finish/day
    currency     CHAR(3) NOT NULL,             -- 'EUR' | 'USD'
    market       NUMERIC(10,2),                -- TCGplayer marketPrice / Cardmarket trend
    low          NUMERIC(10,2),
    mid          NUMERIC(10,2),
    high         NUMERIC(10,2),
    avg7         NUMERIC(10,2),
    avg30        NUMERIC(10,2),
    -- No raw JSONB here: at ~18M rows/year it would multiply storage. Keep the latest raw payload on `cards` if needed.
    PRIMARY KEY (card_id, source, finish, captured_on)
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
    job           TEXT NOT NULL,               -- 'backfill' | 'catalog_sync' | 'prices'
    started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at   TIMESTAMPTZ,
    status        TEXT NOT NULL DEFAULT 'running',  -- running | success | failed
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
CREATE INDEX idx_prices_date         ON price_snapshots (captured_on);  -- retention/roll-up job
```

Migrations are managed with **Alembic**, the standard tool alongside SQLAlchemy and FastAPI.

---

## 5. Ingestion: initial backfill

**Run against the self-hosted TCGdex** (`docker compose up` in a clone of `tcgdex/cards-database`, base URL `http://localhost:3000`), not the public API. That removes about 48,000 requests (24,000 English cards + about the same in French) from `api.tcgdex.net`. Because the server is local, it can run as fast as Postgres accepts writes.

The TCGdex v2 traversal order:

1. `GET /v2/{lang}/series`: upsert `series`, and flag `Pokémon TCG Pocket` as `is_digital = TRUE`.
2. `GET /v2/{lang}/series/{id}`: list each series' sets with release dates.
3. `GET /v2/{lang}/sets/{id}`: upsert the set plus its card briefs.
4. `GET /v2/{lang}/cards/{id}`: full card details and `variants_detailed`. Upsert `cards`, `card_localizations` and `card_variants`.

The job can be resumed, because every write is an idempotent upsert.

Implementation notes:
- **Python with `httpx.AsyncClient`** (or the official TCGdex Python SDK), using one client with connection reuse.
- **Throttling:** wrap calls in an `asyncio.Semaphore`, and when the job targets the *public* API, also apply a rate cap of **≤ 2 requests/second**. On 429/5xx, retry with exponential backoff plus jitter, and honour `Retry-After`.
- **Identify ourselves:** send a `User-Agent: TCG-exemple/0.1 (+https://github.com/Sam-ssp/TCG-exemple)` header so TCGdex can contact us instead of blocking us.
- **IDs are not always URL-safe** (`exu-?`, `exu-!` for Unown cards). Use the IDs exactly as TCGdex returns them, and URL-encode only when building request paths.
- Language-neutral columns come from the `en` pass. The `fr` pass only writes `set_localizations` and `card_localizations`.
- Skip series where `is_digital = TRUE`.
- **Validation:** after each set, check that the number of stored cards equals `card_count_total`, and log any mismatch in `sync_runs.error`.
- Some cards have **no price** (older EX / full-art cards, regional exclusives, very recent releases). Treat `pricing` as optional everywhere.

---

## 6. Keeping the data up to date

| Job | Frequency | What it does |
|---|---|---|
| **Price refresh** (public API) | Daily, around 11:00 UTC (TCGdex prices were observed updating around 09:50 UTC) | Uses a **tiered** schedule instead of re-fetching all 24,000 cards every day (see below). For each card fetched, append one `price_snapshots` row per source/finish for today (`ON CONFLICT DO NOTHING`). Then run `REFRESH MATERIALIZED VIEW CONCURRENTLY latest_prices`. |
| **New set detection** | Daily | `git pull` the `cards-database` repo, rebuild the self-hosted container, and diff its `/v2/en/sets` against the `sets` table. Any new set ID triggers a backfill of that set (all languages). Sets released in the last 30 days are re-synced fully every day, because TCGdex adds their cards over a few days around release. |
| **Catalog sync** (errata, legality, new translations) | Weekly | Against the self-hosted instance: upsert only the cards whose `updated` timestamp is newer than `tcgdex_updated_at`. This picks up rotation changes (`legal_standard`), fixed typos, and new French translations. |
| **Backups** | Daily | Managed-database snapshots, or a `pg_dump` of the catalog plus prices. |

**Tiered price refresh.** This keeps public API usage at about 5,000 requests/day, at ≤ 2 requests/second (about 45 minutes), instead of about 24,000:

| Tier | Cards | Refresh |
|---|---|---|
| Hot | Sets released in the last 12 months, plus any card viewed on the site in the last 7 days | Daily |
| Cold | Everything else (vintage cards move slowly) | Weekly, spread over the week (about 1/7 of the catalog per day) |
| On demand | A card page whose latest price is more than 24 hours old | Queues a background refresh. The page shows the stored price with its date and never waits on TCGdex. |

Send `If-None-Match` with the stored `ETag` on every call, so unchanged responses come back as `304` and cost almost nothing.

**Courtesy:** before the first production run, post in the TCGdex Discord to say what volume we plan to send and ask whether they would prefer a different approach. There is no published rate limit, only *"please be considerate"*.

### Scheduling

- **Start with GitHub Actions `schedule:` cron workflows** that run `python -m ingest prices` and similar commands against the production `DATABASE_URL`, stored as a repo **secret** and never committed. They are free, need no extra server, and keep logs per run. The self-hosted TCGdex for catalog jobs runs as a workflow `services:` container.
- **Known Actions limits:**
  - scheduled runs can start several minutes late
  - jobs are capped at 6 hours
  - **scheduled workflows are disabled automatically after 60 days without repository activity**, so the health check must alert on that case too
  - connect through the database's **connection pooler** (for example Supabase's pooler URL), since Actions runners have changing IPs
- **Later:** move the jobs to the backend host (an APScheduler/cron container or a hosting platform's cron) if the runs exceed Actions limits.

### Monitoring and data quality

- Every job writes a row to `sync_runs`. A small `/admin/health` FastAPI endpoint exposes the last successful run per job.
- **Alert** (GitHub Actions failure email is enough at first) when:
  - a job fails
  - prices have not been updated for more than 48 hours
  - the card count drops by more than 1% (a protection against a bad upstream payload wiping data)
- **Never hard-delete cards during a sync.** Mark them as missing and review manually.
- **Data errors:** contribute fixes upstream to `tcgdex/cards-database`, which benefits everyone and survives re-syncs. Use `card_overrides` only for urgent local fixes.

### Price history retention

Prices are the only growing table.

- **Size estimate:** with tiered refresh, about 8,000 cards are priced per day. At an average of about 3 source/finish rows each, that is roughly 25,000 rows per day, or about 9 million rows per year (around 1 GB with indexes, without raw JSON).
- **Retention policy:**
  - Keep **daily** rows for 90 days.
  - Roll older rows up to **weekly** averages in a separate table, which cuts storage by about 7×.

This keeps the database within free and hobby tiers (for example Supabase free tier = 500 MB).

---

## 7. Hosting options

| Environment | Option |
|---|---|
| Local dev | `docker compose` with `postgres:16` plus the self-hosted TCGdex container |
| Production DB | **Supabase** (managed Postgres) or **Neon** (serverless Postgres, branching). Either works with SQLAlchemy and Alembic. |
| Images | Not hosted by us (see sections 3 and 8) |

---

## 8. Authorization: what we may store and show

Each kind of data has a different owner, so each is assessed separately:

| Data | Owner / license | May we store it? | May we show it publicly? | Conditions |
|---|---|---|---|---|
| Card **metadata** from the TCGdex repo (structure, IDs, set lists, our compilation) | TCGdex, **MIT License** | ✅ Yes | ✅ Yes | Keep the MIT copyright notice ("Copyright (c) 2021 TCGdex") with the data: add it to a `THIRD_PARTY_NOTICES.md` in the repo and to the site's credits page |
| Card **text, names, artwork, images** | © Nintendo / Creatures / GAME FREAK / The Pokémon Company. The MIT license **cannot** grant rights TCGdex doesn't own. | ⚠️ Text: yes, as part of the catalog. **Image files: no, store only URLs.** | ⚠️ **Tolerated, not authorized.** Pokémon's legal page grants no rights beyond *"personal, noncommercial home use"*. Card databases and fan sites exist under the company's tolerance, not under a license. | Non-commercial only; no ads or sales; footer disclaimer: *"Pokémon and all related names and images are trademarks/© of Nintendo, Creatures, GAME FREAK and The Pokémon Company. This site is not affiliated with, endorsed or sponsored by them."*; remove content promptly if asked |
| **Prices** (Cardmarket, TCGplayer) relayed by TCGdex | Originally the marketplaces'. The prices are **not** in the MIT repo and TCGdex publishes **no license** for them. | ⚠️ Gray area. Short-term caching is consistent with how TCGdex expects the API to be used; building a large long-term history goes further than that. | ⚠️ Gray area. Fine for a non-commercial, educational demo with attribution. | Always show the source ("Price: Cardmarket via TCGdex") and its date, link to the marketplace product page, keep history limited (90-day daily + weekly roll-ups), **never offer a bulk price export or public price API**. For any commercial use, switch to a licensed price source (Scrydex / JustTCG) and read its terms first |
| Deprecated pokemontcg.io data | Pokémon TCG API terms | Not used | — | — |

**Bottom line:** the plan is legitimate **for this project as a non-commercial educational/demo site**. It would **not** be enough for a commercial product. That would need a licensed price feed, and Pokémon IP cannot be licensed for a hobby project, so card images would remain the main legal risk.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| TCGdex API becomes unavailable or changes format | Our own DB mirror (the site keeps working); the catalog already comes from a self-hosted TCGdex; ingester base URL is configurable; schema versioned via Alembic |
| TCGdex asks us to reduce traffic or blocks us | Identifying `User-Agent`, ≤ 2 req/s, tiered refresh, ETags, a heads-up on Discord; fall back to weekly-only prices |
| Bad upstream data overwrites good data | Count checks, no hard deletes, daily backups |
| New set appears with incomplete data | Daily re-sync of sets released in the last 30 days |
| Price table growth exceeds free tier | Tiered refresh plus retention and roll-up policy (section 6) |
| Images depend on assets.tcgdex.net uptime | Lazy loading; a placeholder image on error. Re-hosting is not an option without permission (section 8). |
| Takedown request from a rights holder (Pokémon, a marketplace) | Non-commercial scope, disclaimers, attribution; images and prices can be switched off by config without touching the catalog |
| GitHub Actions schedules silently disabled after 60 days of inactivity | `/admin/health` alert on stale `sync_runs` |

---

## 10. Next steps (proposed tickets)

1. **Scaffold backend:** FastAPI + SQLAlchemy + Alembic, plus a `docker compose` with Postgres and the self-hosted TCGdex.
2. **Initial migration** with the section 4 schema.
3. **Ingester:** backfill command (EN, then FR) against the self-hosted TCGdex, with validation.
4. **Tiered price job and new-set detection** as GitHub Actions cron workflows (rate cap, ETag, User-Agent).
5. **Read API:** `GET /sets`, `GET /sets/{id}`, `GET /cards/{id}`, `GET /cards?q=&type=&rarity=&set=`.
6. **Weekly catalog sync job**, plus `/admin/health`, plus the price retention/roll-up job.
7. **Compliance:** `THIRD_PARTY_NOTICES.md` (TCGdex MIT notice), the site footer disclaimer, price attribution and links, and config switches to disable images and prices.

---

## Sources

- TCGdex: <https://tcgdex.dev>, API <https://api.tcgdex.net/v2/en/sets> (queried 2026-10-01)
- TCGdex FAQ (no API key, no hard rate limit, "please be considerate", cache locally): <https://tcgdex.dev/faq>
- TCGdex image assets guidance: <https://tcgdex.dev/assets>
- TCGdex cards database (MIT, Docker self-host): <https://github.com/tcgdex/cards-database>
- Pokémon legal information: <https://www.pokemon.com/us/legal/>
- GitHub Actions scheduled workflows (60-day inactivity disable): <https://docs.github.com/actions/using-workflows/events-that-trigger-workflows#schedule>
- Pokémon TCG API deprecation notice: <https://pokemontcg.io>, <https://docs.pokemontcg.io>
- pokemon-tcg-data deprecation: <https://github.com/PokemonTCG/pokemon-tcg-data>
- Scrydex FAQ: <https://scrydex.com/faq>
- API comparisons: <https://www.scrapingbee.com/blog/pokemon-card-api/>, <https://cardgrader.ai/blog/tcgplayer-api-alternatives>
