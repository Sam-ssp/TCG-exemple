export function Pagination({ page, pages, onPage }: { page: number; pages: number; onPage: (page: number) => void }) {
  if (pages <= 1) return null;
  return (
    <div className="pagination">
      <button className="button secondary" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Précédente
      </button>
      <span>
        Page {page} sur {pages}
      </span>
      <button className="button secondary" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Suivante
      </button>
    </div>
  );
}
