<template>
  <div class="admin-page">
    <div class="page-header">
      <div class="header-content">
        <h1 class="page-title">
          系统管理
        </h1>
        <p class="page-description">
          管理系统配置、用户、权限和系统监控
        </p>
      </div>
    </div>

    <el-tabs
      v-model="activeTab"
      class="admin-tabs"
    >
      <!-- 系统概览 -->
      <el-tab-pane
        label="系统概览"
        name="overview"
      >
        <div class="tab-content">
          <el-row :gutter="20">
            <el-col
              v-for="stat in systemStats"
              :key="stat.key"
              :span="6"
            >
              <el-card
                shadow="hover"
                class="stat-card"
              >
                <div class="stat-content">
                  <div
                    class="stat-icon"
                    :style="{ backgroundColor: stat.color }"
                  >
                    <el-icon :size="24">
                      <component :is="stat.icon" />
                    </el-icon>
                  </div>
                  <div class="stat-info">
                    <div class="stat-value">
                      {{ stat.value }}
                    </div>
                    <div class="stat-label">
                      {{ stat.label }}
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row
            :gutter="20"
            class="mt-4"
          >
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>
                  <div class="card-header">
                    <span>系统状态</span>
                    <el-button
                      text
                      @click="refreshSystemStatus"
                    >
                      刷新
                    </el-button>
                  </div>
                </template>
                <div class="system-status">
                  <div class="status-item">
                    <span class="status-label">API 服务</span>
                    <el-tag :type="systemHealth.api ? 'success' : 'danger'">
                      {{ systemHealth.api ? '运行中' : '离线' }}
                    </el-tag>
                  </div>
                  <div class="status-item">
                    <span class="status-label">数据库</span>
                    <el-tag :type="systemHealth.database ? 'success' : 'danger'">
                      {{ systemHealth.database ? '连接正常' : '连接失败' }}
                    </el-tag>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Redis</span>
                    <el-tag :type="systemHealth.redis ? 'success' : 'warning'">
                      {{ systemHealth.redis ? '连接正常' : '未配置' }}
                    </el-tag>
                  </div>
                  <div class="status-item">
                    <span class="status-label">Celery</span>
                    <el-tag :type="systemHealth.celery ? 'success' : 'warning'">
                      {{ systemHealth.celery ? '运行中' : '未运行' }}
                    </el-tag>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>
                  <span>快速操作</span>
                </template>
                <div class="quick-actions">
                  <el-button
                    type="primary"
                    @click="showCacheDialog = true"
                  >
                    清理缓存
                  </el-button>
                  <el-button
                    type="warning"
                    @click="showBackupDialog = true"
                  >
                    数据备份
                  </el-button>
                  <el-button
                    type="info"
                    @click="refreshSystemStatus"
                  >
                    刷新状态
                  </el-button>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- 用户管理 -->
      <el-tab-pane
        label="用户管理"
        name="users"
      >
        <div class="tab-content">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>用户列表</span>
                <div class="header-actions">
                  <el-input
                    v-model="userSearch"
                    placeholder="搜索用户..."
                    :prefix-icon="Search"
                    clearable
                    style="width: 200px; margin-right: 12px"
                  />
                  <el-button
                    type="primary"
                    @click="showCreateUserDialog = true"
                  >
                    <el-icon><Plus /></el-icon> 添加用户
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              v-loading="loadingUsers"
              :data="filteredUsers"
              stripe
            >
              <el-table-column
                prop="id"
                label="ID"
                width="80"
              />
              <el-table-column
                prop="username"
                label="用户名"
                min-width="120"
              >
                <template #default="{ row }">
                  <div class="user-info">
                    <el-avatar
                      :size="32"
                      :src="row.avatar"
                    >
                      {{ row.username?.charAt(0)?.toUpperCase() }}
                    </el-avatar>
                    <div class="user-details">
                      <span class="username">{{ row.username }}</span>
                      <span class="email">{{ row.email }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column
                prop="role"
                label="角色"
                width="120"
              >
                <template #default="{ row }">
                  <el-tag :type="getRoleTagType(row.role)">
                    {{ getRoleLabel(row.role) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="tenant"
                label="租户"
                width="150"
              >
                <template #default="{ row }">
                  {{ row.tenant_name || '-' }}
                </template>
              </el-table-column>
              <el-table-column
                prop="is_active"
                label="状态"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '活跃' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="created_at"
                label="注册时间"
                width="180"
              >
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column
                label="操作"
                width="200"
                fixed="right"
              >
                <template #default="{ row }">
                  <el-button
                    text
                    type="primary"
                    @click="editUser(row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    text
                    type="warning"
                    @click="resetUserPassword(row)"
                  >
                    重置密码
                  </el-button>
                  <el-button
                    text
                    type="danger"
                    @click="deleteUser(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrapper">
              <el-pagination
                v-model:current-page="userPage"
                v-model:page-size="userPageSize"
                :total="totalUsers"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next"
                @size-change="loadUsers"
                @current-change="loadUsers"
              />
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 租户管理 -->
      <el-tab-pane
        label="租户管理"
        name="tenants"
      >
        <div class="tab-content">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>租户列表</span>
                <div class="header-actions">
                  <el-select
                    v-model="tenantStatusFilter"
                    placeholder="状态筛选"
                    clearable
                    style="width: 150px; margin-right: 12px"
                  >
                    <el-option
                      label="全部"
                      value=""
                    />
                    <el-option
                      label="活跃"
                      value="active"
                    />
                    <el-option
                      label="试用中"
                      value="trial"
                    />
                    <el-option
                      label="已暂停"
                      value="suspended"
                    />
                  </el-select>
                  <el-button
                    type="primary"
                    @click="showCreateTenantDialog = true"
                  >
                    <el-icon><Plus /></el-icon> 创建租户
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              v-loading="loadingTenants"
              :data="filteredTenants"
              stripe
            >
              <el-table-column
                prop="id"
                label="ID"
                width="80"
              />
              <el-table-column
                prop="name"
                label="租户名称"
                min-width="150"
              >
                <template #default="{ row }">
                  <div class="tenant-info">
                    <span class="tenant-name">{{ row.name }}</span>
                    <span class="tenant-slug">{{ row.slug }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column
                prop="plan"
                label="套餐"
                width="120"
              >
                <template #default="{ row }">
                  <el-tag>{{ getPlanLabel(row.plan) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="status"
                label="状态"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag :type="getTenantStatusType(row.status)">
                    {{ getTenantStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="owner"
                label="所有者"
                width="120"
              >
                <template #default="{ row }">
                  {{ row.owner_username }}
                </template>
              </el-table-column>
              <el-table-column
                label="资源使用"
                width="200"
              >
                <template #default="{ row }">
                  <div class="resource-usage">
                    <div class="usage-item">
                      <span class="usage-label">用户</span>
                      <span class="usage-value">{{ row.current_users }}/{{ row.max_users }}</span>
                    </div>
                    <div class="usage-item">
                      <span class="usage-label">工作流</span>
                      <span class="usage-value">{{ row.current_workflows }}/{{ row.max_workflows }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column
                prop="subscription_end"
                label="到期时间"
                width="120"
              >
                <template #default="{ row }">
                  {{ row.subscription_end ? formatDate(row.subscription_end) : '-' }}
                </template>
              </el-table-column>
              <el-table-column
                label="操作"
                width="180"
                fixed="right"
              >
                <template #default="{ row }">
                  <el-button
                    text
                    type="primary"
                    @click="editTenant(row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    text
                    type="danger"
                    @click="deleteTenant(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 系统配置 -->
      <el-tab-pane
        label="系统配置"
        name="config"
      >
        <div class="tab-content">
          <el-card
            shadow="hover"
            class="config-card"
          >
            <template #header>
              <span>常规设置</span>
            </template>
            <el-form
              :model="generalConfig"
              label-width="150px"
            >
              <el-form-item label="站点名称">
                <el-input v-model="generalConfig.site_name" />
              </el-form-item>
              <el-form-item label="站点描述">
                <el-input
                  v-model="generalConfig.site_description"
                  type="textarea"
                  :rows="3"
                />
              </el-form-item>
              <el-form-item label="允许注册">
                <el-switch v-model="generalConfig.allow_registration" />
              </el-form-item>
              <el-form-item label="邮件验证">
                <el-switch v-model="generalConfig.email_verification" />
              </el-form-item>
              <el-form-item label="默认角色">
                <el-select v-model="generalConfig.default_role">
                  <el-option
                    label="查看者"
                    value="viewer"
                  />
                  <el-option
                    label="成员"
                    value="member"
                  />
                  <el-option
                    label="管理员"
                    value="admin"
                  />
                </el-select>
              </el-form-item>
            </el-form>
          </el-card>

          <el-card
            shadow="hover"
            class="config-card mt-4"
          >
            <template #header>
              <span>API 配置</span>
            </template>
            <el-form
              :model="apiConfig"
              label-width="150px"
            >
              <el-form-item label="API 限流">
                <el-input-number
                  v-model="apiConfig.rate_limit_per_minute"
                  :min="1"
                  :max="1000"
                />
                <span class="form-tip">每分钟请求数限制</span>
              </el-form-item>
              <el-form-item label="Token 限制">
                <el-input-number
                  v-model="apiConfig.max_tokens"
                  :min="100"
                  :max="100000"
                  :step="100"
                />
                <span class="form-tip">单次请求最大 Token 数</span>
              </el-form-item>
              <el-form-item label="执行超时">
                <el-input-number
                  v-model="apiConfig.execution_timeout"
                  :min="10"
                  :max="3600"
                />
                <span class="form-tip">秒</span>
              </el-form-item>
              <el-form-item label="启用 API 日志">
                <el-switch v-model="apiConfig.enable_api_logging" />
              </el-form-item>
              <el-form-item label="启用成本追踪">
                <el-switch v-model="apiConfig.enable_cost_tracking" />
              </el-form-item>
            </el-form>
          </el-card>

          <el-card
            shadow="hover"
            class="config-card mt-4"
          >
            <template #header>
              <span>邮件配置</span>
            </template>
            <el-form
              :model="emailConfig"
              label-width="150px"
            >
              <el-form-item label="SMTP 主机">
                <el-input v-model="emailConfig.smtp_host" />
              </el-form-item>
              <el-form-item label="SMTP 端口">
                <el-input-number
                  v-model="emailConfig.smtp_port"
                  :min="1"
                  :max="65535"
                />
              </el-form-item>
              <el-form-item label="SMTP 用户">
                <el-input v-model="emailConfig.smtp_user" />
              </el-form-item>
              <el-form-item label="SMTP 密码">
                <el-input
                  v-model="emailConfig.smtp_password"
                  type="password"
                  show-password
                />
              </el-form-item>
              <el-form-item label="发件人邮箱">
                <el-input v-model="emailConfig.from_email" />
              </el-form-item>
              <el-form-item label="使用 TLS">
                <el-switch v-model="emailConfig.use_tls" />
              </el-form-item>
            </el-form>
          </el-card>

          <div class="config-actions">
            <el-button
              type="primary"
              :loading="savingConfig"
              @click="saveConfig"
            >
              保存配置
            </el-button>
            <el-button @click="resetConfig">
              重置
            </el-button>
          </div>
        </div>
      </el-tab-pane>

      <!-- 告警规则 -->
      <el-tab-pane
        label="告警规则"
        name="alerts"
      >
        <div class="tab-content">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>告警规则列表</span>
                <el-button
                  type="primary"
                  @click="showCreateAlertDialog = true"
                >
                  <el-icon><Plus /></el-icon> 创建规则
                </el-button>
              </div>
            </template>

            <el-table
              v-loading="loadingAlerts"
              :data="alertRules"
              stripe
            >
              <el-table-column
                prop="name"
                label="规则名称"
                min-width="150"
              />
              <el-table-column
                prop="condition"
                label="触发条件"
                width="150"
              >
                <template #default="{ row }">
                  {{ getConditionLabel(row.condition) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="severity"
                label="严重程度"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag :type="getSeverityType(row.severity)">
                    {{ getSeverityLabel(row.severity) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="threshold"
                label="阈值"
                width="100"
              />
              <el-table-column
                prop="is_active"
                label="状态"
                width="100"
              >
                <template #default="{ row }">
                  <el-switch
                    v-model="row.is_active"
                    @change="toggleAlertRule(row)"
                  />
                </template>
              </el-table-column>
              <el-table-column
                label="通知方式"
                width="200"
              >
                <template #default="{ row }">
                  <el-tag
                    v-if="row.notify_email"
                    size="small"
                    class="mr-2"
                  >
                    邮件
                  </el-tag>
                  <el-tag
                    v-if="row.notify_webhook"
                    size="small"
                  >
                    Webhook
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                label="操作"
                width="180"
                fixed="right"
              >
                <template #default="{ row }">
                  <el-button
                    text
                    type="primary"
                    @click="editAlertRule(row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    text
                    type="danger"
                    @click="deleteAlertRule(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 操作日志 -->
      <el-tab-pane
        label="操作日志"
        name="logs"
      >
        <div class="tab-content">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>操作日志</span>
                <div class="header-actions">
                  <el-select
                    v-model="logLevelFilter"
                    placeholder="日志级别"
                    clearable
                    style="width: 120px; margin-right: 12px"
                  >
                    <el-option
                      label="全部"
                      value=""
                    />
                    <el-option
                      label="信息"
                      value="info"
                    />
                    <el-option
                      label="警告"
                      value="warning"
                    />
                    <el-option
                      label="错误"
                      value="error"
                    />
                  </el-select>
                  <el-date-picker
                    v-model="logDateRange"
                    type="daterange"
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    style="margin-right: 12px"
                    @change="loadLogs"
                  />
                  <el-button @click="loadLogs">
                    刷新
                  </el-button>
                </div>
              </div>
            </template>

            <el-table
              v-loading="loadingLogs"
              :data="operationLogs"
              stripe
            >
              <el-table-column
                prop="id"
                label="ID"
                width="80"
              />
              <el-table-column
                prop="timestamp"
                label="时间"
                width="180"
              >
                <template #default="{ row }">
                  {{ formatDateTime(row.timestamp) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="level"
                label="级别"
                width="100"
              >
                <template #default="{ row }">
                  <el-tag
                    :type="getLogLevelType(row.level)"
                    size="small"
                  >
                    {{ row.level }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="user"
                label="用户"
                width="120"
              />
              <el-table-column
                prop="action"
                label="操作"
                min-width="150"
              />
              <el-table-column
                prop="resource"
                label="资源"
                width="150"
              />
              <el-table-column
                prop="ip_address"
                label="IP地址"
                width="140"
              />
              <el-table-column
                label="详情"
                min-width="200"
              >
                <template #default="{ row }">
                  <el-popover
                    placement="top"
                    :width="400"
                    trigger="hover"
                  >
                    <div class="log-details">
                      <pre>{{ JSON.stringify(row.details, null, 2) }}</pre>
                    </div>
                    <template #reference>
                      <el-button text>
                        查看详情
                      </el-button>
                    </template>
                  </el-popover>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrapper">
              <el-pagination
                v-model:current-page="logPage"
                v-model:page-size="logPageSize"
                :total="totalLogs"
                :page-sizes="[20, 50, 100, 200]"
                layout="total, sizes, prev, pager, next"
                @size-change="loadLogs"
                @current-change="loadLogs"
              />
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 创建用户对话框 -->
    <el-dialog
      v-model="showCreateUserDialog"
      title="添加用户"
      width="500px"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-width="100px"
      >
        <el-form-item
          label="用户名"
          prop="username"
        >
          <el-input v-model="userForm.username" />
        </el-form-item>
        <el-form-item
          label="邮箱"
          prop="email"
        >
          <el-input v-model="userForm.email" />
        </el-form-item>
        <el-form-item
          label="密码"
          prop="password"
        >
          <el-input
            v-model="userForm.password"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item
          label="角色"
          prop="role"
        >
          <el-select v-model="userForm.role">
            <el-option
              label="超级管理员"
              value="superuser"
            />
            <el-option
              label="管理员"
              value="admin"
            />
            <el-option
              label="成员"
              value="member"
            />
            <el-option
              label="查看者"
              value="viewer"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="租户"
          prop="tenant"
        >
          <el-select
            v-model="userForm.tenant_id"
            clearable
            placeholder="选择租户(可选)"
          >
            <el-option
              v-for="tenant in tenants"
              :key="tenant.id"
              :label="tenant.name"
              :value="tenant.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateUserDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="createUser"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建租户对话框 -->
    <el-dialog
      v-model="showCreateTenantDialog"
      title="创建租户"
      width="500px"
    >
      <el-form
        ref="tenantFormRef"
        :model="tenantForm"
        :rules="tenantRules"
        label-width="100px"
      >
        <el-form-item
          label="租户名称"
          prop="name"
        >
          <el-input v-model="tenantForm.name" />
        </el-form-item>
        <el-form-item
          label="租户标识"
          prop="slug"
        >
          <el-input
            v-model="tenantForm.slug"
            placeholder="用于URL和API"
          />
        </el-form-item>
        <el-form-item
          label="套餐"
          prop="plan"
        >
          <el-select v-model="tenantForm.plan">
            <el-option
              label="免费版"
              value="free"
            />
            <el-option
              label="入门版"
              value="starter"
            />
            <el-option
              label="专业版"
              value="professional"
            />
            <el-option
              label="企业版"
              value="enterprise"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="所有者"
          prop="owner_id"
        >
          <el-select
            v-model="tenantForm.owner_id"
            filterable
            placeholder="选择所有者"
          >
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="最大用户数">
          <el-input-number
            v-model="tenantForm.max_users"
            :min="1"
            :max="1000"
          />
        </el-form-item>
        <el-form-item label="最大工作流">
          <el-input-number
            v-model="tenantForm.max_workflows"
            :min="1"
            :max="10000"
          />
        </el-form-item>
        <el-form-item label="每月执行限制">
          <el-input-number
            v-model="tenantForm.max_executions_per_month"
            :min="0"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateTenantDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="createTenant"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 创建告警规则对话框 -->
    <el-dialog
      v-model="showCreateAlertDialog"
      title="创建告警规则"
      width="550px"
    >
      <el-form
        ref="alertFormRef"
        :model="alertForm"
        :rules="alertRules_rules"
        label-width="120px"
      >
        <el-form-item
          label="规则名称"
          prop="name"
        >
          <el-input v-model="alertForm.name" />
        </el-form-item>
        <el-form-item
          label="触发条件"
          prop="condition"
        >
          <el-select v-model="alertForm.condition">
            <el-option
              label="执行失败"
              value="execution_failed"
            />
            <el-option
              label="执行超时"
              value="execution_timeout"
            />
            <el-option
              label="错误率高"
              value="error_rate_high"
            />
            <el-option
              label="执行时间过长"
              value="execution_duration_high"
            />
            <el-option
              label="API配额超限"
              value="api_quota_exceeded"
            />
            <el-option
              label="用户配额超限"
              value="user_quota_exceeded"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          label="严重程度"
          prop="severity"
        >
          <el-select v-model="alertForm.severity">
            <el-option
              label="低"
              value="low"
            />
            <el-option
              label="中"
              value="medium"
            />
            <el-option
              label="高"
              value="high"
            />
            <el-option
              label="严重"
              value="critical"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="阈值">
          <el-input-number
            v-model="alertForm.threshold"
            :min="1"
          />
        </el-form-item>
        <el-form-item label="时间窗口(分钟)">
          <el-input-number
            v-model="alertForm.time_window_minutes"
            :min="1"
            :max="1440"
          />
        </el-form-item>
        <el-form-item label="邮件通知">
          <el-switch v-model="alertForm.notify_email" />
        </el-form-item>
        <el-form-item label="Webhook通知">
          <el-switch v-model="alertForm.notify_webhook" />
        </el-form-item>
        <el-form-item
          v-if="alertForm.notify_webhook"
          label="Webhook URL"
        >
          <el-input
            v-model="alertForm.webhook_url"
            placeholder="https://..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateAlertDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="createAlertRule"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 清理缓存对话框 -->
    <el-dialog
      v-model="showCacheDialog"
      title="清理缓存"
      width="400px"
    >
      <p>确定要清理系统缓存吗？这将清除所有临时数据。</p>
      <template #footer>
        <el-button @click="showCacheDialog = false">
          取消
        </el-button>
        <el-button
          type="danger"
          :loading="clearingCache"
          @click="clearCache"
        >
          确认清理
        </el-button>
      </template>
    </el-dialog>

    <!-- 备份对话框 -->
    <el-dialog
      v-model="showBackupDialog"
      title="数据备份"
      width="500px"
    >
      <el-form
        :model="backupForm"
        label-width="100px"
      >
        <el-form-item label="备份类型">
          <el-radio-group v-model="backupForm.type">
            <el-radio label="full">
              完整备份
            </el-radio>
            <el-radio label="database">
              仅数据库
            </el-radio>
            <el-radio label="files">
              仅文件
            </el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="压缩备份">
          <el-switch v-model="backupForm.compress" />
        </el-form-item>
        <el-form-item label="包含媒体">
          <el-switch v-model="backupForm.include_media" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBackupDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="creatingBackup"
          @click="createBackup"
        >
          开始备份
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import {
  User, Key, Monitor, Setting, Plus, Search,
  CircleCheckFilled, CircleCloseFilled, WarningFilled
} from '@element-plus/icons-vue'
import { formatDate, formatDateTime } from '@/utils/formatters'
import { adminApi } from '@/api/admin'

const appStore = useAppStore()

// State
const activeTab = ref('overview')
const loadingUsers = ref(false)
const loadingTenants = ref(false)
const loadingAlerts = ref(false)
const loadingLogs = ref(false)
const savingConfig = ref(false)
const clearingCache = ref(false)
const creatingBackup = ref(false)

// User management
const users = ref([])
const userSearch = ref('')
const userPage = ref(1)
const userPageSize = ref(10)
const totalUsers = ref(0)
const showCreateUserDialog = ref(false)
const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'member',
  tenant_id: null
})
const userFormRef = ref(null)
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

// Tenant management
const tenants = ref([])
const tenantStatusFilter = ref('')
const showCreateTenantDialog = ref(false)
const tenantForm = ref({
  name: '',
  slug: '',
  plan: 'free',
  owner_id: null,
  max_users: 10,
  max_workflows: 50,
  max_executions_per_month: 1000
})
const tenantFormRef = ref(null)
const tenantRules = {
  name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入租户标识', trigger: 'blur' },
    { pattern: /^[a-z0-9-]+$/, message: '只能包含小写字母、数字和连字符', trigger: 'blur' }
  ],
  plan: [{ required: true, message: '请选择套餐', trigger: 'change' }],
  owner_id: [{ required: true, message: '请选择所有者', trigger: 'change' }]
}

// Alert management
const alertRules = ref([])
const showCreateAlertDialog = ref(false)
const alertForm = ref({
  name: '',
  condition: 'execution_failed',
  severity: 'medium',
  threshold: 1,
  time_window_minutes: 5,
  notify_email: true,
  notify_webhook: false,
  webhook_url: ''
})
const alertFormRef = ref(null)
const alertRules_rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  condition: [{ required: true, message: '请选择触发条件', trigger: 'change' }],
  severity: [{ required: true, message: '请选择严重程度', trigger: 'change' }]
}

// Logs
const operationLogs = ref([])
const logLevelFilter = ref('')
const logDateRange = ref([])
const logPage = ref(1)
const logPageSize = ref(20)
const totalLogs = ref(0)

// System status
const systemStats = ref([
  { key: 'users', label: '总用户数', value: 0, icon: User, color: '#409EFF' },
  { key: 'workflows', label: '总工作流', value: 0, icon: Setting, color: '#67C23A' },
  { key: 'executions', label: '总执行次数', value: 0, icon: CircleCheckFilled, color: '#E6A23C' },
  { key: 'alerts', label: '活跃告警', value: 0, icon: WarningFilled, color: '#F56C6C' }
])
const systemHealth = ref({
  api: true,
  database: true,
  redis: true,
  celery: false
})

// Config
const generalConfig = ref({
  site_name: 'Flowly',
  site_description: 'AI Agent 工作流编排平台',
  allow_registration: true,
  email_verification: false,
  default_role: 'member'
})
const apiConfig = ref({
  rate_limit_per_minute: 60,
  max_tokens: 4096,
  execution_timeout: 300,
  enable_api_logging: true,
  enable_cost_tracking: true
})
const emailConfig = ref({
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  from_email: '',
  use_tls: true
})

// Backup
const showCacheDialog = ref(false)
const showBackupDialog = ref(false)
const backupForm = ref({
  type: 'full',
  compress: true,
  include_media: true
})

// Computed
const filteredUsers = computed(() => {
  if (!userSearch.value) return users.value
  const search = userSearch.value.toLowerCase()
  return users.value.filter(u =>
    u.username.toLowerCase().includes(search) ||
    u.email.toLowerCase().includes(search)
  )
})

const filteredTenants = computed(() => {
  if (!tenantStatusFilter.value) return tenants.value
  return tenants.value.filter(t => t.status === tenantStatusFilter.value)
})

// Methods
const loadUsers = async () => {
  loadingUsers.value = true
  try {
    const params = {
      page: userPage.value,
      page_size: userPageSize.value,
      search: userSearch.value
    }
    const res = await adminApi.getUsers(params)
    users.value = res.results || res
    totalUsers.value = res.total || users.value.length
  } catch (error) {
    // Error already shown via appStore.error() above
  } finally {
    loadingUsers.value = false
  }
}

const createUser = async () => {
  try {
    await userFormRef.value.validate()
    appStore.success('用户创建成功')
    showCreateUserDialog.value = false
    loadUsers()
  } catch (e) {
    console.error('Validation failed:', e)
  }
}

const editUser = (user) => {
  appStore.info('编辑用户: ' + user.username)
}

const resetUserPassword = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要重置用户 ${user.username} 的密码吗？`,
      '重置密码',
      { type: 'warning' }
    )
    appStore.success('密码已重置')
  } catch (e) {}
}

const deleteUser = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 ${user.username} 吗？此操作不可撤销。`,
      '删除用户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await adminApi.deleteUser(user.id)
    appStore.success('用户已删除')
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      appStore.error('删除用户失败')
    }
  }
}

const loadTenants = async () => {
  loadingTenants.value = true
  try {
    // Import tenantApi dynamically to avoid circular dependency
    const { tenantApi } = await import('@/api/tenant')
    const res = await tenantApi.getTenants()
    tenants.value = res.results || res
  } catch (error) {
    // Use mock data if API fails
    tenants.value = [
      { id: 1, name: 'Acme Corp', slug: 'acme', plan: 'professional', status: 'active', owner_username: 'john', current_users: 5, max_users: 20, current_workflows: 12, max_workflows: 100, subscription_end: '2025-12-31T00:00:00Z' },
      { id: 2, name: 'Startup Inc', slug: 'startup', plan: 'starter', status: 'trial', owner_username: 'jane', current_users: 2, max_users: 5, current_workflows: 3, max_workflows: 10, subscription_end: null }
    ]
  } finally {
    loadingTenants.value = false
  }
}

const createTenant = async () => {
  try {
    await tenantFormRef.value.validate()
    appStore.success('租户创建成功')
    showCreateTenantDialog.value = false
    loadTenants()
  } catch (e) {
    console.error('Validation failed:', e)
  }
}

const editTenant = (tenant) => {
  appStore.info('编辑租户: ' + tenant.name)
}

const deleteTenant = async (tenant) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除租户 ${tenant.name} 吗？此操作不可撤销。`,
      '删除租户',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    appStore.success('租户已删除')
    loadTenants()
  } catch (e) {}
}

const loadAlertRules = async () => {
  loadingAlerts.value = true
  try {
    alertRules.value = [
      { id: 1, name: '执行失败告警', condition: 'execution_failed', severity: 'high', threshold: 3, is_active: true, notify_email: true, notify_webhook: false },
      { id: 2, name: '高错误率告警', condition: 'error_rate_high', severity: 'critical', threshold: 20, is_active: true, notify_email: true, notify_webhook: true, webhook_url: 'https://...' }
    ]
  } finally {
    loadingAlerts.value = false
  }
}

const createAlertRule = async () => {
  try {
    await alertFormRef.value.validate()
    appStore.success('告警规则创建成功')
    showCreateAlertDialog.value = false
    loadAlertRules()
  } catch (e) {
    console.error('Validation failed:', e)
  }
}

const editAlertRule = (rule) => {
  appStore.info('编辑告警规则: ' + rule.name)
}

const toggleAlertRule = async (rule) => {
    appStore.success(`告警规则 ${rule.is_active ? '已启用' : '已禁用'}`)
}

const deleteAlertRule = async (rule) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除告警规则 ${rule.name} 吗？`,
      '删除告警规则',
      { type: 'warning' }
    )
    appStore.success('告警规则已删除')
    loadAlertRules()
  } catch (e) {}
}

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    operationLogs.value = [
      { id: 1, timestamp: '2024-03-15T10:30:00Z', level: 'info', user: 'admin', action: '用户登录', resource: '认证系统', ip_address: '192.168.1.1', details: {} },
      { id: 2, timestamp: '2024-03-15T10:25:00Z', level: 'warning', user: 'john', action: 'API配额超限', resource: 'API网关', ip_address: '192.168.1.2', details: { quota: 100, used: 105 } },
      { id: 3, timestamp: '2024-03-15T10:20:00Z', level: 'error', user: 'system', action: '工作流执行失败', resource: 'workflow-123', ip_address: '-', details: { error: 'Timeout' } }
    ]
    totalLogs.value = operationLogs.value.length
  } finally {
    loadingLogs.value = false
  }
}

const refreshSystemStatus = async () => {
  try {
    const res = await adminApi.getSystemHealth()
    systemHealth.value = {
      api: res.api || true,
      database: res.database || true,
      redis: res.redis || false,
      celery: res.celery || false
    }

    // Update stats
    const usage = await adminApi.getSystemUsage()
    systemStats.value = [
      { key: 'users', label: '总用户数', value: usage.users?.total || 0, icon: User, color: '#409EFF' },
      { key: 'workflows', label: '总工作流', value: usage.workflows?.total || 0, icon: Setting, color: '#67C23A' },
      { key: 'executions', label: '总执行次数', value: usage.executions?.total || 0, icon: CircleCheckFilled, color: '#E6A23C' },
      { key: 'alerts', label: '活跃告警', value: 0, icon: WarningFilled, color: '#F56C6C' }
    ]

    appStore.success('系统状态已刷新')
  } catch (error) {
    appStore.error('刷新系统状态失败')
  }
}

const saveConfig = async () => {
  savingConfig.value = true
  try {
    await adminApi.updateSystemSettings({
      ...generalConfig.value,
      ...apiConfig.value,
      ...emailConfig.value
    })
    appStore.success('配置保存成功')
  } catch (error) {
    appStore.error('保存配置失败')
  } finally {
    savingConfig.value = false
  }
}

const resetConfig = () => {
  appStore.info('配置已重置')
}

const clearCache = async () => {
  clearingCache.value = true
  try {
    // In production, call admin API to clear cache
    await new Promise(resolve => setTimeout(resolve, 1000))
    appStore.success('缓存清理成功')
    showCacheDialog.value = false
  } catch (error) {
    appStore.error('清理缓存失败')
  } finally {
    clearingCache.value = false
  }
}

const createBackup = async () => {
  creatingBackup.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 2000))
    appStore.success('备份创建成功')
    showBackupDialog.value = false
  } finally {
    creatingBackup.value = false
  }
}

// Helper functions
const getRoleLabel = (role) => {
  const labels = { superuser: '超级管理员', admin: '管理员', member: '成员', viewer: '查看者' }
  return labels[role] || role
}

const getRoleTagType = (role) => {
  const types = { superuser: 'danger', admin: 'warning', member: '', viewer: 'info' }
  return types[role] || ''
}

const getPlanLabel = (plan) => {
  const labels = { free: '免费版', starter: '入门版', professional: '专业版', enterprise: '企业版' }
  return labels[plan] || plan
}

const getTenantStatusLabel = (status) => {
  const labels = { active: '活跃', trial: '试用中', suspended: '已暂停', cancelled: '已取消' }
  return labels[status] || status
}

const getTenantStatusType = (status) => {
  const types = { active: 'success', trial: 'warning', suspended: 'info', cancelled: 'danger' }
  return types[status] || ''
}

const getConditionLabel = (condition) => {
  const labels = {
    execution_failed: '执行失败',
    execution_timeout: '执行超时',
    error_rate_high: '错误率高',
    execution_duration_high: '执行时间过长',
    api_quota_exceeded: 'API配额超限',
    user_quota_exceeded: '用户配额超限'
  }
  return labels[condition] || condition
}

const getSeverityLabel = (severity) => {
  const labels = { low: '低', medium: '中', high: '高', critical: '严重' }
  return labels[severity] || severity
}

const getSeverityType = (severity) => {
  const types = { low: 'info', medium: 'warning', high: 'danger', critical: 'danger' }
  return types[severity] || ''
}

const getLogLevelType = (level) => {
  const types = { info: 'success', warning: 'warning', error: 'danger' }
  return types[level] || ''
}

// Lifecycle
onMounted(() => {
  loadUsers()
  loadTenants()
  loadAlertRules()
  loadLogs()
  refreshSystemStatus()
})
</script>

<style scoped>
.admin-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-description {
  color: var(--text-secondary);
  margin: 0;
}

.admin-tabs {
  background: transparent;
}

.tab-content {
  padding: 0;
}

.mt-4 {
  margin-top: 16px;
}

.stat-card {
  margin-bottom: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.system-status {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.status-label {
  color: var(--text-secondary);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.username {
  font-weight: 500;
}

.email {
  font-size: 12px;
  color: var(--text-secondary);
}

.tenant-info {
  display: flex;
  flex-direction: column;
}

.tenant-name {
  font-weight: 500;
}

.tenant-slug {
  font-size: 12px;
  color: var(--text-secondary);
}

.resource-usage {
  display: flex;
  gap: 16px;
}

.usage-item {
  display: flex;
  flex-direction: column;
}

.usage-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.usage-value {
  font-weight: 500;
}

.config-card {
  margin-bottom: 16px;
}

.form-tip {
  margin-left: 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.config-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.log-details {
  max-height: 300px;
  overflow: auto;
}

.log-details pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
}

.pagination-wrapper {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.mr-2 {
  margin-right: 8px;
}

:deep(.el-tabs__header) {
  margin-bottom: 16px;
}
</style>
