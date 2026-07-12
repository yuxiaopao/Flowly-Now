<template>
  <div class="config-form webhook-trigger-config">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <div class="form-section">
        <h4 class="section-title">
          基本信息
        </h4>
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            placeholder="输入节点名称"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          Webhook 配置
        </h4>
        
        <el-form-item label="HTTP 方法">
          <el-select
            v-model="localData.method"
            placeholder="选择 HTTP 方法"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="GET"
              value="GET"
            />
            <el-option
              label="POST"
              value="POST"
            />
            <el-option
              label="PUT"
              value="PUT"
            />
            <el-option
              label="PATCH"
              value="PATCH"
            />
            <el-option
              label="DELETE"
              value="DELETE"
            />
            <el-option
              label="ANY (任意方法)"
              value="ANY"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="路径">
          <el-input
            v-model="localData.path"
            placeholder="/webhook/my-endpoint"
            @change="handleChange"
          >
            <template #prepend>
              /
            </template>
          </el-input>
          <div class="field-hint">
            Webhook 访问路径，不能包含空格和特殊字符
          </div>
        </el-form-item>

        <el-form-item label="认证方式">
          <el-select
            v-model="localData.auth"
            placeholder="选择认证方式"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="无认证"
              value="none"
            />
            <el-option
              label="Bearer Token"
              value="bearer"
            />
            <el-option
              label="API Key"
              value="api_key"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="localData.auth === 'bearer'"
          label="Token"
        >
          <el-input
            v-model="localData.bearerToken"
            type="password"
            placeholder="Bearer Token"
            show-password
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.auth === 'api_key'"
          label="API Key"
        >
          <el-input
            v-model="localData.apiKey"
            type="password"
            placeholder="API Key"
            show-password
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          响应配置
        </h4>
        
        <el-form-item label="响应模式">
          <el-select
            v-model="localData.responseMode"
            placeholder="选择响应模式"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="最后一个节点输出"
              value="last"
            />
            <el-option
              label="所有节点输出"
              value="all"
            />
          </el-select>
          <div class="field-hint">
            工作流执行完成后返回给 webhook 调用者的响应内容
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">完整路径</span>
            <span class="preview-value">/api/webhooks{{ localData.path || '/example' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">方法</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ localData.method || 'POST' }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">认证</span>
            <el-tag size="small">
              {{ localData.auth === 'none' ? '无' : localData.auth }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: 'Webhook 触发器',
  method: 'POST',
  path: 'my-webhook',
  auth: 'none',
  bearerToken: '',
  apiKey: '',
  responseMode: 'last'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || 'Webhook 触发器',
      method: newVal.method || 'POST',
      path: newVal.path || 'my-webhook',
      auth: newVal.auth || 'none',
      bearerToken: newVal.bearerToken || '',
      apiKey: newVal.apiKey || '',
      responseMode: newVal.responseMode || 'last'
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.config-form {
  padding: 0;
}

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.config-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.preview-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
  }

  .preview-value {
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}
</style>
