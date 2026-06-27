import { GoogleGenAI } from "@google/genai";
import type { GeminiSchema } from "./prompts";
import { RateLimitError, ModelOverloadedError, ModelOutputError } from "./errors";

export const DEFAULT_MODEL = "gemini-2.5-flash";

// Models offered in the Settings dropdown. Single source of truth — the
// <select> options, the default, and any validation all read from here.
// `label` is what the user sees; `id` is the model string sent to Gemini.
export const GEMINI_MODELS: ReadonlyArray<{ id: string; label: string }> = [
  { id: "gemini-2.5-pro", label: "gemini-2.5-pro — most accurate" },
  { id: "gemini-2.5-flash", label: "gemini-2.5-flash — balanced (default)" },
  { id: "gemini-2.5-flash-lite", label: "gemini-2.5-flash-lite — fastest & cheapest" },
  { id: "gemini-2.0-flash", label: "gemini-2.0-flash — legacy fallback" },
];

export function makeAI(apiKey: string) {
  return new GoogleGenAI({ apiKey });
}

type AILike = { models: { generateContent: (args: any) => Promise<{ text?: string }> } };

function isRateLimit(e: unknown): boolean {
  const any = e as { status?: number; message?: string };
  return any?.status === 429 || /resource_exhausted|rate limit|429/i.test(any?.message ?? "");
}

// Gemini returns 503 UNAVAILABLE ("The model is overloaded") when the model is
// in high demand. Transient like a rate limit, but it's Google's capacity, not
// the user's quota — so it gets its own error type and "wait a few minutes" copy.
function isOverloaded(e: unknown): boolean {
  const any = e as { status?: number; message?: string };
  return any?.status === 503 || /unavailable|overloaded|high demand/i.test(any?.message ?? "");
}

export async function callGeminiJSON<T>(opts: {
  ai: AILike;
  model: string;
  system: string;
  user: string;
  responseSchema: GeminiSchema;
  validate: (value: unknown) => T;
  temperature?: number;
  topP?: number;
  maxRetries?: number;
  sleep?: (ms: number) => Promise<void>;
}): Promise<T> {
  const { ai, model, system, user, responseSchema, validate } = opts;
  const maxRetries = opts.maxRetries ?? 5;
  const sleep = opts.sleep ?? ((ms: number) => new Promise((r) => setTimeout(r, ms)));
  // Browser-tuned backoff. The Python GeminiProvider uses 10s base / 120s cap;
  // we deliberately shorten to 1s base / 30s cap because the user is watching a
  // live UI and won't tolerate minute-long waits. (We also skip Python's
  // server-provided retry_in hint parsing for the same reason.)
  const BASE = 1000, CAP = 30000;

  let lastErr: unknown;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await ai.models.generateContent({
        model,
        contents: user,
        config: {
          systemInstruction: system,
          responseMimeType: "application/json",
          responseSchema,
          temperature: opts.temperature ?? 0.1,
          topP: opts.topP ?? 0.9,
        },
      });
      const text = (res.text ?? "").trim();
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new ModelOutputError(text);
      }
      try {
        return validate(parsed);
      } catch {
        throw new ModelOutputError(text, "Model output failed schema validation.");
      }
    } catch (e) {
      lastErr = e;
      if (e instanceof ModelOutputError) throw e;
      // Both rate limits and overload are transient — back off and retry.
      const transient = isRateLimit(e) || isOverloaded(e);
      if (transient && attempt < maxRetries - 1) {
        const expo = Math.min(BASE * 2 ** attempt, CAP);
        const jitter = 0.8 + Math.random() * 0.4;
        await sleep(Math.round(expo * jitter));
        continue;
      }
      if (isOverloaded(e)) throw new ModelOverloadedError();
      if (isRateLimit(e)) throw new RateLimitError();
      throw e;
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("Gemini call failed");
}
