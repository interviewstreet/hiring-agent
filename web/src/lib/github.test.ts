import { describe, it, expect, vi } from "vitest";
import { extractGitHubUsername, classifyRepo, fetchGitHubSummary } from "./github";

describe("github helpers", () => {
  it("extracts username from a profile URL", () => {
    expect(extractGitHubUsername("https://github.com/octocat?tab=repositories")).toBe("octocat");
  });
  it("classifies repos by contributor count", () => {
    expect(classifyRepo(3)).toBe("open_source");
    expect(classifyRepo(1)).toBe("self_project");
  });
  it("builds a summary, skipping low-fork forks", async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith("/users/octocat")) return new Response(JSON.stringify({ login: "octocat", public_repos: 2, followers: 5 }), { status: 200 });
      if (url.includes("/repos")) return new Response(JSON.stringify([
        { name: "real", fork: false, forks_count: 0, stargazers_count: 10 },
        { name: "skipme", fork: true, forks_count: 1, stargazers_count: 0 },
      ]), { status: 200 });
      if (url.includes("/contributors")) return new Response(JSON.stringify([{ login: "octocat" }, { login: "other" }]), { status: 200 });
      return new Response("[]", { status: 200 });
    });
    const summary = await fetchGitHubSummary("https://github.com/octocat", { token: null, fetchImpl });
    expect(summary?.profile?.username).toBe("octocat");
    expect(summary?.projects.map((p) => p.name)).toEqual(["real"]);
    expect(summary?.projects[0].project_type).toBe("open_source");
  });
});
