import type { Metadata } from "next";
import { Atkinson_Hyperlegible_Next, Bricolage_Grotesque } from "next/font/google";
import "./globals.css";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });
const ui = Atkinson_Hyperlegible_Next({ subsets: ["latin"], variable: "--font-ui" });

export const metadata: Metadata = { title: "TCG-exemple", description: "Votre collection Pokémon, carte par carte" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${display.variable} ${ui.variable}`}>
      <body>{children}</body>
    </html>
  );
}
