const { defineConfig } = require("@playwright/test");

const appURL = process.env.V4_APP_URL || "http://localhost:3000";

module.exports = defineConfig({
  testDir: "./tests",
  testMatch: /v4_saas_acceptance\.spec\.js$/,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  workers: 1,
  use: {
    baseURL: appURL,
    headless: true,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  reporter: [["list"], ["html", { outputFolder: "v4-playwright-report", open: "never" }]],
});
