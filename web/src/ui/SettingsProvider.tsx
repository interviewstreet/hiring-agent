"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { StoredSettings } from "@/lib/schemas";
import { loadSettings, persistSettings } from "@/lib/settings";
import { DEFAULT_MODEL } from "@/lib/gemini";

type SettingsContextValue = {
  settings: StoredSettings;
  update: (patch: Partial<StoredSettings>) => void;
  hasKey: boolean;
};

const DEFAULTS: StoredSettings = {
  geminiKey: "",
  githubToken: "",
  model: DEFAULT_MODEL,
  enableGitHub: false,
  rememberKeys: false,
};

const SettingsContext = createContext<SettingsContextValue>({
  settings: DEFAULTS,
  update: () => {},
  hasKey: false,
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<StoredSettings>(DEFAULTS);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const update = useCallback((patch: Partial<StoredSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      persistSettings(next);
      return next;
    });
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, update, hasKey: settings.geminiKey.length > 0 }}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
