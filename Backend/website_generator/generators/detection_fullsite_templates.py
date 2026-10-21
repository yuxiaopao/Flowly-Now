"""Full-featured detection site templates: image / video / realtime / fact / history."""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List, Optional

from .modern_templates import get_modern_css_block

DETECTION_MODES = ('image', 'video', 'realtime', 'fact', 'history')


def build_detection_extra_css(primary: str) -> str:
    return f"""
    .app-layout {{ display: flex; flex-direction: column; min-height: 100vh; }}
    .mode-nav {{
      display: flex; gap: 8px; padding: 12px 24px; border-bottom: 1px solid var(--color-border, #2e2e42);
      background: var(--color-surface, #18181f); flex-wrap: wrap; justify-content: center;
    }}
    .mode-tab {{
      padding: 10px 18px; border-radius: 999px; border: 1px solid var(--color-border, #2e2e42);
      background: transparent; color: var(--color-text-muted, #a1a1aa); cursor: pointer; font-size: 14px;
      transition: all 0.2s; min-height: 40px;
    }}
    .mode-tab:hover {{ border-color: {primary}; color: var(--color-text, #f4f4f5); }}
    .mode-tab.active {{
      background: color-mix(in srgb, {primary} 18%, transparent);
      border-color: {primary}; color: {primary}; font-weight: 600;
    }}
    .panel {{ width: 100%; max-width: 960px; display: none; flex-direction: column; gap: 20px; }}
    .panel.active {{ display: flex; }}
    .upload-zone {{ max-width: 100%; }}
    .upload-zone.video {{ padding: 40px; }}
    .media-stage {{
      position: relative; width: 100%; background: #0a0a0f; border-radius: 12px; overflow: hidden;
      border: 1px solid var(--color-border, #2e2e42); min-height: 240px;
    }}
    .media-stage img, .media-stage video {{ display: block; width: 100%; max-height: 520px; object-fit: contain; }}
    .media-stage canvas {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
    .toolbar {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
    .btn {{
      padding: 10px 18px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; font-weight: 600;
      min-height: 40px;
    }}
    .btn-primary {{ background: {primary}; color: #0f0f14; }}
    .btn-secondary {{ background: var(--color-surface-elevated, #1f1f2e); color: var(--color-text, #f4f4f5); border: 1px solid var(--color-border, #2e2e42); }}
    .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
    .status-pill {{
      display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
      font-size: 12px; background: var(--color-surface, #18181f); border: 1px solid var(--color-border, #2e2e42);
    }}
    .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #71717a; }}
    .status-dot.live {{ background: #22c55e; animation: pulse 1.2s infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .detection-stats {{ padding: 16px 24px; border-bottom: 1px solid var(--color-border, #2e2e42); display: flex; gap: 24px; flex-wrap: wrap; }}
    .stat-value {{ font-size: 20px; font-weight: 700; color: {primary}; }}
    .stat-label {{ font-size: 12px; color: #a1a1aa; }}
    .detection-list {{ padding: 16px 24px; max-height: 220px; overflow-y: auto; }}
    .detection-item {{ display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #2e2e42; }}
    .detection-item:last-child {{ border-bottom: none; }}
    .detection-label {{ font-weight: 600; min-width: 80px; }}
    .confidence-bar {{ flex: 1; height: 6px; background: #2e2e42; border-radius: 3px; overflow: hidden; }}
    .confidence-fill {{ height: 100%; background: {primary}; }}
    .loading {{ color: {primary}; text-align: center; padding: 32px; }}
    .history-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; width: 100%; }}
    .history-card {{
      background: var(--color-surface, #18181f); border: 1px solid var(--color-border, #2e2e42);
      border-radius: 8px; padding: 16px; cursor: pointer; transition: border-color 0.2s;
    }}
    .history-card:hover {{ border-color: {primary}; }}
    .history-card h4 {{ font-size: 14px; margin-bottom: 8px; color: var(--color-text, #f4f4f5); }}
    .history-meta {{ font-size: 12px; color: var(--color-text-muted, #a1a1aa); display: flex; flex-direction: column; gap: 4px; }}
    .mode-badge {{
      display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px;
      background: color-mix(in srgb, {primary} 20%, transparent); color: {primary};
    }}
    .empty-state {{ text-align: center; padding: 48px 24px; color: var(--color-text-muted, #a1a1aa); }}
    .class-legend {{
      display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; padding: 12px 24px 0;
      max-width: 1100px; margin: 0 auto; width: 100%;
    }}
    .class-chip {{
      display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
      border: 1px solid var(--color-border, #2e2e42); background: var(--color-surface, #18181f);
      color: var(--color-text, #f4f4f5); font-size: 12px; cursor: pointer; user-select: none;
    }}
    .class-chip .swatch {{ width: 10px; height: 10px; border-radius: 50%; }}
    .class-chip.active {{ border-color: {primary}; color: {primary}; }}
    .class-chip.dim {{ opacity: 0.45; }}
    .class-filter-bar {{
      display: flex; flex-wrap: wrap; gap: 8px; align-items: center; width: 100%;
      padding: 0 4px; margin-bottom: 4px;
    }}
    .class-filter-bar .hint {{ font-size: 12px; color: #71717a; }}
    input[type="file"] {{ display: none; }}
    @media (max-width: 640px) {{
      .mode-nav {{ padding: 8px 12px; justify-content: flex-start; }}
      .mode-tab {{ padding: 8px 12px; font-size: 13px; }}
      .site-main {{ padding: 16px !important; }}
    }}
"""


def _normalize_class_entities(
    labels: List[str],
    class_entities: Optional[List[Dict[str, Any]]] = None,
    display_names: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    display_names = display_names or {}
    if class_entities:
        out = []
        for idx, ent in enumerate(class_entities):
            if not isinstance(ent, dict):
                continue
            name = str(ent.get('name') or ent.get('filter_key') or '').strip()
            if not name:
                continue
            out.append({
                'id': ent.get('id') or f'cls_{idx}',
                'name': name,
                'display_name': ent.get('display_name') or display_names.get(name) or name.replace('_', ' '),
                'filter_key': ent.get('filter_key') or name,
                'color_index': int(ent.get('color_index') if ent.get('color_index') is not None else idx % 6),
            })
        if out:
            return out
    names = labels or ['目标1', '目标2', '目标3']
    return [
        {
            'id': f'cls_{i}',
            'name': n,
            'display_name': display_names.get(n) or n.replace('_', ' '),
            'filter_key': n,
            'color_index': i % 6,
        }
        for i, n in enumerate(names)
    ]


def build_detection_index_html(
    title: str,
    subtitle: str,
    primary: str,
    upload_hint: str,
    labels: List[str],
    disclaimer_html: str = '',
    class_entities: Optional[List[Dict[str, Any]]] = None,
    display_names: Optional[Dict[str, str]] = None,
) -> str:
    modern_css = get_modern_css_block().replace('--site-primary, #f59e0b', primary)
    entities = _normalize_class_entities(labels, class_entities, display_names)
    labels_for_json = [e['name'] for e in entities] or (labels or ['目标1', '目标2', '目标3'])
    labels_json = json.dumps(labels_for_json, ensure_ascii=False).replace('</', '<\\/')
    entities_json = json.dumps(entities, ensure_ascii=False).replace('</', '<\\/')
    safe_title = html.escape(title or 'AI 识别系统')
    safe_subtitle = html.escape(subtitle or 'AI-powered recognition service')
    safe_upload_hint = html.escape(upload_hint or '点击或拖拽上传图片进行识别')

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>{safe_title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    :root {{ --site-primary: {primary}; --color-primary: {primary}; }}
{modern_css}
{build_detection_extra_css(primary)}
    .header, .site-header {{ padding: 24px 40px; border-bottom: 1px solid var(--color-border, #2e2e42); }}
    .header h1, .site-header h1 {{ font-size: 24px; font-weight: 700; color: {primary}; }}
    .header p, .site-header p {{ color: var(--color-text-muted, #a1a1aa); font-size: 14px; margin-top: 4px; }}
    .site-main {{ flex: 1; padding: 24px 40px 40px; display: flex; flex-direction: column; align-items: center; gap: 20px; max-width: 1100px; margin: 0 auto; width: 100%; }}
  </style>
</head>
<body>
  <div id="app" class="app-layout">
    <header class="site-header">
      <h1>{safe_title}</h1>
      <p>{safe_subtitle}</p>
    </header>
    <div class="class-legend" aria-label="训练类别图例">
      <button
        v-for="ent in classEntities"
        :key="ent.id"
        type="button"
        class="class-chip"
        :class="{{ active: isFilterActive(ent.filter_key), dim: activeFilters.length && !isFilterActive(ent.filter_key) }}"
        @click="toggleFilter(ent.filter_key)"
      >
        <span class="swatch" :style="{{ background: COLORS[ent.color_index % COLORS.length] }}"></span>
        {{{{ ent.display_name }}}}
      </button>
    </div>
    <nav class="mode-nav" role="tablist" aria-label="识别模式">
      <button class="mode-tab" :class="{{ active: mode === 'image' }}" role="tab" :aria-selected="mode==='image'" @click="setMode('image')">图片识别</button>
      <button class="mode-tab" :class="{{ active: mode === 'video' }}" role="tab" :aria-selected="mode==='video'" @click="setMode('video')">视频识别</button>
      <button class="mode-tab" :class="{{ active: mode === 'realtime' }}" role="tab" :aria-selected="mode==='realtime'" @click="setMode('realtime')">实时识别</button>
      <button class="mode-tab" :class="{{ active: mode === 'fact' }}" role="tab" :aria-selected="mode==='fact'" @click="setMode('fact')">事实识别</button>
      <button class="mode-tab" :class="{{ active: mode === 'history' }}" role="tab" :aria-selected="mode==='history'" @click="setMode('history')">历史记录</button>
    </nav>
    <main class="site-main">
      <section class="panel" :class="{{ active: mode === 'image' }}" role="tabpanel">
        <div class="class-filter-bar">
          <span class="hint">类别筛选（点击图例切换，空=全部）</span>
          <button type="button" class="btn btn-secondary" style="min-height:32px;padding:4px 12px;font-size:12px" @click="clearFilters">清除筛选</button>
        </div>
        <div class="upload-zone" :class="{{ dragover: isDragover }}" @click="$refs.imageInput.click()" @dragover.prevent="isDragover=true" @dragleave="isDragover=false" @drop.prevent="onImageDrop">
          <input type="file" ref="imageInput" accept="image/*" @change="onImageSelect" />
          <p>{safe_upload_hint}</p>
          <p class="hint" style="font-size:12px;margin-top:8px;color:#71717a">支持 JPG、PNG、WEBP · 已学习 {{{{ classEntities.length }}}} 个类别</p>
        </div>
        <div v-if="imageUrl" class="result-panel" style="width:100%">
          <div class="media-stage">
            <img :src="imageUrl" ref="imageEl" @load="drawImageBoxes" alt="待识别图片" />
            <canvas ref="imageCanvas"></canvas>
          </div>
          <div v-if="imageLoading" class="loading">正在识别图片...</div>
          <template v-else-if="filteredImageDetections.length">
            <div class="detection-stats"><div class="stat-item"><span class="stat-value">{{{{ filteredImageDetections.length }}}}</span><span class="stat-label">检测到目标</span></div>
            <div class="stat-item" v-if="imageDetections.length !== filteredImageDetections.length"><span class="stat-value">{{{{ imageDetections.length }}}}</span><span class="stat-label">筛选前</span></div></div>
            <div class="detection-list"><div v-for="(d,i) in filteredImageDetections" :key="i" class="detection-item">
              <span class="detection-label">{{{{ displayLabel(d.label) }}}}</span><div class="confidence-bar"><div class="confidence-fill" :style="{{ width: (d.confidence*100)+'%' }}"></div></div>
              <span style="font-size:13px;color:#a1a1aa">{{{{ (d.confidence*100).toFixed(1) }}}}%</span>
            </div></div>
          </template>
          <div v-else-if="imageError" style="color:#ef4444;padding:16px;text-align:center">{{{{ imageError }}}}</div>
          <div v-else-if="imageDetections.length" class="empty-state">当前筛选下无匹配目标</div>
        </div>
      </section>

      <section class="panel" :class="{{ active: mode === 'video' }}" role="tabpanel">
        <div class="upload-zone video" @click="$refs.videoInput.click()">
          <input type="file" ref="videoInput" accept="video/*" @change="onVideoSelect" />
          <p>上传视频进行逐帧目标检测</p>
          <p class="hint" style="font-size:12px;margin-top:8px;color:#71717a">支持 MP4、WEBM、MOV</p>
        </div>
        <div v-if="videoUrl" class="result-panel" style="width:100%">
          <div class="media-stage">
            <video :src="videoUrl" ref="videoEl" controls @loadedmetadata="onVideoMeta"></video>
            <canvas ref="videoCanvas"></canvas>
          </div>
          <div class="toolbar">
            <button class="btn btn-primary" :disabled="videoLoading" @click="analyzeVideo">{{{{ videoLoading ? '分析中...' : '开始视频分析' }}}}</button>
            <span v-if="videoFrames.length" class="status-pill">已分析 {{{{ videoFrames.length }}}} 帧</span>
          </div>
          <div v-if="videoLoading" class="loading">正在逐帧识别视频...</div>
          <template v-else-if="currentVideoFrame">
            <div class="detection-stats"><div class="stat-item"><span class="stat-value">{{{{ currentVideoFrame.boxes.length }}}}</span><span class="stat-label">当前帧目标</span></div>
            <div class="stat-item"><span class="stat-value">{{{{ currentVideoFrame.time_sec.toFixed(1) }}}}s</span><span class="stat-label">时间戳</span></div></div>
            <div class="detection-list"><div v-for="(d,i) in currentVideoFrame.boxes" :key="i" class="detection-item">
              <span class="detection-label">{{{{ d.label }}}}</span><div class="confidence-bar"><div class="confidence-fill" :style="{{ width: (d.confidence*100)+'%' }}"></div></div>
              <span style="font-size:13px;color:#a1a1aa">{{{{ (d.confidence*100).toFixed(1) }}}}%</span>
            </div></div>
          </template>
        </div>
      </section>

      <section class="panel" :class="{{ active: mode === 'realtime' }}" role="tabpanel">
        <div class="toolbar">
          <button class="btn btn-primary" @click="toggleCamera">{{{{ cameraOn ? '停止摄像头' : '开启摄像头' }}}}</button>
          <span class="status-pill"><span class="status-dot" :class="{{ live: cameraOn }}"></span>{{{{ cameraOn ? '实时识别中' : '摄像头未开启' }}}}</span>
          <span v-if="realtimeFps" class="status-pill">{{{{ realtimeFps }}}} FPS</span>
        </div>
        <div class="result-panel" style="width:100%">
          <div class="media-stage" style="min-height:320px">
            <video ref="cameraEl" autoplay playsinline muted style="width:100%"></video>
            <canvas ref="cameraCanvas"></canvas>
          </div>
          <div v-if="!cameraOn" class="empty-state">点击“开启摄像头”开始实时目标检测</div>
          <template v-else-if="realtimeDetections.length">
            <div class="detection-stats"><div class="stat-item"><span class="stat-value">{{{{ realtimeDetections.length }}}}</span><span class="stat-label">当前画面目标</span></div></div>
            <div class="detection-list"><div v-for="(d,i) in realtimeDetections" :key="i" class="detection-item">
              <span class="detection-label">{{{{ d.label }}}}</span><div class="confidence-bar"><div class="confidence-fill" :style="{{ width: (d.confidence*100)+'%' }}"></div></div>
              <span style="font-size:13px;color:#a1a1aa">{{{{ (d.confidence*100).toFixed(1) }}}}%</span>
            </div></div>
          </template>
        </div>
      </section>

      <section class="panel" :class="{{ active: mode === 'history' }}" role="tabpanel">
        <div class="toolbar">
          <button class="btn btn-secondary" @click="loadHistory">刷新记录</button>
          <span class="status-pill">共 {{{{ historyItems.length }}}} 条</span>
        </div>
        <div v-if="historyLoading" class="loading">加载历史记录...</div>
        <div v-else-if="!historyItems.length" class="empty-state">暂无识别记录，完成一次图片、视频或实时识别后将自动保存</div>
        <div v-else class="history-grid">
          <article v-for="item in historyItems" :key="item.id" class="history-card" @click="selectHistory(item)">
            <h4><span class="mode-badge">{{{{ modeLabel(item.mode) }}}}</span> {{{{ item.input_summary }}}}</h4>
            <div class="history-meta">
              <span>{{{{ formatTime(item.created_at) }}}}</span>
              <span>{{{{ item.output_summary }}}}</span>
              <span v-if="item.latency_ms">{{{{ item.latency_ms.toFixed(0) }}}} ms</span>
            </div>
          </article>
        </div>
        <div v-if="selectedHistory" class="result-panel" style="width:100%;margin-top:12px;padding:16px">
          <h3 style="margin-bottom:12px;font-size:16px">记录详情 #{{{{ selectedHistory.id }}}}</h3>
          <pre style="font-size:12px;color:#a1a1aa;white-space:pre-wrap;word-break:break-all">{{{{ JSON.stringify(selectedHistory.detections || [], null, 2) }}}}</pre>
        </div>
      </section>

      <section class="panel" :class="{{ active: mode === 'fact' }}" role="tabpanel">
        <div class="result-panel" style="width:100%;padding:20px">
          <h3 style="margin-bottom:12px;font-size:18px;color:{primary}">事实识别</h3>
          <p style="margin-bottom:14px;color:#a1a1aa;font-size:13px">基于当前模型标签、模型信息和最近识别历史，对用户输入的判断进行一致性检查并保存依据记录。</p>
          <textarea v-model="factClaim" rows="4" style="width:100%;resize:vertical;border-radius:8px;border:1px solid #2e2e42;background:#0f0f14;color:#f4f4f5;padding:12px" placeholder="输入需要核查的事实、识别结论或业务规则"></textarea>
          <div class="toolbar" style="margin-top:12px">
            <button class="btn btn-primary" :disabled="factLoading || !factClaim.trim()" @click="runFactCheck">{{{{ factLoading ? '核查中...' : '开始核查' }}}}</button>
            <button class="btn btn-secondary" @click="loadFactHistory">刷新记录</button>
          </div>
          <div v-if="factLoading" class="loading">正在进行事实一致性检查...</div>
          <div v-if="factResult" class="history-card" style="margin-top:14px">
            <h4>{{{{ factResult.verdict }}}} - {{{{ Math.round((factResult.confidence || 0) * 100) }}}}%</h4>
            <div class="history-meta">
              <span v-for="(line, idx) in factResult.evidence" :key="idx">{{{{ line }}}}</span>
            </div>
          </div>
          <div v-if="factHistory.length" class="history-grid" style="margin-top:16px">
            <article v-for="item in factHistory" :key="item.id" class="history-card">
              <h4>{{{{ item.verdict }}}}</h4>
              <div class="history-meta">
                <span>{{{{ item.claim }}}}</span>
                <span>{{{{ formatTime(item.created_at) }}}}</span>
              </div>
            </article>
          </div>
        </div>
      </section>
    </main>
    {disclaimer_html}
  </div>
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
  <script src="https://unpkg.com/axios@1.6.0/dist/axios.min.js"></script>
  <script>
    const {{ createApp, ref, computed, watch, onUnmounted, nextTick }} = Vue
    const LABELS = {labels_json}
    const CLASS_ENTITIES = {entities_json}
    const COLORS = ['{primary}', '#10b981', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899']
    const MODE_LABELS = {{ image: '图片', video: '视频', realtime: '实时', fact: '事实', history: '历史' }}
    const DISPLAY_MAP = Object.fromEntries(CLASS_ENTITIES.map(e => [e.name, e.display_name]))

    createApp({{
      setup() {{
        const mode = ref('image')
        const isDragover = ref(false)
        const classEntities = ref(CLASS_ENTITIES)
        const activeFilters = ref([])
        const imageUrl = ref(''); const imageLoading = ref(false); const imageDetections = ref([]); const imageError = ref('')
        const imageEl = ref(null); const imageCanvas = ref(null)
        const videoUrl = ref(''); const videoLoading = ref(false); const videoFrames = ref([]); const videoInput = ref(null); const videoEl = ref(null); const videoCanvas = ref(null)
        const currentVideoFrame = computed(() => videoFrames.value.length ? videoFrames.value[videoFrames.value.length - 1] : null)
        const cameraOn = ref(false); const cameraEl = ref(null); const cameraCanvas = ref(null)
        const realtimeDetections = ref([]); const realtimeFps = ref(0); let cameraStream = null; let realtimeTimer = null; let frameCount = 0; let lastFpsTs = Date.now()
        const historyItems = ref([]); const historyLoading = ref(false); const selectedHistory = ref(null)
        const factClaim = ref(''); const factLoading = ref(false); const factResult = ref(null); const factHistory = ref([])

        function displayLabel(label) {{ return DISPLAY_MAP[label] || label }}
        function isFilterActive(key) {{ return activeFilters.value.includes(key) }}
        function toggleFilter(key) {{
          const i = activeFilters.value.indexOf(key)
          if (i >= 0) activeFilters.value = activeFilters.value.filter(k => k !== key)
          else activeFilters.value = [...activeFilters.value, key]
          drawImageBoxes()
        }}
        function clearFilters() {{ activeFilters.value = []; drawImageBoxes() }}
        function filterBoxes(boxes) {{
          if (!activeFilters.value.length) return boxes || []
          return (boxes || []).filter(d => activeFilters.value.includes(d.label))
        }}
        const filteredImageDetections = computed(() => filterBoxes(imageDetections.value))

        function setMode(m) {{
          mode.value = m
          if (m === 'history') loadHistory()
          if (m === 'fact') loadFactHistory()
          if (m !== 'realtime' && cameraOn.value) stopCamera()
        }}

        function drawBoxes(canvas, mediaEl, boxes) {{
          if (!canvas || !mediaEl) return
          const w = mediaEl.videoWidth || mediaEl.naturalWidth || mediaEl.clientWidth
          const h = mediaEl.videoHeight || mediaEl.naturalHeight || mediaEl.clientHeight
          if (!w || !h) return
          canvas.width = w; canvas.height = h
          const ctx = canvas.getContext('2d')
          ctx.clearRect(0, 0, w, h)
          ;(filterBoxes(boxes) || []).forEach((det, i) => {{
            const ent = CLASS_ENTITIES.find(e => e.name === det.label)
            const color = COLORS[(ent ? ent.color_index : i) % COLORS.length]
            const x1 = det.x1 * w, y1 = det.y1 * h, x2 = det.x2 * w, y2 = det.y2 * h
            ctx.strokeStyle = color; ctx.fillStyle = color + '33'; ctx.lineWidth = 3
            ctx.fillRect(x1, y1, x2-x1, y2-y1); ctx.strokeRect(x1, y1, x2-x1, y2-y1)
            const label = displayLabel(det.label) + ' ' + (det.confidence * 100).toFixed(0) + '%'
            ctx.font = 'bold 14px sans-serif'
            const tw = ctx.measureText(label).width + 8
            ctx.fillStyle = color; ctx.fillRect(x1, Math.max(0, y1-22), tw, 22)
            ctx.fillStyle = '#000'; ctx.fillText(label, x1+4, y1-6)
          }})
        }}

        function drawImageBoxes() {{ nextTick(() => drawBoxes(imageCanvas.value, imageEl.value, imageDetections.value)) }}

        async function runPredict(file, endpoint, extra) {{
          const fd = new FormData()
          fd.append('file', file)
          if (extra) Object.entries(extra).forEach(([k,v]) => fd.append(k, v))
          const r = await axios.post(endpoint, fd, {{ headers: {{ 'Content-Type': 'multipart/form-data' }} }})
          return r.data
        }}

        function onImageSelect(e) {{ const f = e.target.files[0]; if (f) processImage(f) }}
        function onImageDrop(e) {{ isDragover.value = false; const f = e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) processImage(f) }}

        async function processImage(file) {{
          imageUrl.value = URL.createObjectURL(file)
          imageLoading.value = true; imageDetections.value = []; imageError.value = ''
          try {{
            const data = await runPredict(file, '/predict', {{ mode: 'image' }})
            imageDetections.value = data.boxes || []
            drawImageBoxes()
          }} catch (e) {{
            imageError.value = (e.response?.data?.error) || e.message || '识别失败'
          }} finally {{ imageLoading.value = false }}
        }}

        function onVideoSelect(e) {{
          const f = e.target.files[0]
          if (!f) return
          videoUrl.value = URL.createObjectURL(f)
          videoFrames.value = []
        }}
        function onVideoMeta() {{ drawBoxes(videoCanvas.value, videoEl.value, []) }}

        async function analyzeVideo() {{
          const file = videoInput.value?.files?.[0]
          if (!file) return
          videoLoading.value = true; videoFrames.value = []
          try {{
            const data = await runPredict(file, '/predict/video', {{ mode: 'video' }})
            videoFrames.value = data.frames || []
            if (videoFrames.value.length && videoEl.value) {{
              const last = videoFrames.value[videoFrames.value.length - 1]
              drawBoxes(videoCanvas.value, videoEl.value, last.boxes)
            }}
          }} catch (e) {{ alert((e.response?.data?.error) || '视频分析失败') }}
          finally {{ videoLoading.value = false }}
        }}

        async function captureRealtimeFrame() {{
          const video = cameraEl.value
          const canvas = document.createElement('canvas')
          if (!video || !video.videoWidth) return
          canvas.width = video.videoWidth; canvas.height = video.videoHeight
          canvas.getContext('2d').drawImage(video, 0, 0)
          const blob = await new Promise(res => canvas.toBlob(res, 'image/jpeg', 0.85))
          const fd = new FormData()
          fd.append('file', blob, 'frame.jpg')
          fd.append('mode', 'realtime')
          try {{
            const r = await axios.post('/predict', fd)
            realtimeDetections.value = r.data.boxes || []
            drawBoxes(cameraCanvas.value, video, realtimeDetections.value)
            frameCount++
            const now = Date.now()
            if (now - lastFpsTs >= 1000) {{ realtimeFps.value = frameCount; frameCount = 0; lastFpsTs = now }}
          }} catch (_) {{}}
        }}

        async function toggleCamera() {{
          if (cameraOn.value) {{ stopCamera(); return }}
          try {{
            cameraStream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'environment' }}, audio: false }})
            cameraEl.value.srcObject = cameraStream
            await cameraEl.value.play()
            cameraOn.value = true
            realtimeTimer = setInterval(captureRealtimeFrame, 600)
          }} catch (e) {{ alert('无法访问摄像头: ' + (e.message || e)) }}
        }}

        function stopCamera() {{
          cameraOn.value = false
          if (realtimeTimer) {{ clearInterval(realtimeTimer); realtimeTimer = null }}
          if (cameraStream) {{ cameraStream.getTracks().forEach(t => t.stop()); cameraStream = null }}
          realtimeDetections.value = []; realtimeFps.value = 0
          drawBoxes(cameraCanvas.value, cameraEl.value, [])
        }}

        async function loadHistory() {{
          historyLoading.value = true; selectedHistory.value = null
          try {{
            const r = await axios.get('/api/history?limit=50')
            historyItems.value = r.data.items || []
          }} catch (e) {{ historyItems.value = [] }}
          finally {{ historyLoading.value = false }}
        }}

        async function selectHistory(item) {{
          try {{
            const r = await axios.get('/api/history/' + item.id)
            selectedHistory.value = r.data
          }} catch (e) {{ selectedHistory.value = item }}
        }}

        async function runFactCheck() {{
          if (!factClaim.value.trim()) return
          factLoading.value = true
          try {{
            const r = await axios.post('/api/fact-check', {{ claim: factClaim.value, source_mode: mode.value, labels: LABELS }})
            factResult.value = r.data
            await loadFactHistory()
          }} catch (e) {{
            factResult.value = {{ verdict: 'error', confidence: 0, evidence: [(e.response?.data?.error) || e.message || '事实识别失败'] }}
          }} finally {{ factLoading.value = false }}
        }}

        async function loadFactHistory() {{
          try {{
            const r = await axios.get('/api/fact-checks?limit=20')
            factHistory.value = r.data.items || []
          }} catch (e) {{ factHistory.value = [] }}
        }}

        function modeLabel(m) {{ return MODE_LABELS[m] || m || '未知' }}
        function formatTime(ts) {{
          if (!ts) return ''
          try {{ return new Date(ts).toLocaleString('zh-CN') }} catch {{ return ts }}
        }}

        onUnmounted(() => stopCamera())
        watch(mode, (m) => {{ if (m === 'history') loadHistory(); if (m === 'fact') loadFactHistory() }})
        watch(activeFilters, () => drawImageBoxes(), {{ deep: true }})

        return {{
          mode, setMode, isDragover, imageUrl, imageLoading, imageDetections, filteredImageDetections, imageError, imageEl, imageCanvas,
          onImageSelect, onImageDrop, drawImageBoxes, videoUrl, videoLoading, videoFrames, videoInput, videoEl, videoCanvas,
          onVideoSelect, onVideoMeta, analyzeVideo, currentVideoFrame, cameraOn, cameraEl, cameraCanvas,
          realtimeDetections, realtimeFps, toggleCamera, historyItems, historyLoading, selectedHistory,
          loadHistory, selectHistory, factClaim, factLoading, factResult, factHistory,
          runFactCheck, loadFactHistory, modeLabel, formatTime,
          classEntities, activeFilters, toggleFilter, clearFilters, isFilterActive, displayLabel, COLORS
        }}
      }}
    }}).mount('#app')
  </script>
</body>
</html>
"""


def build_detection_backend_extensions() -> str:
    """Python helpers appended to generated detection app.py via backend agent or generator."""
    return '''

# --- Flowly detection extensions: video / fact / history ---
HISTORY_DIR = os.path.join(os.path.dirname(__file__), 'data', 'history')
os.makedirs(HISTORY_DIR, exist_ok=True)


def _save_history_record(mode, input_summary, boxes, latency_ms):
    """Persist inference to DB with optional detections JSON."""
    try:
        from db.init_db import log_inference_extended
        log_inference_extended(mode, input_summary, boxes, latency_ms)
    except Exception:
        try:
            log_inference(input_summary, f'{len(boxes or [])} detections', latency_ms)
        except Exception:
            pass


def _run_detection_on_image(img):
    """Shared detection logic for image ndarray BGR."""
    orig_h, orig_w = img.shape[:2]
    if model is None:
        blob, scale, pad_x, pad_y = preprocess_image(img)
        boxes = postprocess_detections(None, scale, pad_x, pad_y, orig_w, orig_h)
    elif hasattr(model, 'predict'):
        boxes = []
        results = model.predict(source=img, conf=0.25, verbose=False)
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                xyxy = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                label = LABELS[cls_id] if cls_id < len(LABELS) else str(cls_id)
                boxes.append({
                    'x1': float(xyxy[0] / orig_w), 'y1': float(xyxy[1] / orig_h),
                    'x2': float(xyxy[2] / orig_w), 'y2': float(xyxy[3] / orig_h),
                    'label': label, 'confidence': round(conf, 4),
                })
    else:
        blob, scale, pad_x, pad_y = preprocess_image(img)
        import torch
        with torch.no_grad():
            outputs = model(torch.from_numpy(blob))
        boxes = postprocess_detections(outputs, scale, pad_x, pad_y, orig_w, orig_h)
    boxes.sort(key=lambda x: x['confidence'], reverse=True)
    return boxes


@app.route('/predict/video', methods=['POST'])
def predict_video():
    started = time.time()
    if 'file' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400
    tmp_path = os.path.join(HISTORY_DIR, f'upload_{int(time.time())}.mp4')
    file.save(tmp_path)
    frames_out = []
    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return jsonify({'error': 'Cannot open video'}), 400
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        step = max(1, int(fps // 2))
        max_samples = 30
        idx = 0
        sampled = 0
        while sampled < max_samples:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % step == 0:
                boxes = _run_detection_on_image(frame)
                time_sec = idx / fps
                frames_out.append({
                    'frame_index': idx,
                    'time_sec': round(time_sec, 2),
                    'boxes': boxes,
                })
                sampled += 1
            idx += 1
        cap.release()
        latency_ms = (time.time() - started) * 1000
        _save_history_record('video', file.filename, frames_out[-1]['boxes'] if frames_out else [], latency_ms)
        return jsonify({
            'frames': frames_out,
            'total_frames': total,
            'sampled': len(frames_out),
            'latency_ms': latency_ms,
        })
    except Exception as e:
        return jsonify({'error': f'Video detection failed: {str(e)}'}), 500
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.route('/api/history', methods=['GET'])
def api_history_list():
    limit = min(int(request.args.get('limit', 50)), 200)
    try:
        from db.init_db import list_inference_history
        items = list_inference_history(limit=limit)
    except Exception:
        items = []
    return jsonify({'items': items, 'count': len(items)})


@app.route('/api/history/<int:record_id>', methods=['GET'])
def api_history_detail(record_id):
    try:
        from db.init_db import get_inference_record
        row = get_inference_record(record_id)
        if not row:
            return jsonify({'error': 'Not found'}), 404
        return jsonify(row)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fact-check', methods=['POST'])
def api_fact_check():
    data = request.get_json(silent=True) or {}
    claim = str(data.get('claim') or '').strip()
    source_mode = str(data.get('source_mode') or 'manual').strip() or 'manual'
    if not claim:
        return jsonify({'error': 'claim is required'}), 400
    claim_l = claim.lower()
    label_hits = [label for label in LABELS if str(label).lower() in claim_l]
    evidence = []
    if label_hits:
        evidence.append('命中当前模型标签: ' + ', '.join(map(str, label_hits[:8])))
    else:
        evidence.append('未直接命中当前模型标签，需要人工或外部数据源复核')
    try:
        from db.init_db import list_inference_history
        recent = list_inference_history(limit=10)
    except Exception:
        recent = []
    if recent:
        evidence.append(f'参考最近 {len(recent)} 条识别历史记录')
    contradiction_terms = ['一定', '100%', '绝对', '全部', '从不', '永远']
    has_overclaim = any(term in claim for term in contradiction_terms)
    if has_overclaim:
        evidence.append('检测到绝对化表述，降低可信度')
    confidence = 0.72 if label_hits else 0.42
    if has_overclaim:
        confidence = min(confidence, 0.48)
    verdict = 'consistent' if confidence >= 0.65 else 'needs_review'
    try:
        from db.init_db import log_fact_check
        log_fact_check(claim, verdict, confidence, evidence, source_mode)
    except Exception:
        pass
    return jsonify({'claim': claim, 'verdict': verdict, 'confidence': confidence, 'evidence': evidence, 'source_mode': source_mode})


@app.route('/api/fact-checks', methods=['GET'])
def api_fact_checks():
    limit = min(int(request.args.get('limit', 50)), 200)
    try:
        from db.init_db import list_fact_checks
        items = list_fact_checks(limit=limit)
    except Exception:
        items = []
    return jsonify({'items': items, 'count': len(items)})
'''
