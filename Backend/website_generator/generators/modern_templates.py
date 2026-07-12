"""Modern scaffold templates for generated sites (Phase 3)."""

from __future__ import annotations

from typing import Any, Dict


def get_modern_css_block() -> str:
    return """
    :root {
      --color-primary: var(--site-primary, #f59e0b);
      --color-bg: #0f0f14;
      --color-surface: #18181f;
      --color-surface-elevated: #1f1f2e;
      --color-border: #2e2e42;
      --color-text: #f4f4f5;
      --color-text-muted: #a1a1aa;
      --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --space-md: 16px;
      --space-lg: 24px;
      --space-xl: 40px;
      --radius-md: 12px;
      --radius-lg: 16px;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: var(--font-family);
      background: var(--color-bg);
      color: var(--color-text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      line-height: 1.5;
    }
    .site-header {
      padding: var(--space-lg) var(--space-xl);
      border-bottom: 1px solid var(--color-border);
      background: linear-gradient(180deg, var(--color-surface-elevated) 0%, transparent 100%);
    }
    .site-header h1 { font-size: 1.5rem; font-weight: 700; color: var(--color-primary); }
    .site-header p { color: var(--color-text-muted); font-size: 0.875rem; margin-top: 4px; }
    .site-main {
      flex: 1;
      padding: var(--space-xl);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--space-lg);
      max-width: 960px;
      margin: 0 auto;
      width: 100%;
    }
    .upload-zone {
      width: 100%;
      border: 2px dashed var(--color-border);
      border-radius: var(--radius-lg);
      padding: 3rem 2rem;
      text-align: center;
      cursor: pointer;
      transition: border-color 0.2s, background 0.2s;
    }
    .upload-zone:hover, .upload-zone.dragover {
      border-color: var(--color-primary);
      background: color-mix(in srgb, var(--color-primary) 8%, transparent);
    }
    .upload-zone p { color: var(--color-text-muted); }
    .result-panel {
      width: 100%;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-lg);
      overflow: hidden;
    }
    @media (max-width: 640px) {
      .site-main { padding: var(--space-md); }
      .site-header { padding: var(--space-md); }
    }
    @media (prefers-reduced-motion: reduce) {
      .upload-zone { transition: none; }
    }
"""


def build_vue_app_vue(title: str, subtitle: str, upload_hint: str, api_path: str = '/predict') -> str:
    return f"""<template>
  <div class="app-shell">
    <header class="site-header">
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </header>
    <main class="site-main">
      <UploadZone :hint="uploadHint" @file-selected="onFile" />
      <ResultPanel v-if="result" :result="result" />
    </main>
  </div>
</template>

<script setup>
import {{ ref }} from 'vue'
import UploadZone from './components/UploadZone.vue'
import ResultPanel from './components/ResultPanel.vue'

const uploadHint = '{upload_hint}'
const result = ref(null)

async function onFile(file) {{
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('{api_path}', {{ method: 'POST', body: form }})
  result.value = await res.json()
}}
</script>

<style>
@import './styles/theme.css';
</style>
"""


def build_upload_zone_component(hint: str) -> str:
    return f"""<template>
  <div
    class="upload-zone"
    role="button"
    tabindex="0"
    aria-label="上传文件"
    @click="pick"
    @keydown.enter="pick"
    @dragover.prevent="drag = true"
    @dragleave="drag = false"
    @drop.prevent="onDrop"
    :class="{{ dragover: drag }}"
  >
    <p>{{ hint }}</p>
    <p class="hint">支持 JPG / PNG</p>
    <input ref="input" type="file" accept="image/*" hidden @change="onChange" />
  </div>
</template>

<script setup>
import {{ ref }} from 'vue'
defineProps({{ hint: {{ type: String, default: '{hint}' }} }})
const emit = defineEmits(['file-selected'])
const input = ref(null)
const drag = ref(false)
function pick() {{ input.value?.click() }}
function onChange(e) {{
  const f = e.target.files?.[0]
  if (f) emit('file-selected', f)
}}
function onDrop(e) {{
  drag.value = false
  const f = e.dataTransfer.files?.[0]
  if (f) emit('file-selected', f)
}}
</script>

<style scoped>
.upload-zone {{ width: 100%; border: 2px dashed var(--color-border, #2e2e42); border-radius: 12px; padding: 3rem; text-align: center; cursor: pointer; }}
.upload-zone.dragover {{ border-color: var(--color-primary, #f59e0b); }}
.hint {{ font-size: 12px; margin-top: 8px; color: var(--color-text-muted, #71717a); }}
</style>
"""


def build_result_panel_component() -> str:
    return """<template>
  <div class="result-panel">
    <pre>{{ JSON.stringify(result, null, 2) }}</pre>
  </div>
</template>

<script setup>
defineProps({ result: { type: Object, default: null } })
</script>

<style scoped>
.result-panel { padding: 1rem; background: var(--color-surface, #18181f); border-radius: 12px; overflow: auto; }
pre { font-size: 13px; color: var(--color-text-muted, #a1a1aa); }
</style>
"""


def build_main_js() -> str:
    return """import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
"""


def build_theme_css(tokens_css: str = '') -> str:
    base = tokens_css or get_modern_css_block()
    return base + """
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
"""


def build_index_html_shell(title: str, subtitle: str, primary: str, upload_hint: str, body_extra: str = '') -> str:
    css = get_modern_css_block().replace('--site-primary, #f59e0b', primary)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    :root {{ --site-primary: {primary}; }}
{css}
  </style>
</head>
<body>
  <header class="site-header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
  </header>
  <main class="site-main">
    <div class="upload-zone" id="uploadZone" role="button" tabindex="0" aria-label="上传图片">
      <p>{upload_hint}</p>
      <p style="font-size:12px;margin-top:8px;color:var(--color-text-muted)">支持 JPG / PNG</p>
    </div>
    <div class="result-panel" id="resultPanel" hidden></div>
  </main>
  {body_extra}
</body>
</html>
"""
