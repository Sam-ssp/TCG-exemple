import type { ChatAction } from "./types";

export const REFRESH_EVENT = "tcg:rafraichir";

export function applyActions(actions: ChatAction[], navigate: (url: string) => void): void {
  for (const action of actions) {
    if (action.type === "naviguer") navigate(action.url);
    else window.dispatchEvent(new CustomEvent(REFRESH_EVENT, { detail: action.cible }));
  }
}
