import { expect, it } from "vitest";
import { energyColor } from "./energy";

it("gives each French energy type its colour", () => {
  expect(energyColor("Feu")).toBe("#e8644a");
  expect(energyColor("Eau")).toBe("#4a90d9");
  expect(energyColor("Électrique")).toBe("#f2c230");
});

it("falls back to a neutral colour for unknown types", () => {
  expect(energyColor("Inconnu")).toBe("#b8b5ac");
});
