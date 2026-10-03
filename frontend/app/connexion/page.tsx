"use client";

import { LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";

// Dracaufeu, Pikachu and Tortank from the 1999 Set de Base.
const FAN = ["base/base1/4", "base/base1/58", "base/base1/2"];

export default function SignInPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/connexion", { method: "POST", body: { utilisateur: username, mot_de_passe: password } });
      router.push("/explorer/");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <main className="signin">
      <div className="signin-art" aria-hidden="true">
        <div className="fan">
          {FAN.map((path) => (
            // eslint-disable-next-line @next/next/no-img-element -- static export, images stay on TCGdex's CDN
            <img key={path} src={`https://assets.tcgdex.net/fr/${path}/high.webp`} alt="" />
          ))}
        </div>
      </div>
      <div className="signin-panel">
        <h1>TCG-exemple</h1>
        <p className="lede">Votre collection Pokémon, carte par carte.</p>
        <form className="signin-form" onSubmit={submit}>
          <label>
            Utilisateur
            <input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </label>
          <label>
            Mot de passe
            <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error && <p className="error">{error}</p>}
          <button className="button large" type="submit">
            Se connecter
            <LogIn />
          </button>
        </form>
      </div>
    </main>
  );
}
