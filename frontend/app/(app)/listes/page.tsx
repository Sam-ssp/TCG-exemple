"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { type CardList, LIST_KIND_LABELS, type ListKind } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const KINDS: ListKind[] = ["souhaits", "collection"];

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
      <div className="page-head">
        <div>
          <h1>Mes listes</h1>
          <p>Une liste Collection range des cartes que vous possédez ; une liste Recherchées accepte n&apos;importe quelle carte.</p>
        </div>
      </div>
      <form className="create-list" onSubmit={create}>
        <input className="field" placeholder="Nom de la nouvelle liste" aria-label="Nom de la nouvelle liste" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="segmented" role="group" aria-label="Type de liste">
          {KINDS.map((k) => (
            <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
              {LIST_KIND_LABELS[k]}
            </button>
          ))}
        </div>
        <button className="button" type="submit" disabled={!name.trim()}>
          Créer la liste
        </button>
      </form>
      {message && <p className="error">{message}</p>}
      {error && <p className="error">{error}</p>}
      {data && data.length === 0 && <p className="empty">Aucune liste pour l&apos;instant. Donnez un nom à votre première liste ci-dessus.</p>}
      <ul className="lists">
        {data?.map((list) => (
          <li key={list.id} className="list-row">
            <Link href={`/listes/voir/?id=${list.id}`}>{list.nom}</Link>
            <span className={`badge ${list.type}`}>{LIST_KIND_LABELS[list.type]}</span>
            <span className="grow muted">{list.nombre === 1 ? "1 carte" : `${list.nombre} cartes`}</span>
            <button className="button quiet" onClick={() => rename(list)}>
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
