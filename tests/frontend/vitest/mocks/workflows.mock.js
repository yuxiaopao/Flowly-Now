// @ts-check
/**
 * Mock data for Workflow E2E tests
 */

export const mockWorkflowList = {
  count: 3,
  next: null,
  previous: null,
  results: [
    {
      id: '123e4567-e89b-12d3-a456-426614174010',
      name: 'Test Workflow',
      description: 'A test workflow',
      status: 'published',
      is_public: false,
      tags: ['test', 'automation'],
      version: 1,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      owner: { id: 1, username: 'testuser' },
    },
    {
      id: '123e4567-e89b-12d3-a456-426614174011',
      name: 'Data Processing Pipeline',
      description: 'Process incoming data',
      status: 'draft',
      is_public: true,
      tags: ['data', 'pipeline'],
      version: 2,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
      owner: { id: 1, username: 'testuser' },
    },
    {
      id: '123e4567-e89b-12d3-a456-426614174012',
      name: 'AI Assistant Workflow',
      description: 'Automated AI responses',
      status: 'published',
      is_public: false,
      tags: ['ai', 'assistant'],
      version: 1,
      created_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
      owner: { id: 1, username: 'testuser' },
    },
  ],
}

export const mockWorkflow = {
  id: '123e4567-e89b-12d3-a456-426614174010',
  name: 'Test Workflow',
  description: 'A test workflow for E2E testing',
  status: 'published',
  is_public: false,
  tags: ['test', 'automation'],
  version: 1,
  config: {
    timeout: 300,
    retry: true,
  },
  nodes: [
    {
      id: 'node-1',
      type: 'start',
      data: { label: 'Start' },
      position: { x: 100, y: 100 },
    },
    {
      id: 'node-2',
      type: 'llm',
      data: {
        label: 'AI Node',
        description: 'AI processing',
        config: { model: 'gpt-4', temperature: 0.7 },
        style: { backgroundColor: '#e3f2fd' },
      },
      position: { x: 300, y: 100 },
    },
    {
      id: 'node-3',
      type: 'end',
      data: { label: 'End' },
      position: { x: 500, y: 100 },
    },
  ],
  edges: [
    { id: 'edge-1', source: 'node-1', target: 'node-2', sourceHandle: 'out', targetHandle: 'in' },
    { id: 'edge-2', source: 'node-2', target: 'node-3', sourceHandle: 'out', targetHandle: 'in' },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  owner: { id: 1, username: 'testuser' },
}

export const workflowListMock = mockWorkflowList
export const workflowDetailMock = mockWorkflow

export const mockNode = mockWorkflow.nodes[0]
export const mockEdge = mockWorkflow.edges[0]

export const mockAvailableModels = {
  count: 3,
  results: [
    { id: 'gpt-4', name: 'GPT-4', provider: 'openai' },
    { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', provider: 'anthropic' },
    { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'deepseek' },
  ],
}

export const mockAvailableTools = {
  count: 3,
  results: [
    { id: 'web-search', name: 'Web Search', type: 'tool' },
    { id: 'calculator', name: 'Calculator', type: 'tool' },
    { id: 'http-request', name: 'HTTP Request', type: 'tool' },
  ],
}

export const mockAvailableNodeTypes = [
  { type: 'start', label: 'Start' },
  { type: 'llm', label: 'LLM' },
  { type: 'end', label: 'End' },
]
