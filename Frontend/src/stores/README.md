# Pinia Store 命名规范

> 所有 Store 必须遵循本文件中的命名规范，以保证代码可读性和一致性。

## 一、Action 命名规范

### 1.1 命名模式速查表

| 动作类型 | 前缀/模式 | 示例 | 说明 |
|---------|-----------|------|------|
| 从 API 获取列表 | `fetch` + 复数名词 | `fetchWorkflows` | 必须处理 loading/error 状态 |
| 从 API 获取单个 | `fetch` + 单数名词 + `ById` | `fetchWorkflowById` | 必须处理 loading/error 状态 |
| 创建（POST） | `create` + 单数名词 | `createWorkflow` | 调用 API POST |
| 更新（PUT/PATCH） | `update` + 单数名词 | `updateWorkflow` | 调用 API PATCH |
| 删除（DELETE） | `delete` + 单数名词 | `deleteWorkflow` | 调用 API DELETE |
| 本地状态加载 | `load` + 名词 | `loadCanvasState` | 不调用 API，仅内存操作 |
| 本地状态保存 | `save` + 名词 | `saveCanvasState` | 不调用 API，仅内存操作 |
| 异步执行 | `execute` + 名词 | `executeWorkflow` | 触发后台任务 |
| 重置状态 | `reset` + 名词 | `resetForm` | 清空表单状态 |
| 切换状态 | `toggle` + 名词 | `toggleTheme` | 布尔值切换 |
| 批量操作 | `batch` + 动词 | `batchUpdatePositions` | 批量更新 |
| 清空数据 | `clear` + 名词 | `clearEditor` | 清空 store 数据 |

### 1.2 命名一致性检查清单

- [ ] 所有 fetch 调用必须设置 `isLoading` 并在 finally 中重置
- [ ] 所有 fetch 调用必须设置 `error` 并在 finally 中清空
- [ ] 所有 API 调用失败时必须抛出错误（让调用方处理）
- [ ] 列表获取用复数名词（`workflows` 而非 `workflowList`）
- [ ] 单个获取用单数名词 + `ById` 后缀
- [ ] 避免使用动词开头的无前缀 action（如 `getWorkflows` 应为 `fetchWorkflows`）

## 二、State 命名规范

### 2.1 状态变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `isLoading` | `boolean` | 通用加载状态 |
| `isSaving` | `boolean` | 保存中状态 |
| `isDirty` | `boolean` | 有未保存的更改 |
| `error` | `string \| null` | 当前错误信息 |
| `items` / `currentItem` | 数组/对象 | 数据状态 |
| `selectedItem` | 对象 | 当前选中项 |

### 2.2 复合命名

- `modelsLoading` - 模型加载中
- `toolsLoading` - 工具加载中
- `nodeTypesLoading` - 节点类型加载中
- `executionHistory` - 执行历史（名词）
- `currentExecution` - 当前执行（名词）

## 三、Getter 命名规范

| 类型 | 模式 | 示例 |
|------|------|------|
| 计算属性 | `has` + 名词 | `hasUnsavedChanges` |
| 计算属性 | `is` + 形容词 | `isLoading` |
| 计算属性 | 普通名词复数 | `workflowNodes` |

## 四、Store 文件结构模板

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/module'

export const useModuleStore = defineStore('module', () => {
  // State
  const items = ref([])
  const currentItem = ref(null)
  const isLoading = ref(false)
  const error = ref(null)

  // Getters
  const hasItems = computed(() => items.value.length > 0)

  // Actions - fetch 列表
  async function fetchItems(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.list(params)
      items.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - fetch 单个
  async function fetchItemById(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.getById(id)
      currentItem.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - create
  async function createItem(data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.create(data)
      items.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - update
  async function updateItem(id, data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.update(id, data)
      const index = items.value.findIndex(i => i.id === id)
      if (index !== -1) items.value[index] = response
      currentItem.value = { ...currentItem.value, ...response }
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - delete
  async function deleteItem(id) {
    isLoading.value = true
    error.value = null
    try {
      await api.delete(id)
      items.value = items.value.filter(i => i.id !== id)
      if (currentItem.value?.id === id) currentItem.value = null
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Actions - local (无 API 调用)
  function clearItems() {
    items.value = []
    currentItem.value = null
    error.value = null
  }

  return {
    // State
    items, currentItem, isLoading, error,
    // Getters
    hasItems,
    // Actions
    fetchItems, fetchItemById, createItem, updateItem, deleteItem, clearItems,
  }
})
```

## 五、已有 Store 命名审查

| Store | 状态 | 说明 |
|-------|------|------|
| `workflow.js` | ✅ 符合规范 | fetch/update/delete/create 模式一致 |
| `agent.js` | ✅ 符合规范 | |
| `auth.js` | ✅ 符合规范 | |
| `nlWorkflow.js` | ✅ 符合规范 | |
| `execution.js` | ✅ 符合规范 | |
| `variables.js` | ✅ 符合规范 | |

**结论**: 所有已有 Store 均符合命名规范，无需修改。
