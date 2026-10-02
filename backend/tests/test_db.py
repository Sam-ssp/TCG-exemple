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


def test_load_catalog_recomputes_search_names(tmp_path):
    catalog = sample_catalog()
    catalog["cards"][0]["name"] = "Goupix d’Alola"
    catalog["cards"][0]["search_name"] = "goupix d’alola"  # as written by an older fetch
    path = tmp_path / "catalog.json.gz"
    write_catalog(path, catalog)
    db_path = str(tmp_path / "tcg.db")
    db.init_db(db_path, str(path))
    connection = db.connect(db_path)
    assert connection.execute("SELECT search_name FROM cards WHERE id = 'base1-4'").fetchone()[0] == "goupix d'alola"
    connection.close()


def test_older_databases_gain_the_language_columns(tmp_path, catalog_file):
    db_path = str(tmp_path / "old.db")
    old = sqlite3.connect(db_path)
    old.executescript(
        "CREATE TABLE sets (id TEXT PRIMARY KEY, series_id TEXT NOT NULL, name TEXT NOT NULL, release_date TEXT,"
        " card_count_official INTEGER, card_count_total INTEGER, logo_url TEXT, symbol_url TEXT);"
        "CREATE TABLE cards (id TEXT PRIMARY KEY, set_id TEXT NOT NULL, local_id TEXT NOT NULL, local_number INTEGER,"
        " name TEXT NOT NULL, search_name TEXT NOT NULL, category TEXT NOT NULL, rarity TEXT, rarity_rank INTEGER,"
        " illustrator TEXT, hp INTEGER, types TEXT, stage TEXT, image_base TEXT, variants TEXT NOT NULL, details TEXT,"
        " UNIQUE (set_id, local_id));"
    )
    old.close()
    db.init_db(db_path, str(catalog_file))
    connection = db.connect(db_path)
    assert connection.execute("SELECT lang FROM cards WHERE id = 'base1-4'").fetchone()["lang"] == "fr"
    assert connection.execute("SELECT lang FROM sets WHERE id = 'base1'").fetchone()["lang"] == "fr"
    connection.close()
