const { test, expect } = require("@playwright/test");

const user = {
  id: "user-commercial",
  email: "commercial@example.com",
  name: "Commercial Tester",
  organization_id: "org-commercial",
  organization_name: "Commercial Test Org",
  role: "owner",
  workspace_id: "workspace-commercial",
  workspace_name: "Main Workspace",
  workspaces: [{ id: "workspace-commercial", name: "Main Workspace" }],
};

const entitlements = {
  organization_id: "org-commercial",
  subscription: {
    plan_id: "trial",
    plan_name: "14-day Trial",
    access_active: true,
    access_reason: "trial_active",
    status: "trialing",
    provider: null,
    provider_subscription_id: null,
  },
  entitlements: {
    max_seats: 2,
    max_workspaces: 1,
    features: ["ask", "decisions", "explore", "reports"],
    remaining: {
      dataset_uploads: 2,
      analyst_questions: 48,
      reports: 5,
      monitoring_rules: 3,
      saved_intelligence: 10,
    },
  },
  usage_period_start: "2026-09-18T12:00:00+00:00",
  billing: {
    provider: "disabled",
    checkout_ready: false,
    customer_portal_available: false,
  },
  usage: {
    dataset_uploads: 1,
    analyst_questions: 2,
    reports: 0,
    monitoring_rules: 0,
    saved_intelligence: 0,
  },
  catalog: [
    {
      plan_id: "trial",
      name: "14-day Trial",
      price_usd_monthly: 0,
      trial_days: 14,
      max_seats: 2,
      max_workspaces: 1,
      monthly_limits: {
        dataset_uploads: 3,
        analyst_questions: 50,
        reports: 5,
        monitoring_rules: 3,
        saved_intelligence: 10,
      },
      features: ["ask", "decisions", "explore", "reports"],
    },
    {
      plan_id: "starter",
      name: "Starter",
      price_usd_monthly: 49,
      trial_days: 0,
      max_seats: 5,
      max_workspaces: 3,
      monthly_limits: {
        dataset_uploads: 25,
        analyst_questions: 500,
        reports: 50,
        monitoring_rules: 10,
        saved_intelligence: 100,
      },
      features: ["ask", "decisions", "explore", "reports"],
    },
    {
      plan_id: "growth",
      name: "Growth",
      price_usd_monthly: 149,
      trial_days: 0,
      max_seats: 15,
      max_workspaces: 10,
      monthly_limits: {
        dataset_uploads: 200,
        analyst_questions: 2500,
        reports: 250,
        monitoring_rules: 50,
        saved_intelligence: 500,
      },
      features: ["ask", "decisions", "explore", "reports"],
    },
  ],
};

test("billing page renders read-only commercial state and plan catalog", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user }),
    });
  });
  await page.route("http://127.0.0.1:8000/api/v1/commercial/entitlements", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(entitlements),
    });
  });

  await page.goto("/dashboard/billing");

  await expect(page.getByRole("heading", { name: "Plan & usage" })).toBeVisible();
  await expect(page.getByText("14-day Trial", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("$49/month", { exact: true })).toBeVisible();
  await expect(page.getByText("$149/month", { exact: true })).toBeVisible();
  await expect(page.getByText("Dataset uploads", { exact: true })).toBeVisible();
  await expect(page.getByText("Billing checkout is not connected yet.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Current plan" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Checkout pending provider setup" }).first()).toBeDisabled();
});


test("billing page starts a configured checkout", async ({ page }) => {
  const checkoutCalls = [];
  const configured = {
    ...entitlements,
    billing: {
      provider: "paddle",
      checkout_ready: true,
      customer_portal_available: false,
    },
  };

  await page.route("http://127.0.0.1:8000/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ user }),
    });
  });
  await page.route("http://127.0.0.1:8000/api/v1/commercial/entitlements", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(configured),
    });
  });
  await page.route("http://127.0.0.1:8000/api/v1/commercial/checkout", async (route) => {
    checkoutCalls.push(await route.request().postDataJSON());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider: "paddle",
        provider_session_id: "txn_test_123",
        checkout_url: "/mock-checkout?txn=txn_test_123",
      }),
    });
  });

  await page.route("http://127.0.0.1:3000/mock-checkout?txn=txn_test_123", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<title>Mock Checkout</title><p>Checkout</p>",
    });
  });

  await page.goto("/dashboard/billing");
  await page.getByRole("button", { name: "Upgrade" }).first().click();
  await page.waitForLoadState("domcontentloaded");
  await expect(page).toHaveURL(/\/mock-checkout\?txn=txn_test_123$/);
  expect(checkoutCalls).toEqual([{ plan_id: "starter" }]);
});
