# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: auth.spec.js >> Authentication >> Token Refresh >> should refresh token on 401 response
- Location: tests\e2e\auth.spec.js:154:5

# Error details

```
Error: expect(received).toBeGreaterThan(expected)

Expected: > 0
Received:   0
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e4]:
    - complementary [ref=e5]:
      - link "Flowly Flowly" [ref=e7] [cursor=pointer]:
        - /url: /home
        - img "Flowly" [ref=e8]
        - generic [ref=e9]: Flowly
      - navigation [ref=e10]:
        - generic [ref=e11]:
          - generic [ref=e12]: 主导航
          - link "仪表盘" [ref=e13] [cursor=pointer]:
            - /url: /home
            - img [ref=e14]
            - generic [ref=e17]: 仪表盘
          - link "工作流" [ref=e18] [cursor=pointer]:
            - /url: /workflows
            - img [ref=e19]
            - generic [ref=e23]: 工作流
          - link "Agent" [ref=e24] [cursor=pointer]:
            - /url: /agents
            - img [ref=e25]
            - generic [ref=e28]: Agent
          - link "知识库" [ref=e29] [cursor=pointer]:
            - /url: /knowledge
            - img [ref=e30]
            - generic [ref=e34]: 知识库
          - link "团队" [ref=e35] [cursor=pointer]:
            - /url: /team
            - img [ref=e36]
            - generic [ref=e41]: 团队
        - generic [ref=e42]:
          - generic [ref=e43]: 工具
          - link "NL 创建" [ref=e44] [cursor=pointer]:
            - /url: /nl-create
            - img [ref=e45]
            - generic [ref=e47]: NL 创建
          - link "代码图谱" [ref=e48] [cursor=pointer]:
            - /url: /codegraph
            - img [ref=e49]
            - generic [ref=e54]: 代码图谱
          - link "监控中心" [ref=e55] [cursor=pointer]:
            - /url: /monitoring
            - img [ref=e56]
            - generic [ref=e57]: 监控中心
          - link "模板" [ref=e58] [cursor=pointer]:
            - /url: /prompts
            - img [ref=e59]
            - generic [ref=e62]: 模板
          - link "数据集推荐" [ref=e63] [cursor=pointer]:
            - /url: /dataset-recommend
            - img [ref=e64]
            - generic [ref=e67]: 数据集推荐
          - link "数据增强" [ref=e68] [cursor=pointer]:
            - /url: /augmentations
            - img [ref=e69]
            - generic [ref=e73]: 数据增强
        - generic [ref=e74]:
          - generic [ref=e75]: 工作流
          - link "新建工作流" [ref=e76] [cursor=pointer]:
            - /url: /workflows/new
            - img [ref=e77]
            - generic [ref=e78]: 新建工作流
      - link "设置" [ref=e80] [cursor=pointer]:
        - /url: /settings
        - img [ref=e81]
        - generic [ref=e84]: 设置
    - generic [ref=e85]:
      - banner [ref=e86]:
        - button [ref=e87] [cursor=pointer]:
          - img [ref=e88]
        - generic [ref=e91]:
          - button "当前主题：深色模式" [ref=e94] [cursor=pointer]:
            - img [ref=e96]
          - button [ref=e99] [cursor=pointer]:
            - img [ref=e101]
          - button [ref=e104] [cursor=pointer]:
            - img [ref=e106]
          - button [ref=e110] [cursor=pointer]
      - main [ref=e112]:
        - generic [ref=e113]:
          - generic [ref=e114]:
            - generic [ref=e115]:
              - heading "工作流" [level=1] [ref=e116]
              - generic [ref=e117]: 0 个工作流
            - generic [ref=e118]:
              - generic [ref=e120]:
                - img [ref=e123]
                - textbox "搜索工作流..." [ref=e126]
              - generic [ref=e128] [cursor=pointer]:
                - generic:
                  - combobox [ref=e130]
                  - generic [ref=e131]: 状态
                - img [ref=e134]
              - link "新建工作流" [ref=e136] [cursor=pointer]:
                - /url: /workflows/new
                - button "新建工作流" [ref=e137]:
                  - img [ref=e139]
                  - generic [ref=e141]: 新建工作流
          - generic [ref=e142]:
            - img [ref=e143]
            - heading "暂无工作流" [level=3] [ref=e147]
            - paragraph [ref=e148]: 创建您的第一个 AI 工作流
            - link "创建工作流" [ref=e149] [cursor=pointer]:
              - /url: /workflows/new
              - button "创建工作流" [ref=e150]:
                - generic [ref=e152]: 创建工作流
  - generic:
    - alert [ref=e153]:
      - img [ref=e154]
      - paragraph [ref=e157]: 网络连接失败，请检查网络
      - button "关闭" [ref=e158] [cursor=pointer]:
        - img [ref=e159]
    - alert [ref=e163]:
      - img [ref=e164]
      - paragraph [ref=e167]: 网络连接失败，请检查网络
      - button "关闭" [ref=e168] [cursor=pointer]:
        - img [ref=e169]
    - alert [ref=e173]:
      - img [ref=e174]
      - paragraph [ref=e177]: 网络连接失败，请检查网络
      - button "关闭" [ref=e178] [cursor=pointer]:
        - img [ref=e179]
    - alert [ref=e183]:
      - img [ref=e184]
      - paragraph [ref=e187]: 获取工作流列表失败
      - button "关闭" [ref=e188] [cursor=pointer]:
        - img [ref=e189]
  - generic:
    - alert [ref=e193]:
      - img [ref=e194]
      - paragraph [ref=e197]: 网络连接失败，请检查网络
      - button "关闭" [ref=e198] [cursor=pointer]:
        - img [ref=e199]
    - alert [ref=e203]:
      - img [ref=e204]
      - paragraph [ref=e207]: 网络连接失败，请检查网络
      - button "关闭" [ref=e208] [cursor=pointer]:
        - img [ref=e209]
    - alert [ref=e213]:
      - img [ref=e214]
      - paragraph [ref=e217]: 网络连接失败，请检查网络
      - button "关闭" [ref=e218] [cursor=pointer]:
        - img [ref=e219]
    - alert [ref=e223]:
      - img [ref=e224]
      - paragraph [ref=e227]: 获取工作流列表失败
      - button "关闭" [ref=e228] [cursor=pointer]:
        - img [ref=e229]
```

# Test source

```ts
  107 |           contentType: 'application/json',
  108 |           body: JSON.stringify({ detail: 'Invalid credentials' }),
  109 |         })
  110 |       })
  111 | 
  112 |       await page.locator('input[type="text"], input[name="username"]').first().fill('baduser')
  113 |       await page.locator('input[type="password"]').first().fill('wrongpass')
  114 |       await page.locator('button[type="submit"]').first().click()
  115 | 
  116 |       // Should show error message
  117 |       await expect(page.locator('.el-message--error, [class*="error"], .error-message').first()).toBeVisible({ timeout: 5000 })
  118 |     })
  119 | 
  120 |     test('should show rate limit error after too many attempts', async ({ page }) => {
  121 |       let loginAttempts = 0
  122 | 
  123 |       await page.route('**/api/v1/auth/login/', async (route) => {
  124 |         loginAttempts += 1
  125 | 
  126 |         if (loginAttempts < 3) {
  127 |           await route.fulfill({
  128 |             status: 401,
  129 |             contentType: 'application/json',
  130 |             body: JSON.stringify({ detail: 'Invalid credentials' }),
  131 |           })
  132 |           return
  133 |         }
  134 | 
  135 |         await route.fulfill({
  136 |           status: 429,
  137 |           contentType: 'application/json',
  138 |           body: JSON.stringify({ detail: 'Too many login attempts. Please try again later.' }),
  139 |         })
  140 |       })
  141 | 
  142 |       await page.locator('input[type="text"], input[name="username"]').first().fill('testuser')
  143 |       await page.locator('input[type="password"]').first().fill('testpass')
  144 | 
  145 |       await page.locator('button[type="submit"]').first().click()
  146 |       await page.locator('button[type="submit"]').first().click()
  147 |       await page.locator('button[type="submit"]').first().click()
  148 | 
  149 |       await expect(page.locator('.el-message--warning, .el-message--error, [role="alert"]').first()).toBeVisible({ timeout: 5000 })
  150 |     })
  151 |   })
  152 | 
  153 |   test.describe('Token Refresh', () => {
  154 |     test('should refresh token on 401 response', async ({ page, context }) => {
  155 |       const refreshCalls = []
  156 |       const accessCalls = []
  157 | 
  158 |       await context.addCookies([
  159 |         {
  160 |           name: 'access_token',
  161 |           value: 'expired-token',
  162 |           domain: 'localhost',
  163 |           path: '/',
  164 |         },
  165 |         {
  166 |           name: 'refresh_token',
  167 |           value: 'valid-refresh-token',
  168 |           domain: 'localhost',
  169 |           path: '/',
  170 |         },
  171 |       ])
  172 | 
  173 |       // Mock refresh endpoint
  174 |       await page.route('**/api/v1/auth/refresh/', async (route) => {
  175 |         refreshCalls.push(route.request().url())
  176 |         await route.fulfill({
  177 |           status: 200,
  178 |           contentType: 'application/json',
  179 |           body: JSON.stringify(mockRefreshResponse),
  180 |         })
  181 |       })
  182 | 
  183 |       // First API call returns 401, second succeeds
  184 |       let callCount = 0
  185 |       await page.route('**/api/v1/workflows/', async (route) => {
  186 |         accessCalls.push(route.request().url())
  187 |         callCount++
  188 |         if (callCount === 1) {
  189 |           await route.fulfill({
  190 |             status: 401,
  191 |             contentType: 'application/json',
  192 |             body: JSON.stringify({ detail: 'Token expired' }),
  193 |           })
  194 |         } else {
  195 |           await route.fulfill({
  196 |             status: 200,
  197 |             contentType: 'application/json',
  198 |             body: JSON.stringify({ results: [] }),
  199 |           })
  200 |         }
  201 |       })
  202 | 
  203 |       await page.goto('/workflows')
  204 |       await page.waitForLoadState('networkidle')
  205 | 
  206 |       // Token refresh should have been called
> 207 |       expect(refreshCalls.length).toBeGreaterThan(0)
      |                                   ^ Error: expect(received).toBeGreaterThan(expected)
  208 |     })
  209 |   })
  210 | 
  211 |   test.describe('Logout', () => {
  212 |     test('should clear auth data on logout', async ({ page }) => {
  213 |       // Set auth data
  214 |       await page.evaluate(() => {
  215 |         localStorage.setItem('access_token', 'mock-token')
  216 |         localStorage.setItem('refresh_token', 'mock-refresh')
  217 |         document.cookie = 'access_token=mock-token; path=/'
  218 |       })
  219 | 
  220 |       await page.goto('/')
  221 |       await page.waitForLoadState('networkidle')
  222 | 
  223 |       // Find and click logout
  224 |       const logoutBtn = page.locator('[data-testid="logout-btn"], button:has-text("Logout"), button:has-text("退出"), button:has-text("登出")').first()
  225 |       if (await logoutBtn.isVisible()) {
  226 |         await logoutBtn.click()
  227 |         // Verify tokens cleared
  228 |         const accessToken = await page.evaluate(() => localStorage.getItem('access_token'))
  229 |         expect(accessToken).toBeNull()
  230 |       }
  231 |     })
  232 |   })
  233 | })
  234 | 
  235 | test.describe('Protected Routes', () => {
  236 |   test('should redirect to login when accessing protected route without auth', async ({ page }) => {
  237 |     await page.goto('/')
  238 | 
  239 |     await page.evaluate(() => {
  240 |       localStorage.removeItem('access_token')
  241 |       localStorage.removeItem('refresh_token')
  242 |     })
  243 | 
  244 |     await page.goto('/workflows')
  245 |     await page.waitForLoadState('networkidle')
  246 | 
  247 |     // Should redirect to login
  248 |     await expect(page).toHaveURL(/\/login/, { timeout: 5000 })
  249 |   })
  250 | 
  251 |   test('should allow access to public routes without auth', async ({ page }) => {
  252 |     await page.goto('/')
  253 |     await page.waitForLoadState('networkidle')
  254 |     // Landing page should load
  255 |     await expect(page.locator('body')).toBeVisible()
  256 |   })
  257 | })
  258 | 
```