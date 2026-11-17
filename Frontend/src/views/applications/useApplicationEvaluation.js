import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { applicationEvaluationsApi as api } from '@/api/applicationEvaluations'
import { applicationsApi } from '@/api/applications'
import { newApplicationRequestKey } from '@/config/applications'
import { APPLICATION_EVALUATIONS as CONFIG } from '@/config/applicationEvaluations'

export function useApplicationEvaluation(props, emit) {
  const suites = ref([]),
    suiteId = ref(''),
    suiteLoading = ref(false),
    suiteError = ref('')
  const cases = ref([]),
    casesLoading = ref(false),
    casesError = ref('')
  const releases = ref([]),
    releasesError = ref('')
  const history = ref([]),
    historyPage = ref(1),
    historyCount = ref(0),
    historyLoading = ref(false),
    historyError = ref(''),
    historySuiteId = ref('')
  const selectedRun = ref(null),
    requestedRunId = ref(''),
    runLoading = ref(false),
    runError = ref(''),
    baseline = ref(null),
    comparison = ref(null),
    compareError = ref(''),
    comparing = ref(false)
  const target = ref('draft'),
    releaseId = ref(''),
    mutation = ref(''),
    feedback = ref(''),
    failedFeedback = ref(false),
    recoverable = ref(false),
    writeUncertain = ref(false)
  const canEdit = computed(() => Boolean(props.application?.canEdit))
  const selectedSuite = computed(() =>
    suites.value.find((row) => String(row.id) === suiteId.value)
  )
  const hasEnabledCases = computed(() => cases.value.some((row) => row.enabled))
  const blocked = computed(() =>
    Boolean(props.busy || mutation.value || writeUncertain.value)
  )
  const historyPages = computed(() =>
    Math.max(1, Math.ceil(historyCount.value / CONFIG.pageSize))
  )
  let disposed = false,
    revision = 0,
    suiteSequence = 0,
    caseSequence = 0,
    historySequence = 0,
    runSequence = 0,
    compareSequence = 0
  let pollTimer,
    attempt = null
  const controllers = new Set()
  const id = () => String(props.application?.id || '')
  const current = (version) => !disposed && version === revision
  const active = (run) => CONFIG.activeStatuses.includes(run?.status)
  function notice(message, failed = false) {
    feedback.value = message
    failedFeedback.value = failed
  }
  async function read(loader) {
    const controller = new AbortController()
    controllers.add(controller)
    try {
      return await loader({ signal: controller.signal })
    } finally {
      controllers.delete(controller)
    }
  }
  async function pages(loader) {
    const rows = []
    let page = 1,
      result
    do {
      result = await read((options) =>
        loader({ page, page_size: CONFIG.pageSize }, options)
      )
      rows.push(...(Array.isArray(result) ? result : result.results || []))
      page++
    } while (result.next)
    return rows
  }
  async function loadSuites(preferredId) {
    const version = revision,
      sequence = ++suiteSequence,
      appId = id()
    suiteLoading.value = true
    suiteError.value = ''
    try {
      const rows = await pages((params, extra) =>
        api.suites(appId, params, extra)
      )
      if (!current(version) || sequence !== suiteSequence) return
      suites.value = rows
      const next = String(preferredId || suiteId.value)
      suiteId.value = rows.some((row) => String(row.id) === next)
        ? next
        : String(rows[0]?.id || '')
    } catch (error) {
      if (current(version) && sequence === suiteSequence)
        suiteError.value = error.message || '测试集加载失败。'
    } finally {
      if (current(version) && sequence === suiteSequence)
        suiteLoading.value = false
    }
  }
  async function loadCases() {
    const version = revision,
      sequence = ++caseSequence,
      appId = id(),
      selected = suiteId.value
    cases.value = []
    casesError.value = ''
    if (!selected) { casesLoading.value = false; return }
    casesLoading.value = true
    try {
      const rows = await pages((params, extra) =>
        api.cases(appId, selected, params, extra)
      )
      if (current(version) && sequence === caseSequence) cases.value = rows
    } catch (error) {
      if (current(version) && sequence === caseSequence)
        casesError.value = error.message || '用例加载失败。'
    } finally {
      if (current(version) && sequence === caseSequence)
        casesLoading.value = false
    }
  }
  async function loadReleases() {
    const version = revision,
      appId = id()
    releasesError.value = ''
    try {
      const rows = await pages((params) =>
        applicationsApi.releases(appId, params)
      )
      if (!current(version)) return
      releases.value = rows
      if (!rows.some((row) => String(row.id) === releaseId.value))
        releaseId.value = String(
          props.application?.activeRelease?.id || rows[0]?.id || ''
        )
    } catch (error) {
      if (current(version))
        releasesError.value = error.message || '发布版本加载失败。'
    }
  }
  async function loadHistory(page = 1) {
    const version = revision,
      sequence = ++historySequence,
      appId = id()
    historyPage.value = page
    historyLoading.value = true
    historyError.value = ''
    try {
      const result = await read((extra) =>
        api.runs(
          appId,
          {
            page,
            page_size: CONFIG.pageSize,
            suite_id: historySuiteId.value || undefined
          },
          extra
        )
      )
      if (!current(version) || sequence !== historySequence) return
      history.value = result.results || result || []
      historyCount.value = result.count ?? history.value.length
      if (!selectedRun.value) {
        const running = history.value.find(active)
        if (running) await loadRun(running.id)
      }
    } catch (error) {
      if (current(version) && sequence === historySequence)
        historyError.value = error.message || '批次历史加载失败。'
    } finally {
      if (current(version) && sequence === historySequence)
        historyLoading.value = false
    }
  }
  function stopPoll() {
    clearTimeout(pollTimer)
  }
  async function refreshApplication(version = revision) {
    try {
      const application = await applicationsApi.get(id())
      if (current(version)) emit('updated', application)
    } catch {
      if (current(version))
        notice(
          '操作结果已记录，但应用状态刷新失败；请刷新应用确认发布条件。',
          true
        )
    }
  }
  async function loadRun(runId, polling = false) {
    const version = revision,
      sequence = ++runSequence,
      appId = id()
    stopPoll()
    requestedRunId.value = runId
    runError.value = ''
    runLoading.value = !polling
    if (!polling) {
      if (selectedRun.value?.id !== runId) selectedRun.value = null
      compareSequence++
      comparing.value = false
      comparison.value = null
      compareError.value = ''
    }
    try {
      const result = await read((extra) => api.run(appId, runId, extra))
      if (!current(version) || sequence !== runSequence) return
      const wasActive = active(selectedRun.value)
      selectedRun.value = result
      if (active(result))
        pollTimer = setTimeout(() => loadRun(result.id, true), CONFIG.pollMs)
      else if (wasActive || !polling) {
        await Promise.all([
          loadHistory(historyPage.value),
          refreshApplication(version)
        ])
      }
    } catch (error) {
      if (current(version) && sequence === runSequence)
        runError.value =
          error.message || '批次状态加载失败；结果仍以服务端为准。'
    } finally {
      if (current(version) && sequence === runSequence) runLoading.value = false
    }
  }
  async function refreshCollections(preferredId) {
    await loadSuites(preferredId)
    await Promise.all([loadCases(), loadHistory(historyPage.value)])
    if (selectedRun.value) await loadRun(selectedRun.value.id)
  }
  async function mutate(kind, loader, preferred) {
    if (!canEdit.value || blocked.value || recoverable.value) return null
    const version = revision
    mutation.value = kind
    feedback.value = ''
    let result
    try {
      result = await loader()
      if (!current(version)) return null
      notice('已保存。旧批次保留原快照，修改后需要重新运行回归。')
      await refreshCollections(preferred ? result?.id : undefined)
      return current(version) ? result ?? true : null
    } catch (error) {
      if (current(version)) {
        writeUncertain.value = !error.response
        notice(
          writeUncertain.value
            ? '操作结果尚未确认，请先刷新列表核对，避免重复创建。'
            : error.message || '操作失败，请重试。',
          true
        )
      }
      return null
    } finally {
      if (current(version)) mutation.value = ''
    }
  }
  const createSuite = (data) =>
    mutate('suite', () => api.createSuite(id(), data), true)
  const updateSuite = (data) =>
    mutate('suite', () => api.updateSuite(id(), suiteId.value, data))
  const removeSuite = () =>
    mutate('suite-delete', () => api.removeSuite(id(), suiteId.value))
  const saveCase = (caseId, data) =>
    mutate('case', () =>
      caseId
        ? api.updateCase(id(), suiteId.value, caseId, data)
        : api.createCase(id(), suiteId.value, data)
    )
  const removeCase = (caseId) =>
    mutate('case-delete', () => api.removeCase(id(), suiteId.value, caseId))
  const importSuite = (artifact) =>
    mutate('import', () => api.importSuite(id(), artifact), true)
  async function confirmUncertainWrite() {
    await refreshCollections()
    if (!suiteError.value && !casesError.value) {
      writeUncertain.value = false
      notice('列表已重新加载，请核对操作结果后再继续。')
    }
  }
  async function startRun() {
    if (
      !canEdit.value ||
      blocked.value ||
      suiteLoading.value ||
      casesLoading.value ||
      (!recoverable.value && !suiteId.value) ||
      (!recoverable.value && (suiteError.value || casesError.value)) ||
      (!recoverable.value && target.value === 'draft' && props.dirty)
    )
      return
    if (!recoverable.value) {
      if (!hasEnabledCases.value) {
        notice('请先保存并启用至少一条用例。', true)
        return
      }
      if (target.value === 'release' && !releaseId.value) {
        notice('请选择真实发布版本。', true)
        return
      }
      attempt = {
        key: newApplicationRequestKey(),
        data: {
          suite_id: suiteId.value,
          target: target.value,
          ...(target.value === 'release' ? { release_id: releaseId.value } : {})
        }
      }
    }
    if (!attempt) return
    const version = revision
    mutation.value = 'start'
    feedback.value = ''
    recoverable.value = false
    try {
      const result = await api.startRun(id(), attempt.data, attempt.key)
      if (!current(version)) return
      selectedRun.value = result
      attempt = null
      notice('评测批次已由服务端记录，执行状态以批次详情为准。')
      await loadRun(result.id)
    } catch (error) {
      if (!current(version)) return
      if (error.evaluationRun) {
        selectedRun.value = error.evaluationRun
        attempt = null
        notice(error.message || '批次未能启动，请查看服务端错误。', true)
      } else {
        recoverable.value = !error.response || error.response.status >= 500
        if (!recoverable.value) attempt = null
        notice(
          recoverable.value
            ? '启动结果尚未确认。恢复会复用同一请求标识，不会主动创建第二个批次。'
            : error.message || '无法启动评测。',
          true
        )
      }
    } finally {
      if (current(version)) {
        mutation.value = ''
        await loadHistory(1)
      }
    }
  }
  async function cancelRun() {
    if (
      !canEdit.value ||
      blocked.value ||
      !active(selectedRun.value) ||
      selectedRun.value.status === 'cancelling'
    )
      return
    const version = revision,
      runId = selectedRun.value.id
    mutation.value = 'cancel'
    try {
      const result = await api.cancelRun(id(), runId)
      if (!current(version)) return
      selectedRun.value = result
      notice(
        result.status === 'cancelling'
          ? '服务端正在取消；在途操作尚未确认结束，外部副作用无法撤回。'
          : '服务端已记录批次取消结果。'
      )
      await loadRun(runId)
    } catch (error) {
      if (current(version))
        notice(error.message || '取消结果未确认，请刷新批次状态。', true)
    } finally {
      if (current(version)) mutation.value = ''
    }
  }
  async function compare() {
    if (
      !selectedRun.value ||
      !baseline.value ||
      active(selectedRun.value) ||
      active(baseline.value)
    )
      return
    if (
      selectedRun.value.suiteId !== baseline.value.suiteId ||
      selectedRun.value.id === baseline.value.id
    ) {
      compareError.value = '请选择同一测试集的两个不同终态批次。'
      return
    }
    const version = revision,
      sequence = ++compareSequence
    comparing.value = true
    compareError.value = ''
    comparison.value = null
    try {
      const result = await api.compare(
        id(),
        selectedRun.value.id,
        baseline.value.id
      )
      if (current(version) && sequence === compareSequence && result.currentId === selectedRun.value?.id && result.baselineId === baseline.value?.id)
        comparison.value = result
    } catch (error) {
      if (current(version) && sequence === compareSequence)
        compareError.value = error.message || '批次比较失败。'
    } finally {
      if (current(version) && sequence === compareSequence)
        comparing.value = false
    }
  }
  async function saveGate(selected) {
    if (!props.application?.canPublish || blocked.value || recoverable.value)
      return false
    const version = revision
    mutation.value = 'gate'
    try {
      const result = await api.saveGate(id(), selected)
      if (!current(version)) return false
      emit('updated', result)
      notice('发布回归门禁已保存。单次草稿测试仍需通过。')
      return true
    } catch (error) {
      if (current(version)) notice(error.message || '门禁保存失败。', true)
      return false
    } finally {
      if (current(version)) mutation.value = ''
    }
  }
  watch(suiteId, loadCases)
  watch(historySuiteId, () => loadHistory(1))
  watch(
    () => props.application?.id,
    () => {
      revision++
      stopPoll()
      controllers.forEach((controller) => controller.abort())
      controllers.clear()
      suites.value = []
      suiteId.value = ''
      cases.value = []
      releases.value = []
      history.value = []
      historyCount.value = 0
      suiteLoading.value = false
      casesLoading.value = false
      historyLoading.value = false
      runLoading.value = false
      comparing.value = false
      selectedRun.value = null
      requestedRunId.value = ''
      baseline.value = null
      comparison.value = null
      target.value = 'draft'
      releaseId.value = ''
      historySuiteId.value = ''
      feedback.value = ''
      runError.value = ''
      mutation.value = ''
      recoverable.value = false
      writeUncertain.value = false
      attempt = null
      if (id())
        Promise.allSettled([loadSuites(), loadReleases(), loadHistory(1)])
    },
    { immediate: true }
  )
  onBeforeUnmount(() => {
    disposed = true
    revision++
    stopPoll()
    controllers.forEach((controller) => controller.abort())
  })
  return {
    suites,
    suiteId,
    selectedSuite,
    hasEnabledCases,
    suiteLoading,
    suiteError,
    cases,
    casesLoading,
    casesError,
    releases,
    releasesError,
    history,
    historyPage,
    historyCount,
    historyPages,
    historyLoading,
    historyError,
    historySuiteId,
    selectedRun,
    requestedRunId,
    runLoading,
    runError,
    baseline,
    comparison,
    compareError,
    comparing,
    target,
    releaseId,
    mutation,
    feedback,
    failedFeedback,
    recoverable,
    writeUncertain,
    canEdit,
    blocked,
    active,
    loadSuites,
    loadCases,
    loadReleases,
    loadHistory,
    loadRun,
    refreshCollections,
    createSuite,
    updateSuite,
    removeSuite,
    saveCase,
    removeCase,
    importSuite,
    confirmUncertainWrite,
    startRun,
    cancelRun,
    compare,
    saveGate,
    notice
  }
}
