import { NoTextError } from "./errors";

export function assembleText(pages: string[]): string {
  const joined = pages.map((p) => p.trim()).filter(Boolean).join("\n\n");
  if (!joined.trim()) throw new NoTextError();
  return joined;
}

// Browser-only. Lazy-imports pdfjs so unit tests (node) never load the worker.
export async function extractTextFromPdf(file: File | ArrayBuffer): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  // This is browser-only, so the worker always loads from the static asset that
  // scripts/copy-pdf-worker.mjs copies to /public (served under both `next dev`
  // and `output: "export"`).
  (pdfjs as any).GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

  const data = file instanceof File ? await file.arrayBuffer() : file;
  const doc = await (pdfjs as any).getDocument({ data }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    pages.push(content.items.map((it: any) => ("str" in it ? it.str : "")).join(" "));
  }
  return assembleText(pages);
}
