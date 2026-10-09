/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    // Pack config lives in ../packs (shared with the Python pipeline);
    // by default the dev server only serves files inside web/.
    fs: { allow: [".."] },
  },
  test: {
    // A simulated browser page inside Node, so component tests need no real browser.
    environment: "jsdom",
  },
});
