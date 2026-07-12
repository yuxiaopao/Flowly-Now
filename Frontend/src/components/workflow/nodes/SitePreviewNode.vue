<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="site_preview"
    :show-iframe="canShowIframe"
    :enable-desktop-preview="true"
    :output-dir="outputDir"
    :preview-port="previewPort"
    :site-id="siteId"
    :blocked="isBlocked"
  />
</template>

<script setup>
import { computed } from 'vue'
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const nodeOutput = computed(() => props.data.output || props.data.result || {})
const gate = computed(() => nodeOutput.value.gate || nodeOutput.value.qa_gate || nodeOutput.value.qaGate || '')
const isBlocked = computed(() => gate.value === 'red' || nodeOutput.value.status === 'blocked')

const outputDir = computed(() => (
  nodeOutput.value.output_dir
  || nodeOutput.value.outputDir
  || props.data.config?.outputDir
  || ''
))

const previewPort = computed(() => {
  const p = nodeOutput.value.assigned_port || nodeOutput.value.port || props.data.config?.port
  return p ? Number(p) : null
})

const siteId = computed(() => (
  nodeOutput.value.site_id
  || nodeOutput.value.siteId
  || props.data.config?.generatedSiteId
  || ''
))

const canShowIframe = computed(() => !isBlocked.value && Boolean(
  nodeOutput.value.preview_url
  || nodeOutput.value.previewUrl
  || outputDir.value,
))
</script>
