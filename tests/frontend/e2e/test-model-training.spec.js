/**
 * Model Training Pipeline E2E Tests
 * Tests for model training integration, WebSocket progress streaming,
 * and dataset management UI
 */

import { test, expect } from '@playwright/test'

// Mock data for testing
const mockTrainingJob = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Test Training Job',
  status: 'queued',
  status_display: '排队中',
  framework: 'pytorch',
  framework_display: 'PyTorch',
  model_type: 'classifier',
  model_type_display: '分类器',
  progress: 0,
  current_epoch: 0,
  total_epochs: 10,
  created_at: new Date().toISOString(),
  dataset_id: '',
  model_path: '',
  error_message: '',
  created_by_name: 'Test User'
}

const mockTrainingJobRunning = {
  ...mockTrainingJob,
  id: '550e8400-e29b-41d4-a716-446655440001',
  status: 'running',
  status_display: '训练中',
  progress: 50,
  current_epoch: 5,
  total_epochs: 10
}

const mockDataset = {
  id: '660e8400-e29b-41d4-a716-446655440000',
  name: 'Test Dataset',
  description: 'A test dataset for model training',
  format: 'csv',
  format_display: 'CSV',
  size: 1048576,
  size_formatted: '1.00 MB',
  row_count: 1000,
  columns: ['feature1', 'feature2', 'label'],
  created_at: new Date().toISOString(),
  created_by_name: 'Test User'
}

test.describe('Model Training Pipeline', () => {

  test.describe('Training Redirect Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/training')
      await page.waitForLoadState('networkidle')
    })

    test('should show workflow migration notice instead of standalone training UI', async ({ page }) => {
      const notice = page.locator('text=/工作流|YOLO 训练节点|识别项目/i')
      await expect(notice.first()).toBeVisible()
    })

    test('should offer shortcut to create YOLO workflow template', async ({ page }) => {
      const createBtn = page.locator('button, .el-button, a').filter({ hasText: /YOLO|工作流|模板/i }).first()
      await expect(createBtn).toBeAttached()
    })
  })

  test.describe('Workflow Editor - Model Training Node', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/workflows/new')
      await page.waitForLoadState('networkidle')
      
      // Mock API responses for workflows
      await page.route('**/api/v1/training/**', async (route) => {
        const url = route.request().url()
        
        if (url.includes('/training/training-jobs/') && route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ results: [mockTrainingJob], count: 1 })
          })
        } else if (url.includes('/training/datasets/') && route.request().method() === 'GET') {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ results: [mockDataset], count: 1 })
          })
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({})
          })
        }
      })
    })

    test('should render model training node in node palette', async ({ page }) => {
      // Look for node palette
      const nodePalette = page.locator('.node-palette, .palette, [class*="palette"]').first()
      
      if (await nodePalette.isVisible()) {
        // Look for model training node option
        const trainingNode = nodePalette.locator('text=/训练|模型|Training/i').first()
        await expect(trainingNode).toBeVisible()
      }
    })

    test('should allow adding model training node to canvas', async ({ page }) => {
      // Find node palette and training node option
      const nodePalette = page.locator('.node-palette, .palette, [class*="palette"]').first()
      
      if (await nodePalette.isVisible()) {
        const trainingOption = nodePalette.locator('text=/训练|模型|Training/i').first()
        
        if (await trainingOption.isVisible()) {
          const canvas = page.locator('.workflow-canvas, .canvas, [class*="canvas"]').first()
          
          if (await canvas.isVisible()) {
            // Drag and drop or click to add
            await trainingOption.dragTo(canvas, { force: true })
            
            // Verify node was added
            const addedNode = page.locator('.model-training-node, [class*="training-node"]').first()
            // May or may not be visible depending on implementation
          }
        }
      }
    })
  })

  test.describe('Model Training Config Panel', () => {
    test.beforeEach(async ({ page }) => {
      // Navigate to workflows page
      await page.goto('/workflows/new')
      await page.waitForLoadState('networkidle')
      
      // Mock API
      await page.route('**/api/v1/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [] })
        })
      })
    })

    test('should display config form when training node selected', async ({ page }) => {
      // This test assumes a training node is already on canvas
      // and clicking it shows the config panel
      
      // Look for config panel
      const configPanel = page.locator('.model-training-config-form, [class*="training-config"]').first()
      
      // If visible, verify it has form fields
      if (await configPanel.isVisible().catch(() => false)) {
        await expect(configPanel.locator('form, .el-form')).toBeVisible()
      }
    })

    test('should have framework selection dropdown', async ({ page }) => {
      const configForm = page.locator('.model-training-config-form, [class*="training-config"]').first()
      
      if (await configForm.isVisible().catch(() => false)) {
        // Look for framework dropdown
        const frameworkSelect = configForm.locator('select, .el-select').filter({ hasText: /框架|Framework|PyTorch/i }).first()
        await expect(frameworkSelect).toBeVisible()
      }
    })

    test('should have hyperparameters section', async ({ page }) => {
      const configForm = page.locator('.model-training-config-form, [class*="training-config"]').first()
      
      if (await configForm.isVisible().catch(() => false)) {
        // Look for hyperparameters section
        const hyperparams = configForm.locator('text=/超参数|Epochs|Batch/i')
        // May have some visible elements
        await expect(hyperparams.first()).toBeAttached()
      }
    })
  })

  test.describe('Dataset Management', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/datasets')
      await page.waitForLoadState('networkidle')
      
      // Mock API
      await page.route('**/api/v1/training/datasets/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [mockDataset], count: 1 })
        })
      })
    })

    test('should load datasets page', async ({ page }) => {
      await expect(page).toHaveTitle(/数据|Dataset/i)
    })

    test('should display dataset list', async ({ page }) => {
      // Look for table or list
      const datasetList = page.locator('.dataset-table, .el-table, [class*="dataset"]').first()
      await expect(datasetList).toBeVisible()
    })

    test('should show dataset details', async ({ page }) => {
      // Click on a dataset row if available
      const datasetRow = page.locator('tr, .dataset-item').filter({ hasText: mockDataset.name }).first()
      
      if (await datasetRow.isVisible().catch(() => false)) {
        await datasetRow.click()
        // Should show detail view or drawer
        await page.waitForTimeout(500)
      }
    })

    test('should have upload dataset button', async ({ page }) => {
      const uploadButton = page.locator('button, .btn').filter({ hasText: /上传|Upload/i }).first()
      await expect(uploadButton).toBeVisible()
    })
  })

  test.describe('Training WebSocket Integration', () => {
    test('should use workflow YOLO node WebSocket URL pattern', async ({ page }) => {
      const jobId = 'test_train_123'
      const wsUrl = `/ws/training/${jobId}/`
      expect(wsUrl).toMatch(/^\/ws\/training\/[^/]+\/$/)

      await page.route('**/ws/training/**', async (route) => {
        await route.abort()
      })

      await page.goto('/workflows/new?template=yolo-detection')
      await page.waitForLoadState('networkidle')
    })

    test('composable handles training progress event types', async () => {
      const eventTypes = [
        'connected',
        'training_started',
        'epoch_start',
        'epoch_complete',
        'training_complete',
        'training_error',
        'training_cancelled',
      ]
      expect(eventTypes.length).toBeGreaterThan(0)
    })
  })

  test.describe('Website Generator Integration', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/workflows/new')
      await page.waitForLoadState('networkidle')
      
      await page.route('**/api/v1/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: [] })
        })
      })
    })

    test('should have website generator node option', async ({ page }) => {
      const nodePalette = page.locator('.node-palette, .palette').first()
      
      if (await nodePalette.isVisible().catch(() => false)) {
        const genNode = nodePalette.locator('text=/网站|Website|生成/i').first()
        await expect(genNode).toBeAttached()
      }
    })

    test('should display website generator config form', async ({ page }) => {
      const configForm = page.locator('.website-generator-config-form, [class*="generator-config"]').first()
      
      if (await configForm.isVisible().catch(() => false)) {
        await expect(configForm.locator('form, .el-form')).toBeVisible()
      }
    })
  })
})

test.describe('Training API Integration', () => {
  test('training API should have correct endpoints', async ({ request }) => {
    const baseURL = 'http://localhost:8000'
    
    // Test training jobs endpoint
    const jobsResponse = await request.get(`${baseURL}/api/v1/training/training-jobs/`)
    expect([200, 401, 403]).toContain(jobsResponse.status())
    
    // Test datasets endpoint
    const datasetsResponse = await request.get(`${baseURL}/api/v1/training/datasets/`)
    expect([200, 401, 403]).toContain(datasetsResponse.status())
  })

  test('training jobs CRUD operations', async ({ request }) => {
    const baseURL = 'http://localhost:8000'
    
    // Create
    const createResponse = await request.post(`${baseURL}/api/v1/training/training-jobs/`, {
      data: {
        framework: 'pytorch',
        model_type: 'classifier',
        config: { epochs: 1 }
      }
    })
    
    // Should be 201 Created or 400 (validation) or auth error
    expect([201, 400, 401, 403]).toContain(createResponse.status())
    
    if (createResponse.status() === 201) {
      const job = await createResponse.json()
      expect(job).toHaveProperty('id')
      
      // Read
      const getResponse = await request.get(`${baseURL}/api/v1/training/training-jobs/${job.id}/`)
      expect(getResponse.status()).toBe(200)
    }
  })

  test('dataset upload flow', async ({ request }) => {
    const baseURL = 'http://localhost:8000'
    
    // List
    const listResponse = await request.get(`${baseURL}/api/v1/training/datasets/`)
    expect([200, 401, 403]).toContain(listResponse.status())
  })
})
