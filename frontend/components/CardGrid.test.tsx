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
  expect(screen.getAllByText("Édition anglaise")).toHaveLength(1);
});
