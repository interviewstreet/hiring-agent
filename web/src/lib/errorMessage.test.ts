import { describe, it, expect } from "vitest";
import { errorMessage } from "./errorMessage";
import {
  MissingKeyError,
  NoTextError,
  RateLimitError,
  ModelOutputError,
} from "./errors";

describe("errorMessage", () => {
  it("maps MissingKeyError to a Settings hint", () => {
    expect(errorMessage(new MissingKeyError())).toBe(
      "Add your Gemini API key in Settings before scoring.",
    );
  });

  it("maps NoTextError to an image-only-PDF hint", () => {
    expect(errorMessage(new NoTextError())).toBe(
      "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.",
    );
  });

  it("maps RateLimitError to a slow-down hint", () => {
    expect(errorMessage(new RateLimitError())).toBe(
      "Gemini is rate-limiting requests. Wait a moment and try again.",
    );
  });

  it("maps ModelOutputError to an invalid-output hint", () => {
    expect(errorMessage(new ModelOutputError("{bad"))).toBe(
      "The model returned output we couldn't read. Try again — this is usually transient.",
    );
  });

  it("falls back to a generic Error's message when present", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom");
  });

  it("uses a generic fallback for an empty Error message", () => {
    expect(errorMessage(new Error(""))).toBe("Something went wrong. Please try again.");
  });

  it("uses a generic fallback for non-Error values", () => {
    expect(errorMessage("nope")).toBe("Something went wrong. Please try again.");
    expect(errorMessage(undefined)).toBe("Something went wrong. Please try again.");
  });
});
