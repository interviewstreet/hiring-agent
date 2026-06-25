import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Delta } from "./Delta";

describe("Delta", () => {
  it("renders a negative value as down with ▼ and abs magnitude", () => {
    const html = renderToStaticMarkup(<Delta value={-3} />);
    expect(html).toContain("delta");
    expect(html).toContain("down");
    expect(html).toContain("▼ -3");
    expect(html).not.toContain("up");
    expect(html).not.toContain("flat");
  });

  it("renders zero as flat with the '— 0' label", () => {
    const html = renderToStaticMarkup(<Delta value={0} />);
    expect(html).toContain("flat");
    expect(html).toContain("— 0");
  });

  it("renders a positive value as up with ▲ and a plus sign", () => {
    const html = renderToStaticMarkup(<Delta value={5} />);
    expect(html).toContain("up");
    expect(html).toContain("▲ +5");
  });

  it("renders null as flat with an em dash and no number", () => {
    const html = renderToStaticMarkup(<Delta value={null} />);
    expect(html).toContain("flat");
    expect(html).toContain("—");
    expect(html).not.toContain("+");
    expect(html).not.toContain("0");
  });

  it("appends the suffix when provided", () => {
    const html = renderToStaticMarkup(<Delta value={5} suffix="vs prev" />);
    expect(html).toContain("▲ +5 vs prev");
  });
});
