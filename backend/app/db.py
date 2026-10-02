import gzip
import json
import sqlite3
from pathlib import Path

from app.text import normalize

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
        # search_name is recomputed so search follows the current normalize(), whatever fetch wrote the snapshot.
        cards = [{**{k: v for k, v in card.items() if k != "dex_ids"}, "search_name": normalize(card["name"])}
                 for card in catalog["cards"]]
        _upsert(conn, "cards", cards)
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
        for table in ("sets", "cards"):  # databases created before English-only releases were added
            if "lang" not in {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN lang TEXT NOT NULL DEFAULT 'fr'")
        stored = conn.execute("SELECT value FROM meta WHERE key = 'catalog_version'").fetchone()
        if stored is None or stored["value"] != catalog["version"]:
            load_catalog(conn, catalog)
        with conn:
            conn.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, ?)", (DEFAULT_USER,))
    finally:
        conn.close()
