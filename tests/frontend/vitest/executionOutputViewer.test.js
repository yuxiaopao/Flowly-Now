import { describe, expect, it } from 'vitest'
import { collectExecutionOutputs, summarizeNodeExecution } from '@/utils/executionOutputViewer'

describe('collectExecutionOutputs', () => {
  it('collects paper markdown, docx path, table, charts, and node source code', () => {
    const tinyPng = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    const paper = `${'# 摘要\n\n'.repeat(12)}这是一篇足够长的论文正文，用于通过长度与标题检测。`
    const bundle = collectExecutionOutputs({
      nodeStatus: {
        n1: {
          name: '论文格式自检',
          output: { format: 'markdown', content: paper },
        },
        n2: {
          name: '导出Word论文',
          output: { path: 'paper/main.docx', format: 'docx' },
        },
        n3: {
          name: '保存论文文件',
          output: { path: 'paper/main.md', content: paper },
        },
        n4: {
          name: '生成结果三线表',
          output: { table_markdown: '| 指标 | 值 |\n| --- | --- |\n| a | 1 |' },
        },
        n5: {
          name: '自动生成模型图表',
          output: {
            chart_images: [{ title: '图1 轨迹', type: 'png', base64: tinyPng, figure_no: 1 }],
          },
        },
        n6: {
          name: '模型建立·问1',
          output: { text: '{"model":"ballistic","params":{"v":1,"g":9.8,"ok":true}}' },
        },
      },
      workflowNodes: [
        {
          id: 'code-1',
          data: {
            type: 'code',
            label: '数值求解·问1',
            config: { code: 'import math\n\ndef solve():\n    return 1\n' },
          },
        },
      ],
    })

    expect(bundle.totals.documents).toBeGreaterThanOrEqual(3)
    expect(bundle.documents[0].title).toBe('论文终稿 (Markdown)')
    expect(bundle.documents.some((d) => d.kind === 'docx' && d.path === 'paper/main.docx')).toBe(true)
    expect(bundle.documents.some((d) => d.title.includes('三线表'))).toBe(true)
    expect(bundle.images).toHaveLength(1)
    expect(bundle.images[0].url).toContain('data:image/png;base64,')
    expect(bundle.codes.some((c) => c.title === '数值求解·问1.py')).toBe(true)
    expect(bundle.codes.some((c) => c.language === 'json' && c.title.includes('模型建立'))).toBe(true)
  })

  it('reads nested result.chart_images and markdown data-url embeds', () => {
    const bundle = collectExecutionOutputs({
      nodeStatus: {
        charts: {
          name: '自动生成模型图表',
          output: {
            result: {
              markdown_embeds: [
                '![图2](data:image/png;base64,abc123==)',
              ],
            },
          },
        },
      },
    })
    expect(bundle.images).toHaveLength(1)
    expect(bundle.images[0].title).toBe('图2')
  })

  it('keeps distinct chart images even when base64 prefixes are identical', () => {
    const prefix = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    const bundle = collectExecutionOutputs({
      nodeStatus: {
        charts: {
          name: '自动生成模型图表',
          output: {
            chart_images: [
              { title: '图1', type: 'png', base64: prefix, figure_no: 1 },
              { title: '图2', type: 'png', base64: prefix, figure_no: 2 },
              { title: '图3', type: 'png', base64: prefix, figure_no: 3 },
            ],
          },
        },
      },
    })
    expect(bundle.images).toHaveLength(3)
    expect(bundle.images.map((item) => item.title)).toEqual(['图1', '图2', '图3'])
  })

  it('drops UUID-named leftover documents from aggregated node outputs', () => {
    const paper = `${'# 摘要\n\n'.repeat(12)}这是一篇足够长的论文正文，用于通过长度与标题检测。`
    const bundle = collectExecutionOutputs({
      outputData: {
        node_outputs: {
          '0e7178b9-975e-4e16-b032-cdf1e33c9fde': { content: paper },
        },
      },
    })
    expect(bundle.documents).toHaveLength(0)
  })

  it('returns empty lists when there is no execution payload', () => {
    const bundle = collectExecutionOutputs({})
    expect(bundle.totals).toEqual({ documents: 0, codes: 0, images: 0 })
  })

  it('summarizes a single node output for canvas presentation', () => {
    const paper = `${'# 摘要\n\n'.repeat(12)}这是一篇足够长的论文正文，用于通过长度与标题检测。`
    const summary = summarizeNodeExecution({
      nodeId: 'n1',
      name: '论文格式自检',
      output: { format: 'markdown', content: paper },
    })
    expect(summary.hasResult).toBe(true)
    expect(summary.documents[0].title).toBe('论文终稿 (Markdown)')
    expect(summarizeNodeExecution({ nodeId: 'empty', output: null }).hasResult).toBe(false)
  })
})
