import { describe, it, expect } from "vitest";
import { describeError } from "./errorMessage";
import {
  MissingKeyError,
  NoTextError,
  RateLimitError,
  ModelOverloadedError,
  ModelOutputError,
} from "./errors";

describe("describeError().message", () => {
  it("maps MissingKeyError to a Settings hint", () => {
    expect(describeError(new MissingKeyError()).message).toBe(
      "Add your Gemini API key in Settings before scoring.",
    );
  });

  it("maps NoTextError to an image-only-PDF hint", () => {
    expect(describeError(new NoTextError()).message).toBe(
      "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.",
    );
  });

  it("maps RateLimitError to a slow-down hint", () => {
    expect(describeError(new RateLimitError()).message).toBe(
      "Gemini is rate-limiting requests. Wait a moment and try again.",
    );
  });

  it("maps ModelOutputError to an invalid-output hint", () => {
    expect(describeError(new ModelOutputError()).message).toBe(
      "The model returned output we couldn't read. Try again — this is usually transient.",
    );
  });

  it("falls back to a generic Error's message when present", () => {
    expect(describeError(new Error("boom")).message).toBe("boom");
  });

  it("uses a generic fallback for an empty Error message", () => {
    expect(describeError(new Error("")).message).toBe("Something went wrong. Please try again.");
  });

  it("maps ModelOverloadedError to a high-demand message", () => {
    expect(describeError(new ModelOverloadedError()).message).toMatch(/high demand/i);
  });

  it("uses a generic fallback for non-Error values", () => {
    expect(describeError("nope").message).toBe("Something went wrong. Please try again.");
    expect(describeError(undefined).message).toBe("Something went wrong. Please try again.");
  });
});

describe("describeError", () => {
  it("flags overload as retryable, amber-toned, with a 'few minutes' label", () => {
    const info = describeError(new ModelOverloadedError());
    expect(info.tone).toBe("warn");
    expect(info.retryLabel).toBe("Try again in a few minutes");
    expect(info.message).toMatch(/high demand/i);
  });

  it("offers a retry for transient rate-limit and model-output errors", () => {
    expect(describeError(new RateLimitError()).retryLabel).not.toBeNull();
    expect(describeError(new RateLimitError()).tone).toBe("warn");
    expect(describeError(new ModelOutputError()).retryLabel).not.toBeNull();
  });

  it("does not offer a retry for hard failures (no key, no text, generic)", () => {
    expect(describeError(new MissingKeyError()).retryLabel).toBeNull();
    expect(describeError(new MissingKeyError()).tone).toBe("bad");
    expect(describeError(new NoTextError()).retryLabel).toBeNull();
    expect(describeError(new Error("boom")).retryLabel).toBeNull();
  });
});
