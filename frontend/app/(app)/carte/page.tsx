"use client";

import { ListPlus, Minus, Plus } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type PointerEvent, Suspense, useState } from "react";
import { CardImage } from "@/components/CardImage";
import { IconButton } from "@/components/IconButton";
import { LinesSkeleton } from "@/components/Skeleton";
import { api, cardPath } from "@/lib/api";
import { energyColor } from "@/lib/energy";
import { explorerUrl, type FilterKey } from "@/lib/explorer";
import { type CardDetail, type CardList, LIST_KIND_LABELS, VARIANT_LABELS } from "@/lib/types";
import { useApi } from "@/lib/useApi";

export default function CardPage() {
  return (
    <Suspense>
      <CardView />
    </Suspense>
  );
}

const filterUrl = (key: FilterKey, value: string) =>
  explorerUrl({ par: key === "illustrateur" || key === "rarete" || key === "pokemon" ? key : "set", filters: { [key]: value }, tri: "", page: 1 });

function Energy({ type }: { type: string }) {
  return <span className="dot" style={{ background: energyColor(type) }} title={type} />;
}

// Tilts the card toward the pointer and moves the holographic highlight with it.
function tilt(event: PointerEvent<HTMLDivElement>) {
  const box = event.currentTarget.getBoundingClientRect();
  const x = (event.clientX - box.left) / box.width;
  const y = (event.clientY - box.top) / box.height;
  const style = event.currentTarget.style;
  style.setProperty("--mx", `${x * 100}%`);
  style.setProperty("--my", `${y * 100}%`);
  style.setProperty("--ry", `${(x - 0.5) * 10}deg`);
  style.setProperty("--rx", `${(0.5 - y) * 10}deg`);
}

function untilt(event: PointerEvent<HTMLDivElement>) {
  event.currentTarget.style.setProperty("--rx", "0deg");
  event.currentTarget.style.setProperty("--ry", "0deg");
}

function CardView() {
  const id = useSearchParams().get("id");
  const card = useApi<CardDetail>(id ? cardPath(id) : null, ["collection", "listes"]);
  const lists = useApi<CardList[]>("/api/listes", ["listes"]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false); // quantities are absolute, so one update at a time

  if (!id) return <p className="error">Aucune carte choisie.</p>;
  if (card.error) return <p className="error">{card.error}</p>;
  if (!card.data) {
    return (
      <section className="showcase" aria-busy="true">
        <div className="skeleton card-shape" />
        <LinesSkeleton />
      </section>
    );
  }
  const data = card.data;

  async function run(action: () => Promise<unknown>) {
    setMessage(null);
    setBusy(true);
    try {
      await action();
      card.reload();
      lists.reload();
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const setQuantity = (variant: string, quantite: number) =>
    run(() => api(`/api/collection/${encodeURIComponent(data.id)}/${variant}`, { method: "PUT", body: { quantite } }));
  const addToList = (listId: string) =>
    run(() => api(`/api/listes/${listId}/cartes/${encodeURIComponent(data.id)}`, { method: "POST" }));
  const available = (lists.data ?? []).filter((list) => !data.listes.some((l) => l.id === list.id));
  const { attacks, abilities, effect, description } = data.details;

  return (
    <section className="showcase">
      <div className="holo" onPointerMove={tilt} onPointerLeave={untilt}>
        <CardImage base={data.image} alt={data.nom} quality="high" />
      </div>

      <div className="detail">
        <div className="detail-head">
          <h1>{data.nom}</h1>
          {data.langue === "en" && (
            <span className="pill indigo" title="Cette carte n'existe pas en français sur TCGdex">
              Édition anglaise
            </span>
          )}
        </div>
        <p className="subtitle">
          <Link href={filterUrl("set", data.set_id)}>{data.set_nom}</Link> n° {data.numero}
          {data.date_sortie && <span className="muted">, {new Date(data.date_sortie).toLocaleDateString("fr-FR", { dateStyle: "long" })}</span>}
        </p>

        <dl className="facts">
          {data.pv !== null && (
            <div>
              <dt>PV</dt>
              <dd className="big">{data.pv}</dd>
            </div>
          )}
          {data.types.length > 0 && (
            <div>
              <dt>Type</dt>
              <dd>
                {data.types.map((type) => (
                  <span key={type} className="type">
                    <Energy type={type} />
                    {type}
                  </span>
                ))}
              </dd>
            </div>
          )}
          <div>
            <dt>Catégorie</dt>
            <dd>{[data.categorie, data.stade].filter(Boolean).join(", ")}</dd>
          </div>
          <div>
            <dt>Rareté</dt>
            <dd>{data.rarete ? <Link href={filterUrl("rarete", data.rarete)}>{data.rarete}</Link> : "—"}</dd>
          </div>
          <div>
            <dt>Illustration</dt>
            <dd>{data.illustrateur ? <Link href={filterUrl("illustrateur", data.illustrateur)}>{data.illustrateur}</Link> : "—"}</dd>
          </div>
          {data.pokemon.length > 0 && (
            <div>
              <dt>Pokédex</dt>
              <dd>
                {data.pokemon.map((p) => (
                  <span key={p.dex_id}>
                    <Link href={filterUrl("pokemon", String(p.dex_id))}>
                      {p.nom} n° {p.dex_id}
                    </Link>{" "}
                  </span>
                ))}
              </dd>
            </div>
          )}
        </dl>

        <div className="block">
          <h2>Ma collection</h2>
          <div className="variants">
            {data.variantes.map((variant) => {
              const quantity = data.quantites[variant] ?? 0;
              const label = VARIANT_LABELS[variant] ?? variant;
              return (
                <div key={variant} className={quantity > 0 ? "variant has" : "variant"}>
                  <span className="label">{label}</span>
                  <span className="stepper">
                    <IconButton label={`Retirer un exemplaire ${label}`} icon={Minus} disabled={busy || quantity === 0} onClick={() => setQuantity(variant, quantity - 1)} />
                    <output aria-live="polite">{quantity}</output>
                    <IconButton label={`Ajouter un exemplaire ${label}`} icon={Plus} disabled={busy} onClick={() => setQuantity(variant, quantity + 1)} />
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="block">
          <h2>Mes listes</h2>
          <div className="list-chips">
            {data.listes.map((list) => (
              <Link key={list.id} className={`list-chip ${list.type}`} href={`/listes/voir/?id=${list.id}`}>
                {list.nom}
              </Link>
            ))}
            {available.length > 0 ? (
              <label className="select-pill add">
                <ListPlus />
                <span className="visually-hidden">Ajouter à une liste</span>
                <select value="" onChange={(e) => e.target.value && addToList(e.target.value)}>
                  <option value="">Ajouter à une liste</option>
                  {available.map((list) => (
                    <option key={list.id} value={list.id}>
                      {list.nom} ({LIST_KIND_LABELS[list.type]})
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              data.listes.length === 0 && (
                <Link className="select-pill add" href="/listes/">
                  <ListPlus />
                  Créer une liste
                </Link>
              )
            )}
          </div>
          {message && <p className="error">{message}</p>}
        </div>

        {(abilities?.length || attacks?.length || effect) && (
          <div className="block">
            <h2>Sur la carte</h2>
            {abilities?.map((ability) => (
              <div key={ability.name} className="attack">
                <div className="attack-head">
                  <span className="pill yellow">Talent</span>
                  <strong>{ability.name}</strong>
                </div>
                <p>{ability.effect}</p>
              </div>
            ))}
            {attacks?.map((attack) => (
              <div key={attack.name} className="attack">
                <div className="attack-head">
                  {attack.cost?.length ? (
                    <span className="cost" role="img" aria-label={`Coût : ${attack.cost.join(", ")}`}>
                      {attack.cost.map((type, i) => (
                        <Energy key={i} type={type} />
                      ))}
                    </span>
                  ) : null}
                  <strong>{attack.name}</strong>
                  {attack.damage !== undefined && <span className="damage">{attack.damage}</span>}
                </div>
                {attack.effect && <p>{attack.effect}</p>}
              </div>
            ))}
            {effect && <p>{effect}</p>}
          </div>
        )}
        {description && <p className="flavor">{description}</p>}
      </div>
    </section>
  );
}
