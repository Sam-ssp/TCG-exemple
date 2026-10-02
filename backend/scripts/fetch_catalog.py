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
