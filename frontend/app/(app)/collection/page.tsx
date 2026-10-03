"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { CardsSkeleton } from "@/components/Skeleton";
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
      <div className="page-head">
        <div className="title-row">
          <h1>Ma collection</h1>
          {data && data.total > 0 && <span className="muted">{data.total === 1 ? "1 carte" : `${data.total} cartes`}</span>}
        </div>
        {data && data.total > 0 && <SortSelect value={tri} onChange={(t) => go(t, 1)} />}
      </div>
      {error && <p className="error">{error}</p>}
      {!data && !error && <CardsSkeleton />}
      {data && data.total === 0 && (
        <p className="empty">
          Classeur vide. <Link href="/explorer/">Parcourir les cartes</Link>
        </p>
      )}
      {data && data.total > 0 && (
        <>
          <CardGrid cards={data.cartes} />
          <Pagination page={data.page} pages={data.pages} onPage={(p) => go(tri, p)} />
        </>
      )}
    </section>
  );
}
