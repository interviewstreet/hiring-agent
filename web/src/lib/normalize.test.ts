import { describe, it, expect } from "vitest";
import { extractDomain, networkName, extractUsername, parseDateRange, normalizeResume } from "./normalize";

describe("url helpers", () => {
  it("extracts domain and strips www", () => {
    expect(extractDomain("https://www.github.com/octocat")).toBe("github.com");
  });
  it("maps known domains to network names", () => {
    expect(networkName("github.com")).toBe("GitHub");
    expect(networkName("linkedin.com")).toBe("LinkedIn");
    expect(networkName("unknown.com")).toBe("");
  });
  it("extracts github username from first path part", () => {
    expect(extractUsername("https://github.com/octocat?tab=repositories", "github.com")).toBe("octocat");
  });
  it("extracts linkedin username from second path part", () => {
    expect(extractUsername("https://linkedin.com/in/jane-doe", "linkedin.com")).toBe("jane-doe");
  });
});

describe("parseDateRange", () => {
  it("handles 'Jan-Mar 2021'", () => {
    expect(parseDateRange("Jan-Mar 2021")).toEqual(["Jan 2021", "Mar 2021"]);
  });
  it("handles 'onwards'", () => {
    expect(parseDateRange("Jan 2021 onwards")).toEqual(["Jan 2021", "Present"]);
  });
  it("handles year range '2020-2021'", () => {
    expect(parseDateRange("2020-2021")).toEqual(["2020-01", "2021-12"]);
  });
});

describe("normalizeResume", () => {
  it("derives network and username for a github profile missing them", () => {
    const out = normalizeResume({ basics: { name: "A", profiles: [{ url: "https://github.com/octocat" }] } });
    expect(out.basics?.profiles?.[0].network).toBe("GitHub");
    expect(out.basics?.profiles?.[0].username).toBe("octocat");
  });
});
