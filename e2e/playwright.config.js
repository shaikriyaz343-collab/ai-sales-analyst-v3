import { defineConfig } from '@playwright/test';

const appURL = process.env.APP_URL;

if (!appURL) {
  throw new Error('APP_URL environment variable is required');
}

export default defineConfig({
  testDir: './tests',
  timeout: 180_000,
  expect: {
    timeout: 30_000,
  },
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  use: {
    baseURL: appURL,
    headless: true,
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
});
