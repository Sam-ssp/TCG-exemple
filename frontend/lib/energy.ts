// Colours of the French TCG energy types, used for type dots and attack costs.
const ENERGY_COLORS: Record<string, string> = {
  Feu: "#e8644a",
  Eau: "#4a90d9",
  Plante: "#5aa85c",
  Électrique: "#f2c230",
  Psy: "#a066b8",
  Combat: "#c0703e",
  Obscurité: "#3f4a57",
  Métal: "#8e9aa6",
  Fée: "#e58fb8",
  Dragon: "#b09140",
  Incolore: "#d8d4c8",
};

export function energyColor(type: string): string {
  return ENERGY_COLORS[type] ?? "#b8b5ac";
}
