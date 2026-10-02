UNAVAILABLE = "Le service IA est indisponible, réessayez."


def make_client():
    return None


def run_chat(conn, user_id, messages, page, client) -> dict:
    return {"reponse": UNAVAILABLE, "actions": []}
