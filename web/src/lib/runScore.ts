import { scoreResume, type Settings } from "./pipeline";
import { makeAI, callGeminiJSON, DEFAULT_MODEL } from "./gemini";
import { extractTextFromPdf } from "./pdf";
import { fetchGitHubSummary } from "./github";
import { JSONResumeSchema, EvaluationSchema, CoachSchema } from "./schemas";
import { buildExtractionPrompt, buildScoringPrompt, buildCoachPrompt } from "./prompts";

export async function runScoreWithRealDeps(file: File, settings: Settings, onProgress?: (s: string) => void) {
  const ai = makeAI(settings.geminiKey);
  const model = settings.model || DEFAULT_MODEL;
  return scoreResume(file, {
    settings,
    fileName: file.name,
    onProgress,
    extractText: (pdf) => extractTextFromPdf(pdf),
    runExtraction: async (text) => {
      const p = buildExtractionPrompt(text);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => JSONResumeSchema.parse(v) });
    },
    runScoring: async (text) => {
      const p = buildScoringPrompt(text);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => EvaluationSchema.parse(v) });
    },
    runCoach: async (text, evalJson) => {
      const p = buildCoachPrompt(text, evalJson);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => CoachSchema.parse(v) });
    },
    fetchGitHub: (url) => fetchGitHubSummary(url, { token: settings.githubToken }),
    genId: () => crypto.randomUUID(),
    now: () => Date.now(),
  });
}
