import Link from "next/link";
import type { ReactNode } from "react";
import type { CardSummary } from "@/lib/types";
import { CardImage } from "./CardImage";

export function CardGrid({ cards, renderAction }: { cards: CardSummary[]; renderAction?: (card: CardSummary) => ReactNode }) {
  if (cards.length === 0) return <p className="empty">Aucune carte.</p>;
  return (
    <ul className="card-grid">
      {cards.map((card) => (
        <li key={card.id}>
          <Link className="card-tile" href={`/carte/?id=${encodeURIComponent(card.id)}`}>
            <CardImage base={card.image} alt={card.nom} quality="low" />
            <span className="card-name">{card.nom}</span>
            <span className="card-meta">
              {card.set_nom} · {card.numero}
            </span>
            {card.quantite > 0 && <span className="owned">x{card.quantite}</span>}
          </Link>
          {renderAction?.(card)}
        </li>
      ))}
    </ul>
  );
}
