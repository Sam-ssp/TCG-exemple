import json
from types import SimpleNamespace

import httpx
import openai

from app import chat, collection


def reply(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))])


def tool_call(call_id, name, args):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(args)))


def fake_client(*responses):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        response = responses[min(len(calls), len(responses)) - 1]
        if isinstance(response, Exception):
            raise response
        return response

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


USER_MESSAGE = [{"role": "user", "content": "Ajoute deux Fouinar reverse"}]


def test_no_client_means_unavailable(conn):
    assert chat.run_chat(conn, 1, USER_MESSAGE, "/explorer/", None) == {"reponse": chat.UNAVAILABLE, "actions": []}


def test_plain_answer_sends_prompt_page_and_tools(conn):
    client, calls = fake_client(reply("Bonjour !"))
    assert chat.run_chat(conn, 1, USER_MESSAGE, "/collection/", client) == {"reponse": "Bonjour !", "actions": []}
    sent = calls[0]
    assert sent["model"] == chat.MODEL
    assert sent["messages"][0]["role"] == "system" and "/collection/" in sent["messages"][0]["content"]
    assert sent["messages"][1:] == USER_MESSAGE
    assert len(sent["tools"]) == 7


def test_tool_round_trip_updates_collection(conn):
    client, calls = fake_client(
        reply(tool_calls=[tool_call("c1", "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse", "quantite": 2})]),
        reply("Deux Fouinar reverse ajoutés."),
    )
    result = chat.run_chat(conn, 1, USER_MESSAGE, None, client)
    assert result == {"reponse": "Deux Fouinar reverse ajoutés.", "actions": [{"type": "rafraichir", "cible": "collection"}]}
    assert collection.quantities(conn, 1, "swsh3-136") == {"reverse": 2}
    second = calls[1]["messages"]
    assert second[-2]["role"] == "assistant" and second[-2]["tool_calls"][0]["id"] == "c1"
    assert second[-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"quantites": {"reverse": 2}}'}


def test_duplicate_actions_are_merged(conn):
    calls_twice = [tool_call("c1", "ajouter_collection", {"card_id": "swsh3-136", "variante": "normal"}),
                   tool_call("c2", "ajouter_collection", {"card_id": "swsh3-136", "variante": "reverse"})]
    client, _ = fake_client(reply(tool_calls=calls_twice), reply("Fait."))
    assert chat.run_chat(conn, 1, USER_MESSAGE, None, client)["actions"] == [{"type": "rafraichir", "cible": "collection"}]


def test_api_error_or_timeout_means_unavailable(conn):
    timeout = openai.APITimeoutError(request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"))
    client, _ = fake_client(timeout)
    assert chat.run_chat(conn, 1, USER_MESSAGE, None, client)["reponse"] == chat.UNAVAILABLE


def test_stops_after_max_rounds(conn):
    looping = reply(tool_calls=[tool_call("c", "chercher_cartes", {"nom": "pikachu"})])
    client, calls = fake_client(looping)
    result = chat.run_chat(conn, 1, USER_MESSAGE, None, client)
    assert len(calls) == chat.MAX_ROUNDS + 1  # five tool rounds, then one call for the answer
    assert result["reponse"] == "Je n'ai pas pu terminer cette demande, essayez de la reformuler."


def test_prompt_forbids_emojis_and_markdown():
    # Replies are shown as plain text, and the project bans emojis.
    assert "emoji" in chat.SYSTEM_PROMPT and "Markdown" in chat.SYSTEM_PROMPT


def test_five_tool_rounds_still_get_an_answer(conn):
    search = reply(tool_calls=[tool_call("c", "chercher_cartes", {"nom": "pikachu"})])
    client, calls = fake_client(search, search, search, search, search, reply("Voici."))
    assert chat.run_chat(conn, 1, USER_MESSAGE, None, client)["reponse"] == "Voici."
