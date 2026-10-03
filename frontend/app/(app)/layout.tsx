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
          Données TCGdex (MIT). Pokémon © Nintendo, Creatures, GAME FREAK, The Pokémon Company. Site non affilié.
        </footer>
      </main>
      <Suspense>
        <ChatPanel />
      </Suspense>
    </div>
  );
}
