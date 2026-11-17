import { describe, it, expect } from 'vitest'
import { metricGroups, primaryMetric, bestValue, lineOptions, confusionData, confusionOptions, classRows, comparisonWarning } from '../../../Frontend/src/components/workflow/yolo/analyticsMetrics'

describe('YOLO task-specific analysis', () => {
  it.each([
    ['classify', 'metrics/accuracy_top1'], ['detect', 'metrics/mAP50-95(B)'],
    ['segment', 'metrics/mAP50-95(M)'], ['pose', 'metrics/mAP50-95(P)'], ['obb', 'metrics/mAP50-95(B)'],
  ])('uses the actual primary metric for %s', (task, key) => {
    const run = { task, history: [{ epoch: 1, [key]: 0 }, { epoch: 2, [key]: 0.8 }] }
    expect(primaryMetric(run)).toBe(key)
    expect(bestValue(run)).toEqual({ value: 0.8, epoch: 2 })
  })
  it('keeps box, mask and pose metrics distinct and omits unrecorded classification accuracy', () => {
    const groups = metricGroups([{ epoch: 1, 'train/box_loss': 0, 'val/seg_loss': 0.3, 'metrics/mAP50(B)': 0.8, 'metrics/mAP50(M)': 0.7, 'metrics/mAP50(P)': 0.6 }])
    expect(groups.losses).toEqual(['train/box_loss', 'val/seg_loss'])
    expect(groups.quality.map(group => group.label)).toEqual(['检测质量', '掩膜质量', '关键点质量'])
    expect(groups.quality.flatMap(group => group.series)).not.toContain('metrics/accuracy_top1')
  })
  it('preserves zero and missing epochs instead of interpolating invented values', () => {
    const option = lineOptions([{ epoch: 1, score: 0 }, { epoch: 3 }, { epoch: 7, score: 0.5 }], ['score'], true)
    expect(option.series[0].data).toEqual([[1, 0], [3, null], [7, 0.5]])
    expect(option.series[0].connectNulls).toBe(false)
  })
})

describe('confusion matrix correctness', () => {
  const report = { classes: ['a', 'b', 'empty'], confusion_matrix: [[8, 2, 0], [1, 4, 0], [0, 0, 0]] }
  it('uses true rows and predicted columns and identifies real misclassification pairs', () => {
    const result = confusionData(report)
    expect(result.cells.find(cell => cell[0] === 1 && cell[1] === 0)).toEqual([1, 0, 2, 2])
    expect(result.errors[0]).toEqual({ actual: 'a', predicted: 'b', count: 2, ratio: 0.2 })
  })
  it('normalizes by the original complete row, including classes with no samples', () => {
    const data = confusionData(report, 'normalized')
    expect(data.cells.find(cell => cell[0] === 1 && cell[1] === 0)).toEqual([1, 0, 0.2, 2])
    expect(data.cells.filter(cell => cell[1] === 2).every(cell => cell[2] === 0)).toBe(true)
  })
  it.each([null, { classes: ['a'], confusion_matrix: [[-1]] }, { classes: ['a'], confusion_matrix: [[NaN]] }, { classes: ['a'], confusion_matrix: [[1, 2]] }])('rejects invalid or missing matrix data: %j', value => {
    expect(confusionData(value)).toBeNull()
  })
  it('escapes class labels in chart tooltips', () => {
    const option = confusionOptions(report, new Map([['a', '<img src=x onerror=bad()>']]), 'count')
    expect(option.tooltip.formatter({ value: [1, 0, 2, 2] })).not.toContain('<img')
  })
  it('keeps evaluation classes aligned by key rather than table position', () => {
    expect(classRows({ per_class: { b: { precision: 0, recall: 1, 'f1-score': 0, support: 3 } } }, [{ key: 'a', label: 'A' }, { key: 'b', label: 'B' }])).toEqual([{ key: 'b', label: 'B', precision: 0, recall: 1, f1: 0, support: 3 }])
  })
})

describe('comparison provenance', () => {
  it('warns about different tasks and unknown data splits', () => {
    expect(comparisonWarning([{ task: 'classify' }, { task: 'detect' }])).toContain('任务类型不同')
    expect(comparisonWarning([{ task: 'classify' }, { task: 'classify' }])).toContain('未确认使用同一数据划分')
    expect(comparisonWarning([{ task: 'classify', dataset: { fingerprint: 'same' } }, { task: 'classify', dataset: { fingerprint: 'same' } }])).toBe('')
  })
})
