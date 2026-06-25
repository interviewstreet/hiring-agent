import { describe, it, expect } from "vitest";
import { assembleText } from "./pdf";
import { NoTextError } from "./errors";

describe("assembleText", () => {
  it("joins page strings with blank lines", () => {
    expect(assembleText(["page one", "page two"])).toBe("page one\n\npage two");
  });
  it("throws NoTextError when all pages are empty", () => {
    expect(() => assembleText(["", "   "])).toThrow(NoTextError);
  });
});
