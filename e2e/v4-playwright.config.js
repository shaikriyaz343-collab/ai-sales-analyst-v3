const { defineConfig } = require("@playwright/test");
const path = require("path");

const e2eRoot = __dirname;
const appURL = process.env.V4_APP_URL || "http://localhost:3000";
const storageState = path.join(e2eRoot, ".auth", "v4-user.json");

module.exports = defineConfig({
  testDir: path.join(e2eRoot, "tests"),
  testMatch: /v4_saas_acceptance\.spec\.js$/,
  globalSetup: path.join(e2eRoot, "v4-auth.global.setup.js"),
  timeout: 120_000,
  expect: { timeout: 20_000 },
  workers: 1,
  use: {
    baseURL: appURL,
    storageState,
    headless: true,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  reporter: [
    ["list"],
    ["html", { outputFolder: path.join(e2eRoot, "v4-playwright-report"), open: "never" }],
  ],
});
