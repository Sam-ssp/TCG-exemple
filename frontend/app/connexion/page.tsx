"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { api } from "@/lib/api";

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
    <form className="login" onSubmit={submit}>
      <h1>TCG-exemple</h1>
      <input className="input" placeholder="Utilisateur" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
      <input className="input" placeholder="Mot de passe" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="error">{error}</p>}
      <button className="button" type="submit">Se connecter</button>
    </form>
  );
}
