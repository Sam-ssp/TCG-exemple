import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import CardPage from "./page";

vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams("id=base1-4") }));

const CARD = {
  id: "base1-4", nom: "Dracaufeu", set_id: "base1", set_nom: "Set de Base", serie_nom: "Base", date_sortie: "1999-01-09",
  numero: "4", categorie: "Pokémon", rarete: "Rare Holo", illustrateur: "Mitsuhiro Arita", pv: 120, types: ["Feu"],
  stade: null, image: null, variantes: ["holo"], details: {}, pokemon: [], quantites: {}, listes: [],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("sends one update at a time so quick clicks are not lost", async () => {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (init?.method === "PUT") return new Promise<Response>(() => {}); // still in flight
    const body = url.startsWith("/api/listes") ? [] : CARD;
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<CardPage />);
  const plus = await screen.findByRole("button", { name: "Ajouter un exemplaire Holo" });
  fireEvent.click(plus);
  fireEvent.click(plus);
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
  expect((plus as HTMLButtonElement).disabled).toBe(true);
});
