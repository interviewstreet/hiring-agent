import { describe, it, expect, vi } from "vitest";
import { z } from "zod";
import { callGeminiJSON } from "./gemini";
import { RateLimitError, ModelOverloadedError, ModelOutputError } from "./errors";

const schema = z.object({ ok: z.boolean() });

function fakeAI(responses: Array<() => Promise<{ text: string }>>) {
  let i = 0;
  return { models: { generateContent: vi.fn(async () => responses[i++]()) } };
}

describe("callGeminiJSON", () => {
  it("parses and validates a good JSON response", async () => {
    const ai = fakeAI([async () => ({ text: '{"ok":true}' })]);
    const out = await callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} });
    expect(out.ok).toBe(true);
  });

  it("retries on a 429 then succeeds", async () => {
    const rl = Object.assign(new Error("429 RESOURCE_EXHAUSTED"), { status: 429 });
    const ai = fakeAI([async () => { throw rl; }, async () => ({ text: '{"ok":true}' })]);
    const sleep = vi.fn(async () => {});
    const out = await callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep, maxRetries: 3 });
    expect(out.ok).toBe(true);
    expect(sleep).toHaveBeenCalledTimes(1);
  });

  it("throws RateLimitError after exhausting retries", async () => {
    const rl = Object.assign(new Error("429"), { status: 429 });
    const ai = fakeAI([async () => { throw rl; }, async () => { throw rl; }]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {}, maxRetries: 2 })).rejects.toBeInstanceOf(RateLimitError);
  });

  it("retries on a 503 overload then succeeds", async () => {
    const ov = Object.assign(new Error("503 The model is overloaded. Please try again later."), { status: 503 });
    const ai = fakeAI([async () => { throw ov; }, async () => ({ text: '{"ok":true}' })]);
    const sleep = vi.fn(async () => {});
    const out = await callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep, maxRetries: 3 });
    expect(out.ok).toBe(true);
    expect(sleep).toHaveBeenCalledTimes(1);
  });

  it("throws ModelOverloadedError after exhausting retries on overload", async () => {
    const ov = Object.assign(new Error("The model is overloaded"), { status: 503 });
    const ai = fakeAI([async () => { throw ov; }, async () => { throw ov; }]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {}, maxRetries: 2 })).rejects.toBeInstanceOf(ModelOverloadedError);
  });

  it("detects overload by message when status is absent", async () => {
    const ov = new Error("UNAVAILABLE: the model is in high demand right now");
    const ai = fakeAI([async () => { throw ov; }, async () => { throw ov; }]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {}, maxRetries: 2 })).rejects.toBeInstanceOf(ModelOverloadedError);
  });

  it("throws ModelOutputError on non-JSON", async () => {
    const ai = fakeAI([async () => ({ text: "not json" })]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} })).rejects.toBeInstanceOf(ModelOutputError);
  });

  it("throws ModelOutputError on schema-invalid JSON", async () => {
    const ai = fakeAI([async () => ({ text: '{"ok":"not-a-boolean"}' })]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} })).rejects.toBeInstanceOf(ModelOutputError);
  });
  it("rethrows a non-rate-limit error as-is", async () => {
    const boom = new Error("network down");
    const ai = fakeAI([async () => { throw boom; }]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} })).rejects.toBe(boom);
  });
});
