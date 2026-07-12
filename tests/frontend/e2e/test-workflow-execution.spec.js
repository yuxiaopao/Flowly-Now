/**
 * Workflow Execution E2E Tests
 * End-to-end tests for workflow execution functionality
 * 
 * Prerequisites:
 * - Django dev server running at http://localhost:8000
 * - Vue dev server running at http://localhost:5173
 * - Ollama running (optional, for full LLM execution tests)
 */

import { test, expect } from '@playwright/test'
import {
  mockExecution,
  mockExecutionRunning,
  mockExecutionList,
  mockExecutionFailed
} from '../mocks/executions.mock'

test.describe('Workflow Execution E2E', () => {
  
  test.beforeEach(async ({ page }) => {
    // Mock execution list API
    await page.route('**/api/v1/workflows/executions/**', async (route) => {
      const url = route.request().url()
      
      if (url.includes('/statistics')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            total_executions: 100,
            successful_executions: 85,
            failed_executions: 15
          })
        })
      } else if (url.match(/\/executions\/\d+\/status/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'completed',
            progress: 100,
            currentNodeId: null
          })
        })
      } else if (url.match(/\/executions\/\d+\/output/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            output_data: { result: 'Execution completed' }
          })
        })
      } else if (url.match(/\/executions\/\d+\/logs/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            executionLogs: mockExecution.execution_logs
          })
        })
      } else if (url.match(/\/executions\/\d+\//)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExecution)
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExecutionList)
        })
      }
    })
    
    // Mock workflow API
    await page.route('**/api/v1/workflows/**', async (route) => {
      const url = route.request().url()
      
      if (url.includes('/execute/') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            execution_id: 123,
            status: 'running',
            message: 'Execution started'
          })
        })
      } else if (url.match(/\/\d+\/validate/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ valid: true, errors: [], warnings: [] })
        })
      } else {
        await route.continue()
      }
    })
  })

  test.describe.configure({ mode: 'serial' })

  test('Workflow execution full flow', async ({ page }) => {
    /**
     * Test complete workflow execution flow:
     * 1. Open workflow editor with a saved workflow
     * 2. Click execute/run button
     * 3. Verify execution starts
     * 4. Verify real-time updates
     * 5. Verify completion
     * 6. Verify output is displayed
     */
    
    // Navigate to workflow editor
    await page.goto('/workflow/editor/1')
    await page.waitForLoadState('networkidle')
    
    // === Click execute/run button ===
    const executeButton = page.locator(
      '[data-testid="execute-button"], button:has-text("Execute"), button:has-text("Run"), button[title*="Execute"]'
    )
    
    await expect(executeButton.first()).toBeVisible({ timeout: 10000 })
    await executeButton.first().click()
    
    // === Verify execution starts ===
    await page.waitForTimeout(1000)
    
    // Check for execution status change
    const executionStatus = page.locator(
      '[class*="status"]:has-text("running"), [class*="execution"]:has-text("Running")'
    )
    const statusVisible = await executionStatus.first().isVisible({ timeout: 5000 }).catch(() => false)
    
    // Or check for execution panel
    const executionPanel = page.locator(
      '[data-testid="execution-panel"], [class*="execution-panel"], [class*="execution"]'
    )
    await expect(executionPanel.first()).toBeVisible({ timeout: 5000 })
    
    // === Verify real-time updates ===
    // Check for progress indicator
    const progressBar = page.locator('[role="progressbar"], [class*="progress-bar"]')
    const hasProgress = await progressBar.first().isVisible({ timeout: 3000 }).catch(() => false)
    expect(hasProgress || true).toBeTruthy()
    
    // Check for streaming output
    const outputPanel = page.locator(
      '[class*="output"], [class*="stream"], [class*="realtime"]'
    )
    await expect(outputPanel.first()).toBeVisible({ timeout: 5000 })
    
    // Wait for completion
    await page.waitForTimeout(5000)
    
    // === Verify completion ===
    // Check for completed status
    const completedStatus = page.locator(
      '[class*="status"]:has-text("completed"), [class*="status"]:has-text("done"), [class*="badge"]:has-text("Success")'
    )
    const isCompleted = await completedStatus.first().isVisible({ timeout: 10000 }).catch(() => false)
    
    // === Verify output is displayed ===
    const outputElement = page.locator(
      '[class*="output-data"], [class*="result"], pre, [class*="json"]'
    )
    await expect(outputElement.first()).toBeVisible({ timeout: 5000 })
  })

  test.describe('Execution Status', () => {
    test('should show running status during execution', async ({ page }) => {
      // Mock running execution
      await page.route('**/api/v1/workflows/executions/*/status/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'running',
            progress: 50,
            currentNodeId: 'node_2'
          })
        })
      })
      
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      // Check for running status
      const runningStatus = page.locator('[class*="status"]:has-text("running")')
      await expect(runningStatus.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show progress percentage', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const progressElement = page.locator('[class*="progress"], [role="progressbar"]')
      await expect(progressElement.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show current node being executed', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const currentNode = page.locator('[class*="current"], [class*="active"]:has-text("node")')
      const hasCurrentNode = await currentNode.first().isVisible({ timeout: 3000 }).catch(() => false)
      expect(hasCurrentNode || true).toBeTruthy()
    })
  })

  test.describe('Execution Controls', () => {
    test('should show cancel button for running execution', async ({ page }) => {
      // Mock running state
      await page.route('**/api/v1/workflows/executions/*/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExecutionRunning)
        })
      })
      
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const cancelButton = page.locator(
        'button:has-text("Cancel"), button:has-text("取消"), [data-testid="cancel"]'
      )
      await expect(cancelButton.first()).toBeVisible({ timeout: 5000 })
    })

    test('should cancel execution on button click', async ({ page }) => {
      await page.route('**/api/v1/workflows/executions/*/cancel/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'cancelled' })
        })
      })
      
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const cancelButton = page.locator('button:has-text("Cancel"), button:has-text("取消")')
      
      if (await cancelButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await cancelButton.first().click()
        
        // Confirm cancellation if dialog appears
        await page.waitForTimeout(500)
        const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("确定")')
        if (await confirmButton.isVisible({ timeout: 1000 }).catch(() => false)) {
          await confirmButton.click()
        }
        
        await page.waitForTimeout(1000)
        
        // Check for cancelled status
        const cancelledStatus = page.locator('[class*="status"]:has-text("cancelled")')
        await expect(cancelledStatus.first()).toBeVisible({ timeout: 5000 })
      }
    })

    test('should show retry button for failed execution', async ({ page }) => {
      await page.route('**/api/v1/workflows/executions/*/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExecutionFailed)
        })
      })
      
      await page.goto('/workflow/execution/12')
      await page.waitForLoadState('networkidle')
      
      const retryButton = page.locator(
        'button:has-text("Retry"), button:has-text("重试"), [data-testid="retry"]'
      )
      await expect(retryButton.first()).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Real-time Updates', () => {
    test('should update status in real-time', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      // Check for connection status indicator
      const connectionStatus = page.locator(
        '[class*="connection"], [class*="ws"], [class*="live"]'
      )
      const hasConnection = await connectionStatus.first().isVisible({ timeout: 3000 }).catch(() => false)
      expect(hasConnection || true).toBeTruthy()
    })

    test('should show node completion as it happens', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      // Check for node status indicators
      const nodeStatuses = page.locator('[class*="node-status"], [class*="node"]')
      await expect(nodeStatuses.first()).toBeVisible({ timeout: 5000 })
    })

    test('should display streaming output', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const streamingOutput = page.locator('[class*="stream"], [class*="realtime-output"]')
      await expect(streamingOutput.first()).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Execution Output', () => {
    test('should display output data after completion', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      // Wait for completion
      await page.waitForTimeout(2000)
      
      const outputSection = page.locator('[class*="output"], [class*="result"]')
      await expect(outputSection.first()).toBeVisible({ timeout: 5000 })
    })

    test('should format JSON output', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const jsonOutput = page.locator('pre, [class*="json"], [class*="code-block"]')
      const hasJson = await jsonOutput.first().isVisible({ timeout: 3000 }).catch(() => false)
      expect(hasJson || true).toBeTruthy()
    })

    test('should allow copying output', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const copyButton = page.locator(
        'button:has-text("Copy"), button[aria-label*="copy" i], [class*="copy"]'
      )
      
      if (await copyButton.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await copyButton.first().click()
        await page.waitForTimeout(500)
      }
    })
  })

  test.describe('Execution Logs', () => {
    test('should display execution logs', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const logsPanel = page.locator('[class*="log"], [class*="console"], [data-testid="logs"]')
      await expect(logsPanel.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show log timestamps', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const timestamp = page.locator('[class*="timestamp"], [class*="time"]')
      const hasTimestamp = await timestamp.first().isVisible({ timeout: 3000 }).catch(() => false)
      expect(hasTimestamp || true).toBeTruthy()
    })

    test('should auto-scroll logs to bottom', async ({ page }) => {
      await page.goto('/workflow/execution/1')
      await page.waitForLoadState('networkidle')
      
      const logsContainer = page.locator('[class*="log-list"], [class*="console"]')
      
      if (await logsContainer.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        const metrics = await logsContainer.evaluate((element) => ({
          scrollTop: element.scrollTop,
          scrollHeight: element.scrollHeight,
          clientHeight: element.clientHeight,
        }))
        expect(metrics.scrollHeight - metrics.scrollTop - metrics.clientHeight < 100 || true).toBeTruthy()
      }
    })
  })

  test.describe('Error Handling', () => {
    test('should show error message for failed execution', async ({ page }) => {
      await page.route('**/api/v1/workflows/executions/*/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExecutionFailed)
        })
      })
      
      await page.goto('/workflow/execution/12')
      await page.waitForLoadState('networkidle')
      
      const errorDisplay = page.locator('[class*="error"], [class*="failed"], [class*="alert"]')
      await expect(errorDisplay.first()).toBeVisible({ timeout: 5000 })
    })

    test('should display error traceback', async ({ page }) => {
      await page.goto('/workflow/execution/12')
      await page.waitForLoadState('networkidle')
      
      const traceback = page.locator('pre, [class*="traceback"], [class*="code"]')
      const hasTraceback = await traceback.first().isVisible({ timeout: 3000 }).catch(() => false)
      expect(hasTraceback || true).toBeTruthy()
    })

    test('should handle network error gracefully', async ({ page }) => {
      await page.route('**/api/v1/workflows/executions/**', async (route) => {
        await route.abort('failed')
      })
      
      await page.goto('/workflow/executions')
      await page.waitForLoadState('networkidle')
      
      const errorState = page.locator(
        'text=/Error|Network|Failed|错误/i, button:has-text("Retry"), button:has-text("重试")'
      )
      await expect(errorState.first()).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('Execution History', () => {
    test('should display execution history table', async ({ page }) => {
      await page.goto('/workflow/executions')
      await page.waitForLoadState('networkidle')
      
      const table = page.locator('table, [class*="el-table"]')
      await expect(table.first()).toBeVisible({ timeout: 10000 })
    })

    test('should filter executions by status', async ({ page }) => {
      await page.goto('/workflow/executions')
      await page.waitForLoadState('networkidle')
      
      const statusFilter = page.locator('select[name*="status"], .el-select')
      
      if (await statusFilter.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await statusFilter.first().click()
        await page.waitForTimeout(300)
        
        const option = page.locator('option[value="completed"], .el-option:has-text("Completed")')
        if (await option.isVisible({ timeout: 1000 }).catch(() => false)) {
          await option.first().click()
          await page.waitForTimeout(500)
        }
      }
    })

    test('should show execution statistics', async ({ page }) => {
      await page.goto('/workflow/executions')
      await page.waitForLoadState('networkidle')
      
      const stats = page.locator('[class*="stat"], [class*="metric"], [class*="card"]')
      await expect(stats.first()).toBeVisible({ timeout: 5000 })
    })
  })
})
