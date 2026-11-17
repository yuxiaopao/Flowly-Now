import { computed, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import workflowApi from '@/api/workflow'
import { useWorkflowStore } from '@/stores/workflow'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { backendWorkflowToFrontend } from '@/utils/workflowTransform'

const DOCUMENT_MESSAGES = {
  defaultName: '未命名工作流', loadError: '加载工作流失败，请重试',
  saving: '正在保存工作流，请稍后再离开',
  leave: { title: '未保存的更改', message: '您有未保存的更改，确定要离开吗？未保存的内容将丢失。', confirmText: '离开', cancelText: '取消', confirmType: 'danger' },
}
const EDITOR_ROUTE_NAMES = new Set(['WorkflowEdit', 'WorkflowCreate'])

/** Owns document identity and navigation; graph rendering and execution remain in the editor. */
export function useWorkflowDocument({ isSaving, resetDocument, loadNewDocument, applyDocument, onDocumentReady }) {
  const route = useRoute()
  const router = useRouter()
  const workflowStore = useWorkflowStore()
  const authStore = useAuthStore()
  const appStore = useAppStore()
  const workflowId = ref(route.params.id)
  const documentVersion = ref(0)
  const workflowName = ref(DOCUMENT_MESSAGES.defaultName)
  const savedName = ref(workflowName.value)
  const isDirty = ref(false)
  const isLoadingWorkflow = ref(false)
  const workflowLoadError = ref('')
  const isNewWorkflow = computed(() => workflowId.value === 'new' || !workflowId.value)
  const hasUnsavedChanges = computed(() => !isLoadingWorkflow.value && (isDirty.value || workflowName.value !== savedName.value))
  const canEditWorkflow = computed(() => {
    if (isNewWorkflow.value) return true
    const workflow = workflowStore.currentWorkflow
    if (!workflow) return true
    if (typeof workflow.canEdit === 'boolean') return workflow.canEdit
    if (authStore.user?.isSuperuser) return true
    const ownerId = workflow.owner?.id ?? workflow.ownerId
    const userId = authStore.user?.id
    return ownerId == null || userId == null || Number(ownerId) === Number(userId)
  })
  let createdNavigationId = null
  let unloadAttached = false

  function markSaved(name, dirty = false) {
    savedName.value = name
    isDirty.value = dirty
  }

  async function adoptCreatedWorkflow(id, name, dirty = false) {
    workflowId.value = id
    markSaved(name, dirty)
    createdNavigationId = String(id)
    try {
      await router.replace(`/workflows/${id}/edit`)
    } finally {
      createdNavigationId = null
    }
  }

  async function loadWorkflowDocument(targetId = route.params.id) {
    const version = ++documentVersion.value
    const previousId = workflowId.value
    workflowId.value = targetId
    isLoadingWorkflow.value = true
    workflowLoadError.value = ''
    workflowName.value = DOCUMENT_MESSAGES.defaultName
    savedName.value = workflowName.value
    isDirty.value = false
    workflowStore.currentWorkflow = null
    workflowStore.nodes = []
    workflowStore.edges = []
    try {
      resetDocument(previousId)
      if (isNewWorkflow.value) {
        loadNewDocument()
      } else {
        const response = await workflowApi.getById(targetId)
        if (version !== documentVersion.value) return
        const workflow = backendWorkflowToFrontend(response)
        workflowStore.currentWorkflow = workflow
        workflowStore.nodes = workflow.nodes || []
        workflowStore.edges = workflow.edges || []
        workflowName.value = workflow.name || DOCUMENT_MESSAGES.defaultName
        savedName.value = workflowName.value
        applyDocument(workflow)
        await nextTick()
        if (version !== documentVersion.value) return
        await onDocumentReady?.()
      }
    } catch (error) {
      if (version !== documentVersion.value) return
      workflowLoadError.value = DOCUMENT_MESSAGES.loadError
      appStore.error(DOCUMENT_MESSAGES.loadError)
    } finally {
      if (version === documentVersion.value) isLoadingWorkflow.value = false
    }
  }

  function protectUnsavedWorkflow(event) {
    if (!hasUnsavedChanges.value && !isSaving.value) return
    event.preventDefault()
    event.returnValue = ''
  }

  async function confirmDocumentLeave(to) {
    if (createdNavigationId && String(to.params.id) === createdNavigationId) return true
    if (isSaving.value) {
      appStore.warning(DOCUMENT_MESSAGES.saving)
      return false
    }
    return !hasUnsavedChanges.value || appStore.confirm(DOCUMENT_MESSAGES.leave)
  }

  function attachUnloadProtection() {
    if (unloadAttached) return
    window.addEventListener('beforeunload', protectUnsavedWorkflow)
    unloadAttached = true
  }
  function detachUnloadProtection() {
    window.removeEventListener('beforeunload', protectUnsavedWorkflow)
    unloadAttached = false
  }

  onBeforeRouteLeave(confirmDocumentLeave)
  onBeforeRouteUpdate((to, from) => {
    if (to.name === from.name && String(to.params.id) === String(from.params.id)) return true
    return confirmDocumentLeave(to)
  })
  watch(() => [route.name, route.params.id], ([name, id]) => {
    if (EDITOR_ROUTE_NAMES.has(name) && String(id ?? '') !== String(workflowId.value ?? '')) loadWorkflowDocument(id)
  })
  onMounted(() => { attachUnloadProtection(); loadWorkflowDocument() })
  onActivated(attachUnloadProtection)
  onDeactivated(detachUnloadProtection)
  onUnmounted(() => { documentVersion.value++; detachUnloadProtection() })

  return {
    workflowId, workflowName, isDirty, isNewWorkflow, canEditWorkflow,
    isLoadingWorkflow, workflowLoadError, hasUnsavedChanges, documentVersion,
    loadWorkflowDocument, markSaved, adoptCreatedWorkflow,
  }
}
