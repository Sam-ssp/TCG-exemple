def test_routes_require_sign_in(make_client):
    anonymous = make_client()
    assert anonymous.get("/api/cartes").status_code == 401
    assert anonymous.get("/api/moi").status_code == 401


def test_sign_in_and_out(make_client):
    session = make_client()
    bad = session.post("/api/connexion", json={"utilisateur": "user", "mot_de_passe": "faux"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "Identifiants incorrects"
    ok = session.post("/api/connexion", json={"utilisateur": "user", "mot_de_passe": "user"})
    assert ok.json() == {"id": 1, "utilisateur": "user"}
    assert session.get("/api/moi").json() == {"id": 1, "utilisateur": "user"}
    session.post("/api/deconnexion")
    assert session.get("/api/moi").status_code == 401


def test_groups_and_cards(client):
    assert [g["valeur"] for g in client.get("/api/groupes", params={"par": "set"}).json()] == ["swsh4", "swsh3", "base1"]
    assert client.get("/api/groupes", params={"par": "prix"}).status_code == 422
    page = client.get("/api/cartes", params={"pokemon": 25, "tri": "pv:desc"}).json()
    assert page["total"] == 4 and page["cartes"][0]["id"] == "swsh4-188"
    assert client.get("/api/cartes", params={"tri": "prix:asc"}).json()["detail"] == "Tri invalide : prix:asc"


def test_card_with_question_mark_id(client):
    response = client.get("/api/cartes/swsh4-%3F")
    assert response.status_code == 200
    assert response.json()["nom"] == "Zarbi ?"
    assert response.json()["quantites"] == {} and response.json()["listes"] == []
    assert client.get("/api/cartes/nope-1").status_code == 404


def test_collection_routes(client):
    response = client.put("/api/collection/base1-4/holo", json={"quantite": 2})
    assert response.json() == {"quantites": {"holo": 2}}
    assert client.put("/api/collection/base1-4/reverse", json={"quantite": 1}).status_code == 400
    assert client.put("/api/collection/base1-4/holo", json={"quantite": -3}).status_code == 400
    owned = client.get("/api/collection").json()
    assert [(c["id"], c["quantite"]) for c in owned["cartes"]] == [("base1-4", 2)]
    assert client.get("/api/cartes/base1-4").json()["quantites"] == {"holo": 2}


def test_list_routes(client):
    created = client.post("/api/listes", json={"nom": "Favoris", "type": "souhaits"}).json()
    assert created["nom"] == "Favoris" and created["nombre"] == 0
    duplicate = client.post("/api/listes", json={"nom": "Favoris", "type": "souhaits"})
    assert duplicate.status_code == 400 and "existe déjà" in duplicate.json()["detail"]
    list_id = created["id"]
    assert client.post(f"/api/listes/{list_id}/cartes/swsh4-%3F").status_code == 200
    detail = client.get(f"/api/listes/{list_id}").json()
    assert detail["nombre"] == 1 and detail["cartes"]["cartes"][0]["id"] == "swsh4-?"
    assert client.patch(f"/api/listes/{list_id}", json={"nom": "Préférées"}).json()["nom"] == "Préférées"
    assert client.get("/api/listes").json()[0]["nom"] == "Préférées"
    assert client.delete(f"/api/listes/{list_id}/cartes/swsh4-%3F").status_code == 200
    assert client.delete(f"/api/listes/{list_id}").status_code == 200
    assert client.get(f"/api/listes/{list_id}").status_code == 404
    collection_list = client.post("/api/listes", json={"nom": "Classeur", "type": "collection"}).json()
    refused = client.post(f"/api/listes/{collection_list['id']}/cartes/base1-4")
    assert refused.status_code == 400


def test_chat_without_key_answers_unavailable(client, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Bonjour"}], "page": "/explorer/"})
    assert response.json() == {"reponse": "Le service IA est indisponible, réessayez.", "actions": []}
