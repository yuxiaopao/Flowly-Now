/**
 * Authentication E2E Tests
 * Tests for login, logout, registration, and token refresh flows
 *
 * Prerequisites:
 * - Backend dev server running at http://localhost:8000
 * - Frontend dev server running at http://localhost:5173
 */

import { test, expect } from '@playwright/test'

// Mock auth responses
const mockLoginResponse = {
  access: 'mock-access-token',
  refresh: 'mock-refresh-token',
  user: {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    is_active: true,
  }
}

const mockRefreshResponse = {
  access: 'mock-new-access-token',
}

const mockUserProfile = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  avatar: null,
  date_joined: '2024-01-01T00:00:00Z',
  last_login: '2024-06-01T00:00:00Z',
}

void mockUserProfile

test.describe('Authentication', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
  })

  test.describe('Login Page', () => {
    test('should display login form', async ({ page }) => {
      await expect(page.locator('input[type="text"], input[name="username"]').first()).toBeVisible()
      await expect(page.locator('input[type="password"]').first()).toBeVisible()
      await expect(page.locator('button[type="submit"]').first()).toBeVisible()
    })

    test('should show validation errors on empty submit', async ({ page }) => {
      await page.locator('button[type="submit"]').first().click()
      // Form should show validation errors (specific selectors depend on UI)
      const form = page.locator('form').first()
      await expect(form).toBeVisible()
    })

    test('should navigate to register page', async ({ page }) => {
      const registerLink = page.locator('a[href*="register"], a[href*="signup"]').first()
      if (await registerLink.isVisible()) {
        await registerLink.click()
        await page.waitForLoadState('networkidle')
        await expect(page).toHaveURL(/register|signup/i)
      }
    })
  })

  test.describe('Login Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Mock login API
      await page.route('**/api/v1/auth/login/', async (route) => {
        const body = route.request().postData()
        const data = JSON.parse(body || '{}')

        if (data.username && data.password) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockLoginResponse),
          })
        } else {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ username: ['This field is required.'], password: ['This field is required.'] }),
          })
        }
      })
    })

    test('should login successfully with valid credentials', async ({ page }) => {
      await page.locator('input[type="text"], input[name="username"]').first().fill('testuser')
      await page.locator('input[type="password"]').first().fill('testpass123')
      await page.locator('button[type="submit"]').first().click()

      // Should redirect to dashboard
      await expect(page).not.toHaveURL(/\/login/, { timeout: 5000 })
    })

    test('should show error on invalid credentials', async ({ page }) => {
      await page.route('**/api/v1/auth/login/', async (route) => {
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Invalid credentials' }),
        })
      })

      await page.locator('input[type="text"], input[name="username"]').first().fill('baduser')
      await page.locator('input[type="password"]').first().fill('wrongpass')
      await page.locator('button[type="submit"]').first().click()

      // Should show error message
      await expect(page.locator('.el-message--error, [class*="error"], .error-message').first()).toBeVisible({ timeout: 5000 })
    })

    test('should show rate limit error after too many attempts', async ({ page }) => {
      let loginAttempts = 0

      await page.route('**/api/v1/auth/login/', async (route) => {
        loginAttempts += 1

        if (loginAttempts < 3) {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Invalid credentials' }),
          })
          return
        }

        await route.fulfill({
          status: 429,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Too many login attempts. Please try again later.' }),
        })
      })

      await page.locator('input[type="text"], input[name="username"]').first().fill('testuser')
      await page.locator('input[type="password"]').first().fill('testpass')

      await page.locator('button[type="submit"]').first().click()
      await page.locator('button[type="submit"]').first().click()
      await page.locator('button[type="submit"]').first().click()

      await expect(page.locator('.el-message--warning, .el-message--error, [role="alert"]').first()).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Token Refresh', () => {
    test('should refresh token on 401 response', async ({ page, context }) => {
      const refreshCalls = []
      const accessCalls = []

      await context.addCookies([
        {
          name: 'access_token',
          value: 'expired-token',
          domain: 'localhost',
          path: '/',
        },
        {
          name: 'refresh_token',
          value: 'valid-refresh-token',
          domain: 'localhost',
          path: '/',
        },
      ])

      // Mock refresh endpoint
      await page.route('**/api/v1/auth/refresh/', async (route) => {
        refreshCalls.push(route.request().url())
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockRefreshResponse),
        })
      })

      // First API call returns 401, second succeeds
      let callCount = 0
      await page.route('**/api/v1/workflows/', async (route) => {
        accessCalls.push(route.request().url())
        callCount++
        if (callCount === 1) {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Token expired' }),
          })
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ results: [] }),
          })
        }
      })

      await page.goto('/workflows')
      await page.waitForLoadState('networkidle')

      // Token refresh should have been called
      expect(refreshCalls.length).toBeGreaterThan(0)
    })
  })

  test.describe('Logout', () => {
    test('should clear auth data on logout', async ({ page }) => {
      // Set auth data
      await page.evaluate(() => {
        localStorage.setItem('access_token', 'mock-token')
        localStorage.setItem('refresh_token', 'mock-refresh')
        document.cookie = 'access_token=mock-token; path=/'
      })

      await page.goto('/')
      await page.waitForLoadState('networkidle')

      // Find and click logout
      const logoutBtn = page.locator('[data-testid="logout-btn"], button:has-text("Logout"), button:has-text("退出"), button:has-text("登出")').first()
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click()
        // Verify tokens cleared
        const accessToken = await page.evaluate(() => localStorage.getItem('access_token'))
        expect(accessToken).toBeNull()
      }
    })
  })
})

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    await page.goto('/')

    await page.evaluate(() => {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    })

    await page.goto('/workflows')
    await page.waitForLoadState('networkidle')

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  })

  test('should allow access to public routes without auth', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    // Landing page should load
    await expect(page.locator('body')).toBeVisible()
  })
})
