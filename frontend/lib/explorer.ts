import { toQuery } from "./query";

export type GroupBy = "set" | "pokemon" | "illustrateur" | "rarete";

export const GROUP_TABS: { par: GroupBy; label: string }[] = [
  { par: "set", label: "Extensions" },
  { par: "pokemon", label: "Pokémon" },
  { par: "illustrateur", label: "Illustrateurs" },
  { par: "rarete", label: "Raretés" },
];

export const FILTER_KEYS = ["set", "pokemon", "illustrateur", "rarete", "type", "q"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];

export const FILTER_LABELS: Record<FilterKey, string> = {
  set: "Extension",
  pokemon: "Pokédex n°",
  illustrateur: "Illustrateur",
  rarete: "Rareté",
  type: "Type",
  q: "Nom",
};

export const SORT_OPTIONS = [
  { value: "", label: "Date de sortie, puis numéro" },
  { value: "nom:asc", label: "Nom (A-Z)" },
  { value: "pokedex:asc", label: "Numéro de Pokédex" },
  { value: "pv:desc", label: "PV décroissants" },
  { value: "rarete:desc", label: "Rareté décroissante" },
  { value: "illustrateur:asc", label: "Illustrateur (A-Z)" },
  { value: "date_sortie:desc", label: "Plus récentes" },
  { value: "numero:asc", label: "Numéro dans l'extension" },
];

export type ExplorerState = { par: GroupBy; filters: Partial<Record<FilterKey, string>>; tri: string; page: number };

export function parseExplorer(params: URLSearchParams): ExplorerState {
  const tab = GROUP_TABS.find((t) => t.par === params.get("par"));
  const filters: ExplorerState["filters"] = {};
  for (const key of FILTER_KEYS) {
    const value = params.get(key);
    if (value) filters[key] = value;
  }
  const page = Number(params.get("page"));
  return { par: tab ? tab.par : "set", filters, tri: params.get("tri") ?? "", page: Number.isInteger(page) && page > 0 ? page : 1 };
}

export function explorerUrl(state: ExplorerState): string {
  return (
    "/explorer/" +
    toQuery({
      par: state.par === "set" ? undefined : state.par,
      ...state.filters,
      tri: state.tri,
      page: state.page > 1 ? state.page : undefined,
    })
  );
}

export function cardsApiUrl(state: ExplorerState): string {
  return "/api/cartes" + toQuery({ ...state.filters, tri: state.tri, page: state.page > 1 ? state.page : undefined });
}

export function hasFilters(state: ExplorerState): boolean {
  return Object.values(state.filters).some(Boolean);
}
