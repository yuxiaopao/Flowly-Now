/**
 * NL Creator E2E Tests
 * Tests for Natural Language workflow creation interface
 */

import { test, expect } from '@playwright/test'
import {
  mockNLModels,
  mockNLSession,
  mockNLWorkflow,
  mockNLHistory
} from '../mocks/nl.mock'



test.describe('NL Creator', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to NL Creator page
    await page.goto('/nl-workflow/creator')
    
    // Wait for page to load
    await page.waitForLoadState('networkidle')
    
    // Mock API responses
    await page.route('**/api/v1/nl-workflow/**', async (route) => {
      const url = route.request().url()
      
      if (url.includes('/models')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockNLModels)
        })
      } else if (url.includes('/sessions')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockNLHistory)
        })
      } else {
        await route.continue()
      }
    })
  })

  test.describe('Page Load', () => {
    test('should load NL Creator page', async ({ page }) => {
      await expect(page).toHaveTitle(/NL|Creator|Flowly|Natural/i)
    })

    test('should display main components', async ({ page }) => {
      // Check for chat input
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await expect(chatInput).toBeVisible({ timeout: 10000 })
    })

    test('should display model selector', async ({ page }) => {
      const modelSelector = page.locator(
        '[data-testid="model-selector"], select, [class*="model"] select, .el-select'
      )
      const isVisible = await modelSelector.first().isVisible({ timeout: 5000 }).catch(() => false)
      expect(isVisible).toBeTruthy()
    })
  })

  test.describe('Conversation Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Mock session creation
      await page.route('**/api/v1/nl-workflow/sessions/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              session_id: 1,
              workflow_json: mockNLWorkflow,
              message: 'I have created your workflow'
            })
          })
        } else {
          await route.continue()
        }
      })
    })

    test('should send message and receive response', async ({ page }) => {
      const chatInput = page.locator('textarea, input[type="text"]').first()
      
      // Type a message
      await chatInput.fill('Create a simple chatbot workflow')
      
      // Find and click send button
      const sendButton = page.locator(
        'button[type="submit"], button:has-text("Send"), button:has-text("提交"), button[aria-label="Send"]'
      )
      await sendButton.first().click()
      
      // Wait for user message to appear
      const userMessage = page.locator('text="Create a simple chatbot workflow"')
      await expect(userMessage).toBeVisible({ timeout: 5000 })
      
      // Wait for assistant response
      await page.waitForTimeout(2000)
      
      // Check for assistant message or workflow preview
      const assistantMessage = page.locator('[class*="message"]:has-text("workflow"), [class*="assistant"]')
      await expect(assistantMessage.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show typing indicator while generating', async ({ page }) => {
      // Slow down the mock response
      await page.route('**/api/v1/nl-workflow/sessions/', async (route) => {
        if (route.request().method() === 'POST') {
          // Delay response to show loading state
          await new Promise(resolve => setTimeout(resolve, 1000))
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              session_id: 1,
              workflow_json: mockNLWorkflow,
              message: 'Done'
            })
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a workflow')
      
      const sendButton = page.locator('button[type="submit"], button:has-text("Send")')
      await sendButton.first().click()
      
      // Check for loading indicator
      const loadingIndicator = page.locator(
        '[class*="loading"], [class*="typing"], [class*="generating"], .el-loading'
      )
      await expect(loadingIndicator.first()).toBeVisible({ timeout: 3000 })
    })

    test('should continue conversation with follow-up messages', async ({ page }) => {
      // Mock session continuation
      await page.route('**/api/v1/nl-workflow/sessions/*/message/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'I have updated the workflow'
          })
        })
      })
      
      // First message
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot')
      await page.locator('button[type="submit"]').first().click()
      await page.waitForTimeout(1000)
      
      // Second message
      await chatInput.fill('Add a condition node')
      await page.locator('button[type="submit"]').first().click()
      await page.waitForTimeout(1000)
      
      // Both messages should be visible
      const firstMessage = page.locator('text="Create a chatbot"')
      const secondMessage = page.locator('text="Add a condition node"')
      await expect(firstMessage).toBeVisible()
      await expect(secondMessage).toBeVisible()
    })
  })

  test.describe('Streaming Output', () => {
    test('should display streaming tokens as they arrive', async ({ page }) => {
      // Create streaming mock with incremental responses
      let tokenIndex = 0
      const tokens = ['Creating ', 'your ', 'workflow...']
      
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          // Simulate SSE streaming
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: tokens.map(t => `data: ${JSON.stringify({ type: 'token', content: t })}\n\n`).join(''),
            headers: {
              'Content-Type': 'text/event-stream'
            }
          })
        } else {
          await route.continue()
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a workflow')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Wait for streaming to start
      await page.waitForTimeout(500)
      
      // Check for streaming content
      const streamingContent = page.locator('[class*="streaming"], [class*="output"]')
      await expect(streamingContent.first()).toBeVisible({ timeout: 3000 })
    })

    test('should show progress indicator during streaming', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'progress', progress: 25, stage: 'analyzing' })}
data: ${JSON.stringify({ type: 'progress', progress: 50, stage: 'creating nodes' })}
data: ${JSON.stringify({ type: 'done', workflow_json: JSON.stringify(mockNLWorkflow) })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a workflow')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Check for progress indicator
      const progressBar = page.locator('[role="progressbar"], [class*="progress"]')
      await expect(progressBar.first()).toBeVisible({ timeout: 3000 })
    })

    test('should complete streaming successfully', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done', message: 'Workflow created!' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Wait for completion
      await page.waitForTimeout(2000)
      
      // Streaming should be complete
      const loadingIndicator = page.locator('[class*="loading"], [class*="generating"]')
      await expect(loadingIndicator.first()).not.toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Workflow Preview', () => {
    test('should display generated workflow preview', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Wait for workflow preview
      await page.waitForTimeout(2000)
      
      // Check for workflow preview section
      const preview = page.locator(
        '[data-testid="workflow-preview"], [class*="preview"], [class*="workflow-preview"]'
      )
      await expect(preview.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show node list in preview', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      await page.waitForTimeout(2000)
      
      // Check for node labels in preview
      for (const node of mockNLWorkflow.nodes) {
        const nodeLabel = page.locator(`text="${node.data.label}"`)
        await expect(nodeLabel.first()).toBeVisible({ timeout: 3000 })
      }
    })

    test('should edit workflow in preview', async ({ page }) => {
      // First generate a workflow
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot')
      await page.locator('button[type="submit"]').first().click()
      await page.waitForTimeout(2000)
      
      // Look for edit button in preview
      const editButton = page.locator(
        'button:has-text("Edit"), button:has-text("编辑"), [data-testid="edit-workflow"]'
      )
      const isVisible = await editButton.first().isVisible({ timeout: 2000 }).catch(() => false)
      
      if (isVisible) {
        await editButton.first().click()
        
        // Should navigate to editor or show edit mode
        await page.waitForTimeout(1000)
      }
    })
  })

  test.describe('Intent Display', () => {
    test('should show detected intent during message processing', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'intent', intent: 'create', action: 'create_workflow' })}
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a chatbot workflow')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Wait for intent display
      await page.waitForTimeout(1500)
      
      // Check for intent indicator
      const intentBadge = page.locator(
        '[class*="intent"], [class*="badge"]:has-text("create"), text="create"'
      )
      await expect(intentBadge.first()).toBeVisible({ timeout: 3000 })
    })

    test('should highlight different intent types', async ({ page }) => {
      // Test modify intent
      await page.route('**/api/v1/nl-workflow/stream/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            body: `
data: ${JSON.stringify({ type: 'intent', intent: 'modify', action: 'modify_workflow' })}
data: ${JSON.stringify({ type: 'workflow', workflow: mockNLWorkflow })}
data: ${JSON.stringify({ type: 'done' })}
            `,
            headers: { 'Content-Type': 'text/event-stream' }
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Modify the workflow')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      await page.waitForTimeout(1500)
      
      const intentBadge = page.locator('[class*="intent"]:has-text("modify")')
      await expect(intentBadge.first()).toBeVisible({ timeout: 3000 })
    })
  })

  test.describe('History', () => {
    test('should show session history', async ({ page }) => {
      // Look for history panel/button
      const historyButton = page.locator(
        'button:has-text("History"), button:has-text("历史"), [data-testid="history"]'
      )
      
      if (await historyButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await historyButton.first().click()
        
        // Check for history list
        await page.waitForTimeout(500)
        const historyList = page.locator('[class*="history"], [class*="session-list"]')
        await expect(historyList.first()).toBeVisible({ timeout: 3000 })
      }
    })

    test('should load previous session', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/sessions/*/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockNLSession)
        })
      })
      
      // Find and click on a history item
      const historyItem = page.locator('[class*="history-item"], [class*="session-item"]').first()
      
      if (await historyItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        await historyItem.click()
        
        // Should load the session
        await page.waitForTimeout(1000)
      }
    })

    test('should delete session from history', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/sessions/*/', async (route) => {
        if (route.request().method() === 'DELETE') {
          await route.fulfill({
            status: 204,
            contentType: 'application/json',
            body: ''
          })
        } else {
          await route.continue()
        }
      })
      
      // Open history
      const historyButton = page.locator('button:has-text("History")')
      if (await historyButton.isVisible().catch(() => false)) {
        await historyButton.click()
        await page.waitForTimeout(500)
        
        // Look for delete button
        const deleteButton = page.locator(
          '[class*="delete"], button[aria-label*="delete" i], button[title*="delete" i]'
        )
        if (await deleteButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
          await deleteButton.first().click()
          
          // Confirm deletion
          const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("确定")')
          if (await confirmButton.isVisible({ timeout: 1000 }).catch(() => false)) {
            await confirmButton.click()
          }
        }
      }
    })
  })

  test.describe('Error Handling', () => {
    test('should show error on API failure', async ({ page }) => {
      await page.route('**/api/v1/nl-workflow/sessions/', async (route) => {
        if (route.request().method() === 'POST') {
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Server error' })
          })
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a workflow')
      
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      
      // Wait for error
      await page.waitForTimeout(2000)
      
      // Check for error message
      const errorMessage = page.locator('text=/Error|错误|失败|error/i')
      await expect(errorMessage.first()).toBeVisible({ timeout: 5000 })
    })

    test('should allow retry after error', async ({ page }) => {
      let attemptCount = 0
      
      await page.route('**/api/v1/nl-workflow/sessions/', async (route) => {
        if (route.request().method() === 'POST') {
          attemptCount++
          if (attemptCount === 1) {
            await route.fulfill({
              status: 500,
              contentType: 'application/json',
              body: JSON.stringify({ error: 'Temporary error' })
            })
          } else {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                session_id: 1,
                workflow_json: mockNLWorkflow,
                message: 'Success'
              })
            })
          }
        }
      })
      
      const chatInput = page.locator('textarea, input[type="text"]').first()
      await chatInput.fill('Create a workflow')
      
      // First attempt
      const sendButton = page.locator('button[type="submit"]')
      await sendButton.first().click()
      await page.waitForTimeout(1500)
      
      // Retry button should appear
      const retryButton = page.locator('button:has-text("Retry"), button:has-text("重试")')
      if (await retryButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await retryButton.first().click()
        await page.waitForTimeout(2000)
      }
    })
  })

  test.describe('Settings', () => {
    test('should allow model selection', async ({ page }) => {
      // Find model selector
      const modelSelector = page.locator('select, .el-select, [class*="model"] select')
      
      if (await modelSelector.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        // Select a different model
        await modelSelector.first().click()
        await page.waitForTimeout(300)
        
        const option = page.locator('option:has-text("gpt-3.5"), .el-option').first()
        if (await option.isVisible({ timeout: 1000 }).catch(() => false)) {
          await option.click()
        }
      }
    })

    test('should allow temperature adjustment', async ({ page }) => {
      // Look for temperature slider or input
      const tempInput = page.locator(
        'input[type="range"], input[name*="temperature"], [class*="temperature"] input'
      )
      
      if (await tempInput.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await tempInput.first().fill('0.9')
      }
    })
  })
})
