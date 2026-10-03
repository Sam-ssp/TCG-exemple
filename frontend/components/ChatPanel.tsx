"use client";

import { SendHorizontal, Sparkles, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { applyActions } from "@/lib/chat";
import type { ChatAction, ChatMessage } from "@/lib/types";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { IconButton } from "./IconButton";

const SUGGESTIONS = [
  "Montre les cartes de Ken Sugimori par PV décroissants",
  "Ajoute 2 Fouinar reverse de Ténèbres Embrasées",
];

export function ChatPanel() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const wide = useMediaQuery("(min-width: 1200px)");
  const [choice, setChoice] = useState<boolean | null>(null); // null until the user opens or closes it
  const open = choice ?? wide;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const list = useRef<HTMLDivElement>(null);

  // Scroll only the message list; scrollIntoView would also scroll the page.
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [messages, busy]);

  async function send(text: string) {
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

  function submit(event: FormEvent) {
    event.preventDefault();
    send(input.trim());
  }

  if (!open) {
    return (
      <aside className="chat-tab">
        <IconButton label="Ouvrir l'assistant" icon={Sparkles} tone="solid" className="large" onClick={() => setChoice(true)} />
      </aside>
    );
  }

  return (
    <aside className="chat" aria-label="Assistant">
      <div className="chat-head">
        <span className="chat-mark" aria-hidden="true">
          <Sparkles />
        </span>
        <h2>Assistant</h2>
        <IconButton label="Fermer l'assistant" icon={X} onClick={() => setChoice(false)} />
      </div>
      <div className="chat-messages" ref={list}>
        {messages.length === 0 && (
          <div className="chat-intro">
            {SUGGESTIONS.map((suggestion) => (
              <button key={suggestion} className="suggestion" onClick={() => send(suggestion)}>
                {suggestion}
              </button>
            ))}
          </div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            {message.content}
          </div>
        ))}
        {busy && (
          <div className="message assistant typing" role="status" aria-label="L'assistant répond">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>
      <form className="chat-form" onSubmit={submit}>
        <input placeholder="Demandez une carte, un tri, un ajout…" aria-label="Votre demande" value={input} onChange={(e) => setInput(e.target.value)} />
        <IconButton label="Envoyer" icon={SendHorizontal} tone="solid" type="submit" disabled={busy || !input.trim()} />
      </form>
    </aside>
  );
}
