import pytest

from app import catalog
from app.catalog import Filters
from app.errors import NotFound, RuleError


def ids(result):
    return [card["id"] for card in result["cartes"]]


def test_default_order_is_release_date_then_number(conn):
    result = catalog.search_cards(conn, Filters())
    assert result["total"] == 10
    assert ids(result)[:4] == ["base1-4", "base1-58", "base1-88", "base1-98"]
    assert ids(result)[-4:] == ["swsh4-44", "swsh4-188", "swsh4-200", "swsh4-?"]


def test_filters(conn):
    assert ids(catalog.search_cards(conn, Filters(set="swsh3"))) == ["swsh3-20", "swsh3-136"]
    assert ids(catalog.search_cards(conn, Filters(pokemon=25))) == ["base1-58", "swsh4-44", "swsh4-188", "swsh4-200"]
    assert catalog.search_cards(conn, Filters(illustrateur="MITSUHIRO ARITA"))["total"] == 4
    assert ids(catalog.search_cards(conn, Filters(rarete="Ultra Rare"))) == ["swsh4-188", "swsh4-200"]
    assert ids(catalog.search_cards(conn, Filters(type="Feu"))) == ["base1-4", "swsh3-20"]
    assert ids(catalog.search_cards(conn, Filters(type="Feu", set="base1"))) == ["base1-4"]


def test_search_is_literal_and_accent_insensitive(conn):
    assert ids(catalog.search_cards(conn, Filters(q="dracau"))) == ["base1-4", "swsh3-20"]
    assert ids(catalog.search_cards(conn, Filters(q="ENERGIE"))) == ["base1-98"]
    assert ids(catalog.search_cards(conn, Filters(q="zarbi ?"))) == ["swsh4-?"]
    assert catalog.search_cards(conn, Filters(q="%"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="_"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="dracaufeu%"))["total"] == 0
    assert catalog.search_cards(conn, Filters(q="l'"))["total"] == 0


def test_sort_by_hp_desc_puts_nulls_last(conn):
    result = ids(catalog.search_cards(conn, Filters(), tri="pv:desc"))
    assert result[:2] == ["swsh3-20", "swsh4-188"]
    assert result[-2:] == ["base1-88", "base1-98"]


def test_sort_by_rarity_breaks_ties_by_date_then_number(conn):
    result = ids(catalog.search_cards(conn, Filters(), tri="rarete:desc"))
    assert result[:4] == ["swsh3-20", "swsh4-188", "swsh4-200", "base1-4"]
    assert result[-1] == "base1-98"


def test_sort_by_number_and_combined_sort(conn):
    assert ids(catalog.search_cards(conn, Filters(set="swsh4"), tri="numero:desc")) == ["swsh4-200", "swsh4-188", "swsh4-44", "swsh4-?"]
    assert ids(catalog.search_cards(conn, Filters(pokemon=25), tri="nom:asc,pv:desc")) == ["swsh4-44", "base1-58", "swsh4-200", "swsh4-188"]
    assert ids(catalog.search_cards(conn, Filters(type="Électrique"), tri="pokedex:asc"))[0] == "base1-58"


def test_invalid_sort_and_page(conn):
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), tri="prix:desc")
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), tri="nom:up")
    with pytest.raises(RuleError):
        catalog.search_cards(conn, Filters(), page=0)


def test_pagination(conn):
    result = catalog.search_cards(conn, Filters(), page=2, page_size=3)
    assert ids(result) == ["base1-98", "swsh3-20", "swsh3-136"]
    assert result["pages"] == 4
    assert catalog.search_cards(conn, Filters(), page=9, page_size=3)["cartes"] == []


def test_card_summary_fields(conn):
    card = catalog.search_cards(conn, Filters(set="swsh3"), user_id=1)["cartes"][1]
    assert card == {
        "id": "swsh3-136", "nom": "Fouinar", "set_id": "swsh3", "set_nom": "Ténèbres Embrasées",
        "numero": "136", "rarete": "Peu Commune", "illustrateur": "tetsuya koizumi", "pv": 110,
        "image": "https://assets.tcgdex.net/fr/test/swsh3/136", "quantite": 0,
    }


def test_groups(conn):
    sets = catalog.list_groups(conn, "set")
    assert [(g["valeur"], g["groupe"], g["nombre"]) for g in sets] == [
        ("base1", "Base", 4), ("swsh3", "Épée et Bouclier", 2), ("swsh4", "Épée et Bouclier", 4),
    ]
    pokemon = catalog.list_groups(conn, "pokemon")
    assert [(g["valeur"], g["nom"], g["nombre"]) for g in pokemon][:2] == [("6", "Dracaufeu", 2), ("25", "Pikachu", 4)]
    assert [g["nom"] for g in catalog.list_groups(conn, "illustrateur")] == [
        "aky CG Works", "Ken Sugimori", "Mitsuhiro Arita", "tetsuya koizumi",
    ]
    assert [g["nom"] for g in catalog.list_groups(conn, "rarete")] == [
        "Commune", "Peu Commune", "Rare", "Rare Holo", "Holo Rare VMAX", "Ultra Rare",
    ]


def test_get_card(conn):
    card = catalog.get_card(conn, "swsh4-200")
    assert card["nom"] == "Pikachu et Zekrom GX"
    assert card["set_nom"] == "Voltage Éclatant"
    assert card["serie_nom"] == "Épée et Bouclier"
    assert card["variantes"] == ["holo"]
    assert card["types"] == ["Électrique"]
    assert card["pokemon"] == [{"dex_id": 25, "nom": "Pikachu"}, {"dex_id": 644, "nom": "Pikachu et Zekrom GX"}]
    with pytest.raises(NotFound):
        catalog.get_card(conn, "nope-1")


def test_sets_without_cards_are_not_listed(conn):
    conn.execute("INSERT INTO sets (id, series_id, name) VALUES ('jumbo', 'base', 'Cartes Jumbo')")
    conn.commit()
    assert "jumbo" not in [g["valeur"] for g in catalog.list_groups(conn, "set")]


def test_empty_illustrator_is_not_a_group(conn):
    # Some French TCGdex cards carry illustrator "" instead of no value.
    conn.execute("UPDATE cards SET illustrator = '' WHERE id = 'base1-98'")
    conn.commit()
    assert "" not in [g["valeur"] for g in catalog.list_groups(conn, "illustrateur")]
