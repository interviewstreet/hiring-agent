import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.{ts,tsx}"],
    passWithNoTests: true,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
});
