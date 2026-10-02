import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "TCG-exemple", description: "Collection de cartes Pokémon" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
