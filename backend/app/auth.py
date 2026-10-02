import sqlite3

from fastapi import HTTPException, Request

# MVP: one hardcoded account. The users table already supports more.
USERNAME = "user"
PASSWORD = "user"


def login(conn: sqlite3.Connection, request: Request, username: str, password: str) -> dict:
    if username != USERNAME or password != PASSWORD:
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    row = conn.execute("SELECT id, username FROM users WHERE username = ?", (username,)).fetchone()
    request.session["user_id"] = row["id"]
    return {"id": row["id"], "utilisateur": row["username"]}


def current_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Non connecté")
    return user_id
