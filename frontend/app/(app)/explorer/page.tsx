"use client";

import { Search, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useRef, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { IconButton } from "@/components/IconButton";
import { Pagination } from "@/components/Pagination";
import { CardsSkeleton, LinesSkeleton, TilesSkeleton } from "@/components/Skeleton";
import { SortSelect } from "@/components/SortSelect";
import { logoUrl } from "@/lib/assets";
import {
  cardsApiUrl,
  explorerUrl,
  type ExplorerState,
  FILTER_LABELS,
  type FilterKey,
  GROUP_TABS,
  hasFilters,
  parseExplorer,
} from "@/lib/explorer";
import { normalize } from "@/lib/text";
import type { CardPage, Group } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Go = (next: ExplorerState) => void;

export default function ExplorerPage() {
  return (
    <Suspense>
      <Explorer />
    </Suspense>
  );
}

function Explorer() {
  const router = useRouter();
  const state = parseExplorer(new URLSearchParams(useSearchParams().toString()));
  const go: Go = (next) => router.push(explorerUrl(next));
  const filtered = hasFilters(state);

  return (
    <section>
      <div className="page-head">
        <h1>Explorer</h1>
        <div className="segmented" role="group" aria-label="Parcourir par">
          {GROUP_TABS.map((tab) => (
            <button
              key={tab.par}
              aria-pressed={tab.par === state.par && !filtered}
              onClick={() => go({ par: tab.par, filters: {}, tri: state.tri, page: 1 })}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <SearchBox key={state.filters.q ?? ""} initial={state.filters.q ?? ""} onSearch={(q) => go({ ...state, filters: { ...state.filters, q }, page: 1 })} />
      {filtered ? <CardResults state={state} go={go} /> : <GroupList key={state.par} state={state} go={go} />}
    </section>
  );
}

function SearchBox({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial);
  const input = useRef<HTMLInputElement>(null);
  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(value.trim());
  }
  return (
    <form className="search" role="search" onSubmit={submit}>
      <Search />
      <label className="visually-hidden" htmlFor="search">Rechercher une carte</label>
      <input ref={input} id="search" type="search" placeholder="Dracaufeu, Pikachu, Énergie…" value={value} onChange={(e) => setValue(e.target.value)} />
      {value && (
        <IconButton
          label="Effacer la recherche"
          icon={X}
          onClick={() => {
            setValue("");
            input.current?.focus();
            if (initial) onSearch("");
          }}
        />
      )}
    </form>
  );
}

function GroupList({ state, go }: { state: ExplorerState; go: Go }) {
  const { data, error } = useApi<Group[]>(`/api/groupes?par=${state.par}`);
  const [filter, setFilter] = useState("");
  if (error) return <p className="error">{error}</p>;
  if (!data) return state.par === "set" ? <TilesSkeleton /> : <LinesSkeleton count={12} />;
  const needle = normalize(filter);
  const groups = data.filter((group) => normalize(group.nom).includes(needle));
  const open = (group: Group) => go({ ...state, filters: { [state.par]: group.valeur }, page: 1 });
  const label = GROUP_TABS.find((tab) => tab.par === state.par)?.label.toLowerCase();

  return (
    <div>
      <label className="filter-field">
        <Search />
        <input placeholder={`Filtrer les ${label}`} aria-label={`Filtrer les ${label}`} value={filter} onChange={(e) => setFilter(e.target.value)} />
      </label>
      {groups.length === 0 && <p className="empty">Rien ne correspond à « {filter} ».</p>}
      {state.par === "set" ? <SetShelf groups={groups} onOpen={open} /> : <Index groups={groups} showDex={state.par === "pokemon"} onOpen={open} />}
    </div>
  );
}

function SetShelf({ groups, onOpen }: { groups: Group[]; onOpen: (group: Group) => void }) {
  const series: { name: string; sets: Group[] }[] = [];
  for (const group of groups) {
    const last = series.at(-1);
    if (last && last.name === group.groupe) last.sets.push(group);
    else series.push({ name: group.groupe ?? "", sets: [group] });
  }
  return (
    <>
      {series.map((serie) => (
        <section key={serie.name} className="series">
          <h2>{serie.name}</h2>
          <ul className="shelf">
            {serie.sets.map((set) => (
              <li key={set.valeur}>
                <button className="set-tile" onClick={() => onOpen(set)} title={set.nom} aria-label={setLabel(set)}>
                  <SetLogo group={set} />
                  {set.langue === "en" && (
                    <span className="edition-en" aria-hidden="true">
                      EN
                    </span>
                  )}
                  <span className="tile-count" aria-hidden="true">
                    {set.nombre}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  );
}

const setLabel = (set: Group) =>
  [set.nom, set.nombre === 1 ? "1 carte" : `${set.nombre} cartes`, set.langue === "en" && "Édition anglaise"].filter(Boolean).join(", ");

function SetLogo({ group }: { group: Group }) {
  const [failed, setFailed] = useState(false);
  const src = logoUrl(group.image);
  if (!src || failed) return <span className="logo-text">{group.nom}</span>;
  // eslint-disable-next-line @next/next/no-img-element -- static export, logos stay on TCGdex's CDN
  return <img src={src} alt="" loading="lazy" onError={() => setFailed(true)} />;
}

function Index({ groups, showDex, onOpen }: { groups: Group[]; showDex: boolean; onOpen: (group: Group) => void }) {
  return (
    <ul className="index">
      {groups.map((group) => (
        <li key={group.valeur}>
          <button onClick={() => onOpen(group)}>
            {showDex && <span className="dex">{group.valeur.padStart(3, "0")}</span>}
            <span className="name">{group.nom}</span>
            <span className="count">{group.nombre}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function CardResults({ state, go }: { state: ExplorerState; go: Go }) {
  const { data, error } = useApi<CardPage>(cardsApiUrl(state), ["collection"]);
  const remove = (key: FilterKey) => {
    const filters = { ...state.filters };
    delete filters[key];
    go({ ...state, filters, page: 1 });
  };
  return (
    <div>
      <div className="toolbar">
        <div className="chips">
          {Object.entries(state.filters).map(([key, value]) => (
            <button key={key} className="chip" onClick={() => remove(key as FilterKey)} aria-label={`Retirer le filtre ${FILTER_LABELS[key as FilterKey]} ${value}`}>
              <span className="chip-key">{FILTER_LABELS[key as FilterKey]}</span>
              {value}
              <X />
            </button>
          ))}
        </div>
        <SortSelect value={state.tri} onChange={(tri) => go({ ...state, tri, page: 1 })} />
      </div>
      {error && <p className="error">{error}</p>}
      {!data && !error && <CardsSkeleton />}
      {data && (
        <>
          <p className="result-count">{data.total === 1 ? "1 carte" : `${data.total} cartes`}</p>
          <CardGrid cards={data.cartes} />
          <Pagination page={data.page} pages={data.pages} onPage={(page) => go({ ...state, page })} />
        </>
      )}
    </div>
  );
}
