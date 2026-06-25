// @vitest-environment jsdom
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_MODEL } from "./gemini";
import {
  loadSettings,
  persistSettings,
  toPipelineSettings,
  clearAllData,
} from "./settings";
import { clearAllRuns } from "./store";
import type { StoredSettings } from "./schemas";

vi.mock("./store", () => ({ clearAllRuns: vi.fn(async () => {}) }));

// Node.js 22 exposes `localStorage` as `undefined` experimentally, which prevents
// Vitest's jsdom environment from overriding it. Patch it explicitly so tests can
// use a real jsdom-backed localStorage.
beforeAll(() => {
  if (typeof localStorage === "undefined" && typeof window !== "undefined" && window.jsdom) {
    Object.defineProperty(globalThis, "localStorage", {
      value: window.jsdom.window.localStorage,
      writable: true,
      configurable: true,
    });
  }
});

function base(overrides: Partial<StoredSettings> = {}): StoredSettings {
  return {
    geminiKey: "",
    githubToken: "",
    model: DEFAULT_MODEL,
    enableGitHub: false,
    rememberKeys: false,
    ...overrides,
  };
}

beforeEach(() => {
  localStorage.clear();
  // Reset the module-level session object to empty, then clear LS again.
  persistSettings(base());
  localStorage.clear();
  vi.clearAllMocks();
});

describe("settings", () => {
  it("returns defaults when storage is empty", () => {
    expect(loadSettings()).toEqual({
      geminiKey: "",
      githubToken: "",
      model: DEFAULT_MODEL,
      enableGitHub: false,
      rememberKeys: false,
    });
  });

  it("persists keys to localStorage when rememberKeys is true", () => {
    persistSettings(
      base({
        geminiKey: "sk-abc",
        githubToken: "ghp_xyz",
        model: "gemini-2.5-pro",
        enableGitHub: true,
        rememberKeys: true,
      }),
    );
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk-abc");
    expect(localStorage.getItem("ha-github-token")).toBe("ghp_xyz");
    expect(localStorage.getItem("ha-remember-keys")).toBe("true");
    expect(localStorage.getItem("ha-model")).toBe("gemini-2.5-pro");
    expect(localStorage.getItem("ha-enable-github")).toBe("true");
    expect(loadSettings().geminiKey).toBe("sk-abc");
  });

  it("does NOT persist keys when rememberKeys is false but keeps them in session", () => {
    persistSettings(base({ geminiKey: "sk-session", githubToken: "ghp_session", rememberKeys: false }));
    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    // Non-key prefs are still written.
    expect(localStorage.getItem("ha-remember-keys")).toBe("false");
    // loadSettings falls back to the in-memory session keys.
    const loaded = loadSettings();
    expect(loaded.geminiKey).toBe("sk-session");
    expect(loaded.githubToken).toBe("ghp_session");
  });

  it("removes previously persisted keys when toggling rememberKeys off", () => {
    persistSettings(base({ geminiKey: "sk-1", githubToken: "ghp_1", rememberKeys: true }));
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk-1");
    persistSettings(base({ geminiKey: "sk-1", githubToken: "ghp_1", rememberKeys: false }));
    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    expect(loadSettings().geminiKey).toBe("sk-1");
  });

  it("toPipelineSettings maps empty githubToken to null and passes model/enableGitHub", () => {
    const out = toPipelineSettings(
      base({ geminiKey: "k", githubToken: "", model: "m", enableGitHub: true }),
    );
    expect(out).toEqual({ geminiKey: "k", githubToken: null, model: "m", enableGitHub: true });
  });

  it("toPipelineSettings passes through a non-empty githubToken", () => {
    const out = toPipelineSettings(base({ githubToken: "ghp_z" }));
    expect(out.githubToken).toBe("ghp_z");
  });

  it("clearAllData clears ha-* keys except ha-theme and calls clearAllRuns", async () => {
    localStorage.setItem("ha-theme", "dark");
    persistSettings(base({ geminiKey: "sk", githubToken: "tok", rememberKeys: true }));
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk");

    await clearAllData();

    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    expect(localStorage.getItem("ha-remember-keys")).toBeNull();
    expect(localStorage.getItem("ha-theme")).toBe("dark");
    expect(clearAllRuns).toHaveBeenCalledTimes(1);
    // Session keys are reset, so defaults come back.
    expect(loadSettings().geminiKey).toBe("");
  });
});
