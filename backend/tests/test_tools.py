import json

from app import collection, tools


def run(conn, name, args, actions=None):
    actions = [] if actions is None else actions
    return json.loads(tools.run_tool(conn, 1, name, json.dumps(args), actions)), actions


def test_schemas_list_every_tool():
    names = [schema["function"]["name"] for schema in tools.TOOL_SCHEMAS]
    assert names == ["chercher_cartes", "lister_groupes", "ajouter_collection", "retirer_collection",
                     "creer_liste", "ajouter_a_liste", "afficher_navigation"]
    assert all(schema["function"]["description"] for schema in tools.TOOL_SCHEMAS)


def test_chercher_cartes(conn):
    result, actions = run(conn, "chercher_cartes", {"nom": "pikachu", "tri": "pv:desc", "limite": 2})
    assert result["total"] == 4
    assert result["cartes"] == [
        {"id": "swsh4-188", "nom": "Pikachu VMAX", "set_nom": "Voltage Éclatant", "numero": "188", "rarete": "Ultra Rare", "quantite": 0},
        {"id": "swsh4-200", "nom": "Pikachu et Zekrom GX", "set_nom": "Voltage Éclatant", "numero": "200", "rarete": "Ultra Rare", "quantite": 0},
    ]
    assert actions == []


def test_lister_groupes_matches_without_accents(conn):
    result, _ = run(conn, "lister_groupes", {"par": "set", "filtre": "voltage eclatant"})
    assert [g["valeur"] for g in result["groupes"]] == ["swsh4"]


def test_ajouter_et_retirer_collection(conn):
    result, actions = run(conn, "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse", "quantite": 2})
    assert result == {"quantites": {"reverse": 2}}
    assert actions == [{"type": "rafraichir", "cible": "collection"}]
    result, _ = run(conn, "retirer_collection", {"card_id": "swsh3-136", "variante": "reverse"})
    assert result == {"quantites": {"reverse": 1}}


def test_creer_liste_et_ajouter(conn):
    collection.add_copies(conn, 1, "base1-4", "holo", 1)
    result, actions = run(conn, "creer_liste", {"nom": "Classeur", "type": "collection"})
    assert result["nom"] == "Classeur"
    result, actions = run(conn, "ajouter_a_liste", {"liste": "classeur", "card_ids": ["base1-4", "swsh3-20", "nope-1"]})
    assert result["ajoutees"] == ["base1-4"]
    assert set(result["erreurs"]) == {"swsh3-20", "nope-1"}
    assert actions == [{"type": "rafraichir", "cible": "listes"}]


def test_afficher_navigation(conn):
    result, actions = run(conn, "afficher_navigation", {"par": "illustrateur", "illustrateur": "Ken Sugimori", "tri": "pv:desc"})
    assert result["url"] == "/explorer/?par=illustrateur&illustrateur=Ken+Sugimori&tri=pv%3Adesc"
    assert actions == [{"type": "naviguer", "url": result["url"]}]


def test_run_tool_reports_errors_to_the_model(conn):
    actions = []
    assert "Outil inconnu" in json.loads(tools.run_tool(conn, 1, "vendre", "{}", actions))["erreur"]
    assert "Arguments invalides" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", "{pas du json", actions))["erreur"]
    assert "Arguments invalides" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "base1-4", "quantite": 0}', actions))["erreur"]
    assert json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "nope-1"}', actions)) == {"erreur": "Carte introuvable"}
    assert "Variante" in json.loads(tools.run_tool(conn, 1, "ajouter_collection", '{"card_id": "base1-4"}', actions))["erreur"]
    assert "Tri invalide" in json.loads(tools.run_tool(conn, 1, "afficher_navigation", '{"tri": "prix"}', actions))["erreur"]
    assert actions == []
