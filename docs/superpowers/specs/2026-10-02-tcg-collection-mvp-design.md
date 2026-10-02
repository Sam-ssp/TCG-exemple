# TCG Collection MVP: design

Date: 2026-10-02. Deadline: 2026-10-08. Jira: KAN-5.
Source requirements: `AGENT.md`. Data details: `docs/PLAN.md`.

## 1. Goal and success criteria

A local web app to browse every physical Pokemon TCG card in French, manage a personal collection and lists, and drive the app through an AI chat.

It is judged by a course grader on three things:
1. It starts with one script and every feature works end to end.
2. It demos well (clean UI, smooth flows).
3. The code is clean, structured and tested.

## 2. Decisions

| Topic | Decision |
|---|---|
| Card language | French only (TCGdex `fr`), Pokemon TCG Pocket excluded |
| Interface language | French, including AI replies |
| Collection entry | Card + variant + quantity |
| Lists | Two kinds: `collection` (owned cards only) and `souhaits` (any card); card-level, no variant |
| Prices | None in the MVP |
| AI custom sort | The AI sets filters and sort on the explorer page, from a fixed set of sort fields |
| Architecture | REST API, server-side AI tool loop, explorer state in the URL, no streaming |
| Sign-in | Hardcoded `user` / `user`, database supports several users |

Out of scope: prices, other languages, real authentication, chat history persistence, streaming replies, hosting.

## 3. Structure

```
backend/                     FastAPI app, managed with uv
  app/
    main.py                  /api routes; serves the static frontend at /
    db.py                    connection, start-up (schema, catalog load, default user)
    schema.sql
    catalog.py               browse, groups, search, card detail
    collection.py            collection and list rules
    auth.py                  hardcoded sign-in, signed session cookie
    chat.py                  OpenRouter call and tool loop
    tools.py                 tool definitions -> catalog/collection functions
  scripts/fetch_catalog.py   developer script: TCGdex fr -> data/catalog.json.gz
  data/catalog.json.gz       committed catalog snapshot
  tests/
frontend/                    Next.js, static export (output: "export")
scripts/                     start/stop: .sh (Mac, Linux) and .ps1 (Windows)
Dockerfile                   stage 1 Node: next build; stage 2 Python + uv: backend + out/
```

- One container, one process: `uvicorn` serves `/api/*` and the static files at `/`. No Node at runtime.
- Database: `/app/data/tcg.db` on a named Docker volume. Created on first start; catalog loaded from the snapshot. Network is only needed for card images (`assets.tcgdex.net`) and OpenRouter.
- Start scripts build the image and run it with `.env` (`OPENROUTER_API_KEY`), port 8000 and the volume. Stop scripts stop and remove the container.
- `catalog.py` and `collection.py` know nothing about HTTP or AI. API routes, AI tools and tests call the same functions.

## 4. Data

### 4.1 Catalog snapshot

`fetch_catalog.py` (run manually with `uv run`) reads `api.tcgdex.net/v2/fr`: series, each set, each card's details. It skips the `tcgp` series, uses `httpx.AsyncClient` at about 5 concurrent requests, URL-encodes ids (they can contain `?` and `!`), and writes `catalog.json.gz` with a version string (the fetch date).

It also:
- builds the Pokemon list: for each Pokedex number, the shortest French card name among cards showing only that Pokemon;
- computes `local_number` and `rarity_rank` (section 4.2);
- prints a coverage report: set and card counts, cards with no image, cards with no rarity, sets whose card count differs from `cardCount.total`, rarities missing from the rank table.

Start-up: if the database file does not exist, run `schema.sql`. If `meta.catalog_version` differs from the snapshot's version, upsert all catalog tables (never delete). Insert user `user` (id 1) if missing. If the snapshot is missing or unreadable, stop with an error.

### 4.2 Schema (SQLite)

`PRAGMA foreign_keys = ON` on every connection; `journal_mode = WAL`.

```sql
CREATE TABLE IF NOT EXISTS series (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    logo_url      TEXT,
    release_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sets (
    id                  TEXT PRIMARY KEY,
    series_id           TEXT NOT NULL REFERENCES series(id),
    name                TEXT NOT NULL,
    release_date        TEXT,
    card_count_official INTEGER,
    card_count_total    INTEGER,
    logo_url            TEXT,
    symbol_url          TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    id           TEXT PRIMARY KEY,
    set_id       TEXT NOT NULL REFERENCES sets(id),
    local_id     TEXT NOT NULL,
    local_number INTEGER,              -- digits of local_id; NULL sorts last
    name         TEXT NOT NULL,
    search_name  TEXT NOT NULL,        -- lowercase, accents removed
    category     TEXT NOT NULL,        -- 'Pokemon' | 'Trainer' | 'Energy'
    rarity       TEXT,
    rarity_rank  INTEGER,              -- fixed order, Commune lowest
    illustrator  TEXT,
    hp           INTEGER,
    types        TEXT,                 -- JSON array
    stage        TEXT,
    image_base   TEXT,                 -- NULL when no image
    variants     TEXT NOT NULL,        -- JSON: {"normal":true,"reverse":false,"holo":true,"firstEdition":false}
    details      TEXT,                 -- JSON: attacks, abilities, weaknesses, effect, retreat
    UNIQUE (set_id, local_id)
);

CREATE TABLE IF NOT EXISTS card_pokemon (
    card_id TEXT NOT NULL REFERENCES cards(id),
    dex_id  INTEGER NOT NULL,
    PRIMARY KEY (card_id, dex_id)
);

CREATE TABLE IF NOT EXISTS pokemon (
    dex_id INTEGER PRIMARY KEY,
    name   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    username   TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_items (
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    card_id  TEXT NOT NULL REFERENCES cards(id),
    variant  TEXT NOT NULL,            -- 'normal' | 'reverse' | 'holo' | 'firstEdition'
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, card_id, variant)
);

CREATE TABLE IF NOT EXISTS lists (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('collection', 'souhaits')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS list_items (
    list_id  INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    card_id  TEXT NOT NULL REFERENCES cards(id),
    added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (list_id, card_id)
);

CREATE INDEX IF NOT EXISTS idx_cards_set         ON cards (set_id);
CREATE INDEX IF NOT EXISTS idx_cards_rarity      ON cards (rarity);
CREATE INDEX IF NOT EXISTS idx_cards_illustrator ON cards (illustrator);
CREATE INDEX IF NOT EXISTS idx_cards_search_name ON cards (search_name);
CREATE INDEX IF NOT EXISTS idx_card_pokemon_dex  ON card_pokemon (dex_id);
```

No migration tool: if the schema changes during the MVP, delete the local database; the catalog reloads itself.

### 4.3 Rules (in `collection.py`)

- A variant must be `true` in the card's `variants`.
- Setting a quantity to 0 deletes the row.
- A `collection` list accepts only cards the user owns (any variant).
- When a card's total quantity for a user reaches 0, it is removed from all of that user's `collection` lists.
- `souhaits` lists accept any card; owning it later changes nothing.

### 4.4 Sorting and search

Sort fields (shared by API and AI): `nom`, `pokedex`, `pv`, `rarete` (by `rarity_rank`), `illustrateur`, `date_sortie`, `numero` (by `local_number`, then `local_id`). Each `asc` or `desc`; several can be combined, e.g. `tri=rarete:desc,pv:desc`. Ties always end with `date_sortie`, then `numero`. NULLs sort last.

Search: `search_name LIKE '%term%'` with the term normalized the same way.

## 5. API

JSON. Every route except `POST /api/connexion` requires the session cookie (401 otherwise). Errors return 4xx with a French `detail`.

| Route | Purpose |
|---|---|
| `POST /api/connexion` `{utilisateur, mot_de_passe}` | Sign in, sets a signed cookie |
| `POST /api/deconnexion` | Sign out |
| `GET /api/moi` | Current user |
| `GET /api/groupes?par=set\|pokemon\|illustrateur\|rarete` | Groups with card counts; sets grouped by series, release order |
| `GET /api/cartes?set=&pokemon=&illustrateur=&rarete=&type=&q=&tri=&page=` | Filtered, sorted cards, 60 per page, with total |
| `GET /api/cartes/{id}` | Card detail + my quantity per variant + my lists containing it |
| `GET /api/collection?tri=&page=` | My collection cards with quantities |
| `PUT /api/collection/{card_id}/{variant}` `{quantite}` | Set quantity; 0 removes |
| `GET /api/listes`, `POST /api/listes` `{nom, type}` | My lists; create |
| `GET /api/listes/{id}`, `PATCH` `{nom}`, `DELETE` | View with cards, rename, delete |
| `POST /api/listes/{id}/cartes/{card_id}`, `DELETE` same | Add or remove a card |
| `POST /api/chat` `{messages, page}` | AI chat; returns `{reponse, actions}` |

## 6. Frontend

Static Next.js export, French, colors from `AGENT.md` (grey `#F3F3ED`, dark grey `#515151`, blue `#5D5C8E`, red `#E78A78`, green `#70BC94`, yellow `#F1D3AC`).

| Page | Content |
|---|---|
| `/connexion` | Sign-in form |
| `/explorer` | Tabs Par extension / Par Pokemon / Par illustrateur / Par rareté; group list; card grid with sort menu and name search. All state in the URL: `?par=&valeur=&q=&tri=&page=` |
| `/carte?id=` | Large image, card text, quantity control per available variant, "Ajouter à une liste" menu |
| `/collection` | My cards in the same grid, with quantities and sort |
| `/listes`, `/listes/voir?id=` | My lists (kind shown), create/rename/delete; a list's cards |

Every signed-in page has a header with the tabs and a collapsible chat panel on the right. A 401 from any call redirects to `/connexion`. Grids use `{image_base}/low.webp` with `loading="lazy"`; the card page uses `high.webp`; a placeholder is shown when there is no image or loading fails. Failed requests show a short message in the page. Footer: the Pokemon trademark disclaimer and TCGdex credit.

## 7. AI chat

1. The panel sends the last 20 messages and the current page URL to `POST /api/chat`. History lives only in the browser.
2. `chat.py` calls OpenRouter (`openai/gpt-oss-120b`, key from `OPENROUTER_API_KEY`) with a short French system prompt and the tools.
3. While the model returns tool calls, the backend runs them for the signed-in user and sends results back, at most 5 rounds, then returns `{reponse, actions}`.

| Tool | Does |
|---|---|
| `chercher_cartes(nom, set, pokemon, illustrateur, rarete, type, tri, limite)` | Up to 20 short results (id, name, set, number) |
| `lister_groupes(par, filtre)` | Resolve a set, Pokemon, illustrator or rarity name to its value |
| `ajouter_collection(card_id, variante, quantite)` | Add copies |
| `retirer_collection(card_id, variante, quantite)` | Remove copies |
| `creer_liste(nom, type)` | Create a list |
| `ajouter_a_liste(liste, card_ids)` | Add cards to a list found by name |
| `afficher_navigation(par, valeur, filtres, tri)` | No query; returns a `naviguer` action with the `/explorer` URL |

- Arguments are validated with Pydantic against the same allowed fields as the API. A validation or rule error is returned to the model as the tool result, so it can correct itself.
- Actions: `{"type": "naviguer", "url": "..."}` (the frontend navigates) and `{"type": "rafraichir", "cible": "collection" | "listes"}` (the frontend refetches).
- The prompt tells the model to search before acting and, when several cards match, to ask or show them with `afficher_navigation` instead of guessing.
- If OpenRouter fails or takes more than 30 s, the reply is "Le service IA est indisponible, réessayez." The rest of the app is unaffected.

## 8. Testing

- Backend, pytest, on a sample catalog fixture (about 3 sets, 30 cards) in a temporary SQLite file:
  - sorting (including `numero` and `rarete`), filters, search with accents
  - collection quantities and the variant check
  - list rules, including automatic removal from `collection` lists
  - sign-in and 401 on protected routes
  - each tool with fixed arguments
  - the chat loop with a fake OpenRouter client (no network, no key)
- Frontend, Vitest + Testing Library: explorer reads and writes its state in the URL; chat panel applies `naviguer` and `rafraichir`.
- Manual check before 2026-10-08: start script on a clean machine, then all five features, including AI commands.

## 9. Licensing

- TCGdex data is MIT: its notice goes in `THIRD_PARTY_NOTICES.md`.
- Card names, text and images belong to Nintendo / Creatures / GAME FREAK / The Pokemon Company: images are shown by URL only, never copied, and the footer carries a non-affiliation disclaimer.

## 10. Order of work

| Day | Work |
|---|---|
| 1 (Oct 3) | Fetch script and French snapshot; schema and start-up; catalog functions with tests |
| 2 (Oct 4) | Collection and list functions; sign-in; API routes with tests |
| 3 (Oct 5) | Frontend: sign-in, explorer, card page |
| 4 (Oct 6) | Frontend: collection, lists; Dockerfile; start/stop scripts |
| 5 (Oct 7) | AI chat: loop, tools, panel, tests |
| 6 (Oct 8) | Buffer: fixes, README, notices, disclaimer, demo rehearsal |
