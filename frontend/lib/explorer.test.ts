import { describe, expect, it } from "vitest";
import { cardsApiUrl, explorerUrl, hasFilters, parseExplorer, type ExplorerState } from "./explorer";

describe("parseExplorer", () => {
  it("defaults to the set tab with no filters", () => {
    expect(parseExplorer(new URLSearchParams(""))).toEqual({ par: "set", filters: {}, tri: "", page: 1 });
  });

  it("reads tab, filters, sort and page", () => {
    const params = new URLSearchParams("par=illustrateur&illustrateur=Ken+Sugimori&tri=pv%3Adesc&page=3");
    expect(parseExplorer(params)).toEqual({
      par: "illustrateur",
      filters: { illustrateur: "Ken Sugimori" },
      tri: "pv:desc",
      page: 3,
    });
  });

  it("ignores an unknown tab and a bad page", () => {
    expect(parseExplorer(new URLSearchParams("par=prix&page=-2"))).toEqual({ par: "set", filters: {}, tri: "", page: 1 });
  });

  it("reads the URL the AI builds", () => {
    const state = parseExplorer(new URLSearchParams("par=pokemon&pokemon=25&type=%C3%89lectrique&tri=rarete%3Adesc%2Cpv%3Adesc"));
    expect(state.filters).toEqual({ pokemon: "25", type: "Électrique" });
    expect(state.tri).toBe("rarete:desc,pv:desc");
  });
});

describe("explorerUrl", () => {
  it("omits defaults and empty values", () => {
    expect(explorerUrl({ par: "set", filters: { q: "" }, tri: "", page: 1 })).toBe("/explorer/");
  });

  it("round-trips through parseExplorer", () => {
    const state: ExplorerState = { par: "rarete", filters: { rarete: "Ultra Rare", q: "pikachu" }, tri: "pv:desc", page: 2 };
    const url = new URL(explorerUrl(state), "http://localhost");
    expect(parseExplorer(url.searchParams)).toEqual(state);
  });
});

describe("cardsApiUrl", () => {
  it("sends filters, sort and page but not the tab", () => {
    expect(cardsApiUrl({ par: "pokemon", filters: { pokemon: "25" }, tri: "pv:desc", page: 2 })).toBe(
      "/api/cartes?pokemon=25&tri=pv%3Adesc&page=2",
    );
  });
});

describe("hasFilters", () => {
  it("is true only when a filter has a value", () => {
    expect(hasFilters({ par: "set", filters: {}, tri: "nom:asc", page: 1 })).toBe(false);
    expect(hasFilters({ par: "set", filters: { q: "pika" }, tri: "", page: 1 })).toBe(true);
  });
});
