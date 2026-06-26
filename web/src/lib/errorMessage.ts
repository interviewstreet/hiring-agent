import {
  MissingKeyError,
  NoTextError,
  RateLimitError,
  ModelOutputError,
} from "./errors";

const GENERIC = "Something went wrong. Please try again.";

/** Map any thrown value to user-facing copy for the Score screen. PURE. */
export function errorMessage(err: unknown): string {
  if (err instanceof MissingKeyError) {
    return "Add your Gemini API key in Settings before scoring.";
  }
  if (err instanceof NoTextError) {
    return "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.";
  }
  if (err instanceof RateLimitError) {
    return "Gemini is rate-limiting requests. Wait a moment and try again.";
  }
  if (err instanceof ModelOutputError) {
    return "The model returned output we couldn't read. Try again — this is usually transient.";
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return err.message;
  }
  return GENERIC;
}
