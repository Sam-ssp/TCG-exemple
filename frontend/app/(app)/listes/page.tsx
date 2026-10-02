"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { type CardList, LIST_KIND_LABELS, type ListKind } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ListsPage() {
  const { data, error, reload } = useApi<CardList[]>("/api/listes", ["listes"]);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ListKind>("souhaits");
  const [message, setMessage] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>) {
    setMessage(null);
    try {
      await action();
      reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  function create(event: FormEvent) {
    event.preventDefault();
    run(async () => {
      await api("/api/listes", { method: "POST", body: { nom: name, type: kind } });
      setName("");
    });
  }

  function rename(list: CardList) {
    const nom = window.prompt("Nouveau nom de la liste", list.nom);
    if (nom) run(() => api(`/api/listes/${list.id}`, { method: "PATCH", body: { nom } }));
  }

  function remove(list: CardList) {
    if (window.confirm(`Supprimer la liste « ${list.nom} » ?`)) run(() => api(`/api/listes/${list.id}`, { method: "DELETE" }));
  }

  return (
    <section>
      <h1>Mes listes</h1>
      <form className="form-row" onSubmit={create}>
        <input className="input" placeholder="Nom de la nouvelle liste" value={name} onChange={(e) => setName(e.target.value)} />
        <select value={kind} onChange={(e) => setKind(e.target.value as ListKind)}>
          <option value="souhaits">Recherchées (n&apos;importe quelle carte)</option>
          <option value="collection">Collection (cartes possédées)</option>
        </select>
        <button className="button" type="submit" disabled={!name.trim()}>
          Créer
        </button>
      </form>
      {message && <p className="error">{message}</p>}
      {error && <p className="error">{error}</p>}
      {data && data.length === 0 && <p className="empty">Aucune liste pour le moment.</p>}
      <ul className="lists">
        {data?.map((list) => (
          <li key={list.id} className="list-row">
            <Link href={`/listes/voir/?id=${list.id}`}>{list.nom}</Link>
            <span className="muted">
              {LIST_KIND_LABELS[list.type]} · {list.nombre} cartes
            </span>
            <button className="button secondary" onClick={() => rename(list)}>
              Renommer
            </button>
            <button className="button danger" onClick={() => remove(list)}>
              Supprimer
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
