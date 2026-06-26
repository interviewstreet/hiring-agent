// Copies the pdfjs-dist web worker into web/public so it ships as a static
// asset at /pdf.worker.min.mjs under both `next dev` and `output: "export"`.
// Runs automatically via the predev/prebuild npm hooks; safe to run by hand.
import { existsSync, mkdirSync, copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const src = resolve(webRoot, "node_modules/pdfjs-dist/build/pdf.worker.min.mjs");
const destDir = resolve(webRoot, "public");
const dest = resolve(destDir, "pdf.worker.min.mjs");

if (!existsSync(src)) {
  console.error(`[copy-pdf-worker] missing source: ${src}\nRun \`npm install\` first.`);
  process.exit(1);
}
mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`[copy-pdf-worker] copied -> ${dest}`);
