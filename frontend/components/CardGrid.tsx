import Link from "next/link";
import type { ReactNode } from "react";
import type { CardSummary } from "@/lib/types";
import { CardImage } from "./CardImage";

export function CardGrid({ cards, renderAction }: { cards: CardSummary[]; renderAction?: (card: CardSummary) => ReactNode }) {
  if (cards.length === 0) return <p className="empty">Aucune carte ne correspond.</p>;
  return (
    <ul className="binder">
      {cards.map((card) => (
        <li key={card.id}>
          <Link className="pocket" href={`/carte/?id=${encodeURIComponent(card.id)}`}>
            <span className="sleeve">
              <CardImage base={card.image} alt={card.nom} quality="low" />
            </span>
            {card.quantite > 0 && <span className="owned" aria-label={`${card.quantite} possédée(s)`}>x{card.quantite}</span>}
            <span className="name">{card.nom}</span>
            <span className="meta">
              {card.set_nom}, n° {card.numero}
            </span>
          </Link>
          {renderAction && <div className="pocket-action">{renderAction(card)}</div>}
        </li>
      ))}
    </ul>
  );
}
