// Generates a short, text-based resume PDF for the Playwright smoke test.
// Run once and commit the output:
//   cd web && node test/fixtures/make-sample-pdf.mjs
import PDFDocument from "pdfkit";
import { createWriteStream } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "sample-resume.pdf");

const doc = new PDFDocument({ size: "LETTER", margin: 54 });
doc.pipe(createWriteStream(out));

doc.fontSize(20).text("Test Candidate");
doc.moveDown(0.5);
doc.fontSize(11).text("test@example.com  |  github.com/test-candidate");
doc.moveDown();

doc.fontSize(14).text("Experience");
doc.fontSize(11).text(
  "Software Engineer, Acme Corp (2021-2024). Built and shipped production " +
    "TypeScript services. Led migration to a typed API layer.",
);
doc.moveDown();

doc.fontSize(14).text("Projects");
doc.fontSize(11).text(
  "open-source-tool - a CLI used by 1k+ developers. Maintained tests and CI.",
);
doc.moveDown();

doc.fontSize(14).text("Skills");
doc.fontSize(11).text("TypeScript, React, Node.js, Python, PostgreSQL");

doc.end();
console.log(`[make-sample-pdf] wrote -> ${out}`);
