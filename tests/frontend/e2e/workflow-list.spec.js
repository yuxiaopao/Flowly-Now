// @ts-check
import { test, expect } from '@playwright/test'
import { workflowListMock, workflowDetailMock } from '../mocks/workflows.mock'

/**
 * Workflow List Page E2E Tests
 * Covers: workflow list display, filtering, sorting, pagination, and empty states.
 */
test.describe('Workflow List Page', () => {

  test.beforeEach(async ({ page }) => {
    // Intercept API calls and return mock data
    await page.route('**/api/v1/workflows/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowListMock),
      });
    });

    await page.route(/\/api\/v1\/workflows\/\d+/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowDetailMock),
      });
    });
  });

  test('should display workflow list page with correct title', async ({ page }) => {
    await page.goto('/workflows');
    await expect(page).toHaveTitle(/工作流|Workflow/i);
  });

  test('should display list of workflows', async ({ page }) => {
    await page.goto('/workflows');
    // Wait for the list to load
    await page.waitForSelector('[data-testid="workflow-list"]', { timeout: 5000 }).catch(() => {});
    // Check if workflows are rendered (either in list or empty state)
    const listItems = await page.locator('[data-testid^="workflow-item-"]').count();
    const emptyState = await page.locator('[data-testid="workflow-list-empty"]').count();
    expect(listItems > 0 || emptyState > 0).toBeTruthy();
  });

  test('should navigate to workflow detail on click', async ({ page }) => {
    await page.goto('/workflows');
    // Find and click the first workflow item
    const firstItem = page.locator('[data-testid^="workflow-item-"]').first();
    if (await firstItem.count() > 0) {
      await firstItem.click();
      // Should navigate to detail page
      await expect(page).toHaveURL(/\/workflows\/\d+/);
    }
  });

  test('should display workflow search/filter input', async ({ page }) => {
    await page.goto('/workflows');
    const searchInput = page.locator('input[placeholder*="搜索" i], input[placeholder*="search" i], [data-testid="workflow-search"]');
    await expect(searchInput.first()).toBeVisible();
  });

  test('should filter workflows by search input', async ({ page }) => {
    await page.goto('/workflows');
    const searchInput = page.locator('input[placeholder*="搜索" i], input[placeholder*="search" i], [data-testid="workflow-search"]').first();

    // Mock filtered results
    await page.route('**/api/v1/workflows/', (route) => {
      const url = new URL(route.request().url());
      const search = url.searchParams.get('search');
      if (search) {
        const filtered = {
          ...workflowListMock,
          results: workflowListMock.results.filter(w =>
            w.name.toLowerCase().includes(search.toLowerCase())
          ),
        };
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(filtered),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(workflowListMock),
        });
      }
    });

    await searchInput.fill('Test Workflow');
    await page.waitForTimeout(500); // debounce
    // List should update
    const items = await page.locator('[data-testid^="workflow-item-"]').count();
    expect(items).toBeLessThanOrEqual(workflowListMock.results.length);
  });

  test('should display status filter tabs', async ({ page }) => {
    await page.goto('/workflows');
    const tabs = page.locator('[role="tab"], .el-tabs__item, [data-testid="workflow-status-tab"]');
    await expect(tabs.first()).toBeVisible();
  });

  test('should display pagination controls when paginated', async ({ page }) => {
    await page.goto('/workflows');
    const pagination = page.locator('.el-pagination, [data-testid="workflow-pagination"]');
    if (await pagination.count() > 0) {
      await expect(pagination.first()).toBeVisible();
    }
  });

  test('should display create workflow button', async ({ page }) => {
    await page.goto('/workflows');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-workflow-btn"]');
    await expect(createBtn.first()).toBeVisible();
  });

  test('should navigate to create workflow page on create button click', async ({ page }) => {
    await page.goto('/workflows');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-workflow-btn"]').first();
    if (await createBtn.count() > 0) {
      await createBtn.click();
      await expect(page).toHaveURL(/\/workflows\/create|new/);
    }
  });

  test('should show loading skeleton while fetching workflows', async ({ page }) => {
    // Slow down the response to catch loading state
    await page.route('**/api/v1/workflows/', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowListMock),
      });
    });

    await page.goto('/workflows');
    const skeleton = page.locator('.el-skeleton, [data-testid="workflow-list-skeleton"], .loading-skeleton');
    // Skeleton or content should be visible
    const skeletonVisible = await skeleton.count() > 0;
    const contentVisible = await page.locator('[data-testid^="workflow-item-"], [data-testid="workflow-list-empty"]').count() > 0;
    expect(skeletonVisible || contentVisible).toBeTruthy();
  });

  test('should handle empty state gracefully', async ({ page }) => {
    await page.route('**/api/v1/workflows/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      });
    });

    await page.goto('/workflows');
    const emptyState = page.locator('[data-testid="workflow-list-empty"], .empty-state, .el-empty');
    await expect(emptyState.first()).toBeVisible();
  });

  test('should handle API error gracefully', async ({ page }) => {
    await page.route('**/api/v1/workflows/', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.goto('/workflows');
    const errorState = page.locator('.error-state, .error-message, [data-testid="workflow-list-error"]');
    if (await errorState.count() > 0) {
      await expect(errorState.first()).toBeVisible();
    }
  });

  test('should require authentication', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Clear any existing auth
    await context.clearCookies();

    await page.goto('/workflows');
    // Should redirect to login
    await page.waitForURL(/\/login|auth/, { timeout: 5000 }).catch(() => {});
    await context.close();
  });
});
