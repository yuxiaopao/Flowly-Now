/**
 * 节点连线后的自动传参（变量引用接线）。
 *
 * 设计原则（防乱传 / 防重复）：
 * 1. 仅允许「语义匹配」的 source→target 组合（白名单），其它连线不传参。
 * 2. 一条边只填「该上游产出的那一个槽位」：图边只填图、文边只填文。
 * 3. 每个槽位只写一个主字段；若任一别名已有值则跳过（不重复填）。
 * 4. 永不覆盖用户已写内容。
 */

const IMAGE_TYPES = new Set(['image_generation', 'image_editing'])
const VIDEO_TYPES = new Set(['video_generation'])

/** 槽位：主字段 + 别名（任一有值即视为已接线） */
const SLOTS = {
  llmUser: { primary: 'userTemplate', aliases: ['user_template'] },
  prompt: { primary: 'prompt', aliases: ['text'] },
  image: { primary: 'inputImage', aliases: ['input_image', 'image'] },
  instruction: { primary: 'instruction', aliases: ['prompt'] },
  audioText: { primary: 'text', aliases: ['prompt', 'input'] },
  subtitleVideo: { primary: 'inputPath', aliases: ['input_path', 'input', 'inputVideo', 'input_video'] },
  burnVideo: { primary: 'video_input', aliases: ['videoInput', 'inputVideo'] },
  burnSubtitle: { primary: 'subtitle_input', aliases: ['subtitleInput', 'srt'] },
  outputTemplate: { primary: 'template', aliases: [] },
  httpBody: { primary: 'body', aliases: [] },
}

function isEmptyRef(value) {
  if (value == null) return true
  if (typeof value === 'string') return !value.trim()
  return false
}

function slotFilled(config, slot) {
  const keys = [slot.primary, ...(slot.aliases || [])]
  return keys.some((k) => !isEmptyRef(config[k]))
}

/** 只写主字段一次；别名已有值也算已填 */
function fillSlot(config, slot, value) {
  if (slotFilled(config, slot)) return false
  config[slot.primary] = value
  return true
}

function getNodeConfig(node) {
  return node?.data?.config || node?.config || {}
}

/** input 节点变量名 → {prompt} / {input} 等 */
export function getInputVarRef(sourceNode) {
  const cfg = getNodeConfig(sourceNode)
  const name = String(
    cfg.input_name || cfg.variable_name || cfg.variableName || 'input',
  ).trim() || 'input'
  return `{${name}}`
}

function getNodeType(node) {
  return String(node?.type || node?.data?.type || '').trim()
}

/**
 * @param {string} sourceType
 * @param {string} targetType
 * @param {object} targetConfig
 * @param {{ sourceNode?: object }} [opts]
 * @returns {{ config: object, changed: boolean, hints: string[] }}
 */
export function wireTargetConfigOnConnect(sourceType, targetType, targetConfig = {}, opts = {}) {
  const source = String(sourceType || '').trim()
  const target = String(targetType || '').trim()
  const config = { ...(targetConfig || {}) }
  const hints = []
  let changed = false

  const mark = (ok, hint) => {
    if (ok) {
      changed = true
      if (hint) hints.push(hint)
    }
  }

  const inputRef = opts.sourceNode ? getInputVarRef(opts.sourceNode) : '{input}'

  // —— LLM / Prompt：只接上游文本 ——
  if (target === 'llm' || target === 'prompt') {
    if (source === 'input') {
      mark(fillSlot(config, SLOTS.llmUser, inputRef), `已引用输入 ${inputRef}`)
    } else if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.llmUser, '{text}'), '已引用上游文案 {text}')
    }
    // start / rag / http 等不自动接线，避免乱填
  }

  // —— 文生图：只接文本 prompt ——
  if (target === 'image_generation') {
    if (source === 'input') {
      mark(fillSlot(config, SLOTS.prompt, inputRef), `已引用输入 ${inputRef}`)
    } else if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.prompt, '{text}'), '已引用上游文案 {text}')
    }
  }

  // —— 图像编辑：图边只填图，文边只填指令（互不抢槽） ——
  if (target === 'image_editing') {
    if (IMAGE_TYPES.has(source)) {
      mark(fillSlot(config, SLOTS.image, '{images.0.url}'), '已引用上游图片 {images.0.url}')
    } else if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.instruction, '{text}'), '已引用编辑指令 {text}')
    } else if (source === 'input') {
      mark(fillSlot(config, SLOTS.instruction, inputRef), `已引用编辑指令 ${inputRef}`)
    }
  }

  // —— 视频：图边只填 inputImage，文边只填 prompt ——
  if (target === 'video_generation') {
    if (IMAGE_TYPES.has(source)) {
      mark(fillSlot(config, SLOTS.image, '{images.0.url}'), '已引用上游图片 {images.0.url}')
    } else if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.prompt, '{text}'), '已引用视频提示词 {text}')
    } else if (source === 'input') {
      mark(fillSlot(config, SLOTS.prompt, inputRef), `已引用视频提示词 ${inputRef}`)
    }
  }

  // —— 语音：只接文本 ——
  if (target === 'audio_generation') {
    if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.audioText, '{text}'), '已引用上游文案 {text}')
    } else if (source === 'input') {
      mark(fillSlot(config, SLOTS.audioText, inputRef), `已引用输入 ${inputRef}`)
    }
  }

  // —— 字幕：只接视频 ——
  if (target === 'subtitle_generation') {
    if (VIDEO_TYPES.has(source) || source === 'video_upload') {
      mark(fillSlot(config, SLOTS.subtitleVideo, '{video_url}'), '已引用上游视频 {video_url}')
    }
  }

  // —— 烧录：视频边 / 字幕边分槽 ——
  if (target === 'subtitle_burn') {
    if (VIDEO_TYPES.has(source) || source === 'video_upload' || source === 'lip_sync') {
      mark(fillSlot(config, SLOTS.burnVideo, '{video_url}'), '已引用视频 {video_url}')
    } else if (source === 'subtitle_generation' || source === 'subtitle_translate') {
      mark(fillSlot(config, SLOTS.burnSubtitle, '{srt}'), '已引用字幕 {srt}')
    }
  }

  // —— 输出：按上游产物类型选模板 ——
  if (target === 'output') {
    if (IMAGE_TYPES.has(source)) {
      mark(fillSlot(config, SLOTS.outputTemplate, '{images.0.url}'), '输出引用图片')
    } else if (VIDEO_TYPES.has(source)) {
      mark(fillSlot(config, SLOTS.outputTemplate, '{video_url}'), '输出引用视频')
    } else if (source === 'audio_generation') {
      mark(fillSlot(config, SLOTS.outputTemplate, '{audio_url}'), '输出引用音频')
    } else if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.outputTemplate, '{text}'), '输出引用文本')
    } else if (source === 'input') {
      mark(fillSlot(config, SLOTS.outputTemplate, inputRef), `输出引用 ${inputRef}`)
    }
  }

  // —— HTTP：仅 LLM/Prompt 文本作 body ——
  if (target === 'http_request') {
    if (source === 'llm' || source === 'prompt') {
      mark(fillSlot(config, SLOTS.httpBody, '{text}'), '请求体引用上游文本')
    }
  }

  return { config, changed, hints: hints.filter(Boolean) }
}

/**
 * 根据 source/target 节点对象接线，返回更新后的 target 节点（浅拷贝）。
 */
export function wireNodesOnConnect(sourceNode, targetNode) {
  if (!sourceNode || !targetNode) {
    return { node: targetNode, changed: false, hints: [] }
  }
  const sourceType = getNodeType(sourceNode)
  const targetType = getNodeType(targetNode)
  const prevConfig = getNodeConfig(targetNode)
  const { config, changed, hints } = wireTargetConfigOnConnect(
    sourceType,
    targetType,
    prevConfig,
    { sourceNode },
  )
  if (!changed) {
    return { node: targetNode, changed: false, hints: [] }
  }
  const next = {
    ...targetNode,
    data: {
      ...(targetNode.data || {}),
      type: targetType,
      config,
    },
    config,
  }
  return { node: next, changed: true, hints }
}

/**
 * 对整图按边批量接线（NL / 加载 / 保存兜底）。
 * 多入边时：各边只填各自槽位，先填满的槽不会被后边覆盖。
 */
export function wireWorkflowVariableRefs(nodes = [], edges = []) {
  const nodeById = Object.fromEntries((nodes || []).map((n) => [n.id, n]))
  let patched = false
  const allHints = []

  ;(edges || []).forEach((edge) => {
    const source = nodeById[edge.source]
    const target = nodeById[edge.target]
    if (!source || !target) return
    const { node, changed, hints } = wireNodesOnConnect(source, target)
    if (changed) {
      nodeById[edge.target] = node
      patched = true
      allHints.push(...hints)
    }
  })

  return {
    nodes: (nodes || []).map((n) => nodeById[n.id] || n),
    patched,
    hints: allHints,
  }
}

export const NODE_WIRING_IMAGE_TYPES = IMAGE_TYPES
export const NODE_WIRING_SLOTS = SLOTS
