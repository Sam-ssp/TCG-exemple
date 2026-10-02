"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { api } from "@/lib/api";
import { toQuery } from "@/lib/query";
import { type CardList, type CardPage, LIST_KIND_LABELS } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function ListViewPage() {
  return (
    <Suspense>
      <ListView />
    </Suspense>
  );
}

function ListView() {
  const router = useRouter();
  const params = useSearchParams();
  const id = params.get("id");
  const page = Number(params.get("page")) || 1;
  const { data, error, reload } = useApi<CardList & { cartes: CardPage }>(
    id ? `/api/listes/${id}${toQuery({ page: page > 1 ? page : undefined })}` : null,
    ["listes", "collection"],
  );
  const [message, setMessage] = useState<string | null>(null);

  if (!id) return <p className="error">Aucune liste choisie.</p>;
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Chargement...</p>;

  async function removeCard(cardId: string) {
    setMessage(null);
    try {
      await api(`/api/listes/${id}/cartes/${encodeURIComponent(cardId)}`, { method: "DELETE" });
      reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  return (
    <section>
      <Link className="back" href="/listes/">
        Mes listes
      </Link>
      <div className="page-head">
        <div>
          <h1>{data.nom}</h1>
          <p>
            <span className={`badge ${data.type}`}>{LIST_KIND_LABELS[data.type]}</span> {data.nombre === 1 ? "1 carte" : `${data.nombre} cartes`}
          </p>
        </div>
      </div>
      {message && <p className="error">{message}</p>}
      {data.nombre === 0 ? (
        <p className="empty">
          Cette liste est vide. Ouvrez une carte depuis <Link href="/explorer/">Explorer</Link> pour l&apos;y ajouter.
        </p>
      ) : (
        <CardGrid
          cards={data.cartes.cartes}
          renderAction={(card) => (
            <button className="button quiet" onClick={() => removeCard(card.id)}>
              Retirer de la liste
            </button>
          )}
        />
      )}
      <Pagination
        page={data.cartes.page}
        pages={data.cartes.pages}
        onPage={(p) => router.push(`/listes/voir/${toQuery({ id, page: p > 1 ? p : undefined })}`)}
      />
    </section>
  );
}
