export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pages">
      <button className="button quiet" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Précédente
      </button>
      <span className="muted">
        Page {page} sur {pages}
      </span>
      <button className="button quiet" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Suivante
      </button>
    </nav>
  );
}
