export const JSON_OPERATIONS = [
  { value: 'json_to_object', label: 'JSON 解析为对象' },
  { value: 'object_to_json', label: '对象序列化为 JSON' },
  { value: 'map', label: '字段映射' },
  { value: 'filter', label: '数据过滤' },
  { value: 'flatten', label: '数据展开' },
  { value: 'merge', label: '数据合并' },
  { value: 'parse_array', label: '解析数组' },
  { value: 'json_to_xml', label: 'JSON 转 XML' },
  { value: 'xml_to_json', label: 'XML 转 JSON' },
  { value: 'json_schema', label: 'JSON 模式验证' },
  { value: 'json_path', label: 'JSON 路径查询' },
  { value: 'json_merge', label: 'JSON 合并' },
  { value: 'json_query', label: 'JSON 查询' },
]

export const CSV_OPERATIONS = [
  { value: 'csv_to_json', label: 'CSV 转 JSON' },
  { value: 'csv_to_excel', label: 'CSV 转 Excel' },
  { value: 'filter', label: '数据过滤' },
  { value: 'aggregate', label: '数据聚合' },
  { value: 'sort', label: '数据排序' },
  { value: 'join', label: '数据连接' },
  { value: 'pivot', label: '数据透视' },
]

export function createDataTransformConfig(config = {}, kind = 'json') {
  const operation = config.operation || config.transformType || (kind === 'csv' ? 'csv_to_json' : 'json_to_object')
  return { ...config, operation, transformType: operation }
}

export function getDataTransformOperationLabel(operation, kind = 'json') {
  return (kind === 'csv' ? CSV_OPERATIONS : JSON_OPERATIONS).find(item => item.value === operation)?.label || operation || '未配置'
}

export const DATA_TRANSFORM_EXAMPLES = {
  json: {
    map: { mappings: [{ from: 'id', to: 'userId' }] },
    filter: { condition: 'item.age > 18' },
    flatten: { separator: '_' },
    merge: { other: { enabled: true }, deep: true },
    json_merge: { other: { enabled: true }, deep: true },
    json_schema: { type: 'object', required: ['id'], properties: { id: { type: 'integer' } } },
    json_path: { path: '$.items[*].name' },
    json_query: { query: 'items[].name' },
    json_to_xml: { root: 'root' },
  },
  csv: {
    filter: { column: '金额', operator: 'gt', value: 100 },
    aggregate: { groupBy: '类别', agg: 'sum', target: '金额' },
    sort: { column: '金额', ascending: false },
    join: { left: 'id', right: 'id', type: 'inner', rightData: [{ id: 1, name: '示例' }] },
    pivot: { index: '日期', columns: '类别', values: '金额', aggFunc: 'sum' },
  },
}

export function formatDataTransformField(value, fallback = '') {
  if (value === undefined || value === null) return value === null ? 'null' : fallback
  return typeof value === 'string' ? value : JSON.stringify(value, null, 2)
}

export function getDataTransformJsonError(value, { objectOnly = false, arrayOnly = false, allowXml = false } = {}) {
  if (!value?.trim() || (allowXml && value.trim().startsWith('<'))) return ''
  try {
    const parsed = JSON.parse(value)
    if (objectOnly && (!parsed || Array.isArray(parsed) || typeof parsed !== 'object')) return '操作参数必须是 JSON 对象'
    if (arrayOnly && !Array.isArray(parsed)) return 'CSV 备用数据必须是 JSON 数组'
    return ''
  } catch {
    return '请输入有效的 JSON'
  }
}

const DEFAULT_NODE_LABELS = { start: '开始', end: '结束' }

export function getBoundaryNodeLabel(label, type) {
  if (!label || label.trim().toLowerCase() === type) return DEFAULT_NODE_LABELS[type] || label
  return label
}
