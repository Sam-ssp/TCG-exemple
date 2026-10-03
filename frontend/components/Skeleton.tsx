// Shimmering placeholders shown while data loads, shaped like the content they stand for.
const range = (count: number) => Array.from({ length: count }, (_, i) => i);

function Loading({ className, shape, count }: { className: string; shape: string; count: number }) {
  return (
    <div className={className} role="status">
      <span className="visually-hidden">Chargement…</span>
      {range(count).map((i) => (
        <span key={i} className={`skeleton ${shape}`} aria-hidden="true" />
      ))}
    </div>
  );
}

export const CardsSkeleton = ({ count = 12 }: { count?: number }) => <Loading className="binder" shape="card-shape" count={count} />;

export const TilesSkeleton = ({ count = 12 }: { count?: number }) => <Loading className="shelf" shape="tile-shape" count={count} />;

export const LinesSkeleton = ({ count = 6 }: { count?: number }) => <Loading className="lines-skeleton" shape="line-shape" count={count} />;
