// @ts-check
import { test, expect } from '@playwright/test'
import { workflowListMock, workflowDetailMock } from '../vitest/mocks/workflows.mock'

/**
 * Workflow List Page E2E Tests
 * Covers: workflow list display, filtering, sorting, pagination, and empty states.
 */

// 登录态：通过 localStorage 与 cookie 注入 token，路由守卫读取 access_token 后放行受保护页面。
// 注意不能只注入 cookie：js-cookie 与 addCookies 组合在 SPA 首屏会被 401 拦截器清空。
const MOCK_USER = { id: 1, username: 'testuser', email: 'test@example.com', avatar: null }

// 列表接口可能带分页/搜索参数，统一用正则匹配到可选查询串
const WORKFLOW_LIST_RE = /\/api\/v1\/workflows\/?(\?.*)?$/
// 详情接口（UUID 主键，不能用 \d+）
const WORKFLOW_DETAIL_RE = /\/api\/v1\/workflows\/[^/]+\/$/

async function setupAuth(page) {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'mock-access-token')
    localStorage.setItem('refresh_token', 'mock-refresh-token')
    document.cookie = 'access_token=mock-access-token; path=/'
    document.cookie = 'refresh_token=mock-refresh-token; path=/'
  })

  // 路由守卫会拉取用户信息，必须 mock 成功，否则会被重定向到登录页
  await page.route(/\/api\/v1\/auth\/user\/$/, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_USER),
    })
  })

  // 侧边栏 AppLayout 会拉取已生成站点导航，mock 空列表避免真实 401 连锁清空登录态
  await page.route(/\/api\/v1\/website-generator(\/|\?|$)/, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: 0, results: [] }),
    })
  })

  // 编辑器/详情页会拉取模型与工具列表，未 mock 时真实后端 401 会清空登录态
  await page.route(/\/api\/v1\/gateway\/models\/available\/?(\?.*)?$/, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: 0, results: [] }),
    })
  })
  await page.route(/\/api\/v1\/tools\/?(\?.*)?$/, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: 0, results: [] }),
    })
  })
  await page.route(/\/api\/v1\/workflows\/executions\/?(\?.*)?$/, (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ count: 0, results: [] }),
    })
  })
}

test.describe('Workflow List Page', () => {

  test.beforeEach(async ({ page }) => {
    await setupAuth(page)

    await page.route(WORKFLOW_LIST_RE, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowListMock),
      })
    })

    await page.route(WORKFLOW_DETAIL_RE, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowDetailMock),
      })
    })
  })

  test('should display workflow list page with correct title', async ({ page }) => {
    await page.goto('/workflows')
    await expect(page).toHaveTitle(/工作流|Workflow/i)
  })

  test('should display list of workflows', async ({ page }) => {
    await page.goto('/workflows')
    const rows = page.locator('.el-table__row')
    await expect(rows.first()).toBeVisible()
    await expect(rows).toHaveCount(workflowListMock.results.length)
  })

  test('should navigate to workflow detail on click', async ({ page }) => {
    await page.goto('/workflows')
    // 表格里的名称链接指向详情页；页头还有「新建工作流」链接，需要限定在表格内
    const firstLink = page.locator('.workflow-table a[href^="/workflows/"]').first()
    await expect(firstLink).toBeVisible()
    await firstLink.click()
    await expect(page).toHaveURL(/\/workflows\/[^/]+$/)
  })

  test('should display workflow search/filter input', async ({ page }) => {
    await page.goto('/workflows')
    const searchInput = page.locator('input[placeholder="搜索工作流..."]')
    await expect(searchInput).toBeVisible()
  })

  test('should filter workflows by search input', async ({ page }) => {
    await page.goto('/workflows')

    // 搜索时按 search 参数过滤，模拟后端筛选结果
    await page.route(WORKFLOW_LIST_RE, (route) => {
      const url = new URL(route.request().url())
      const search = (url.searchParams.get('search') || '').toLowerCase()
      const filtered = {
        ...workflowListMock,
        results: workflowListMock.results.filter(w =>
          w.name.toLowerCase().includes(search)
        ),
      }
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(filtered),
      })
    })

    const searchInput = page.locator('input[placeholder="搜索工作流..."]')
    await searchInput.fill('Test Workflow')
    // 页面搜索有 300ms 防抖
    await expect(page.locator('.el-table__row')).toHaveCount(1, { timeout: 5000 })
    await expect(page.locator('.el-table__row').first()).toContainText('Test Workflow')
  })

  test('should display status filter select', async ({ page }) => {
    await page.goto('/workflows')
    const statusSelect = page.locator('.status-select')
    await expect(statusSelect).toBeVisible()
  })

  test('should display pagination controls when paginated', async ({ page }) => {
    // 返回超过一页的数据量，触发分页组件渲染
    const manyResults = Array.from({ length: 30 }, (_, i) => ({
      ...workflowListMock.results[i % workflowListMock.results.length],
      id: `123e4567-e89b-12d3-a456-426614174${String(i).padStart(3, '0')}`,
      name: `Workflow ${i + 1}`,
    }))
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/workflows')) console.log('WF REQ:', req.url())
    })
    await page.route(WORKFLOW_LIST_RE, (route) => {
      console.log('PAGINATION ROUTE HIT:', route.request().url())
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 30, results: manyResults }),
      })
    })

    await page.goto('/workflows')
    await page.waitForTimeout(1000)
    await expect(page.locator('.el-pagination')).toBeVisible()
  })

  test('should display create workflow button', async ({ page }) => {
    await page.goto('/workflows')
    const createBtn = page.locator('a[href="/workflows/new"]')
    await expect(createBtn).toBeVisible()
  })

  test('should navigate to create workflow page on create button click', async ({ page }) => {
    await page.goto('/workflows')
    await page.locator('a[href="/workflows/new"]').click()
    await expect(page).toHaveURL(/\/workflows\/new/)
  })

  test('should show loading skeleton while fetching workflows', async ({ page }) => {
    // 放慢响应以捕获加载态
    await page.route(WORKFLOW_LIST_RE, async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1200))
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(workflowListMock),
      })
    })

    await page.goto('/workflows')
    await expect(page.locator('.el-skeleton')).toBeVisible()
  })

  test('should handle empty state gracefully', async ({ page }) => {
    await page.route(WORKFLOW_LIST_RE, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ count: 0, results: [] }),
      })
    })

    await page.goto('/workflows')
    const emptyState = page.locator('.page-empty-state')
    await expect(emptyState).toBeVisible()
    await expect(emptyState).toContainText('暂无工作流')
  })

  test('should handle API error gracefully', async ({ page }) => {
    await page.route(WORKFLOW_LIST_RE, (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      })
    })

    await page.goto('/workflows')
    const errorState = page.locator('.list-feedback[role="alert"]')
    await expect(errorState).toBeVisible()
    await expect(errorState).toContainText('工作流加载失败')
  })

  test('should require authentication', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()

    // 清空 cookie，验证受保护路由会跳转登录
    await context.clearCookies()
    await page.goto('/workflows')
    await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
    await context.close()
  })
})
