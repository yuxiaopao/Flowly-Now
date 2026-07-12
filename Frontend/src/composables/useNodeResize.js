/**
 * Lightweight drag-to-resize for workflow canvas nodes (ComfyUI-style).
 *
 * Vue Flow ships no bundled resizer by default in this project, so this composable
 * implements a minimal corner-handle drag that:
 *  - compensates for canvas zoom so drag speed feels 1:1 regardless of zoom level
 *  - persists the chosen size onto node data (`uiSize`) so it survives reloads
 *  - stops pointer events from bubbling into Vue Flow's node-drag handler
 */
import { ref, computed } from 'vue'
import { useVueFlow } from '@vue-flow/core'

export function useNodeResize({ id, initialWidth, initialHeight, minWidth = 220, minHeight = 120, maxWidth = 960, maxHeight = 900 }) {
  const { updateNodeData, getViewport } = useVueFlow()

  const width = ref(initialWidth?.value ?? initialWidth ?? null)
  const height = ref(initialHeight?.value ?? initialHeight ?? null)
  const isResizing = ref(false)

  const sizeStyle = computed(() => {
    const style = {}
    if (width.value) {
      style.width = `${width.value}px`
      // Override the shared `.domain-node { max-width: 280px }` base rule so the
      // dragged size actually takes effect instead of being clamped.
      style.maxWidth = 'none'
    }
    if (height.value) style.height = `${height.value}px`
    return style
  })

  let startX = 0
  let startY = 0
  let startWidth = 0
  let startHeight = 0

  function onPointerMove(event) {
    if (!isResizing.value) return
    const zoom = getViewport?.()?.zoom || 1
    const dx = (event.clientX - startX) / zoom
    const dy = (event.clientY - startY) / zoom
    width.value = Math.min(maxWidth, Math.max(minWidth, Math.round(startWidth + dx)))
    height.value = Math.min(maxHeight, Math.max(minHeight, Math.round(startHeight + dy)))
  }

  function onPointerUp() {
    if (!isResizing.value) return
    isResizing.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    if (id) {
      updateNodeData(id, { uiSize: { width: width.value, height: height.value } })
    }
  }

  function startResize(event, currentWidth, currentHeight) {
    event.preventDefault()
    event.stopPropagation()
    isResizing.value = true
    startX = event.clientX
    startY = event.clientY
    startWidth = width.value || currentWidth || minWidth
    startHeight = height.value || currentHeight || minHeight
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function resetSize() {
    width.value = null
    height.value = null
    if (id) {
      updateNodeData(id, { uiSize: null })
    }
  }

  return {
    width,
    height,
    sizeStyle,
    isResizing,
    startResize,
    resetSize,
  }
}
