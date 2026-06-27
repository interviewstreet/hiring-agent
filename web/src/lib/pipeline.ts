import type { JSONResume, Evaluation, Coach, RunRecord, GitHubSummary } from "./schemas";
import { normalizeResume } from "./normalize";
import { MissingKeyError } from "./errors";

export type Settings = { geminiKey: string; githubToken: string | null; model: string; enableGitHub: boolean };

export type PipelineDeps = {
  settings: Settings;
  fileName?: string;
  extractText: (pdf: File | ArrayBuffer) => Promise<string>;
  runExtraction: (resumeText: string) => Promise<JSONResume>;
  runScoring: (resumeText: string) => Promise<Evaluation>;
  runCoach: (resumeText: string, evaluationJson: string) => Promise<Coach>;
  fetchGitHub: (profileUrl: string) => Promise<GitHubSummary | null>;
  genId: () => string;
  now: () => number;
  onProgress?: (stage: string) => void;
};

function findGitHubProfileUrl(resume: JSONResume): string | null {
  const profiles = resume.basics?.profiles ?? [];
  const p = profiles.find((x) => (x.network ?? "").toLowerCase() === "github");
  return p?.url ?? null;
}

export async function scoreResume(pdf: File | ArrayBuffer, deps: PipelineDeps): Promise<RunRecord> {
  if (!deps.settings.geminiKey) throw new MissingKeyError();

  deps.onProgress?.("Reading PDF");
  const resumeText = await deps.extractText(pdf);

  // Resume extraction exists only to find the GitHub profile URL, so it runs
  // only when GitHub enrichment is on. With it off (the default) we skip a whole
  // LLM call — the scorer and coach read the raw resume text, not parsedResume.
  let parsedResume: JSONResume = {};
  let githubSummary: GitHubSummary | null = null;
  if (deps.settings.enableGitHub) {
    deps.onProgress?.("Extracting resume");
    parsedResume = normalizeResume(await deps.runExtraction(resumeText));
    const url = findGitHubProfileUrl(parsedResume);
    if (url) {
      deps.onProgress?.("Enriching from GitHub");
      try {
        githubSummary = await deps.fetchGitHub(url);
      } catch {
        githubSummary = null; // degrade gracefully
      }
    }
  }

  // Append a compact GitHub context block to the text the scorer sees (mirrors score.py).
  let scoringText = resumeText;
  if (githubSummary) {
    const gh = `\n\n=== GITHUB DATA ===\nUsername: ${githubSummary.profile?.username ?? "N/A"}\n` +
      githubSummary.projects.slice(0, 10).map((p) => `- ${p.name} [${p.project_type}] ★${p.stars}`).join("\n");
    scoringText += gh;
  }

  deps.onProgress?.("Scoring");
  const evaluation = await deps.runScoring(scoringText);

  deps.onProgress?.("Coaching");
  // The coach sees the same (possibly GitHub-enriched) text as the scorer so its
  // advice stays consistent with what was actually scored.
  const coach = await deps.runCoach(scoringText, JSON.stringify(evaluation));

  return {
    id: deps.genId(),
    createdAt: deps.now(),
    fileName: deps.fileName ?? "resume.pdf",
    parsedResume,
    evaluation,
    coach,
    githubSummary,
  };
}
