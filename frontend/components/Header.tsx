"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const LINKS = [
  { href: "/explorer/", label: "Explorer" },
  { href: "/collection/", label: "Ma collection" },
  { href: "/listes/", label: "Mes listes" },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    await api("/api/deconnexion", { method: "POST" });
    router.push("/connexion/");
  }

  return (
    <header className="header">
      <Link className="brand" href="/explorer/">TCG-exemple</Link>
      <nav>
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href} className={pathname.startsWith(link.href.slice(0, -1)) ? "active" : ""}>
            {link.label}
          </Link>
        ))}
      </nav>
      <button className="button secondary" onClick={signOut}>Se déconnecter</button>
    </header>
  );
}
