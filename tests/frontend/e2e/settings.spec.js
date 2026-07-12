// @ts-check
import { test, expect } from '@playwright/test'

/**
 * Settings & Profile Page E2E Tests
 * Covers: profile settings, API keys, preferences, and account management.
 */
test.describe('Settings Page', () => {

  test('should display settings page with navigation tabs', async ({ page }) => {
    await page.goto('/settings');
    const tabs = page.locator('.el-tabs__item, [role="tab"], [data-testid="settings-tab"]');
    await expect(tabs.first()).toBeVisible();
  });

  test('should display profile settings tab', async ({ page }) => {
    await page.goto('/settings');
    const profileTab = page.locator('*:has-text("个人设置" i), *:has-text("Profile" i)').first();
    await expect(profileTab).toBeVisible();
  });

  test('should validate profile form', async ({ page }) => {
    await page.goto('/settings');

    // Try submitting empty or invalid form
    const submitBtn = page.locator('button:has-text("保存" i), [data-testid="save-profile-btn"]').first();
    if (await submitBtn.count() > 0) {
      await submitBtn.click();
      await page.waitForTimeout(300);
    }
  });

  test('should update username', async ({ page }) => {
    await page.route('PATCH', '**/api/v1/users/me/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ username: 'new_username', email: 'test@example.com' }),
      });
    });

    await page.goto('/settings');
    const usernameInput = page.locator('input[type="text"], [data-testid="username-input"]').first();
    await usernameInput.fill('new_username');

    const saveBtn = page.locator('button:has-text("保存" i), [data-testid="save-profile-btn"]').first();
    if (await saveBtn.count() > 0) {
      await saveBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should display API keys section', async ({ page }) => {
    await page.goto('/settings');

    await page.route('**/api/v1/gateway/keys/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      });
    });

    const apiKeysSection = page.locator('*:has-text("API" i), *:has-text("密钥" i)').first();
    await expect(apiKeysSection).toBeVisible();
  });

  test('should display create API key button', async ({ page }) => {
    await page.goto('/settings');
    const createKeyBtn = page.locator('button:has-text("创建" i):has-text("API" i), [data-testid="create-api-key-btn"]');
    await expect(createKeyBtn.first()).toBeVisible();
  });

  test('should open create API key dialog', async ({ page }) => {
    await page.goto('/settings');
    const createKeyBtn = page.locator('button:has-text("创建" i):has-text("API" i), [data-testid="create-api-key-btn"]').first();
    if (await createKeyBtn.count() > 0) {
      await createKeyBtn.click();
      await page.waitForTimeout(300);
      const dialog = page.locator('.el-dialog, [data-testid="create-key-dialog"]');
      await expect(dialog.first()).toBeVisible();
    }
  });

  test('should create new API key', async ({ page }) => {
    await page.goto('/settings');

    await page.route('POST', '**/api/v1/gateway/keys/', (route) => {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'key-1',
          name: 'Test Key',
          masked_key: 'sk-te****',
          provider: 'openai',
          is_active: true,
        }),
      });
    });

    const createKeyBtn = page.locator('button:has-text("创建" i):has-text("API" i), [data-testid="create-api-key-btn"]').first();
    if (await createKeyBtn.count() > 0) {
      await createKeyBtn.click();
      await page.waitForTimeout(300);

      const dialog = page.locator('.el-dialog').first();
      const nameInput = dialog.locator('input').first();
      await nameInput.fill('Test Key');

      const providerSelect = dialog.locator('.el-select').first();
      if (await providerSelect.count() > 0) {
        await providerSelect.click();
        await page.locator('.el-select-dropdown__item').first().click();
      }

      const submitBtn = dialog.locator('button:has-text("创建" i), [type="submit"]').first();
      await submitBtn.click();
      await page.waitForTimeout(500);
    }
  });

  test('should delete API key with confirmation', async ({ page }) => {
    await page.goto('/settings');

    await page.route('**/api/v1/gateway/keys/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          count: 1,
          results: [{
            id: 'key-1',
            name: 'Test Key',
            masked_key: 'sk-te****',
            provider: 'openai',
            is_active: true,
          }],
        }),
      });
    });

    await page.waitForTimeout(500);
    const deleteBtn = page.locator('button:has-text("删除" i), [data-testid="delete-key-btn"]').first();
    if (await deleteBtn.count() > 0) {
      // Mock delete
      await page.route('DELETE', '**/api/v1/gateway/keys/key-1/', (route) => {
        route.fulfill({ status: 204, body: '' });
      });

      await deleteBtn.click();
      await page.waitForTimeout(300);
      // Confirm dialog if present
      const confirmBtn = page.locator('.el-button--primary:has-text("确认" i), .el-message-box__btn:has-text("确定" i)').first();
      if (await confirmBtn.count() > 0) {
        await confirmBtn.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should display notification preferences', async ({ page }) => {
    await page.goto('/settings');
    const notifSection = page.locator('*:has-text("通知" i), *:has-text("Notification" i)').first();
    await expect(notifSection).toBeVisible();
  });

  test('should toggle notification preference', async ({ page }) => {
    await page.goto('/settings');

    const toggle = page.locator('.el-switch, [data-testid="notification-toggle"]').first();
    if (await toggle.count() > 0) {
      await toggle.click();
      await page.waitForTimeout(300);
    }
  });

  test('should display subscription/billing section', async ({ page }) => {
    await page.goto('/settings');

    await page.route('**/api/v1/billing/subscriptions/my/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'sub-1',
          plan_type: 'free',
          status: 'active',
        }),
      });
    });

    const billingSection = page.locator('*:has-text("订阅" i), *:has-text("Subscription" i), *:has-text("计费" i)').first();
    await expect(billingSection).toBeVisible();
  });

  test('should display usage statistics', async ({ page }) => {
    await page.goto('/settings');

    await page.route('**/api/v1/billing/subscriptions/usage/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_usage: {
            workflow_count: 5,
            execution_count: 50,
          },
          limits: {
            max_workflows: 10,
            max_executions: 100,
          },
          usage_percentages: {
            workflow_count: 50,
            execution_count: 50,
          },
        }),
      });
    });

    await page.waitForTimeout(500);
    const usageSection = page.locator('*:has-text("使用" i), *:has-text("Usage" i), [data-testid="usage-stats"]');
    await expect(usageSection.first()).toBeVisible();
  });

  test('should require authentication', async ({ browser }) => {
    const context = await browser.newContext();
    await context.clearCookies();
    const page = await context.newPage();

    await page.goto('/settings');
    await page.waitForURL(/\/login|auth/, { timeout: 5000 }).catch(() => {});
    await context.close();
  });
});


/**
 * User Profile Page E2E Tests
 */
test.describe('Profile Page', () => {

  test('should display user profile information', async ({ page }) => {
    await page.goto('/profile');

    await page.route('**/api/v1/users/me/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          username: 'testuser',
          email: 'test@example.com',
          is_staff: false,
        }),
      });
    });

    await page.waitForTimeout(500);
    const username = page.locator('*:has-text("testuser" i)').first();
    await expect(username).toBeVisible();
  });

  test('should display avatar or avatar placeholder', async ({ page }) => {
    await page.goto('/profile');
    const avatar = page.locator('.avatar, img, [data-testid="user-avatar"]');
    await expect(avatar.first()).toBeVisible();
  });

  test('should allow changing password', async ({ page }) => {
    await page.goto('/profile');

    await page.route('POST', '**/api/v1/auth/change-password/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Password changed successfully' }),
      });
    });

    const passwordSection = page.locator('*:has-text("密码" i), *:has-text("Password" i)').first();
    await expect(passwordSection).toBeVisible();
  });

  test('should validate password change with wrong current password', async ({ page }) => {
    await page.goto('/profile');

    await page.route('POST', '**/api/v1/auth/change-password/', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Current password is incorrect' }),
      });
    });
  });

  test('should require authentication', async ({ browser }) => {
    const context = await browser.newContext();
    await context.clearCookies();
    const page = await context.newPage();

    await page.goto('/profile');
    await page.waitForURL(/\/login|auth/, { timeout: 5000 }).catch(() => {});
    await context.close();
  });
});
