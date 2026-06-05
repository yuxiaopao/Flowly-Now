/**
 * Variable Store - Workflow Variable Management
 */

import { defineStore } from 'pinia'

// Variable interpolation regex
const VARIABLE_REGEX = /\{\{\s*([^}]+)\s*\}\}/g
const JSON_PATH_REGEX = /\{\{\s*\$json\.([^}]+)\s*\}\}/g

export const useVariableStore = defineStore('variable', {
  state: () => ({
    // Global variables (accessible everywhere)
    globalVariables: {},

    // Workflow-specific variables
    workflowVariables: {},

    // Environment variables
    environments: {
      development: {},
      production: {}
    },

    // Current environment
    currentEnvironment: 'development',

    // Variable history for undo
    history: [],
    historyIndex: -1,

    // Built-in variables
    builtInVariables: {
      'workflow.id': 'Current workflow ID',
      'workflow.name': 'Current workflow name',
      'workflow.created_at': 'Workflow creation time',
      'execution.id': 'Current execution ID',
      'execution.started_at': 'Execution start time',
      'env.NODE_ENV': 'Node environment',
      'timestamp': 'Current timestamp',
      'date': 'Current date',
      'time': 'Current time',
      'random.uuid': 'Random UUID',
      'random.number': 'Random number'
    }
  }),

  getters: {
    // Get all variables for current environment
    allVariables: (state) => {
      return {
        ...state.globalVariables,
        ...state.workflowVariables,
        ...state.environments[state.currentEnvironment]
      }
    },

    // Get variables as array
    variablesList: (state) => {
      const vars = []
      const addVars = (obj, prefix = '') => {
        Object.entries(obj).forEach(([key, value]) => {
          const fullKey = prefix ? `${prefix}.${key}` : key
          if (typeof value === 'object' && value !== null) {
            addVars(value, fullKey)
          } else {
            vars.push({ key: fullKey, value, type: typeof value })
          }
        })
      }
      addVars(state.globalVariables, 'global')
      addVars(state.workflowVariables, 'workflow')
      addVars(state.environments[state.currentEnvironment], 'env')
      return vars
    },

    // Get variable by key (with path support)
    getVariable: (state) => (key) => {
      // Check built-in variables
      if (state.builtInVariables[key]) {
        return {
          value: getBuiltInValue(key),
          description: state.builtInVariables[key],
          isBuiltIn: true
        }
      }

      // Check environments
      for (const env of Object.keys(state.environments)) {
        if (state.environments[env][key] !== undefined) {
          return {
            value: state.environments[env][key],
            environment: env,
            isBuiltIn: false
          }
        }
      }

      // Check workflow variables
      if (state.workflowVariables[key] !== undefined) {
        return { value: state.workflowVariables[key], isBuiltIn: false }
      }

      // Check global variables
      if (state.globalVariables[key] !== undefined) {
        return { value: state.globalVariables[key], isBuiltIn: false }
      }

      return null
    },

    // Get variable count
    variableCount: (state) => {
      return (
        Object.keys(state.globalVariables).length +
        Object.keys(state.workflowVariables).length +
        Object.keys(state.environments[state.currentEnvironment]).length
      )
    },

    // Check if can undo
    canUndo: (state) => state.historyIndex > 0,

    // Check if can redo
    canRedo: (state) => state.historyIndex < state.history.length - 1
  },

  actions: {
    // ==================== Variable Management ====================

    setGlobalVariable(key, value, description = '') {
      this._saveToHistory()
      this.globalVariables[key] = value
      if (description) {
        this.globalVariables[`${key}_description`] = description
      }
    },

    setWorkflowVariable(key, value) {
      this._saveToHistory()
      this.workflowVariables[key] = value
    },

    setEnvironmentVariable(key, value, env = null) {
      this._saveToHistory()
      const targetEnv = env || this.currentEnvironment
      this.environments[targetEnv][key] = value
    },

    removeVariable(key, scope = 'global') {
      this._saveToHistory()
      switch (scope) {
        case 'global':
          delete this.globalVariables[key]
          break
        case 'workflow':
          delete this.workflowVariables[key]
          break
        case 'env':
        case 'environment':
          delete this.environments[this.currentEnvironment][key]
          break
      }
    },

    clearVariables(scope = 'all') {
      this._saveToHistory()
      switch (scope) {
        case 'global':
          this.globalVariables = {}
          break
        case 'workflow':
          this.workflowVariables = {}
          break
        case 'env':
        case 'environment':
          this.environments[this.currentEnvironment] = {}
          break
        case 'all':
          this.globalVariables = {}
          this.workflowVariables = {}
          this.environments = {
            development: {},
            production: {}
          }
          break
      }
    },

    // ==================== Environment Management ====================

    setEnvironment(env) {
      if (this.environments[env] !== undefined) {
        this.currentEnvironment = env
      }
    },

    createEnvironment(name) {
      if (!this.environments[name]) {
        this.environments[name] = {}
      }
    },

    deleteEnvironment(name) {
      if (this.environments[name] && name !== 'development' && name !== 'production') {
        delete this.environments[name]
        if (this.currentEnvironment === name) {
          this.currentEnvironment = 'development'
        }
      }
    },

    copyEnvironment(from, to) {
      if (this.environments[from]) {
        this.environments[to] = { ...this.environments[from] }
      }
    },

    // ==================== Variable Interpolation ====================

    /**
     * Interpolate variables in a string
     * Supports {{variable}} and {{$json.path.to.field}} syntax
     */
    interpolate(text, context = {}) {
      if (!text || typeof text !== 'string') {
        return text
      }

      let result = text

      // Replace built-in variables
      result = result.replace(VARIABLE_REGEX, (match, varPath) => {
        const value = this.resolveVariable(varPath.trim(), context)
        return value !== undefined ? value : match
      })

      return result
    },

    /**
     * Resolve a variable path to its value
     */
    resolveVariable(path, context = {}) {
      // Handle built-in variables
      if (path.startsWith('env.') || path.startsWith('$env.')) {
        const varName = path.replace(/^\$?env\./, '')
        return this.environments[this.currentEnvironment]?.[varName]
      }

      // Handle workflow variables
      if (path.startsWith('workflow.') || path.startsWith('$workflow.')) {
        const varName = path.replace(/^\$?workflow\./, '')
        return this.workflowVariables[varName]
      }

      // Handle global variables
      if (path.startsWith('global.') || path.startsWith('$global.')) {
        const varName = path.replace(/^\$?global\./, '')
        return this.globalVariables[varName]
      }

      // Handle JSON path (e.g., $json.data.items[0].name)
      if (path.startsWith('$json.')) {
        const jsonPath = path.replace(/^\$json\./, '')
        return this._getJsonPath(context, jsonPath)
      }

      // Check built-in variables
      if (this.builtInVariables[path]) {
        return getBuiltInValue(path)
      }

      // Check local context first
      if (context[path] !== undefined) {
        return context[path]
      }

      // Check workflow variables
      if (this.workflowVariables[path] !== undefined) {
        return this.workflowVariables[path]
      }

      // Check global variables
      if (this.globalVariables[path] !== undefined) {
        return this.globalVariables[path]
      }

      // Check environment variables
      return this.environments[this.currentEnvironment]?.[path]
    },

    /**
     * Get value from object using JSON path
     */
    _getJsonPath(obj, path) {
      const parts = path.split('.').map(p => {
        // Handle array indices like items[0]
        const match = p.match(/^(\w+)\[(\d+)\]$/)
        if (match) {
          return { key: match[1], index: parseInt(match[2]) }
        }
        return { key: p, index: null }
      })

      let current = obj
      for (const part of parts) {
        if (current === undefined || current === null) {
          return undefined
        }
        current = current[part.key]
        if (part.index !== null && Array.isArray(current)) {
          current = current[part.index]
        }
      }
      return current
    },

    // ==================== Context Management ====================

    /**
     * Build context object from variables
     */
    buildContext(additionalContext = {}) {
      return {
        global: { ...this.globalVariables },
        workflow: { ...this.workflowVariables },
        env: { ...this.environments[this.currentEnvironment] },
        ...additionalContext
      }
    },

    /**
     * Update context with execution results
     */
    updateContextFromResults(results) {
      if (results && typeof results === 'object') {
        Object.entries(results).forEach(([key, value]) => {
          this.setWorkflowVariable(key, value)
        })
      }
    },

    // ==================== History (Undo/Redo) ====================

    _saveToHistory() {
      const state = {
        globalVariables: JSON.parse(JSON.stringify(this.globalVariables)),
        workflowVariables: JSON.parse(JSON.stringify(this.workflowVariables)),
        environments: JSON.parse(JSON.stringify(this.environments))
      }

      // Remove future history if we're not at the end
      if (this.historyIndex < this.history.length - 1) {
        this.history = this.history.slice(0, this.historyIndex + 1)
      }

      this.history.push(state)
      this.historyIndex = this.history.length - 1

      // Limit history size
      if (this.history.length > 50) {
        this.history.shift()
        this.historyIndex--
      }
    },

    undo() {
      if (this.canUndo) {
        this.historyIndex--
        this._restoreState(this.history[this.historyIndex])
      }
    },

    redo() {
      if (this.canRedo) {
        this.historyIndex++
        this._restoreState(this.history[this.historyIndex])
      }
    },

    _restoreState(state) {
      if (state) {
        this.globalVariables = JSON.parse(JSON.stringify(state.globalVariables))
        this.workflowVariables = JSON.parse(JSON.stringify(state.workflowVariables))
        this.environments = JSON.parse(JSON.stringify(state.environments))
      }
    },

    // ==================== Import/Export ====================

    exportVariables() {
      return {
        globalVariables: this.globalVariables,
        workflowVariables: this.workflowVariables,
        environments: this.environments,
        currentEnvironment: this.currentEnvironment
      }
    },

    importVariables(data) {
      if (data.globalVariables) {
        this.globalVariables = data.globalVariables
      }
      if (data.workflowVariables) {
        this.workflowVariables = data.workflowVariables
      }
      if (data.environments) {
        this.environments = data.environments
      }
      if (data.currentEnvironment) {
        this.currentEnvironment = data.currentEnvironment
      }
    },

    // ==================== Utilities ====================

    clearHistory() {
      this.history = []
      this.historyIndex = -1
    },

    reset() {
      this.globalVariables = {}
      this.workflowVariables = {}
      this.environments = {
        development: {},
        production: {}
      }
      this.currentEnvironment = 'development'
      this.clearHistory()
    },

    // ==================== Remote API Operations ====================

    /**
     * 从后端加载工作流变量
     * @param {string|number} workflowId
     */
    async fetchVariables(workflowId) {
      try {
        const { getVariables } = await import('@/api/variable')
        const vars = await getVariables(workflowId)
        this.workflowVariables = vars.results || vars || {}
      } catch (e) {
        console.error('Failed to fetch variables:', e)
        throw e
      }
    },

    /**
     * 保存变量到后端
     * @param {string|number} workflowId
     * @param {Object} variables
     */
    async saveVariables(workflowId, variables) {
      try {
        const { createVariable, updateVariable, getVariables } = await import('@/api/variable')
        const results = await getVariables(workflowId)
        const existingVars = results.results || results || []
        const existingMap = new Map(existingVars.map(v => [v.name, v]))

        const created = []
        const updated = []

        for (const [name, varDef] of Object.entries(variables)) {
          const existing = existingMap.get(name)
          if (existing) {
            await updateVariable(existing.id, { ...varDef, name })
            updated.push(name)
          } else {
            await createVariable(workflowId, { ...varDef, name })
            created.push(name)
          }
        }

        return { created, updated }
      } catch (e) {
        console.error('Failed to save variables:', e)
        throw e
      }
    },

    /**
     * 验证变量定义的合法性
     * @param {Object} variables
     * @returns {{ valid: boolean, errors: string[], warnings: string[] }}
     */
    validateVariableDefinitions(variables) {
      const errors = []
      const warnings = []
      const varNames = new Set()

      for (const [name, varDef] of Object.entries(variables)) {
        // 检查名称合法性
        if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name)) {
          errors.push(`变量名非法: ${name} (必须以字母或下划线开头，只能包含字母、数字和下划线)`)
        }

        // 检查重复
        if (varNames.has(name)) {
          errors.push(`重复的变量名: ${name}`)
        }
        varNames.add(name)

        // 检查循环引用（简化实现）
        const value = typeof varDef === 'object' && varDef !== null ? varDef.value : varDef
        if (typeof value === 'string' && value.includes(`{{${name}}}`)) {
          errors.push(`循环引用: ${name}`)
        }

        // 检查空值
        if (value === undefined || value === null || value === '') {
          warnings.push(`变量 ${name} 的值为空`)
        }
      }

      return { valid: errors.length === 0, errors, warnings }
    },

    /**
     * 获取运行时变量（从节点配置中提取）
     * @param {Array} nodes - 工作流节点数组
     * @returns {Array<{name: string, source: string, nodeId: string, value: any, type: string}>}
     */
    extractRuntimeVariables(nodes) {
      const vars = []

      if (!Array.isArray(nodes)) return vars

      for (const node of nodes) {
        // Variable 节点
        if (node.type === 'variable' || node.type === 'code') {
          const config = node.data?.config || {}
          if (config.variableName) {
            vars.push({
              name: config.variableName,
              source: node.type,
              nodeId: node.id,
              nodeName: node.data?.label || node.type,
              value: config.variableValue || config.code || '',
              type: 'runtime'
            })
          }
        }

        // Input 节点
        if (node.type === 'input') {
          const config = node.data?.config || {}
          vars.push({
            name: config.variableName || 'input',
            source: 'input',
            nodeId: node.id,
            nodeName: node.data?.label || 'Input',
            value: config.placeholder || '',
            type: 'input'
          })
        }

        // LLM/Prompt 节点 - 提取模板变量
        if (node.type === 'llm' || node.type === 'prompt') {
          const config = node.data?.config || {}
          const template = config.userTemplate || config.template || ''

          // 提取 {{variable}} 格式的变量
          const varPattern = /\{\{\s*([^}]+)\s*\}\}/g
          let match
          while ((match = varPattern.exec(template)) !== null) {
            const varName = match[1].trim()
            if (!vars.find(v => v.name === varName && v.nodeId === node.id)) {
              vars.push({
                name: varName,
                source: node.type,
                nodeId: node.id,
                nodeName: node.data?.label || node.type,
                value: '',
                type: 'reference'
              })
            }
          }

          // 从 variables 数组中提取定义的变量
          if (config.variables && Array.isArray(config.variables)) {
            for (const v of config.variables) {
              if (v.name && !vars.find(rv => rv.name === v.name && rv.nodeId === node.id)) {
                vars.push({
                  name: v.name,
                  source: node.type,
                  nodeId: node.id,
                  nodeName: node.data?.label || node.type,
                  value: v.value || '',
                  type: 'defined'
                })
              }
            }
          }
        }

        // HTTP 节点 - 提取 URL 和 body 中的变量
        if (node.type === 'http') {
          const config = node.data?.config || {}
          const textToScan = [config.url, config.body, config.headers].filter(Boolean).join(' ')

          const varPattern = /\{\{\s*([^}]+)\s*\}\}/g
          let match
          while ((match = varPattern.exec(textToScan)) !== null) {
            const varName = match[1].trim()
            if (!vars.find(v => v.name === varName && v.nodeId === node.id)) {
              vars.push({
                name: varName,
                source: 'http',
                nodeId: node.id,
                nodeName: node.data?.label || 'HTTP',
                value: '',
                type: 'reference'
              })
            }
          }
        }

        // Condition 节点 - 提取条件中的变量
        if (node.type === 'condition') {
          const config = node.data?.config || {}
          if (config.conditions && Array.isArray(config.conditions)) {
            for (const cond of config.conditions) {
              const textToScan = [cond.field, cond.value].filter(Boolean).join(' ')
              const varPattern = /\{\{\s*([^}]+)\s*\}\}/g
              let match
              while ((match = varPattern.exec(textToScan)) !== null) {
                const varName = match[1].trim()
                if (!vars.find(v => v.name === varName && v.nodeId === node.id)) {
                  vars.push({
                    name: varName,
                    source: 'condition',
                    nodeId: node.id,
                    nodeName: node.data?.label || 'Condition',
                    value: '',
                    type: 'reference'
                  })
                }
              }
            }
          }
        }
      }

      return vars
    }
  }
})

// Helper function to get built-in variable values
function getBuiltInValue(key) {
  const now = new Date()
  switch (key) {
    case 'timestamp':
      return now.toISOString()
    case 'date':
      return now.toLocaleDateString()
    case 'time':
      return now.toLocaleTimeString()
    case 'random.uuid':
      return crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    case 'random.number':
      return Math.floor(Math.random() * 10000)
    case 'env.NODE_ENV':
      return import.meta.env.MODE || 'development'
    default:
      return undefined
  }
}

export default useVariableStore
