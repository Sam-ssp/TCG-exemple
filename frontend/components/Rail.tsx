"use client";

import { BookOpen, LayoutGrid, ListChecks, LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const LINKS = [
  { href: "/explorer/", label: "Explorer", Icon: LayoutGrid },
  { href: "/collection/", label: "Ma collection", Icon: BookOpen },
  { href: "/listes/", label: "Mes listes", Icon: ListChecks },
];

export function Rail() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await api("/api/deconnexion", { method: "POST" });
    router.push("/connexion/");
  }

  return (
    <nav className="rail" aria-label="Navigation principale">
      <Link className="mark" href="/explorer/" aria-label="TCG-exemple, accueil">
        TCG
      </Link>
      {LINKS.map(({ href, label, Icon }) => (
        <Link
          key={href}
          href={href}
          className="nav"
          aria-label={label}
          data-tip={label}
          aria-current={pathname.startsWith(href.slice(0, -1)) ? "page" : undefined}
        >
          <Icon />
        </Link>
      ))}
      <span className="spacer" />
      <button className="nav" aria-label="Se déconnecter" data-tip="Se déconnecter" onClick={signOut}>
        <LogOut />
      </button>
    </nav>
  );
}
