import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "./IconButton";

export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pages">
      <IconButton label="Page précédente" icon={ChevronLeft} disabled={page <= 1} onClick={() => onPage(page - 1)} />
      <span className="page-count" aria-current="page">
        {page} <span className="muted">/ {pages}</span>
      </span>
      <IconButton label="Page suivante" icon={ChevronRight} disabled={page >= pages} onClick={() => onPage(page + 1)} />
    </nav>
  );
}
