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
