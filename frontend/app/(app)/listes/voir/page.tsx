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
      <p>
        <Link href="/listes/">Mes listes</Link>
      </p>
      <h1>{data.nom}</h1>
      <p className="muted">
        {LIST_KIND_LABELS[data.type]} · {data.nombre} cartes
      </p>
      {message && <p className="error">{message}</p>}
      <CardGrid
        cards={data.cartes.cartes}
        renderAction={(card) => (
          <button className="button secondary" onClick={() => removeCard(card.id)}>
            Retirer
          </button>
        )}
      />
      <Pagination
        page={data.cartes.page}
        pages={data.cartes.pages}
        onPage={(p) => router.push(`/listes/voir/${toQuery({ id, page: p > 1 ? p : undefined })}`)}
      />
    </section>
  );
}
