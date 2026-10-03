import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";

afterEach(cleanup);

const renderDialog = () => {
  const onConfirm = vi.fn();
  const onClose = vi.fn();
  render(<ConfirmDialog open title="Supprimer « Recherchées » ?" confirmLabel="Supprimer" onConfirm={onConfirm} onClose={onClose} />);
  return { onConfirm, onClose };
};

it("is named by its title and confirms with its button", () => {
  const { onConfirm, onClose } = renderDialog();
  const dialog = screen.getByRole("dialog", { hidden: true });
  expect(document.getElementById(dialog.getAttribute("aria-labelledby")!)?.textContent).toBe("Supprimer « Recherchées » ?");
  fireEvent.click(screen.getByRole("button", { hidden: true, name: "Supprimer" }));
  expect(onConfirm).toHaveBeenCalledOnce();
  fireEvent.click(dialog.querySelector(".dialog-body")!); // inside the panel, not the backdrop
  expect(onClose).not.toHaveBeenCalled();
});

it("cancels on a backdrop click", () => {
  const { onClose } = renderDialog();
  fireEvent.click(screen.getByRole("dialog", { hidden: true }));
  expect(onClose).toHaveBeenCalledOnce();
});
