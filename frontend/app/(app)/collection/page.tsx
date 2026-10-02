"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { SortSelect } from "@/components/SortSelect";
import { toQuery } from "@/lib/query";
import type { CardPage } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CollectionPage() {
  return (
    <Suspense>
      <Collection />
    </Suspense>
  );
}

function Collection() {
  const router = useRouter();
  const params = useSearchParams();
  const tri = params.get("tri") ?? "";
  const page = Number(params.get("page")) || 1;
  const query = (t: string, p: number) => toQuery({ tri: t, page: p > 1 ? p : undefined });
  const { data, error } = useApi<CardPage>(`/api/collection${query(tri, page)}`, ["collection"]);
  const go = (t: string, p: number) => router.push(`/collection/${query(t, p)}`);

  return (
    <section>
      <h1>Ma collection</h1>
      <div className="toolbar">
        <span className="muted">{data ? `${data.total} cartes différentes` : ""}</span>
        <SortSelect value={tri} onChange={(t) => go(t, 1)} />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          {data.total === 0 && <p className="empty">Votre collection est vide. Ajoutez des cartes depuis Explorer ou avec l&apos;assistant.</p>}
          {data.total > 0 && <CardGrid cards={data.cartes} />}
          <Pagination page={data.page} pages={data.pages} onPage={(p) => go(tri, p)} />
        </>
      )}
    </section>
  );
}
