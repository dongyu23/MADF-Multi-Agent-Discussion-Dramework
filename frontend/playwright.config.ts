import { defineConfig } from "@playwright/test";

const baseURL = process.env.MADF_E2E_BASE_URL ?? "http://localhost";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "**/*.e2e.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "../output/playwright-report" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
});
