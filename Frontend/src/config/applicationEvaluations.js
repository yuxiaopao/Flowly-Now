import { APPLICATIONS, parseApplicationInput } from './applications'

export const APPLICATION_EVALUATIONS = Object.freeze({
  pageSize: APPLICATIONS.pageSize,
  pollMs: APPLICATIONS.requestPollMs,
  nameMaxLength: 160,
  descriptionMaxLength: 4000,
  maxAssertions: 20,
  maxImportBytes: 2 * 1024 * 1024,
  maxPointerLength: 1000,
  maxTextExpectedLength: 4000,
  maxSources: 50,
  activeStatuses: Object.freeze(['queued', 'running', 'cancelling']),
  runStatuses: Object.freeze({
    queued: '排队中',
    running: '执行中',
    cancelling: '正在取消',
    completed: '已完成',
    failed: '批次失败',
    cancelled: '已取消'
  }),
  caseStatuses: Object.freeze({
    pending: '等待执行',
    running: '执行中',
    passed: '通过',
    failed: '断言未通过',
    error: '执行错误',
    skipped: '未执行',
    cancelled: '已取消'
  }),
  changes: Object.freeze({
    added: '新增用例',
    removed: '移除用例',
    modified: '用例已修改',
    regressed: '退步',
    improved: '进步',
    unchanged: '无变化',
    inconclusive: '不可归因'
  }),
  jsonTypes: Object.freeze([
    'object',
    'array',
    'string',
    'number',
    'boolean',
    'null'
  ]),
  assertionTypes: Object.freeze(
    [
      {
        value: 'json_equals',
        label: 'JSON 值相等',
        pointer: true,
        hint: 'expected 可为任意 JSON 值，区分大小写和类型。'
      },
      {
        value: 'json_contains',
        label: 'JSON 包含',
        pointer: true,
        hint: '字符串包含文本、数组包含完整元素，或对象包含指定键值。'
      },
      {
        value: 'json_exists',
        label: 'JSON 字段存在',
        pointer: true,
        hint: 'expected 填 true 或 false。'
      },
      {
        value: 'json_type',
        label: 'JSON 值类型',
        pointer: true,
        hint: 'expected 填类型字符串，例如 "string"。'
      },
      {
        value: 'response_contains',
        label: '回答包含文本',
        hint: '仅检查知识回答 response，expected 填非空 JSON 字符串。'
      },
      {
        value: 'grounded',
        label: '回答有证据',
        hint: '检查真实 grounded 字段，expected 填 true 或 false。'
      },
      {
        value: 'sources_min',
        label: '最少来源数',
        hint: 'expected 填 0 至 50 的整数。'
      },
      {
        value: 'latency_max',
        label: '最大耗时（毫秒）',
        hint: 'expected 填非负数值；没有真实耗时不能判为通过。'
      },
      {
        value: 'error_code',
        label: '预期错误代码',
        hint: '用于负向用例，expected 填实际错误代码字符串。'
      }
    ].map(Object.freeze)
  )
})

const finiteJson = (value) =>
  typeof value === 'number'
    ? Number.isFinite(value)
    : Array.isArray(value)
      ? value.every(finiteJson)
      : value && typeof value === 'object'
        ? Object.values(value).every(finiteJson)
        : true

export function parseEvaluationJson(text, label = 'JSON') {
  let value
  try {
    value = JSON.parse(text)
  } catch {
    throw new Error(`${label} 不是有效 JSON。`)
  }
  if (!finiteJson(value)) throw new Error(`${label} 必须使用有限 JSON 数值。`)
  return value
}

export function parseEvaluationCase(form) {
  const name = form.name.trim()
  if (!name || name.length > APPLICATION_EVALUATIONS.nameMaxLength)
    throw new Error('用例名称需要 1 至 160 字。')
  const input = parseApplicationInput(form.inputText)
  const position = Number(form.position || 0)
  if (!Number.isInteger(position) || position < 0 || position > 10000) throw new Error('排列位置需要 0 至 10000 的整数。')
  if (!finiteJson(input)) throw new Error('输入必须使用有限 JSON 数值。')
  if (
    !form.assertions.length ||
    form.assertions.length > APPLICATION_EVALUATIONS.maxAssertions
  )
    throw new Error('每条用例需要 1 至 20 条断言。')
  const assertions = form.assertions.map((row) => {
    const definition = APPLICATION_EVALUATIONS.assertionTypes.find(
      (item) => item.value === row.type
    )
    if (!definition) throw new Error('请选择支持的断言类型。')
    const path = definition.pointer ? row.path || '' : ''
    if (
      path.length > APPLICATION_EVALUATIONS.maxPointerLength ||
      (path && (!path.startsWith('/') || /~(?![01])/.test(path)))
    )
      throw new Error('字段路径必须为有效 JSON Pointer；根对象使用空字符串。')
    const expected = parseEvaluationJson(row.expectedText, '断言 expected')
    if (
      ['json_exists', 'grounded'].includes(row.type) &&
      typeof expected !== 'boolean'
    )
      throw new Error('存在性和证据断言需要 true 或 false。')
    if (
      row.type === 'json_type' &&
      !APPLICATION_EVALUATIONS.jsonTypes.includes(expected)
    )
      throw new Error('请选择有效 JSON 类型字符串。')
    if (
      ['response_contains', 'error_code'].includes(row.type) &&
      (typeof expected !== 'string' ||
        !expected ||
        expected.length > APPLICATION_EVALUATIONS.maxTextExpectedLength)
    )
      throw new Error('文本与错误代码断言需要非空 JSON 字符串。')
    if (
      ['sources_min', 'latency_max'].includes(row.type) &&
      (typeof expected !== 'number' || expected < 0)
    )
      throw new Error('来源数与最大耗时需要非负有限数值。')
    if (
      row.type === 'sources_min' &&
      (!Number.isInteger(expected) ||
        expected > APPLICATION_EVALUATIONS.maxSources)
    )
      throw new Error('最少来源数需要 0 至 50 的整数。')
    return { type: row.type, path, expected }
  })
  return {
    name,
    input_data: input,
    assertions,
    enabled: Boolean(form.enabled),
    position
  }
}

export function sameEvaluationInput(left, right) {
  if (left === right) return true
  if (
    !left ||
    !right ||
    typeof left !== 'object' ||
    typeof right !== 'object' ||
    Array.isArray(left) !== Array.isArray(right)
  )
    return false
  const keys = Object.keys(left)
  return (
    keys.length === Object.keys(right).length &&
    keys.every(
      (key) =>
        Object.hasOwn(right, key) && sameEvaluationInput(left[key], right[key])
    )
  )
}

export const evaluationPercent = (value) =>
  value == null
    ? '未提供'
    : new Intl.NumberFormat('zh-CN', {
        style: 'percent',
        maximumFractionDigits: 1
      }).format(value)
