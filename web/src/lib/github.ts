import type { GitHubSummary } from "./schemas";

export function extractGitHubUsername(url: string): string | null {
  if (!url) return null;
  const cleaned = url.replace(/\s/g, "").trim();
  const patterns = [/https?:\/\/github\.com\/([^/]+)/, /github\.com\/([^/]+)/, /@([^/]+)/, /^([a-zA-Z0-9-]+)$/];
  for (const re of patterns) {
    const m = cleaned.match(re);
    if (m) return m[1].split("?")[0];
  }
  return null;
}

export function classifyRepo(contributorCount: number): "open_source" | "self_project" {
  return contributorCount > 1 ? "open_source" : "self_project";
}

type FetchFn = (url: string, init?: RequestInit) => Promise<Response>;
type FetchOpts = { token: string | null; fetchImpl?: FetchFn };

async function ghGet(url: string, opts: FetchOpts): Promise<any> {
  const f: FetchFn = opts.fetchImpl ?? fetch;
  const headers: Record<string, string> = { Accept: "application/vnd.github+json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  try {
    const res = await f(url, { headers });
    if (res.status !== 200) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchGitHubSummary(profileUrl: string, opts: FetchOpts): Promise<GitHubSummary | null> {
  const username = extractGitHubUsername(profileUrl);
  if (!username) return null;

  const profile = await ghGet(`https://api.github.com/users/${username}`, opts);
  if (!profile) return null;

  const repos: any[] = (await ghGet(`https://api.github.com/users/${username}/repos?sort=updated&per_page=100&type=all`, opts)) ?? [];
  const projects: GitHubSummary["projects"] = [];
  for (const repo of repos) {
    if (repo.fork && (repo.forks_count ?? 0) < 5) continue;
    const repoName: string | undefined = repo.name;
    if (!repoName) continue;
    const contributors: any[] = (await ghGet(`https://api.github.com/repos/${username}/${repoName}/contributors`, opts)) ?? [];
    projects.push({
      name: repoName,
      project_type: classifyRepo(contributors.length),
      stars: repo.stargazers_count ?? 0,
    });
  }
  projects.sort((a, b) => b.stars - a.stars);

  return {
    profile: { username, public_repos: profile.public_repos, followers: profile.followers },
    projects,
  };
}
