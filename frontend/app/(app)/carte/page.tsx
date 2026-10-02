"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CardImage } from "@/components/CardImage";
import { api, cardPath } from "@/lib/api";
import { explorerUrl } from "@/lib/explorer";
import { type CardDetail, type CardList, LIST_KIND_LABELS, VARIANT_LABELS } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CardPage() {
  return (
    <Suspense>
      <CardView />
    </Suspense>
  );
}

function CardView() {
  const id = useSearchParams().get("id");
  const card = useApi<CardDetail>(id ? cardPath(id) : null, ["collection", "listes"]);
  const lists = useApi<CardList[]>("/api/listes", ["listes"]);
  const [message, setMessage] = useState<string | null>(null);

  if (!id) return <p className="error">Aucune carte choisie.</p>;
  if (card.error) return <p className="error">{card.error}</p>;
  if (!card.data) return <p className="muted">Chargement...</p>;
  const data = card.data;

  async function run(action: () => Promise<unknown>) {
    setMessage(null);
    try {
      await action();
      card.reload();
      lists.reload();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  const setQuantity = (variant: string, quantite: number) =>
    run(() => api(`/api/collection/${encodeURIComponent(data.id)}/${variant}`, { method: "PUT", body: { quantite } }));
  const addToList = (listId: string) =>
    run(() => api(`/api/listes/${listId}/cartes/${encodeURIComponent(data.id)}`, { method: "POST" }));
  const available = (lists.data ?? []).filter((list) => !data.listes.some((l) => l.id === list.id));

  return (
    <section className="card-detail">
      <CardImage base={data.image} alt={data.nom} quality="high" />
      <div>
        <h1>{data.nom}</h1>
        <div className="panel facts">
          <span>Extension</span>
          <Link href={explorerUrl({ par: "set", filters: { set: data.set_id }, tri: "", page: 1 })}>
            {data.set_nom} ({data.serie_nom})
          </Link>
          <span>Numéro</span>
          <span>{data.numero}</span>
          <span>Date de sortie</span>
          <span>{data.date_sortie ?? "Inconnue"}</span>
          <span>Catégorie</span>
          <span>{[data.categorie, data.stade].filter(Boolean).join(" · ")}</span>
          {data.pv !== null && (
            <>
              <span>PV</span>
              <span>{data.pv}</span>
            </>
          )}
          {data.types.length > 0 && (
            <>
              <span>Types</span>
              <span>{data.types.join(", ")}</span>
            </>
          )}
          <span>Rareté</span>
          <span>{data.rarete ?? "Non renseignée"}</span>
          <span>Illustrateur</span>
          <span>{data.illustrateur ?? "Non renseigné"}</span>
          {data.pokemon.length > 0 && (
            <>
              <span>Pokémon</span>
              <span>
                {data.pokemon.map((p) => (
                  <Link key={p.dex_id} href={explorerUrl({ par: "pokemon", filters: { pokemon: String(p.dex_id) }, tri: "", page: 1 })}>
                    {p.nom} (n° {p.dex_id}){" "}
                  </Link>
                ))}
              </span>
            </>
          )}
        </div>

        <div className="panel">
          <h2>Ma collection</h2>
          {data.variantes.map((variant) => {
            const quantity = data.quantites[variant] ?? 0;
            return (
              <div key={variant} className="variant-row">
                <span className="label">{VARIANT_LABELS[variant] ?? variant}</span>
                <button className="button secondary" disabled={quantity === 0} onClick={() => setQuantity(variant, quantity - 1)}>
                  -
                </button>
                <span>{quantity}</span>
                <button className="button" onClick={() => setQuantity(variant, quantity + 1)}>
                  +
                </button>
              </div>
            );
          })}
        </div>

        <div className="panel">
          <h2>Mes listes</h2>
          {data.listes.length === 0 && <p className="muted">Cette carte n&apos;est dans aucune liste.</p>}
          <ul>
            {data.listes.map((list) => (
              <li key={list.id}>
                <Link href={`/listes/voir/?id=${list.id}`}>{list.nom}</Link> ({LIST_KIND_LABELS[list.type]})
              </li>
            ))}
          </ul>
          {available.length > 0 && (
            <select value="" onChange={(e) => e.target.value && addToList(e.target.value)}>
              <option value="">Ajouter à une liste...</option>
              {available.map((list) => (
                <option key={list.id} value={list.id}>
                  {list.nom} ({LIST_KIND_LABELS[list.type]})
                </option>
              ))}
            </select>
          )}
          {message && <p className="error">{message}</p>}
        </div>

        {(data.details.abilities?.length || data.details.attacks?.length || data.details.effect) && (
          <div className="panel">
            {data.details.abilities?.map((ability) => (
              <p key={ability.name}>
                <strong>Talent : {ability.name}</strong> {ability.effect}
              </p>
            ))}
            {data.details.attacks?.map((attack) => (
              <p key={attack.name}>
                <strong>{attack.name}</strong> {attack.cost?.length ? `(${attack.cost.join(", ")})` : ""} {attack.damage ?? ""}
                {attack.effect && <><br />{attack.effect}</>}
              </p>
            ))}
            {data.details.effect && <p>{data.details.effect}</p>}
          </div>
        )}
        {data.details.description && <p className="muted">{data.details.description}</p>}
      </div>
    </section>
  );
}
