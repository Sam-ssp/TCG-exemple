"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { BinderIcon, ExploreIcon, ListIcon, LogoutIcon } from "./Icons";

const LINKS = [
  { href: "/explorer/", label: "Explorer", Icon: ExploreIcon },
  { href: "/collection/", label: "Collection", Icon: BinderIcon },
  { href: "/listes/", label: "Listes", Icon: ListIcon },
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
      <Link className="mark" href="/explorer/">
        TCG
        <br />
        ex.
      </Link>
      {LINKS.map(({ href, label, Icon }) => (
        <Link key={href} href={href} className="nav" aria-current={pathname.startsWith(href.slice(0, -1)) ? "page" : undefined}>
          <Icon />
          {label}
        </Link>
      ))}
      <span className="spacer" />
      <button className="nav" onClick={signOut}>
        <LogoutIcon />
        Quitter
      </button>
    </nav>
  );
}
