import Link from "next/link";
import type { ReactNode } from "react";
import type { CardSummary } from "@/lib/types";
import { CardImage } from "./CardImage";

// Everything a sighted visitor reads from the badges, said once for screen readers.
export function cardLabel(card: CardSummary): string {
  return [
    card.nom,
    `${card.set_nom} n° ${card.numero}`,
    card.langue === "en" && "Édition anglaise",
    card.quantite > 0 && `${card.quantite} possédée${card.quantite > 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(", ");
}

export function CardGrid({ cards, renderAction }: { cards: CardSummary[]; renderAction?: (card: CardSummary) => ReactNode }) {
  if (cards.length === 0) return <p className="empty">Aucune carte ne correspond.</p>;
  return (
    <ul className="binder">
      {cards.map((card) => (
        <li key={card.id} className="pocket-slot">
          <Link className="pocket" href={`/carte/?id=${encodeURIComponent(card.id)}`} aria-label={cardLabel(card)} title={card.nom}>
            <CardImage base={card.image} alt={card.nom} quality="low" />
            {card.langue === "en" && (
              <span className="edition-en" aria-hidden="true">
                EN
              </span>
            )}
            {card.quantite > 0 && (
              <span className="owned" aria-hidden="true">
                ×{card.quantite}
              </span>
            )}
          </Link>
          {renderAction && <div className="pocket-action">{renderAction(card)}</div>}
        </li>
      ))}
    </ul>
  );
}
