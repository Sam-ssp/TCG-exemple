"use client";

import { Check, Heart, Library, Pencil, Plus, Trash2, X } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { IconButton } from "@/components/IconButton";
import { LinesSkeleton } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { type CardList, LIST_KIND_LABELS, type ListKind } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const KIND_ICONS = { souhaits: Heart, collection: Library };
const KIND_HINTS: Record<ListKind, string> = { souhaits: "N'importe quelle carte", collection: "Seulement des cartes possédées" };
const KINDS: ListKind[] = ["souhaits", "collection"];

export default function ListsPage() {
  const { data, error, reload } = useApi<CardList[]>("/api/listes", ["listes"]);
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ListKind>("souhaits");
  const [editing, setEditing] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<CardList | null>(null);
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
      await api("/api/listes", { method: "POST", body: { nom: name.trim(), type: kind } });
      setName("");
    });
  }

  function rename(list: CardList, nom: string) {
    setEditing(null);
    if (nom && nom !== list.nom) run(() => api(`/api/listes/${list.id}`, { method: "PATCH", body: { nom } }));
  }

  function remove(list: CardList) {
    setDeleting(null);
    run(() => api(`/api/listes/${list.id}`, { method: "DELETE" }));
  }

  return (
    <section>
      <div className="page-head">
        <h1>Mes listes</h1>
      </div>
      <form className="create-list" onSubmit={create}>
        <input placeholder="Nouvelle liste" aria-label="Nom de la nouvelle liste" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="segmented" role="group" aria-label="Type de liste">
          {KINDS.map((k) => {
            const Icon = KIND_ICONS[k];
            return (
              <button key={k} type="button" aria-pressed={kind === k} title={KIND_HINTS[k]} onClick={() => setKind(k)}>
                <Icon />
                {LIST_KIND_LABELS[k]}
              </button>
            );
          })}
        </div>
        <IconButton label="Créer la liste" icon={Plus} tone="solid" type="submit" disabled={!name.trim()} />
      </form>
      {message && <p className="error">{message}</p>}
      {error && <p className="error">{error}</p>}
      {!data && !error && <LinesSkeleton count={4} />}
      {data && data.length === 0 && <p className="empty">Aucune liste. Nommez la première ci-dessus.</p>}
      <ul className="lists">
        {data?.map((list) => {
          const Icon = KIND_ICONS[list.type];
          return (
            <li key={list.id} className="list-row">
              <span className={`list-icon ${list.type}`} title={LIST_KIND_LABELS[list.type]}>
                <Icon />
                <span className="visually-hidden">{LIST_KIND_LABELS[list.type]}</span>
              </span>
              {editing === list.id ? (
                <RenameForm list={list} onDone={(nom) => rename(list, nom)} onCancel={() => setEditing(null)} />
              ) : (
                <>
                  <Link className="grow" href={`/listes/voir/?id=${list.id}`}>
                    {list.nom}
                  </Link>
                  <span className="muted count">{list.nombre === 1 ? "1 carte" : `${list.nombre} cartes`}</span>
                  <span className="row-actions">
                    <IconButton label={`Renommer ${list.nom}`} icon={Pencil} onClick={() => setEditing(list.id)} />
                    <IconButton label={`Supprimer ${list.nom}`} icon={Trash2} tone="danger" onClick={() => setDeleting(list)} />
                  </span>
                </>
              )}
            </li>
          );
        })}
      </ul>
      <ConfirmDialog
        open={deleting !== null}
        title={`Supprimer « ${deleting?.nom ?? ""} » ?`}
        confirmLabel="Supprimer"
        onConfirm={() => deleting && remove(deleting)}
        onClose={() => setDeleting(null)}
      />
    </section>
  );
}

function RenameForm({ list, onDone, onCancel }: { list: CardList; onDone: (nom: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState(list.nom);
  function submit(event: FormEvent) {
    event.preventDefault();
    onDone(value.trim());
  }
  return (
    <form className="rename grow" onSubmit={submit}>
      <input
        aria-label="Nouveau nom de la liste"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onCancel()}
        autoFocus
      />
      <IconButton label="Enregistrer le nom" icon={Check} tone="solid" type="submit" disabled={!value.trim()} />
      <IconButton label="Annuler" icon={X} onClick={onCancel} />
    </form>
  );
}
