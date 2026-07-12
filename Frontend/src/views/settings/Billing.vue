<template>
  <div class="billing-page">
    <PageHeader
      compact
      title="订阅管理"
      subtitle="管理您的订阅计划和账单"
    />

    <!-- Current Plan -->
    <div class="current-plan-section">
      <el-card shadow="never">
        <div class="current-plan">
          <div class="plan-info">
            <div
              class="plan-badge"
              :style="{ backgroundColor: currentPlan.color }"
            >
              {{ currentPlan.name }}
            </div>
            <div class="plan-details">
              <h3>{{ currentPlan.price }}<span v-if="currentPlan.price !== '免费'">/月</span></h3>
              <p>包含 {{ planFeatureLimits.max_workflows }} 个工作流，{{ planFeatureLimits.max_members }} 位成员</p>
            </div>
          </div>
          <div class="plan-actions">
            <el-button @click="showUpgradeDialog = true">
              升级套餐
            </el-button>
            <el-button
              v-if="currentPlan.type !== 'free'"
              text
              @click="showCancelDialog = true"
            >
              取消订阅
            </el-button>
          </div>
        </div>

        <!-- Usage Stats -->
        <div class="usage-section">
          <h4>当前使用量</h4>
          <div class="usage-grid">
            <div class="usage-item">
              <div class="usage-header">
                <span class="usage-label">工作流</span>
                <span class="usage-value">{{ usage.workflows }}/{{ limits.max_workflows }}</span>
              </div>
              <el-progress
                :percentage="usagePercentages.workflows"
                :color="getProgressColor(usagePercentages.workflows)"
              />
            </div>
            <div class="usage-item">
              <div class="usage-header">
                <span class="usage-label">本月执行次数</span>
                <span class="usage-value">{{ usage.executions }}/{{ limits.max_executions }}</span>
              </div>
              <el-progress
                :percentage="usagePercentages.executions"
                :color="getProgressColor(usagePercentages.executions)"
              />
            </div>
            <div class="usage-item">
              <div class="usage-header">
                <span class="usage-label">存储空间</span>
                <span class="usage-value">{{ usage.storage }}GB/{{ limits.max_storage }}GB</span>
              </div>
              <el-progress
                :percentage="usagePercentages.storage"
                :color="getProgressColor(usagePercentages.storage)"
              />
            </div>
            <div class="usage-item">
              <div class="usage-header">
                <span class="usage-label">API 调用</span>
                <span class="usage-value">{{ usage.api_calls }}/{{ limits.max_api_calls }}</span>
              </div>
              <el-progress
                :percentage="usagePercentages.api_calls"
                :color="getProgressColor(usagePercentages.api_calls)"
              />
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Available Plans -->
    <div class="plans-section">
      <h2>可用套餐</h2>
      <div class="plans-grid">
        <div
          v-for="plan in availablePlans"
          :key="plan.type"
          class="plan-card"
          :class="{ current: plan.type === currentPlan.type, featured: plan.featured }"
        >
          <div
            v-if="plan.featured"
            class="featured-badge"
          >
            推荐
          </div>
          <h3 class="plan-name">
            {{ plan.name }}
          </h3>
          <div class="plan-price">
            <span class="price">{{ plan.price }}</span>
            <span
              v-if="plan.price !== '免费'"
              class="period"
            >/月</span>
          </div>
          <p class="plan-desc">
            {{ plan.description }}
          </p>
          <ul class="plan-features">
            <li
              v-for="feature in plan.highlights"
              :key="feature"
            >
              <Check class="check-icon" />
              {{ feature }}
            </li>
          </ul>
          <el-button
            :type="plan.type === currentPlan.type ? 'default' : 'primary'"
            :disabled="plan.type === currentPlan.type"
            @click="selectPlan(plan)"
          >
            {{ plan.type === currentPlan.type ? '当前套餐' : plan.action }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Billing History -->
    <div class="billing-history-section">
      <h2>账单记录</h2>
      <el-table
        :data="billingHistory"
        stripe
      >
        <el-table-column
          label="日期"
          prop="date"
          width="120"
        />
        <el-table-column
          label="描述"
          prop="description"
        />
        <el-table-column
          label="金额"
          width="100"
        >
          <template #default="{ row }">
            <span class="amount">{{ row.amount }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'paid' ? 'success' : 'warning'"
              size="small"
            >
              {{ row.status === 'paid' ? '已支付' : '待支付' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'paid'"
              size="small"
              text
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Upgrade Dialog -->
    <el-dialog
      v-model="showUpgradeDialog"
      title="升级套餐"
      width="600px"
    >
      <div class="upgrade-options">
        <div
          v-for="plan in upgradeOptions"
          :key="plan.type"
          class="upgrade-option"
          :class="{ selected: selectedPlan?.type === plan.type }"
          @click="selectedPlan = plan"
        >
          <div class="option-header">
            <h4>{{ plan.name }}</h4>
            <span class="option-price">{{ plan.price }}/月</span>
          </div>
          <p class="option-desc">
            {{ plan.description }}
          </p>
        </div>
      </div>
      <template #footer>
        <el-button @click="showUpgradeDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="isUpgrading"
          @click="upgradePlan"
        >
          确认升级
        </el-button>
      </template>
    </el-dialog>

    <!-- Cancel Dialog -->
    <el-dialog
      v-model="showCancelDialog"
      title="取消订阅"
      width="400px"
    >
      <div class="cancel-content">
        <AlertTriangle class="warning-icon" />
        <p>确定要取消当前订阅吗？</p>
        <ul>
          <li>您的订阅将在当前周期结束前保持有效</li>
          <li>之后您将无法享受高级功能</li>
          <li>所有数据将被保留</li>
        </ul>
      </div>
      <template #footer>
        <el-button @click="showCancelDialog = false">
          保留订阅
        </el-button>
        <el-button
          type="danger"
          @click="cancelSubscription"
        >
          确认取消
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Check, AlertTriangle } from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useBillingStore } from '@/stores/billing'
import PageHeader from '@/components/layout/PageHeader.vue'

const appStore = useAppStore()
const billingStore = useBillingStore()

const showUpgradeDialog = ref(false)
const showCancelDialog = ref(false)
const selectedPlan = ref(null)
const isUpgrading = ref(false)

const currentPlan = computed(() => {
  const sub = billingStore.subscription
  const planColors = {
    free: '#10b981',
    starter: '#3b82f6',
    professional: '#3b82f6',
    enterprise: '#f59e0b'
  }
  if (!sub) {
    return {
      type: 'free',
      name: '免费版',
      price: '免费',
      color: planColors.free,
    }
  }
  const planType = sub.planType ?? sub.plan_type ?? 'free'
  const planName = sub.planName ?? sub.plan_type_display ?? sub.planTypeDisplay ?? planType
  const monthlyPrice = sub.monthlyPrice ?? sub.monthly_price
  return {
    type: planType,
    name: planName,
    price: monthlyPrice ? `¥${monthlyPrice}` : '免费',
    color: planColors[planType] || '#3b82f6',
  }
})

const planFeatureLimits = computed(() => billingStore.usageLimits)

const usage = computed(() => {
  const u = billingStore.currentUsage?.currentUsage
    || billingStore.currentUsage?.current_usage
    || {}
  return {
    workflows: u.workflowCount ?? u.workflow_count ?? 0,
    executions: u.executionCount ?? u.execution_count ?? 0,
    storage: (u.storageUsedMb ?? u.storage_used_mb)
      ? Number((Number(u.storageUsedMb ?? u.storage_used_mb) / 1024).toFixed(1))
      : 0,
    api_calls: u.apiCallCount ?? u.api_call_count ?? 0
  }
})

const limits = computed(() => billingStore.usageLimits)
const usagePercentages = computed(() => billingStore.usagePercentages)

const availablePlans = computed(() => {
  const plans = []
  const plansData = billingStore.plans

  if (Object.keys(plansData).length === 0) {
    return [
      {
        type: 'free',
        name: '免费版',
        price: '免费',
        description: '适合个人用户入门体验',
        featured: false,
        action: '开始使用',
        highlights: ['5 个工作流', '每月 100 次执行', '1 位团队成员', '基础支持']
      },
      {
        type: 'starter',
        name: '入门版',
        price: '¥99',
        description: '适合小型团队和项目',
        featured: false,
        action: '升级',
        highlights: ['20 个工作流', '每月 1,000 次执行', '5 位团队成员', '优先级支持']
      },
      {
        type: 'professional',
        name: '专业版',
        price: '¥299',
        description: '适合成长中的团队',
        featured: true,
        action: '升级',
        highlights: ['100 个工作流', '每月 10,000 次执行', '20 位团队成员', '高级节点', '版本历史', '优先支持']
      },
      {
        type: 'enterprise',
        name: '企业版',
        price: '¥999',
        description: '适合大型组织',
        featured: false,
        action: '联系销售',
        highlights: ['无限工作流', '无限执行次数', '无限团队成员', '自定义域名', 'SSO', '专属支持']
      }
    ]
  }

  for (const [planType, value] of Object.entries(plansData)) {
    const tiers = value?.tiers || []
    const tier = tiers.find(t => (t.billingCycle ?? t.billing_cycle) === 'monthly') || tiers[0]
    if (!tier) continue

    const type = tier.planType ?? tier.plan_type ?? planType
    const priceVal = Number(tier.price ?? tier.monthlyPrice ?? tier.monthly_price ?? 0)
    const maxWorkflows = tier.maxWorkflows ?? tier.max_workflows
    const maxExecutions = tier.maxExecutionsPerMonth ?? tier.max_executions_per_month
    const maxMembers = tier.maxTeamMembers ?? tier.max_team_members

    plans.push({
      type,
      name: value.name || tier.planTypeDisplay || tier.plan_type_display || type,
      price: priceVal > 0 ? `¥${priceVal}` : '免费',
      description: value.description || '',
      featured: type === 'professional',
      action: type === currentPlan.value.type ? '当前套餐' : (type === 'enterprise' ? '联系销售' : '升级'),
      highlights: [
        `${maxWorkflows} 个工作流`,
        `每月 ${maxExecutions} 次执行`,
        `${maxMembers} 位团队成员`,
      ],
    })
  }

  return plans.sort((a, b) => {
    const order = ['free', 'starter', 'professional', 'enterprise']
    return order.indexOf(a.type) - order.indexOf(b.type)
  })
})

const upgradeOptions = computed(() => {
  return availablePlans.value.filter(p => p.type !== 'free')
})

const billingHistory = computed(() => {
  const list = Array.isArray(billingStore.invoices) ? billingStore.invoices : []
  return list.map(inv => ({
    date: inv.period_start ? inv.period_start.substring(0, 7) : inv.created_at?.substring(0, 7),
    description: inv.description || `${inv.invoice_number} - 发票`,
    amount: inv.total_amount ? `¥${inv.total_amount}` : '-',
    status: inv.status?.toLowerCase() || 'paid',
    id: inv.id
  }))
})

const getProgressColor = (percentage) => {
  if (percentage >= 90) return '#ef4444'
  if (percentage >= 70) return '#f59e0b'
  return '#10b981'
}

const selectPlan = (plan) => {
  selectedPlan.value = plan
  showUpgradeDialog.value = true
}

const upgradePlan = async () => {
  if (!selectedPlan.value) return
  isUpgrading.value = true
  try {
    await billingStore.subscribe({
      plan_type: selectedPlan.value.type,
      billing_cycle: 'monthly'
    })
    appStore.success(`已升级到 ${selectedPlan.value.name}`)
    showUpgradeDialog.value = false
    await billingStore.fetchSubscription()
    await billingStore.fetchPlans()
  } catch (error) {
    appStore.error('升级失败，请稍后重试')
  } finally {
    isUpgrading.value = false
  }
}

const cancelSubscription = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要取消当前订阅吗？您的订阅将在当前周期结束前保持有效。',
      '取消订阅',
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '保留订阅',
        type: 'warning'
      }
    )
    await billingStore.cancelSubscription()
    appStore.success('订阅将在当前周期结束时取消')
    showCancelDialog.value = false
  } catch (error) {
    if (error !== 'cancel') {
      appStore.error('操作失败，请稍后重试')
    }
  }
}

onMounted(async () => {
  await billingStore.fetchSubscription()
  await Promise.all([
    billingStore.fetchPlans(),
    billingStore.fetchUsage(),
    billingStore.fetchInvoices(),
  ])
})
</script>

<style lang="scss" scoped>
.billing-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.current-plan-section {
  margin-bottom: 32px;
}

.current-plan {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;

  .plan-info {
    display: flex;
    align-items: flex-start;
    gap: 16px;

    .plan-badge {
      padding: 8px 16px;
      border-radius: 8px;
      color: white;
      font-weight: 600;
    }

    .plan-details {
      h3 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;

        span {
          font-size: 14px;
          color: var(--el-text-color-secondary);
        }
      }

      p {
        margin: 4px 0 0;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .plan-actions {
    display: flex;
    gap: 8px;
  }
}

.usage-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--el-border-color-lighter);

  h4 {
    margin: 0 0 16px;
    font-size: 16px;
  }

  .usage-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }

  .usage-item {
    .usage-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;

      .usage-label {
        color: var(--el-text-color-secondary);
        font-size: 14px;
      }

      .usage-value {
        font-weight: 600;
        font-size: 14px;
      }
    }
  }
}

.plans-section {
  margin-bottom: 32px;

  h2 {
    margin: 0 0 16px;
    font-size: 20px;
  }
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.plan-card {
  position: relative;
  padding: 24px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.current {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  &.featured {
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);

    .plan-name {
      color: var(--el-color-primary);
    }
  }

  .featured-badge {
    position: absolute;
    top: -10px;
    left: 50%;
    transform: translateX(-50%);
    padding: 4px 12px;
    background: var(--el-color-primary);
    color: white;
    font-size: 12px;
    font-weight: 600;
    border-radius: 12px;
  }

  .plan-name {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .plan-price {
    margin: 12px 0;

    .price {
      font-size: 28px;
      font-weight: 700;
    }

    .period {
      color: var(--el-text-color-secondary);
    }
  }

  .plan-desc {
    margin: 0 0 16px;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }

  .plan-features {
    margin: 0 0 24px;
    padding: 0;
    list-style: none;

    li {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      font-size: 14px;

      .check-icon {
        width: 16px;
        height: 16px;
        color: #10b981;
      }
    }
  }
}

.billing-history-section {
  h2 {
    margin: 0 0 16px;
    font-size: 20px;
  }

  .amount {
    font-weight: 600;
  }
}

.upgrade-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upgrade-option {
  padding: 16px;
  border: 2px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }

  &.selected {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
  }

  .option-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h4 {
      margin: 0;
    }

    .option-price {
      font-weight: 600;
    }
  }

  .option-desc {
    margin: 8px 0 0;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }
}

.cancel-content {
  text-align: center;

  .warning-icon {
    width: 48px;
    height: 48px;
    color: #f59e0b;
    margin-bottom: 16px;
  }

  p {
    font-size: 16px;
    margin: 0 0 16px;
  }

  ul {
    margin: 0;
    padding-left: 24px;
    text-align: left;
    color: var(--el-text-color-secondary);

    li {
      margin: 8px 0;
    }
  }
}
</style>
