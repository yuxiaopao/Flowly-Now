<template>
  <div class="clip-ret-config">
    <el-form label-position="top" size="small">
      <el-form-item label="索引构建位置">
        <el-radio-group :model-value="config.indexMode || 'server'" @update:model-value="patch('indexMode', $event)">
          <el-radio value="server">服务端构建</el-radio>
          <el-radio value="desktop">Desktop 本地 GPU</el-radio>
        </el-radio-group>
        <p v-if="config.indexMode === 'desktop'" class="hint">
          在 Flowly Desktop 中执行工作流时，将使用本机 GPU 构建索引后再继续下游节点
        </p>
      </el-form-item>

      <el-form-item label="索引类型">
        <el-select :model-value="config.indexType || 'flat'" @update:model-value="patch('indexType', $event)">
          <el-option label="Flat（精确检索）" value="flat" />
          <el-option label="HNSW（近似，后续）" value="hnsw" disabled />
        </el-select>
      </el-form-item>

      <el-form-item label="嵌入模型">
        <el-select :model-value="config.baseModel || 'simple-bow'" @update:model-value="patch('baseModel', $event)">
          <el-option label="Simple BOW（轻量，默认）" value="simple-bow" />
          <el-option label="ViT-B/32 CLIP" value="ViT-B/32" />
        </el-select>
        <p class="hint">需上游 dataset_upload(format=image_text_pairs)</p>
      </el-form-item>

      <el-form-item label="输出目录">
        <el-input
          :model-value="config.outputDir || ''"
          placeholder="留空则使用 {dataset_path}/index"
          @update:model-value="patch('outputDir', $event)"
        />
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const config = computed(() => props.modelValue || {})

function patch(key, value) {
  const next = { ...props.modelValue, [key]: value }
  emit('update:modelValue', next)
  emit('change', next)
}
</script>

<style scoped>
.hint { margin: 4px 0 0; font-size: 12px; color: var(--text-secondary, #a1a1aa); }
</style>
