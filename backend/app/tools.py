import json
import sqlite3
from urllib.parse import urlencode

from pydantic import BaseModel, Field, ValidationError

from app import catalog, collection
from app.errors import NotFound, RuleError
from app.text import normalize

REFRESH_COLLECTION = {"type": "rafraichir", "cible": "collection"}
REFRESH_LISTS = {"type": "rafraichir", "cible": "listes"}


class ChercherCartes(BaseModel):
    """Chercher des cartes dans le catalogue (20 au maximum)."""

    nom: str | None = Field(None, description="Partie du nom de la carte, ex. dracaufeu")
    set: str | None = Field(None, description="Identifiant d'extension, ex. swsh3 (voir lister_groupes)")
    pokemon: int | None = Field(None, description="Numéro de Pokédex national, ex. 25")
    illustrateur: str | None = None
    rarete: str | None = Field(None, description="Rareté exacte, ex. Ultra Rare (voir lister_groupes)")
    type: str | None = Field(None, description="Type en français, ex. Feu, Eau, Électrique")
    tri: str | None = Field(None, description="Tri, ex. pv:desc,nom:asc")
    limite: int = Field(10, ge=1, le=20)


class ListerGroupes(BaseModel):
    """Trouver des extensions, Pokémon, illustrateurs ou raretés par leur nom."""

    par: catalog.GroupBy
    filtre: str | None = Field(None, description="Partie du nom recherché")


class ModifierCollection(BaseModel):
    card_id: str = Field(description="Identifiant de carte, ex. swsh3-136")
    variante: collection.Variant = "normal"
    quantite: int = Field(1, ge=1, le=100)


class AjouterCollection(ModifierCollection):
    """Ajouter des exemplaires d'une carte à la collection de l'utilisateur."""


class RetirerCollection(ModifierCollection):
    """Retirer des exemplaires d'une carte de la collection de l'utilisateur."""


class CreerListe(BaseModel):
    """Créer une liste : 'collection' (cartes possédées) ou 'souhaits' (n'importe quelle carte)."""

    nom: str
    type: collection.ListKind


class AjouterAListe(BaseModel):
    """Ajouter des cartes à une liste existante, désignée par son nom."""

    liste: str
    card_ids: list[str] = Field(min_length=1, max_length=50)


class AfficherNavigation(BaseModel):
    """Afficher des cartes dans la page Explorer avec ces filtres et ce tri."""

    par: catalog.GroupBy = Field("set", description="Onglet affiché")
    set: str | None = None
    pokemon: int | None = None
    illustrateur: str | None = None
    rarete: str | None = None
    type: str | None = None
    q: str | None = Field(None, description="Recherche par nom")
    tri: str | None = None


def chercher_cartes(conn, user_id, args: ChercherCartes, actions):
    filters = catalog.Filters(set=args.set, pokemon=args.pokemon, illustrateur=args.illustrateur,
                              rarete=args.rarete, type=args.type, q=args.nom)
    result = catalog.search_cards(conn, filters, args.tri, 1, user_id, page_size=args.limite)
    keys = ("id", "nom", "set_nom", "numero", "rarete", "quantite")
    return {"total": result["total"], "cartes": [{k: card[k] for k in keys} for card in result["cartes"]]}


def lister_groupes(conn, user_id, args: ListerGroupes, actions):
    groups = catalog.list_groups(conn, args.par)
    if args.filtre:
        needle = normalize(args.filtre)
        groups = [g for g in groups if needle in normalize(g["nom"])]
    return {"total": len(groups), "groupes": groups[:20]}


def ajouter_collection(conn, user_id, args: AjouterCollection, actions):
    result = collection.add_copies(conn, user_id, args.card_id, args.variante, args.quantite)
    actions.append(REFRESH_COLLECTION)
    return {"quantites": result}


def retirer_collection(conn, user_id, args: RetirerCollection, actions):
    result = collection.remove_copies(conn, user_id, args.card_id, args.variante, args.quantite)
    actions.append(REFRESH_COLLECTION)
    return {"quantites": result}


def creer_liste(conn, user_id, args: CreerListe, actions):
    result = collection.create_list(conn, user_id, args.nom, args.type)
    actions.append(REFRESH_LISTS)
    return result


def ajouter_a_liste(conn, user_id, args: AjouterAListe, actions):
    card_list = collection.find_list(conn, user_id, args.liste)
    added, errors = [], {}
    for card_id in args.card_ids:
        try:
            collection.add_to_list(conn, user_id, card_list["id"], card_id)
            added.append(card_id)
        except (NotFound, RuleError) as exc:
            errors[card_id] = str(exc)
    if added:
        actions.append(REFRESH_LISTS)
    return {"ajoutees": added, "erreurs": errors}


def afficher_navigation(conn, user_id, args: AfficherNavigation, actions):
    catalog.parse_sort(args.tri)  # raises RuleError before the page gets a bad sort
    params = {key: value for key, value in args.model_dump().items() if value is not None}
    url = "/explorer/?" + urlencode(params)
    actions.append({"type": "naviguer", "url": url})
    return {"url": url}


TOOLS = {
    "chercher_cartes": (ChercherCartes, chercher_cartes),
    "lister_groupes": (ListerGroupes, lister_groupes),
    "ajouter_collection": (AjouterCollection, ajouter_collection),
    "retirer_collection": (RetirerCollection, retirer_collection),
    "creer_liste": (CreerListe, creer_liste),
    "ajouter_a_liste": (AjouterAListe, ajouter_a_liste),
    "afficher_navigation": (AfficherNavigation, afficher_navigation),
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": name, "description": model.__doc__, "parameters": model.model_json_schema()}}
    for name, (model, _) in TOOLS.items()
]


def run_tool(conn: sqlite3.Connection, user_id: int, name: str, arguments: str, actions: list[dict]) -> str:
    """Run one tool call; errors are returned to the model as text so it can correct itself."""
    if name not in TOOLS:
        return json.dumps({"erreur": f"Outil inconnu : {name}"}, ensure_ascii=False)
    model, function = TOOLS[name]
    try:
        result = function(conn, user_id, model.model_validate_json(arguments or "{}"), actions)
    except ValidationError as exc:
        result = {"erreur": f"Arguments invalides : {exc.errors(include_url=False, include_context=False)}"}
    except (NotFound, RuleError) as exc:
        result = {"erreur": str(exc)}
    return json.dumps(result, ensure_ascii=False, default=str)
