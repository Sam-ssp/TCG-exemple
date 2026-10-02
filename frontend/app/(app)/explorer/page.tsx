"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";
import { CardGrid } from "@/components/CardGrid";
import { Pagination } from "@/components/Pagination";
import { SortSelect } from "@/components/SortSelect";
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

  return (
    <section>
      <div className="tabs">
        {GROUP_TABS.map((tab) => (
          <button
            key={tab.par}
            className={tab.par === state.par && !hasFilters(state) ? "tab active" : "tab"}
            onClick={() => go({ par: tab.par, filters: {}, tri: state.tri, page: 1 })}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <SearchBox key={state.filters.q ?? ""} initial={state.filters.q ?? ""} onSearch={(q) => go({ ...state, filters: { ...state.filters, q }, page: 1 })} />
      {hasFilters(state) ? <CardResults state={state} go={go} /> : <GroupList key={state.par} state={state} go={go} />}
    </section>
  );
}

function SearchBox({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial);
  function submit(event: FormEvent) {
    event.preventDefault();
    onSearch(value.trim());
  }
  return (
    <form className="form-row" onSubmit={submit}>
      <input className="input" placeholder="Rechercher une carte par nom" value={value} onChange={(e) => setValue(e.target.value)} />
      <button className="button" type="submit">Rechercher</button>
    </form>
  );
}

function GroupList({ state, go }: { state: ExplorerState; go: Go }) {
  const { data, error } = useApi<Group[]>(`/api/groupes?par=${state.par}`);
  const [filter, setFilter] = useState("");
  if (error) return <p className="error">{error}</p>;
  if (!data) return <p className="muted">Chargement...</p>;
  const needle = normalize(filter);
  const groups = data.filter((group) => normalize(group.nom).includes(needle));
  return (
    <div>
      <input className="input" placeholder="Filtrer la liste" value={filter} onChange={(e) => setFilter(e.target.value)} />
      <ul className="group-list">
        {groups.map((group, index) => (
          <li key={group.valeur} style={{ display: "contents" }}>
            {group.groupe && group.groupe !== groups[index - 1]?.groupe && <h3 className="group-heading">{group.groupe}</h3>}
            <button className="group-item" onClick={() => go({ ...state, filters: { [state.par]: group.valeur }, page: 1 })}>
              <span>{group.nom}</span>
              <span className="muted">{group.nombre}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
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
            <button key={key} className="chip" onClick={() => remove(key as FilterKey)} title="Retirer ce filtre">
              {FILTER_LABELS[key as FilterKey]} : {value} ×
            </button>
          ))}
        </div>
        <SortSelect value={state.tri} onChange={(tri) => go({ ...state, tri, page: 1 })} />
      </div>
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <p className="muted">{data.total} cartes</p>
          <CardGrid cards={data.cartes} />
          <Pagination page={data.page} pages={data.pages} onPage={(page) => go({ ...state, page })} />
        </>
      )}
    </div>
  );
}
