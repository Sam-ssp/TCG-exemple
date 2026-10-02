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
