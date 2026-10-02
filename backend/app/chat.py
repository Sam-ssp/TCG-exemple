import os
import sqlite3

import openai

from app import tools

MODEL = "openai/gpt-oss-120b"
MAX_ROUNDS = 5
UNAVAILABLE = "Le service IA est indisponible, réessayez."
GAVE_UP = "Je n'ai pas pu terminer cette demande, essayez de la reformuler."

SYSTEM_PROMPT = """Tu es l'assistant de TCG-exemple, une application de collection de cartes Pokémon en français.
Réponds toujours en français, en une ou deux phrases, en texte simple : jamais d'emoji ni de mise en forme Markdown.
Utilise les outils pour chercher des cartes, gérer la collection et les listes de l'utilisateur, et changer l'affichage de la page Explorer.
Avant d'ajouter ou de retirer une carte, trouve son identifiant avec chercher_cartes. Si plusieurs cartes correspondent, ne devine pas : demande laquelle, ou montre-les avec afficher_navigation.
Pour trouver l'identifiant d'une extension, le numéro d'un Pokémon, un illustrateur ou une rareté, utilise lister_groupes.
Quand l'utilisateur veut voir ou trier des cartes, utilise afficher_navigation.
Tris possibles : nom, pokedex, pv, rarete, illustrateur, date_sortie, numero, chacun suivi de :asc ou :desc, séparés par des virgules."""


def make_client() -> openai.OpenAI | None:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    return openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key, timeout=30, max_retries=1)


def _unique(actions: list[dict]) -> list[dict]:
    return [action for i, action in enumerate(actions) if action not in actions[:i]]


def run_chat(conn: sqlite3.Connection, user_id: int, messages: list[dict], page: str | None, client) -> dict:
    if client is None:
        return {"reponse": UNAVAILABLE, "actions": []}
    history = [{"role": "system", "content": f"{SYSTEM_PROMPT}\nPage actuelle : {page or 'inconnue'}"}, *messages]
    actions: list[dict] = []
    try:
        # Up to MAX_ROUNDS rounds of tool calls, plus one call for the final answer.
        for round_number in range(MAX_ROUNDS + 1):
            message = client.chat.completions.create(
                model=MODEL, messages=history, tools=tools.TOOL_SCHEMAS
            ).choices[0].message
            if not message.tool_calls:
                return {"reponse": message.content or "", "actions": _unique(actions)}
            if round_number == MAX_ROUNDS:
                break
            history.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {"id": call.id, "type": "function",
                     "function": {"name": call.function.name, "arguments": call.function.arguments}}
                    for call in message.tool_calls
                ],
            })
            for call in message.tool_calls:
                result = tools.run_tool(conn, user_id, call.function.name, call.function.arguments, actions)
                history.append({"role": "tool", "tool_call_id": call.id, "content": result})
    except openai.APIError:
        return {"reponse": UNAVAILABLE, "actions": _unique(actions)}
    return {"reponse": GAVE_UP, "actions": _unique(actions)}
