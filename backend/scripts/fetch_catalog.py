"""Fetch the French TCGdex catalog into data/catalog.json.gz.

Run from backend/: uv run python -m scripts.fetch_catalog
"""

import asyncio
import gzip
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx

from app.text import normalize

API_ROOT = "https://api.tcgdex.net/v2"
OUT = Path(__file__).resolve().parent.parent / "data" / "catalog.json.gz"
USER_AGENT = "TCG-exemple (+https://github.com/Sam-ssp/TCG-exemple)"
CONCURRENCY = 5
EXCLUDED_SERIES = {"tcgp"}  # Pokemon TCG Pocket, a digital game
VARIANTS = ("normal", "reverse", "holo", "firstEdition", "wPromo")
DETAIL_KEYS = (
    "attacks", "abilities", "weaknesses", "resistances", "retreat", "effect", "description",
    "evolveFrom", "trainerType", "energyType", "regulationMark", "item",
)

ASSETS = "https://assets.tcgdex.net"

# TCGdex fr lists these galleries and vaults as their own sets; on the card they are part of the main set.
SUBSETS = {
    "exu": "ex10",  # Collection Zarbi -> EX Forces Cachées
    "sma": "sm115",  # Coffre Étincelant -> Destinées Occultes
    "swsh4.5sv": "swsh4.5",  # Coffre Étincelant -> Destinées Radieuses
    "cel25cc": "cel25",  # Collection Classique -> Célébrations
    "swsh9tg": "swsh9",  # Galerie de Dresseurs -> Stars Étincelantes
    "swsh10tg": "swsh10",
    "swsh11tg": "swsh11",
    "swsh12tg": "swsh12",
    "swsh12.5gg": "swsh12.5",  # Galerie Galaroise -> Zénith Suprême
    "rc": "bw11",  # Radiant Collection -> Legendary Treasures
    "30th-c": "30th",  # Collection Classique -> 30e Anniversaire
}
# 30th-c numbers 001-030 like its main set; TCGdex numbers the same kind of cards CC001 in Célébrations.
SUBSET_NUMBER_PREFIX = {"30th-c": "CC"}

# English-only cards keep their English names and text, but use the French values the filters know.
EN_CATEGORIES = {"Pokemon": "Pokémon", "Trainer": "Dresseur", "Energy": "Énergie"}
EN_TYPES = {
    "Fire": "Feu", "Water": "Eau", "Grass": "Plante", "Lightning": "Électrique", "Psychic": "Psy",
    "Fighting": "Combat", "Darkness": "Obscurité", "Metal": "Métal", "Fairy": "Fée", "Dragon": "Dragon",
    "Colorless": "Incolore",
}
EN_STAGES = {
    "Basic": "Base", "Stage1": "Niveau 1", "Stage2": "Niveau 2", "Baby": "Bébé", "MEGA": "MÉGA",
    "RESTORED": "Restauré", "BREAK": "TURBO", "LEVEL-UP": "Niveau Sup",
}
EN_RARITIES = {
    "Common": "Commune", "Uncommon": "Peu Commune", "Rare PRIME": "Rare Prime", "LEGEND": "LÉGENDE",
    "Black White Rare": "Rare Noir Blanc", "Amazing Rare": "Magnifique", "Radiant Rare": "Radieux Rare",
    "Classic Collection": "Collection Classique", "Full Art Trainer": "Dresseur Full Art",
    "Shiny Ultra Rare": "Chromatique ultra rare", "Special illustration rare": "Illustration spéciale rare",
    "Mega Hyper Rare": "Méga Hyper Rare", "ACE SPEC Rare": "HIGH-TECH rare", "None": "Sans Rareté",
}

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
    "Secret Rare": 85,
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


def build_set(detail: dict, lang: str = "fr") -> dict:
    count = detail.get("cardCount", {})
    return {
        "lang": lang,
        "id": detail["id"],
        "series_id": detail["serie"]["id"],
        "name": detail["name"],
        "release_date": detail.get("releaseDate"),
        "card_count_official": count.get("official"),
        "card_count_total": count.get("total"),
        "logo_url": detail.get("logo"),
        "symbol_url": detail.get("symbol"),
    }


def _to_french(raw: dict) -> dict:
    """English card with the category, types, stage, rarity and energy costs the French data uses."""
    raw = dict(raw)
    raw["category"] = EN_CATEGORIES.get(raw["category"], raw["category"])
    raw["types"] = [EN_TYPES.get(t, t) for t in raw.get("types") or []]
    if raw.get("stage"):
        raw["stage"] = EN_STAGES.get(raw["stage"], raw["stage"])
    if raw.get("rarity"):
        raw["rarity"] = EN_RARITIES.get(raw["rarity"], raw["rarity"])
    if raw.get("attacks"):
        raw["attacks"] = [{**a, "cost": [EN_TYPES.get(t, t) for t in a.get("cost") or []]} for a in raw["attacks"]]
    return raw


def build_card(raw: dict, set_id: str | None = None, lang: str = "fr") -> dict:
    """set_id: the set the card is filed under, when it differs from raw["set"]. lang "en": English-only card."""
    if lang == "en":
        raw = _to_french(raw)
    variants = {key: bool(raw.get("variants", {}).get(key)) for key in VARIANTS}
    if not any(variants.values()):
        variants["normal"] = True
    rarity = raw.get("rarity")
    prefix = SUBSET_NUMBER_PREFIX.get(raw["set"]["id"], "")
    local_id = raw["localId"] if raw["localId"].startswith(prefix) else prefix + raw["localId"]
    return {
        "lang": lang,
        "id": raw["id"],
        "set_id": set_id or raw["set"]["id"],
        "local_id": local_id,
        "local_number": local_number(local_id),
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


def merge_subsets(sets: list[dict]) -> list[dict]:
    """Drop sub-sets and add their card counts to their main set."""
    by_id = {s["id"]: dict(s) for s in sets}
    for child, parent in SUBSETS.items():
        if child in by_id and parent in by_id:
            by_id[parent]["card_count_total"] = (by_id[parent]["card_count_total"] or 0) + (by_id.pop(child)["card_count_total"] or 0)
    return [by_id[s["id"]] for s in sets if s["id"] in by_id]


def label_sets(sets: list[dict], cards: list[dict]) -> list[dict]:
    """A set is an English-only release when none of its cards exists in French."""
    french = {card["set_id"] for card in cards if card["lang"] == "fr"}
    return [{**s, "lang": "fr" if s["id"] in french else "en"} for s in sets]


def image_candidates(card: dict, serie_id: str, en_image: str | None, origin: tuple[str, str] | None = None) -> list[str]:
    """Image bases to try, in order, for a card the French API gives no image for.

    origin: the card's own set and number on TCGdex, when it was filed under a main set.
    """
    paths = [f"{serie_id}/{card['set_id']}/{quote(card['local_id'], safe='')}"]
    if origin:
        paths.append(f"{serie_id}/{origin[0]}/{quote(origin[1], safe='')}")
    candidates = [*(f"{ASSETS}/fr/{p}" for p in paths), en_image, *(f"{ASSETS}/en/{p}" for p in paths)]
    return [c for i, c in enumerate(candidates) if c and c not in candidates[:i]]


def card_set(own_set: str, listing_set: str, known_sets: set[str]) -> str:
    """The set a card is filed under: its own set if the catalog has it, else the set that lists it."""
    set_id = own_set if own_set in known_sets else listing_set
    return SUBSETS.get(set_id, set_id)


def pokemon_names(cards: list[dict]) -> list[dict]:
    """Name each Pokedex number after its shortest card name: French first, single-Pokemon cards first."""
    best: dict[int, tuple] = {}
    for card in cards:
        for dex_id in card["dex_ids"]:
            key = (card["lang"] != "fr", len(card["dex_ids"]) > 1, len(card["name"]), card["name"])
            if dex_id not in best or key < best[dex_id]:
                best[dex_id] = key
    return [{"dex_id": dex_id, "name": key[3]} for dex_id, key in sorted(best.items())]


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


async def get_json(client: httpx.AsyncClient, limit: asyncio.Semaphore, path: str, optional: bool = False, lang: str = "fr"):
    async with limit:
        response = await client.get(f"{API_ROOT}/{lang}{path}")
    if optional and response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


async def find_image(client: httpx.AsyncClient, limit: asyncio.Semaphore, card: dict, serie_id: str, origin: tuple[str, str]) -> None:
    """The French API omits images it has no French scan for; try the French files, then English."""
    english = await get_json(client, limit, f"/cards/{quote(card['id'], safe='')}", optional=True, lang="en")
    for base in image_candidates(card, serie_id, (english or {}).get("image"), origin):
        async with limit:
            found = (await client.head(f"{base}/low.webp")).status_code == 200
        if found:
            card["image_base"] = base
            return


async def fetch() -> tuple[dict, list[str]]:
    limit = asyncio.Semaphore(CONCURRENCY)
    transport = httpx.AsyncHTTPTransport(retries=3)
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}, transport=transport) as client:

        async def many(paths: list[str], lang: str = "fr", optional: bool = False) -> list:
            return await asyncio.gather(*(get_json(client, limit, p, optional=optional, lang=lang) for p in paths))

        def card_paths(ids: list[str]) -> list[str]:
            return [f"/cards/{quote(card_id, safe='')}" for card_id in ids]

        # French catalog, then the English catalog for every set and card French lacks.
        series = {}
        for lang in ("en", "fr"):  # French series and names win
            listed = [s for s in await get_json(client, limit, "/series", lang=lang) if s["id"] not in EXCLUDED_SERIES]
            for detail in await many([f"/series/{s['id']}" for s in listed], lang):
                series[detail["id"]] = detail
        series_details = sorted(series.values(), key=lambda s: s.get("releaseDate") or "9999")
        fr_set_ids = [s["id"] for d in series_details for s in d.get("sets", [])]
        fr_sets = await many([f"/sets/{quote(i, safe='')}" for i in fr_set_ids], optional=True)
        fr_sets = [d for d in fr_sets if d]
        en_series = [d for d in series_details]
        en_set_ids = []
        for d in await many([f"/series/{d['id']}" for d in en_series], "en", optional=True):
            en_set_ids += [s["id"] for s in (d or {}).get("sets", [])]
        en_sets = [d for d in await many([f"/sets/{quote(i, safe='')}" for i in en_set_ids], "en", optional=True) if d]
        fr_ids = {d["id"] for d in fr_sets}
        en_only_sets = [d for d in en_sets if d["id"] not in fr_ids]
        known = fr_ids | {d["id"] for d in en_only_sets}

        fr_listed = [(d["id"], c["id"]) for d in fr_sets for c in d.get("cards", [])]
        fr_raw = await many(card_paths([i for _, i in fr_listed]), optional=True)
        cards = [build_card(raw, card_set(raw["set"]["id"], s, known)) for (s, _), raw in zip(fr_listed, fr_raw) if raw]
        french_ids = {card["id"] for card in cards}
        en_listed = [(d["id"], c["id"]) for d in en_sets for c in d.get("cards", []) if c["id"] not in french_ids]
        en_raw = await many(card_paths([i for _, i in en_listed]), "en", optional=True)
        cards += [build_card(raw, card_set(raw["set"]["id"], s, known), lang="en") for (s, _), raw in zip(en_listed, en_raw) if raw]
        missing = [i for (_, i), raw in [*zip(fr_listed, fr_raw), *zip(en_listed, en_raw)] if raw is None]

        series_of = {d["id"]: d["serie"]["id"] for d in [*fr_sets, *en_only_sets]}
        origins = {raw["id"]: (raw["set"]["id"], raw["localId"]) for raw in [*fr_raw, *en_raw] if raw}
        await asyncio.gather(*(
            find_image(client, limit, card, series_of[card["set_id"]], origins[card["id"]])
            for card in cards if not card["image_base"]
        ))

    sets = [build_set(d) for d in fr_sets] + [build_set(d, "en") for d in en_only_sets]
    used_series = {s["series_id"] for s in sets}
    catalog = {
        "version": datetime.now().strftime("%Y-%m-%d %H:%M"),  # databases reload when it changes
        "series": [build_series(d, order) for order, d in enumerate(d for d in series_details if d["id"] in used_series)],
        "sets": label_sets(merge_subsets(sets), cards),
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
