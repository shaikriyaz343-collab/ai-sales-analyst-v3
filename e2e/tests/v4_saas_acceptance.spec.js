import { test, expect } from "@playwright/test";
import path from "path";

const fixtures = path.resolve(process.cwd(), "e2e", "fixtures");

async function upload(page, file) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const input = page.locator('input[type="file"]').first();
  await expect(input).toBeAttached();
  await input.setInputFiles(path.join(fixtures, file));
  await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 120_000 });
}

test("V4 onboarding creates a dataset-backed workspace", async ({ page }) => {
  await upload(page, "retail.csv");
  await expect(page.locator("header").getByText("Transactional / Retail Sales", { exact: true })).toBeVisible();
  await expect(page.getByText(/Revenue/i).first()).toBeVisible();
});

test("V4 scope persists across workspaces", async ({ page }) => {
  await upload(page, "retail.csv");
  await page.getByText("Filter", { exact: true }).click();
  const field = page.getByLabel("Scope field", { exact: true });
  const value = page.getByLabel("Scope value", { exact: true });
  await field.selectOption("region");
  await expect(value.locator("option").nth(1)).toBeAttached();
  await value.selectOption({ label: "North" });
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByText("region = North", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Explore", exact: true }).click();
  await expect(page.getByText("region = North", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Insights", exact: true }).click();
  await expect(page.getByText("region = North", { exact: true })).toBeVisible();
});

test("V4 dataset replacement creates a clean analytical session", async ({ page }) => {
  await upload(page, "retail.csv");
  await page.getByText("Replace dataset", { exact: true }).click();
  const input = page.locator('input[type="file"]').last();
  await input.setInputFiles(path.join(fixtures, "pipeline.csv"));
  await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 120_000 });
  await expect(page.locator("header").getByText("Sales Pipeline", { exact: true })).toBeVisible();
  await expect(page.getByText("retail.csv", { exact: true })).toHaveCount(0);
});


test("V4 executive report uses the current session and survives dataset replacement", async ({ page }) => {
  await upload(page, "retail.csv");
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Executive report/i })).toBeVisible();
  await expect(page.getByRole("button", { name: "Print / Save PDF" })).toBeVisible();
  await expect(page.locator("header").getByText("retail.csv", { exact: true })).toBeVisible();

  const replaceInput = page.locator("label.upload-mini input[type=file]");
  await replaceInput.setInputFiles(path.join(fixtures, "pipeline.csv"));
  await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 120_000 });
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page.locator("header").getByText("Sales Pipeline", { exact: true })).toBeVisible();
  await expect(page.getByText(/Executive report — Sales Pipeline/i)).toBeVisible();
  await expect(page.getByText("retail.csv", { exact: true })).toHaveCount(0);
});
