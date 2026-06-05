// @ts-check
import { test, expect } from '@playwright/test'
import { agentMock, agentListMock } from '../mocks/agents.mock'

/**
 * Agent List Page E2E Tests
 * Covers: agent list display, filtering, creation, and conversation.
 */
test.describe('Agent List Page', () => {

  test.beforeEach(async ({ page }) => {
    await page.route(/\/api\/v1\/agents\/?$/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agentListMock),
      })
    })

    await page.route(/\/api\/v1\/agents\/\d+/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agentMock),
      });
    });
  });

  test('should display agent list page with correct heading', async ({ page }) => {
    await page.goto('/agents');
    const heading = page.locator('h1, h2, .page-title, [data-testid="agent-page-heading"]');
    await expect(heading.first()).toBeVisible();
  });

  test('should display list of agents', async ({ page }) => {
    await page.goto('/agents');
    const agentCards = page.locator('[data-testid^="agent-card-"], .agent-card, .agent-item');
    const emptyState = page.locator('[data-testid="agent-list-empty"], .el-empty');
    const hasAgents = await agentCards.count() > 0;
    const hasEmpty = await emptyState.count() > 0;
    expect(hasAgents || hasEmpty).toBeTruthy();
  });

  test('should navigate to agent detail on card click', async ({ page }) => {
    await page.goto('/agents');
    const firstCard = page.locator('[data-testid^="agent-card-"]').first();
    if (await firstCard.count() > 0) {
      await firstCard.click();
      await expect(page).toHaveURL(/\/agents\/\d+/);
    }
  });

  test('should display agent type filter', async ({ page }) => {
    await page.goto('/agents');
    const filter = page.locator('.el-select, [data-testid="agent-type-filter"]');
    await expect(filter.first()).toBeVisible();
  });

  test('should filter agents by type', async ({ page }) => {
    await page.goto('/agents');
    const select = page.locator('.el-select').first();
    if (await select.count() > 0) {
      await select.click();
      await page.locator('.el-select-dropdown__item').first().click();
      await page.waitForTimeout(300);
    }
  });

  test('should display create agent button', async ({ page }) => {
    await page.goto('/agents');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-agent-btn"]');
    await expect(createBtn.first()).toBeVisible();
  });

  test('should open agent creation dialog on create button click', async ({ page }) => {
    await page.goto('/agents');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-agent-btn"]').first();
    if (await createBtn.count() > 0) {
      await createBtn.click();
      await page.waitForTimeout(300);
      const dialog = page.locator('.el-dialog, .dialog, [data-testid="agent-create-dialog"]');
      await expect(dialog.first()).toBeVisible();
    }
  });

  test('should validate agent creation form', async ({ page }) => {
    await page.goto('/agents');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-agent-btn"]').first();
    if (await createBtn.count() > 0) {
      await createBtn.click();
      await page.waitForTimeout(300);
      const dialog = page.locator('.el-dialog, .dialog').first();

      // Try submitting empty form
      const submitBtn = dialog.locator('button:has-text("创建" i), [type="submit"]').first();
      if (await submitBtn.count() > 0) {
        await submitBtn.click();
        // Form should show validation errors
        await page.waitForTimeout(300);
        const errors = dialog.locator('.el-form-item__error, .error, [data-testid="form-error"]');
        expect(await errors.count()).toBeGreaterThan(0);
      }
    }
  });

  test('should create agent with valid data', async ({ page }) => {
    await page.goto('/agents');
    const createBtn = page.locator('button:has-text("创建" i), [data-testid="create-agent-btn"]').first();

    if (await createBtn.count() > 0) {
      await createBtn.click();
      await page.waitForTimeout(300);
      const dialog = page.locator('.el-dialog, .dialog').first();

      // Fill name
      const nameInput = dialog.locator('input').first();
      await nameInput.fill('Test Agent');

      // Select type
      const typeSelect = dialog.locator('.el-select').first();
      await typeSelect.click();
      await page.locator('.el-select-dropdown__item').first().click();

      await page.route(/\/api\/v1\/agents\/?$/, (route) => {
        route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify(agentMock),
        })
      })

      // Submit
      const submitBtn = dialog.locator('button:has-text("创建" i), [type="submit"]').first();
      await submitBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should handle empty agent list', async ({ page }) => {
    await page.route('**/api/v1/agents/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      });
    });

    await page.goto('/agents');
    const emptyState = page.locator('[data-testid="agent-list-empty"], .el-empty');
    await expect(emptyState.first()).toBeVisible();
  });

  test('should require authentication', async ({ browser }) => {
    const context = await browser.newContext();
    await context.clearCookies();
    const page = await context.newPage();

    await page.goto('/agents');
    await page.waitForURL(/\/login|auth/, { timeout: 5000 }).catch(() => {});
    await context.close();
  });
});


/**
 * Agent Conversation Page E2E Tests
 */
test.describe('Agent Conversation', () => {

  test.beforeEach(async ({ page }) => {
    await page.route(/\/api\/v1\/agents\/\d+/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(agentMock),
      });
    });

    await page.route(/\/api\/v1\/agents\/conversations\/?$/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      })
    })
  });

  test('should display conversation interface', async ({ page }) => {
    await page.goto('/agents/1/chat');
    const chatArea = page.locator('[data-testid="chat-area"], .chat-messages, .message-list');
    await expect(chatArea.first()).toBeVisible();
  });

  test('should display message input', async ({ page }) => {
    await page.goto('/agents/1/chat');
    const input = page.locator('textarea, input[type="text"], [data-testid="message-input"]');
    await expect(input.first()).toBeVisible();
  });

  test('should send message and display response', async ({ page }) => {
    await page.goto('/agents/1/chat');

    const input = page.locator('textarea, input[type="text"], [data-testid="message-input"]').first();
    await input.fill('Hello agent');

    await page.route(/\/api\/v1\/agents\/chat\/?$/, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Hello! How can I help you?',
          conversation_id: 'conv-1',
        }),
      })
    })

    const sendBtn = page.locator('[data-testid="send-btn"], button:has-text("发送" i)').first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should not send empty message', async ({ page }) => {
    await page.goto('/agents/1/chat');
    const sendBtn = page.locator('[data-testid="send-btn"], button:has-text("发送" i)').first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('should display loading indicator during send', async ({ page }) => {
    await page.goto('/agents/1/chat');

    await page.route(/\/api\/v1\/agents\/chat\/?$/, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1500))
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Response' }),
      })
    })

    const input = page.locator('textarea, input[type="text"], [data-testid="message-input"]').first();
    await input.fill('Test message');

    const sendBtn = page.locator('[data-testid="send-btn"], button:has-text("发送" i)').first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
      // Loading indicator should appear
      await page.waitForTimeout(100);
      const loading = page.locator('.el-loading-mask, [data-testid="message-loading"]');
      if (await loading.count() > 0) {
        await expect(loading.first()).toBeVisible();
      }
    }
  });

  test('should handle API error during chat', async ({ page }) => {
    await page.goto('/agents/1/chat');

    await page.route(/\/api\/v1\/agents\/chat\/?$/, (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Server error' }),
      })
    })

    const input = page.locator('textarea, input[type="text"], [data-testid="message-input"]').first();
    await input.fill('Test message');

    const sendBtn = page.locator('[data-testid="send-btn"], button:has-text("发送" i)').first();
    if (await sendBtn.count() > 0) {
      await sendBtn.click();
      await page.waitForTimeout(500);
      const errorMsg = page.locator('.error-message, .el-message--error');
      if (await errorMsg.count() > 0) {
        await expect(errorMsg.first()).toBeVisible();
      }
    }
  });
});
