
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
    expectedSections: ['Overview', 'What Needs Your Attention', 'Performance', 'Products', 'Customers', 'Regions', 'Discounts', 'Returns', 'Payments', 'Ask Your Business Analyst', 'Executive Report'],
    scopeLabel: 'Product',
    scopeValue: 'Laptop',
  },
  {
    file: 'pipeline.csv',
    typeText: 'Sales Pipeline',
    overviewMetric: '155,000',
    ask: 'What is our pipeline value?',
    answerMustContain: '155',
    expectedSections: ['Overview', 'What Needs Your Attention', 'Performance', 'Pipeline', 'Sales Forecast', 'Ask Your Business Analyst', 'Executive Report'],
    scopeLabel: 'Pipeline stage',
    scopeValue: 'Proposal',
  },
  {
    file: 'subscription.csv',
    typeText: 'Subscription / Recurring Revenue',
    overviewMetric: '800',
    ask: 'What is our MRR?',
    answerMustContain: '800',
    expectedSections: ['Overview', 'What Needs Your Attention', 'Performance', 'Recurring Revenue', 'Retention', 'Churn', 'Ask Your Business Analyst', 'Executive Report'],
    scopeLabel: 'Plan',
    scopeValue: 'Basic',
  },
  {
    file: 'services.csv',
    typeText: 'Services / Professional Services',
    overviewMetric: '4,640',
    ask: 'What are our billings?',
    answerMustContain: '4,640',
    expectedSections: ['Overview', 'What Needs Your Attention', 'Performance', 'Services', 'Billings', 'Utilization', 'Ask Your Business Analyst', 'Executive Report'],
    scopeLabel: 'Client',
    scopeValue: 'A',
  },
];

async function assertNoAppError(page) {
  const body = await page.locator('body').innerText();
  expect(body).not.toMatch(/Traceback|ImportError|ModuleNotFoundError|KeyError:|StreamlitAPIException|No module named/i);
}

async function uploadAndAnalyze(page, file) {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('input[type="file"]').first()).toBeAttached();
  await page.locator('input[type="file"]').first().setInputFiles(path.join(samples, file));
  await page.getByRole('button', { name: /Understand my data|Analyze my business/i }).first().click();
  await expect(page.getByText(/Review your business/i)).toBeVisible();
}

async function chooseReviewSection(page, title) {
  const reviewSelect = page.locator('[data-testid="stSelectbox"]').filter({ hasText: /Review section/i }).getByRole('combobox');
  if (await reviewSelect.count()) {
    await reviewSelect.click();
    await page.getByText(title, { exact: true }).last().click();
  } else {
    const tab = page.getByText(title, { exact: true }).last();
    await tab.click();
  }
}

async function chooseScopeValue(page, label, value) {
  const scope = page.locator('[data-testid="stExpander"]').filter({ hasText: /Explore a subset of the business/i });
  await expect(scope).toBeVisible();
  const box = scope.locator('[data-testid="stSelectbox"]').filter({ hasText: new RegExp(`^${label}$`, 'i') }).getByRole('combobox');
  await expect(box).toBeVisible();
  await box.click();
  await page.getByText(value, { exact: true }).last().click();
}

for (const archetype of archetypes) {
  test(`${archetype.file} — end-to-end business acceptance`, async ({ page }) => {
    await uploadAndAnalyze(page, archetype.file);
    await assertNoAppError(page);

    const body = await page.locator('body').innerText();
    expect(body).toContain(archetype.typeText);

    // Overview must show the expected full-file metric.
    expect(body.replace(/,/g, '')).toContain(archetype.overviewMetric.replace(/,/g, ''));

    // Review section must never display unrelated content.
    for (const section of archetype.expectedSections) {
      await chooseReviewSection(page, section);
      await page.waitForTimeout(300);
      await assertNoAppError(page);
      const visible = await page.locator('body').innerText();

      if (section === 'Ask Your Business Analyst') {
        expect(visible).toContain('Ask Your Business Analyst');
      } else if (section === 'Executive Report') {
        expect(visible).toContain('Executive Report');
      } else {
        expect(visible).toMatch(new RegExp(section.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'));
      }
    }

    // Scope must be a real business-view operation, not cosmetic UI.
    await page.getByText('Overview', { exact: true }).last().click().catch(() => {});
    const expander = page.getByText('Explore a subset of the business', { exact: false }).first();
    await expander.click();
    await chooseScopeValue(page, archetype.scopeLabel, archetype.scopeValue);

    await expect(page.getByText(/matching rows/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Apply view', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Apply view', exact: true }).click();

    await expect(page.getByText(/Dashboard scope:/i)).toBeVisible();
    await assertNoAppError(page);

    const scopedBody = await page.locator('body').innerText();

    // A scoped finding must never falsely describe itself as the "uploaded sample".
    expect(scopedBody).not.toMatch(/100\.0% of revenue in the uploaded sample/i);

    // The app must make the selected scope visible.
    expect(scopedBody).toContain(archetype.scopeValue);

    // Q&A must answer from verified data.
    await chooseReviewSection(page, 'Ask Your Business Analyst');
    const q = page.getByLabel('What would you like to know about your business?');
    await q.fill(archetype.ask);
    await page.getByRole('button', { name: /Get Business Answer/i }).click();

    await expect(page.getByText('Answer', { exact: true })).toBeVisible();
    const answered = await page.locator('body').innerText();
    expect(answered).toContain(archetype.answerMustContain);

    // Editing the question must not leave a stale answer visible as current.
    await q.fill('This is a different question');
    await expect(page.getByText(/New question detected/i)).toBeVisible();

    // Clear must actually clear the state.
    await page.getByRole('button', { name: 'Clear', exact: true }).click();
    await expect(q).toHaveValue('');
    await expect(page.getByText('Answer', { exact: true })).not.toBeVisible();

    await assertNoAppError(page);
  });
}
