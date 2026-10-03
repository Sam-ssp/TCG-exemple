"use client";

import { useEffect, useId, useRef } from "react";

type Props = { open: boolean; title: string; confirmLabel: string; onConfirm: () => void; onClose: () => void };

// Modal confirmation on the native <dialog>: Escape and a click on the backdrop cancel.
export function ConfirmDialog({ open, title, confirmLabel, onConfirm, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal?.();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  // The dialog itself has no padding, so a click whose target is the dialog landed on the backdrop.
  return (
    <dialog ref={ref} className="dialog" aria-labelledby={titleId} onClose={onClose} onClick={(e) => e.target === e.currentTarget && onClose()}>
      {open && (
        <div className="dialog-body">
          <h2 id={titleId}>{title}</h2>
          <div className="dialog-actions">
            <button type="button" className="button ghost" onClick={onClose}>
              Annuler
            </button>
            <button type="button" className="button danger" onClick={onConfirm}>
              {confirmLabel}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
