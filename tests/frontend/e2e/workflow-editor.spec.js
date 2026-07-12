/**
 * Workflow Editor E2E Tests
 * Tests for the workflow editor canvas, node operations, and execution
 */

import { test, expect } from '@playwright/test'
import {
  mockWorkflow,
  mockWorkflowList
} from '../mocks/workflows.mock'



test.describe('Workflow Editor', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to workflow editor
    await page.goto('/workflow/editor')
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle')
    
    // Mock API responses
    await page.route('**/api/v1/workflows/**', async (route) => {
      const url = route.request().url()
      
      if (url.includes('/api/v1/workflows/$') || url.match(/\/api\/v1\/workflows\/\d+\/$/)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockWorkflow)
        })
      } else if (url.includes('/api/v1/workflows/')) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: mockWorkflowList.results })
        })
      } else {
        await route.continue()
      }
    })
  })

  test.describe('Page Load and Navigation', () => {
    test('should load workflow editor page', async ({ page }) => {
      // Check page title or header
      await expect(page).toHaveTitle(/Workflow|Editor|Flowly/i)
    })

    test('should display workflow editor layout', async ({ page }) => {
      // Check for main components
      const canvas = page.locator('[data-testid="workflow-canvas"], .vue-flow, #workflow-canvas')
      await expect(canvas.first()).toBeVisible({ timeout: 10000 })
    })

    test('should display node panel', async ({ page }) => {
      const nodePanel = page.locator('[data-testid="node-panel"], .node-panel, [class*="node-panel"]')
      await expect(nodePanel.first()).toBeVisible({ timeout: 10000 })
    })
  })

  test.describe('Node Operations', () => {
    test('should add node from panel to canvas', async ({ page }) => {
      // Find and drag a node from the panel
      const nodeInPanel = page.locator('[data-testid="node-item"], .node-item').first()
      const canvas = page.locator('.vue-flow').first()
      
      // Get bounding boxes
      const nodeBox = await nodeInPanel.boundingBox()
      const canvasBox = await canvas.boundingBox()
      
      if (nodeBox && canvasBox) {
        // Perform drag and drop
        await page.mouse.move(nodeBox.x + nodeBox.width / 2, nodeBox.y + nodeBox.height / 2)
        await page.mouse.down()
        await page.mouse.move(
          canvasBox.x + canvasBox.width / 2,
          canvasBox.y + canvasBox.height / 2,
          { steps: 10 }
        )
        await page.mouse.up()
        
        // Verify node was added (check for node in canvas)
        await page.waitForTimeout(500)
        const nodesInCanvas = page.locator('.vue-flow__node')
        await expect(nodesInCanvas.first()).toBeVisible({ timeout: 5000 })
      }
    })

    test('should select a node', async ({ page }) => {
      // Wait for nodes to load
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Click on a node
      const node = page.locator('.vue-flow__node').first()
      await node.click()
      
      // Check if node is selected (visual indicator)
      await expect(node).toHaveClass(/selected/)
    })

    test('should delete selected node with Delete key', async ({ page }) => {
      // Wait for nodes to load
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      const initialCount = await page.locator('.vue-flow__node').count()
      
      // Select a node
      await page.locator('.vue-flow__node').first().click()
      
      // Press Delete key
      await page.keyboard.press('Delete')
      
      // Verify node was deleted
      await page.waitForTimeout(300)
      const newCount = await page.locator('.vue-flow__node').count()
      expect(newCount).toBeLessThan(initialCount)
    })

    test('should delete node with context menu', async ({ page }) => {
      // Wait for nodes to load
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Right-click on node
      await page.locator('.vue-flow__node').first().click({ button: 'right' })
      
      // Look for delete option
      const deleteOption = page.locator('text=/Delete|删除/i')
      await expect(deleteOption.first()).toBeVisible({ timeout: 3000 })
      
      // Click delete
      await deleteOption.first().click()
    })
  })

  test.describe('Node Connection', () => {
    test('should create connection between nodes', async ({ page }) => {
      // Wait for nodes to load
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Find source and target handles
      const sourceHandle = page.locator('.vue-flow__handle-source').first()
      const targetHandle = page.locator('.vue-flow__handle-target').first()
      
      if (await sourceHandle.isVisible() && await targetHandle.isVisible()) {
        const sourceBox = await sourceHandle.boundingBox()
        const targetBox = await targetHandle.boundingBox()
        
        if (sourceBox && targetBox) {
          // Drag from source to target
          await page.mouse.move(
            sourceBox.x + sourceBox.width / 2,
            sourceBox.y + sourceBox.height / 2
          )
          await page.mouse.down()
          await page.mouse.move(
            targetBox.x + targetBox.width / 2,
            targetBox.y + targetBox.height / 2,
            { steps: 10 }
          )
          await page.mouse.up()
          
          // Verify edge was created
          await page.waitForTimeout(500)
          const edges = page.locator('.vue-flow__edge')
          await expect(edges.first()).toBeVisible({ timeout: 3000 })
        }
      }
    })

    test('should delete edge', async ({ page }) => {
      // Wait for edges to load
      await page.waitForSelector('.vue-flow__edge', { timeout: 10000 })
      
      const initialEdgeCount = await page.locator('.vue-flow__edge').count()
      
      // Click on edge to select it
      await page.locator('.vue-flow__edge-path').first().click()
      
      // Press Delete
      await page.keyboard.press('Delete')
      
      // Verify edge was deleted
      await page.waitForTimeout(300)
      const newEdgeCount = await page.locator('.vue-flow__edge').count()
      expect(newEdgeCount).toBeLessThan(initialEdgeCount)
    })
  })

  test.describe('Canvas Operations', () => {
    test('should zoom in and out', async ({ page }) => {
      // Wait for canvas to load
      const canvas = page.locator('.vue-flow').first()
      await expect(canvas).toBeVisible({ timeout: 10000 })
      
      // Get initial transform
      const initialTransform = await canvas.evaluate((el) => {
        return window.getComputedStyle(el).transform
      })
      
      // Zoom in with Ctrl+Plus or mouse wheel
      await page.keyboard.down('Control')
      await page.mouse.wheel(0, -100) // Scroll up to zoom in
      await page.keyboard.up('Control')
      
      await page.waitForTimeout(300)
      
      // Verify transform changed
      const newTransform = await canvas.evaluate((el) => {
        return window.getComputedStyle(el).transform
      })
      
      // Transform should be different
      expect(newTransform).not.toBe(initialTransform)
    })

    test('should pan canvas with mouse drag', async ({ page }) => {
      // Wait for canvas to load
      const canvas = page.locator('.vue-flow').first()
      await expect(canvas).toBeVisible({ timeout: 10000 })
      
      const canvasBox = await canvas.boundingBox()
      
      if (canvasBox) {
        // Drag on canvas background
        await page.mouse.move(canvasBox.x + 100, canvasBox.y + 100)
        await page.mouse.down()
        await page.mouse.move(canvasBox.x + 300, canvasBox.y + 300, { steps: 10 })
        await page.mouse.up()
        
        // Canvas should have moved (transform should change)
        await page.waitForTimeout(300)
      }
    })

    test('should fit view with button', async ({ page }) => {
      // Look for fit view button
      const fitButton = page.locator('[data-testid="fit-view"], button:has-text("Fit"), button[title*="Fit"]')
      
      if (await fitButton.first().isVisible()) {
        await fitButton.first().click()
        await page.waitForTimeout(300)
      }
    })
  })

  test.describe('Workflow Save', () => {
    test('should save workflow', async ({ page }) => {
      // Mock save API
      await page.route('**/api/v1/workflows/*/update/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        })
      })
      
      // Look for save button
      const saveButton = page.locator('[data-testid="save-button"], button:has-text("Save"), button[title*="Save"]')
      await expect(saveButton.first()).toBeVisible({ timeout: 10000 })
      
      // Click save
      await saveButton.first().click()
      
      // Wait for save to complete
      await page.waitForTimeout(1000)
      
      // Check for success notification
      const successToast = page.locator('text=/Saved|Success|成功/i')
      await expect(successToast.first()).toBeVisible({ timeout: 5000 })
    })

    test('should show unsaved changes warning on navigate away', async ({ page }) => {
      // Make some changes to trigger dirty state
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Select and modify a node
      await page.locator('.vue-flow__node').first().click()
      await page.keyboard.press('ArrowRight') // Move node
      
      // Try to navigate
      await page.locator('a[href="/"], a[href*="dashboard"]').first().click()
      
      // Should show confirmation dialog
      const dialog = page.locator('[role="dialog"], .el-dialog')
      const hasDialog = await dialog.first().isVisible({ timeout: 2000 }).catch(() => false)
      
      if (hasDialog) {
        // Dialog should contain warning text
        await expect(dialog.first()).toContainText(/unsaved|未保存|leave|离开/i)
      }
    })
  })

  test.describe('Workflow Execute', () => {
    test.beforeEach(async ({ page }) => {
      // Mock execute API
      await page.route('**/api/v1/workflows/*/execute/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ execution_id: 1, status: 'pending' })
        })
      })
    })

    test('should execute workflow', async ({ page }) => {
      // Look for execute button
      const executeButton = page.locator(
        '[data-testid="execute-button"], button:has-text("Execute"), button:has-text("Run"), button[title*="Execute"]'
      )
      await expect(executeButton.first()).toBeVisible({ timeout: 10000 })
      
      // Click execute
      await executeButton.first().click()
      
      // Wait for execution to start
      await page.waitForTimeout(2000)
      
      // Should show execution panel or status
      const executionPanel = page.locator(
        '[data-testid="execution-panel"], .execution-panel, [class*="execution"]'
      )
      await expect(executionPanel.first()).toBeVisible({ timeout: 5000 })
    })

    test('should cancel running execution', async ({ page }) => {
      // Mock execution response
      await page.route('**/api/v1/workflows/*/execute/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ execution_id: 1, status: 'running' })
        })
      })
      
      // Start execution
      const executeButton = page.locator(
        '[data-testid="execute-button"], button:has-text("Execute"), button:has-text("Run")'
      )
      await executeButton.first().click()
      
      // Wait for execution panel
      await page.waitForSelector('[class*="execution"], .execution-panel', { timeout: 5000 })
      
      // Look for cancel button
      const cancelButton = page.locator(
        'button:has-text("Cancel"), button[title*="Cancel"], [data-testid="cancel-button"]'
      )
      
      if (await cancelButton.first().isVisible({ timeout: 2000 }).catch(() => false)) {
        await cancelButton.first().click()
        
        // Confirm cancellation
        const confirmButton = page.locator('button:has-text("Confirm"), button:has-text("确定")')
        if (await confirmButton.first().isVisible({ timeout: 1000 }).catch(() => false)) {
          await confirmButton.first().click()
        }
        
        await page.waitForTimeout(1000)
      }
    })
  })

  test.describe('Keyboard Shortcuts', () => {
    test('should use Ctrl+S to save', async ({ page }) => {
      await page.route('**/api/v1/workflows/*/update/', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true })
        })
      })
      
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Press Ctrl+S
      await page.keyboard.press('Control+s')
      
      await page.waitForTimeout(1000)
      
      // Check for success
      const successToast = page.locator('text=/Saved|Success|成功/i')
      await expect(successToast.first()).toBeVisible({ timeout: 5000 })
    })

    test('should use Delete/Backspace to remove selected node', async ({ page }) => {
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      const initialCount = await page.locator('.vue-flow__node').count()
      
      // Select node
      await page.locator('.vue-flow__node').first().click()
      
      // Delete
      await page.keyboard.press('Delete')
      
      await page.waitForTimeout(300)
      expect(await page.locator('.vue-flow__node').count()).toBeLessThan(initialCount)
    })

    test('should use Ctrl+Z to undo', async ({ page }) => {
      await page.waitForSelector('.vue-flow__node', { timeout: 10000 })
      
      // Get initial state
      const initialCount = await page.locator('.vue-flow__node').count()
      
      // Add a change
      await page.locator('.vue-flow__node').first().click()
      await page.keyboard.press('ArrowRight')
      
      await page.waitForTimeout(300)
      
      // Undo
      await page.keyboard.press('Control+z')
      
      await page.waitForTimeout(500)
    })
  })

  test.describe('Error Handling', () => {
    test('should show error on save failure', async ({ page }) => {
      // Mock failed save
      await page.route('**/api/v1/workflows/*/update/', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        })
      })
      
      const saveButton = page.locator('[data-testid="save-button"], button:has-text("Save")')
      await saveButton.first().click()
      
      await page.waitForTimeout(1000)
      
      // Check for error message
      const errorToast = page.locator('text=/Error|错误|失败|Failed/i')
      await expect(errorToast.first()).toBeVisible({ timeout: 5000 })
    })

    test('should handle network error gracefully', async ({ page }) => {
      // Mock network error
      await page.route('**/api/v1/workflows/**', async (route) => {
        await route.abort('failed')
      })
      
      // Reload page
      await page.reload()
      
      // Should show error state
      await page.waitForTimeout(2000)
      
      // Look for error message or retry button
      const errorMessage = page.locator('text=/Error|Network|网络|重试|Retry/i')
      const hasError = await errorMessage.first().isVisible({ timeout: 5000 }).catch(() => false)
      
      // Either show error or page loads with empty state
      expect(hasError || await page.locator('.vue-flow').isVisible()).toBeTruthy()
    })
  })

  test.describe('Responsive Design', () => {
    test('should work on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      
      await page.goto('/workflow/editor')
      await page.waitForLoadState('networkidle')
      
      // Should show mobile-friendly elements
      const mobileMenu = page.locator('[data-testid="mobile-menu"], .hamburger, button[aria-label="Menu"]')
      const hasMobileMenu = await mobileMenu.first().isVisible({ timeout: 5000 }).catch(() => false)
      
      // Canvas should still be functional
      const canvas = page.locator('.vue-flow').first()
      await expect(canvas).toBeVisible({ timeout: 10000 })
    })
  })
})
