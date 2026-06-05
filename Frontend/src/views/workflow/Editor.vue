<template>
  <div class="workflow-editor">
    <!-- 顶部工具栏 -->
    <header class="editor-toolbar">
      <!-- 左侧：返回 + 工作流名称 -->
      <div class="toolbar-section toolbar-section--left">
        <el-tooltip
          content="返回工作流列表"
          placement="bottom"
        >
          <el-button
            :icon="ArrowLeft"
            class="toolbar-back-btn"
            @click="handleBack"
          />
        </el-tooltip>
        <div class="workflow-name-wrapper">
          <input
            v-model="workflowName"
            class="workflow-name-input"
            placeholder="输入工作流名称..."
            @blur="handleNameBlur"
          >
          <span
            v-if="isDirty"
            class="unsaved-indicator"
          >未保存</span>
        </div>
      </div>

      <!-- 中间：画布操作（缩放/撤销重做/连线/添加） -->
      <div class="toolbar-section toolbar-section--center">
        <div class="toolbar-btn-group">
          <el-tooltip
            content="放大画布"
            placement="bottom"
          >
            <el-button
              :icon="ZoomIn"
              @click="handleZoomIn"
            />
          </el-tooltip>
          <el-tooltip
            content="缩小画布"
            placement="bottom"
          >
            <el-button
              :icon="ZoomOut"
              @click="handleZoomOut"
            />
          </el-tooltip>
          <el-tooltip
            content="适应窗口"
            placement="bottom"
          >
            <el-button
              :icon="Maximize2"
              @click="handleFitView"
            />
          </el-tooltip>
        </div>
        <div class="toolbar-btn-group">
          <el-tooltip
            content="撤销 (Ctrl+Z)"
            placement="bottom"
          >
            <el-button
              :icon="Undo"
              :disabled="!canUndo"
              @click="handleUndo"
            />
          </el-tooltip>
          <el-tooltip
            content="重做 (Ctrl+Y)"
            placement="bottom"
          >
            <el-button
              :icon="Redo"
              :disabled="!canRedo"
              @click="handleRedo"
            />
          </el-tooltip>
        </div>
        <div class="toolbar-btn-group toolbar-btn-group--single">
          <el-tooltip
            :content="autoConnectMode ? '退出连线模式' : '连线模式'"
            placement="bottom"
          >
            <el-button
              :type="autoConnectMode ? 'primary' : 'default'"
              :icon="Link2"
              size="small"
              @click="autoConnectMode ? cancelAutoConnect() : null"
            >
              连线
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="右键画布快速添加节点"
            placement="bottom"
          >
            <el-button
              :icon="Plus"
              size="small"
              @click="() => {}"
            >
              添加
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="自动排列节点"
            placement="bottom"
          >
            <el-button
              :icon="Layout"
              size="small"
              @click="handleAutoLayout"
            >
              布局
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="触发器配置"
            placement="bottom"
          >
            <el-button
              :icon="Clock"
              size="small"
              @click="openTriggerConfig"
            >
              触发器
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- 右侧：操作按钮 -->
      <div class="toolbar-section toolbar-section--right">
        <!-- 核心操作：验证 + 保存 + 执行 — 始终显示 -->
        <el-tooltip
          content="验证工作流配置"
          placement="bottom"
        >
          <el-button
            :icon="AlertCircle"
            class="toolbar-core-btn"
            @click="handleValidate"
          >
            <span class="btn-label">验证</span>
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="保存工作流 (Ctrl+S)"
          placement="bottom"
        >
          <el-button
            :icon="Save"
            :loading="isSaving"
            class="toolbar-core-btn"
            @click="handleSave"
          >
            <span class="btn-label">保存</span>
          </el-button>
        </el-tooltip>
        <el-tooltip
          content="立即运行工作流"
          placement="bottom"
        >
          <el-button
            type="primary"
            :icon="Play"
            class="toolbar-core-btn toolbar-core-btn--primary"
            @click="handleExecute"
          >
            <span class="btn-label">执行</span>
          </el-button>
        </el-tooltip>

        <!-- 折叠按钮：小屏幕时显示展开菜单 -->
        <el-dropdown
          trigger="click"
          class="toolbar-more-dropdown"
          @command="(cmd) => handleToolbarCommand(cmd)"
        >
          <el-tooltip
            content="更多操作"
            placement="bottom"
          >
            <el-button
              :icon="MoreHorizontal"
              class="toolbar-more-btn"
            />
          </el-tooltip>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="variable">
                <VariableIcon
                  :size="15"
                  style="margin-right: 8px;"
                />
                变量管理
              </el-dropdown-item>
              <el-dropdown-item command="assistant">
                <MessageSquare
                  :size="15"
                  style="margin-right: 8px;"
                />
                AI 助手
              </el-dropdown-item>
              <el-dropdown-item command="theme">
                <PanelRightClose
                  :size="15"
                  style="margin-right: 8px;"
                />
                切换主题
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="editor-container">
      <!-- 左侧节点面板 -->
      <aside class="node-panel">
        <div class="panel-section">
          <h3 class="panel-title">
            流程节点
          </h3>

          <!-- 搜索框 -->
          <div class="node-search">
            <el-input
              v-model="nodeSearchQuery"
              placeholder="搜索节点..."
              :prefix-icon="Search"
              clearable
              size="small"
            />
          </div>

          <!-- 控制流节点 -->
          <div
            v-if="filteredControlNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>控制流</span>
              <span class="category-count">{{ filteredControlNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredControlNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- AI 节点 -->
          <div
            v-if="filteredAiNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>AI 节点</span>
              <span class="category-count">{{ filteredAiNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredAiNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 数据节点 -->
          <div
            v-if="filteredDataNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>数据节点</span>
              <span class="category-count">{{ filteredDataNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredDataNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 工具节点 -->
          <div
            v-if="filteredToolNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>工具节点</span>
              <span class="category-count">{{ filteredToolNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredToolNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 多模态生成节点 -->
          <div
            v-if="filteredMultimodalNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>多模态生成</span>
              <span class="category-count">{{ filteredMultimodalNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredMultimodalNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 模型训练节点 -->
          <div
            v-if="filteredModelTrainingNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>模型训练</span>
              <span class="category-count">{{ filteredModelTrainingNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredModelTrainingNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- RAG 检索节点 -->
          <div
            v-if="filteredRagNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>RAG 检索</span>
              <span class="category-count">{{ filteredRagNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredRagNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- Agent 节点 -->
          <div
            v-if="filteredAgentNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>Agent</span>
              <span class="category-count">{{ filteredAgentNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredAgentNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 数据处理节点 -->
          <div
            v-if="filteredDataProcessNodes.length"
            class="node-category"
          >
            <div class="category-header">
              <span>数据处理</span>
              <span class="category-count">{{ filteredDataProcessNodes.length }}</span>
            </div>
            <div
              v-for="node in filteredDataProcessNodes"
              :key="node.type"
              class="node-item"
              :style="{ '--node-color': node.color }"
              draggable="true"
              :title="node.description"
              @dragstart="onDragStart($event, node)"
            >
              <div
                class="node-item-preview"
                :style="{ backgroundColor: node.bgColor, borderColor: node.color }"
              >
                <component
                  :is="node.icon"
                  class="node-icon"
                  :style="{ color: node.color }"
                />
              </div>
              <div class="node-item-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-desc">{{ node.description }}</span>
              </div>
              <kbd
                class="node-shortcut"
                :style="{ backgroundColor: node.bgColor, color: node.color, borderColor: node.color }"
              >{{ node.shortcut }}</kbd>
            </div>
          </div>

          <!-- 空状态 -->
          <div
            v-if="!hasAnyNodes"
            class="node-empty"
          >
            <Search class="empty-icon" />
            <span>未找到匹配的节点</span>
          </div>
        </div>
      </aside>

      <!-- 中间画布 -->
      <main
        class="canvas-wrapper"
        @drop="onDrop"
        @dragover.prevent
        @contextmenu="onPaneContextMenu"
        @dblclick="onPaneDoubleClick"
      >
        <VueFlow
          ref="vueFlowRef"
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-viewport="viewport"
          :snap-to-grid="snapToGrid"
          :snap-grid="[16, 16]"
          @node-click="onNodeClick"
          @edge-click="handleEdgeClick"
          @pane-click="onPaneClick"
          @nodes-change="handleNodesChange"
          @edges-change="handleEdgesChange"
          @node-drag="onNodeDrag"
          @node-drag-stop="onNodeDragStop"
          @connect="onConnect"
          @node-context-menu="onNodeContextMenu"
          @nodes-initialized="onNodesInitialized"
        >
          <Background
            pattern-color="#1a1a2e"
            :gap="16"
          />
          <Controls />
          <MiniMap
            :node-types="nodeTypes"
            :node-color="minimapNodeColor"
            :node-stroke-width="3"
            mask-color="rgba(15, 15, 30, 0.7)"
          />
        </VueFlow>

        <!-- 空状态提示 -->
        <div
          v-if="nodes.length === 0"
          class="empty-canvas"
        >
          <div class="empty-content">
            <div class="empty-icon-wrapper">
              <GitBranch class="empty-icon" />
            </div>
            <h3>开始创建工作流</h3>
            <p>从左侧面板拖拽节点到画布，或右键/双击画布快速添加</p>
            <div class="quick-hint-row">
              <kbd>S</kbd><span>开始</span>
              <kbd>E</kbd><span>结束</span>
              <kbd>A</kbd><span>LLM</span>
              <kbd>I</kbd><span>输入</span>
              <kbd>O</kbd><span>输出</span>
            </div>
          </div>
        </div>

        <!-- 快速添加菜单 (右键菜单) -->
        <div
          v-if="showQuickAddMenu"
          class="quick-add-menu"
          :style="{ left: quickAddMenuPos.x + 'px', top: quickAddMenuPos.y + 'px' }"
          @contextmenu.prevent
        >
          <div class="quick-add-header">
            <Plus class="menu-icon" />
            <span>快速添加节点</span>
            <button
              class="close-btn"
              @click="closeQuickAddMenu"
            >
              <X class="btn-icon" />
            </button>
          </div>
          <div class="quick-add-body">
            <div class="quick-add-section">
              <div class="section-label">
                控制流
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in controlNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                AI 节点
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in aiNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                数据处理
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in dataNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                工具
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in toolNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                多模态生成
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in multimodalNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                模型训练
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in modelTrainingNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                RAG 检索
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in ragNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                Agent
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in agentNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
            <div class="quick-add-section">
              <div class="section-label">
                数据处理
              </div>
              <div class="quick-add-items">
                <button
                  v-for="n in dataProcessNodes"
                  :key="n.type"
                  class="quick-add-item"
                  @click="handleQuickAddSelect(n.type)"
                >
                  <component
                    :is="n.icon"
                    class="item-icon"
                    :style="{ color: n.color }"
                  />
                  <span>{{ n.label }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 自动连线模式指示器 -->
        <div
          v-if="autoConnectMode"
          class="auto-connect-indicator"
        >
          <Link2 class="indicator-icon" />
          <span>连线模式: 点击目标节点完成连线</span>
          <el-button
            size="small"
            @click="cancelAutoConnect"
          >
            取消 (ESC)
          </el-button>
        </div>

        <!-- 节点数量统计 -->
        <div class="canvas-status-bar">
          <span class="status-item">
            <span
              class="status-dot"
              style="background: #3b82f6;"
            />
            {{ nodes.length }} 个节点
          </span>
          <span class="status-item">
            <span
              class="status-dot"
              style="background: #10b981;"
            />
            {{ edges.length }} 条连线
          </span>
          <span
            v-if="autoConnectMode"
            class="status-item connect-mode"
          >
            <Link2 class="status-icon" />
            连线模式
          </span>
        </div>
      </main>
    </div>

    <!-- 验证结果对话框 -->
    <el-dialog
      v-model="showValidateDialog"
      title="工作流验证"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="true"
    >
      <div
        v-if="validationResult.valid"
        class="validate-success"
      >
        <CheckCircle class="success-icon" />
        <p>工作流结构验证通过</p>
      </div>
      <div
        v-else
        class="validate-errors"
      >
        <div
          v-if="validationResult.errors?.length"
          class="error-list"
        >
          <h4>错误</h4>
          <ul>
            <li
              v-for="(error, index) in validationResult.errors"
              :key="index"
            >
              {{ error }}
            </li>
          </ul>
        </div>
        <div
          v-if="validationResult.warnings?.length"
          class="warning-list"
        >
          <h4>警告</h4>
          <ul>
            <li
              v-for="(warning, index) in validationResult.warnings"
              :key="index"
            >
              {{ warning }}
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="showValidateDialog = false">
          关闭
        </el-button>
      </template>
    </el-dialog>

    <!-- 触发器配置抽屉 -->
    <TriggerConfig
      v-model:visible="triggerConfigVisible"
      :workflow-id="workflowId"
    />

    <!-- 变量管理面板 -->
    <VariablePanel
      v-model="variablePanelVisible"
      :workflow-id="workflowId"
      :nodes="nodes"
    />

    <!-- AI 工作流助手 -->
    <WorkflowAssistant
      v-model="showAssistant"
      :nodes="nodes"
      :edges="edges"
    />

    <!-- 底部执行面板 -->
    <Transition name="slide-up">
      <div
        v-if="showExecutionPanel"
        class="execution-bottom-panel"
      >
        <div
          class="exec-panel-handle"
          title="点击折叠"
          @click="showExecutionPanel = false"
        />

        <!-- 面板头部 -->
        <div class="exec-panel-header">
          <div class="exec-header-left">
            <Zap class="exec-icon" />
            <span class="exec-title">执行状态</span>
            <el-tag
              :type="executionStatus === 'completed' ? 'success' : executionStatus === 'failed' ? 'danger' : executionStatus === 'running' ? 'warning' : 'info'"
              size="small"
            >
              {{ executionStatus === 'idle' ? '就绪' : executionStatus === 'running' ? '执行中' : executionStatus === 'completed' ? '已完成' : executionStatus === 'cancelled' ? '已取消' : '失败' }}
            </el-tag>
            <span class="exec-node-count">
              {{ completedNodeCount }}/{{ nodes.length }} 节点
            </span>
          </div>
          <div class="exec-header-right">
            <span
              v-if="executionElapsed"
              class="exec-elapsed"
            >{{ executionElapsed }}</span>
            <el-button
              v-if="executionStatus === 'running'"
              type="danger"
              size="small"
              @click="cancelExecution"
            >
              取消
            </el-button>
            <el-button
              v-if="executionStatus === 'completed' || executionStatus === 'failed'"
              size="small"
              @click="startExecution"
            >
              重试
            </el-button>
            <el-button
              size="small"
              @click="showExecutionPanel = false"
            >
              <X class="btn-icon" />
            </el-button>
          </div>
        </div>

        <!-- 三栏主体 -->
        <div class="exec-panel-body">
          <!-- 左栏：节点执行时间线 -->
          <div class="exec-timeline">
            <div class="timeline-header">
              节点状态
            </div>
            <div class="timeline-list">
              <div
                v-for="node in executionNodeList"
                :key="node.id"
                class="timeline-item"
                :class="`node-${node.status}`"
                @click="selectedExecNode = node"
              >
                <div class="timeline-status">
                  <Loader
                    v-if="node.status === 'running'"
                    class="tl-icon spinning"
                  />
                  <Check
                    v-else-if="node.status === 'completed'"
                    class="tl-icon success"
                  />
                  <X
                    v-else-if="node.status === 'failed'"
                    class="tl-icon error"
                  />
                  <Circle
                    v-else
                    class="tl-icon pending"
                  />
                </div>
                <div class="timeline-info">
                  <span class="tl-name">{{ node.name }}</span>
                  <span class="tl-type">{{ node.type }}</span>
                </div>
              </div>
              <div
                v-if="!executionNodeList.length"
                class="timeline-empty"
              >
                暂无执行数据
              </div>
            </div>
          </div>

          <!-- 中栏：节点输出卡片 -->
          <div class="exec-output">
            <div class="output-header">
              <span>输出详情</span>
              <span
                v-if="selectedExecNode"
                class="output-node-name"
              >{{ selectedExecNode.name }}</span>
            </div>
            <div class="output-content">
              <template v-if="selectedExecNode">
                <div
                  v-if="selectedExecNode.status === 'running'"
                  class="output-running"
                >
                  <Loader class="output-spinner spinning" />
                  <span>执行中...</span>
                </div>
                <div
                  v-else-if="selectedExecNode.status === 'completed'"
                  class="output-success"
                >
                  <Check class="output-check success" />
                  <span>执行完成</span>
                  <pre class="output-data">{{ formatNodeOutput(selectedExecNode.output) }}</pre>
                </div>
                <div
                  v-else-if="selectedExecNode.status === 'failed'"
                  class="output-error"
                >
                  <X class="output-check error" />
                  <span>执行失败</span>
                  <div class="output-err-detail">
                    {{ selectedExecNode.error || '未知错误' }}
                  </div>
                </div>
                <div
                  v-else
                  class="output-pending"
                >
                  <span>等待执行</span>
                </div>
              </template>
              <div
                v-else
                class="output-placeholder"
              >
                <span>点击左侧节点查看详情</span>
              </div>
            </div>
          </div>

          <!-- 右栏：执行进度摘要 -->
          <div class="exec-summary">
            <div class="summary-header">
              执行摘要
            </div>
            <div class="summary-stats">
              <div class="stat-item">
                <span class="stat-label">总节点</span>
                <span class="stat-value">{{ nodes.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已完成</span>
                <span class="stat-value success">{{ completedNodeCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">进行中</span>
                <span class="stat-value running">{{ runningNodeCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">失败</span>
                <span class="stat-value error">{{ failedNodeCount }}</span>
              </div>
            </div>

            <!-- 进度条 -->
            <div class="summary-progress">
              <div class="progress-track">
                <div
                  class="progress-fill"
                  :style="{ width: executionProgressPct + '%' }"
                />
              </div>
              <span class="progress-pct">{{ executionProgressPct }}%</span>
            </div>

            <!-- 日志流 -->
            <div class="summary-logs">
              <div class="logs-header">
                执行日志
              </div>
              <div
                ref="execPanelBodyRef"
                class="logs-scroll"
              >
                <div
                  v-for="(log, idx) in executionLogs"
                  :key="idx"
                  class="exec-log-item"
                  :class="`log-${log.type}`"
                >
                  <span class="log-time">{{ log.time }}</span>
                  <span class="log-text">{{ log.text }}</span>
                </div>
                <div
                  v-if="executionStatus === 'running'"
                  class="exec-loading"
                >
                  <span class="exec-spinner" />
                  <span>执行中...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, shallowRef, markRaw, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { autoLayoutWorkflow } from '@/utils/workflowLayout'
import { useAppStore } from '@/stores/app'
import {
  ArrowLeft, Save, Play, ZoomIn, ZoomOut,
  Maximize2, Undo, Redo, CheckCircle,
  AlertCircle, GitBranch,
  PlayCircle, Circle, FileText, Zap, MessageSquare,
  Hammer, User, Code, Webhook, Variable as VariableIcon, LogOut,
  RefreshCw, Timer, SplitSquareHorizontal, Search,
  Plus, Link2, Clock, GitMerge, Shuffle, Mail,
  Brain, BookOpen, Bot, Database, Globe, Sparkles, X,
  MoreHorizontal, ChevronDown, PanelRightClose,
  Loader, Check, Layout
} from 'lucide-vue-next'
import { VueFlow, useVueFlow, MarkerType } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import StartNode from '@/components/workflow/nodes/StartNode.vue'
import EndNode from '@/components/workflow/nodes/EndNode.vue'
import LLMNode from '@/components/workflow/nodes/LLMNode.vue'
import PromptNode from '@/components/workflow/nodes/PromptNode.vue'
import ConditionNode from '@/components/workflow/nodes/ConditionNode.vue'
import LoopNode from '@/components/workflow/nodes/LoopNode.vue'
import InputNode from '@/components/workflow/nodes/InputNode.vue'
import OutputNode from '@/components/workflow/nodes/OutputNode.vue'
import CodeNode from '@/components/workflow/nodes/CodeNode.vue'
import VariableNode from '@/components/workflow/nodes/VariableNode.vue'
import ToolNode from '@/components/workflow/nodes/ToolNode.vue'
import HttpNode from '@/components/workflow/nodes/HttpNode.vue'
import SwitchNode from '@/components/workflow/nodes/SwitchNode.vue'
import DelayNode from '@/components/workflow/nodes/DelayNode.vue'
import TransformNode from '@/components/workflow/nodes/TransformNode.vue'
import EmailNode from '@/components/workflow/nodes/EmailNode.vue'
import SubworkflowNode from '@/components/workflow/nodes/SubworkflowNode.vue'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'
import VariablePanel from '@/views/workflow/VariablePanel.vue'
import TriggerConfig from './TriggerConfig.vue'
import WorkflowAssistant from '@/components/workflow/WorkflowAssistant.vue'

// Domain node components (Wave 2 - placeholder imports)
import ImageGenerationNode from '@/components/workflow/nodes/ImageGenerationNode.vue'
import VideoGenerationNode from '@/components/workflow/nodes/VideoGenerationNode.vue'
import AudioGenerationNode from '@/components/workflow/nodes/AudioGenerationNode.vue'
import SubtitleGenerationNode from '@/components/workflow/nodes/SubtitleGenerationNode.vue'
import ImageEditingNode from '@/components/workflow/nodes/ImageEditingNode.vue'
import DatasetUploadNode from '@/components/workflow/nodes/DatasetUploadNode.vue'
import DataAnnotationNode from '@/components/workflow/nodes/DataAnnotationNode.vue'
import DataAugmentationNode from '@/components/workflow/nodes/DataAugmentationNode.vue'
import ModelTrainingNode from '@/components/workflow/nodes/ModelTrainingNode.vue'
import ModelEvaluationNode from '@/components/workflow/nodes/ModelEvaluationNode.vue'
import ModelDeploymentNode from '@/components/workflow/nodes/ModelDeploymentNode.vue'
import WebsiteGeneratorNode from '@/components/workflow/nodes/WebsiteGeneratorNode.vue'
import DocumentLoaderNode from '@/components/workflow/nodes/DocumentLoaderNode.vue'
import EmbeddingNode from '@/components/workflow/nodes/EmbeddingNode.vue'
import VectorStoreNode from '@/components/workflow/nodes/VectorStoreNode.vue'
import RetrieverNode from '@/components/workflow/nodes/RetrieverNode.vue'
import RerankerNode from '@/components/workflow/nodes/RerankerNode.vue'
import AgentNodeComponent from '@/components/workflow/nodes/AgentNode.vue'
import PlannerNode from '@/components/workflow/nodes/PlannerNode.vue'
import ExecutorNode from '@/components/workflow/nodes/ExecutorNode.vue'
import MemoryNode from '@/components/workflow/nodes/MemoryNode.vue'
import FileReaderNode from '@/components/workflow/nodes/FileReaderNode.vue'
import FileWriterNode from '@/components/workflow/nodes/FileWriterNode.vue'
import WebScraperNodeComponent from '@/components/workflow/nodes/WebScraperNode.vue'
import CsvTransformNode from '@/components/workflow/nodes/CsvTransformNode.vue'
import JsonTransformNode from '@/components/workflow/nodes/JsonTransformNode.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()

const workflowId = computed(() => route.params.id)
const isNewWorkflow = computed(() => workflowId.value === 'new' || !workflowId.value)

const workflowName = ref('未命名工作流')
const isDirty = ref(false)
const isSaving = computed(() => workflowStore.isSaving)
const showValidateDialog = ref(false)
const validationResult = ref({ valid: true, errors: [], warnings: [] })
const triggerConfigVisible = ref(false)
const variablePanelVisible = ref(false)
const showAssistant = ref(false)

// 执行面板状态
const showExecutionPanel = ref(false)
const executionId = ref(null)
const executionStatus = ref('idle') // idle | running | completed | failed | cancelled
const executionLogs = ref([]) // { type: 'info'|'success'|'error', time: string, text: string }
const executionStartTime = ref(null)
const selectedExecNode = ref(null)
const elapsedTick = ref(0) // 触发 executionElapsed 重新计算

const executionNodeList = computed(() => {
  return nodes.value.map(n => ({
    id: n.id,
    name: n.data?.label || n.label || n.id,
    type: n.type,
    status: 'pending',
    output: null,
    error: null
  }))
})

const completedNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'completed').length)
const runningNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'running').length)
const failedNodeCount = computed(() => executionNodeList.value.filter(n => n.status === 'failed').length)

const executionProgressPct = computed(() => {
  if (!nodes.value.length) return 0
  return Math.round((completedNodeCount.value / nodes.value.length) * 100)
})

const executionElapsed = computed(() => {
  if (!executionStartTime.value) return null
  elapsedTick.value // 依赖响应式，触发更新
  const ms = Date.now() - executionStartTime.value
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  if (m > 0) return `${m}m ${s % 60}s`
  return `${s}s`
})

function formatNodeOutput(output) {
  if (!output) return ''
  if (typeof output === 'string') return output
  try { return JSON.stringify(output, null, 2) } catch { return String(output) }
}

const viewport = ref({ x: 50, y: 50, zoom: 1 })
const snapToGrid = ref(true)
const vueFlowRef = ref(null)

const selectedNode = ref(null)
const selectedEdge = ref(null)
const execPanelBodyRef = ref(null)

const nodes = shallowRef([])
const edges = shallowRef([])

// 可用的模型和工具列表（从 API 获取）
const availableModels = ref([])
const availableTools = ref([])
const modelsLoading = ref(false)
const toolsLoading = ref(false)

// 历史记录（用于撤销/重做）
const history = ref([])
const historyIndex = ref(-1)

// ============================================================
// 核心新增功能：点击添加节点 + 自动连线
// ============================================================

// 快速添加菜单
const showQuickAddMenu = ref(false)
const quickAddMenuPos = ref({ x: 0, y: 0 })
const quickAddTargetPos = ref({ x: 0, y: 0 })

// 自动连线模式
const autoConnectMode = ref(false)
const autoConnectSourceNode = ref(null)
const autoConnectSourceHandle = ref(null)
const connectionPreviewPos = ref({ x: 0, y: 0 })

// 节点悬停高亮（用于显示连接桩）
const hoveredNode = ref(null)
const hoveredHandle = ref(null)

// 连接桩提示
const showHandleTooltip = ref(false)
const handleTooltipPos = ref({ x: 0, y: 0 })
const handleTooltipText = ref('')

// 快速添加分类
const quickAddCategories = [
  { name: 'control', label: '控制流', icon: 'GitBranch' },
  { name: 'ai', label: 'AI 节点', icon: 'Zap' },
  { name: 'data', label: '数据处理', icon: 'FileText' },
  { name: 'tools', label: '工具', icon: 'Hammer' },
]

// 自动连线辅助：将节点按从上到下、从左到右排序
function getAutoConnectSuggestion(newNodeId) {
  const newNode = nodes.value.find(n => n.id === newNodeId)
  if (!newNode) return null

  const nodeBelow = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.x - newNode.position.x) < 200 &&
    n.position.y > newNode.position.y
  )
  const nodeAbove = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.x - newNode.position.x) < 200 &&
    n.position.y < newNode.position.y
  )
  const nodeLeft = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.y - newNode.position.y) < 100 &&
    n.position.x < newNode.position.x
  )
  const nodeRight = nodes.value.find(n =>
    n.id !== newNodeId &&
    Math.abs(n.position.y - newNode.position.y) < 100 &&
    n.position.x > newNode.position.x
  )

  // 如果上面有节点，优先自动连接到上面的节点
  if (nodeAbove) {
    return { source: nodeAbove.id, target: newNodeId, label: '自动连线' }
  }
  // 如果右边有节点，自动连接
  if (nodeRight) {
    return { source: nodeRight.id, target: newNodeId, label: '自动连线' }
  }
  return null
}

// 自动创建连线
function createAutoConnect(source, target, label = '自动连线') {
  // 避免重复连线
  const exists = edges.value.some(
    e => e.source === source && e.target === target
  )
  if (exists) return

  const newEdge = {
    id: `edge_auto_${Date.now()}`,
    source,
    target,
    label,
    type: 'default',
    animated: true,
    markerEnd: MarkerType.ArrowClosed,
    style: 'stroke: #3b82f6; stroke-dasharray: 5,5;'
  }
  edges.value = [...edges.value, newEdge]
  markDirty()
  saveHistory()
}

// 在画布指定位置添加节点（带自动连线）
function addNodeAtPosition(type, position) {
  const nodeType = allNodes.find(n => n.type === type)
  if (!nodeType) return

  // 网格对齐
  const snappedPos = {
    x: Math.round(position.x / 16) * 16,
    y: Math.round(position.y / 16) * 16
  }

  const newNode = {
    id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
    type,
    position: snappedPos,
    data: {
      label: nodeType.label,
      type,
      config: getDefaultConfig(type),
      description: ''
    }
  }

  nodes.value = [...nodes.value, newNode]
  saveHistory()

  // 自动连线逻辑
  const suggestion = getAutoConnectSuggestion(newNode.id)
  if (suggestion) {
    createAutoConnect(suggestion.source, suggestion.target, suggestion.label)
  }

  // 选中刚添加的节点
  selectedNode.value = newNode
  selectedEdge.value = null

  markDirty()
  return newNode
}

// 打开快速添加菜单
function openQuickAddMenu(clientX, clientY) {
  // 计算相对于画布的位置
  const canvasEl = document.querySelector('.canvas-wrapper')
  if (!canvasEl) return
  const rect = canvasEl.getBoundingClientRect()

  quickAddTargetPos.value = {
    x: Math.round((clientX - rect.left) / 16) * 16,
    y: Math.round((clientY - rect.top) / 16) * 16
  }
  quickAddMenuPos.value = {
    x: clientX - rect.left,
    y: clientY - rect.top
  }
  showQuickAddMenu.value = true
}

// 关闭快速添加菜单
function closeQuickAddMenu() {
  showQuickAddMenu.value = false
}

// 处理快速添加菜单选择
function handleQuickAddSelect(type) {
  closeQuickAddMenu()
  addNodeAtPosition(type, quickAddTargetPos.value)
}

// 处理连接桩点击（手动连线）
function handleConnectClick(nodeId, handleType, handleId) {
  if (!autoConnectMode.value) {
    // 开始连线
    autoConnectMode.value = true
    autoConnectSourceNode.value = nodeId
    autoConnectSourceHandle.value = handleId
    document.body.style.cursor = 'crosshair'
  } else {
    // 完成连线
    if (autoConnectSourceNode.value && autoConnectSourceNode.value !== nodeId) {
      const newEdge = {
        id: `edge_${Date.now()}`,
        source: autoConnectSourceNode.value,
        target: nodeId,
        sourceHandle: autoConnectSourceHandle.value,
        targetHandle: handleId,
        label: '',
        type: 'default',
        animated: false,
        markerEnd: MarkerType.ArrowClosed
      }
      edges.value = [...edges.value, newEdge]
      saveHistory()
      markDirty()
    }
    cancelAutoConnect()
  }
}

// 取消连线模式
function cancelAutoConnect() {
  autoConnectMode.value = false
  autoConnectSourceNode.value = null
  autoConnectSourceHandle.value = null
  document.body.style.cursor = 'default'
}

// ESC 取消操作
function handleGlobalKeyDown(e) {
  if (e.key === 'Escape') {
    if (showQuickAddMenu.value) {
      closeQuickAddMenu()
    }
    if (autoConnectMode.value) {
      cancelAutoConnect()
    }
  }
  // 快捷键添加节点
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return

  // Delete / Backspace 删除选中节点
  if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNode.value) {
    e.preventDefault()
    handleDeleteNode()
    return
  }

  const shortcuts = {
    's': 'start', 'S': 'start',
    'e': 'end', 'E': 'end',
    'a': 'llm', 'A': 'llm',
    'p': 'prompt', 'P': 'prompt',
    'i': 'input', 'I': 'input',
    'o': 'output', 'O': 'output',
    'c': 'code', 'C': 'code',
    'v': 'variable', 'V': 'variable',
    'h': 'http', 'H': 'http',
    'g': 'tool', 'G': 'tool',
    'l': 'loop', 'L': 'loop',
    'd': 'delay', 'D': 'delay',
    'w': 'switch', 'W': 'switch',
    'r': 'condition', 'R': 'condition',
    'f': 'subworkflow', 'F': 'subworkflow',
    't': 'transform', 'T': 'transform',
    'm': 'email', 'M': 'email',
  }

  if (shortcuts[e.key]) {
    e.preventDefault()
    const pos = {
      x: 400 + Math.random() * 100,
      y: 300 + Math.random() * 100
    }
    addNodeAtPosition(shortcuts[e.key], pos)
    appStore.success(`已添加节点: ${allNodes.find(n => n.type === shortcuts[e.key])?.label}`)
  }
}

// 画布右键菜单
function onPaneContextMenu(event) {
  event.preventDefault()
  openQuickAddMenu(event.clientX, event.clientY)
}

// 双击画布添加节点
function onPaneDoubleClick(event) {
  const canvasEl = document.querySelector('.canvas-wrapper')
  if (!canvasEl) return
  const rect = canvasEl.getBoundingClientRect()
  const pos = {
    x: Math.round((event.clientX - rect.left) / 16) * 16,
    y: Math.round((event.clientY - rect.top) / 16) * 16
  }
  // 双击添加 LLM 节点作为默认
  addNodeAtPosition('llm', pos)
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeyDown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeyDown)
  document.body.style.cursor = 'default'
})

// 节点分类
const controlNodes = [
  { type: 'start', label: '开始', icon: PlayCircle, description: '工作流入口点', shortcut: 'S', color: '#10b981', bgColor: '#000' },
  { type: 'end', label: '结束', icon: Circle, description: '工作流结束点', shortcut: 'E', color: '#ef4444', bgColor: '#000' },
  { type: 'condition', label: '条件判断', icon: GitBranch, description: '根据条件分流执行', shortcut: 'C', color: '#3b82f6', bgColor: '#000' },
  { type: 'loop', label: '循环', icon: RefreshCw, description: '重复执行循环体', shortcut: 'L', color: '#f59e0b', bgColor: '#000' },
  { type: 'switch', label: '分支选择', icon: SplitSquareHorizontal, description: '多分支条件选择', shortcut: 'W', color: '#3b82f6', bgColor: '#000' },
  { type: 'delay', label: '延时', icon: Timer, description: '等待指定时间', shortcut: 'D', color: '#14b8a6', bgColor: '#000' },
  { type: 'subworkflow', label: '子工作流', icon: GitMerge, description: '调用子工作流', shortcut: 'F', color: '#8b5cf6', bgColor: '#000' },
]

const aiNodes = [
  { type: 'llm', label: '大语言模型', icon: Zap, description: '调用 LLM 生成内容', shortcut: 'A', color: '#3b82f6', bgColor: '#fff' },
  { type: 'prompt', label: '提示词', icon: MessageSquare, description: '定义结构化提示词', shortcut: 'P', color: '#f59e0b', bgColor: '#000' },
]

const dataNodes = [
  { type: 'input', label: '输入', icon: FileText, description: '接收用户输入数据', shortcut: 'I', color: '#06b6d4', bgColor: '#fff' },
  { type: 'output', label: '输出', icon: LogOut, description: '输出工作流结果', shortcut: 'O', color: '#84cc16', bgColor: '#fff' },
  { type: 'code', label: '代码执行', icon: Code, description: '执行自定义 JavaScript', shortcut: 'X', color: '#f97316', bgColor: '#000' },
  { type: 'variable', label: '变量', icon: VariableIcon, description: '变量赋值与读取', shortcut: 'V', color: '#10b981', bgColor: '#000' },
  { type: 'transform', label: '数据转换', icon: Shuffle, description: '数据格式转换与处理', shortcut: 'T', color: '#8b5cf6', bgColor: '#fff' },
]

const toolNodes = [
  { type: 'tool', label: '工具', icon: Hammer, description: '调用内置或自定义工具', shortcut: 'G', color: '#ec4899', bgColor: '#000' },
  { type: 'http', label: 'HTTP请求', icon: Webhook, description: '发送 HTTP 网络请求', shortcut: 'H', color: '#f97316', bgColor: '#000' },
  { type: 'email', label: '发送邮件', icon: Mail, description: '发送电子邮件', shortcut: 'M', color: '#dc2626', bgColor: '#fff' },
]

const multimodalNodes = [
  { type: 'image_generation', label: '图像生成', icon: Sparkles, description: '使用 AI 生成图像', shortcut: 'I', color: '#ec4899', bgColor: '#fff' },
  { type: 'video_generation', label: '视频生成', icon: Sparkles, description: '使用 AI 生成视频', shortcut: 'V', color: '#ec4899', bgColor: '#fff' },
  { type: 'audio_generation', label: '音频生成', icon: Sparkles, description: '使用 AI 生成音频', shortcut: 'A', color: '#ec4899', bgColor: '#fff' },
  { type: 'subtitle_generation', label: '字幕生成', icon: Sparkles, description: '从音视频生成字幕', shortcut: 'S', color: '#ec4899', bgColor: '#fff' },
  { type: 'image_editing', label: '图像编辑', icon: Sparkles, description: '使用 AI 编辑图像', shortcut: 'E', color: '#ec4899', bgColor: '#fff' },
]

const modelTrainingNodes = [
  { type: 'dataset_upload', label: '数据集上传', icon: Database, description: '上传和验证数据集', shortcut: 'D', color: '#f59e0b', bgColor: '#fff' },
  { type: 'data_annotation', label: '数据标注', icon: Database, description: '对数据集进行标注', shortcut: 'N', color: '#f59e0b', bgColor: '#fff' },
  { type: 'data_augmentation', label: '数据增强', icon: Database, description: '数据增强和变换', shortcut: 'U', color: '#f59e0b', bgColor: '#fff' },
  { type: 'model_training', label: '模型训练', icon: Brain, description: '训练机器学习模型', shortcut: 'T', color: '#f59e0b', bgColor: '#000' },
  { type: 'model_evaluation', label: '模型评估', icon: Brain, description: '评估模型性能', shortcut: 'R', color: '#f59e0b', bgColor: '#000' },
  { type: 'model_deployment', label: '模型部署', icon: Brain, description: '部署模型到生产环境', shortcut: 'Y', color: '#f59e0b', bgColor: '#000' },
  { type: 'website_generator', label: '网站生成', icon: Globe, description: '生成可部署的AI网站', shortcut: 'W', color: '#8b5cf6', bgColor: '#fff' },
]

const ragNodes = [
  { type: 'document_loader', label: '文档加载', icon: BookOpen, description: '加载各种格式的文档', shortcut: 'L', color: '#06b6d4', bgColor: '#fff' },
  { type: 'embedding', label: '向量化', icon: BookOpen, description: '文本嵌入和向量化', shortcut: 'B', color: '#06b6d4', bgColor: '#fff' },
  { type: 'vector_store', label: '向量库', icon: BookOpen, description: '向量存储和检索', shortcut: 'K', color: '#06b6d4', bgColor: '#fff' },
  { type: 'retriever', label: '检索器', icon: BookOpen, description: '从向量库检索相关内容', shortcut: 'R', color: '#06b6d4', bgColor: '#fff' },
  { type: 'reranker', label: '重排序', icon: BookOpen, description: '对检索结果重排序', shortcut: 'R', color: '#06b6d4', bgColor: '#fff' },
]

const agentNodes = [
  { type: 'agent', label: 'Agent', icon: Bot, description: 'AI Agent 执行复杂任务', shortcut: 'G', color: '#8b5cf6', bgColor: '#fff' },
  { type: 'planner', label: '任务规划', icon: Bot, description: '分解复杂任务为子任务', shortcut: 'P', color: '#8b5cf6', bgColor: '#fff' },
  { type: 'executor', label: '任务执行', icon: Bot, description: '执行规划的任务', shortcut: 'X', color: '#8b5cf6', bgColor: '#fff' },
  { type: 'memory', label: '记忆存储', icon: Bot, description: 'Agent 记忆管理', shortcut: 'M', color: '#8b5cf6', bgColor: '#fff' },
]

const dataProcessNodes = [
  { type: 'file_reader', label: '文件读取', icon: Database, description: '读取各种格式的文件', shortcut: 'R', color: '#10b981', bgColor: '#fff' },
  { type: 'file_writer', label: '文件写入', icon: Database, description: '写入数据到文件', shortcut: 'W', color: '#10b981', bgColor: '#fff' },
  { type: 'web_scraper', label: '网页抓取', icon: Database, description: '从网页提取数据', shortcut: 'S', color: '#10b981', bgColor: '#fff' },
  { type: 'csv_transform', label: 'CSV 转换', icon: Database, description: 'CSV 数据转换处理', shortcut: 'C', color: '#10b981', bgColor: '#fff' },
  { type: 'json_transform', label: 'JSON 转换', icon: Database, description: 'JSON 数据转换处理', shortcut: 'J', color: '#10b981', bgColor: '#fff' },
]

const allNodes = [...controlNodes, ...aiNodes, ...dataNodes, ...toolNodes, ...multimodalNodes, ...modelTrainingNodes, ...ragNodes, ...agentNodes, ...dataProcessNodes]

// #region DEBUG: check undefined icons
;(function(){
  const undefinedIcons = allNodes.filter(n => typeof n.icon === 'undefined').map(n => n.type)
  if (undefinedIcons.length > 0) {
    console.warn('[DEBUG] UNDEFINED_ICONS:', undefinedIcons)
  }
})()
// #endregion

const nodeSearchQuery = ref('')

const filteredControlNodes = computed(() => {
  if (!nodeSearchQuery.value) return controlNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return controlNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredAiNodes = computed(() => {
  if (!nodeSearchQuery.value) return aiNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return aiNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredDataNodes = computed(() => {
  if (!nodeSearchQuery.value) return dataNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return dataNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredToolNodes = computed(() => {
  if (!nodeSearchQuery.value) return toolNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return toolNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredMultimodalNodes = computed(() => {
  if (!nodeSearchQuery.value) return multimodalNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return multimodalNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredModelTrainingNodes = computed(() => {
  if (!nodeSearchQuery.value) return modelTrainingNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return modelTrainingNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredRagNodes = computed(() => {
  if (!nodeSearchQuery.value) return ragNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return ragNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredAgentNodes = computed(() => {
  if (!nodeSearchQuery.value) return agentNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return agentNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const filteredDataProcessNodes = computed(() => {
  if (!nodeSearchQuery.value) return dataProcessNodes
  const q = nodeSearchQuery.value.toLowerCase()
  return dataProcessNodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.shortcut.toLowerCase().includes(q)
  )
})

const hasAnyNodes = computed(() =>
  filteredControlNodes.value.length ||
  filteredAiNodes.value.length ||
  filteredDataNodes.value.length ||
  filteredToolNodes.value.length ||
  filteredMultimodalNodes.value.length ||
  filteredModelTrainingNodes.value.length ||
  filteredRagNodes.value.length ||
  filteredAgentNodes.value.length ||
  filteredDataProcessNodes.value.length
)

// Custom node type components for Vue Flow
// markRaw prevents Vue from making component definitions reactive (avoids performance overhead warning)
const nodeTypes = markRaw({
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  prompt: PromptNode,
  condition: ConditionNode,
  loop: LoopNode,
  input: InputNode,
  output: OutputNode,
  code: CodeNode,
  variable: VariableNode,
  tool: ToolNode,
  http: HttpNode,
  switch: SwitchNode,
  delay: DelayNode,
  transform: TransformNode,
  email: EmailNode,
  subworkflow: SubworkflowNode,
  image_generation: ImageGenerationNode,
  video_generation: VideoGenerationNode,
  audio_generation: AudioGenerationNode,
  subtitle_generation: SubtitleGenerationNode,
  image_editing: ImageEditingNode,
  dataset_upload: DatasetUploadNode,
  data_annotation: DataAnnotationNode,
  data_augmentation: DataAugmentationNode,
  model_training: ModelTrainingNode,
  model_evaluation: ModelEvaluationNode,
  model_deployment: ModelDeploymentNode,
  website_generator: WebsiteGeneratorNode,
  document_loader: DocumentLoaderNode,
  embedding: EmbeddingNode,
  vector_store: VectorStoreNode,
  retriever: RetrieverNode,
  reranker: RerankerNode,
  agent: AgentNodeComponent,
  planner: PlannerNode,
  executor: ExecutorNode,
  memory: MemoryNode,
  file_reader: FileReaderNode,
  file_writer: FileWriterNode,
  web_scraper: WebScraperNodeComponent,
  csv_transform: CsvTransformNode,
  json_transform: JsonTransformNode
})

// MiniMap node colors matching the actual node styles
const minimapNodeColor = (node) => {
  const colorMap = {
    start: '#10b981',
    end: '#ef4444',
    llm: '#3b82f6',
    prompt: '#f59e0b',
    condition: '#3b82f6',
    loop: '#f59e0b',
    input: '#06b6d4',
    output: '#84cc16',
    code: '#f97316',
    variable: '#22c55e',
    tool: '#ec4899',
    http: '#f97316',
    switch: '#3b82f6',
    delay: '#14b8a6',
    subworkflow: '#8b5cf6',
    // Domain node types (Wave 2)
    image_generation: '#ec4899',
    video_generation: '#ec4899',
    audio_generation: '#ec4899',
    subtitle_generation: '#ec4899',
    image_editing: '#ec4899',
    dataset_upload: '#f59e0b',
    data_annotation: '#f59e0b',
    data_augmentation: '#f59e0b',
    model_training: '#f59e0b',
    model_evaluation: '#f59e0b',
    model_deployment: '#f59e0b',
    document_loader: '#06b6d4',
    embedding: '#06b6d4',
    vector_store: '#06b6d4',
    retriever: '#06b6d4',
    reranker: '#06b6d4',
    agent: '#8b5cf6',
    planner: '#8b5cf6',
    executor: '#8b5cf6',
    memory: '#8b5cf6',
    file_reader: '#10b981',
    file_writer: '#10b981',
    web_scraper: '#10b981',
    csv_transform: '#10b981',
    json_transform: '#10b981',
  }
  return colorMap[node.type] || '#6b7280'
}

// Vue Flow composable
const {
  applyNodeChanges,
  applyEdgeChanges,
  zoomIn,
  zoomOut,
  fitView,
  addNodes,
  project,
  onNodeClick,
} = useVueFlow()

onNodeClick(({ node }) => {
  selectedNode.value = node
  selectedEdge.value = null
})

function onNodeSelect(nodeId) {
  const node = nodes.value.find(n => n.id === nodeId)
  if (node) {
    selectedNode.value = node
    selectedEdge.value = null
  }
}

// 撤销/重做
const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value < history.value.length - 1)

// 选中节点数据

// 保存历史状态
function saveHistory() {
  const state = JSON.stringify({ nodes: nodes.value, edges: edges.value })
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(state)
  historyIndex.value = history.value.length - 1
  isDirty.value = true
}

function handleUndo() {
  if (canUndo.value) {
    historyIndex.value--
    const state = JSON.parse(history.value[historyIndex.value])
    nodes.value = state.nodes
    edges.value = state.edges
    isDirty.value = true
  }
}

function handleRedo() {
  if (canRedo.value) {
    historyIndex.value++
    const state = JSON.parse(history.value[historyIndex.value])
    nodes.value = state.nodes
    edges.value = state.edges
    isDirty.value = true
  }
}

// 拖拽开始
function onDragStart(event, nodeType) {
  event.dataTransfer.setData('application/flowly-node', JSON.stringify(nodeType))
  event.dataTransfer.effectAllowed = 'move'
}

// 拖放
function onDrop(event) {
  const nodeDataStr = event.dataTransfer.getData('application/flowly-node')
  if (!nodeDataStr) return

  const nodeType = JSON.parse(nodeDataStr)
  const { left, top } = event.currentTarget.getBoundingClientRect()
  const position = project({
    x: event.clientX - left,
    y: event.clientY - top
  })

  const newNode = {
    id: `node_${Date.now()}`,
    type: nodeType.type,
    position,
    data: {
      label: nodeType.label,
      type: nodeType.type,
      config: getDefaultConfig(nodeType.type),
      description: ''
    }
  }

  nodes.value = [...nodes.value, newNode]
  saveHistory()
}

// 获取节点默认配置
function getDefaultConfig(type) {
  const defaults = {
    start: {},
    end: {},
    input: { placeholder: '请输入...' },
    output: {},
    llm: { model: '', temperature: 0.7, systemPrompt: '', userTemplate: '{input}' },
    prompt: { template: '', variables: [] },
    condition: { conditions: [], defaultBranch: 'false' },
    loop: {
      loopType: 'for',
      start: 0,
      end: 10,
      step: 1,
      whileCondition: 'i < 10',
      items: '',
      maxIterations: 100
    },
    variable: {
      operation: 'set',
      variableName: '',
      variableValue: '',
      scope: 'local'
    },
    tool: { tool: 'calculator', parameters: {} },
    http: { method: 'GET', url: '', headers: '{}', body: '' },
    code: { code: 'input = input\noutput = {"result": input}' },
    subworkflow: {
      subworkflowId: '',
      subworkflowName: '',
      version: 'latest',
      inputMapping: [],
      outputMapping: [],
      executionMode: 'sync',
      timeout: 300,
      onError: 'stop',
      fallbackValue: null
    },
    switch: {
      label: '分支',
      description: '',
      branches: [
        { id: 'branch_1', label: '条件 1', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' },
        { id: 'branch_2', label: '条件 2', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' }
      ],
      defaultBranch: '默认'
    },
    transform: {
      label: '数据转换',
      description: '',
      transformType: 'map',
      mappings: [],
      filterExpression: '',
      sortField: '',
      sortOrder: 'asc'
    },
    email: {
      label: '发送邮件',
      description: '',
      to: '',
      cc: '',
      bcc: '',
      fromEmail: '',
      subject: '',
      isHtml: false,
      body: '',
      smtpConfig: {
        server: '',
        port: 587,
        useTls: true,
        username: '',
        password: ''
      }
    }
  }
  return defaults[type] || {}
}

// 连线
function onConnect(params) {
  const newEdge = {
    id: `edge_${Date.now()}`,
    source: params.source,
    target: params.target,
    sourceHandle: params.sourceHandle,
    targetHandle: params.targetHandle,
    label: '',
    type: 'default',
    animated: false,
    markerEnd: MarkerType.ArrowClosed
  }
  edges.value = [...edges.value, newEdge]
  markDirty()
  saveHistory()
}

// 节点点击（使用 useVueFlow composable 的 onNodeClick 替代 @node-click）
function handleEdgeClick(event) {
  selectedEdge.value = event.edge
  selectedNode.value = null
}

// 画布点击
function onPaneClick() {
  selectedNode.value = null
  selectedEdge.value = null
}

// VueFlow 节点尺寸计算完成后执行 fitView
// nodes-initialized 事件在 ResizeObserver 测量完所有节点尺寸后触发
// 这确保 fitView 能获取正确的节点边界，从而正确计算缩放比例
function onNodesInitialized() {
  if (!isNewWorkflow.value && nodes.value.length > 0) {
    nextTick(() => {
      nextTick(() => {
        if (vueFlowRef.value) {
          vueFlowRef.value.fitView({ padding: 0.2, duration: 400 })
        }
      })
    })
  }
}

// 节点变化（先交给 Vue Flow 应用变更，再标记脏状态）
function handleNodesChange(changes) {
  applyNodeChanges(changes)
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      markDirty()
    }
  })
}

// 连线变化
function handleEdgesChange(changes) {
  applyEdgeChanges(changes)
}

// 节点拖拽停止
function onNodeDragStop() {
  nodes.value = [...nodes.value]
  markDirty()
}

// 节点拖拽中 - 实时同步位置到响应式数组
function onNodeDrag({ node }) {
  const idx = nodes.value.findIndex(n => n.id === node.id)
  if (idx !== -1) {
    const updated = [...nodes.value]
    updated[idx] = { ...updated[idx], position: { x: node.position.x, y: node.position.y } }
    nodes.value = updated
  }
}

// 节点右键菜单
function onNodeContextMenu(event) {
  // 可以添加右键菜单
}

// 标记为已修改
function markDirty() {
  isDirty.value = true
}

// 添加工具函数
function addVariable() {
  if (selectedNodeData.value?.config?.variables) {
    selectedNodeData.value.config.variables.push({ name: '', value: '' })
    markDirty()
  }
}

function removeVariable(index) {
  if (selectedNodeData.value?.config?.variables) {
    selectedNodeData.value.config.variables.splice(index, 1)
    markDirty()
  }
}

function addCondition() {
  if (selectedNodeData.value?.config?.conditions) {
    selectedNodeData.value.config.conditions.push({
      field: '',
      operator: 'equals',
      value: '',
      branch: 'true'
    })
    markDirty()
  }
}

function removeCondition(index) {
  if (selectedNodeData.value?.config?.conditions) {
    selectedNodeData.value.config.conditions.splice(index, 1)
    markDirty()
  }
}

// 删除节点
function handleDeleteNode() {
  if (selectedNode.value) {
    nodes.value = nodes.value.filter(n => n.id !== selectedNode.value.id)
    edges.value = edges.value.filter(
      e => e.source !== selectedNode.value.id && e.target !== selectedNode.value.id
    )
    selectedNode.value = null
    saveHistory()
  }
}

// 删除连线
function handleDeleteEdge() {
  if (selectedEdge.value) {
    edges.value = edges.value.filter(e => e.id !== selectedEdge.value.id)
    selectedEdge.value = null
    saveHistory()
  }
}

// 缩放控制
function handleZoomIn() {
  zoomIn()
}

function handleZoomOut() {
  zoomOut()
}

function handleFitView() {
  fitView()
}

function handleAutoLayout() {
  const layouted = autoLayoutWorkflow(nodes.value, edges.value, {
    nodeWidth: 220,
    nodeHeight: 140,
    gapX: 160,
    gapY: 60,
    startX: 80,
    startY: 80
  })
  nodes.value = layouted
  nextTick(() => {
    fitView({ padding: 0.1, duration: 300 })
  })
}

function handleToolbarCommand(cmd) {
  switch (cmd) {
    case 'variable':
      variablePanelVisible.value = true
      break
    case 'assistant':
      showAssistant.value = true
      break
    case 'theme': {
      const themeBtn = document.querySelector('[data-theme-switcher]')
      if (themeBtn) themeBtn.click()
      break
    }
  }
}

// 名称修改
function handleNameBlur() {
  if (workflowName.value.trim()) {
    markDirty()
  }
}

// 验证工作流
async function handleValidate() {
  try {
    const { validateWorkflowSchema, highlightErrorNodes, showValidationResult } = await import('@/utils/workflow-schema')

    // 先清除之前的高亮
    clearErrorHighlights()

    // 执行验证
    const result = validateWorkflowSchema(nodes.value, edges.value)

    // 高亮错误节点
    highlightErrorNodes(nodes.value, result.nodeErrors)

    // 显示验证结果
    showValidationResult(result)

    // 更新验证对话框数据（兼容现有对话框）
    validationResult.value = {
      valid: result.valid,
      errors: result.errors.map(e => e.message),
      warnings: result.warnings.map(w => w.message)
    }
    showValidateDialog.value = true
  } catch (err) {
    console.error('验证失败:', err)
    appStore.error('验证失败')
  }
}

// 清除错误高亮
function clearErrorHighlights() {
  for (const node of nodes.value) {
    if (node.data?.hasError) {
      node.data = {
        ...node.data,
        hasError: false,
        errorMessages: []
      }
    }
  }
}

// 高亮指定节点（由 WorkflowOptimizer 调用）
function handleHighlightNodes(nodeIds) {
  clearErrorHighlights()
  for (const nodeId of nodeIds) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.data = {
        ...node.data,
        hasError: true,
        errorMessages: ['AI建议修改的节点']
      }
    }
  }
}

// 应用 AI 修复建议
async function handleApplyFix(fixDescription, nodeId) {
  appStore.success(`已应用修复: ${fixDescription}`)
}

// 打开触发器配置
function openTriggerConfig() {
  if (isNewWorkflow.value) {
    appStore.warning('请先保存工作流后再配置触发器')
    return
  }
  triggerConfigVisible.value = true
}

// 保存
async function handleSave() {
  try {
    const saveNodes = nodes.value.map((n, index) => ({
      id: n.id,
      node_type: n.type,
      name: n.data.label,
      description: n.data.description || '',
      position_x: n.position.x,
      position_y: n.position.y,
      sort_order: index,
      config: n.data.config || {}
    }))
    const saveEdges = edges.value.map(e => ({
      source_node: e.source,
      target_node: e.target,
      label: e.label || '',
      animated: e.animated || false
    }))

    if (isNewWorkflow.value) {
      const result = await workflowStore.createWorkflow({ name: workflowName.value, nodes: saveNodes, edges: saveEdges })
      appStore.success('工作流创建成功')
      router.replace(`/workflows/${result.id}/edit`)
    } else {
      await workflowStore.updateWorkflow(workflowId.value, { name: workflowName.value, nodes: saveNodes, edges: saveEdges })
      appStore.success('工作流已保存')
    }

    isDirty.value = false
  } catch (err) {
    const resp = err?.response?.data
    let errorMsg = resp?.detail || err?.message

    // Extract validation errors for nodes/edges
    if (resp && typeof resp === 'object') {
      const msgs = []
      if (resp.nodes) msgs.push(`节点: ${Array.isArray(resp.nodes) ? resp.nodes[0] : resp.nodes}`)
      if (resp.edges) msgs.push(`连线: ${Array.isArray(resp.edges) ? resp.edges[0] : resp.edges}`)
      if (resp.node_type) msgs.push(`节点类型: ${Array.isArray(resp.node_type) ? resp.node_type[0] : resp.node_type}`)
      if (resp.non_field_errors) msgs.push(Array.isArray(resp.non_field_errors) ? resp.non_field_errors[0] : resp.non_field_errors)
      if (msgs.length > 0) {
        errorMsg = msgs.join('; ')
      }
    }

    console.error('[handleSave] Failed to save workflow:', err, { responseData: resp })
    if (errorMsg) {
      appStore.error(`保存失败: ${errorMsg}`)
    }
  }
}

// 执行
function handleExecute() {
  if (isDirty.value) {
    appStore.warning('请先保存工作流')
    return
  }
  showExecutionPanel.value = true
  startExecution()
}

// 执行引擎
async function startExecution() {
  executionLogs.value = []
  executionStatus.value = 'running'
  executionStartTime.value = Date.now()
  elapsedTimer.value = setInterval(() => {}, 1000)

  try {
    const resp = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/workflows/${workflowId.value}/execute/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify({ input_data: {} })
      }
    )
    const data = await resp.json()

    if (!resp.ok) {
      throw new Error(data.error || data.message || '执行失败')
    }

    if (data.execution_id) {
      executionId.value = data.execution_id
      await pollExecutionResult(data.execution_id)
    } else {
      // 同步执行，结果直接返回
      executionStatus.value = 'completed'
      executionLogs.value.push({ type: 'info', time: new Date().toLocaleTimeString(), text: '执行完成' })
    }
  } catch (err) {
    executionStatus.value = 'failed'
    executionLogs.value.push({ type: 'error', time: new Date().toLocaleTimeString(), text: err.message })
  }
}

// 轮询执行结果
async function pollExecutionResult(execId) {
  const poll = async () => {
    if (executionStatus.value === 'cancelled') return
    elapsedTick.value++ // 触发 elapsed timer 更新
    try {
      const resp = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'}/executions/${execId}/`,
        { headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } }
      )
      const data = await resp.json()
      const exec = data.data || data

      if (exec.status === 'completed') {
        executionStatus.value = 'completed'
        executionLogs.value.push({ type: 'success', time: new Date().toLocaleTimeString(), text: `执行完成 (耗时 ${exec.duration_seconds || 0}s)` })
        return
      } else if (exec.status === 'failed') {
        executionStatus.value = 'failed'
        executionLogs.value.push({ type: 'error', time: new Date().toLocaleTimeString(), text: exec.error_message || '执行失败' })
        return
      }

      if (exec.node_executions) {
        exec.node_executions.forEach(ne => {
          executionLogs.value.push({
            type: ne.status === 'failed' ? 'error' : 'info',
            time: new Date().toLocaleTimeString(),
            text: `${ne.node_name || ne.node}: ${ne.status} ${ne.error_message ? '— ' + ne.error_message : ''}`
          })
        })
      }

      executionLogs.value.push({ type: 'info', time: new Date().toLocaleTimeString(), text: '执行中...' })
      setTimeout(poll, 2000)
    } catch {
      setTimeout(poll, 3000)
    }
  }
  await poll()
}

function cancelExecution() {
  executionStatus.value = 'cancelled'
  executionLogs.value.push({ type: 'info', time: new Date().toLocaleTimeString(), text: '已取消' })
}

// 返回
function handleBack() {
  if (isDirty.value) {
    appStore.confirm({
      title: '未保存的更改',
      message: '您有未保存的更改，确定要离开吗？',
      confirmText: '离开',
      cancelText: '取消'
    }).then(() => {
      router.push('/workflows')
    })
  } else {
    router.push('/workflows')
  }
}

// 加载模型和工具列表
async function loadModelsAndTools() {
  try {
    const [modelsRes, toolsRes] = await Promise.allSettled([
      workflowStore.fetchAvailableModels({ type: 'chat' }),
      workflowStore.fetchAvailableTools()
    ])

    if (modelsRes.status === 'fulfilled' && modelsRes.value) {
      availableModels.value = modelsRes.value.map(m => ({
        value: m.model_id || m.id,
        label: `${m.name} (${m.provider?.name || m.provider_name || 'Unknown'})`
      }))
    }

    if (toolsRes.status === 'fulfilled' && toolsRes.value) {
      availableTools.value = toolsRes.value.map(t => ({
        value: t.name,
        label: t.name
      }))
    }
  } catch {
    // Error shown via appStore
  }
}

onMounted(async () => {
  // 初始化历史
  saveHistory()

  // 加载模型和工具列表
  loadModelsAndTools()

  if (!isNewWorkflow.value) {
    try {
      await workflowStore.fetchWorkflow(workflowId.value)
      workflowName.value = workflowStore.currentWorkflow?.name || '未命名工作流'

      // Store already has Vue Flow format data from backendWorkflowToFrontend
      nodes.value = [...(workflowStore.nodes || [])]

      // 自动布局：如果所有节点都在 (0,0)，使用DAG拓扑分层布局
      const allZero = nodes.value.every(n => n.position?.x === 0 && n.position?.y === 0)
      if (allZero && nodes.value.length > 0) {
        const layoutedNodes = autoLayoutWorkflow(nodes.value, workflowStore.edges || [])
        nodes.value = layoutedNodes
      }

      edges.value = (workflowStore.edges || [])
        .map(e => ({
          ...e,
          // source_node_id is the integer ID from backend; source is the string ID
          source: String(e.source || e.source_node_id || ''),
          target: String(e.target || e.target_node_id || ''),
          markerEnd: MarkerType.ArrowClosed
        }))
        .filter(e => e.source && e.source !== 'undefined' && e.target && e.target !== 'undefined')

      // 更新历史
      saveHistory()

      // 自动适应画布，让所有节点可见
      // 使用 vueFlowRef.value.fitView() 调用实例方法
      // nodes-initialized 事件会再次触发 fitView，双重保障
      await nextTick()
      await nextTick()
      if (vueFlowRef.value) {
        vueFlowRef.value.fitView({ padding: 0.2, duration: 600 })
      }
    } catch (err) {
      appStore.error('加载工作流失败')
    }
  }
})

// 监听节点和连线变化
watch([nodes, edges], () => {
  if (!isDirty.value) return
}, { deep: true })

// 执行日志自动滚动到底部
watch(executionLogs, async () => {
  await nextTick()
  if (execPanelBodyRef.value) {
    execPanelBodyRef.value.scrollTop = execPanelBodyRef.value.scrollHeight
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.workflow-editor {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 $spacing-4;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  z-index: 10;
  gap: $spacing-3;
  flex-shrink: 0;
}

// 工具栏三段式布局
.toolbar-section {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  &--left {
    flex-shrink: 0;
    max-width: 100%;
  }

  &--center {
    flex: 1;
    justify-content: center;
    flex-wrap: wrap;
    gap: $spacing-2;
    overflow: hidden;
  }

  &--right {
    flex-shrink: 0;
    flex-wrap: nowrap;
    justify-content: flex-end;
  }
}

.toolbar-back-btn {
  flex-shrink: 0;
}

.toolbar-btn-group {
  display: inline-flex;
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;

  .el-button {
    border: none;
    border-radius: 0;
    padding: 6px 10px;

    &:not(:last-child) {
      border-right: 1px solid var(--border-primary);
    }
  }

  &--single {
    border: none;
    gap: 2px;

    .el-button {
      border: 1px solid var(--border-primary);
      border-radius: $radius-md;
      padding: 6px 10px;
    }
  }
}

.workflow-name-wrapper {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  overflow: hidden;
  min-width: 0;
}

.workflow-name-input {
  background: transparent;
  border: none;
  font-size: $font-size-base;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  min-width: 200px;
  max-width: 360px;

  &:hover,
  &:focus {
    background-color: var(--bg-hover);
    outline: none;
  }
}

.unsaved-indicator {
  font-size: $font-size-xs;
  color: $color-warning;
  flex-shrink: 0;
}

// 核心按钮：小屏幕时隐藏文字
.toolbar-core-btn {
  .btn-label {
    transition: opacity 0.2s;
  }
}

.toolbar-more-dropdown {
  flex-shrink: 0;
}

.toolbar-more-btn {
  padding: 6px 8px !important;
}

// 响应式断点
// 1. 1200px 以下：隐藏核心按钮文字
@media (max-width: 1200px) {
  .toolbar-core-btn {
    .btn-label {
      display: none;
    }

    padding: 6px 10px !important;
    min-width: auto;
  }
}

// 2. 1000px 以下：隐藏中心区域的触发器文字
@media (max-width: 1000px) {
  .toolbar-section--center {
    .toolbar-btn-group--single .el-button {
      padding: 6px 8px;

      span:not(.el-icon) {
        display: none;
      }
    }
  }
}

// 3. 850px 以下：隐藏验证/保存/执行的文字，折叠到图标
@media (max-width: 850px) {
  .toolbar-core-btn {
    .btn-label {
      display: none;
    }
  }

  .workflow-name-input {
    min-width: 150px;
    max-width: 250px;
  }
}

// 4. 700px 以下：隐藏中心区域所有文字，仅保留图标按钮
@media (max-width: 700px) {
  .toolbar-section--center {
    .el-button {
      span:not(.el-icon) {
        display: none;
      }
    }
  }

  .workflow-name-input {
    min-width: 100px;
    max-width: 160px;
  }
}

// 5. 500px 以下：隐藏连线文字，仅图标
@media (max-width: 500px) {
  .toolbar-section--center {
    .toolbar-btn-group--single .el-button span {
      display: none;
    }
  }

  .workflow-name-input {
    min-width: 80px;
    max-width: 120px;
  }
}

// 超小屏幕完全隐藏中间区域（保留画布操作）
@media (max-width: 380px) {
  .toolbar-section--center {
    display: none;
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.node-panel {
  width: 260px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  overflow-y: auto;
}

.panel-section {
  padding: $spacing-4;
}

.panel-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  letter-spacing: 0.02em;
}

.node-search {
  margin-bottom: $spacing-4;

  .el-input__wrapper {
    background: var(--bg-tertiary) !important;
    box-shadow: 0 0 0 1px var(--border-primary) inset !important;
  }

  .el-input__inner {
    color: var(--text-primary) !important;
  }

  .el-input__prefix {
    color: var(--text-tertiary) !important;
  }
}

.node-category {
  margin-bottom: $spacing-4;
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-bottom: $spacing-2;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: $font-weight-medium;

  .category-count {
    background: var(--bg-tertiary);
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 10px;
  }
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: grab;
  transition: all $transition-fast;
  margin-bottom: $spacing-2;

  &:hover {
    border-color: var(--node-color, var(--accent-primary));
    background-color: var(--bg-hover);
    transform: translateX(2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  &:active {
    cursor: grabbing;
    transform: scale(0.98);
  }
}

.node-item-preview {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-label {
  font-size: $font-size-sm;
  font-weight: $font-weight-medium;
  color: var(--text-primary);
  line-height: 1.2;
}

.node-desc {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-shortcut {
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 5px;
  border-radius: 4px;
  border: 1.5px solid;
  flex-shrink: 0;
  letter-spacing: 0;
  opacity: 0.8;
  line-height: 1;
}

.node-icon {
  width: 16px;
  height: 16px;
}

.node-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-2;
  padding: $spacing-6;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  text-align: center;

  .empty-icon {
    width: 24px;
    height: 24px;
    opacity: 0.5;
  }
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  background-color: var(--bg-primary);
}

.empty-canvas {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;

  .empty-content {
    text-align: center;

    .empty-icon-wrapper {
      width: 80px;
      height: 80px;
      margin: 0 auto $spacing-4;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(59, 130, 246, 0.08);
      border: 1px solid rgba(59, 130, 246, 0.2);
      border-radius: 24px;
    }

    .empty-icon {
      width: 40px;
      height: 40px;
      color: rgba(59, 130, 246, 0.6);
    }

    h3 {
      color: var(--text-primary);
      margin: 0 0 $spacing-2;
      font-size: $font-size-xl;
      font-weight: $font-weight-semibold;
    }

    p {
      color: var(--text-tertiary);
      margin: 0;
      font-size: $font-size-sm;
    }

    .quick-hint-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $spacing-2;
      margin-top: $spacing-4;
      flex-wrap: wrap;

      kbd {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 26px;
        height: 26px;
        padding: 0 6px;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-primary);
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        color: var(--text-secondary);
        box-shadow: 0 2px 0 var(--border-primary);
      }

      span {
        font-size: $font-size-xs;
        color: var(--text-tertiary);
      }
    }
  }
}

.property-panel {
  width: 340px;
  background-color: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  overflow-y: auto;
  transform: translateX(100%);
  transition: transform $transition-normal;

  &.visible {
    transform: translateX(0);
  }
}

.property-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  h3 {
    margin: 0;
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }
}

.property-form {
  padding: $spacing-4;
}

.form-group {
  margin-bottom: $spacing-4;

  label {
    display: block;
    margin-bottom: $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
  }

  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
  }
}

.variable-list,
.condition-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.variable-item,
.condition-item {
  display: flex;
  gap: $spacing-2;
  align-items: center;

  .el-input {
    flex: 1;
  }

  .el-select {
    width: 100px;
  }
}

.code-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
  }
}

.property-actions {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);

  .el-button {
    width: 100%;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.empty-properties {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;

  .empty-content {
    text-align: center;

    .empty-icon {
      width: 48px;
      height: 48px;
      color: var(--text-tertiary);
      margin-bottom: $spacing-3;
    }

    p {
      color: var(--text-tertiary);
      margin: 0;
    }
  }
}

.validate-success {
  text-align: center;
  padding: $spacing-6;

  .success-icon {
    width: 48px;
    height: 48px;
    color: $color-success;
    margin-bottom: $spacing-4;
  }
}

.validate-errors,
.warning-list {
  h4 {
    margin: 0 0 $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
  }

  ul {
    margin: 0;
    padding-left: $spacing-5;
  }

  li {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    margin-bottom: $spacing-1;
  }
}

.error-list {
  margin-bottom: $spacing-4;

  li {
    color: $color-error;
  }
}

// ============================================================
// 错误节点高亮样式
// ============================================================
:deep(.vue-flow__node) {
  &.has-error {
    .node-card,
    .node-wrapper {
      background: rgba(239, 68, 68, 0.15) !important;
      border: 2px solid var(--el-color-danger, #ef4444) !important;
      animation: error-shake 0.3s ease-in-out;
      box-shadow: 0 0 12px rgba(239, 68, 68, 0.4) !important;
    }
  }

  &.has-warning {
    .node-card,
    .node-wrapper {
      background: rgba(245, 158, 11, 0.15) !important;
      border: 2px solid var(--el-color-warning, #f59e0b) !important;
      box-shadow: 0 0 8px rgba(245, 158, 11, 0.3) !important;
    }
  }
}

@keyframes error-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

// ============================================================
// 快速添加菜单样式
// ============================================================
.quick-add-menu {
  position: absolute;
  z-index: 100;
  background: var(--bg-secondary, #1a1a2e);
  border: 1px solid var(--border-primary, rgba(255,255,255,0.1));
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255,255,255,0.05) inset;
  width: 320px;
  max-height: 480px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(20px);
}

.quick-add-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-3 $spacing-4;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-tertiary, #0f0f1a);

  .menu-icon {
    width: 16px;
    height: 16px;
    color: $color-primary;
  }

  span {
    flex: 1;
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-tertiary);
    padding: 2px;
    border-radius: 4px;
    display: flex;
    align-items: center;

    &:hover {
      color: var(--text-primary);
      background: var(--bg-hover);
    }
  }
}

.quick-add-body {
  padding: $spacing-3;
  overflow-y: auto;
  max-height: 400px;
}

.quick-add-section {
  margin-bottom: $spacing-3;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: $spacing-2;
  padding-left: $spacing-1;
}

.quick-add-items {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-2;
}

.quick-add-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: $spacing-3 $spacing-2;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 500;

  &:hover {
    background: var(--bg-hover);
    border-color: $color-primary;
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(59, 130, 246, 0.2);
  }

  &:active {
    transform: translateY(0) scale(0.98);
  }

  .item-icon {
    width: 20px;
    height: 20px;
  }
}

// ============================================================
// 自动连线模式指示器
// ============================================================
.auto-connect-indicator {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3 $spacing-4;
  background: rgba(59, 130, 246, 0.95);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
  color: white;
  font-size: $font-size-sm;
  font-weight: 500;
  white-space: nowrap;

  .indicator-icon {
    width: 16px;
    height: 16px;
    animation: pulse 1.5s infinite;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

// ============================================================
// 画布状态栏
// ============================================================
.canvas-status-bar {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  display: flex;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-2 $spacing-4;
  background: rgba(15, 15, 26, 0.85);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: var(--text-secondary);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.03) inset;

  .status-item {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-icon {
    width: 12px;
    height: 12px;
  }

  .connect-mode {
    color: #3b82f6;
    font-weight: 500;
  }
}

// ============================================================
// 空状态提示增强
// ============================================================
.empty-canvas {
  .empty-content {
    .quick-hint {
      margin-top: $spacing-3;
      font-size: 11px;
      color: var(--text-tertiary);
      background: var(--bg-tertiary);
      padding: 4px 8px;
      border-radius: 4px;
    }
  }
}

// ============================================
// 响应式设计 - Responsive Design
// ============================================

@media (max-width: 1024px) {
  .node-panel {
    width: 220px;
  }

  .property-panel {
    width: 300px;
  }
}

@media (max-width: 768px) {
  .editor-header {
    padding: $spacing-3 $spacing-4;

    .header-left,
    .header-right {
      gap: $spacing-2;
    }
  }

  .toolbar-center {
    display: none;
  }

  .node-panel {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 10;
    width: 260px;
    transform: translateX(-100%);
    transition: transform $transition-normal;
    box-shadow: $shadow-lg;

    &.open {
      transform: translateX(0);
    }
  }

  .property-panel {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    z-index: 10;
    width: 100%;
    max-width: 340px;
    box-shadow: $shadow-lg;
  }

  .canvas-wrapper {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .editor-header {
    padding: $spacing-2 $spacing-3;
  }

  .header-title {
    font-size: $font-size-base;
  }

  .el-button {
    padding: $spacing-2 $spacing-3;
    font-size: $font-size-sm;
  }
}

// =============================================================================
// 底部执行面板
// =============================================================================

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
}

.execution-bottom-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 320px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  z-index: 200;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.3);
}

.exec-panel-handle {
  height: 6px;
  cursor: pointer;
  background: transparent;
  border-radius: 3px 3px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
  transition: background 0.2s;

  &::after {
    content: '';
    display: block;
    width: 36px;
    height: 3px;
    border-radius: 2px;
    background: var(--border-primary);
    transition: background 0.2s;
  }

  &:hover::after {
    background: var(--text-muted);
  }
}

.exec-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;

  .exec-header-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .exec-icon {
      color: var(--color-primary, #6366f1);
      width: 16px;
      height: 16px;
    }

    .exec-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .exec-node-count {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
  }

  .exec-header-right {
    display: flex;
    align-items: center;
    gap: 8px;

    .exec-elapsed {
      font-size: 12px;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }
  }
}

.exec-panel-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  gap: 0;
  min-height: 0;
}

// 三栏布局
.exec-timeline {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .timeline-header {
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
  }

  .timeline-list {
    flex: 1;
    overflow-y: auto;
    padding: 6px 0;

    &::-webkit-scrollbar { width: 4px; }
    &::-webkit-scrollbar-track { background: transparent; }
    &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 2px; }
  }

  .timeline-empty {
    padding: 16px 12px;
    color: var(--text-muted);
    font-size: 12px;
    text-align: center;
  }
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: rgba(255,255,255,0.04); }
  &.node-running { background: rgba(59,130,246,0.08); }
  &.node-completed { background: rgba(16,185,129,0.06); }
  &.node-failed { background: rgba(239,68,68,0.08); }

  .timeline-status {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .tl-icon {
    width: 14px;
    height: 14px;
    &.success { color: #10b981; }
    &.error { color: #ef4444; }
    &.pending { color: var(--text-muted); }
    &.spinning { color: #3b82f6; }
  }

  .timeline-info {
    display: flex;
    flex-direction: column;
    min-width: 0;

    .tl-name {
      font-size: 12px;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tl-type {
      font-size: 10px;
      color: var(--text-muted);
    }
  }
}

.exec-output {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border-primary);

  .output-header {
    padding: 8px 16px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;

    .output-node-name {
      color: var(--text-primary);
      font-size: 12px;
      text-transform: none;
      letter-spacing: 0;
    }
  }

  .output-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;

    &::-webkit-scrollbar { width: 6px; }
    &::-webkit-scrollbar-track { background: transparent; }
    &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 3px; }
  }

  .output-placeholder {
    color: var(--text-muted);
    font-size: 12px;
    text-align: center;
    padding: 32px 0;
  }

  .output-running, .output-pending {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-muted);
    font-size: 12px;
    padding: 16px 0;
  }

  .output-success, .output-error {
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 12px;
  }

  .output-check { width: 16px; height: 16px; &.success { color: #10b981; } &.error { color: #ef4444; } }
  .output-spinner { color: #3b82f6; }
  .output-data {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    padding: 10px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
    margin-top: 8px;
  }

  .output-err-detail {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 11px;
    color: #ef4444;
    font-family: 'JetBrains Mono', monospace;
  }
}

.exec-summary {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .summary-header {
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;
  }

  .summary-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--border-primary);
    border-bottom: 1px solid var(--border-primary);
    flex-shrink: 0;

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 8px;
      background: var(--bg-secondary);
      gap: 2px;

      .stat-label {
        font-size: 10px;
        color: var(--text-muted);
      }

      .stat-value {
        font-size: 18px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: var(--text-primary);

        &.success { color: #10b981; }
        &.running { color: #3b82f6; }
        &.error { color: #ef4444; }
      }
    }
  }

  .summary-progress {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-primary);
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;

    .progress-track {
      flex: 1;
      height: 4px;
      background: rgba(255,255,255,0.08);
      border-radius: 2px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      border-radius: 2px;
      transition: width 0.3s ease;
    }

    .progress-pct {
      font-size: 11px;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-secondary);
      min-width: 32px;
      text-align: right;
    }
  }

  .summary-logs {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;

    .logs-header {
      padding: 6px 12px;
      font-size: 10px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-primary);
      flex-shrink: 0;
    }

    .logs-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 6px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      line-height: 1.5;

      &::-webkit-scrollbar { width: 4px; }
      &::-webkit-scrollbar-track { background: transparent; }
      &::-webkit-scrollbar-thumb { background: var(--border-primary); border-radius: 2px; }
    }
  }
}

.exec-empty {
  color: var(--text-muted);
  padding: 16px 0;
}

.exec-log-item {
  display: flex;
  gap: 12px;
  padding: 3px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);

  .log-time {
    color: var(--text-muted);
    flex-shrink: 0;
    font-size: 11px;
  }

  .log-text {
    color: var(--text-secondary);
    word-break: break-all;
  }

  &.log-success .log-text {
    color: #22c55e;
  }

  &.log-error .log-text {
    color: #ef4444;
  }

  &.log-warning .log-text {
    color: #f59e0b;
  }
}

.exec-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: var(--text-muted);

  .exec-spinner {
    display: inline-block;
    width: 12px;
    height: 12px;
    border: 2px solid var(--border-primary);
    border-top-color: var(--color-primary, #6366f1);
    border-radius: 50%;
    animation: exec-spin 0.8s linear infinite;
  }
}

@keyframes exec-spin {
  to { transform: rotate(360deg); }
}
</style>
