import type { Settings } from "./pipeline";
import type { StoredSettings } from "./schemas";
import { DEFAULT_MODEL } from "./gemini";
import { clearAllRuns } from "./store";

const LS_REMEMBER = "ha-remember-keys";
const LS_GEMINI = "ha-gemini-key";
const LS_GITHUB = "ha-github-token";
const LS_MODEL = "ha-model";
const LS_ENABLE_GH = "ha-enable-github";

// In-memory fallback for secrets when the user opts out of persistence.
const session: { geminiKey: string; githubToken: string } = {
  geminiKey: "",
  githubToken: "",
};

function lsGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function lsSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {}
}
function lsRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {}
}

export function loadSettings(): StoredSettings {
  const rememberKeys = lsGet(LS_REMEMBER) === "true";
  const model = lsGet(LS_MODEL) ?? DEFAULT_MODEL;
  const enableGitHub = lsGet(LS_ENABLE_GH) === "true";
  const geminiKey = lsGet(LS_GEMINI) ?? session.geminiKey;
  const githubToken = lsGet(LS_GITHUB) ?? session.githubToken;
  return { geminiKey, githubToken, model, enableGitHub, rememberKeys };
}

export function persistSettings(s: StoredSettings): void {
  lsSet(LS_REMEMBER, s.rememberKeys ? "true" : "false");
  lsSet(LS_MODEL, s.model);
  lsSet(LS_ENABLE_GH, s.enableGitHub ? "true" : "false");

  // Keys always live in the session object; they additionally persist to
  // localStorage only when the user opted in.
  session.geminiKey = s.geminiKey;
  session.githubToken = s.githubToken;

  if (s.rememberKeys) {
    lsSet(LS_GEMINI, s.geminiKey);
    lsSet(LS_GITHUB, s.githubToken);
  } else {
    lsRemove(LS_GEMINI);
    lsRemove(LS_GITHUB);
  }
}

export function toPipelineSettings(s: StoredSettings): Settings {
  return {
    geminiKey: s.geminiKey,
    githubToken: s.githubToken === "" ? null : s.githubToken,
    model: s.model,
    enableGitHub: s.enableGitHub,
  };
}

export async function clearAllData(): Promise<void> {
  try {
    const toRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("ha-") && k !== "ha-theme") toRemove.push(k);
    }
    for (const k of toRemove) localStorage.removeItem(k);
  } catch {}
  session.geminiKey = "";
  session.githubToken = "";
  await clearAllRuns();
}
