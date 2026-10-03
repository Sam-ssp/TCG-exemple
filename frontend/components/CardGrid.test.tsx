import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { CardSummary } from "@/lib/types";
import { CardGrid } from "./CardGrid";

afterEach(cleanup);

const card = (over: Partial<CardSummary>): CardSummary => ({
  id: "ex7-2", nom: "Dark Blastoise", set_id: "ex7", set_nom: "Team Rocket Returns", numero: "2", rarete: "Rare Holo",
  illustrateur: null, pv: 80, image: null, quantite: 0, langue: "en", ...over,
});

it("labels English-only cards", () => {
  render(<CardGrid cards={[card({}), card({ id: "base1-4", nom: "Dracaufeu", langue: "fr" })]} />);
  expect(screen.getAllByRole("link", { name: /Édition anglaise/ })).toHaveLength(1);
});

it("shows no caption but names each card for screen readers", () => {
  render(<CardGrid cards={[card({ quantite: 2, image: "https://assets.tcgdex.net/en/ex/ex7/2" })]} />);
  expect(screen.getByRole("link").getAttribute("aria-label")).toBe("Dark Blastoise, Team Rocket Returns n° 2, Édition anglaise, 2 possédées");
  expect(screen.queryByText("Dark Blastoise")).toBeNull(); // no text under the card
});
