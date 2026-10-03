import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { CardImage } from "./CardImage";

afterEach(cleanup);

it("shows a placeholder when the card has no image", () => {
  render(<CardImage base={null} alt="Énergie Feu" quality="low" />);
  expect(screen.getByRole("img", { name: "Énergie Feu" }).className).toContain("card-placeholder");
});

it("loads the webp image at the requested quality", () => {
  render(<CardImage base="https://assets.tcgdex.net/fr/swsh/swsh3/136" alt="Fouinar" quality="high" />);
  expect(screen.getByRole("img", { name: "Fouinar" }).getAttribute("src")).toBe(
    "https://assets.tcgdex.net/fr/swsh/swsh3/136/high.webp",
  );
});

it("falls back to the placeholder when loading fails", () => {
  render(<CardImage base="https://assets.tcgdex.net/fr/x/y/1" alt="Carte" quality="low" />);
  fireEvent.error(screen.getByRole("img", { name: "Carte" }));
  expect(screen.getByRole("img", { name: "Carte" }).className).toContain("card-placeholder");
});
