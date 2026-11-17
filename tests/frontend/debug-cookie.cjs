const { chromium } = require('@playwright/test')

;(async () => {
  const browser = await chromium.launch()
  const context = await browser.newContext({ baseURL: 'http://localhost:5200' })
  const page = await context.newPage()
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'mock-access-token')
    localStorage.setItem('refresh_token', 'mock-refresh-token')
  })
  await page.route(/\/api\/v1\/auth\/user\/$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 1, username: 'u', email: 'e@e.com' }) }))
  await page.route(/\/api\/v1\/website-generator(\/|\?|$)/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, results: [] }) }))
  await page.route(/\/api\/v1\/gateway\/models\/available\/?(\?.*)?$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, results: [] }) }))
  await page.route(/\/api\/v1\/tools\/?(\?.*)?$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, results: [] }) }))
  await page.route(/\/api\/v1\/workflows\/executions\/?(\?.*)?$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 0, results: [] }) }))
  await page.route(/\/api\/v1\/workflows\/?(\?.*)?$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ count: 3, results: [
    { id: '123e4567-e89b-12d3-a456-426614174010', name: 'Test Workflow', description: 'A', status: 'draft', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
    { id: '123e4567-e89b-12d3-a456-426614174011', name: 'B', description: '', status: 'draft', created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
  ] }) }))
  await page.route(/\/api\/v1\/workflows\/[^/]+\/$/, (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: '123e4567-e89b-12d3-a456-426614174010', name: 'Test Workflow', description: '', status: 'draft', nodes: [], edges: [] }) }))
  await page.goto('/workflows')
  await page.waitForSelector('.workflow-table a[href^="/workflows/"]')
  console.log('before:', await page.evaluate(() => location.href))
  await page.locator('.workflow-table a[href^="/workflows/"]').first().click()
  await page.waitForTimeout(1500)
  console.log('after click:', await page.evaluate(() => location.href))
  await page.locator('.workflow-table a[href^="/workflows/"]').first().evaluate(el => el.click())
  await page.waitForTimeout(1500)
  console.log('after evaluate click:', await page.evaluate(() => location.href))
  await browser.close()
})().catch(e => { console.error(e); process.exit(1) })
