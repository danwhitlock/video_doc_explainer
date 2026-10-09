/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    // A simulated browser page inside Node, so component tests need no real browser.
    environment: "jsdom",
  },
});
