const { test, expect, request: playwrightRequest } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const fixtures = path.join(__dirname, "..", "fixtures");
const apiURL = (process.env.V4_E2E_API_URL || "https://ai-sales-analyst-v3-production.up.railway.app").replace(/\/$/, "");


async function signUpFreshAccount(page, testInfo) {
  const stamp = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const email = `v4-browser-${stamp}@example.com`;
  const response = await page.request.post("/api/v1/auth/signup", {
    data: {
      email,
      password: "BrowserTest123!",
      name: "V4 Browser Owner",
      organization_name: `V4 Browser Organization ${testInfo.testId}`,
    },
  });
  expect(response.status()).toBe(200);
  const me = await page.request.get("/api/v1/auth/me");
  expect(me.status()).toBe(200);
}

async function upload(page, file) {
  await page.goto("/dashboard/overview", { waitUntil: "domcontentloaded" });
  const input = page.locator('input[type="file"]').first();
  await expect(input).toBeAttached();
  await input.setInputFiles(path.join(fixtures, file));
  await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 120_000 });
  await expect(page.locator('[data-v4-readiness="dataset-ready"]')).toBeVisible({ timeout: 120_000 });
  await expect(page.locator("header").getByText(file, { exact: true })).toBeVisible({ timeout: 120_000 });
}


test.beforeEach(async ({ page }, testInfo) => {
  const title = testInfo.title;
  if (
    title.includes("public landing explains the value proposition") ||
    title.includes("deployed tenant isolation rejects cross-organization") ||
    title.includes("organization account can sign up, sign out and sign back in")
  ) {
    return;
  }
  await signUpFreshAccount(page, testInfo);
});

test.describe("V4 public acquisition entrypoint", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("public landing explains the value proposition and routes to signup", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: /Know what changed in your pipeline before the meeting starts/i })).toBeVisible();
    await expect(page.getByText("Avelyntics", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Evidence-first analysis", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Start with a sales team. Expand when the workflow sticks/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Numbers come from your data\. Unsupported answers stop there/i })).toBeVisible();
    await expect(page.getByText("No guessing when the data is silent", { exact: true })).toBeVisible();
    await expect(page.getByText("WHAT CHANGED", { exact: true }).first()).toBeVisible();
    await page.getByRole("link", { name: /^Start your 14-day trial/ }).first().click();
    await expect(page).toHaveURL(/\/login\?mode=signup$/);
    await expect(page.getByRole("tab", { name: "Create account", exact: true })).toHaveAttribute("aria-selected", "true");
  });
});

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
  const input = page.locator("label.upload-mini input[type=file]");
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
  await expect(page.getByText(/Executive report/i).first()).toBeVisible();
  await expect(page.getByText("retail.csv", { exact: true })).toHaveCount(0);
});

test("V4 monitoring creates and evaluates a session-scoped alert", async ({ page }) => {
  await upload(page, "retail.csv");
  await page.getByRole("link", { name: "Monitoring", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Keep watch on what matters/i })).toBeVisible();
  await page.getByLabel("Monitor name", { exact: true }).fill("Return rate watch");
  await page.getByLabel("Monitor metric", { exact: true }).selectOption("return_rate");
  await page.getByLabel("Monitor operator", { exact: true }).selectOption("gt");
  await page.getByLabel("Monitor threshold", { exact: true }).fill("10");
  await page.getByRole("button", { name: "Create monitor", exact: true }).click();
  await expect(page.getByText("Return rate watch", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Evaluate now", exact: true }).click();
  await expect(page.getByText(/Return rate watch is triggered/i)).toBeVisible();
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page.getByText(/Executive report/i).first()).toBeVisible();
});

test("V4 saved intelligence persists across refresh and can reopen an analysis", async ({ page }) => {
  await upload(page, "retail.csv");
  await page.getByRole("link", { name: "Explore", exact: true }).click();
  await page.getByLabel("Saved intelligence name", { exact: true }).fill("Revenue by product");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("button", { name: "Saved", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Saved", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Keep the signals you care about/i })).toBeVisible();
  await expect(page.getByText("Revenue by product", { exact: true })).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Keep the signals you care about/i })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Revenue by product", { exact: true })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: "Open analysis", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\/explore/);
});

test("V4 deployed tenant isolation rejects cross-organization dataset access", async () => {
  const first = await playwrightRequest.newContext({ baseURL: apiURL });
  const second = await playwrightRequest.newContext({ baseURL: apiURL });
  const suffix = Date.now();
  const firstEmail = `v4-tenant-a-${suffix}@example.com`;
  const secondEmail = `v4-tenant-b-${suffix}@example.com`;
  const password = "BrowserTenant123!";

  try {
    const firstSignup = await first.post("/api/v1/auth/signup", {
      data: {
        email: firstEmail,
        password,
        name: "V4 Tenant A",
        organization_name: `V4 Tenant A ${suffix}`,
      },
    });
    expect(firstSignup.status()).toBe(200);

    const uploadResponse = await first.post("/api/v1/onboarding/profile", {
      multipart: {
        file: {
          name: "retail.csv",
          mimeType: "text/csv",
          buffer: fs.readFileSync(path.join(fixtures, "retail.csv")),
        },
      },
    });
    expect(uploadResponse.status()).toBe(200);
    const uploadBody = await uploadResponse.json();
    expect(uploadBody.session_id).toBeTruthy();
    const datasetId = uploadBody.dataset.dataset_id;
    expect(datasetId).toBeTruthy();

    const secondSignup = await second.post("/api/v1/auth/signup", {
      data: {
        email: secondEmail,
        password,
        name: "V4 Tenant B",
        organization_name: `V4 Tenant B ${suffix}`,
      },
    });
    expect(secondSignup.status()).toBe(200);

    const deniedDataset = await second.get(`/api/v1/datasets/${datasetId}`);
    expect(deniedDataset.status()).toBe(404);

    const deniedOverview = await second.get(`/api/v1/datasets/${datasetId}/overview`);
    expect(deniedOverview.status()).toBe(404);
  } finally {
    await first.dispose();
    await second.dispose();
  }
});

test.describe("V4 authentication lifecycle", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("V4 organization account can sign up, sign out and sign back in", async ({ page }) => {
    const stamp = Date.now();
    const email = `v4-auth-${stamp}@example.com`;
    const password = "BrowserTest123!";

    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await page.getByRole("tab", { name: "Create account", exact: true }).click();
    await page.getByLabel("Full name", { exact: true }).fill("V4 Browser User");
    await page.getByLabel("Organization name", { exact: true }).fill("V4 Browser Org");
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(page).toHaveURL("/", { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: /Know what changed in your pipeline/i })).toBeVisible();
    await page.getByRole("link", { name: "Sign in", exact: true }).first().click();
    await expect(page).toHaveURL(/\/login$/);
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/dashboard\/overview/, { timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Sign out", exact: true })).toBeVisible({ timeout: 30_000 });
  });
});

test("V4 browser API requests and auth cookie stay on the frontend origin", async ({ page }) => {
  const appURL = process.env.V4_APP_URL || "http://localhost:3000";
  const appHost = new URL(appURL).host;
  const apiHosts = new Set();

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/")) {
      apiHosts.add(url.host);
    }
  });

  await page.goto("/dashboard/overview", { waitUntil: "domcontentloaded" });
  await expect(page.locator("body")).toBeVisible();
  await expect.poll(() => apiHosts.size, { timeout: 20_000 }).toBeGreaterThan(0);

  expect([...apiHosts]).toEqual([appHost]);

  const cookies = await page.context().cookies();
  const authCookie = cookies.find((cookie) =>
    cookie.name === "__Host-v4_auth_session" || cookie.name === "v4_auth_session"
  );
  expect(authCookie).toBeTruthy();
  expect(authCookie.domain).toBe(new URL(appURL).hostname);
  expect(authCookie.path).toBe("/");
  if (authCookie.name.startsWith("__Host-")) {
    expect(authCookie.secure).toBe(true);
  }
});
