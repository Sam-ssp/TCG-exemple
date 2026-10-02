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
