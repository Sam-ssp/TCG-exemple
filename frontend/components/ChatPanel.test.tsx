import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/explorer/",
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(cleanup);

it("does not scroll the page when it opens", () => {
  const scrollIntoView = vi.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  render(<ChatPanel />);
  expect(screen.getByText("Assistant")).toBeTruthy();
  expect(scrollIntoView).not.toHaveBeenCalled();
});
