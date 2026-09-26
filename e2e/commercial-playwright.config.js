const { defineConfig } = require("@playwright/test");
const path = require("path");

const e2eRoot = __dirname;

module.exports = defineConfig({
  testDir: path.join(e2eRoot, "tests"),
  testMatch: /v4_commercial_billing\.spec\.js$/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3000",
    cwd: path.join(e2eRoot, "..", "frontend"),
    url: "http://127.0.0.1:3000",
    timeout: 120_000,
    reuseExistingServer: false,
    env: {
      NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000",
    },
  },
  reporter: [["list"], ["html", { outputFolder: path.join(e2eRoot, "commercial-playwright-report"), open: "never" }]],
});
