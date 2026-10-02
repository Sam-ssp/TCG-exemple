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
