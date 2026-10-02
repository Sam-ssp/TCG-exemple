import { expect, it, vi } from "vitest";
import { applyActions, REFRESH_EVENT } from "./chat";

it("navigates for naviguer and broadcasts rafraichir", () => {
  const navigate = vi.fn();
  const seen: string[] = [];
  const listener = (event: Event) => seen.push((event as CustomEvent<string>).detail);
  window.addEventListener(REFRESH_EVENT, listener);

  applyActions(
    [
      { type: "rafraichir", cible: "collection" },
      { type: "naviguer", url: "/explorer/?par=pokemon&pokemon=25" },
      { type: "rafraichir", cible: "listes" },
    ],
    navigate,
  );

  window.removeEventListener(REFRESH_EVENT, listener);
  expect(navigate).toHaveBeenCalledWith("/explorer/?par=pokemon&pokemon=25");
  expect(seen).toEqual(["collection", "listes"]);
});
