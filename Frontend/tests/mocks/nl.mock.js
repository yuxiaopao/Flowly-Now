// Mock data for NL workflow tests

export const mockNLModels = {
  models: [
    { model_id: 'gpt-4', name: 'GPT-4', provider: 'openai' },
    { model_id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai' },
    { model_id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'anthropic' }
  ],
  default: 'gpt-4'
}

export const mockNLSession = {
  id: 1,
  session_id: 1,
  name: 'NL Workflow 1',
  description: 'Create a simple chatbot workflow',
  model: 'gpt-4',
  status: 'completed',
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T10:35:00Z'
}

export const mockNLWorkflow = {
  nodes: [
    {
      id: 'node_1',
      type: 'start',
      position: { x: 250, y: 50 },
      data: { label: 'Start' }
    },
    {
      id: 'node_2',
      type: 'input',
      position: { x: 250, y: 150 },
      data: { label: 'User Input' }
    },
    {
      id: 'node_3',
      type: 'llm',
      position: { x: 250, y: 250 },
      data: { label: 'Chat LLM', model: 'gpt-4' }
    },
    {
      id: 'node_4',
      type: 'output',
      position: { x: 250, y: 350 },
      data: { label: 'Response' }
    }
  ],
  edges: [
    { id: 'e1', source: 'node_1', target: 'node_2' },
    { id: 'e2', source: 'node_2', target: 'node_3' },
    { id: 'e3', source: 'node_3', target: 'node_4' }
  ]
}

export const mockNLIntentCreate = {
  intent: 'create',
  confidence: 0.95,
  action: 'create_workflow',
  suggested_nodes: ['start', 'llm', 'end'],
  description: 'User wants to create a new workflow'
}

export const mockNLIntentModify = {
  intent: 'modify',
  confidence: 0.88,
  action: 'modify_workflow',
  target: 'workflow_1',
  modifications: ['add_node', 'update_prompt'],
  description: 'User wants to modify an existing workflow'
}

export const mockNLIntentDelete = {
  intent: 'delete',
  confidence: 0.92,
  action: 'delete_workflow',
  target: 'workflow_1',
  description: 'User wants to delete a workflow'
}

export const mockNLIntentChat = {
  intent: 'chat',
  confidence: 0.85,
  action: 'continue_conversation',
  description: 'User wants to continue the conversation'
}

export const mockNLSuggestions = {
  suggestions: [
    'Add a condition node to handle errors',
    'Use a loop for batch processing',
    'Add input validation node',
    'Include a delay node for rate limiting'
  ]
}

export const mockNLStreamSession = {
  session_id: 2,
  status: 'streaming',
  message: 'Creating your workflow...'
}

export const mockNLStreamProgress = {
  type: 'progress',
  progress: 25,
  stage: 'analyzing_intent',
  message: 'Analyzing your request...'
}

export const mockNLStreamToken = {
  type: 'token',
  content: 'Creating a '
}

export const mockNLStreamWorkflow = {
  type: 'workflow',
  workflow: mockNLWorkflow
}

export const mockNLStreamDone = {
  type: 'done',
  workflow_json: JSON.stringify(mockNLWorkflow),
  message: 'Workflow generated successfully!'
}

export const mockNLStreamError = {
  type: 'error',
  error: 'Model API unavailable'
}

export const mockNLAnalyzeIntent = {
  intent: 'create',
  confidence: 0.95,
  action: 'create_workflow',
  suggested_workflow_type: 'chatbot',
  suggested_nodes: ['start', 'input', 'llm', 'output', 'end'],
  keywords: ['chat', 'respond', 'user message']
}

export const mockNLHistory = [
  {
    session_id: 1,
    name: 'Chatbot Workflow',
    created_at: '2024-01-15T10:30:00Z',
    workflow_id: 1,
    status: 'completed'
  },
  {
    session_id: 2,
    name: 'Data Processing',
    created_at: '2024-01-14T14:00:00Z',
    workflow_id: 2,
    status: 'completed'
  },
  {
    session_id: 3,
    name: 'API Integration',
    created_at: '2024-01-13T09:00:00Z',
    workflow_id: null,
    status: 'in_progress'
  }
]

export const mockNLConfirmResponse = {
  workflow_id: 10,
  status: 'saved',
  message: 'Workflow saved successfully'
}
