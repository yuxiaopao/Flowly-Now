// Mock data for execution tests

export const mockExecutionList = {
  count: 5,
  results: [
    {
      id: 1,
      workflow_id: 1,
      workflow_name: 'Test Workflow 1',
      status: 'completed',
      created_at: '2024-01-15T10:30:00Z',
      completed_at: '2024-01-15T10:35:00Z',
      duration: 300,
      tokens: { prompt: 100, completion: 50, total: 150 }
    },
    {
      id: 2,
      workflow_id: 1,
      workflow_name: 'Test Workflow 1',
      status: 'running',
      created_at: '2024-01-15T11:00:00Z',
      duration: 120,
      tokens: { prompt: 80, completion: 20, total: 100 }
    },
    {
      id: 3,
      workflow_id: 2,
      workflow_name: 'Test Workflow 2',
      status: 'failed',
      created_at: '2024-01-15T12:00:00Z',
      error_message: 'Connection timeout'
    },
    {
      id: 4,
      workflow_id: 1,
      workflow_name: 'Test Workflow 1',
      status: 'pending',
      created_at: '2024-01-15T13:00:00Z'
    },
    {
      id: 5,
      workflow_id: 3,
      workflow_name: 'Complex Workflow',
      status: 'completed',
      created_at: '2024-01-15T14:00:00Z',
      completed_at: '2024-01-15T14:10:00Z',
      duration: 600,
      tokens: { prompt: 500, completion: 200, total: 700 }
    }
  ]
}

export const mockExecution = {
  id: 1,
  workflow_id: 1,
  workflow_name: 'Test Workflow',
  status: 'completed',
  created_at: '2024-01-15T10:30:00Z',
  started_at: '2024-01-15T10:30:05Z',
  completed_at: '2024-01-15T10:35:00Z',
  duration: 295,
  progress: 100,
  currentNodeId: null,
  nodeStatus: {
    node_1: 'completed',
    node_2: 'completed',
    node_3: 'completed'
  },
  output_data: {
    result: 'Hello from workflow!'
  },
  tokens: {
    prompt: 100,
    completion: 50,
    total: 150
  },
  execution_logs: [
    {
      id: 1,
      type: 'node_start',
      node_id: 'node_1',
      node_name: 'Start',
      timestamp: '2024-01-15T10:30:05Z'
    },
    {
      id: 2,
      type: 'node_complete',
      node_id: 'node_1',
      node_name: 'Start',
      status: 'completed',
      timestamp: '2024-01-15T10:30:10Z'
    },
    {
      id: 3,
      type: 'node_start',
      node_id: 'node_2',
      node_name: 'LLM Node',
      timestamp: '2024-01-15T10:30:10Z'
    },
    {
      id: 4,
      type: 'node_complete',
      node_id: 'node_2',
      node_name: 'LLM Node',
      status: 'completed',
      output: { result: 'Hello from workflow!' },
      timestamp: '2024-01-15T10:35:00Z'
    }
  ],
  node_results: {
    node_1: { input: {}, output: {} },
    node_2: { input: { text: 'Hello' }, output: { result: 'Hello from workflow!' } },
    node_3: { input: { text: 'Hello from workflow!' }, output: { result: 'Hello from workflow!' } }
  }
}

export const mockExecutionPending = {
  id: 10,
  workflow_id: 1,
  workflow_name: 'Test Workflow',
  status: 'pending',
  created_at: '2024-01-15T15:00:00Z'
}

export const mockExecutionRunning = {
  id: 11,
  workflow_id: 1,
  workflow_name: 'Test Workflow',
  status: 'running',
  created_at: '2024-01-15T15:00:00Z',
  started_at: '2024-01-15T15:00:05Z',
  progress: 50,
  current_node_id: 'node_2',
  node_status: {
    node_1: 'completed',
    node_2: 'running'
  }
}

export const mockExecutionFailed = {
  id: 12,
  workflow_id: 1,
  workflow_name: 'Test Workflow',
  status: 'failed',
  created_at: '2024-01-15T15:00:00Z',
  error_message: 'API rate limit exceeded',
  traceback: 'Error: API rate limit exceeded\n    at LLMNode.execute (llm.js:100)\n    at Workflow.run (workflow.js:50)'
}

export const mockExecutionStatus = {
  status: 'running',
  progress: 50,
  currentNodeId: 'node_2',
  nodeStatus: {
    node_1: 'completed',
    node_2: 'running',
    node_3: 'pending'
  },
  outputData: { partial: 'Hello ' }
}

export const mockExecutionStatistics = {
  total_executions: 100,
  successful_executions: 85,
  failed_executions: 15,
  average_duration: 45.5,
  total_tokens: 50000
}

export const mockNodeExecutionDetail = {
  id: 'node_2',
  name: 'LLM Node',
  status: 'completed',
  started_at: '2024-01-15T10:30:10Z',
  completed_at: '2024-01-15T10:35:00Z',
  duration: 290,
  input: { text: 'Hello' },
  output: { result: 'Hello from workflow!' },
  tokens: { prompt: 80, completion: 40, total: 120 }
}

// WebSocket event simulation data
export const mockWsExecutionStart = {
  type: 'execution_start',
  execution_id: 11,
  workflow_id: 1,
  workflow_name: 'Test Workflow'
}

export const mockWsNodeStart = {
  type: 'node_start',
  node_id: 'node_2',
  node_name: 'LLM Node'
}

export const mockWsNodeComplete = {
  type: 'node_complete',
  node_id: 'node_2',
  node_name: 'LLM Node',
  status: 'completed',
  output: { result: 'Hello!' }
}

export const mockWsExecutionComplete = {
  type: 'execution_complete',
  execution_id: 11,
  output_data: { result: 'Workflow completed!' }
}

export const mockWsExecutionError = {
  type: 'execution_error',
  error: 'API connection failed'
}

export const mockWsStreamOutput = {
  type: 'stream_output',
  node_id: 'node_2',
  node_name: 'LLM Node',
  text: 'Hello ',
  partial: true
}
