export const ANALYTICS = Object.freeze({ pollMs: 2000, maxCompare: 4, pageSize: 100, maxErrors: 12 })
export const TASK_LABELS = Object.freeze({ classify: '图像分类', detect: '目标检测', segment: '实例分割', pose: '姿态估计', obb: '旋转框检测' })
export const STATUS_LABELS = Object.freeze({ completed: '训练完成', running: '训练中', queued: '排队中', failed: '训练失败', cancelled: '已取消' })
const finite = value => typeof value === 'number' && Number.isFinite(value)
export const formatMetric = value => finite(value) ? `${(value * 100).toFixed(2)}%` : '—'
export const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char])

export function metricLabel(key) {
  const names = { 'accuracy_top1': 'Top-1 准确率', 'accuracy_top5': 'Top-5 准确率', precision: 'Precision', recall: 'Recall', mAP50: 'mAP50', 'mAP50-95': 'mAP50–95' }
  const bare = key.replace(/^metrics\//, '')
  const match = bare.match(/^(.*?)(\([BMP]\))?$/)
  const suffix = { '(B)': '框', '(M)': '掩膜', '(P)': '关键点' }[match?.[2]]
  return (names[match?.[1]] || bare) + (suffix ? ` · ${suffix}` : '')
}

export function metricGroups(history) {
  const keys = [...new Set(history.flatMap(row => Object.keys(row)))].filter(key => history.some(row => finite(row[key])))
  const metrics = keys.filter(key => key.startsWith('metrics/'))
  const grouped = new Map()
  for (const key of metrics) {
    const group = key.includes('(M)') ? '掩膜质量' : key.includes('(P)') ? '关键点质量' : key.includes('accuracy') ? '验证准确率' : '检测质量'
    grouped.set(group, [...(grouped.get(group) || []), key])
  }
  return {
    losses: keys.filter(key => /^(train|val)\/.+loss$|^(train|val)\/loss$/.test(key)),
    quality: [...grouped].map(([label, series]) => ({ label, series })),
    learningRates: keys.filter(key => key.startsWith('lr/')),
  }
}

export function primaryMetric(run) {
  const keys = metricGroups(run.history || []).quality.flatMap(group => group.series)
  const preferred = run.task === 'classify' ? ['metrics/accuracy_top1']
    : run.task === 'segment' ? ['metrics/mAP50-95(M)', 'metrics/mAP50(M)']
      : run.task === 'pose' ? ['metrics/mAP50-95(P)', 'metrics/mAP50(P)']
        : ['metrics/mAP50-95(B)', 'metrics/mAP50(B)']
  return preferred.find(key => keys.includes(key)) || keys[0] || null
}

export function bestValue(run, key = primaryMetric(run)) {
  const rows = (run.history || []).filter(row => key && finite(row[key]))
  return rows.reduce((best, row) => !best || row[key] > best.value ? { value: row[key], epoch: row.epoch } : best, null)
}

export function lineOptions(history, keys, percentage = false) {
  return {
    tooltip: { trigger: 'axis', valueFormatter: value => finite(value) ? percentage ? formatMetric(value) : Number(value).toPrecision(5) : '—' },
    legend: { type: 'scroll', bottom: 0 },
    grid: { top: 24, left: 56, right: 26, bottom: 88 },
    xAxis: { type: 'value', name: '轮次', min: 1, minInterval: 1 },
    yAxis: { type: 'value', ...(percentage ? { min: 0, max: 1, axisLabel: { formatter: value => `${Math.round(value * 100)}%` } } : {}) },
    dataZoom: [{ type: 'inside', filterMode: 'none' }, { type: 'slider', bottom: 30, height: 18, filterMode: 'none' }],
    series: keys.map(key => ({ name: key.startsWith('metrics/') ? metricLabel(key) : key, type: 'line', connectNulls: false, showSymbol: history.length < 80, symbolSize: 5, data: history.map(row => [row.epoch, finite(row[key]) ? row[key] : null]) })),
  }
}

export function confusionData(report, mode = 'count') {
  const names = report?.classes || []
  const matrix = report?.confusion_matrix
  if (!Array.isArray(matrix) || matrix.length !== names.length || matrix.some(row => !Array.isArray(row) || row.length !== names.length || row.some(value => !finite(value) || value < 0))) return null
  const cells = []
  const errors = []
  matrix.forEach((row, actual) => {
    const total = row.reduce((sum, value) => sum + value, 0)
    row.forEach((count, predicted) => {
      cells.push([predicted, actual, mode === 'normalized' ? total ? count / total : 0 : count, count])
      if (actual !== predicted && count > 0) errors.push({ actual: names[actual], predicted: names[predicted], count, ratio: total ? count / total : 0 })
    })
  })
  return { names, cells, errors: errors.sort((a, b) => b.count - a.count).slice(0, ANALYTICS.maxErrors) }
}

export function confusionOptions(report, labels, mode) {
  const data = confusionData(report, mode)
  if (!data) return null
  const display = key => labels.get(key) || key
  const normalized = mode === 'normalized'
  return {
    animation: false,
    tooltip: { position: 'top', confine: true, formatter: item => {
      const [predicted, actual, value, count] = item.value
      return `真实：${escapeHtml(display(data.names[actual]))}<br>预测：${escapeHtml(display(data.names[predicted]))}<br>样本数：${count}<br>${normalized ? `该真实类别占比：${formatMetric(value)}` : ''}`
    } },
    grid: { top: 22, left: 190, right: 58, bottom: 150 },
    xAxis: { type: 'category', name: '预测类别', data: data.names.map(display), axisLabel: { rotate: 60, fontSize: 10, width: 110, overflow: 'truncate' }, splitArea: { show: true } },
    yAxis: { type: 'category', name: '真实类别', inverse: true, data: data.names.map(display), axisLabel: { fontSize: 10, width: 165, overflow: 'truncate' } },
    visualMap: { min: 0, max: normalized ? 1 : Math.max(1, ...data.cells.map(cell => cell[2])), calculable: true, orient: 'horizontal', left: 'center', bottom: 0, itemWidth: 12, itemHeight: 180, text: normalized ? ['100%', '0%'] : ['多', '少'] },
    dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'none' }, { type: 'slider', yAxisIndex: 0, right: 8, filterMode: 'none', width: 16 }],
    series: [{ type: 'heatmap', data: data.cells, label: { show: data.names.length <= 16, formatter: item => normalized ? formatMetric(item.value[2]) : item.value[3] }, emphasis: { itemStyle: { borderWidth: 1 } } }],
  }
}

export function classRows(report, classes) {
  return classes.flatMap(item => {
    const row = report?.per_class?.[item.key]
    return row ? [{ ...item, precision: row.precision, recall: row.recall, f1: row['f1-score'], support: row.support }] : []
  })
}

export function classOptions(rows, metric) {
  const data = [...rows].filter(row => finite(row[metric])).sort((a, b) => a[metric] - b[metric])
  return {
    tooltip: { trigger: 'axis', valueFormatter: formatMetric },
    grid: { top: 20, left: 190, right: 52, bottom: 40 },
    xAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: value => `${Math.round(value * 100)}%` } },
    yAxis: { type: 'category', inverse: true, data: data.map(row => row.label), axisLabel: { width: 170, overflow: 'truncate' } },
    dataZoom: data.length > 18 ? [{ type: 'slider', yAxisIndex: 0, right: 2, width: 16, startValue: 0, endValue: 17 }] : [],
    series: [{ name: metric, type: 'bar', barMaxWidth: 18, data: data.map(row => row[metric]), label: { show: true, position: 'right', formatter: item => formatMetric(item.value) } }],
  }
}

export function comparisonWarning(runs) {
  if (new Set(runs.map(run => run.task)).size > 1) return '任务类型不同，请选择同一种任务再比较。'
  const fingerprints = runs.map(run => run.dataset?.fingerprint)
  if (fingerprints.every(Boolean) && new Set(fingerprints).size === 1) return ''
  return runs.length > 1 ? '这些记录未确认使用同一数据划分，指标仅供参考，不代表公平的模型排名。' : ''
}
