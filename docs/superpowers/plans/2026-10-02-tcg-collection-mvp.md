# TCG Collection MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local, French-language Pokemon TCG collection web app: browse every physical card by set, Pokemon, illustrator and rarity, manage a collection and lists, and drive it through an AI chat, all in one Docker container.

**Architecture:** A FastAPI backend owns a SQLite database loaded from a committed TCGdex catalog snapshot. Pure Python modules (`catalog.py`, `collection.py`) hold all data logic and are called by both the REST routes and the AI tools. A Next.js static export is served by FastAPI at `/`. The explorer keeps its state in the URL, so the AI drives it by returning a `naviguer` action.

**Tech Stack:** Python 3.14, uv, FastAPI 0.142, Pydantic 2.13, httpx 0.28, openai SDK 3.x (pointed at OpenRouter), pytest 9; Next.js 16 (static export), React 19, TypeScript, Vitest 5 + Testing Library; SQLite; Docker.

**Spec:** `docs/superpowers/specs/2026-10-02-tcg-collection-mvp-design.md`

## Global Constraints

- Card data: TCGdex French catalog only (`https://api.tcgdex.net/v2/fr`), series `tcgp` (Pokemon TCG Pocket) excluded.
- All user-facing text in French, with correct accents. No emojis anywhere (code, UI, docs, commits).
- Colors: grey `#F3F3ED`, dark grey `#515151`, blue `#5D5C8E`, red `#E78A78`, green `#70BC94`, yellow `#F1D3AC`.
- Sign-in hardcoded to `user` / `user`; every user-owned row carries `user_id`.
- AI model `openai/gpt-oss-120b` via OpenRouter, key `OPENROUTER_API_KEY` from `.env` at the project root.
- Sort fields, exactly: `nom`, `pokedex`, `pv`, `rarete`, `illustrateur`, `date_sortie`, `numero`; each `asc` or `desc`; comma-combined.
- 60 cards per page. Chat: last 20 messages, at most 5 tool rounds, 30 s timeout.
- No prices, no other languages, no migrations tool, no streaming.
- Keep it simple: no extra features, no defensive layers beyond what this plan specifies. Minimal README.
- Use the latest library versions as of 2026-10-02.

Deviations from the spec, decided while checking the live TCGdex data on 2026-10-02:
- `cards.category` stores TCGdex's French values: `Pokémon`, `Dresseur`, `Énergie`.
- Variants are `normal`, `reverse`, `holo`, `firstEdition` and `wPromo` (TCGdex has five).
- The database lives at `/data/tcg.db` in the container (volume `/data`), so the volume does not hide `/app/data/catalog.json.gz`.
- The test catalog fixture has 10 cards, chosen to cover every sort and filter edge case.

## Review Focus

1. Search text containing `%`, `_`, apostrophes or accents (`dracaufeu%`, `énergie`) must match literally and accent-insensitively, never act as a wildcard. Test: Task 4, `test_search_is_literal_and_accent_insensitive`.
2. Card ids containing `?` (`swsh4-?`, real case `exu-?`) must load through the API and links. Test: Task 6, `test_card_with_question_mark_id`; Task 9 encodes ids with `encodeURIComponent`.
3. Quantities: negative, zero, or removing more copies than owned must give a 400 or floor at zero, and clean collection lists. Tests: Task 5, `test_set_quantity_rejects_bad_values`, `test_remove_copies_floors_at_zero_and_cleans_lists`.
4. The AI sends an unknown tool, malformed JSON arguments or a non-existent card: the chat must still answer, with the error fed back to the model. Tests: Task 7, `test_run_tool_reports_errors_to_the_model`.
5. Creating or renaming a list to a name that already exists must return a French 400, not a 500. Tests: Task 5, `test_duplicate_list_name_is_rule_error`; Task 6, `test_list_routes`.

---

## File map

```
backend/
  pyproject.toml, uv.lock         uv project (Task 1)
  app/__init__.py
  app/text.py                     normalize() for search (Task 1)
  app/errors.py                   NotFound, RuleError (Task 1)
  app/schema.sql                  SQLite schema (Task 3)
  app/db.py                       connect, init_db, load_catalog (Task 3)
  app/catalog.py                  Filters, parse_sort, search_cards, list_groups, get_card (Task 4)
  app/collection.py               quantities, lists and their rules (Task 5)
  app/auth.py                     hardcoded sign-in, current_user (Task 6)
  app/main.py                     create_app: routes, static files (Task 6)
  app/tools.py                    AI tool models, TOOL_SCHEMAS, run_tool (Task 7)
  app/chat.py                     run_chat loop, make_client (Task 7)
  scripts/__init__.py
  scripts/fetch_catalog.py        TCGdex -> data/catalog.json.gz (Tasks 1-2)
  data/catalog.json.gz            committed snapshot (Task 2)
  tests/conftest.py               sample catalog, fixtures (Task 3)
  tests/test_fetch_catalog.py, test_db.py, test_catalog.py, test_collection.py,
  tests/test_api.py, test_tools.py, test_chat.py
frontend/                         Next.js app (Tasks 8-12)
  next.config.ts, vitest.config.ts
  app/globals.css, app/layout.tsx, app/page.tsx, app/connexion/page.tsx
  app/(app)/layout.tsx            header, footer, chat panel around signed-in pages
  app/(app)/explorer/page.tsx, carte/page.tsx, collection/page.tsx,
  app/(app)/listes/page.tsx, listes/voir/page.tsx
  components/Header.tsx, CardImage.tsx, CardGrid.tsx, Pagination.tsx, SortSelect.tsx, ChatPanel.tsx
  lib/types.ts, api.ts, query.ts, text.ts, explorer.ts, chat.ts, useApi.ts (+ *.test.ts)
Dockerfile, .dockerignore         (Task 13)
scripts/start.sh, stop.sh, start.ps1, stop.ps1   (Task 13)
README.md, CLAUDE.md, THIRD_PARTY_NOTICES.md     (Task 13)
```

Day mapping: Tasks 1-4 on Oct 3, Tasks 5-6 on Oct 4, Tasks 8-10 on Oct 5, Tasks 11 and 13 on Oct 6, Tasks 7 and 12 on Oct 7, Task 14 on Oct 8.

---

### Task 1: Backend project and catalog transforms

**Files:**
- Create: `backend/pyproject.toml` (via uv), `backend/app/__init__.py`, `backend/app/text.py`, `backend/app/errors.py`, `backend/scripts/__init__.py`, `backend/scripts/fetch_catalog.py`
- Test: `backend/tests/test_fetch_catalog.py`

**Interfaces:**
- Produces: `app.text.normalize(text: str) -> str`; `app.errors.NotFound`, `app.errors.RuleError`; in `scripts.fetch_catalog`: `local_number(local_id: str) -> int | None`, `rarity_rank(rarity: str | None) -> int | None`, `RARITY_RANKS: dict[str, int]`, `UNKNOWN_RARITY_RANK = 45`, `VARIANTS`, `build_series(detail: dict, order: int) -> dict`, `build_set(detail: dict) -> dict`, `build_card(raw: dict) -> dict` (DB column names plus `dex_ids: list[int]`), `pokemon_names(cards: list[dict]) -> list[dict]` (`{"dex_id", "name"}`), `report(catalog: dict, missing: list[str]) -> list[str]`.

- [ ] **Step 1: Install uv and create the project**

uv is not installed on this machine. Run in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then, from the repo root (new shell so `uv` is on PATH):

```bash
mkdir backend && cd backend
uv init --app --name tcg-backend --python 3.14 --no-readme --vcs none
rm main.py
uv add fastapi uvicorn httpx openai itsdangerous pydantic
uv add --dev pytest
mkdir app scripts tests data
touch app/__init__.py scripts/__init__.py
```

Append to `backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `app/text.py` and `app/errors.py`**

```python
# backend/app/text.py
import unicodedata


def normalize(text: str) -> str:
    """Lowercase and strip accents, so 'Énergie' and 'energie' compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower().strip()
```

```python
# backend/app/errors.py
class NotFound(Exception):
    """A card, list or user that does not exist."""


class RuleError(Exception):
    """A request that breaks a validation or collection rule."""
```

- [ ] **Step 3: Write the failing tests**

```python
# backend/tests/test_fetch_catalog.py
import json

from app.text import normalize
from scripts.fetch_catalog import (
    UNKNOWN_RARITY_RANK,
    build_card,
    build_set,
    local_number,
    pokemon_names,
    rarity_rank,
    report,
)

RAW_FOUINAR = {
    "category": "Pokémon",
    "id": "swsh3-136",
    "illustrator": "tetsuya koizumi",
    "image": "https://assets.tcgdex.net/fr/swsh/swsh3/136",
    "localId": "136",
    "name": "Fouinar",
    "rarity": "Peu Commune",
    "set": {"id": "swsh3", "name": "Ténèbres Embrasées"},
    "variants": {"firstEdition": False, "holo": False, "normal": True, "reverse": True, "wPromo": False},
    "dexId": [162],
    "hp": 110,
    "types": ["Incolore"],
    "evolveFrom": "Fouinette",
    "stage": "Niveau 1",
    "attacks": [{"cost": ["Incolore"], "name": "Mode Cool", "effect": "Piochez 3 cartes."}],
    "retreat": 1,
    "pricing": {"cardmarket": {"avg": 0.08}},
}


def test_normalize_strips_accents_and_case():
    assert normalize("  Énergie Électrique ") == "energie electrique"


def test_local_number():
    assert local_number("136") == 136
    assert local_number("TG05") == 5
    assert local_number("SV010") == 10
    assert local_number("?") is None


def test_rarity_rank_orders_known_and_flags_unknown():
    assert rarity_rank("Commune") < rarity_rank("Peu Commune") < rarity_rank("Rare") < rarity_rank("Hyper rare")
    assert rarity_rank("Rareté inventée") == UNKNOWN_RARITY_RANK
    assert rarity_rank(None) is None


def test_build_card_maps_columns():
    card = build_card(RAW_FOUINAR)
    assert card["id"] == "swsh3-136"
    assert card["set_id"] == "swsh3"
    assert card["local_number"] == 136
    assert card["search_name"] == "fouinar"
    assert card["category"] == "Pokémon"
    assert card["rarity_rank"] == rarity_rank("Peu Commune")
    assert card["hp"] == 110
    assert json.loads(card["types"]) == ["Incolore"]
    assert card["stage"] == "Niveau 1"
    assert card["image_base"] == "https://assets.tcgdex.net/fr/swsh/swsh3/136"
    assert json.loads(card["variants"]) == {
        "normal": True, "reverse": True, "holo": False, "firstEdition": False, "wPromo": False,
    }
    details = json.loads(card["details"])
    assert details["attacks"][0]["name"] == "Mode Cool"
    assert details["evolveFrom"] == "Fouinette"
    assert "pricing" not in details
    assert card["dex_ids"] == [162]


def test_build_card_without_variants_or_optional_fields():
    raw = {"id": "base1-98", "localId": "98", "name": "Énergie Feu", "category": "Énergie", "set": {"id": "base1"}}
    card = build_card(raw)
    assert json.loads(card["variants"])["normal"] is True
    assert card["rarity"] is None and card["rarity_rank"] is None
    assert card["hp"] is None and card["image_base"] is None
    assert card["dex_ids"] == []


def test_build_set_reads_detail():
    detail = {
        "id": "swsh3", "name": "Ténèbres Embrasées", "releaseDate": "2020-08-14",
        "serie": {"id": "swsh"}, "cardCount": {"official": 189, "total": 201},
        "logo": "https://assets.tcgdex.net/fr/swsh/swsh3/logo",
        "symbol": "https://assets.tcgdex.net/univ/swsh/swsh3/symbol",
    }
    assert build_set(detail) == {
        "id": "swsh3", "series_id": "swsh", "name": "Ténèbres Embrasées", "release_date": "2020-08-14",
        "card_count_official": 189, "card_count_total": 201,
        "logo_url": "https://assets.tcgdex.net/fr/swsh/swsh3/logo",
        "symbol_url": "https://assets.tcgdex.net/univ/swsh/swsh3/symbol",
    }


def test_pokemon_names_prefers_single_pokemon_cards():
    cards = [
        {"name": "Pikachu et Zekrom GX", "dex_ids": [25, 644]},
        {"name": "Pikachu VMAX", "dex_ids": [25]},
        {"name": "Pikachu", "dex_ids": [25]},
    ]
    assert pokemon_names(cards) == [
        {"dex_id": 25, "name": "Pikachu"},
        {"dex_id": 644, "name": "Pikachu et Zekrom GX"},
    ]


def test_report_flags_gaps():
    catalog = {
        "series": [{"id": "swsh"}],
        "sets": [{"id": "swsh3", "card_count_total": 2}],
        "cards": [
            {"set_id": "swsh3", "image_base": None, "rarity": "Rareté inventée"},
        ],
    }
    lines = report(catalog, ["swsh3-999"])
    assert "1 séries, 1 extensions, 1 cartes" in lines
    assert "Cartes sans image : 1" in lines
    assert "Raretés sans rang : Rareté inventée" in lines
    assert "Extension swsh3 : 1 cartes, 2 annoncées" in lines
    assert "Cartes introuvables (404) : 1 : swsh3-999" in lines
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_fetch_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.fetch_catalog'` (the `normalize` test cannot be collected either).

- [ ] **Step 5: Write `scripts/fetch_catalog.py`**

```python
"""Fetch the French TCGdex catalog into data/catalog.json.gz.

Run from backend/: uv run python -m scripts.fetch_catalog
"""

import asyncio
import gzip
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

from app.text import normalize

API = "https://api.tcgdex.net/v2/fr"
OUT = Path(__file__).resolve().parent.parent / "data" / "catalog.json.gz"
USER_AGENT = "TCG-exemple (+https://github.com/Sam-ssp/TCG-exemple)"
CONCURRENCY = 5
EXCLUDED_SERIES = {"tcgp"}  # Pokemon TCG Pocket, a digital game
VARIANTS = ("normal", "reverse", "holo", "firstEdition", "wPromo")
DETAIL_KEYS = (
    "attacks", "abilities", "weaknesses", "resistances", "retreat", "effect", "description",
    "evolveFrom", "trainerType", "energyType", "regulationMark", "item",
)

UNKNOWN_RARITY_RANK = 45
RARITY_RANKS = {
    "Sans Rareté": 0,
    "Commune": 10,
    "Peu Commune": 20,
    "Promo": 25,
    "Rare": 30,
    "Rare Holo": 40,
    "Holo Rare": 40,
    "Rare Holo LV.X": 50,
    "Rare Prime": 50,
    "LÉGENDE": 50,
    "Rare Noir Blanc": 50,
    "Holo Rare V": 50,
    "Double rare": 50,
    "Radieux Rare": 50,
    "Magnifique": 50,
    "Pikachu Rare": 50,
    "Collection Classique": 55,
    "Holo Rare VMAX": 60,
    "Holo Rare VSTAR": 60,
    "Ultra Rare": 60,
    "Dresseur Full Art": 60,
    "Futuristic Rare": 60,
    "HIGH-TECH rare": 60,
    "Mega Attack Rare": 60,
    "RGB Rare": 60,
    "Illustration rare": 70,
    "Shiny rare": 70,
    "Shiny rare V": 70,
    "Shiny rare VMAX": 70,
    "Magnifique rare": 70,
    "Chromatique ultra rare": 80,
    "Illustration spéciale rare": 80,
    "Hyper rare": 90,
    "Méga Hyper Rare": 90,
}


def local_number(local_id: str) -> int | None:
    digits = re.search(r"\d+", local_id)
    return int(digits.group()) if digits else None


def rarity_rank(rarity: str | None) -> int | None:
    if rarity is None:
        return None
    return RARITY_RANKS.get(rarity, UNKNOWN_RARITY_RANK)


def build_series(detail: dict, order: int) -> dict:
    return {"id": detail["id"], "name": detail["name"], "logo_url": detail.get("logo"), "release_order": order}


def build_set(detail: dict) -> dict:
    count = detail.get("cardCount", {})
    return {
        "id": detail["id"],
        "series_id": detail["serie"]["id"],
        "name": detail["name"],
        "release_date": detail.get("releaseDate"),
        "card_count_official": count.get("official"),
        "card_count_total": count.get("total"),
        "logo_url": detail.get("logo"),
        "symbol_url": detail.get("symbol"),
    }


def build_card(raw: dict) -> dict:
    variants = {key: bool(raw.get("variants", {}).get(key)) for key in VARIANTS}
    if not any(variants.values()):
        variants["normal"] = True
    rarity = raw.get("rarity")
    return {
        "id": raw["id"],
        "set_id": raw["set"]["id"],
        "local_id": raw["localId"],
        "local_number": local_number(raw["localId"]),
        "name": raw["name"],
        "search_name": normalize(raw["name"]),
        "category": raw["category"],
        "rarity": rarity,
        "rarity_rank": rarity_rank(rarity),
        "illustrator": raw.get("illustrator"),
        "hp": int(raw["hp"]) if raw.get("hp") is not None else None,
        "types": json.dumps(raw.get("types") or [], ensure_ascii=False),
        "stage": raw.get("stage"),
        "image_base": raw.get("image"),
        "variants": json.dumps(variants),
        "details": json.dumps({k: raw[k] for k in DETAIL_KEYS if k in raw}, ensure_ascii=False),
        "dex_ids": raw.get("dexId") or [],
    }


def pokemon_names(cards: list[dict]) -> list[dict]:
    """Name each Pokedex number after its shortest card name, preferring single-Pokemon cards."""
    best: dict[int, tuple] = {}
    for card in cards:
        for dex_id in card["dex_ids"]:
            key = (len(card["dex_ids"]) > 1, len(card["name"]), card["name"])
            if dex_id not in best or key < best[dex_id]:
                best[dex_id] = key
    return [{"dex_id": dex_id, "name": key[2]} for dex_id, key in sorted(best.items())]


def report(catalog: dict, missing: list[str]) -> list[str]:
    cards = catalog["cards"]
    per_set = Counter(card["set_id"] for card in cards)
    lines = [
        f"{len(catalog['series'])} séries, {len(catalog['sets'])} extensions, {len(cards)} cartes",
        f"Cartes sans image : {sum(1 for c in cards if not c['image_base'])}",
        f"Cartes sans rareté : {sum(1 for c in cards if c['rarity'] is None)}",
    ]
    unknown = sorted({c["rarity"] for c in cards if c["rarity"] and c["rarity"] not in RARITY_RANKS})
    if unknown:
        lines.append("Raretés sans rang : " + ", ".join(unknown))
    for card_set in catalog["sets"]:
        total = card_set["card_count_total"]
        if total is not None and per_set[card_set["id"]] != total:
            lines.append(f"Extension {card_set['id']} : {per_set[card_set['id']]} cartes, {total} annoncées")
    if missing:
        lines.append(f"Cartes introuvables (404) : {len(missing)} : {', '.join(missing[:20])}")
    return lines


async def get_json(client: httpx.AsyncClient, limit: asyncio.Semaphore, path: str, optional: bool = False):
    async with limit:
        response = await client.get(API + path)
    if optional and response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


async def fetch() -> tuple[dict, list[str]]:
    limit = asyncio.Semaphore(CONCURRENCY)
    transport = httpx.AsyncHTTPTransport(retries=3)
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}, transport=transport) as client:
        series = [s for s in await get_json(client, limit, "/series") if s["id"] not in EXCLUDED_SERIES]
        series_details = await asyncio.gather(*(get_json(client, limit, f"/series/{s['id']}") for s in series))
        series_details.sort(key=lambda s: s.get("releaseDate") or "9999")
        set_ids = [s["id"] for detail in series_details for s in detail.get("sets", [])]
        set_details = await asyncio.gather(
            *(get_json(client, limit, f"/sets/{quote(set_id, safe='')}") for set_id in set_ids)
        )
        card_ids = [c["id"] for detail in set_details for c in detail.get("cards", [])]
        raw_cards = await asyncio.gather(
            *(get_json(client, limit, f"/cards/{quote(card_id, safe='')}", optional=True) for card_id in card_ids)
        )
    missing = [card_id for card_id, raw in zip(card_ids, raw_cards) if raw is None]
    cards = [build_card(raw) for raw in raw_cards if raw is not None]
    catalog = {
        "version": date.today().isoformat(),
        "series": [build_series(detail, order) for order, detail in enumerate(series_details)],
        "sets": [build_set(detail) for detail in set_details],
        "cards": cards,
        "pokemon": pokemon_names(cards),
    }
    return catalog, missing


def main() -> None:
    catalog, missing = asyncio.run(fetch())
    for line in report(catalog, missing):
        print(line)
    OUT.parent.mkdir(exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False)
    print(f"Écrit : {OUT} ({OUT.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_fetch_catalog.py -v`
Expected: 8 passed.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "KAN-5: Backend project and TCGdex catalog transforms"
```

---

### Task 2: Generate the French catalog snapshot

**Files:**
- Create: `backend/data/catalog.json.gz`

**Interfaces:**
- Consumes: `python -m scripts.fetch_catalog` from Task 1.
- Produces: `backend/data/catalog.json.gz` with keys `version`, `series`, `sets`, `cards`, `pokemon` (shapes from Task 1's builders).

- [ ] **Step 1: Run the fetch (network, about 10 minutes)**

Run: `cd backend && uv run python -m scripts.fetch_catalog`
Expected: the report, then `Écrit : ...catalog.json.gz (N Ko)`. Expected magnitudes (2026-10-02 checks): about 20,000 cards (22,155 French cards including Pocket), a few thousand without image, no or few "Raretés sans rang".

- [ ] **Step 2: Fix rarity ranks if needed**

If the report prints `Raretés sans rang : ...`, add each listed name to `RARITY_RANKS` in `scripts/fetch_catalog.py` at the rank of the closest existing rarity, rerun Step 1, and confirm the line is gone. Rerun `uv run pytest tests/test_fetch_catalog.py`.

- [ ] **Step 3: Check the file**

Run: `cd backend && uv run python -c "import gzip,json;d=json.load(gzip.open('data/catalog.json.gz','rt',encoding='utf-8'));print(d['version'],len(d['sets']),len(d['cards']),len(d['pokemon']))"`
Expected: today's date, about 190 sets, about 20,000 cards, about 1,000 Pokemon. File size a few MB; if it is over 50 MB, stop and report.

Save the report output in the commit message body; the README (Task 13) quotes the counts.

- [ ] **Step 4: Commit**

```bash
git add backend/data/catalog.json.gz backend/scripts/fetch_catalog.py
git commit -m "KAN-5: Add French TCGdex catalog snapshot"
```

---

### Task 3: Database schema and start-up load

**Files:**
- Create: `backend/app/schema.sql`, `backend/app/db.py`, `backend/tests/conftest.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: `build_card`, `pokemon_names` (Task 1) in the test fixture.
- Produces: `db.connect(path: str) -> sqlite3.Connection` (row factory `sqlite3.Row`, foreign keys on, usable across threads); `db.read_catalog(path: str) -> dict`; `db.load_catalog(conn, catalog: dict) -> None`; `db.init_db(db_path: str, catalog_path: str) -> None`. Fixtures: `sample_catalog()` function, `catalog_file`, `conn`, `make_client(chat_client=None) -> TestClient`, `client` (signed-in TestClient; used from Task 6).

- [ ] **Step 1: Write `app/schema.sql`**

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
    local_number INTEGER,
    name         TEXT NOT NULL,
    search_name  TEXT NOT NULL,
    category     TEXT NOT NULL,
    rarity       TEXT,
    rarity_rank  INTEGER,
    illustrator  TEXT,
    hp           INTEGER,
    types        TEXT,
    stage        TEXT,
    image_base   TEXT,
    variants     TEXT NOT NULL,
    details      TEXT,
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
    variant  TEXT NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_cards_illustrator ON cards (illustrator COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_cards_search_name ON cards (search_name);
CREATE INDEX IF NOT EXISTS idx_card_pokemon_dex  ON card_pokemon (dex_id);
```

- [ ] **Step 2: Write `tests/conftest.py`**

```python
import gzip
import json

import pytest
from fastapi.testclient import TestClient

from app import db
from scripts.fetch_catalog import build_card, pokemon_names


def _raw(card_id, name, *, category="Pokémon", rarity="Commune", illustrator=None, hp=None,
         types=None, dex=None, variants=None, image=True):
    set_id, local_id = card_id.rsplit("-", 1)
    card = {"id": card_id, "localId": local_id, "name": name, "category": category,
            "set": {"id": set_id}, "variants": variants or {"normal": True}}
    optional = {
        "rarity": rarity, "illustrator": illustrator, "hp": hp, "types": types, "dexId": dex,
        "image": f"https://assets.tcgdex.net/fr/test/{set_id}/{local_id}" if image else None,
    }
    card.update({key: value for key, value in optional.items() if value is not None})
    return card


RAW_CARDS = [
    _raw("base1-4", "Dracaufeu", rarity="Rare Holo", illustrator="Mitsuhiro Arita", hp=120,
         types=["Feu"], dex=[6], variants={"holo": True, "firstEdition": True}),
    _raw("base1-58", "Pikachu", illustrator="Mitsuhiro Arita", hp=40, types=["Électrique"], dex=[25],
         variants={"normal": True, "firstEdition": True}),
    _raw("base1-88", "Professeur Chen", category="Dresseur", rarity="Peu Commune", illustrator="Ken Sugimori"),
    _raw("base1-98", "Énergie Feu", category="Énergie", rarity=None, image=False),
    _raw("swsh3-20", "Dracaufeu VMAX", rarity="Holo Rare VMAX", illustrator="aky CG Works", hp=330,
         types=["Feu"], dex=[6], variants={"holo": True}),
    _raw("swsh3-136", "Fouinar", rarity="Peu Commune", illustrator="tetsuya koizumi", hp=110,
         types=["Incolore"], dex=[162], variants={"normal": True, "reverse": True}),
    _raw("swsh4-44", "Pikachu", illustrator="Mitsuhiro Arita", hp=60, types=["Électrique"], dex=[25],
         variants={"normal": True, "reverse": True}),
    _raw("swsh4-188", "Pikachu VMAX", rarity="Ultra Rare", illustrator="aky CG Works", hp=310,
         types=["Électrique"], dex=[25], variants={"holo": True}),
    _raw("swsh4-200", "Pikachu et Zekrom GX", rarity="Ultra Rare", illustrator="Mitsuhiro Arita", hp=240,
         types=["Électrique"], dex=[25, 644], variants={"holo": True}),
    _raw("swsh4-?", "Zarbi ?", rarity="Rare", hp=50, types=["Psy"], dex=[201]),
]


def sample_catalog(version="test-1"):
    cards = [build_card(raw) for raw in RAW_CARDS]
    return {
        "version": version,
        "series": [
            {"id": "base", "name": "Base", "logo_url": None, "release_order": 0},
            {"id": "swsh", "name": "Épée et Bouclier", "logo_url": None, "release_order": 1},
        ],
        "sets": [
            {"id": "base1", "series_id": "base", "name": "Set de Base", "release_date": "1999-01-09",
             "card_count_official": 102, "card_count_total": 102, "logo_url": None, "symbol_url": None},
            {"id": "swsh3", "series_id": "swsh", "name": "Ténèbres Embrasées", "release_date": "2020-08-14",
             "card_count_official": 189, "card_count_total": 201, "logo_url": None, "symbol_url": None},
            {"id": "swsh4", "series_id": "swsh", "name": "Voltage Éclatant", "release_date": "2020-11-13",
             "card_count_official": 185, "card_count_total": 203, "logo_url": None, "symbol_url": None},
        ],
        "cards": cards,
        "pokemon": pokemon_names(cards),
    }


def write_catalog(path, catalog):
    with gzip.open(path, "wt", encoding="utf-8") as file:
        json.dump(catalog, file, ensure_ascii=False)


@pytest.fixture
def catalog_file(tmp_path):
    path = tmp_path / "catalog.json.gz"
    write_catalog(path, sample_catalog())
    return path


@pytest.fixture
def conn(tmp_path, catalog_file):
    db_path = str(tmp_path / "tcg.db")
    db.init_db(db_path, str(catalog_file))
    connection = db.connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def make_client(tmp_path, catalog_file):
    from app.main import create_app

    def make(chat_client=None):
        app = create_app(db_path=str(tmp_path / "api.db"), catalog_path=str(catalog_file),
                         static_dir=str(tmp_path / "no-static"), chat_client=chat_client)
        return TestClient(app)

    return make


@pytest.fixture
def client(make_client):
    signed_in = make_client()
    signed_in.post("/api/connexion", json={"utilisateur": "user", "mot_de_passe": "user"})
    return signed_in
```

- [ ] **Step 3: Write the failing tests**

```python
# backend/tests/test_db.py
import sqlite3

import pytest

from app import db
from tests.conftest import sample_catalog, write_catalog


def test_init_loads_catalog_and_default_user(conn):
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 10
    assert conn.execute("SELECT COUNT(*) FROM sets").fetchone()[0] == 3
    assert conn.execute("SELECT name FROM pokemon WHERE dex_id = 25").fetchone()["name"] == "Pikachu"
    assert conn.execute("SELECT COUNT(*) FROM card_pokemon WHERE card_id = 'swsh4-200'").fetchone()[0] == 2
    assert conn.execute("SELECT value FROM meta WHERE key = 'catalog_version'").fetchone()["value"] == "test-1"
    assert conn.execute("SELECT id FROM users WHERE username = 'user'").fetchone()["id"] == 1


def test_new_catalog_version_updates_cards_and_keeps_user_data(tmp_path, catalog_file):
    db_path = str(tmp_path / "tcg.db")
    db.init_db(db_path, str(catalog_file))
    connection = db.connect(db_path)
    connection.execute("INSERT INTO collection_items (user_id, card_id, variant, quantity) VALUES (1, 'base1-4', 'holo', 2)")
    connection.commit()

    updated = sample_catalog(version="test-2")
    updated["cards"][0]["name"] = "Dracaufeu (corrigé)"
    write_catalog(catalog_file, updated)
    db.init_db(db_path, str(catalog_file))

    assert connection.execute("SELECT name FROM cards WHERE id = 'base1-4'").fetchone()["name"] == "Dracaufeu (corrigé)"
    assert connection.execute("SELECT quantity FROM collection_items").fetchone()["quantity"] == 2
    connection.close()


def test_missing_catalog_stops_start_up(tmp_path):
    with pytest.raises(RuntimeError, match="Catalogue introuvable"):
        db.init_db(str(tmp_path / "tcg.db"), str(tmp_path / "absent.json.gz"))


def test_foreign_keys_are_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO collection_items (user_id, card_id, variant, quantity) VALUES (1, 'nope-1', 'normal', 1)")
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: FAIL with `AttributeError: module 'app.db' has no attribute 'init_db'` (or `ImportError` on `app.db`).

- [ ] **Step 5: Write `app/db.py`**

```python
import gzip
import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_USER = "user"


def connect(path: str) -> sqlite3.Connection:
    # One connection per request; FastAPI may run the dependency and the route on different threads.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def read_catalog(path: str) -> dict:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise RuntimeError(
            f"Catalogue introuvable : {path}. Lancez 'uv run python -m scripts.fetch_catalog' dans backend/."
        ) from None


def _upsert(conn: sqlite3.Connection, table: str, rows: list[dict], key: str = "id") -> None:
    if not rows:
        return
    columns = list(rows[0])
    updates = ", ".join(f"{c} = excluded.{c}" for c in columns if c != key)
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))}) "
        f"ON CONFLICT({key}) DO UPDATE SET {updates}",
        [tuple(row[c] for c in columns) for row in rows],
    )


def load_catalog(conn: sqlite3.Connection, catalog: dict) -> None:
    """Upsert the catalog. Rows are never deleted, so user data keeps valid card ids."""
    with conn:
        _upsert(conn, "series", catalog["series"])
        _upsert(conn, "sets", catalog["sets"])
        _upsert(conn, "cards", [{k: v for k, v in card.items() if k != "dex_ids"} for card in catalog["cards"]])
        conn.executemany(
            "INSERT OR IGNORE INTO card_pokemon (card_id, dex_id) VALUES (?, ?)",
            [(card["id"], dex_id) for card in catalog["cards"] for dex_id in card["dex_ids"]],
        )
        _upsert(conn, "pokemon", catalog["pokemon"], key="dex_id")
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('catalog_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (catalog["version"],),
        )


def init_db(db_path: str, catalog_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    catalog = read_catalog(catalog_path)
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        stored = conn.execute("SELECT value FROM meta WHERE key = 'catalog_version'").fetchone()
        if stored is None or stored["value"] != catalog["version"]:
            load_catalog(conn, catalog)
        with conn:
            conn.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, ?)", (DEFAULT_USER,))
    finally:
        conn.close()
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && uv run pytest -v`
Expected: all tests pass (8 from Task 1, 4 new).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schema.sql backend/app/db.py backend/tests
git commit -m "KAN-5: SQLite schema and catalog load at start-up"
```

---

### Task 4: Catalog queries (browse, groups, search, detail)

**Files:**
- Create: `backend/app/catalog.py`
- Test: `backend/tests/test_catalog.py`

**Interfaces:**
- Consumes: `conn` fixture, `normalize`, `NotFound`, `RuleError`.
- Produces:
  - `GroupBy = Literal["set", "pokemon", "illustrateur", "rarete"]`, `PAGE_SIZE = 60`, `SORT_FIELDS: tuple[str, ...]`
  - `class Filters(BaseModel)`: `set, illustrateur, rarete, type, q: str | None`; `pokemon, proprietaire, liste: int | None` (all default `None`)
  - `parse_sort(tri: str | None) -> list[tuple[str, str]]` (raises `RuleError`)
  - `search_cards(conn, filters: Filters, tri: str | None = None, page: int = 1, user_id: int | None = None, page_size: int = PAGE_SIZE) -> dict` returning `{"cartes": [CardSummary], "total": int, "page": int, "pages": int}`, where a CardSummary is `{"id", "nom", "set_id", "set_nom", "numero", "rarete", "illustrateur", "pv", "image", "quantite"}` (`quantite` = total copies owned by `user_id`, 0 if none)
  - `list_groups(conn, par: GroupBy) -> list[dict]` with `{"valeur": str, "nom": str, "nombre": int, "groupe": str | None, "image": str | None}`
  - `get_card(conn, card_id: str) -> dict` with keys `id, nom, set_id, set_nom, serie_nom, date_sortie, numero, categorie, rarete, illustrateur, pv, types (list), stade, image, variantes (list of available variant names), details (dict), pokemon (list of {"dex_id", "nom"})`; raises `NotFound`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_catalog.py
import pytest

from app import catalog
from app.catalog import Filters
from app.errors import NotFound, RuleError


def ids(result):
    return [card["id"] for card in result["cartes"]]


def test_default_order_is_release_date_then_number(conn):
    result = catalog.search_cards(conn, Filters())
    assert result["total"] == 10
    assert ids(result)[:4] == ["base1-4", "base1-58", "base1-88", "base1-98"]
    assert ids(result)[-4:] == ["swsh4-44", "swsh4-188", "swsh4-200", "swsh4-?"]


def test_filters(conn):
    assert ids(catalog.search_cards(conn, Filters(set="swsh3"))) == ["swsh3-20", "swsh3-136"]
    assert ids(catalog.search_cards(conn, Filters(pokemon=25))) == ["base1-58", "swsh4-44", "swsh4-188", "swsh4-200"]
    assert catalog.search_cards(conn, Filters(illustrateur="MITSUHIRO ARITA"))["total"] == 4
    assert ids(catalog.search_cards(conn, Filters(rarete="Ultra Rare"))) == ["swsh4-188", "swsh4-200"]
    assert ids(catalog.search_cards(conn, Filters(type="Feu"))) == ["base1-4", "swsh3-20"]
    assert ids(catalog.search_cards(conn, Filters(type="Feu", set="base1"))) == ["base1-4"]


def test_search_is_literal_and_accent_insensitive(conn):
    assert ids(catalog.search_cards(conn, Filters(q="dracau"))) == ["base1-4", "swsh3-20"]
    assert ids(catalog.search_cards(conn, Filters(q="ENERGIE"))) == ["base1-98"]
    assert ids(catalog.search_cards(conn, Filters(q="zarbi ?"))) == ["swsh4-?"]
    assert catalog.search_cards(conn, Filters(q="%"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="_"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="dracaufeu%"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="l'"))["total"] == 0


def test_sort_by_hp_desc_puts_nulls_last(conn):
    result = ids(catalog.search_cards(conn, Filters(), tri="pv:desc"))
    assert result[:2] == ["swsh3-20", "swsh4-188"]
    assert result[-2:] == ["base1-88", "base1-98"]


def test_sort_by_rarity_breaks_ties_by_date_then_number(conn):
    result = ids(catalog.search_cards(conn, Filters(), tri="rarete:desc"))
    assert result[:4] == ["swsh3-20", "swsh4-188", "swsh4-200", "base1-4"]
    assert result[-1] == "base1-98"


def test_sort_by_number_and_combined_sort(conn):
    assert ids(catalog.search_cards(conn, Filters(set="swsh4"), tri="numero:desc")) == ["swsh4-200", "swsh4-188", "swsh4-44", "swsh4-?"]
    assert ids(catalog.search_cards(conn, Filters(pokemon=25), tri="nom:asc,pv:desc")) == ["swsh4-44", "base1-58", "swsh4-200", "swsh4-188"]
    assert ids(catalog.search_cards(conn, Filters(type="Électrique"), tri="pokedex:asc"))[0] == "base1-58"


def test_invalid_sort_and_page(conn):
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), tri="prix:desc")
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), tri="nom:up")
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), page=0)


def test_pagination(conn):
    result = catalog.search_cards(conn, Filters(), page=2, page_size=3)
    assert ids(result) == ["base1-98", "swsh3-20", "swsh3-136"]
    assert result["pages"] == 4
    assert catalog.search_cards(conn, Filters(), page=9, page_size=3)["cartes"] == []


def test_card_summary_fields(conn):
    card = catalog.search_cards(conn, Filters(set="swsh3"), user_id=1)["cartes"][1]
    assert card == {
        "id": "swsh3-136", "nom": "Fouinar", "set_id": "swsh3", "set_nom": "Ténèbres Embrasées",
        "numero": "136", "rarete": "Peu Commune", "illustrateur": "tetsuya koizumi", "pv": 110,
        "image": "https://assets.tcgdex.net/fr/test/swsh3/136", "quantite": 0,
    }


def test_groups(conn):
    sets = catalog.list_groups(conn, "set")
    assert [(g["valeur"], g["groupe"], g["nombre"]) for g in sets] == [
        ("base1", "Base", 4), ("swsh3", "Épée et Bouclier", 2), ("swsh4", "Épée et Bouclier", 4),
    ]
    pokemon = catalog.list_groups(conn, "pokemon")
    assert [(g["valeur"], g["nom"], g["nombre"]) for g in pokemon][:2] == [("6", "Dracaufeu", 2), ("25", "Pikachu", 4)]
    assert [g["nom"] for g in catalog.list_groups(conn, "illustrateur")] == [
        "aky CG Works", "Ken Sugimori", "Mitsuhiro Arita", "tetsuya koizumi",
    ]
    assert [g["nom"] for g in catalog.list_groups(conn, "rarete")] == [
        "Commune", "Peu Commune", "Rare", "Rare Holo", "Holo Rare VMAX", "Ultra Rare",
    ]


def test_get_card(conn):
    card = catalog.get_card(conn, "swsh4-200")
    assert card["nom"] == "Pikachu et Zekrom GX"
    assert card["set_nom"] == "Voltage Éclatant"
    assert card["serie_nom"] == "Épée et Bouclier"
    assert card["variantes"] == ["holo"]
    assert card["types"] == ["Électrique"]
    assert card["pokemon"] == [{"dex_id": 25, "nom": "Pikachu"}, {"dex_id": 644, "nom": "Pikachu et Zekrom GX"}]
    with pytest.raises(NotFound):
        catalog.get_card(conn, "nope-1")
```

Check of the combined-sort expectation: `nom:asc` on `search_name` gives "pikachu" (base1-58, swsh4-44), "pikachu et zekrom gx", "pikachu vmax"; within the two "pikachu", `pv:desc` puts swsh4-44 (60) before base1-58 (40).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_catalog.py -v`
Expected: FAIL with `ImportError: cannot import name 'catalog' from 'app'`.

- [ ] **Step 3: Write `app/catalog.py`**

```python
import json
import sqlite3
from typing import Literal

from pydantic import BaseModel

from app.errors import NotFound, RuleError
from app.text import normalize

PAGE_SIZE = 60
GroupBy = Literal["set", "pokemon", "illustrateur", "rarete"]

SORT_COLUMNS = {
    "nom": "c.search_name",
    "pokedex": "(SELECT MIN(dex_id) FROM card_pokemon WHERE card_id = c.id)",
    "pv": "c.hp",
    "rarete": "c.rarity_rank",
    "illustrateur": "c.illustrator COLLATE NOCASE",
    "date_sortie": "s.release_date",
    "numero": "c.local_number",
}
SORT_FIELDS = tuple(SORT_COLUMNS)
# Every sort ends with these, so pages are stable.
TIEBREAK = ["s.release_date ASC NULLS LAST", "c.set_id ASC", "c.local_number ASC NULLS LAST", "c.local_id ASC"]

CARD_COLUMNS = """
    c.id, c.name AS nom, c.set_id, s.name AS set_nom, c.local_id AS numero, c.rarity AS rarete,
    c.illustrator AS illustrateur, c.hp AS pv, c.image_base AS image,
    COALESCE((SELECT SUM(quantity) FROM collection_items ci
              WHERE ci.card_id = c.id AND ci.user_id = ?), 0) AS quantite
"""

GROUP_QUERIES = {
    "set": """
        SELECT s.id AS valeur, s.name AS nom, COUNT(c.id) AS nombre, se.name AS groupe, s.symbol_url AS image
        FROM sets s JOIN series se ON se.id = s.series_id LEFT JOIN cards c ON c.set_id = s.id
        GROUP BY s.id ORDER BY se.release_order, s.release_date, s.id
    """,
    "pokemon": """
        SELECT CAST(p.dex_id AS TEXT) AS valeur, p.name AS nom, COUNT(*) AS nombre, NULL AS groupe, NULL AS image
        FROM pokemon p JOIN card_pokemon cp ON cp.dex_id = p.dex_id
        GROUP BY p.dex_id ORDER BY p.dex_id
    """,
    "illustrateur": """
        SELECT illustrator AS valeur, illustrator AS nom, COUNT(*) AS nombre, NULL AS groupe, NULL AS image
        FROM cards WHERE illustrator IS NOT NULL
        GROUP BY illustrator COLLATE NOCASE ORDER BY illustrator COLLATE NOCASE
    """,
    "rarete": """
        SELECT rarity AS valeur, rarity AS nom, COUNT(*) AS nombre, NULL AS groupe, NULL AS image
        FROM cards WHERE rarity IS NOT NULL
        GROUP BY rarity ORDER BY MIN(rarity_rank), rarity
    """,
}


class Filters(BaseModel):
    set: str | None = None
    pokemon: int | None = None
    illustrateur: str | None = None
    rarete: str | None = None
    type: str | None = None
    q: str | None = None
    proprietaire: int | None = None  # user id: only cards this user owns
    liste: int | None = None  # list id: only cards in this list


def parse_sort(tri: str | None) -> list[tuple[str, str]]:
    keys = []
    for part in (tri or "").split(","):
        part = part.strip()
        if not part:
            continue
        field, _, direction = part.partition(":")
        direction = direction or "asc"
        if field not in SORT_COLUMNS or direction not in ("asc", "desc"):
            raise RuleError(f"Tri invalide : {part}")
        keys.append((field, direction))
    return keys


def _like_pattern(term: str) -> str:
    escaped = normalize(term).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _where(filters: Filters) -> tuple[str, list]:
    conditions = [
        (filters.set, "c.set_id = ?"),
        (filters.pokemon, "EXISTS (SELECT 1 FROM card_pokemon cp WHERE cp.card_id = c.id AND cp.dex_id = ?)"),
        (filters.illustrateur, "c.illustrator = ? COLLATE NOCASE"),
        (filters.rarete, "c.rarity = ?"),
        (filters.type, "EXISTS (SELECT 1 FROM json_each(c.types) WHERE value = ?)"),
        (_like_pattern(filters.q) if filters.q else None, "c.search_name LIKE ? ESCAPE '\\'"),
        (filters.proprietaire, "EXISTS (SELECT 1 FROM collection_items ci WHERE ci.card_id = c.id AND ci.user_id = ?)"),
        (filters.liste, "EXISTS (SELECT 1 FROM list_items li WHERE li.card_id = c.id AND li.list_id = ?)"),
    ]
    active = [(value, sql) for value, sql in conditions if value is not None and value != ""]
    if not active:
        return "", []
    return "WHERE " + " AND ".join(sql for _, sql in active), [value for value, _ in active]


def search_cards(conn: sqlite3.Connection, filters: Filters, tri: str | None = None, page: int = 1,
                 user_id: int | None = None, page_size: int = PAGE_SIZE) -> dict:
    if page < 1:
        raise RuleError("Page invalide")
    where, params = _where(filters)
    order = [f"{SORT_COLUMNS[field]} {direction.upper()} NULLS LAST" for field, direction in parse_sort(tri)]
    total = conn.execute(f"SELECT COUNT(*) FROM cards c {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {CARD_COLUMNS} FROM cards c JOIN sets s ON s.id = c.set_id {where} "
        f"ORDER BY {', '.join(order + TIEBREAK)} LIMIT ? OFFSET ?",
        [user_id, *params, page_size, (page - 1) * page_size],
    ).fetchall()
    return {"cartes": [dict(row) for row in rows], "total": total, "page": page,
            "pages": max(1, -(-total // page_size))}


def list_groups(conn: sqlite3.Connection, par: GroupBy) -> list[dict]:
    if par not in GROUP_QUERIES:
        raise RuleError(f"Regroupement invalide : {par}")
    return [dict(row) for row in conn.execute(GROUP_QUERIES[par])]


def get_card(conn: sqlite3.Connection, card_id: str) -> dict:
    row = conn.execute(
        """SELECT c.*, s.name AS set_nom, s.release_date, se.name AS serie_nom
           FROM cards c JOIN sets s ON s.id = c.set_id JOIN series se ON se.id = s.series_id
           WHERE c.id = ?""",
        (card_id,),
    ).fetchone()
    if row is None:
        raise NotFound("Carte introuvable")
    pokemon = conn.execute(
        """SELECT p.dex_id, p.name AS nom FROM card_pokemon cp JOIN pokemon p ON p.dex_id = cp.dex_id
           WHERE cp.card_id = ? ORDER BY p.dex_id""",
        (card_id,),
    ).fetchall()
    return {
        "id": row["id"],
        "nom": row["name"],
        "set_id": row["set_id"],
        "set_nom": row["set_nom"],
        "serie_nom": row["serie_nom"],
        "date_sortie": row["release_date"],
        "numero": row["local_id"],
        "categorie": row["category"],
        "rarete": row["rarity"],
        "illustrateur": row["illustrator"],
        "pv": row["hp"],
        "types": json.loads(row["types"] or "[]"),
        "stade": row["stage"],
        "image": row["image_base"],
        "variantes": [name for name, available in json.loads(row["variants"]).items() if available],
        "details": json.loads(row["details"] or "{}"),
        "pokemon": [dict(p) for p in pokemon],
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/catalog.py backend/tests/test_catalog.py
git commit -m "KAN-5: Catalog browse, groups, search and card detail"
```

---

### Task 5: Collection and lists

**Files:**
- Create: `backend/app/collection.py`
- Test: `backend/tests/test_collection.py`

**Interfaces:**
- Consumes: `catalog.search_cards`, `Filters` (Task 4).
- Produces:
  - `VARIANTS = ("normal", "reverse", "holo", "firstEdition", "wPromo")`, `Variant` (Literal of those), `ListKind = Literal["collection", "souhaits"]`, `MAX_QUANTITY = 9999`
  - `quantities(conn, user_id, card_id) -> dict[str, int]`
  - `set_quantity(conn, user_id, card_id, variant, quantity) -> dict[str, int]`
  - `add_copies(conn, user_id, card_id, variant, quantity) -> dict[str, int]`, `remove_copies(...) -> dict[str, int]`
  - `create_list(conn, user_id, name, kind) -> dict`, `user_lists(conn, user_id) -> list[dict]`, `get_list(conn, user_id, list_id) -> dict`, `find_list(conn, user_id, name) -> dict`, `rename_list(conn, user_id, list_id, name) -> dict`, `delete_list(conn, user_id, list_id) -> None`; a list dict is `{"id": int, "nom": str, "type": ListKind, "nombre": int}`
  - `add_to_list(conn, user_id, list_id, card_id) -> None`, `remove_from_list(conn, user_id, list_id, card_id) -> None`, `lists_containing(conn, user_id, card_id) -> list[dict]` (`{"id", "nom", "type"}`)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_collection.py
import pytest

from app import catalog, collection
from app.catalog import Filters
from app.errors import NotFound, RuleError


def test_set_quantity_per_variant(conn):
    assert collection.set_quantity(conn, 1, "base1-4", "holo", 2) == {"holo": 2}
    assert collection.set_quantity(conn, 1, "base1-4", "firstEdition", 1) == {"holo": 2, "firstEdition": 1}
    assert collection.set_quantity(conn, 1, "base1-4", "holo", 0) == {"firstEdition": 1}


def test_set_quantity_rejects_bad_values(conn):
    with pytest.raises(RuleError, match="Variante"):
        collection.set_quantity(conn, 1, "base1-4", "reverse", 1)
    with pytest.raises(RuleError, match="Variante"):
        collection.set_quantity(conn, 1, "base1-4", "brillante", 1)
    with pytest.raises(RuleError, match="Quantité"):
        collection.set_quantity(conn, 1, "base1-4", "holo", -1)
    with pytest.raises(RuleError, match="Quantité"):
        collection.set_quantity(conn, 1, "base1-4", "holo", collection.MAX_QUANTITY + 1)
    with pytest.raises(NotFound):
        collection.set_quantity(conn, 1, "nope-1", "normal", 1)


def test_add_copies_accumulates(conn):
    collection.add_copies(conn, 1, "swsh3-136", "reverse", 2)
    assert collection.add_copies(conn, 1, "swsh3-136", "reverse", 3) == {"reverse": 5}
    with pytest.raises(RuleError):
        collection.add_copies(conn, 1, "swsh3-136", "reverse", 0)


def test_remove_copies_floors_at_zero_and_cleans_lists(conn):
    collection.add_copies(conn, 1, "swsh3-136", "normal", 1)
    collection.add_copies(conn, 1, "swsh3-136", "reverse", 1)
    owned = collection.create_list(conn, 1, "Classeur", "collection")
    wished = collection.create_list(conn, 1, "Recherchées", "souhaits")
    collection.add_to_list(conn, 1, owned["id"], "swsh3-136")
    collection.add_to_list(conn, 1, wished["id"], "swsh3-136")

    collection.remove_copies(conn, 1, "swsh3-136", "normal", 5)
    assert collection.get_list(conn, 1, owned["id"])["nombre"] == 1  # still owns the reverse

    assert collection.remove_copies(conn, 1, "swsh3-136", "reverse", 5) == {}
    assert collection.get_list(conn, 1, owned["id"])["nombre"] == 0
    assert collection.get_list(conn, 1, wished["id"])["nombre"] == 1


def test_collection_list_accepts_only_owned_cards(conn):
    owned = collection.create_list(conn, 1, "Classeur", "collection")
    with pytest.raises(RuleError, match="possédées"):
        collection.add_to_list(conn, 1, owned["id"], "base1-4")
    wished = collection.create_list(conn, 1, "Recherchées", "souhaits")
    collection.add_to_list(conn, 1, wished["id"], "base1-4")
    collection.add_to_list(conn, 1, wished["id"], "base1-4")  # adding twice is harmless
    assert collection.get_list(conn, 1, wished["id"])["nombre"] == 1
    with pytest.raises(NotFound):
        collection.add_to_list(conn, 1, wished["id"], "nope-1")


def test_duplicate_list_name_is_rule_error(conn):
    collection.create_list(conn, 1, "Favoris", "souhaits")
    with pytest.raises(RuleError, match="existe déjà"):
        collection.create_list(conn, 1, "Favoris", "collection")
    other = collection.create_list(conn, 1, "Autre", "souhaits")
    with pytest.raises(RuleError, match="existe déjà"):
        collection.rename_list(conn, 1, other["id"], "Favoris")
    with pytest.raises(RuleError):
        collection.create_list(conn, 1, "   ", "souhaits")
    with pytest.raises(RuleError):
        collection.create_list(conn, 1, "Mauvais type", "vitrine")


def test_lists_are_private_to_their_user(conn):
    conn.execute("INSERT INTO users (id, username) VALUES (2, 'autre')")
    conn.commit()
    mine = collection.create_list(conn, 1, "Favoris", "souhaits")
    with pytest.raises(NotFound):
        collection.get_list(conn, 2, mine["id"])
    with pytest.raises(NotFound):
        collection.delete_list(conn, 2, mine["id"])
    assert collection.user_lists(conn, 2) == []


def test_list_management(conn):
    first = collection.create_list(conn, 1, "Favoris", "souhaits")
    assert first == {"id": first["id"], "nom": "Favoris", "type": "souhaits", "nombre": 0}
    collection.add_to_list(conn, 1, first["id"], "swsh4-?")
    assert collection.find_list(conn, 1, "favoris")["id"] == first["id"]
    assert collection.rename_list(conn, 1, first["id"], "Préférées")["nom"] == "Préférées"
    assert collection.lists_containing(conn, 1, "swsh4-?") == [{"id": first["id"], "nom": "Préférées", "type": "souhaits"}]
    collection.remove_from_list(conn, 1, first["id"], "swsh4-?")
    assert collection.lists_containing(conn, 1, "swsh4-?") == []
    collection.delete_list(conn, 1, first["id"])
    assert collection.user_lists(conn, 1) == []
    with pytest.raises(NotFound):
        collection.find_list(conn, 1, "Préférées")


def test_owned_cards_through_search(conn):
    collection.add_copies(conn, 1, "base1-4", "holo", 2)
    collection.add_copies(conn, 1, "base1-4", "firstEdition", 1)
    result = catalog.search_cards(conn, Filters(proprietaire=1), user_id=1)
    assert [(c["id"], c["quantite"]) for c in result["cartes"]] == [("base1-4", 3)]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_collection.py -v`
Expected: FAIL with `ImportError: cannot import name 'collection' from 'app'`.

- [ ] **Step 3: Write `app/collection.py`**

```python
import json
import sqlite3
from typing import Literal

from app.errors import NotFound, RuleError

VARIANTS = ("normal", "reverse", "holo", "firstEdition", "wPromo")
Variant = Literal["normal", "reverse", "holo", "firstEdition", "wPromo"]
ListKind = Literal["collection", "souhaits"]
MAX_QUANTITY = 9999

LIST_SUMMARY = """
    SELECT l.id, l.name AS nom, l.kind AS type, COUNT(li.card_id) AS nombre
    FROM lists l LEFT JOIN list_items li ON li.list_id = l.id
"""


def _available_variants(conn: sqlite3.Connection, card_id: str) -> list[str]:
    row = conn.execute("SELECT variants FROM cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        raise NotFound("Carte introuvable")
    return [name for name, available in json.loads(row["variants"]).items() if available]


def quantities(conn: sqlite3.Connection, user_id: int, card_id: str) -> dict[str, int]:
    rows = conn.execute(
        "SELECT variant, quantity FROM collection_items WHERE user_id = ? AND card_id = ? ORDER BY added_at, variant",
        (user_id, card_id),
    )
    return {row["variant"]: row["quantity"] for row in rows}


def set_quantity(conn: sqlite3.Connection, user_id: int, card_id: str, variant: str, quantity: int) -> dict[str, int]:
    if variant not in _available_variants(conn, card_id):
        raise RuleError(f"Variante « {variant} » indisponible pour cette carte")
    if not 0 <= quantity <= MAX_QUANTITY:
        raise RuleError(f"Quantité invalide : {quantity}")
    with conn:
        if quantity == 0:
            conn.execute(
                "DELETE FROM collection_items WHERE user_id = ? AND card_id = ? AND variant = ?",
                (user_id, card_id, variant),
            )
            # A card no longer owned in any variant leaves the user's collection lists.
            conn.execute(
                """DELETE FROM list_items WHERE card_id = ?
                   AND list_id IN (SELECT id FROM lists WHERE user_id = ? AND kind = 'collection')
                   AND NOT EXISTS (SELECT 1 FROM collection_items WHERE user_id = ? AND card_id = ?)""",
                (card_id, user_id, user_id, card_id),
            )
        else:
            conn.execute(
                """INSERT INTO collection_items (user_id, card_id, variant, quantity) VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, card_id, variant) DO UPDATE SET quantity = excluded.quantity""",
                (user_id, card_id, variant, quantity),
            )
    return quantities(conn, user_id, card_id)


def add_copies(conn: sqlite3.Connection, user_id: int, card_id: str, variant: str, quantity: int) -> dict[str, int]:
    if quantity < 1:
        raise RuleError(f"Quantité invalide : {quantity}")
    current = quantities(conn, user_id, card_id).get(variant, 0)
    return set_quantity(conn, user_id, card_id, variant, current + quantity)


def remove_copies(conn: sqlite3.Connection, user_id: int, card_id: str, variant: str, quantity: int) -> dict[str, int]:
    if quantity < 1:
        raise RuleError(f"Quantité invalide : {quantity}")
    current = quantities(conn, user_id, card_id).get(variant, 0)
    return set_quantity(conn, user_id, card_id, variant, max(0, current - quantity))


def _clean_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise RuleError("Le nom de la liste est vide")
    return name


def create_list(conn: sqlite3.Connection, user_id: int, name: str, kind: str) -> dict:
    name = _clean_name(name)
    if kind not in ("collection", "souhaits"):
        raise RuleError(f"Type de liste invalide : {kind}")
    try:
        with conn:
            cursor = conn.execute("INSERT INTO lists (user_id, name, kind) VALUES (?, ?, ?)", (user_id, name, kind))
    except sqlite3.IntegrityError:
        raise RuleError(f"Une liste « {name} » existe déjà") from None
    return get_list(conn, user_id, cursor.lastrowid)


def user_lists(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(f"{LIST_SUMMARY} WHERE l.user_id = ? GROUP BY l.id ORDER BY l.name COLLATE NOCASE", (user_id,))
    return [dict(row) for row in rows]


def get_list(conn: sqlite3.Connection, user_id: int, list_id: int) -> dict:
    row = conn.execute(f"{LIST_SUMMARY} WHERE l.id = ? AND l.user_id = ? GROUP BY l.id", (list_id, user_id)).fetchone()
    if row is None:
        raise NotFound("Liste introuvable")
    return dict(row)


def find_list(conn: sqlite3.Connection, user_id: int, name: str) -> dict:
    row = conn.execute(
        "SELECT id FROM lists WHERE user_id = ? AND name = ? COLLATE NOCASE", (user_id, name.strip())
    ).fetchone()
    if row is None:
        raise NotFound(f"Liste « {name} » introuvable")
    return get_list(conn, user_id, row["id"])


def rename_list(conn: sqlite3.Connection, user_id: int, list_id: int, name: str) -> dict:
    get_list(conn, user_id, list_id)
    name = _clean_name(name)
    try:
        with conn:
            conn.execute("UPDATE lists SET name = ? WHERE id = ?", (name, list_id))
    except sqlite3.IntegrityError:
        raise RuleError(f"Une liste « {name} » existe déjà") from None
    return get_list(conn, user_id, list_id)


def delete_list(conn: sqlite3.Connection, user_id: int, list_id: int) -> None:
    get_list(conn, user_id, list_id)
    with conn:
        conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))


def add_to_list(conn: sqlite3.Connection, user_id: int, list_id: int, card_id: str) -> None:
    card_list = get_list(conn, user_id, list_id)
    _available_variants(conn, card_id)  # raises NotFound for an unknown card
    if card_list["type"] == "collection" and not quantities(conn, user_id, card_id):
        raise RuleError("Seules les cartes possédées peuvent être ajoutées à une liste de collection")
    with conn:
        conn.execute("INSERT OR IGNORE INTO list_items (list_id, card_id) VALUES (?, ?)", (list_id, card_id))


def remove_from_list(conn: sqlite3.Connection, user_id: int, list_id: int, card_id: str) -> None:
    get_list(conn, user_id, list_id)
    with conn:
        conn.execute("DELETE FROM list_items WHERE list_id = ? AND card_id = ?", (list_id, card_id))


def lists_containing(conn: sqlite3.Connection, user_id: int, card_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT l.id, l.name AS nom, l.kind AS type FROM lists l JOIN list_items li ON li.list_id = l.id
           WHERE l.user_id = ? AND li.card_id = ? ORDER BY l.name COLLATE NOCASE""",
        (user_id, card_id),
    )
    return [dict(row) for row in rows]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/collection.py backend/tests/test_collection.py
git commit -m "KAN-5: Collection quantities and lists with their rules"
```

---

### Task 6: Sign-in and REST API

**Files:**
- Create: `backend/app/auth.py`, `backend/app/main.py`, `backend/app/chat.py` (stub replaced in Task 7)
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `db`, `catalog`, `collection` (Tasks 3-5).
- Produces: `create_app(db_path=None, catalog_path=None, static_dir=None, chat_client=None) -> FastAPI` (defaults from env `DB_PATH`, `CATALOG_PATH`, `STATIC_DIR`; run with `uvicorn --factory app.main:create_app`). Routes exactly as in the spec section 5. `chat.run_chat(conn, user_id: int, messages: list[dict], page: str | None, client) -> dict` and `chat.make_client()` are called by `POST /api/chat`; Task 7 implements them.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_api.py
def test_routes_require_sign_in(make_client):
    anonymous = make_client()
    assert anonymous.get("/api/cartes").status_code == 401
    assert anonymous.get("/api/moi").status_code == 401


def test_sign_in_and_out(make_client):
    session = make_client()
    bad = session.post("/api/connexion", json={"utilisateur": "user", "mot_de_passe": "faux"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Identifiants incorrects"
    ok = session.post("/api/connexion", json={"utilisateur": "user", "mot_de_passe": "user"})
    assert ok.json() == {"id": 1, "utilisateur": "user"}
    assert session.get("/api/moi").json() == {"id": 1, "utilisateur": "user"}
    session.post("/api/deconnexion")
    assert session.get("/api/moi").status_code == 401


def test_groups_and_cards(client):
    assert [g["valeur"] for g in client.get("/api/groupes", params={"par": "set"}).json()] == ["base1", "swsh3", "swsh4"]
    assert client.get("/api/groupes", params={"par": "prix"}).status_code == 422
    page = client.get("/api/cartes", params={"pokemon": 25, "tri": "pv:desc"}).json()
    assert page["total"] == 4 and page["cartes"][0]["id"] == "swsh4-188"
    assert client.get("/api/cartes", params={"tri": "prix:asc"}).json()["detail"] == "Tri invalide : prix:asc"


def test_card_with_question_mark_id(client):
    response = client.get("/api/cartes/swsh4-%3F")
    assert response.status_code == 200
    assert response.json()["nom"] == "Zarbi ?"
    assert response.json()["quantites"] == {} and response.json()["listes"] == []
    assert client.get("/api/cartes/nope-1").status_code == 404


def test_collection_routes(client):
    response = client.put("/api/collection/base1-4/holo", json={"quantite": 2})
    assert response.json() == {"quantites": {"holo": 2}}
    assert client.put("/api/collection/base1-4/reverse", json={"quantite": 1}).status_code == 400
    assert client.put("/api/collection/base1-4/holo", json={"quantite": -3}).status_code == 400
    owned = client.get("/api/collection").json()
    assert [(c["id"], c["quantite"]) for c in owned["cartes"]] == [("base1-4", 2)]
    assert client.get("/api/cartes/base1-4").json()["quantites"] == {"holo": 2}


def test_list_routes(client):
    created = client.post("/api/listes", json={"nom": "Favoris", "type": "souhaits"}).json()
    assert created["nom"] == "Favoris" and created["nombre"] == 0
    duplicate = client.post("/api/listes", json={"nom": "Favoris", "type": "souhaits"})
    assert duplicate.status_code == 400 and "existe déjà" in duplicate.json()["detail"]
    list_id = created["id"]
    assert client.post(f"/api/listes/{list_id}/cartes/swsh4-%3F").status_code == 200
    detail = client.get(f"/api/listes/{list_id}").json()
    assert detail["nombre"] == 1 and detail["cartes"]["cartes"][0]["id"] == "swsh4-?"
    assert client.patch(f"/api/listes/{list_id}", json={"nom": "Préférées"}).json()["nom"] == "Préférées"
    assert client.get("/api/listes").json()[0]["nom"] == "Préférées"
    assert client.delete(f"/api/listes/{list_id}/cartes/swsh4-%3F").status_code == 200
    assert client.delete(f"/api/listes/{list_id}").status_code == 200
    assert client.get(f"/api/listes/{list_id}").status_code == 404
    collection_list = client.post("/api/listes", json={"nom": "Classeur", "type": "collection"}).json()
    refused = client.post(f"/api/listes/{collection_list['id']}/cartes/base1-4")
    assert refused.status_code == 400


def test_chat_without_key_answers_unavailable(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Bonjour"}], "page": "/explorer/"})
    assert response.json() == {"reponse": "Le service IA est indisponible, réessayez.", "actions": []}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Write `app/auth.py`**

```python
import sqlite3

from fastapi import HTTPException, Request

# MVP: one hardcoded account. The users table already supports more.
USERNAME = "user"
PASSWORD = "user"


def login(conn: sqlite3.Connection, request: Request, username: str, password: str) -> dict:
    if username != USERNAME or password != PASSWORD:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    row = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
    request.session["user_id"] = row["id"]
    return {"id": row["id"], "utilisateur": row["username"]}


def current_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Non connecté")
    return user_id
```

- [ ] **Step 4: Write a minimal `app/chat.py` (completed in Task 7)**

```python
UNAVAILABLE = "Le service IA est indisponible, réessayez."


def make_client():
    return None


def run_chat(conn, user_id, messages, page, client) -> dict:
    return {"reponse": UNAVAILABLE, "actions": []}
```

- [ ] **Step 5: Write `app/main.py`**

```python
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app import auth, catalog, chat, collection, db
from app.errors import NotFound, RuleError

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Credentials(BaseModel):
    utilisateur: str
    mot_de_passe: str


class QuantityBody(BaseModel):
    quantite: int


class NewList(BaseModel):
    nom: str
    type: collection.ListKind


class ListName(BaseModel):
    nom: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    page: str | None = None


def create_app(db_path: str | None = None, catalog_path: str | None = None,
               static_dir: str | None = None, chat_client=None) -> FastAPI:
    db_path = db_path or os.environ.get("DB_PATH", str(BACKEND_DIR / "tcg.db"))
    catalog_path = catalog_path or os.environ.get("CATALOG_PATH", str(BACKEND_DIR / "data" / "catalog.json.gz"))
    static_dir = static_dir or os.environ.get("STATIC_DIR", str(BACKEND_DIR / "static"))
    db.init_db(db_path, catalog_path)

    app = FastAPI(title="TCG-exemple")
    app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET") or secrets.token_hex(32))

    @app.exception_handler(NotFound)
    def not_found(request: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RuleError)
    def rule_error(request: Request, exc: RuleError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def get_conn():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
    User = Annotated[int, Depends(auth.current_user)]

    @app.post("/api/connexion")
    def sign_in(body: Credentials, request: Request, conn: Conn):
        return auth.login(conn, request, body.utilisateur, body.mot_de_passe)

    @app.post("/api/deconnexion")
    def sign_out(request: Request):
        request.session.clear()
        return {}

    @app.get("/api/moi")
    def me(user: User, conn: Conn):
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user,)).fetchone()
        return {"id": row["id"], "utilisateur": row["username"]}

    @app.get("/api/groupes")
    def groups(par: catalog.GroupBy, user: User, conn: Conn):
        return catalog.list_groups(conn, par)

    @app.get("/api/cartes")
    def cards(user: User, conn: Conn, set: str | None = None, pokemon: int | None = None,
              illustrateur: str | None = None, rarete: str | None = None, type: str | None = None,
              q: str | None = None, tri: str | None = None, page: int = 1):
        filters = catalog.Filters(set=set, pokemon=pokemon, illustrateur=illustrateur, rarete=rarete, type=type, q=q)
        return catalog.search_cards(conn, filters, tri, page, user_id=user)

    @app.get("/api/cartes/{card_id}")
    def card(card_id: str, user: User, conn: Conn):
        return {
            **catalog.get_card(conn, card_id),
            "quantites": collection.quantities(conn, user, card_id),
            "listes": collection.lists_containing(conn, user, card_id),
        }

    @app.get("/api/collection")
    def my_collection(user: User, conn: Conn, tri: str | None = None, page: int = 1):
        return catalog.search_cards(conn, catalog.Filters(proprietaire=user), tri, page, user_id=user)

    @app.put("/api/collection/{card_id}/{variant}")
    def set_quantity(card_id: str, variant: str, body: QuantityBody, user: User, conn: Conn):
        return {"quantites": collection.set_quantity(conn, user, card_id, variant, body.quantite)}

    @app.get("/api/listes")
    def lists(user: User, conn: Conn):
        return collection.user_lists(conn, user)

    @app.post("/api/listes")
    def create_list(body: NewList, user: User, conn: Conn):
        return collection.create_list(conn, user, body.nom, body.type)

    @app.get("/api/listes/{list_id}")
    def get_list(list_id: int, user: User, conn: Conn, tri: str | None = None, page: int = 1):
        summary = collection.get_list(conn, user, list_id)
        return {**summary, "cartes": catalog.search_cards(conn, catalog.Filters(liste=list_id), tri, page, user_id=user)}

    @app.patch("/api/listes/{list_id}")
    def rename_list(list_id: int, body: ListName, user: User, conn: Conn):
        return collection.rename_list(conn, user, list_id, body.nom)

    @app.delete("/api/listes/{list_id}")
    def delete_list(list_id: int, user: User, conn: Conn):
        collection.delete_list(conn, user, list_id)
        return {}

    @app.post("/api/listes/{list_id}/cartes/{card_id}")
    def add_to_list(list_id: int, card_id: str, user: User, conn: Conn):
        collection.add_to_list(conn, user, list_id, card_id)
        return {}

    @app.delete("/api/listes/{list_id}/cartes/{card_id}")
    def remove_from_list(list_id: int, card_id: str, user: User, conn: Conn):
        collection.remove_from_list(conn, user, list_id, card_id)
        return {}

    @app.post("/api/chat")
    def chat_route(body: ChatRequest, user: User, conn: Conn):
        client = chat_client or chat.make_client()
        messages = [m.model_dump() for m in body.messages[-20:]]
        return chat.run_chat(conn, user, messages, body.page, client)

    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 7: Smoke-test the real server**

Run: `cd backend && uv run uvicorn --factory app.main:create_app --port 8000` then, in another shell:
`curl -s -c /tmp/c -H "Content-Type: application/json" -d '{"utilisateur":"user","mot_de_passe":"user"}' http://localhost:8000/api/connexion && curl -s -b /tmp/c "http://localhost:8000/api/cartes?q=dracaufeu&tri=pv:desc" | head -c 400`
Expected: `{"id":1,"utilisateur":"user"}`, then JSON with French Dracaufeu cards from the real snapshot. Stop the server.

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests/test_api.py
git commit -m "KAN-5: Sign-in and REST API"
```

---

### Task 7: AI tools and chat loop

**Files:**
- Create: `backend/app/tools.py`
- Modify: `backend/app/chat.py` (replace the Task 6 stub entirely)
- Test: `backend/tests/test_tools.py`, `backend/tests/test_chat.py`

**Interfaces:**
- Consumes: `catalog.search_cards`, `catalog.list_groups`, `catalog.parse_sort`, `collection.add_copies`, `collection.remove_copies`, `collection.create_list`, `collection.find_list`, `collection.add_to_list`.
- Produces: `tools.TOOL_SCHEMAS: list[dict]` (OpenAI function format), `tools.run_tool(conn, user_id, name: str, arguments: str, actions: list[dict]) -> str` (JSON text); actions are `{"type": "naviguer", "url": str}` or `{"type": "rafraichir", "cible": "collection" | "listes"}`. `chat.run_chat(conn, user_id, messages, page, client) -> {"reponse": str, "actions": list[dict]}`, `chat.make_client() -> openai.OpenAI | None`, `chat.UNAVAILABLE`, `chat.MODEL`.

- [ ] **Step 1: Write the failing tool tests**

```python
# backend/tests/test_tools.py
import json

from app import collection, tools


def run(conn, name, args, actions=None):
    actions = [] if actions is None else actions
    return json.loads(tools.run_tool(conn, 1, name, json.dumps(args), actions)), actions


def test_schemas_list_every_tool():
    names = [schema["function"]["name"] for schema in tools.TOOL_SCHEMAS]
    assert names == ["chercher_cartes", "lister_groupes", "ajouter_collection", "retirer_collection",
                     "creer_liste", "ajouter_a_liste", "afficher_navigation"]
    assert all(schema["function"]["description"] for schema in tools.TOOL_SCHEMAS)


def test_chercher_cartes(conn):
    result, actions = run(conn, "chercher_cartes", {"nom": "pikachu", "tri": "pv:desc", "limite": 2})
    assert result["total"] == 4
    assert result["cartes"] == [
        {"id": "swsh4-188", "nom": "Pikachu VMAX", "set_nom": "Voltage Éclatant", "numero": "188", "rarete": "Ultra Rare", "quantite": 0},
        {"id": "swsh4-200", "nom": "Pikachu et Zekrom GX", "set_nom": "Voltage Éclatant", "numero": "200", "rarete": "Ultra Rare", "quantite": 0},
    ]
    assert actions == []


def test_lister_groupes_matches_without_accents(conn):
    result, _ = run(conn, "lister_groupes", {"par": "set", "filtre": "voltage eclatant"})
    assert [g["valeur"] for g in result["groupes"]] == ["swsh4"]


def test_ajouter_et_retirer_collection(conn):
    result, actions = run(conn, "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse", "quantite": 2})
    assert result == {"quantites": {"reverse": 2}}
    assert actions == [{"type": "rafraichir", "cible": "collection"}]
    result, _ = run(conn, "retirer_collection", {"card_id": "swsh3-136", "variante": "reverse"})
    assert result == {"quantites": {"reverse": 1}}


def test_creer_liste_et_ajouter(conn):
    collection.add_copies(conn, 1, "base1-4", "holo", 1)
    result, actions = run(conn, "creer_liste", {"nom": "Classeur", "type": "collection"})
    assert result["nom"] == "Classeur"
    result, actions = run(conn, "ajouter_a_liste", {"liste": "classeur", "card_ids": ["base1-4", "swsh3-20", "nope-1"]})
    assert result["ajoutees"] == ["base1-4"]
    assert set(result["erreurs"]) == {"swsh3-20", "nope-1"}
    assert actions == [{"type": "rafraichir", "cible": "listes"}]


def test_afficher_navigation(conn):
    result, actions = run(conn, "afficher_navigation", {"par": "illustrateur", "illustrateur": "Ken Sugimori", "tri": "pv:desc"})
    assert result["url"] == "/explorer/?par=illustrateur&illustrateur=Ken+Sugimori&tri=pv%3Adesc"
    assert actions == [{"type": "naviguer", "url": result["url"]}]


def test_run_tool_reports_errors_to_the_model(conn):
    actions = []
    assert "Outil inconnu" in json.loads(tools.run_tool(conn, 1, "vendre", "{}", actions))["erreur"]
    assert "Arguments invalides" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", "{pas du json", actions))["erreur"]
    assert "Arguments invalides" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "base1-4", "quantite": 0}', actions))["erreur"]
    assert json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "nope-1"}', actions)) == {"erreur": "Carte introuvable"}
    assert "Variante" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "base1-4"}', actions))["erreur"]
    assert "Tri invalide" in json.loads(tools.run_tool(conn, 1, "afficher_navigation", '{"tri": "prix"}', actions))["erreur"]
    assert actions == []
```

- [ ] **Step 2: Write the failing chat tests**

```python
# backend/tests/test_chat.py
import json
from types import SimpleNamespace

import httpx
import openai

from app import chat, collection


def reply(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))])


def tool_call(call_id, name, args):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def fake_client(*responses):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        response = responses[min(len(calls), len(responses)) - 1]
        if isinstance(response, Exception):
            raise response
        return response

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


USER_MESSAGE = [{"role": "user", "content": "Ajoute deux Fouinar reverse"}]


def test_no_client_means_unavailable(conn):
    assert chat.run_chat(conn, 1, USER_MESSAGE, "/explorer/", None) == {"reponse": chat.UNAVAILABLE, "actions": []}


def test_plain_answer_sends_prompt_page_and_tools(conn):
    client, calls = fake_client(reply("Bonjour !"))
    assert chat.run_chat(conn, 1, USER_MESSAGE, "/collection/", client) == {"reponse": "Bonjour !", "actions": []}
    sent = calls[0]
    assert sent["model"] == chat.MODEL
    assert sent["messages"][0]["role"] == "system" and "/collection/" in sent["messages"][0]["content"]
    assert sent["messages"][1:] == USER_MESSAGE
    assert len(sent["tools"]) == 7


def test_tool_round_trip_updates_collection(conn):
    client, calls = fake_client(
        reply(tool_calls=[tool_call("c1", "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse", "quantite": 2})]),
        reply("Deux Fouinar reverse ajoutés."),
    )
    result = chat.run_chat(conn, 1, USER_MESSAGE, None, client)
    assert result == {"reponse": "Deux Fouinar reverse ajoutés.", "actions": [{"type": "rafraichir", "cible": "collection"}]}
    assert collection.quantities(conn, 1, "swsh3-136") == {"reverse": 2}
    second = calls[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-2]["tool_calls"][0]["id"] == "c1"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"quantites": {"reverse": 2}}'}


def test_duplicate_actions_are_merged(conn):
    calls_twice = [tool_call("c1", "ajouter_collection", {"card_id": "swsh3-136", "variante": "normal"}),
                   tool_call("c2", "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse"})]
    client, _ = fake_client(reply(tool_calls=calls_twice), reply("Fait."))
    assert chat.run_chat(conn, 1, USER_MESSAGE, None, client)["actions"] == [{"type": "rafraichir", "cible": "collection"}]


def test_api_error_or_timeout_means_unavailable(conn):
    timeout = openai.APITimeoutError(request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    client, _ = fake_client(timeout)
    assert chat.run_chat(conn, 1, USER_MESSAGE, None, client)["reponse"] == chat.UNAVAILABLE


def test_stops_after_max_rounds(conn):
    looping = reply(tool_calls=[tool_call("c", "chercher_cartes", {"nom": "pikachu"})])
    client, calls = fake_client(looping)
    result = chat.run_chat(conn, 1, USER_MESSAGE, None, client)
    assert len(calls) == chat.MAX_ROUNDS
    assert result["reponse"] == "Je n'ai pas pu terminer cette demande, essayez de la reformuler."
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_tools.py tests/test_chat.py -v`
Expected: FAIL with `ImportError: cannot import name 'tools' from 'app'` and `AttributeError: module 'app.chat' has no attribute 'MODEL'`.

- [ ] **Step 4: Write `app/tools.py`**

```python
import json
import sqlite3
from urllib.parse import urlencode

from pydantic import BaseModel, Field, ValidationError

from app import catalog, collection
from app.errors import NotFound, RuleError
from app.text import normalize

REFRESH_COLLECTION = {"type": "rafraichir", "cible": "collection"}
REFRESH_LISTS = {"type": "rafraichir", "cible": "listes"}


class ChercherCartes(BaseModel):
    """Chercher des cartes dans le catalogue (20 au maximum)."""

    nom: str | None = Field(None, description="Partie du nom de la carte, ex. dracaufeu")
    set: str | None = Field(None, description="Identifiant d'extension, ex. swsh3 (voir lister_groupes)")
    pokemon: int | None = Field(None, description="Numéro de Pokédex national, ex. 25")
    illustrateur: str | None = None
    rarete: str | None = Field(None, description="Rareté exacte, ex. Ultra Rare (voir lister_groupes)")
    type: str | None = Field(None, description="Type en français, ex. Feu, Eau, Électrique")
    tri: str | None = Field(None, description="Tri, ex. pv:desc,nom:asc")
    limite: int = Field(10, ge=1, le=20)


class ListerGroupes(BaseModel):
    """Trouver des extensions, Pokémon, illustrateurs ou raretés par leur nom."""

    par: catalog.GroupBy
    filtre: str | None = Field(None, description="Partie du nom recherché")


class ModifierCollection(BaseModel):
    card_id: str = Field(description="Identifiant de carte, ex. swsh3-136")
    variante: collection.Variant = "normal"
    quantite: int = Field(1, ge=1, le=100)


class AjouterCollection(ModifierCollection):
    """Ajouter des exemplaires d'une carte à la collection de l'utilisateur."""


class RetirerCollection(ModifierCollection):
    """Retirer des exemplaires d'une carte de la collection de l'utilisateur."""


class CreerListe(BaseModel):
    """Créer une liste : 'collection' (cartes possédées) ou 'souhaits' (n'importe quelle carte)."""

    nom: str
    type: collection.ListKind


class AjouterAListe(BaseModel):
    """Ajouter des cartes à une liste existante, désignée par son nom."""

    liste: str
    card_ids: list[str] = Field(min_length=1, max_length=50)


class AfficherNavigation(BaseModel):
    """Afficher des cartes dans la page Explorer avec ces filtres et ce tri."""

    par: catalog.GroupBy = Field("set", description="Onglet affiché")
    set: str | None = None
    pokemon: int | None = None
    illustrateur: str | None = None
    rarete: str | None = None
    type: str | None = None
    q: str | None = Field(None, description="Recherche par nom")
    tri: str | None = None


def chercher_cartes(conn, user_id, args: ChercherCartes, actions):
    filters = catalog.Filters(set=args.set, pokemon=args.pokemon, illustrateur=args.illustrateur,
                              rarete=args.rarete, type=args.type, q=args.nom)
    result = catalog.search_cards(conn, filters, args.tri, 1, user_id, page_size=args.limite)
    keys = ("id", "nom", "set_nom", "numero", "rarete", "quantite")
    return {"total": result["total"], "cartes": [{k: card[k] for k in keys} for card in result["cartes"]]}


def lister_groupes(conn, user_id, args: ListerGroupes, actions):
    groups = catalog.list_groups(conn, args.par)
    if args.filtre:
        needle = normalize(args.filtre)
        groups = [g for g in groups if needle in normalize(g["nom"])]
    return {"total": len(groups), "groupes": groups[:20]}


def ajouter_collection(conn, user_id, args: AjouterCollection, actions):
    result = collection.add_copies(conn, user_id, args.card_id, args.variante, args.quantite)
    actions.append(REFRESH_COLLECTION)
    return {"quantites": result}


def retirer_collection(conn, user_id, args: RetirerCollection, actions):
    result = collection.remove_copies(conn, user_id, args.card_id, args.variante, args.quantite)
    actions.append(REFRESH_COLLECTION)
    return {"quantites": result}


def creer_liste(conn, user_id, args: CreerListe, actions):
    result = collection.create_list(conn, user_id, args.nom, args.type)
    actions.append(REFRESH_LISTS)
    return result


def ajouter_a_liste(conn, user_id, args: AjouterAListe, actions):
    card_list = collection.find_list(conn, user_id, args.liste)
    added, errors = [], {}
    for card_id in args.card_ids:
        try:
            collection.add_to_list(conn, user_id, card_list["id"], card_id)
            added.append(card_id)
        except (NotFound, RuleError) as exc:
            errors[card_id] = str(exc)
    if added:
        actions.append(REFRESH_LISTS)
    return {"ajoutees": added, "erreurs": errors}


def afficher_navigation(conn, user_id, args: AfficherNavigation, actions):
    catalog.parse_sort(args.tri)  # raises RuleError before the page gets a bad sort
    params = {key: value for key, value in args.model_dump().items() if value is not None}
    url = "/explorer/?" + urlencode(params)
    actions.append({"type": "naviguer", "url": url})
    return {"url": url}


TOOLS = {
    "chercher_cartes": (ChercherCartes, chercher_cartes),
    "lister_groupes": (ListerGroupes, lister_groupes),
    "ajouter_collection": (AjouterCollection, ajouter_collection),
    "retirer_collection": (RetirerCollection, retirer_collection),
    "creer_liste": (CreerListe, creer_liste),
    "ajouter_a_liste": (AjouterAListe, ajouter_a_liste),
    "afficher_navigation": (AfficherNavigation, afficher_navigation),
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": name, "description": model.__doc__, "parameters": model.model_json_schema()}}
    for name, (model, _) in TOOLS.items()
]


def run_tool(conn: sqlite3.Connection, user_id: int, name: str, arguments: str, actions: list[dict]) -> str:
    """Run one tool call; errors are returned to the model as text so it can correct itself."""
    if name not in TOOLS:
        return json.dumps({"erreur": f"Outil inconnu : {name}"}, ensure_ascii=False)
    model, function = TOOLS[name]
    try:
        result = function(conn, user_id, model.model_validate_json(arguments or "{}"), actions)
    except ValidationError as exc:
        result = {"erreur": f"Arguments invalides : {exc.errors(include_url=False, include_context=False)}"}
    except (NotFound, RuleError) as exc:
        result = {"erreur": str(exc)}
    return json.dumps(result, ensure_ascii=False, default=str)
```

Note on `test_creer_liste_et_ajouter`: `swsh3-20` fails because the list is of kind `collection` and the card is not owned; `nope-1` fails with "Carte introuvable". `run()` gives each call a fresh actions list, so the `ajouter_a_liste` call holds one `rafraichir` action.

- [ ] **Step 5: Replace `app/chat.py`**

```python
import os
import sqlite3

import openai

from app import tools

MODEL = "openai/gpt-oss-120b"
MAX_ROUNDS = 5
UNAVAILABLE = "Le service IA est indisponible, réessayez."
GAVE_UP = "Je n'ai pas pu terminer cette demande, essayez de la reformuler."

SYSTEM_PROMPT = """Tu es l'assistant de TCG-exemple, une application de collection de cartes Pokémon en français.
Réponds toujours en français, en une ou deux phrases.
Utilise les outils pour chercher des cartes, gérer la collection et les listes de l'utilisateur, et changer l'affichage de la page Explorer.
Avant d'ajouter ou de retirer une carte, trouve son identifiant avec chercher_cartes. Si plusieurs cartes correspondent, ne devine pas : demande laquelle, ou montre-les avec afficher_navigation.
Pour trouver l'identifiant d'une extension, le numéro d'un Pokémon, un illustrateur ou une rareté, utilise lister_groupes.
Quand l'utilisateur veut voir ou trier des cartes, utilise afficher_navigation.
Tris possibles : nom, pokedex, pv, rarete, illustrateur, date_sortie, numero, chacun suivi de :asc ou :desc, séparés par des virgules."""


def make_client() -> openai.OpenAI | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    return openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=30, max_retries=1)


def _unique(actions: list[dict]) -> list[dict]:
    return [action for i, action in enumerate(actions) if action not in actions[:i]]


def run_chat(conn: sqlite3.Connection, user_id: int, messages: list[dict], page: str | None, client) -> dict:
    if client is None:
        return {"reponse": UNAVAILABLE, "actions": []}
    history = [{"role": "system", "content": f"{SYSTEM_PROMPT}\nPage actuelle : {page or 'inconnue'}"}, *messages]
    actions: list[dict] = []
    try:
        for _ in range(MAX_ROUNDS):
            message = client.chat.completions.create(
                model=MODEL, messages=history, tools=tools.TOOL_SCHEMAS
            ).choices[0].message
            if not message.tool_calls:
                return {"reponse": message.content or "", "actions": _unique(actions)}
            history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {"id": call.id, "type": "function",
                     "function": {"name": call.function.name, "arguments": call.function.arguments}}
                    for call in message.tool_calls
                ],
            })
            for call in message.tool_calls:
                result = tools.run_tool(conn, user_id, call.function.name, call.function.arguments, actions)
                history.append({"role": "tool", "tool_call_id": call.id, "content": result})
    except openai.APIError:
        return {"reponse": UNAVAILABLE, "actions": _unique(actions)}
    return {"reponse": GAVE_UP, "actions": _unique(actions)}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && uv run pytest -v`
Expected: all pass.

- [ ] **Step 7: Try one real call**

With `OPENROUTER_API_KEY` set from the root `.env` (bash: `set -a; . ../.env; set +a`), run:
`cd backend && uv run python -c "from app import db, chat; db.init_db('tcg.db','data/catalog.json.gz'); c=db.connect('tcg.db'); print(chat.run_chat(c,1,[{'role':'user','content':'Montre les cartes de Ken Sugimori triées par PV décroissants'}],'/explorer/',chat.make_client()))"`
Expected: a French reply and a `naviguer` action whose URL contains `illustrateur=Ken+Sugimori` and `tri=pv%3Adesc`. If the model never calls tools, check the OpenRouter response for errors before changing the prompt.

- [ ] **Step 8: Commit**

```bash
git add backend/app/tools.py backend/app/chat.py backend/tests/test_tools.py backend/tests/test_chat.py
git commit -m "KAN-5: AI chat tools and OpenRouter loop"
```

---

### Task 8: Frontend project, API client and sign-in page

**Files:**
- Create: `frontend/` via create-next-app; `frontend/next.config.ts`, `frontend/vitest.config.ts`, `frontend/app/globals.css`, `frontend/app/layout.tsx`, `frontend/app/page.tsx`, `frontend/app/connexion/page.tsx`, `frontend/lib/types.ts`, `frontend/lib/api.ts`, `frontend/lib/query.ts`, `frontend/lib/text.ts`
- Test: `frontend/lib/api.test.ts`

**Interfaces:**
- Consumes: the API from Task 6.
- Produces: `api<T>(path: string, options?: { method?: string; body?: unknown }): Promise<T>`; `ApiError`; `navigation.toLogin()`; `cardPath(id: string): string`; `toQuery(values: Record<string, string | number | undefined>): string` (`""` or `"?a=b"`); `normalize(text: string): string`; types `CardSummary`, `CardPage`, `Group`, `ListKind`, `CardList`, `CardDetail`, `ChatAction`, `ChatMessage`, `RefreshTarget`, `VARIANT_LABELS`.

- [ ] **Step 1: Create the app**

From the repo root:

```bash
npx create-next-app@16 frontend --typescript --eslint --app --no-src-dir --no-tailwind --import-alias "@/*" --use-npm --yes
cd frontend
rm -f app/page.module.css public/*.svg
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom
npm pkg set scripts.test="vitest run"
```

If create-next-app still asks a question, accept its default.

- [ ] **Step 2: Configure Next.js and Vitest**

```ts
// frontend/next.config.ts
import type { NextConfig } from "next";

// Production: static files served by FastAPI. Development: proxy /api to the backend on :8000.
const nextConfig: NextConfig =
  process.env.NODE_ENV === "development"
    ? {
        async rewrites() {
          return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
        },
      }
    : { output: "export", trailingSlash: true, images: { unoptimized: true } };

export default nextConfig;
```

```ts
// frontend/vitest.config.ts
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom" },
  resolve: { alias: { "@": fileURLToPath(new URL(".", import.meta.url)) } },
});
```

- [ ] **Step 3: Write the shared types and helpers**

```ts
// frontend/lib/types.ts
export type CardSummary = {
  id: string;
  nom: string;
  set_id: string;
  set_nom: string;
  numero: string;
  rarete: string | null;
  illustrateur: string | null;
  pv: number | null;
  image: string | null;
  quantite: number;
};

export type CardPage = { cartes: CardSummary[]; total: number; page: number; pages: number };

export type Group = { valeur: string; nom: string; nombre: number; groupe: string | null; image: string | null };

export type ListKind = "collection" | "souhaits";

export type CardList = { id: number; nom: string; type: ListKind; nombre: number };

export type Attack = { name: string; cost?: string[]; damage?: number | string; effect?: string };

export type CardDetail = {
  id: string;
  nom: string;
  set_id: string;
  set_nom: string;
  serie_nom: string;
  date_sortie: string | null;
  numero: string;
  categorie: string;
  rarete: string | null;
  illustrateur: string | null;
  pv: number | null;
  types: string[];
  stade: string | null;
  image: string | null;
  variantes: string[];
  details: { attacks?: Attack[]; abilities?: { name: string; effect: string }[]; effect?: string; description?: string };
  pokemon: { dex_id: number; nom: string }[];
  quantites: Record<string, number>;
  listes: { id: number; nom: string; type: ListKind }[];
};

export type RefreshTarget = "collection" | "listes";

export type ChatAction = { type: "naviguer"; url: string } | { type: "rafraichir"; cible: RefreshTarget };

export type ChatMessage = { role: "user" | "assistant"; content: string };

export const VARIANT_LABELS: Record<string, string> = {
  normal: "Normale",
  reverse: "Reverse",
  holo: "Holo",
  firstEdition: "1re édition",
  wPromo: "Promo W",
};

export const LIST_KIND_LABELS: Record<ListKind, string> = { collection: "Collection", souhaits: "Recherchées" };
```

```ts
// frontend/lib/query.ts
export function toQuery(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}
```

```ts
// frontend/lib/text.ts
export function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();
}
```

- [ ] **Step 4: Write the failing API client tests**

```ts
// frontend/lib/api.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, cardPath, navigation } from "./api";

function respond(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api", () => {
  it("returns the JSON body", async () => {
    respond(200, { total: 3 });
    await expect(api("/api/cartes")).resolves.toEqual({ total: 3 });
  });

  it("sends JSON bodies", async () => {
    respond(200, {});
    await api("/api/listes", { method: "POST", body: { nom: "Favoris" } });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe('{"nom":"Favoris"}');
  });

  it("throws the French detail on errors", async () => {
    respond(400, { detail: "Une liste « Favoris » existe déjà" });
    await expect(api("/api/listes")).rejects.toThrow(new ApiError("Une liste « Favoris » existe déjà"));
  });

  it("sends the user to the sign-in page on 401", async () => {
    const toLogin = vi.spyOn(navigation, "toLogin").mockImplementation(() => {});
    respond(401, { detail: "Non connecté" });
    await expect(api("/api/cartes")).rejects.toThrow("Non connecté");
    expect(toLogin).toHaveBeenCalled();
  });

  it("does not redirect when the sign-in itself fails", async () => {
    const toLogin = vi.spyOn(navigation, "toLogin").mockImplementation(() => {});
    respond(401, { detail: "Identifiants incorrects" });
    await expect(api("/api/connexion", { method: "POST", body: {} })).rejects.toThrow("Identifiants incorrects");
    expect(toLogin).not.toHaveBeenCalled();
  });
});

describe("cardPath", () => {
  it("encodes ids with question marks", () => {
    expect(cardPath("swsh4-?")).toBe("/api/cartes/swsh4-%3F");
  });
});
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL with `Failed to resolve import "./api"`.

- [ ] **Step 6: Write `lib/api.ts`**

```ts
// frontend/lib/api.ts
export class ApiError extends Error {}

export const navigation = {
  toLogin() {
    window.location.assign("/connexion/");
  },
};

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const hasBody = options.body !== undefined;
  const response = await fetch(path, {
    method: options.method ?? "GET",
    credentials: "same-origin",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    body: hasBody ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => ({}));
  if (response.ok) return data as T;
  const detail = typeof data.detail === "string" ? data.detail : "Requête invalide";
  if (response.status === 401 && path !== "/api/connexion") navigation.toLogin();
  throw new ApiError(detail);
}

export const cardPath = (id: string) => `/api/cartes/${encodeURIComponent(id)}`;
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd frontend && npm test`
Expected: 6 passed.

- [ ] **Step 8: Write the global styles, root layout, home redirect and sign-in page**

```css
/* frontend/app/globals.css */
:root {
  --grey: #f3f3ed;
  --dark: #515151;
  --blue: #5d5c8e;
  --red: #e78a78;
  --green: #70bc94;
  --yellow: #f1d3ac;
  --white: #ffffff;
  --radius: 8px;
}

* { box-sizing: border-box; }
body { margin: 0; background: var(--grey); color: var(--dark); font-family: system-ui, sans-serif; }
a { color: var(--blue); text-decoration: none; }
h1, h2, h3 { color: var(--dark); }
button { font: inherit; cursor: pointer; }

.button { background: var(--blue); color: var(--white); border: 0; border-radius: var(--radius); padding: 0.5rem 1rem; }
.button.secondary { background: var(--white); color: var(--blue); border: 1px solid var(--blue); }
.button.danger { background: var(--red); }
.button:disabled { opacity: 0.5; cursor: default; }
.input, select { border: 1px solid #ccc; border-radius: var(--radius); padding: 0.5rem; font: inherit; background: var(--white); }
.error { color: var(--red); }
.muted { color: #888; }
.empty { color: #888; padding: 2rem 0; }

.login { max-width: 22rem; margin: 15vh auto; background: var(--white); padding: 2rem; border-radius: var(--radius); display: grid; gap: 0.75rem; border-top: 6px solid var(--yellow); }

.shell { min-height: 100vh; display: grid; grid-template-rows: auto 1fr auto; }
.header { display: flex; align-items: center; gap: 2rem; padding: 0.75rem 1.5rem; background: var(--blue); }
.header .brand { color: var(--white); font-weight: 700; font-size: 1.2rem; }
.header nav { display: flex; gap: 1rem; flex: 1; }
.header nav a { color: var(--grey); padding: 0.25rem 0.5rem; border-radius: var(--radius); }
.header nav a.active { background: var(--yellow); color: var(--dark); }
.body { display: flex; min-height: 0; }
.main { flex: 1; padding: 1.5rem; min-width: 0; }
.footer { padding: 1rem 1.5rem; font-size: 0.8rem; color: #888; border-top: 1px solid #ddd; }

.tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
.tab { background: var(--white); border: 1px solid var(--blue); color: var(--blue); border-radius: 999px; padding: 0.35rem 0.9rem; }
.tab.active { background: var(--blue); color: var(--white); }
.toolbar { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin: 1rem 0; }
.chips { display: flex; gap: 0.5rem; flex: 1; flex-wrap: wrap; }
.chip { background: var(--yellow); border: 0; border-radius: 999px; padding: 0.25rem 0.75rem; }

.group-list { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); gap: 0.5rem; }
.group-heading { grid-column: 1 / -1; margin: 1rem 0 0; font-size: 1rem; }
.group-item { width: 100%; text-align: left; background: var(--white); border: 1px solid #ddd; border-radius: var(--radius); padding: 0.6rem; display: flex; justify-content: space-between; gap: 0.5rem; }
.group-item:hover { border-color: var(--blue); }

.card-grid { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr)); gap: 1rem; }
.card-tile { display: grid; gap: 0.25rem; background: var(--white); border-radius: var(--radius); padding: 0.5rem; color: var(--dark); position: relative; }
.card-tile:hover { outline: 2px solid var(--blue); }
.card-name { font-weight: 600; }
.card-meta { font-size: 0.8rem; color: #888; }
.owned { position: absolute; top: 0.75rem; right: 0.75rem; background: var(--green); color: var(--white); border-radius: 999px; padding: 0.1rem 0.5rem; font-size: 0.8rem; }
.card-img.low, .card-placeholder.low { width: 100%; aspect-ratio: 245 / 337; border-radius: 6px; }
.card-img.high, .card-placeholder.high { width: 100%; max-width: 24rem; aspect-ratio: 600 / 825; border-radius: 12px; }
.card-placeholder { display: grid; place-items: center; background: var(--grey); color: #888; font-size: 0.8rem; text-align: center; }

.pagination { display: flex; gap: 1rem; align-items: center; justify-content: center; margin: 1.5rem 0; }

.card-detail { display: grid; grid-template-columns: minmax(16rem, 24rem) 1fr; gap: 2rem; }
.panel { background: var(--white); border-radius: var(--radius); padding: 1rem; margin-bottom: 1rem; }
.facts { display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; }
.variant-row { display: flex; align-items: center; gap: 0.75rem; margin: 0.35rem 0; }
.variant-row .label { width: 7rem; }

.lists { list-style: none; padding: 0; display: grid; gap: 0.5rem; }
.list-row { display: flex; align-items: center; gap: 1rem; background: var(--white); border-radius: var(--radius); padding: 0.75rem 1rem; }
.list-row a { flex: 1; font-weight: 600; }
.form-row { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 1rem 0; }

.chat { width: 22rem; border-left: 1px solid #ddd; background: var(--white); display: flex; flex-direction: column; height: calc(100vh - 3.5rem); position: sticky; top: 0; }
.chat.closed { width: auto; }
.chat-header { display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1rem; border-bottom: 1px solid #ddd; }
.chat-messages { flex: 1; overflow-y: auto; padding: 1rem; display: grid; gap: 0.5rem; align-content: start; }
.message { padding: 0.5rem 0.75rem; border-radius: var(--radius); white-space: pre-wrap; }
.message.user { background: var(--yellow); justify-self: end; }
.message.assistant { background: var(--grey); justify-self: start; }
.chat-form { display: flex; gap: 0.5rem; padding: 0.75rem; border-top: 1px solid #ddd; }
.chat-form .input { flex: 1; }
```

```tsx
// frontend/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "TCG-exemple", description: "Collection de cartes Pokémon" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
```

```tsx
// frontend/app/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const router = useRouter();
  useEffect(() => router.replace("/explorer/"), [router]);
  return null;
}
```

```tsx
// frontend/app/connexion/page.tsx
"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";

export default function SignInPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/connexion", { method: "POST", body: { utilisateur: username, mot_de_passe: password } });
      router.push("/explorer/");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form className="login" onSubmit={submit}>
      <h1>TCG-exemple</h1>
      <input className="input" placeholder="Utilisateur" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
      <input className="input" placeholder="Mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="error">{error}</p>}
      <button className="button" type="submit">Se connecter</button>
    </form>
  );
}
```

- [ ] **Step 9: Build and check**

Run: `cd frontend && npm run build && npm run lint`
Expected: build succeeds and writes `out/connexion/index.html`; lint has no errors.

- [ ] **Step 10: Commit**

```bash
git add frontend
git commit -m "KAN-5: Next.js frontend, API client and sign-in page"
```

---

### Task 9: App shell and explorer

**Files:**
- Create: `frontend/lib/explorer.ts`, `frontend/lib/chat.ts` (only `REFRESH_EVENT` in this task), `frontend/lib/useApi.ts`, `frontend/components/Header.tsx`, `frontend/components/CardImage.tsx`, `frontend/components/CardGrid.tsx`, `frontend/components/Pagination.tsx`, `frontend/components/SortSelect.tsx`, `frontend/app/(app)/layout.tsx`, `frontend/app/(app)/explorer/page.tsx`
- Test: `frontend/lib/explorer.test.ts`, `frontend/components/CardImage.test.tsx`

**Interfaces:**
- Consumes: `api`, `toQuery`, `normalize`, types (Task 8).
- Produces: `GroupBy`, `GROUP_TABS`, `FILTER_KEYS`, `FilterKey`, `ExplorerState = { par: GroupBy; filters: Partial<Record<FilterKey, string>>; tri: string; page: number }`, `parseExplorer(params: URLSearchParams): ExplorerState`, `explorerUrl(state): string`, `cardsApiUrl(state): string`, `hasFilters(state): boolean`, `FILTER_LABELS`, `SORT_OPTIONS`; `REFRESH_EVENT = "tcg:rafraichir"`; `useApi<T>(url: string | null, refreshOn?: RefreshTarget[]): { data: T | null; error: string | null; reload: () => void }`; components `CardImage({ base, alt, quality })`, `CardGrid({ cards, renderAction? })`, `Pagination({ page, pages, onPage })`, `SortSelect({ value, onChange })`. The `(app)` layout renders a `ChatPanel` slot that Task 12 fills; until then it renders no panel.

- [ ] **Step 1: Write the failing explorer and image tests**

```ts
// frontend/lib/explorer.test.ts
import { describe, expect, it } from "vitest";
import { cardsApiUrl, explorerUrl, hasFilters, parseExplorer, type ExplorerState } from "./explorer";

describe("parseExplorer", () => {
  it("defaults to the set tab with no filters", () => {
    expect(parseExplorer(new URLSearchParams(""))).toEqual({ par: "set", filters: {}, tri: "", page: 1 });
  });

  it("reads tab, filters, sort and page", () => {
    const params = new URLSearchParams("par=illustrateur&illustrateur=Ken+Sugimori&tri=pv%3Adesc&page=3");
    expect(parseExplorer(params)).toEqual({
      par: "illustrateur",
      filters: { illustrateur: "Ken Sugimori" },
      tri: "pv:desc",
      page: 3,
    });
  });

  it("ignores an unknown tab and a bad page", () => {
    expect(parseExplorer(new URLSearchParams("par=prix&page=-2"))).toEqual({ par: "set", filters: {}, tri: "", page: 1 });
  });

  it("reads the URL the AI builds", () => {
    const state = parseExplorer(new URLSearchParams("par=pokemon&pokemon=25&type=%C3%89lectrique&tri=rarete%3Adesc%2Cpv%3Adesc"));
    expect(state.filters).toEqual({ pokemon: "25", type: "Électrique" });
    expect(state.tri).toBe("rarete:desc,pv:desc");
  });
});

describe("explorerUrl", () => {
  it("omits defaults and empty values", () => {
    expect(explorerUrl({ par: "set", filters: { q: "" }, tri: "", page: 1 })).toBe("/explorer/");
  });

  it("round-trips through parseExplorer", () => {
    const state: ExplorerState = { par: "rarete", filters: { rarete: "Ultra Rare", q: "pikachu" }, tri: "pv:desc", page: 2 };
    const url = new URL(explorerUrl(state), "http://localhost");
    expect(parseExplorer(url.searchParams)).toEqual(state);
  });
});

describe("cardsApiUrl", () => {
  it("sends filters, sort and page but not the tab", () => {
    expect(cardsApiUrl({ par: "pokemon", filters: { pokemon: "25" }, tri: "pv:desc", page: 2 })).toBe(
      "/api/cartes?pokemon=25&tri=pv%3Adesc&page=2",
    );
  });
});

describe("hasFilters", () => {
  it("is true only when a filter has a value", () => {
    expect(hasFilters({ par: "set", filters: {}, tri: "nom:asc", page: 1 })).toBe(false);
    expect(hasFilters({ par: "set", filters: { q: "pika" }, tri: "", page: 1 })).toBe(true);
  });
});
```

```tsx
// frontend/components/CardImage.test.tsx
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { CardImage } from "./CardImage";

afterEach(cleanup);

it("shows a placeholder when the card has no image", () => {
  render(<CardImage base={null} alt="Énergie Feu" quality="low" />);
  expect(screen.getByText("Image indisponible")).toBeTruthy();
});

it("loads the webp image at the requested quality", () => {
  render(<CardImage base="https://assets.tcgdex.net/fr/swsh/swsh3/136" alt="Fouinar" quality="high" />);
  expect(screen.getByRole("img", { name: "Fouinar" }).getAttribute("src")).toBe(
    "https://assets.tcgdex.net/fr/swsh/swsh3/136/high.webp",
  );
});

it("falls back to the placeholder when loading fails", () => {
  render(<CardImage base="https://assets.tcgdex.net/fr/x/y/1" alt="Carte" quality="low" />);
  fireEvent.error(screen.getByRole("img", { name: "Carte" }));
  expect(screen.getByText("Image indisponible")).toBeTruthy();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL with `Failed to resolve import "./explorer"` and `"./CardImage"`.

- [ ] **Step 3: Write `lib/explorer.ts`, `lib/chat.ts`, `lib/useApi.ts`**

```ts
// frontend/lib/explorer.ts
import { toQuery } from "./query";

export type GroupBy = "set" | "pokemon" | "illustrateur" | "rarete";

export const GROUP_TABS: { par: GroupBy; label: string }[] = [
  { par: "set", label: "Par extension" },
  { par: "pokemon", label: "Par Pokémon" },
  { par: "illustrateur", label: "Par illustrateur" },
  { par: "rarete", label: "Par rareté" },
];

export const FILTER_KEYS = ["set", "pokemon", "illustrateur", "rarete", "type", "q"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];

export const FILTER_LABELS: Record<FilterKey, string> = {
  set: "Extension",
  pokemon: "Pokédex n°",
  illustrateur: "Illustrateur",
  rarete: "Rareté",
  type: "Type",
  q: "Nom",
};

export const SORT_OPTIONS = [
  { value: "", label: "Par défaut (date, numéro)" },
  { value: "nom:asc", label: "Nom (A-Z)" },
  { value: "pokedex:asc", label: "Numéro de Pokédex" },
  { value: "pv:desc", label: "PV décroissants" },
  { value: "rarete:desc", label: "Rareté décroissante" },
  { value: "illustrateur:asc", label: "Illustrateur" },
  { value: "date_sortie:desc", label: "Plus récentes" },
  { value: "numero:asc", label: "Numéro dans l'extension" },
];

export type ExplorerState = { par: GroupBy; filters: Partial<Record<FilterKey, string>>; tri: string; page: number };

export function parseExplorer(params: URLSearchParams): ExplorerState {
  const tab = GROUP_TABS.find((t) => t.par === params.get("par"));
  const filters: ExplorerState["filters"] = {};
  for (const key of FILTER_KEYS) {
    const value = params.get(key);
    if (value) filters[key] = value;
  }
  const page = Number(params.get("page"));
  return { par: tab ? tab.par : "set", filters, tri: params.get("tri") ?? "", page: Number.isInteger(page) && page > 0 ? page : 1 };
}

export function explorerUrl(state: ExplorerState): string {
  return (
    "/explorer/" +
    toQuery({
      par: state.par === "set" ? undefined : state.par,
      ...state.filters,
      tri: state.tri,
      page: state.page > 1 ? state.page : undefined,
    })
  );
}

export function cardsApiUrl(state: ExplorerState): string {
  return "/api/cartes" + toQuery({ ...state.filters, tri: state.tri, page: state.page > 1 ? state.page : undefined });
}

export function hasFilters(state: ExplorerState): boolean {
  return Object.values(state.filters).some(Boolean);
}
```

```ts
// frontend/lib/chat.ts
export const REFRESH_EVENT = "tcg:rafraichir";
```

```ts
// frontend/lib/useApi.ts
"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import { REFRESH_EVENT } from "./chat";
import type { RefreshTarget } from "./types";

export function useApi<T>(url: string | null, refreshOn: RefreshTarget[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const targets = refreshOn.join(",");

  useEffect(() => {
    if (!targets) return;
    const onRefresh = (event: Event) => {
      if (targets.split(",").includes((event as CustomEvent<RefreshTarget>).detail)) setVersion((v) => v + 1);
    };
    window.addEventListener(REFRESH_EVENT, onRefresh);
    return () => window.removeEventListener(REFRESH_EVENT, onRefresh);
  }, [targets]);

  useEffect(() => {
    if (url === null) return;
    let active = true;
    api<T>(url).then(
      (result) => {
        if (!active) return;
        setData(result);
        setError(null);
      },
      (err: Error) => {
        if (active) setError(err.message);
      },
    );
    return () => {
      active = false;
    };
  }, [url, version]);

  return { data, error, reload: () => setVersion((v) => v + 1) };
}
```

- [ ] **Step 4: Write the components**

```tsx
// frontend/components/CardImage.tsx
"use client";

import { useState } from "react";

export function CardImage({ base, alt, quality }: { base: string | null; alt: string; quality: "low" | "high" }) {
  const [failed, setFailed] = useState(false);
  if (!base || failed) return <div className={`card-placeholder ${quality}`}>Image indisponible</div>;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static export, images stay on TCGdex's CDN
    <img className={`card-img ${quality}`} src={`${base}/${quality}.webp`} alt={alt} loading="lazy" onError={() => setFailed(true)} />
  );
}
```

```tsx
// frontend/components/CardGrid.tsx
import Link from "next/link";
import type { ReactNode } from "react";
import type { CardSummary } from "@/lib/types";
import { CardImage } from "./CardImage";

export function CardGrid({ cards, renderAction }: { cards: CardSummary[]; renderAction?: (card: CardSummary) => ReactNode }) {
  if (cards.length === 0) return <p className="empty">Aucune carte.</p>;
  return (
    <ul className="card-grid">
      {cards.map((card) => (
        <li key={card.id}>
          <Link className="card-tile" href={`/carte/?id=${encodeURIComponent(card.id)}`}>
            <CardImage base={card.image} alt={card.nom} quality="low" />
            <span className="card-name">{card.nom}</span>
            <span className="card-meta">
              {card.set_nom} · {card.numero}
            </span>
            {card.quantite > 0 && <span className="owned">x{card.quantite}</span>}
          </Link>
          {renderAction?.(card)}
        </li>
      ))}
    </ul>
  );
}
```

```tsx
// frontend/components/Pagination.tsx
export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <div className="pagination">
      <button className="button secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Précédente
      </button>
      <span>
        Page {page} sur {pages}
      </span>
      <button className="button secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Suivante
      </button>
    </div>
  );
}
```

```tsx
// frontend/components/SortSelect.tsx
import { SORT_OPTIONS } from "@/lib/explorer";

export function SortSelect({ value, onChange }: { value: string; onChange: (tri: string) => void }) {
  const known = SORT_OPTIONS.some((option) => option.value === value);
  return (
    <label>
      Trier :{" "}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {!known && <option value={value}>Tri personnalisé ({value})</option>}
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
```

```tsx
// frontend/components/Header.tsx
"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const LINKS = [
  { href: "/explorer/", label: "Explorer" },
  { href: "/collection/", label: "Ma collection" },
  { href: "/listes/", label: "Mes listes" },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await api("/api/deconnexion", { method: "POST" });
    router.push("/connexion/");
  }

  return (
    <header className="header">
      <Link className="brand" href="/explorer/">TCG-exemple</Link>
      <nav>
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} className={pathname.startsWith(link.href.slice(0, -1)) ? "active" : ""}>
            {link.label}
          </Link>
        ))}
      </nav>
      <button className="button secondary" onClick={signOut}>Se déconnecter</button>
    </header>
  );
}
```

```tsx
// frontend/app/(app)/layout.tsx
import { Header } from "@/components/Header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Header />
      <div className="body">
        <main className="main">{children}</main>
      </div>
      <footer className="footer">
        Données des cartes : TCGdex (licence MIT). Pokémon et tous les noms et images associés sont des marques et
        propriétés de Nintendo, Creatures, GAME FREAK et The Pokémon Company. Ce site n&apos;est ni affilié, ni approuvé, ni
        sponsorisé par eux.
      </footer>
    </div>
  );
}
```

- [ ] **Step 5: Write the explorer page**

```tsx
// frontend/app/(app)/explorer/page.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { SortSelect } from "@/components/SortSelect";
import {
  cardsApiUrl,
  explorerUrl,
  type ExplorerState,
  FILTER_LABELS,
  type FilterKey,
  GROUP_TABS,
  hasFilters,
  parseExplorer,
} from "@/lib/explorer";
import { normalize } from "@/lib/text";
import type { CardPage, Group } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Go = (next: ExplorerState) => void;

export default function ExplorerPage() {
  return (
    <Suspense>
      <Explorer />
    </Suspense>
  );
}

function Explorer() {
  const router = useRouter();
  const state = parseExplorer(new URLSearchParams(useSearchParams().toString()));
  const go: Go = (next) => router.push(explorerUrl(next));

  return (
    <section>
      <div className="tabs">
        {GROUP_TABS.map((tab) => (
          <button
            key={tab.par}
            className={tab.par === state.par && !hasFilters(state) ? "tab active" : "tab"}
            onClick={() => go({ par: tab.par, filters: {}, tri: state.tri, page: 1 })}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <SearchBox key={state.filters.q ?? ""} initial={state.filters.q ?? ""} onSearch={(q) => go({ ...state, filters: { ...state.filters, q }, page: 1 })} />
      {hasFilters(state) ? <CardResults state={state} go={go} /> : <GroupList key={state.par} state={state} go={go} />}
    </section>
  );
}

function SearchBox({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial);
  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(value.trim());
  }
  return (
    <form className="form-row" onSubmit={submit}>
      <input className="input" placeholder="Rechercher une carte par nom" value={value} onChange={(e) => setValue(e.target.value)} />
      <button className="button" type="submit">Rechercher</button>
    </form>
  );
}

function GroupList({ state, go }: { state: ExplorerState; go: Go }) {
  const { data, error } = useApi<Group[]>(`/api/groupes?par=${state.par}`);
  const [filter, setFilter] = useState("");
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Chargement...</p>;
  const needle = normalize(filter);
  const groups = data.filter((group) => normalize(group.nom).includes(needle));
  return (
    <div>
      <input className="input" placeholder="Filtrer la liste" value={filter} onChange={(e) => setFilter(e.target.value)} />
      <ul className="group-list">
        {groups.map((group, index) => (
          <li key={group.valeur} style={{ display: "contents" }}>
            {group.groupe && group.groupe !== groups[index - 1]?.groupe && <h3 className="group-heading">{group.groupe}</h3>}
            <button className="group-item" onClick={() => go({ ...state, filters: { [state.par]: group.valeur }, page: 1 })}>
              <span>{group.nom}</span>
              <span className="muted">{group.nombre}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function CardResults({ state, go }: { state: ExplorerState; go: Go }) {
  const { data, error } = useApi<CardPage>(cardsApiUrl(state), ["collection"]);
  const remove = (key: FilterKey) => {
    const filters = { ...state.filters };
    delete filters[key];
    go({ ...state, filters, page: 1 });
  };
  return (
    <div>
      <div className="toolbar">
        <div className="chips">
          {Object.entries(state.filters).map(([key, value]) => (
            <button key={key} className="chip" onClick={() => remove(key as FilterKey)} title="Retirer ce filtre">
              {FILTER_LABELS[key as FilterKey]} : {value} ×
            </button>
          ))}
        </div>
        <SortSelect value={state.tri} onChange={(tri) => go({ ...state, tri, page: 1 })} />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="muted">{data.total} cartes</p>
          <CardGrid cards={data.cartes} />
          <Pagination page={data.page} pages={data.pages} onPage={(page) => go({ ...state, page })} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Run the tests, lint and build**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: all tests pass (6 + 8 + 3), no lint errors, `out/explorer/index.html` exists.

- [ ] **Step 7: Check in the browser**

Run the backend (`cd backend && uv run uvicorn --factory app.main:create_app --port 8000`) and the frontend dev server (`cd frontend && npm run dev`). Open `http://localhost:3000/connexion`, sign in with `user`/`user`, then check: the four tabs list groups; clicking "Ténèbres Embrasées" shows its cards with images; "Trier : PV décroissants" reorders; the back button restores the previous view; a search for "energie" finds energy cards.

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "KAN-5: App shell and card explorer"
```

---

### Task 10: Card page

**Files:**
- Create: `frontend/app/(app)/carte/page.tsx`

**Interfaces:**
- Consumes: `useApi`, `api`, `cardPath`, `CardImage`, `VARIANT_LABELS`, `LIST_KIND_LABELS`, types `CardDetail`, `CardList`.
- Produces: page `/carte/?id=<card id>`.

- [ ] **Step 1: Write the page**

```tsx
// frontend/app/(app)/carte/page.tsx
"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CardImage } from "@/components/CardImage";
import { api, cardPath } from "@/lib/api";
import { explorerUrl } from "@/lib/explorer";
import { type CardDetail, type CardList, LIST_KIND_LABELS, VARIANT_LABELS } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CardPage() {
  return (
    <Suspense>
      <CardView />
    </Suspense>
  );
}

function CardView() {
  const id = useSearchParams().get("id");
  const card = useApi<CardDetail>(id ? cardPath(id) : null, ["collection", "listes"]);
  const lists = useApi<CardList[]>("/api/listes", ["listes"]);
  const [message, setMessage] = useState<string | null>(null);

  if (!id) return <p className="error">Aucune carte choisie.</p>;
  if (card.error) return <p className="error">{card.error}</p>;
  if (!card.data) return <p className="muted">Chargement...</p>;
  const data = card.data;

  async function run(action: () => Promise<unknown>) {
    setMessage(null);
    try {
      await action();
      card.reload();
      lists.reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  const setQuantity = (variant: string, quantite: number) =>
    run(() => api(`/api/collection/${encodeURIComponent(data.id)}/${variant}`, { method: "PUT", body: { quantite } }));
  const addToList = (listId: string) =>
    run(() => api(`/api/listes/${listId}/cartes/${encodeURIComponent(data.id)}`, { method: "POST" }));
  const available = (lists.data ?? []).filter((list) => !data.listes.some((l) => l.id === list.id));

  return (
    <section className="card-detail">
      <CardImage base={data.image} alt={data.nom} quality="high" />
      <div>
        <h1>{data.nom}</h1>
        <div className="panel facts">
          <span>Extension</span>
          <Link href={explorerUrl({ par: "set", filters: { set: data.set_id }, tri: "", page: 1 })}>
            {data.set_nom} ({data.serie_nom})
          </Link>
          <span>Numéro</span>
          <span>{data.numero}</span>
          <span>Date de sortie</span>
          <span>{data.date_sortie ?? "Inconnue"}</span>
          <span>Catégorie</span>
          <span>{[data.categorie, data.stade].filter(Boolean).join(" · ")}</span>
          {data.pv !== null && (
            <>
              <span>PV</span>
              <span>{data.pv}</span>
            </>
          )}
          {data.types.length > 0 && (
            <>
              <span>Types</span>
              <span>{data.types.join(", ")}</span>
            </>
          )}
          <span>Rareté</span>
          <span>{data.rarete ?? "Non renseignée"}</span>
          <span>Illustrateur</span>
          <span>{data.illustrateur ?? "Non renseigné"}</span>
          {data.pokemon.length > 0 && (
            <>
              <span>Pokémon</span>
              <span>
                {data.pokemon.map((p) => (
                  <Link key={p.dex_id} href={explorerUrl({ par: "pokemon", filters: { pokemon: String(p.dex_id) }, tri: "", page: 1 })}>
                    {p.nom} (n° {p.dex_id}){" "}
                  </Link>
                ))}
              </span>
            </>
          )}
        </div>

        <div className="panel">
          <h2>Ma collection</h2>
          {data.variantes.map((variant) => {
            const quantity = data.quantites[variant] ?? 0;
            return (
              <div key={variant} className="variant-row">
                <span className="label">{VARIANT_LABELS[variant] ?? variant}</span>
                <button className="button secondary" disabled={quantity === 0} onClick={() => setQuantity(variant, quantity - 1)}>
                  -
                </button>
                <span>{quantity}</span>
                <button className="button" onClick={() => setQuantity(variant, quantity + 1)}>
                  +
                </button>
              </div>
            );
          })}
        </div>

        <div className="panel">
          <h2>Mes listes</h2>
          {data.listes.length === 0 && <p className="muted">Cette carte n&apos;est dans aucune liste.</p>}
          <ul>
            {data.listes.map((list) => (
              <li key={list.id}>
                <Link href={`/listes/voir/?id=${list.id}`}>{list.nom}</Link> ({LIST_KIND_LABELS[list.type]})
              </li>
            ))}
          </ul>
          {available.length > 0 && (
            <select value="" onChange={(e) => e.target.value && addToList(e.target.value)}>
              <option value="">Ajouter à une liste...</option>
              {available.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.nom} ({LIST_KIND_LABELS[list.type]})
                </option>
              ))}
            </select>
          )}
          {message && <p className="error">{message}</p>}
        </div>

        {(data.details.abilities?.length || data.details.attacks?.length || data.details.effect) && (
          <div className="panel">
            {data.details.abilities?.map((ability) => (
              <p key={ability.name}>
                <strong>Talent : {ability.name}</strong> {ability.effect}
              </p>
            ))}
            {data.details.attacks?.map((attack) => (
              <p key={attack.name}>
                <strong>{attack.name}</strong> {attack.cost?.length ? `(${attack.cost.join(", ")})` : ""} {attack.damage ?? ""}
                {attack.effect && <><br />{attack.effect}</>}
              </p>
            ))}
            {data.details.effect && <p>{data.details.effect}</p>}
          </div>
        )}
        {data.details.description && <p className="muted">{data.details.description}</p>}
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Lint, build and check in the browser**

Run: `cd frontend && npm run lint && npm run build`
Expected: no errors; `out/carte/index.html` exists.

With both dev servers running, open a card from the explorer and check: high-resolution image or placeholder; "+" on "Reverse" sets the count to 1; going back to the explorer shows the green "x1" badge; adding to a "Collection" list of a card not owned shows the French error. Also open `http://localhost:3000/carte/?id=exu-%3F` (real id with "?") and confirm it loads.

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "KAN-5: Card page with collection and list controls"
```

---

### Task 11: Collection and lists pages

**Files:**
- Create: `frontend/app/(app)/collection/page.tsx`, `frontend/app/(app)/listes/page.tsx`, `frontend/app/(app)/listes/voir/page.tsx`

**Interfaces:**
- Consumes: `useApi`, `api`, `toQuery`, `CardGrid`, `Pagination`, `SortSelect`, `LIST_KIND_LABELS`, types.
- Produces: pages `/collection/?tri=&page=`, `/listes/`, `/listes/voir/?id=&page=`.

- [ ] **Step 1: Write the collection page**

```tsx
// frontend/app/(app)/collection/page.tsx
"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { SortSelect } from "@/components/SortSelect";
import { toQuery } from "@/lib/query";
import type { CardPage } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CollectionPage() {
  return (
    <Suspense>
      <Collection />
    </Suspense>
  );
}

function Collection() {
  const router = useRouter();
  const params = useSearchParams();
  const tri = params.get("tri") ?? "";
  const page = Number(params.get("page")) || 1;
  const query = (t: string, p: number) => toQuery({ tri: t, page: p > 1 ? p : undefined });
  const { data, error } = useApi<CardPage>(`/api/collection${query(tri, page)}`, ["collection"]);
  const go = (t: string, p: number) => router.push(`/collection/${query(t, p)}`);

  return (
    <section>
      <h1>Ma collection</h1>
      <div className="toolbar">
        <span className="muted">{data ? `${data.total} cartes différentes` : ""}</span>
        <SortSelect value={tri} onChange={(t) => go(t, 1)} />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          {data.total === 0 && <p className="empty">Votre collection est vide. Ajoutez des cartes depuis Explorer ou avec l&apos;assistant.</p>}
          {data.total > 0 && <CardGrid cards={data.cartes} />}
          <Pagination page={data.page} pages={data.pages} onPage={(p) => go(tri, p)} />
        </>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Write the lists page**

```tsx
// frontend/app/(app)/listes/page.tsx
"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { type CardList, LIST_KIND_LABELS, type ListKind } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ListsPage() {
  const { data, error, reload } = useApi<CardList[]>("/api/listes", ["listes"]);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ListKind>("souhaits");
  const [message, setMessage] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setMessage(null);
    try {
      await action();
      reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  function create(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      await api("/api/listes", { method: "POST", body: { nom: name, type: kind } });
      setName("");
    });
  }

  function rename(list: CardList) {
    const nom = window.prompt("Nouveau nom de la liste", list.nom);
    if (nom) run(() => api(`/api/listes/${list.id}`, { method: "PATCH", body: { nom } }));
  }

  function remove(list: CardList) {
    if (window.confirm(`Supprimer la liste « ${list.nom} » ?`)) run(() => api(`/api/listes/${list.id}`, { method: "DELETE" }));
  }

  return (
    <section>
      <h1>Mes listes</h1>
      <form className="form-row" onSubmit={create}>
        <input className="input" placeholder="Nom de la nouvelle liste" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={kind} onChange={(e) => setKind(e.target.value as ListKind)}>
          <option value="souhaits">Recherchées (n&apos;importe quelle carte)</option>
          <option value="collection">Collection (cartes possédées)</option>
        </select>
        <button className="button" type="submit" disabled={!name.trim()}>
          Créer
        </button>
      </form>
      {message && <p className="error">{message}</p>}
      {error && <p className="error">{error}</p>}
      {data && data.length === 0 && <p className="empty">Aucune liste pour le moment.</p>}
      <ul className="lists">
        {data?.map((list) => (
          <li key={list.id} className="list-row">
            <Link href={`/listes/voir/?id=${list.id}`}>{list.nom}</Link>
            <span className="muted">
              {LIST_KIND_LABELS[list.type]} · {list.nombre} cartes
            </span>
            <button className="button secondary" onClick={() => rename(list)}>
              Renommer
            </button>
            <button className="button danger" onClick={() => remove(list)}>
              Supprimer
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 3: Write the list view page**

```tsx
// frontend/app/(app)/listes/voir/page.tsx
"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { api } from "@/lib/api";
import { toQuery } from "@/lib/query";
import { type CardList, type CardPage, LIST_KIND_LABELS } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ListViewPage() {
  return (
    <Suspense>
      <ListView />
    </Suspense>
  );
}

function ListView() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");
  const page = Number(params.get("page")) || 1;
  const { data, error, reload } = useApi<CardList & { cartes: CardPage }>(
    id ? `/api/listes/${id}${toQuery({ page: page > 1 ? page : undefined })}` : null,
    ["listes", "collection"],
  );
  const [message, setMessage] = useState<string | null>(null);

  if (!id) return <p className="error">Aucune liste choisie.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Chargement...</p>;

  async function removeCard(cardId: string) {
    setMessage(null);
    try {
      await api(`/api/listes/${id}/cartes/${encodeURIComponent(cardId)}`, { method: "DELETE" });
      reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  return (
    <section>
      <p>
        <Link href="/listes/">Mes listes</Link>
      </p>
      <h1>{data.nom}</h1>
      <p className="muted">
        {LIST_KIND_LABELS[data.type]} · {data.nombre} cartes
      </p>
      {message && <p className="error">{message}</p>}
      <CardGrid
        cards={data.cartes.cartes}
        renderAction={(card) => (
          <button className="button secondary" onClick={() => removeCard(card.id)}>
            Retirer
          </button>
        )}
      />
      <Pagination
        page={data.cartes.page}
        pages={data.cartes.pages}
        onPage={(p) => router.push(`/listes/voir/${toQuery({ id, page: p > 1 ? p : undefined })}`)}
      />
    </section>
  );
}
```

- [ ] **Step 4: Lint, build and check in the browser**

Run: `cd frontend && npm run lint && npm run build`
Expected: no errors.

In the browser: create "Recherchées" (souhaits) and "Classeur" (collection); a duplicate name shows "Une liste « ... » existe déjà"; add cards from a card page; set an owned card's quantities to 0 and confirm it disappears from "Classeur" but stays in "Recherchées"; rename and delete work.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "KAN-5: Collection and lists pages"
```

---

### Task 12: Chat panel

**Files:**
- Modify: `frontend/lib/chat.ts` (add `applyActions`), `frontend/app/(app)/layout.tsx` (render the panel)
- Create: `frontend/components/ChatPanel.tsx`
- Test: `frontend/lib/chat.test.ts`

**Interfaces:**
- Consumes: `POST /api/chat` (Task 7), `REFRESH_EVENT`, `api`, types `ChatAction`, `ChatMessage`.
- Produces: `applyActions(actions: ChatAction[], navigate: (url: string) => void): void`; component `ChatPanel`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/lib/chat.test.ts
import { expect, it, vi } from "vitest";
import { applyActions, REFRESH_EVENT } from "./chat";

it("navigates for naviguer and broadcasts rafraichir", () => {
  const navigate = vi.fn();
  const seen: string[] = [];
  const listener = (event: Event) => seen.push((event as CustomEvent<string>).detail);
  window.addEventListener(REFRESH_EVENT, listener);

  applyActions(
    [
      { type: "rafraichir", cible: "collection" },
      { type: "naviguer", url: "/explorer/?par=pokemon&pokemon=25" },
      { type: "rafraichir", cible: "listes" },
    ],
    navigate,
  );

  window.removeEventListener(REFRESH_EVENT, listener);
  expect(navigate).toHaveBeenCalledWith("/explorer/?par=pokemon&pokemon=25");
  expect(seen).toEqual(["collection", "listes"]);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && npm test -- lib/chat.test.ts`
Expected: FAIL with `applyActions is not a function` (or a missing export error).

- [ ] **Step 3: Complete `lib/chat.ts`**

```ts
// frontend/lib/chat.ts
import type { ChatAction } from "./types";

export const REFRESH_EVENT = "tcg:rafraichir";

export function applyActions(actions: ChatAction[], navigate: (url: string) => void): void {
  for (const action of actions) {
    if (action.type === "naviguer") navigate(action.url);
    else window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: action.cible }));
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && npm test`
Expected: all pass.

- [ ] **Step 5: Write `components/ChatPanel.tsx` and add it to the layout**

```tsx
// frontend/components/ChatPanel.tsx
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { applyActions } from "@/lib/chat";
import type { ChatAction, ChatMessage } from "@/lib/types";

const EXAMPLES = "Exemples : « Montre les cartes de Ken Sugimori par PV décroissants », « Ajoute 2 Fouinar reverse de Ténèbres Embrasées ».";

export function ChatPanel() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [messages, busy]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const page = params.size ? `${pathname}?${params.toString()}` : pathname;
      const result = await api<{ reponse: string; actions: ChatAction[] }>("/api/chat", {
        method: "POST",
        body: { messages: next.slice(-20), page },
      });
      setMessages([...next, { role: "assistant", content: result.reponse }]);
      applyActions(result.actions, (url) => router.push(url));
    } catch (err) {
      setMessages([...next, { role: "assistant", content: (err as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <aside className="chat closed">
        <button className="button" onClick={() => setOpen(true)}>Assistant</button>
      </aside>
    );
  }

  return (
    <aside className="chat">
      <div className="chat-header">
        <strong>Assistant</strong>
        <button className="button secondary" onClick={() => setOpen(false)}>Fermer</button>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && <p className="muted">{EXAMPLES}</p>}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
        {busy && <div className="message assistant">...</div>}
        <div ref={end} />
      </div>
      <form className="chat-form" onSubmit={send}>
        <input className="input" placeholder="Votre demande" value={input} onChange={(e) => setInput(e.target.value)} />
        <button className="button" type="submit" disabled={busy}>Envoyer</button>
      </form>
    </aside>
  );
}
```

Replace `frontend/app/(app)/layout.tsx` with:

```tsx
import { Suspense } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Header />
      <div className="body">
        <main className="main">{children}</main>
        <Suspense>
          <ChatPanel />
        </Suspense>
      </div>
      <footer className="footer">
        Données des cartes : TCGdex (licence MIT). Pokémon et tous les noms et images associés sont des marques et
        propriétés de Nintendo, Creatures, GAME FREAK et The Pokémon Company. Ce site n&apos;est ni affilié, ni approuvé, ni
        sponsorisé par eux.
      </footer>
    </div>
  );
}
```

- [ ] **Step 6: Lint, build and check with the real model**

Run: `cd frontend && npm test && npm run lint && npm run build`
Expected: all pass.

Start the backend with the key loaded (bash: `set -a; . ../.env; set +a; uv run uvicorn --factory app.main:create_app --port 8000`) and the frontend dev server. In the chat, check:
1. "Montre les cartes de Ken Sugimori triées par PV décroissants": the explorer switches to that filter and sort.
2. "Ajoute 2 Fouinar reverse de Ténèbres Embrasées": a one-line confirmation; "Ma collection" shows Fouinar x2 without reloading.
3. "Ajoute Pikachu": the assistant asks which one or shows the matches instead of adding one.
4. "Crée une liste Recherchées de type souhaits et ajoutes-y Dracaufeu du Set de Base": the list appears on "Mes listes".
5. Moving between pages keeps the conversation.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "KAN-5: AI chat panel"
```

---

### Task 13: Docker, start/stop scripts and docs

**Files:**
- Create: `Dockerfile`, `.dockerignore`, `scripts/start.sh`, `scripts/stop.sh`, `scripts/start.ps1`, `scripts/stop.ps1`, `THIRD_PARTY_NOTICES.md`
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: `create_app` factory (env `DB_PATH`, `CATALOG_PATH`, `STATIC_DIR`), `frontend/out` from `npm run build`.
- Produces: image `tcg-exemple`, container `tcg-exemple` on port 8000, volume `tcg-exemple-data` at `/data`.

- [ ] **Step 1: Write the Dockerfile and .dockerignore**

```dockerfile
# Dockerfile
FROM node:24-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/app ./app
COPY backend/data ./data
COPY --from=frontend /frontend/out ./static
ENV PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/tcg.db \
    CATALOG_PATH=/app/data/catalog.json.gz \
    STATIC_DIR=/app/static
EXPOSE 8000
CMD ["uvicorn", "--factory", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
```

```
# .dockerignore
.git
.env
**/node_modules
**/.next
**/out
**/.venv
**/*.db
**/__pycache__
```

- [ ] **Step 2: Write the start/stop scripts**

```bash
#!/usr/bin/env bash
# scripts/start.sh - Mac and Linux
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t tcg-exemple .
docker rm -f tcg-exemple >/dev/null 2>&1 || true
docker run -d --name tcg-exemple -p 8000:8000 --env-file .env -v tcg-exemple-data:/data tcg-exemple
echo "TCG-exemple : http://localhost:8000 (utilisateur : user / mot de passe : user)"
```

```bash
#!/usr/bin/env bash
# scripts/stop.sh - Mac and Linux
set -euo pipefail
docker rm -f tcg-exemple
```

```powershell
# scripts/start.ps1 - Windows
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
docker build -t tcg-exemple .
if ($LASTEXITCODE -ne 0) { exit 1 }
docker rm -f tcg-exemple 2>$null | Out-Null
docker run -d --name tcg-exemple -p 8000:8000 --env-file .env -v tcg-exemple-data:/data tcg-exemple
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "TCG-exemple : http://localhost:8000 (utilisateur : user / mot de passe : user)"
```

```powershell
# scripts/stop.ps1 - Windows
docker rm -f tcg-exemple
```

Then: `chmod +x scripts/*.sh` and `git update-index --chmod=+x scripts/start.sh scripts/stop.sh` after adding them.

- [ ] **Step 3: Build and run the container**

Run: `./scripts/start.sh` (or `powershell -File scripts/start.ps1`)
Expected: build succeeds, then the URL line. Check:
- `curl -s http://localhost:8000/connexion/ | head -c 200` returns HTML.
- Sign in at `http://localhost:8000`, add a card, run `./scripts/stop.sh` then `./scripts/start.sh`, sign in again: the card is still in the collection (volume works).
- `docker logs tcg-exemple` shows no errors.

- [ ] **Step 4: Write `THIRD_PARTY_NOTICES.md`**

```markdown
# Third-party notices

## TCGdex

Card data comes from TCGdex (https://tcgdex.dev, https://github.com/tcgdex/cards-database).

MIT License

Copyright (c) 2021 TCGdex

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Pokemon

Pokemon and all related names, card texts and images are trademarks and copyright of Nintendo, Creatures, GAME FREAK and The Pokemon Company. This project is a non-commercial educational example, not affiliated with, endorsed or sponsored by them. Card images are loaded from TCGdex's servers and are not stored in this repository.
```

Before committing, open https://github.com/tcgdex/cards-database/blob/master/LICENSE and confirm the copyright line matches; fix it if not.

- [ ] **Step 5: Rewrite `README.md`**

````markdown
# TCG-exemple

A local web app to browse every physical Pokemon TCG card in French, manage a collection and lists, and use an AI assistant. Built as a course project, due October 8, 2026.

## Run

Requires Docker and a `.env` file at the project root containing `OPENROUTER_API_KEY=...`.

- Mac / Linux: `./scripts/start.sh`, stop with `./scripts/stop.sh`
- Windows: `powershell -File scripts/start.ps1`, stop with `powershell -File scripts/stop.ps1`

Open http://localhost:8000 and sign in with `user` / `user`.

## Data

Card data: TCGdex French catalog, snapshot in `backend/data/catalog.json.gz` (see `THIRD_PARTY_NOTICES.md`). Refresh it with `cd backend && uv run python -m scripts.fetch_catalog`, then rebuild.

Design and plan: `docs/`.
````

- [ ] **Step 6: Update `CLAUDE.md`**

Replace the "Current state" section with:

````markdown
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
- `db.py` creates the database and loads the catalog snapshot `backend/data/catalog.json.gz` (built by `scripts/fetch_catalog.py` from TCGdex, French) when its version changes. Catalog rows are never deleted.
- `chat.py` runs the OpenRouter tool loop and returns `{reponse, actions}`; the frontend applies `naviguer` (change URL) and `rafraichir` (refetch) actions.
- The frontend is a Next.js static export served by FastAPI at `/`. The explorer's state lives in the URL (`lib/explorer.ts`).
- Design spec: `docs/superpowers/specs/2026-10-02-tcg-collection-mvp-design.md`.
````

- [ ] **Step 7: Commit**

```bash
git add Dockerfile .dockerignore scripts THIRD_PARTY_NOTICES.md README.md CLAUDE.md
git commit -m "KAN-5: Docker image, start/stop scripts and docs"
```

---

### Task 14: End-to-end check before the deadline

**Files:** none (fixes go in the task that owns the code, with a test first).

- [ ] **Step 1: Run every automated check**

Run: `cd backend && uv run pytest` and `cd frontend && npm test && npm run lint && npm run build`
Expected: everything passes.

- [ ] **Step 2: Clean-machine run**

Remove the old state: `docker rm -f tcg-exemple; docker volume rm tcg-exemple-data`. Run `./scripts/start.sh` (on Windows also `scripts/start.ps1`).

- [ ] **Step 3: Walk through every feature at http://localhost:8000**

1. Sign in with a wrong password (French error), then with `user` / `user`.
2. Explorer: each of the four tabs lists groups; open a set, a Pokemon, an illustrator and a rarity; try every sort; search "énergie" and "energie" (same results); paginate; use back/forward.
3. Card page: change quantities per variant; open a card without an image (placeholder).
4. Collection: the counts match; sorting works.
5. Lists: create both kinds, duplicate name error, add from the card page, automatic removal from the collection list when quantity reaches 0, rename, delete.
6. AI: the five checks from Task 12 Step 6, plus a request while the network is off (the "indisponible" message, app still usable).
7. Stop and start again: data is still there.

- [ ] **Step 4: Record the result**

Write any problem found as a failing test in the owning task's test file, fix it, and commit. When everything passes, report to the user with the commit list; do not push or open a PR until they ask.
