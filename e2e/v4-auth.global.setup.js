const { request } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const API_URL = process.env.V4_E2E_API_URL || "http://localhost:8000";
const EMAIL = process.env.V4_E2E_EMAIL || `v4-browser-owner-${Date.now()}@example.com`;
const PASSWORD = process.env.V4_E2E_PASSWORD || "BrowserTest123!";
const AUTH_DIR = path.join(__dirname, ".auth");
const STORAGE_STATE = path.join(AUTH_DIR, "v4-user.json");

async function waitForApi(api) {
  const deadline = Date.now() + 30_000;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const response = await api.get("/api/v1/health");
      if (response.ok()) return;
      lastError = new Error(`health returned ${response.status()}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`V4 API did not become ready: ${lastError?.message || "unknown error"}`);
}

module.exports = async function globalSetup() {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const api = await request.newContext({ baseURL: API_URL });
  try {
    await waitForApi(api);

    let response = await api.post("/api/v1/auth/login", {
      data: { email: EMAIL, password: PASSWORD },
    });

    if (response.status() === 401) {
      response = await api.post("/api/v1/auth/signup", {
        data: {
          email: EMAIL,
          password: PASSWORD,
          name: "V4 Browser Owner",
          organization_name: "V4 Browser Organization",
        },
      });
    }

    if (!response.ok()) {
      throw new Error(`V4 E2E authentication setup failed (${response.status()}): ${await response.text()}`);
    }

    const me = await api.get("/api/v1/auth/me");
    if (!me.ok()) {
      throw new Error(`V4 E2E /auth/me verification failed (${me.status()}): ${await me.text()}`);
    }

    const workspace = await api.get("/api/v1/workspaces");
    if (!workspace.ok()) {
      throw new Error(`V4 E2E workspace verification failed (${workspace.status()}): ${await workspace.text()}`);
    }

    await api.storageState({ path: STORAGE_STATE });
  } finally {
    await api.dispose();
  }
};
