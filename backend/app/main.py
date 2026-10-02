import os
import secrets
import sqlite3
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from app import auth, catalog, chat, collection, db
from app.errors import NotFound, RuleError

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Credentials(BaseModel):
    utilisateur: str
    mot_de_passe: str


class QuantityBody(BaseModel):
    quantite: int


class NewList(BaseModel):
    nom: str
    type: collection.ListKind


class ListName(BaseModel):
    nom: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    page: str | None = None


def create_app(db_path: str | None = None, catalog_path: str | None = None,
               static_dir: str | None = None, chat_client=None) -> FastAPI:
    db_path = db_path or os.environ.get("DB_PATH", str(BACKEND_DIR / "tcg.db"))
    catalog_path = catalog_path or os.environ.get("CATALOG_PATH", str(BACKEND_DIR / "data" / "catalog.json.gz"))
    static_dir = static_dir or os.environ.get("STATIC_DIR", str(BACKEND_DIR / "static"))
    db.init_db(db_path, catalog_path)

    app = FastAPI(title="TCG-exemple")
    app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET") or secrets.token_hex(32))

    @app.exception_handler(NotFound)
    def not_found(request: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(RuleError)
    def rule_error(request: Request, exc: RuleError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def get_conn():
        conn = db.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()

    Conn = Annotated[sqlite3.Connection, Depends(get_conn)]
    User = Annotated[int, Depends(auth.current_user)]

    @app.post("/api/connexion")
    def sign_in(body: Credentials, request: Request, conn: Conn):
        return auth.login(conn, request, body.utilisateur, body.mot_de_passe)

    @app.post("/api/deconnexion")
    def sign_out(request: Request):
        request.session.clear()
        return {}

    @app.get("/api/moi")
    def me(user: User, conn: Conn):
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user,)).fetchone()
        return {"id": row["id"], "utilisateur": row["username"]}

    @app.get("/api/groupes")
    def groups(par: catalog.GroupBy, user: User, conn: Conn):
        return catalog.list_groups(conn, par)

    @app.get("/api/cartes")
    def cards(user: User, conn: Conn, set: str | None = None, pokemon: int | None = None,
              illustrateur: str | None = None, rarete: str | None = None, type: str | None = None,
              q: str | None = None, tri: str | None = None, page: int = 1):
        filters = catalog.Filters(set=set, pokemon=pokemon, illustrateur=illustrateur, rarete=rarete, type=type, q=q)
        return catalog.search_cards(conn, filters, tri, page, user_id=user)

    @app.get("/api/cartes/{card_id}")
    def card(card_id: str, user: User, conn: Conn):
        return {
            **catalog.get_card(conn, card_id),
            "quantites": collection.quantities(conn, user, card_id),
            "listes": collection.lists_containing(conn, user, card_id),
        }

    @app.get("/api/collection")
    def my_collection(user: User, conn: Conn, tri: str | None = None, page: int = 1):
        return catalog.search_cards(conn, catalog.Filters(proprietaire=user), tri, page, user_id=user)

    @app.put("/api/collection/{card_id}/{variant}")
    def set_quantity(card_id: str, variant: str, body: QuantityBody, user: User, conn: Conn):
        return {"quantites": collection.set_quantity(conn, user, card_id, variant, body.quantite)}

    @app.get("/api/listes")
    def lists(user: User, conn: Conn):
        return collection.user_lists(conn, user)

    @app.post("/api/listes")
    def create_list(body: NewList, user: User, conn: Conn):
        return collection.create_list(conn, user, body.nom, body.type)

    @app.get("/api/listes/{list_id}")
    def get_list(list_id: int, user: User, conn: Conn, tri: str | None = None, page: int = 1):
        summary = collection.get_list(conn, user, list_id)
        return {**summary, "cartes": catalog.search_cards(conn, catalog.Filters(liste=list_id), tri, page, user_id=user)}

    @app.patch("/api/listes/{list_id}")
    def rename_list(list_id: int, body: ListName, user: User, conn: Conn):
        return collection.rename_list(conn, user, list_id, body.nom)

    @app.delete("/api/listes/{list_id}")
    def delete_list(list_id: int, user: User, conn: Conn):
        collection.delete_list(conn, user, list_id)
        return {}

    @app.post("/api/listes/{list_id}/cartes/{card_id}")
    def add_to_list(list_id: int, card_id: str, user: User, conn: Conn):
        collection.add_to_list(conn, user, list_id, card_id)
        return {}

    @app.delete("/api/listes/{list_id}/cartes/{card_id}")
    def remove_from_list(list_id: int, card_id: str, user: User, conn: Conn):
        collection.remove_from_list(conn, user, list_id, card_id)
        return {}

    @app.post("/api/chat")
    def chat_route(body: ChatRequest, user: User, conn: Conn):
        client = chat_client or chat.make_client()
        messages = [m.model_dump() for m in body.messages[-20:]]
        return chat.run_chat(conn, user, messages, body.page, client)

    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app
