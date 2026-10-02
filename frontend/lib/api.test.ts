import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, cardPath, navigation } from "./api";

function respond(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status })));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api", () => {
  it("returns the JSON body", async () => {
    respond(200, { total: 3 });
    await expect(api("/api/cartes")).resolves.toEqual({ total: 3 });
  });

  it("sends JSON bodies", async () => {
    respond(200, {});
    await api("/api/listes", { method: "POST", body: { nom: "Favoris" } });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe('{"nom":"Favoris"}');
  });

  it("throws the French detail on errors", async () => {
    respond(400, { detail: "Une liste « Favoris » existe déjà" });
    await expect(api("/api/listes")).rejects.toThrow(new ApiError("Une liste « Favoris » existe déjà"));
  });

  it("sends the user to the sign-in page on 401", async () => {
    const toLogin = vi.spyOn(navigation, "toLogin").mockImplementation(() => {});
    respond(401, { detail: "Non connecté" });
    await expect(api("/api/cartes")).rejects.toThrow("Non connecté");
    expect(toLogin).toHaveBeenCalled();
  });

  it("does not redirect when the sign-in itself fails", async () => {
    const toLogin = vi.spyOn(navigation, "toLogin").mockImplementation(() => {});
    respond(401, { detail: "Identifiants incorrects" });
    await expect(api("/api/connexion", { method: "POST", body: {} })).rejects.toThrow("Identifiants incorrects");
    expect(toLogin).not.toHaveBeenCalled();
  });
});

describe("cardPath", () => {
  it("encodes ids with question marks", () => {
    expect(cardPath("swsh4-?")).toBe("/api/cartes/swsh4-%3F");
  });
});
