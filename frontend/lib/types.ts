export type CardSummary = {
  id: string;
  nom: string;
  set_id: string;
  set_nom: string;
  numero: string;
  rarete: string | null;
  illustrateur: string | null;
  pv: number | null;
  image: string | null;
  quantite: number;
};

export type CardPage = { cartes: CardSummary[]; total: number; page: number; pages: number };

export type Group = { valeur: string; nom: string; nombre: number; groupe: string | null; image: string | null };

export type ListKind = "collection" | "souhaits";

export type CardList = { id: number; nom: string; type: ListKind; nombre: number };

export type Attack = { name: string; cost?: string[]; damage?: number | string; effect?: string };

export type CardDetail = {
  id: string;
  nom: string;
  set_id: string;
  set_nom: string;
  serie_nom: string;
  date_sortie: string | null;
  numero: string;
  categorie: string;
  rarete: string | null;
  illustrateur: string | null;
  pv: number | null;
  types: string[];
  stade: string | null;
  image: string | null;
  variantes: string[];
  details: { attacks?: Attack[]; abilities?: { name: string; effect: string }[]; effect?: string; description?: string };
  pokemon: { dex_id: number; nom: string }[];
  quantites: Record<string, number>;
  listes: { id: number; nom: string; type: ListKind }[];
};

export type RefreshTarget = "collection" | "listes";

export type ChatAction = { type: "naviguer"; url: string } | { type: "rafraichir"; cible: RefreshTarget };

export type ChatMessage = { role: "user" | "assistant"; content: string };

export const VARIANT_LABELS: Record<string, string> = {
  normal: "Normale",
  reverse: "Reverse",
  holo: "Holo",
  firstEdition: "1re édition",
  wPromo: "Promo W",
};

export const LIST_KIND_LABELS: Record<ListKind, string> = { collection: "Collection", souhaits: "Recherchées" };
