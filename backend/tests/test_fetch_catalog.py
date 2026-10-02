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
        "lang": "fr",
        "id": "swsh3", "series_id": "swsh", "name": "Ténèbres Embrasées", "release_date": "2020-08-14",
        "card_count_official": 189, "card_count_total": 201,
        "logo_url": "https://assets.tcgdex.net/fr/swsh/swsh3/logo",
        "symbol_url": "https://assets.tcgdex.net/univ/swsh/swsh3/symbol",
    }


def test_pokemon_names_prefers_single_pokemon_cards():
    cards = [
        {"name": "Pikachu et Zekrom GX", "dex_ids": [25, 644], "lang": "fr"},
        {"name": "Pikachu VMAX", "dex_ids": [25], "lang": "fr"},
        {"name": "Pikachu", "dex_ids": [25], "lang": "fr"},
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


def test_build_card_uses_the_set_that_lists_it():
    # TCGdex fr lists the Arceus AR cards in a set while their own set id (pl4) has no French set.
    raw = {"id": "pl4-AR1", "localId": "AR1", "name": "Arceus", "category": "Pokémon", "set": {"id": "pl4"}}
    assert build_card(raw, set_id="pl3")["set_id"] == "pl3"
    assert build_card(raw)["set_id"] == "pl4"


def test_normalize_unifies_apostrophes_and_ligatures():
    # TCGdex fr mixes ’ and ' in names; keyboards type ' and "oe".
    assert normalize("Goupix d’Alola") == normalize("Goupix d'Alola") == "goupix d'alola"
    assert normalize("Nœunœuf") == "noeunoeuf"
    assert normalize("Æ") == "ae"


def test_subsets_are_filed_under_their_main_set():
    from scripts.fetch_catalog import SUBSETS, merge_subsets

    assert SUBSETS["swsh12.5gg"] == "swsh12.5"  # Zénith Suprême Galerie Galaroise
    assert SUBSETS["rc"] == "bw11"  # Radiant Collection -> Legendary Treasures
    assert SUBSETS["30th-c"] == "30th"
    sets = [
        {"id": "swsh12.5", "card_count_official": 159, "card_count_total": 160},
        {"id": "swsh12.5gg", "card_count_official": 70, "card_count_total": 70},
        {"id": "swsh12", "card_count_official": 195, "card_count_total": 215},
    ]
    assert merge_subsets(sets) == [
        {"id": "swsh12.5", "card_count_official": 159, "card_count_total": 230},
        {"id": "swsh12", "card_count_official": 195, "card_count_total": 215},
    ]


def test_image_candidates_try_french_files_then_english():
    from scripts.fetch_catalog import image_candidates

    card = {"id": "swsh12.5gg-GG01", "local_id": "GG01", "set_id": "swsh12.5"}
    assert image_candidates(card, "swsh", "https://assets.tcgdex.net/en/swsh/swsh12.5/GG01") == [
        "https://assets.tcgdex.net/fr/swsh/swsh12.5/GG01",
        "https://assets.tcgdex.net/en/swsh/swsh12.5/GG01",
    ]
    odd = {"id": "exu-%3F", "local_id": "%3F", "set_id": "ex10"}
    assert image_candidates(odd, "ex", None) == [
        "https://assets.tcgdex.net/fr/ex/ex10/%253F",
        "https://assets.tcgdex.net/en/ex/ex10/%253F",
    ]


RAW_EN_BLASTOISE = {
    "category": "Pokemon", "id": "ex7-2", "localId": "2", "name": "Dark Blastoise", "rarity": "Rare Holo",
    "set": {"id": "ex7"}, "illustrator": "Mitsuhiro Arita", "image": "https://assets.tcgdex.net/en/ex/ex7/2",
    "dexId": [9], "hp": 80, "types": ["Water"], "stage": "Stage2",
    "attacks": [{"cost": ["Water", "Colorless"], "name": "Hydrocannon", "damage": 40}],
}


def test_english_only_cards_are_labelled_and_fit_french_filters():
    card = build_card(RAW_EN_BLASTOISE, lang="en")
    assert card["lang"] == "en"
    assert card["name"] == "Dark Blastoise"  # names and text stay in English
    assert card["category"] == "Pokémon"
    assert json.loads(card["types"]) == ["Eau"]
    assert card["stage"] == "Niveau 2"
    assert card["rarity"] == "Rare Holo"
    assert json.loads(card["details"])["attacks"][0]["cost"] == ["Eau", "Incolore"]
    assert build_card({**RAW_EN_BLASTOISE, "rarity": "Common"}, lang="en")["rarity"] == "Commune"
    assert build_card({**RAW_EN_BLASTOISE, "rarity": "ACE SPEC Rare"}, lang="en")["rarity"] == "HIGH-TECH rare"
    assert build_card(RAW_FOUINAR)["lang"] == "fr"


def test_card_set_prefers_the_cards_own_set_when_it_exists():
    from scripts.fetch_catalog import card_set

    known = {"pl3", "pl4", "swsh12.5"}
    assert card_set("pl4", "pl3", known) == "pl4"  # Arceus AR cards listed in pl3 belong to Arceus
    assert card_set("pl4", "pl3", {"pl3"}) == "pl3"
    assert card_set("swsh12.5gg", "swsh12.5gg", known) == "swsh12.5"


def test_pokemon_names_prefer_french_names():
    cards = [
        {"name": "Charizard", "dex_ids": [6], "lang": "en"},
        {"name": "Dracaufeu", "dex_ids": [6], "lang": "fr"},
        {"name": "Smeargle", "dex_ids": [235], "lang": "en"},
    ]
    assert pokemon_names(cards) == [{"dex_id": 6, "name": "Dracaufeu"}, {"dex_id": 235, "name": "Smeargle"}]


def test_a_set_is_english_only_when_none_of_its_cards_is_french():
    from scripts.fetch_catalog import label_sets

    sets = [{"id": "pl4", "lang": "en"}, {"id": "jumbo", "lang": "fr"}, {"id": "pl3", "lang": "fr"}]
    cards = [
        {"set_id": "pl4", "lang": "fr"}, {"set_id": "pl4", "lang": "en"},
        {"set_id": "jumbo", "lang": "en"}, {"set_id": "pl3", "lang": "fr"},
    ]
    assert [s["lang"] for s in label_sets(sets, cards)] == ["fr", "en", "fr"]



def test_classic_collection_numbers_get_the_cc_prefix_when_merged():
    # 30th-c numbers 001-030 like the main set; TCGdex names the same kind of cards CC001 in Célébrations.
    raw = {"id": "30th-c-001", "localId": "001", "name": "Dracaufeu", "category": "Pokémon", "set": {"id": "30th-c"}}
    card = build_card(raw, "30th")
    assert card["id"] == "30th-c-001"
    assert card["local_id"] == "CC001"
    assert card["local_number"] == 1
    assert build_card({**raw, "set": {"id": "30th"}, "id": "30th-001"}, "30th")["local_id"] == "001"
