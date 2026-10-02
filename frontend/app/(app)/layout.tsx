import { Suspense } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <Header />
      <div className="body">
        <main className="main">{children}</main>
        <Suspense>
          <ChatPanel />
        </Suspense>
      </div>
      <footer className="footer">
        Données des cartes : TCGdex (licence MIT). Pokémon et tous les noms et images associés sont des marques et
        propriétés de Nintendo, Creatures, GAME FREAK et The Pokémon Company. Ce site n&apos;est ni affilié, ni approuvé, ni
        sponsorisé par eux.
      </footer>
    </div>
  );
}
