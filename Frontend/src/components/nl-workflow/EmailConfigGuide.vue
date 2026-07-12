<template>
  <div
    class="email-config-guide"
    :class="{ expanded: isExpanded }"
  >
    <div
      class="guide-header"
      @click="toggle"
    >
      <div class="guide-title">
        <Mail class="guide-icon" />
        <span class="guide-label">邮件配置提醒</span>
      </div>
      <div class="guide-actions">
        <el-tag
          v-if="configStatus === 'complete'"
          size="small"
          type="success"
          class="guide-tag"
        >
          已配置
        </el-tag>
        <el-tag
          v-else-if="configStatus === 'partial'"
          size="small"
          type="warning"
          class="guide-tag"
        >
          部分配置
        </el-tag>
        <el-tag
          v-else
          size="small"
          type="danger"
          class="guide-tag"
        >
          需要配置
        </el-tag>
        <button class="toggle-btn">
          <ChevronDown
            class="toggle-icon"
            :class="{ rotated: isExpanded }"
          />
        </button>
      </div>
    </div>

    <Transition name="slide">
      <div
        v-if="isExpanded"
        class="guide-body"
      >
        <p class="guide-desc">
          {{ guidance.description }}
        </p>

        <!-- Warning banner if SMTP not configured -->
        <div
          v-if="guidance.warning"
          class="warning-banner"
        >
          <AlertTriangle class="warning-icon" />
          <span>{{ guidance.warning }}</span>
        </div>

        <!-- Missing fields list -->
        <div
          v-if="guidance.missing_fields && guidance.missing_fields.length > 0"
          class="missing-fields"
        >
          <div class="section-label">
            <AlertCircle class="section-icon" />
            必填字段缺失 ({{ guidance.missing_fields.length }})
          </div>
          <ul class="missing-list">
            <li
              v-for="field in guidance.missing_fields"
              :key="field"
              class="missing-item"
            >
              {{ field }}
            </li>
          </ul>
        </div>

        <!-- Step-by-step configuration guide -->
        <div class="config-steps">
          <div class="section-label">
            <Settings class="section-icon" />
            配置步骤
          </div>
          <div class="steps-list">
            <div
              v-for="(item, idx) in guidance.items"
              :key="item.field"
              class="step-item"
              :class="{ completed: isFieldConfigured(item.field) }"
            >
              <div class="step-number">
                {{ idx + 1 }}
              </div>
              <div class="step-content">
                <div class="item-header">
                  <span class="item-field">{{ item.field }}</span>
                  <el-tag
                    v-if="item.required"
                    size="small"
                    type="danger"
                    class="required-tag"
                  >
                    必填
                  </el-tag>
                  <el-tag
                    v-else
                    size="small"
                    type="info"
                    class="optional-tag"
                  >
                    可选
                  </el-tag>
                  <span
                    v-if="isFieldConfigured(item.field)"
                    class="check-mark"
                  >
                    <CheckCircle class="check-icon" />
                  </span>
                </div>
                <div class="item-tip">
                  <template
                    v-for="(line, lineIdx) in item.tip.split('\n')"
                    :key="lineIdx"
                  >
                    {{ line }}
                    <br v-if="lineIdx < item.tip.split('\n').length - 1">
                  </template>
                </div>
                <div
                  v-if="item.example"
                  class="item-example"
                >
                  <span class="example-label">示例:</span>
                  <code class="example-value">{{ item.example }}</code>
                  <button
                    class="copy-btn"
                    @click.stop="copyToClipboard(item.example)"
                  >
                    <Copy class="copy-icon" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- SMTP quick reference -->
        <div class="smtp-reference">
          <div class="section-label">
            <Server class="section-icon" />
            常用 SMTP 快速配置
          </div>
          <div class="smtp-grid">
            <div
              v-for="provider in smtpProviders"
              :key="provider.name"
              class="smtp-card"
              :class="{ selected: selectedProvider === provider.name }"
              @click="applyProvider(provider)"
            >
              <div class="smtp-name">
                {{ provider.name }}
              </div>
              <div class="smtp-detail">
                <span class="smtp-host">{{ provider.host }}</span>
                <span class="smtp-port">:{{ provider.port }}</span>
                <span class="smtp-encrypt">{{ provider.encrypt }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick links -->
        <div
          v-if="guidance.quick_links && guidance.quick_links.length > 0"
          class="quick-links"
        >
          <div class="section-label">
            <ExternalLink class="section-icon" />
            快速配置入口
          </div>
          <div class="links-grid">
            <a
              v-for="link in guidance.quick_links"
              :key="link.path"
              :href="link.path"
              class="link-card"
              @click.prevent="handleLinkClick(link.path)"
            >
              <span class="link-label">{{ link.label }}</span>
              <span class="link-desc">{{ link.description }}</span>
            </a>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Mail, ChevronDown, AlertTriangle, AlertCircle,
  Server, ExternalLink, Settings, CheckCircle, Copy
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

const props = defineProps({
  guidance: {
    type: Object,
    default: () => ({})
  }
})

const router = useRouter()
const isExpanded = ref(true)
const selectedProvider = ref(null)

const smtpProviders = [
  { name: 'Gmail', host: 'smtp.gmail.com', port: '587', encrypt: 'TLS' },
  { name: 'QQ邮箱', host: 'smtp.qq.com', port: '587', encrypt: 'TLS' },
  { name: '163邮箱', host: 'smtp.163.com', port: '465', encrypt: 'SSL' },
  { name: '企业邮箱', host: 'smtp.company.com', port: '465', encrypt: 'SSL' },
]

const configStatus = computed(() => {
  const items = props.guidance?.items || []
  const requiredItems = items.filter(i => i.required)
  if (requiredItems.length === 0) return 'complete'
  const configured = requiredItems.filter(i => isFieldConfigured(i.field)).length
  if (configured === requiredItems.length) return 'complete'
  if (configured > 0) return 'partial'
  return 'missing'
})

function isFieldConfigured(field) {
  const config = props.guidance?.config || {}
  return !!config[field]
}

function toggle() {
  isExpanded.value = !isExpanded.value
}

function handleLinkClick(path) {
  if (path.startsWith('/')) {
    router.push(path)
  } else {
    window.open(path, '_blank')
  }
}

function applyProvider(provider) {
  selectedProvider.value = provider.name
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
}
</script>

<style lang="scss" scoped>
// 一套主题变量驱动的样式，自动适配 dark / light / pure-bw / high-contrast
.email-config-guide {
  background: linear-gradient(135deg, var(--warning-bg) 0%, var(--bg-elevated) 100%);
  border: 1.5px solid var(--warning);
  border-radius: 12px;
  overflow: hidden;
  margin-top: 12px;
  box-shadow: var(--shadow-md);
  font-family: inherit;
  transition: box-shadow 0.2s ease;

  &.expanded {
    box-shadow: var(--shadow-lg);
  }
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  background: var(--warning-bg);
  border-bottom: 1px solid var(--accent-amber-soft);
  user-select: none;
  transition: background 0.2s ease;

  &:hover {
    background: var(--surface-strong);
  }
}

.guide-title {
  display: flex;
  align-items: center;
  gap: 8px;

  .guide-icon {
    width: 18px;
    height: 18px;
    color: var(--warning);
    flex-shrink: 0;
  }

  .guide-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--warning);
  }
}

.guide-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-tag {
  font-size: 11px;
}

.toggle-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-muted);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--surface-strong);
  }

  .toggle-icon {
    width: 16px;
    height: 16px;
    color: var(--warning);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

.guide-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.guide-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.warning-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--error-bg);
  border: 1px solid var(--accent-rose-soft);
  border-radius: 8px;
  font-size: 12px;
  color: var(--error);

  .warning-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }
}

.missing-fields {
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--error);
    margin-bottom: 8px;

    .section-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.missing-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.missing-item {
  font-size: 12px;
  color: var(--error);
  padding: 4px 8px;
  background: var(--error-bg);
  border-radius: 4px;
  border-left: 3px solid var(--error);

  &::before {
    content: '⚠ ';
  }
}

.config-steps {
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--warning);
    margin-bottom: 10px;

    .section-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.step-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-amber-soft);
    transform: translateX(2px);
  }

  &.completed {
    border-color: var(--accent-emerald-soft);
    background: var(--success-bg);

    .step-number {
      background: var(--success);
      color: var(--text-inverse);
    }

    .item-field {
      color: var(--success);
    }
  }

  .step-number {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--warning);
    color: var(--text-inverse);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
    transition: all 0.2s;
  }

  .step-content {
    flex: 1;
  }

  .item-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    .item-field {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .required-tag {
      font-size: 10px;
      transform: scale(0.9);
    }

    .optional-tag {
      font-size: 10px;
      transform: scale(0.9);
    }

    .check-mark {
      margin-left: auto;

      .check-icon {
        width: 16px;
        height: 16px;
        color: var(--success);
      }
    }
  }

  .item-tip {
    font-size: 11px;
    color: var(--text-secondary);
    line-height: 1.6;
    white-space: pre-line;
    margin-bottom: 6px;
  }

  .item-example {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;

    .example-label {
      font-size: 10px;
      color: var(--warning);
      flex-shrink: 0;
    }

    .example-value {
      font-size: 11px;
      font-family: 'JetBrains Mono', 'Courier New', monospace;
      background: var(--surface-muted);
      padding: 2px 6px;
      border-radius: 4px;
      color: var(--text-primary);
    }

    .copy-btn {
      width: 22px;
      height: 22px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--surface-muted);
      border: 1px solid var(--border-primary);
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
      padding: 0;

      &:hover {
        background: var(--surface-strong);
      }

      .copy-icon {
        width: 12px;
        height: 12px;
        color: var(--warning);
      }
    }
  }
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;

  .item-field {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .required-tag {
    font-size: 10px;
    transform: scale(0.9);
  }

  .optional-tag {
    font-size: 10px;
    transform: scale(0.9);
  }
}

.item-tip {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-line;
}

.smtp-reference {
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--warning);
    margin-bottom: 8px;

    .section-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.smtp-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.smtp-card {
  padding: 8px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-hover);
    border-color: var(--accent-amber-soft);
    transform: translateY(-1px);
  }

  &.selected {
    background: var(--warning-bg);
    border-color: var(--warning);
    box-shadow: 0 0 0 2px var(--accent-amber-soft);
  }

  .smtp-name {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 3px;
  }

  .smtp-detail {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 10px;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
  }

  .smtp-host {
    color: var(--text-secondary);
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .smtp-port {
    color: var(--warning);
  }

  .smtp-encrypt {
    color: var(--success);
    margin-left: 2px;
  }
}

.quick-links {
  .section-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--info);
    margin-bottom: 8px;

    .section-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.links-grid {
  display: flex;
  gap: 8px;
}

.link-card {
  flex: 1;
  padding: 10px 12px;
  background: var(--info-bg);
  border: 1px solid var(--accent-blue-soft);
  border-radius: 8px;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 2px;

  &:hover {
    background: var(--surface-strong);
    border-color: var(--info);
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
  }

  .link-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--info);
  }

  .link-desc {
    font-size: 10px;
    color: var(--text-secondary);
    line-height: 1.4;
  }
}

.slide-enter-active {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  overflow: hidden;
}

.slide-leave-active {
  transition: all 0.2s ease-in;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.slide-enter-to,
.slide-leave-from {
  opacity: 1;
  max-height: 800px;
}
</style>
