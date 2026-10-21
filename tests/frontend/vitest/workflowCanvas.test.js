import { describe, expect, it } from 'vitest'
import {
  WORKFLOW_EXECUTION_PANEL,
  clampExecutionPanelHeight,
  readExecutionPanelHeight,
  writeExecutionPanelHeight,
} from '@/config/workflowCanvas'

describe('execution panel height', () => {
  it('clamps below the minimum to minHeight', () => {
    expect(clampExecutionPanelHeight(80, 900)).toBe(WORKFLOW_EXECUTION_PANEL.minHeight)
  })

  it('clamps above the viewport budget', () => {
    expect(clampExecutionPanelHeight(2000, 900)).toBe(900 - WORKFLOW_EXECUTION_PANEL.maxViewportOffset)
  })

  it('reads stored height and writes the clamped value', () => {
    const storage = {
      data: {},
      getItem(key) {
        return this.data[key] ?? null
      },
      setItem(key, value) {
        this.data[key] = String(value)
      },
    }

    expect(readExecutionPanelHeight(storage, 1080)).toBe(WORKFLOW_EXECUTION_PANEL.defaultHeight)

    const saved = writeExecutionPanelHeight(640, storage, 1080)
    expect(saved).toBe(640)
    expect(storage.data[WORKFLOW_EXECUTION_PANEL.storageKey]).toBe('640')
    expect(readExecutionPanelHeight(storage, 1080)).toBe(640)
  })
})
