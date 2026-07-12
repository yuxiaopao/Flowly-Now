// @ts-check
/**
 * Mock data for Agent E2E tests
 */

export const agentMock = {
  id: '123e4567-e89b-12d3-a456-426614174001',
  name: 'Test Agent',
  description: 'A test agent for E2E testing',
  agent_type: 'conversational',
  system_prompt: 'You are a helpful AI assistant.',
  model: 'gpt-4',
  temperature: 0.7,
  max_tokens: 2048,
  tools: ['web_search', 'calculator'],
  skills: [],
  memory_enabled: true,
  context_window: 10,
  is_active: true,
  settings: {},
  tools_detail: [
    { id: 'tool-1', name: 'web_search', tool_type: 'browser', config: {}, is_enabled: true },
    { id: 'tool-2', name: 'calculator', tool_type: 'utility', config: {}, is_enabled: true },
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const agentListMock = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: '123e4567-e89b-12d3-a456-426614174001',
      name: 'Test Agent',
      description: 'A test agent',
      agent_type: 'conversational',
      model: 'gpt-4',
      temperature: 0.7,
      max_tokens: 2048,
      tools: ['web_search'],
      skills: [],
      memory_enabled: true,
      context_window: 10,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '123e4567-e89b-12d3-a456-426614174002',
      name: 'Research Agent',
      description: 'An agent for research tasks',
      agent_type: 'research',
      model: 'gpt-4',
      temperature: 0.3,
      max_tokens: 4096,
      tools: ['web_search', 'file_reader'],
      skills: [],
      memory_enabled: false,
      context_window: 5,
      is_active: true,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ],
};

export const conversationMock = {
  id: 'conv-123',
  agent: '123e4567-e89b-12d3-a456-426614174001',
  messages: [
    { role: 'user', content: 'Hello', timestamp: '2024-01-01T00:00:00Z' },
    { role: 'assistant', content: 'Hi! How can I help?', timestamp: '2024-01-01T00:00:01Z' },
  ],
  summary: 'User greeting',
  message_count: 2,
  token_count: 50,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:01Z',
};

export const agentExecutionMock = {
  id: 'exec-123',
  agent: '123e4567-e89b-12d3-a456-426614174001',
  agent_name: 'Test Agent',
  conversation: 'conv-123',
  status: 'completed',
  input_data: { message: 'Hello' },
  output_data: { message: 'Hi! How can I help?' },
  error_message: null,
  started_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T00:00:05Z',
  exchange_count: 1,
};

export const availableToolsMock = {
  count: 5,
  results: [
    { id: 'tool-1', name: 'web_search', tool_type: 'browser', config: {}, is_enabled: true },
    { id: 'tool-2', name: 'calculator', tool_type: 'utility', config: {}, is_enabled: true },
    { id: 'tool-3', name: 'file_reader', tool_type: 'file', config: {}, is_enabled: true },
    { id: 'tool-4', name: 'code_interpreter', tool_type: 'execution', config: {}, is_enabled: true },
    { id: 'tool-5', name: 'image_generator', tool_type: 'media', config: {}, is_enabled: false },
  ],
};
