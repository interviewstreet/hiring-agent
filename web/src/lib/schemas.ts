import { z } from "zod";

export const CATEGORY_KEYS = ["open_source", "self_projects", "production", "technical_skills"] as const;
export type CategoryKey = (typeof CATEGORY_KEYS)[number];

// ── JSON Resume (subset that gets scored) ──
const ProfileSchema = z.object({
  network: z.string().nullable().optional(),
  username: z.string().nullable().optional(),
  url: z.string(),
});
const BasicsSchema = z.object({
  name: z.string(),
  email: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
  profiles: z.array(ProfileSchema).nullable().optional(),
});
// Only `basics` is consumed (basics.profiles → the GitHub URL). The scorer reads
// raw resume text, not this structure, so the rest of JSON Resume isn't extracted.
export const JSONResumeSchema = z.object({
  basics: BasicsSchema.nullable().optional(),
});
export type JSONResume = z.infer<typeof JSONResumeSchema>;

// ── Evaluation (mirrors models.py EvaluationData) ──
const CategoryScoreSchema = z.object({
  score: z.number().min(0),
  max: z.number().positive(),
  evidence: z.string().min(1),
});
export const EvaluationSchema = z.object({
  scores: z.object({
    open_source: CategoryScoreSchema,
    self_projects: CategoryScoreSchema,
    production: CategoryScoreSchema,
    technical_skills: CategoryScoreSchema,
  }),
  bonus_points: z.object({ total: z.number().min(0).max(20), breakdown: z.string() }),
  deductions: z.object({ total: z.number().min(0), reasons: z.string() }),
  key_strengths: z.array(z.string()).min(1).max(5),
  areas_for_improvement: z.array(z.string()).min(1).max(5),
});
export type Evaluation = z.infer<typeof EvaluationSchema>;

// ── Coach (new) ──
const CategoryEnum = z.enum(CATEGORY_KEYS);
export const CoachSchema = z.object({
  verdict: z.string().min(1),
  fixes: z.array(z.object({
    priority: z.number().int().positive(),
    category: CategoryEnum,
    title: z.string().min(1),
    detail: z.string().min(1),
    estGain: z.number().min(0),
  })).max(5),
  boosts: z.array(z.object({
    category: CategoryEnum,
    text: z.string().min(1),
    estGain: z.number().min(0),
  })).max(5),
});
export type Coach = z.infer<typeof CoachSchema>;

// ── GitHub summary (subset persisted for display) ──
export type GitHubSummary = {
  profile: { username: string } | null;
  projects: Array<{ name: string; project_type: string; stars: number }>;
};

// ── Stored run ──
export type RunRecord = {
  id: string;
  createdAt: number;
  fileName: string;
  label?: string;
  parsedResume: JSONResume;
  evaluation: Evaluation;
  coach: Coach;
  githubSummary?: GitHubSummary | null;
};

// ── Persisted settings (UI-facing superset of pipeline Settings) ──
export type StoredSettings = {
  geminiKey: string;
  githubToken: string;
  model: string;
  enableGitHub: boolean;
  rememberKeys: boolean;
};
