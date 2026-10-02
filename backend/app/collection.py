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
