import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { svelteTesting } from "@testing-library/svelte/vite";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte(), tailwindcss(), svelteTesting()],
  resolve: process.env.VITEST ? { conditions: ["browser"] } : undefined,
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["./tests/**/*.test.ts"],
    reporters: ["default", "junit"],
    outputFile: {
      junit: "./test-results/junit.xml",
    },
    coverage: {
      provider: "v8",
      all: true,
      include: [
        "src/lib/api/**/*.ts",
        "src/lib/components/**/*.svelte",
        "src/lib/utils/**/*.ts",
      ],
      reporter: ["text", "html", "json-summary", "lcov"],
      thresholds: {
        perFile: true,
        lines: 70,
        branches: 70,
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://backend:8000",
        changeOrigin: true
      },
    }, 
    watch: {
      usePolling: true
    }
  }
});
