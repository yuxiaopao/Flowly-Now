import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { applicationsApi } from '@/api/applications'
import { APPLICATIONS, emptyApplicationDraft, newApplicationRequestKey, parseApplicationInput } from '@/config/applications'
import { useAppStore } from '@/stores/app'
import { authSession } from '@/utils/authSession'

const clone = value => JSON.parse(JSON.stringify(value))
const formFrom = application => ({ name: application.name, description: application.description || '', draft: clone(application.draft || emptyApplicationDraft(application.kind)) })

export function useApplicationWorkspace() {
  const route = useRoute()
  const router = useRouter()
  const app = useAppStore()
  const application = ref(null)
  const form = ref({ name: '', description: '', draft: {} })
  const baseline = ref('')
  const loading = ref(false)
  const loadError = ref('')
  const busy = ref('')
  const feedback = ref('')
  const feedbackIsError = ref(false)
  const testInput = ref('')
  const initialTestInput = ref('')
  const inputOwner = ref(null)
  const evaluationDirty = ref(false)
  const evaluationBusy = ref(false)
  const testResult = ref(null)
  const testError = ref('')
  const testRecoverable = ref(false)
  const publicationUncertain = ref(false)
  const secret = ref('')
  const refreshRevision = ref(0)
  const activeTab = computed(() => APPLICATIONS.tabs.some(tab => tab.id === route.query.tab) ? route.query.tab : 'build')
  const dirty = computed(() => Boolean(application.value && JSON.stringify(form.value) !== baseline.value))
  const testInputDirty = computed(() => Boolean(inputOwner.value && testInput.value !== initialTestInput.value))
  const canEdit = computed(() => application.value?.canEdit === true)
  const canPublish = computed(() => application.value?.canPublish === true)
  const readyToPublish = computed(() => canPublish.value && !dirty.value && !busy.value && !testRecoverable.value && !publicationUncertain.value && application.value?.evaluationGate?.ready !== false && Boolean(application.value?.testedFingerprint) && application.value.testedFingerprint === application.value.draftFingerprint && application.value.lastTestStatus === 'completed')
  let revision = 0
  let disposed = false
  let allowDeletedLeave = false
  let testAttempt = null
  let pollTimer = null
  let wakePoll = null

  function stopPolling() { clearTimeout(pollTimer); wakePoll?.(); wakePoll = null }

  function showFeedback(message, isError = false) { feedback.value = message; feedbackIsError.value = isError }
  async function load() {
    const current = ++revision
    const id = String(route.params.id)
    const preservedInput = inputOwner.value === id ? { value: testInput.value, baseline: initialTestInput.value } : null
    if (!preservedInput) { inputOwner.value = null; testInput.value = ''; initialTestInput.value = '' }
    evaluationDirty.value = false
    evaluationBusy.value = false
    loading.value = true
    loadError.value = ''
    application.value = null
    secret.value = ''
    busy.value = ''
    testResult.value = null
    testError.value = ''
    testRecoverable.value = false
    publicationUncertain.value = false
    testAttempt = null
    stopPolling()
    feedback.value = ''
    try {
      const result = await applicationsApi.get(id)
      if (current !== revision || disposed) return
      application.value = result
      form.value = formFrom(result)
      baseline.value = JSON.stringify(form.value)
      const defaultInput = JSON.stringify(result.kind === 'knowledge' ? { query: '请介绍这份知识库的主要内容。' } : {}, null, 2)
      testInput.value = preservedInput?.value ?? defaultInput
      initialTestInput.value = preservedInput?.baseline ?? defaultInput
      inputOwner.value = id
    } catch (failure) { if (current === revision && !disposed) loadError.value = failure.message || '应用无法加载，请检查权限或重新加载。' }
    finally { if (current === revision && !disposed) loading.value = false }
  }
  async function refreshMetadata(id, current) {
    const result = await applicationsApi.get(id)
    if (current === revision && !disposed) application.value = result
    return result
  }
  function validationError() {
    if (!form.value.name.trim()) return '请输入应用名称。'
    if (form.value.name.length > APPLICATIONS.nameMaxLength) return `应用名称不能超过 ${APPLICATIONS.nameMaxLength} 字。`
    const draft = form.value.draft
    if (application.value.kind === 'workflow') return draft.workflow_id ? '' : '请选择工作流。'
    if (!draft.collection_id) return '请选择知识库。'
    if ((draft.system_prompt || '').length > APPLICATIONS.promptMaxLength) return `系统提示词不能超过 ${APPLICATIONS.promptMaxLength} 字。`
    if (!Number.isInteger(draft.top_k) || draft.top_k < 1 || draft.top_k > APPLICATIONS.maxTopK) return `检索片段数应是 1 到 ${APPLICATIONS.maxTopK} 的整数。`
    if (!Number.isFinite(draft.min_similarity) || draft.min_similarity < 0 || draft.min_similarity > 1) return '相似度阈值应在 0 到 1 之间。'
    return ''
  }
  async function save() {
    if (!canEdit.value || busy.value || !dirty.value) return
    const validation = validationError()
    if (validation) { showFeedback(validation, true); return }
    const current = revision
    const id = application.value.id
    const submittedSource = JSON.stringify(form.value)
    const submitted = clone(form.value)
    submitted.name = submitted.name.trim()
    busy.value = 'save'
    feedback.value = ''
    try {
      const result = await applicationsApi.update(id, submitted)
      if (current !== revision || disposed) return
      application.value = result
      const serverForm = formFrom(result)
      if (JSON.stringify(form.value) === submittedSource) form.value = serverForm
      baseline.value = JSON.stringify(serverForm)
      showFeedback('草稿已保存。配置变更后请重新测试，再发布新版本。')
    } catch (failure) { if (current === revision && !disposed) showFeedback(failure.message || '保存失败，修改仍保留在当前页面。', true) }
    finally { if (current === revision && !disposed) busy.value = '' }
  }
  async function runTest() {
    if (!canEdit.value || dirty.value || busy.value) return
    let input
    try { input = testRecoverable.value && testAttempt ? testAttempt.input : parseApplicationInput(testInput.value) }
    catch (failure) { testError.value = failure.message; return }
    if (!testRecoverable.value || !testAttempt) testAttempt = { input, key: newApplicationRequestKey() }
    const current = revision
    const id = application.value.id
    busy.value = 'test'
    testError.value = ''
    if (!testRecoverable.value) testResult.value = null
    testRecoverable.value = false
    feedback.value = ''
    try {
      let result = await applicationsApi.test(id, input, testAttempt.key)
      if (current !== revision || disposed) return
      testResult.value = result
      const startedAt = Date.now()
      let firstPoll = true
      while (result.status === 'running') {
        if (Date.now() - startedAt >= APPLICATIONS.executionTimeoutMs) throw new Error('请求仍在运行，可恢复同一请求，或到请求日志检查结果。')
        if (!firstPoll) await new Promise(resolve => { wakePoll = resolve; pollTimer = setTimeout(resolve, APPLICATIONS.requestPollMs) })
        firstPoll = false
        if (current !== revision || disposed) return
        result = await applicationsApi.request(id, result.id)
        if (current !== revision || disposed) return
        testResult.value = result
      }
      if (result.status !== 'completed') testError.value = result.errorMessage || '本次测试未成功，请查看请求详情。'
      await refreshMetadata(id, current)
      if (current === revision && !disposed) { refreshRevision.value++; testAttempt = null }
    } catch (failure) {
      if (current !== revision || disposed) return
      testError.value = failure.message || '测试未完成，请检查连接后重试。'
      if (failure.applicationRequest) testResult.value = failure.applicationRequest
      testRecoverable.value = !failure.applicationRequest && (!failure.response || failure.response.status >= 500)
      if (!testRecoverable.value) testAttempt = null
      try { await refreshMetadata(id, current) } catch { /* The failed trace remains visible when the refresh also fails. */ }
      if (current === revision && !disposed) refreshRevision.value++
    } finally { if (current === revision && !disposed) busy.value = '' }
  }
  async function changePublication(action, releaseId) {
    if (!canPublish.value || busy.value || (action === 'publish' && !readyToPublish.value)) return
    if (action !== 'publish' && !await app.confirm({ title: action === 'rollback' ? '切换线上版本？' : '下线应用？', message: action === 'rollback' ? '后续 API 请求将使用所选发布版本，草稿保持不变。' : '下线后发布 API 将拒绝新调用；发布历史与请求记录仍保留。', confirmText: action === 'rollback' ? '切换版本' : '下线应用', cancelText: '保留现状', confirmType: 'warning' })) return
    const current = revision
    const id = application.value.id
    busy.value = action
    feedback.value = ''
    try {
      const result = action === 'rollback' ? await applicationsApi.rollback(id, releaseId) : await applicationsApi[action](id)
      if (current !== revision || disposed) return
      application.value = action === 'publish' ? { ...application.value, activeRelease: result, status: 'published' } : result
      refreshRevision.value++
      showFeedback(action === 'publish' ? '新版本已发布，可在下方配置 API 接入。' : action === 'rollback' ? '线上版本已切换。' : '应用已下线。')
      try { await refreshMetadata(id, current) }
      catch { if (current === revision && !disposed) showFeedback(`${action === 'publish' ? '版本已发布' : action === 'rollback' ? '线上版本已切换' : '应用已下线'}，但最新状态读取失败。请刷新状态后继续。`, true) }
    } catch (failure) {
      if (current === revision && !disposed) {
        publicationUncertain.value = !failure.response || failure.response.status >= 500
        showFeedback(publicationUncertain.value ? '操作结果尚未确认，请先刷新状态检查发布记录，避免重复操作。' : failure.message || '操作未完成，请刷新状态后重试。', true)
        try { await refreshMetadata(id, current) } catch { /* Keep the actionable operation error. */ }
      }
    } finally { if (current === revision && !disposed) busy.value = '' }
  }
  async function remove() {
    if (!canPublish.value || busy.value) return
    if (!await app.confirm({ title: '删除这个应用？', message: '调用能力与密钥将失效，发布和请求记录仍保留为后台审计。', confirmText: '删除应用', cancelText: '保留应用', confirmType: 'danger' })) return
    busy.value = 'delete'
    const current = revision
    try {
      await applicationsApi.remove(application.value.id)
      if (current !== revision || disposed) return
      allowDeletedLeave = true
      secret.value = ''
      await router.push('/applications')
    } catch (failure) { if (current === revision && !disposed) showFeedback(failure.message || '删除失败，请重试。', true) }
    finally { if (current === revision && !disposed) busy.value = '' }
  }
  async function guard({ preserveInput = false } = {}) {
    if (allowDeletedLeave) return true
    if (evaluationBusy.value) { showFeedback('正在同步评测操作结果，请完成后再离开。', true); return false }
    if (busy.value) { showFeedback('当前操作仍在执行，请等待完成后离开。', true); return false }
    if (evaluationDirty.value) return app.confirm({ title: '离开回归评测？',
      message: '未保存的评测编辑将丢失；已提交的批次仍会在后台运行，可从历史中找回。', confirmText: '仍然离开', cancelText: '继续编辑', confirmType: 'warning' })
    if (!dirty.value && !secret.value && !testRecoverable.value) {
      if (!testInputDirty.value || preserveInput) return true
      return app.confirm({ title: APPLICATIONS.inputDraftDiscardTitle, message: APPLICATIONS.inputDraftDiscardMessage,
        confirmText: '放弃并离开', cancelText: '保留输入', confirmType: 'warning' })
    }
    return app.confirm({ title: secret.value ? '离开前保存调用密钥' : testRecoverable.value ? '测试结果尚未确认' : '放弃未保存的草稿？', message: secret.value ? '新密钥只显示这一次。离开后无法再次查看明文；未保存的配置也将丢失。' : testRecoverable.value ? '请求可能仍在服务端执行。离开不会停止执行，可稍后到请求日志检查；未保存的配置也将丢失。' : '当前修改尚未保存，离开后将丢失。', confirmText: '仍然离开', cancelText: '留在工作区', confirmType: 'warning' })
  }
  function beforeUnload(event) { if (dirty.value || evaluationDirty.value || evaluationBusy.value || testInputDirty.value || busy.value || secret.value || testRecoverable.value) { event.preventDefault(); event.returnValue = '' } }
  async function reload() { if (await guard({ preserveInput: true })) await load() }
  function acknowledgeTestInput(input) {
    try { if (JSON.stringify(parseApplicationInput(testInput.value)) === JSON.stringify(input)) initialTestInput.value = testInput.value }
    catch { /* Invalid input is still protected until the user fixes or discards it. */ }
  }
  function updateMetadata(value) {
    if (String(value?.id) === String(application.value?.id)) { application.value = value; refreshRevision.value++ }
  }
  function selectTab(tab) {
    const query = { ...route.query, tab }
    if (tab !== 'requests') delete query.request
    return router.replace({ query })
  }
  watch(() => route.params.id, load, { immediate: true })
  watch(() => authSession.user?.id, (next, previous) => {
    if (previous != null && next !== previous) {
      revision++; stopPolling(); testInput.value = ''; initialTestInput.value = ''; testResult.value = null;
      inputOwner.value = null
      application.value = null; secret.value = ''; busy.value = ''; loading.value = false;
      evaluationDirty.value = false
      evaluationBusy.value = false
      loadError.value = '登录身份已变化，请重新打开应用。'
    }
  })
  watch(activeTab, (next, previous) => { if (previous === 'evaluations' && next !== previous) evaluationDirty.value = false })
  onBeforeRouteLeave(guard)
  onBeforeRouteUpdate(to => String(to.params.id) !== String(route.params.id) || (activeTab.value === 'evaluations' && to.query.tab !== 'evaluations' && (evaluationDirty.value || evaluationBusy.value)) ? guard() : true)
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => { disposed = true; revision++; stopPolling(); secret.value = ''; window.removeEventListener('beforeunload', beforeUnload) })
  return { application, form, loading, loadError, busy, feedback, feedbackIsError, testInput, testInputDirty, evaluationDirty, evaluationBusy, testResult, testError, testRecoverable, secret, refreshRevision, activeTab, dirty, canEdit, canPublish, readyToPublish, load, reload, save, runTest, changePublication, remove, selectTab, showFeedback, acknowledgeTestInput, updateMetadata }
}

