"use client";

import { ArrowLeft, X } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { IconButton } from "@/components/IconButton";
import { Pagination } from "@/components/Pagination";
import { CardsSkeleton } from "@/components/Skeleton";
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
  if (!data) return <CardsSkeleton />;

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
      <div className="page-head">
        <div className="title-row">
          <Link className="icon-button plain" href="/listes/" aria-label="Mes listes" data-tip="Mes listes">
            <ArrowLeft />
          </Link>
          <h1>{data.nom}</h1>
          <span className={`pill ${data.type}`}>{LIST_KIND_LABELS[data.type]}</span>
          <span className="muted">{data.nombre === 1 ? "1 carte" : `${data.nombre} cartes`}</span>
        </div>
      </div>
      {message && <p className="error">{message}</p>}
      {data.nombre === 0 ? (
        <p className="empty">
          Liste vide. <Link href="/explorer/">Parcourir les cartes</Link>
        </p>
      ) : (
        <CardGrid
          cards={data.cartes.cartes}
          renderAction={(card) => (
            <IconButton label={`Retirer ${card.nom} de la liste`} icon={X} tone="solid" onClick={() => removeCard(card.id)} />
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
