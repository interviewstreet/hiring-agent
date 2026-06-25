import { describe, it, expect } from "vitest";
import { buildExtractionPrompt, buildScoringPrompt, buildCoachPrompt, RESUME_SCHEMA, EVAL_SCHEMA, COACH_SCHEMA } from "./prompts";

describe("prompt builders", () => {
  it("embeds resume text in the extraction prompt", () => {
    const p = buildExtractionPrompt("RESUME TEXT HERE");
    expect(p.user).toContain("RESUME TEXT HERE");
    expect(p.responseSchema).toBe(RESUME_SCHEMA);
  });
  it("embeds resume text and the four categories in the scoring prompt", () => {
    const p = buildScoringPrompt("RESUME BODY");
    expect(p.user).toContain("RESUME BODY");
    expect(p.user).toContain("open_source");
    expect(p.user).toContain("technical_skills");
    expect(p.responseSchema).toBe(EVAL_SCHEMA);
  });
  it("includes the evaluation summary in the coach prompt", () => {
    const p = buildCoachPrompt("RESUME BODY", '{"scores":{"production":{"score":10,"max":25}}}');
    expect(p.user).toContain("production");
    expect(p.responseSchema).toBe(COACH_SCHEMA);
  });
  it("response schemas use Gemini OBJECT types", () => {
    expect(RESUME_SCHEMA.type).toBe("OBJECT");
    expect(EVAL_SCHEMA.type).toBe("OBJECT");
    expect(COACH_SCHEMA.type).toBe("OBJECT");
  });
});
