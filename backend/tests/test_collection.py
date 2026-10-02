import pytest

from app import catalog, collection
from app.catalog import Filters
from app.errors import NotFound, RuleError


def test_set_quantity_per_variant(conn):
    assert collection.set_quantity(conn, 1, "base1-4", "holo", 2) == {"holo": 2}
    assert collection.set_quantity(conn, 1, "base1-4", "firstEdition", 1) == {"holo": 2, "firstEdition": 1}
    assert collection.set_quantity(conn, 1, "base1-4", "holo", 0) == {"firstEdition": 1}


def test_set_quantity_rejects_bad_values(conn):
    with pytest.raises(RuleError, match="Variante"):
        collection.set_quantity(conn, 1, "base1-4", "reverse", 1)
    with pytest.raises(RuleError, match="Variante"):
        collection.set_quantity(conn, 1, "base1-4", "brillante", 1)
    with pytest.raises(RuleError, match="Quantité"):
        collection.set_quantity(conn, 1, "base1-4", "holo", -1)
    with pytest.raises(RuleError, match="Quantité"):
        collection.set_quantity(conn, 1, "base1-4", "holo", collection.MAX_QUANTITY + 1)
    with pytest.raises(NotFound):
        collection.set_quantity(conn, 1, "nope-1", "normal", 1)


def test_add_copies_accumulates(conn):
    collection.add_copies(conn, 1, "swsh3-136", "reverse", 2)
    assert collection.add_copies(conn, 1, "swsh3-136", "reverse", 3) == {"reverse": 5}
    with pytest.raises(RuleError):
        collection.add_copies(conn, 1, "swsh3-136", "reverse", 0)


def test_remove_copies_floors_at_zero_and_cleans_lists(conn):
    collection.add_copies(conn, 1, "swsh3-136", "normal", 1)
    collection.add_copies(conn, 1, "swsh3-136", "reverse", 1)
    owned = collection.create_list(conn, 1, "Classeur", "collection")
    wished = collection.create_list(conn, 1, "Recherchées", "souhaits")
    collection.add_to_list(conn, 1, owned["id"], "swsh3-136")
    collection.add_to_list(conn, 1, wished["id"], "swsh3-136")

    collection.remove_copies(conn, 1, "swsh3-136", "normal", 5)
    assert collection.get_list(conn, 1, owned["id"])["nombre"] == 1  # still owns the reverse

    assert collection.remove_copies(conn, 1, "swsh3-136", "reverse", 5) == {}
    assert collection.get_list(conn, 1, owned["id"])["nombre"] == 0
    assert collection.get_list(conn, 1, wished["id"])["nombre"] == 1


def test_collection_list_accepts_only_owned_cards(conn):
    owned = collection.create_list(conn, 1, "Classeur", "collection")
    with pytest.raises(RuleError, match="possédées"):
        collection.add_to_list(conn, 1, owned["id"], "base1-4")
    wished = collection.create_list(conn, 1, "Recherchées", "souhaits")
    collection.add_to_list(conn, 1, wished["id"], "base1-4")
    collection.add_to_list(conn, 1, wished["id"], "base1-4")  # adding twice is harmless
    assert collection.get_list(conn, 1, wished["id"])["nombre"] == 1
    with pytest.raises(NotFound):
        collection.add_to_list(conn, 1, wished["id"], "nope-1")


def test_duplicate_list_name_is_rule_error(conn):
    collection.create_list(conn, 1, "Favoris", "souhaits")
    with pytest.raises(RuleError, match="existe déjà"):
        collection.create_list(conn, 1, "Favoris", "collection")
    other = collection.create_list(conn, 1, "Autre", "souhaits")
    with pytest.raises(RuleError, match="existe déjà"):
        collection.rename_list(conn, 1, other["id"], "Favoris")
    with pytest.raises(RuleError):
        collection.create_list(conn, 1, "   ", "souhaits")
    with pytest.raises(RuleError):
        collection.create_list(conn, 1, "Mauvais type", "vitrine")


def test_lists_are_private_to_their_user(conn):
    conn.execute("INSERT INTO users (id, username) VALUES (2, 'autre')")
    conn.commit()
    mine = collection.create_list(conn, 1, "Favoris", "souhaits")
    with pytest.raises(NotFound):
        collection.get_list(conn, 2, mine["id"])
    with pytest.raises(NotFound):
        collection.delete_list(conn, 2, mine["id"])
    assert collection.user_lists(conn, 2) == []


def test_list_management(conn):
    first = collection.create_list(conn, 1, "Favoris", "souhaits")
    assert first == {"id": first["id"], "nom": "Favoris", "type": "souhaits", "nombre": 0}
    collection.add_to_list(conn, 1, first["id"], "swsh4-?")
    assert collection.find_list(conn, 1, "favoris")["id"] == first["id"]
    assert collection.rename_list(conn, 1, first["id"], "Préférées")["nom"] == "Préférées"
    assert collection.lists_containing(conn, 1, "swsh4-?") == [{"id": first["id"], "nom": "Préférées", "type": "souhaits"}]
    collection.remove_from_list(conn, 1, first["id"], "swsh4-?")
    assert collection.lists_containing(conn, 1, "swsh4-?") == []
    collection.delete_list(conn, 1, first["id"])
    assert collection.user_lists(conn, 1) == []
    with pytest.raises(NotFound):
        collection.find_list(conn, 1, "Préférées")


def test_owned_cards_through_search(conn):
    collection.add_copies(conn, 1, "base1-4", "holo", 2)
    collection.add_copies(conn, 1, "base1-4", "firstEdition", 1)
    result = catalog.search_cards(conn, Filters(proprietaire=1), user_id=1)
    assert [(c["id"], c["quantite"]) for c in result["cartes"]] == [("base1-4", 3)]
