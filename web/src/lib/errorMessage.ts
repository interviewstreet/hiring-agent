import {
  MissingKeyError,
  NoTextError,
  RateLimitError,
  ModelOverloadedError,
  ModelOutputError,
} from "./errors";

const GENERIC = "Something went wrong. Please try again.";

/** "warn" = transient/recoverable (amber); "bad" = hard failure (red). */
export type ErrorTone = "warn" | "bad";

export type ErrorInfo = {
  message: string;
  /** Label for a retry button, or null when retrying the same input can't help. */
  retryLabel: string | null;
  tone: ErrorTone;
};

/** Map any thrown value to user-facing copy + retry affordance. PURE. */
export function describeError(err: unknown): ErrorInfo {
  if (err instanceof MissingKeyError) {
    return {
      message: "Add your Gemini API key in Settings before scoring.",
      retryLabel: null,
      tone: "bad",
    };
  }
  if (err instanceof NoTextError) {
    return {
      message:
        "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.",
      retryLabel: null,
      tone: "bad",
    };
  }
  if (err instanceof ModelOverloadedError) {
    return {
      message:
        "The model is in high demand right now. This is on Google's side, not yours — give it a few minutes and try again.",
      retryLabel: "Try again in a few minutes",
      tone: "warn",
    };
  }
  if (err instanceof RateLimitError) {
    return {
      message: "Gemini is rate-limiting requests. Wait a moment and try again.",
      retryLabel: "Try again in a moment",
      tone: "warn",
    };
  }
  if (err instanceof ModelOutputError) {
    return {
      message: "The model returned output we couldn't read. Try again — this is usually transient.",
      retryLabel: "Try again",
      tone: "warn",
    };
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return { message: err.message, retryLabel: null, tone: "bad" };
  }
  return { message: GENERIC, retryLabel: null, tone: "bad" };
}

/** Convenience: the user-facing message only. PURE. */
export function errorMessage(err: unknown): string {
  return describeError(err).message;
}
