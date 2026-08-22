import { test, expect } from '@playwright/test';
import path from 'path';

const root = path.resolve(process.cwd(), '..');
const samples = path.join(root, 'samples');

const archetypes = [
  {
    file: 'retail.csv',
    typeText: 'Transactional / Retail Sales',
    overviewMetric: '4,180',
    ask: 'Which product generated most revenue?',
    answerMustContain: 'Phone',
    expectedSections: [
      'Overview',
      'What Needs Your Attention',
      'Performance',
      'Products',
      'Customers',
      'Regions',
      'Discounts',
      'Returns',
      'Payments',
      'Ask Your Business Analyst',
      'Executive Report',
    ],
    scopeLabel: 'Product',
    scopeValue: 'Laptop',
  },
  {
    file: 'pipeline.csv',
    typeText: 'Sales Pipeline',
    overviewMetric: '155,000',
    ask: 'What is our pipeline value?',
    answerMustContain: '155',
    expectedSections: [
      'Overview',
      'What Needs Your Attention',
      'Performance',
      'Pipeline',
      'Sales Forecast',
      'Ask Your Business Analyst',
      'Executive Report',
    ],
    scopeLabel: 'Pipeline stage',
    scopeValue: 'Proposal',
  },
  {
    file: 'subscription.csv',
    typeText: 'Subscription / Recurring Revenue',
    overviewMetric: '800',
    ask: 'What is our MRR?',
    answerMustContain: '800',
    expectedSections: [
      'Overview',
      'What Needs Your Attention',
      'Performance',
      'Recurring Revenue',
      'Retention',
      'Churn',
      'Ask Your Business Analyst',
      'Executive Report',
    ],
    scopeLabel: 'Plan',
    scopeValue: 'Basic',
  },
  {
    file: 'services.csv',
    typeText: 'Services / Professional Services',
    overviewMetric: '4,640',
    ask: 'What are our billings?',
    answerMustContain: '4,640',
    expectedSections: [
      'Overview',
      'What Needs Your Attention',
      'Performance',
      'Services',
      'Billings',
      'Utilization',
      'Ask Your Business Analyst',
      'Executive Report',
    ],
    scopeLabel: 'Client',
    scopeValue: 'A',
  },
];

const APP_IFRAME = 'iframe[title="streamlitApp"]';

async function getApp(page) {
  await page.goto('/', {
    waitUntil: 'domcontentloaded',
  });

  await expect(page.locator(APP_IFRAME)).toBeAttached({
    timeout: 120_000,
  });

  const app = page.frameLocator(APP_IFRAME);

  // Real application readiness: the Streamlit file uploader exists inside
  // the application iframe, not in the outer Streamlit Cloud shell.
  await expect(
    app.locator('input[type="file"]').first()
  ).toBeAttached({
    timeout: 120_000,
  });

  return app;
}

async function assertNoAppError(app) {
  const body = await app.locator('body').innerText();

  expect(body).not.toMatch(
    /Traceback|ImportError|ModuleNotFoundError|KeyError:|StreamlitAPIException|No module named/i
  );
}

async function uploadAndAnalyze(page, file) {
  const app = await getApp(page);

  await app
    .locator('input[type="file"]')
    .first()
    .setInputFiles(path.join(samples, file));

  await app
    .getByRole('button', {
      name: /Understand my data/i,
    })
    .click();

  // The application intentionally uses a two-stage analysis flow:
  // 1) Understand my data -> infer/profile the business
  // 2) Analyze my business -> build the full dashboard/report
  await expect(
    app.getByRole('button', {
      name: /Analyze my business/i,
    })
  ).toBeVisible({
    timeout: 120_000,
  });

  await app
    .getByRole('button', {
      name: /Analyze my business/i,
    })
    .click();

  // Post-analysis contract: the dashboard exposes the Business Brief.
  await expect(
    app.getByText(/Business Brief/i).first()
  ).toBeVisible({
    timeout: 120_000,
  });

  return app;
}

async function chooseReviewSection(app, title) {
  const labeled = app.getByLabel('Review section', {
    exact: true,
  });

  if (await labeled.count()) {
    await labeled.click();

    const option = app.getByRole('option', {
      name: title,
      exact: true,
    });

    if (await option.count()) {
      await option.click();
    } else {
      await app.getByText(title, { exact: true }).last().click();
    }

    return;
  }

  const radio = app.getByRole('radio', {
    name: title,
    exact: true,
  });

  if (await radio.count()) {
    await radio.click();
    return;
  }

  await app.getByText(title, { exact: true }).last().click();
}

async function openScope(app) {
  const expander = app
    .getByText('Explore a subset of the business', {
      exact: false,
    })
    .first();

  await expect(expander).toBeVisible({
    timeout: 30_000,
  });

  await expander.click();
}

async function chooseScopeValue(app, label, value) {
  const box = app.getByLabel(label, {
    exact: true,
  });

  await expect(box).toBeVisible({
    timeout: 30_000,
  });

  await box.click();

  const option = app.getByRole('option', {
    name: value,
    exact: true,
  });

  if (await option.count()) {
    await option.click();
  } else {
    await app.getByText(value, { exact: true }).last().click();
  }
}

async function applyScope(app) {
  await expect(
    app.getByText(/matching rows/i)
  ).toBeVisible({
    timeout: 30_000,
  });

  const apply = app.getByRole('button', {
    name: 'Apply view',
    exact: true,
  });

  await expect(apply).toBeEnabled();
  await apply.click();

  await expect(
    app.getByText(/Dashboard scope:/i)
  ).toBeVisible({
    timeout: 60_000,
  });
}

async function resetScope(app) {
  const reset = app.getByRole('button', {
    name: 'Show full business',
    exact: true,
  });

  await expect(reset).toBeVisible({
    timeout: 30_000,
  });

  await reset.click();

  await expect(
    app.getByText(/Dashboard scope:/i)
  ).not.toBeVisible({
    timeout: 30_000,
  });
}

async function exercisePdf(page, app) {
  await chooseReviewSection(app, 'Executive Report');

  await expect(
    app.getByText('Executive Report', { exact: true }).last()
  ).toBeVisible({
    timeout: 30_000,
  });

  await app
    .getByRole('button', {
      name: 'Create Executive PDF',
      exact: true,
    })
    .click();

  const downloadButton = app.getByRole('button', {
    name: 'Download Executive PDF',
    exact: true,
  });

  await expect(downloadButton).toBeVisible({
    timeout: 90_000,
  });

  await expect(downloadButton).toBeEnabled();

  const downloadPromise = page.waitForEvent('download');
  await downloadButton.click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toMatch(/_business_report\.pdf$/i);
}

for (const archetype of archetypes) {
  test(`${archetype.file} — end-to-end business acceptance`, async ({ page }) => {
    const app = await uploadAndAnalyze(page, archetype.file);

    await assertNoAppError(app);

    const body = await app.locator('body').innerText();

    expect(body).toContain(archetype.typeText);
    expect(body.replace(/,/g, '')).toContain(
      archetype.overviewMetric.replace(/,/g, '')
    );

    // Business-specific review navigation.
    for (const section of archetype.expectedSections) {
      await chooseReviewSection(app, section);
      await page.waitForTimeout(500);
      await assertNoAppError(app);

      const visible = await app.locator('body').innerText();

      if (section === 'Ask Your Business Analyst') {
        expect(visible).toContain('Ask Your Business Analyst');
      } else if (section === 'Executive Report') {
        expect(visible).toContain('Executive Report');
      } else {
        expect(visible).toMatch(
          new RegExp(
            section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
            'i'
          )
        );
      }
    }

    // Business-specific scope operation.
    await chooseReviewSection(app, 'Overview');
    await openScope(app);
    await chooseScopeValue(
      app,
      archetype.scopeLabel,
      archetype.scopeValue
    );
    await applyScope(app);

    await assertNoAppError(app);

    const scopedBody = await app.locator('body').innerText();

    expect(scopedBody).toContain(archetype.scopeValue);
    expect(scopedBody).not.toMatch(
      /100\.0% of revenue in the uploaded sample/i
    );

    // Reset must return the dashboard to the full-file context.
    await resetScope(app);
    await assertNoAppError(app);

    // Q&A from the full uploaded file.
    await chooseReviewSection(app, 'Ask Your Business Analyst');

    const q = app.getByLabel(
      'What would you like to know about your business?',
      { exact: true }
    );

    await expect(q).toBeVisible();
    await q.fill(archetype.ask);

    await app
      .getByRole('button', {
        name: /Get Business Answer/i,
      })
      .click();

    await expect(
      app.getByText('Answer', { exact: true })
    ).toBeVisible({
      timeout: 90_000,
    });

    const answered = await app.locator('body').innerText();
    expect(answered.toLowerCase()).toContain(
      archetype.answerMustContain.toLowerCase()
    );

    // Editing the question must invalidate the previous answer.
    await q.fill('This is a different question');

    await expect(
      app.getByText(/New question detected/i)
    ).toBeVisible();

    // Clear must actually clear the Q&A state.
    await app
      .getByRole('button', {
        name: 'Clear',
        exact: true,
      })
      .click();

    await expect(q).toHaveValue('');
    await expect(
      app.getByText('Answer', { exact: true })
    ).not.toBeVisible();

    await assertNoAppError(app);

    // Executive report must render and generate a PDF.
    await exercisePdf(page, app);
  });
}

// Retail-specific state/scope regression coverage.
test('retail.csv — customer scope and zero-row combined scope', async ({ page }) => {
  const app = await uploadAndAnalyze(page, 'retail.csv');

  await chooseReviewSection(app, 'Overview');
  await openScope(app);

  // Customer-only scope.
  await chooseScopeValue(app, 'Customer', 'A');
  await applyScope(app);

  let scopedBody = await app.locator('body').innerText();
  expect(scopedBody).toContain('customer=A');
  expect(scopedBody).toMatch(/Dashboard scope:/i);

  await resetScope(app);
  await openScope(app);

  // Combined Product + Customer scope intentionally has zero rows:
  // Laptop belongs to D, while A bought Phone/Shirt.
  await chooseScopeValue(app, 'Product', 'Laptop');
  await chooseScopeValue(app, 'Customer', 'A');

  await expect(
    app.getByText(/0 rows/i).first()
  ).toBeVisible({
    timeout: 30_000,
  });

  const warning = app.getByText(
    /This filter combination matches 0 rows/i
  );

  await expect(warning).toBeVisible();

  const apply = app.getByRole('button', {
    name: 'Apply view',
    exact: true,
  });

  await expect(apply).toBeDisabled();
  await assertNoAppError(app);
});
