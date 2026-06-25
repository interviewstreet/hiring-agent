import type { JSONResume } from "./schemas";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const NETWORKS: Record<string, string> = {
  "github.com": "GitHub",
  "linkedin.com": "LinkedIn",
  "leetcode.com": "LeetCode",
  "stackoverflow.com": "Stack Overflow",
  "hackerrank.com": "HackerRank",
  "behance.net": "Behance",
  "dev.to": "DEV Community",
  "twitter.com": "X",
  "x.com": "X",
};

export function extractDomain(url: string): string {
  try {
    let u = url;
    if (u.includes("://")) u = u.split("://")[1];
    let domain = u.split("/")[0];
    if (domain.startsWith("www.")) domain = domain.slice(4);
    return domain;
  } catch {
    return "";
  }
}

export function networkName(domain: string): string {
  return NETWORKS[domain] ?? "";
}

export function extractUsername(url: string, domain: string): string {
  try {
    const path = url.includes(domain) ? url.split(domain)[1] : "";
    if (!path) return "";
    const parts = path.replace(/^\/+/, "").split("/").filter(Boolean).map((p) => p.split("?")[0]);
    if (parts.length === 0) return "";
    if (domain === "linkedin.com") return parts[1] ?? "";
    if (domain === "stackoverflow.com") return parts[2] ?? "";
    return parts[0];
  } catch {
    return "";
  }
}

export function parseDateRange(range: string): [string | null, string | null] {
  if (!range) return [null, null];
  if (range.includes("onwards")) {
    const start = range.replace("onwards", "").trim();
    return start ? [start, "Present"] : [null, "Present"];
  }
  if (range.includes(" ") && MONTHS.some((m) => range.includes(m))) {
    const parts = range.split(" ");
    if (parts.length >= 2) {
      const year = parts[parts.length - 1];
      if (parts[0].includes("-") && parts[0].split("-").length === 2) {
        const [sm, em] = parts[0].split("-");
        return [`${sm} ${year}`, `${em} ${year}`];
      }
      return [`${parts[0]} ${year}`, null];
    }
  }
  if (range.includes("-") && range.split("-").length === 2) {
    const [sy, ey] = range.split("-");
    return [`${sy}-01`, `${ey}-12`];
  }
  return [null, null];
}

export function normalizeResume(resume: JSONResume): JSONResume {
  const out: JSONResume = { ...resume };
  const profiles = out.basics?.profiles;
  if (out.basics && Array.isArray(profiles)) {
    out.basics = {
      ...out.basics,
      profiles: profiles.map((p) => {
        if (p.url && (p.network === null || p.network === undefined)) {
          const domain = extractDomain(p.url);
          const net = networkName(domain);
          if (net) {
            const username = p.username ?? (extractUsername(p.url, domain) || undefined);
            return { ...p, network: net, username };
          }
        }
        return p;
      }),
    };
  }
  return out;
}
