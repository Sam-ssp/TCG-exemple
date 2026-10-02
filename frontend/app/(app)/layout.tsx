import { Suspense } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Rail } from "@/components/Rail";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app">
      <Rail />
      <main className="main">
        {children}
        <footer className="footer">
          Données des cartes : TCGdex (licence MIT). Pokémon et les noms et images associés sont des marques de Nintendo,
          Creatures, GAME FREAK et The Pokémon Company. Ce site n&apos;est ni affilié, ni approuvé, ni sponsorisé par eux.
        </footer>
      </main>
      <Suspense>
        <ChatPanel />
      </Suspense>
    </div>
  );
}
