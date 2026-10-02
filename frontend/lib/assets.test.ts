import { expect, it } from "vitest";
import { logoUrl } from "./assets";

it("builds the webp logo URL from the TCGdex base", () => {
  expect(logoUrl("https://assets.tcgdex.net/fr/swsh/swsh3/logo")).toBe("https://assets.tcgdex.net/fr/swsh/swsh3/logo.webp");
  expect(logoUrl(null)).toBeNull();
});
