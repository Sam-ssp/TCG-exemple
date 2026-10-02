import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/explorer/",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("does not scroll the page when it opens", () => {
  const scrollIntoView = vi.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  render(<ChatPanel />);
  expect(screen.getByText("Assistant")).toBeTruthy();
  expect(scrollIntoView).not.toHaveBeenCalled();
});


it("sends a suggestion when it is clicked", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ reponse: "Voici.", actions: [] }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<ChatPanel />);
  fireEvent.click(screen.getByRole("button", { name: "Ajoute 2 Fouinar reverse de Ténèbres Embrasées" }));
  expect(await screen.findByText("Voici.")).toBeTruthy();
  const body = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(body.messages).toEqual([{ role: "user", content: "Ajoute 2 Fouinar reverse de Ténèbres Embrasées" }]);
});
