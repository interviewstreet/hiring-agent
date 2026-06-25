import { GoogleGenAI } from "@google/genai";
import type { GeminiSchema } from "./prompts";
import { RateLimitError, ModelOutputError } from "./errors";

export const DEFAULT_MODEL = "gemini-2.5-flash";

export function makeAI(apiKey: string) {
  return new GoogleGenAI({ apiKey });
}

type AILike = { models: { generateContent: (args: any) => Promise<{ text?: string }> } };

function isRateLimit(e: unknown): boolean {
  const any = e as { status?: number; message?: string };
  return any?.status === 429 || /resource_exhausted|rate limit|429/i.test(any?.message ?? "");
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
      return validate(parsed);
    } catch (e) {
      lastErr = e;
      if (e instanceof ModelOutputError) throw e;
      if (isRateLimit(e) && attempt < maxRetries - 1) {
        const expo = Math.min(BASE * 2 ** attempt, CAP);
        const jitter = 0.8 + Math.random() * 0.4;
        await sleep(Math.round(expo * jitter));
        continue;
      }
      if (isRateLimit(e)) throw new RateLimitError();
      throw e;
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("Gemini call failed");
}
