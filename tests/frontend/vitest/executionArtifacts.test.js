import { describe, expect, it } from 'vitest'
import { extractExecutionArtifacts, getExecutionArtifactSummary } from '../../../Frontend/src/utils/executionArtifacts'

describe('execution history preserves all generated artifacts', () => {
  it('keeps native 3D model assets downloadable beside the rendered video', () => {
    const result = extractExecutionArtifacts({ outputData: {
      video_url: 'http://localhost/media/final.mp4',
      website_url: 'http://localhost/media/viewer.html',
      files: ['scene.blend', 'pattern.glb', 'garment.gltf', 'mesh.obj', 'model.fbx'].map(name => ({url: `http://localhost/media/${name}`})),
    } })
    expect(result.grouped.file).toHaveLength(5)
    expect(result.grouped.video).toHaveLength(1)
    expect(result.grouped.website).toHaveLength(1)
  })
  it('shows a completed video recorded at workflow level without node records', () => {
    const summary = getExecutionArtifactSummary({ outputData: { video_url: 'https://example.test/final.mp4' } })
    expect(summary.counts.video).toBe(1)
  })

  it('keeps final media beside intermediate node outputs and deduplicates aliases', () => {
    const result = extractExecutionArtifacts({
      nodeExecutions: [{ node_id: 'image', output_data: { images: [{ url: 'https://example.test/keyframe.png' }] } }],
      outputData: { video_url: 'https://example.test/final.mp4', images: [{ url: 'https://example.test/keyframe.png' }] },
    })
    expect(result.grouped.video).toHaveLength(1)
    expect(result.grouped.image).toHaveLength(1)
  })

  it('reads list artifact outputs even when a failed run has no aggregate output', () => {
    const summary = getExecutionArtifactSummary({
      status: 'failed', nodeStatus: { image: 'completed', video: 'failed' },
      artifactOutputs: [{ node_id: 'image', output_data: { images: [{ url: 'https://example.test/keyframe.png' }] } }],
    })
    expect(summary.counts.image).toBe(1)
  })

  it('does not lose media in aggregates with more than twelve node outputs', () => {
    const node_outputs = Object.fromEntries(Array.from({ length: 15 }, (_, i) => [`node-${i}`, { video_url: `https://example.test/${i}.mp4` }]))
    const result = extractExecutionArtifacts({ outputData: { node_outputs } })
    expect(result.grouped.video).toHaveLength(15)
  })

  it('preserves nested node outputs in failed execution snapshots', () => {
    const node_outputs = Object.fromEntries(Array.from({ length: 15 }, (_, i) => [`node-${i}`, { image_url: `https://example.test/${i}.png` }]))
    const result = extractExecutionArtifacts({ outputData: { variables: { node_outputs } } })
    expect(result.grouped.image).toHaveLength(15)
  })

  it('keeps source provenance out of media previews and classifies local paths as files', () => {
    const result = extractExecutionArtifacts({ outputData: {
      videoUrl: 'https://example.test/final.mp4',
      video: 'E:\\outputs\\final.mp4',
      localPath: 'E:\\outputs\\final.mp4',
      metadata: { sources: [{ file: 'E:\\outputs\\keyframe.png' }] },
      files: [{ url: 'https://example.test/report.json' }, { url: 'https://example.test/result.zip' }, { url: 'https://example.test/prompt.txt' }, { url: 'https://example.test/notes.md' }],
    } })
    expect(result.grouped.video).toHaveLength(1)
    expect(result.grouped.image).toHaveLength(0)
    expect(result.grouped.file).toHaveLength(5)
  })
})
