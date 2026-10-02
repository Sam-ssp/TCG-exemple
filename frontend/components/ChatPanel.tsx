"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { applyActions } from "@/lib/chat";
import type { ChatAction, ChatMessage } from "@/lib/types";

const EXAMPLES = "Exemples : « Montre les cartes de Ken Sugimori par PV décroissants », « Ajoute 2 Fouinar reverse de Ténèbres Embrasées ».";

export function ChatPanel() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [open, setOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const list = useRef<HTMLDivElement>(null);

  // Scroll only the message list; scrollIntoView would also scroll the page.
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [messages, busy]);

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const page = params.size ? `${pathname}?${params.toString()}` : pathname;
      const result = await api<{ reponse: string; actions: ChatAction[] }>("/api/chat", {
        method: "POST",
        body: { messages: next.slice(-20), page },
      });
      setMessages([...next, { role: "assistant", content: result.reponse }]);
      applyActions(result.actions, (url) => router.push(url));
    } catch (err) {
      setMessages([...next, { role: "assistant", content: (err as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <aside className="chat closed">
        <button className="button" onClick={() => setOpen(true)}>Assistant</button>
      </aside>
    );
  }

  return (
    <aside className="chat">
      <div className="chat-header">
        <strong>Assistant</strong>
        <button className="button secondary" onClick={() => setOpen(false)}>Fermer</button>
      </div>
      <div className="chat-messages" ref={list}>
        {messages.length === 0 && <p className="muted">{EXAMPLES}</p>}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
        {busy && <div className="message assistant">...</div>}
      </div>
      <form className="chat-form" onSubmit={send}>
        <input className="input" placeholder="Votre demande" value={input} onChange={(e) => setInput(e.target.value)} />
        <button className="button" type="submit" disabled={busy}>Envoyer</button>
      </form>
    </aside>
  );
}
