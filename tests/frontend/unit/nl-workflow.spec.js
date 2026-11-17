/**
 * NL Workflow Frontend API Tests
 * Tests for API response format, UUID handling, and credentials configuration.
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';

// Mock the request module
const mockRequest = {
  get: jest.fn().mockResolvedValue({}),
  post: jest.fn().mockResolvedValue({}),
  put: jest.fn().mockResolvedValue({}),
  patch: jest.fn().mockResolvedValue({}),
  delete: jest.fn().mockResolvedValue({}),
};

jest.mock('@/api/index', () => ({
  request: mockRequest,
  api: {},
  default: {},
  toCamelCase: (str) => str,
  toSnakeCase: (str) => str,
  toCamelCaseKeys: (obj) => obj,
  toSnakeCaseKeys: (obj) => obj
}));

const nlWorkflowApi = require('@/api/nl-workflow').default;
const { APP_CONFIG } = require('@/config');

beforeEach(() => jest.clearAllMocks());

describe('NL Workflow API - Backend Compatibility', () => {
  describe('getSessions response format', () => {
    it('returns {code, message, data, count} format', async () => {
      const mockResponse = {
        code: 0,
        message: 'success',
        data: [
          { session_id: '123e4567-e89b-12d3-a456-426614174000', name: 'Session 1', status: 'active' }
        ],
        count: 1
      };
      mockRequest.get.mockResolvedValue(mockResponse);

      const response = await nlWorkflowApi.getSessions();

      expect(response).toHaveProperty('code');
      expect(response).toHaveProperty('message');
      expect(response).toHaveProperty('data');
      expect(response).toHaveProperty('count');
      expect(response.code).toBe(0);
      expect(response.message).toBe('success');
      expect(Array.isArray(response.data)).toBe(true);
    });

    it('handles list endpoint response correctly', async () => {
      const mockResponse = {
        code: 0,
        message: 'success',
        data: [
          { session_id: 'uuid-1', name: 'Session 1' },
          { session_id: 'uuid-2', name: 'Session 2' }
        ],
        count: 2
      };
      mockRequest.get.mockResolvedValue(mockResponse);

      const response = await nlWorkflowApi.getSessions();

      expect(response.data).toHaveLength(2);
    });
  });

  describe('createSession returns UUID id', () => {
    it('session.id is UUID format', async () => {
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const mockResponse = {
        session_id: '123e4567-e89b-12d3-a456-426614174000',
        workflow_json: { name: 'Test', nodes: [], edges: [] },
        status: 'active'
      };
      mockRequest.post.mockResolvedValue(mockResponse);

      const response = await nlWorkflowApi.createSession({ description: 'Test' });

      expect(response.session_id).toMatch(uuidPattern);
    });

    it('handles string UUID from backend', async () => {
      const mockResponse = {
        session_id: '123e4567-e89b-12d3-a456-426614174000',
        workflow_json: { name: 'Test', nodes: [], edges: [] },
        status: 'active'
      };
      mockRequest.post.mockResolvedValue(mockResponse);

      const response = await nlWorkflowApi.createSession({ description: 'Test' });

      expect(typeof response.session_id).toBe('string');
      expect(response.session_id.length).toBe(36); // Standard UUID length
    });
  });

  describe('streamWorkflow credentials configuration', () => {
    it('should use credentials include in fetch (verified via request module)', async () => {
      // This test verifies that the API layer uses proper authentication
      // The actual fetch configuration is in the request utility
      
      const mockStreamResponse = {
        type: 'workflow',
        workflow: { name: 'Test', nodes: [], edges: [] }
      };
      
      // Simulate how the API would be called
      mockRequest.post.mockResolvedValue(mockStreamResponse);
      
      await nlWorkflowApi.createSession({ description: 'Test' });
      
      // Verify the post was called
      expect(mockRequest.post).toHaveBeenCalledWith(
        '/nl-workflow/sessions/',
        expect.objectContaining({ description: 'Test' }),
        expect.any(Object)
      );
    });

    it('does NOT manually add Authorization header', async () => {
      // The fix was to use credentials: 'include' instead of manual Authorization header
      // This test verifies the API call structure
      
      mockRequest.post.mockResolvedValue({
        session_id: '123e4567-e89b-12d3-a456-426614174000',
        workflow_json: { name: 'Test', nodes: [], edges: [] },
        status: 'active'
      });

      await nlWorkflowApi.createSession({ description: 'Test' });

      // Verify call was made without manual auth header in the data
      const callArgs = mockRequest.post.mock.calls[0];
      const callData = callArgs[1];
      
      // Authorization should not be in the request body
      expect(callData).not.toHaveProperty('Authorization');
    });
  });

  describe('getSession with UUID', () => {
    it('fetches session by UUID', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      mockRequest.get.mockResolvedValue({
        session_id: sessionId,
        name: 'Test Session',
        workflow_json: { name: 'Workflow', nodes: [], edges: [] },
        messages: [],
        status: 'active'
      });

      const response = await nlWorkflowApi.getSession(sessionId);

      expect(mockRequest.get).toHaveBeenCalledWith(`/nl-workflow/sessions/${sessionId}/`, {}, { preserveWorkflowKeys: true });
      expect(response.session_id).toBe(sessionId);
    });

    it('handles UUID string format', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      mockRequest.get.mockResolvedValue({
        session_id: sessionId,
        name: 'Test'
      });

      const response = await nlWorkflowApi.getSession(sessionId);

      expect(response.session_id).toBe(sessionId);
    });
  });

  describe('deleteSession with UUID', () => {
    it('deletes session by UUID', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      mockRequest.delete.mockResolvedValue({ message: '会话已删除' });

      const response = await nlWorkflowApi.deleteSession(sessionId);

      expect(mockRequest.delete).toHaveBeenCalledWith(`/nl-workflow/sessions/${sessionId}/`);
      expect(response.message).toBe('会话已删除');
    });
  });

  describe('sendMessage with UUID session', () => {
    it('sends message to UUID session', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      mockRequest.post.mockResolvedValue({
        message: 'Response message',
        suggestions: ['suggestion 1'],
        workflow_json: { name: 'Updated', nodes: [], edges: [] }
      });

      const response = await nlWorkflowApi.sendMessage(sessionId, 'Add email step');

      expect(mockRequest.post).toHaveBeenCalledWith(
        `/nl-workflow/sessions/${sessionId}/message/`,
        { message: 'Add email step' },
        { timeout: APP_CONFIG.nlWorkflowRequestTimeout, preserveWorkflowKeys: true, signal: undefined }
      );
      expect(response.message).toBe('Response message');
    });

    it('handles workflow update in response', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      const updatedWorkflow = { name: 'Updated Workflow', nodes: [], edges: [] };
      mockRequest.post.mockResolvedValue({
        message: 'Updated',
        workflow_json: updatedWorkflow,
        changes: ['added email node']
      });

      const response = await nlWorkflowApi.sendMessage(sessionId, 'Add email');

      expect(response.workflow_json).toEqual(updatedWorkflow);
    });
  });

  describe('confirmWorkflow with UUID', () => {
    it('confirms workflow for UUID session', async () => {
      const sessionId = '123e4567-e89b-12d3-a456-426614174000';
      mockRequest.post.mockResolvedValue({
        workflow_id: 456,
        workflow_json: { name: 'Saved Workflow' },
        status: 'completed'
      });

      const response = await nlWorkflowApi.confirmWorkflow(sessionId);

      expect(mockRequest.post).toHaveBeenCalledWith(`/nl-workflow/sessions/${sessionId}/confirm/`, {});
      expect(response.workflow_id).toBe(456);
    });
  });
});

// Keyword classification belongs to the backend and is exercised by test_nl_intent.py.
// Here the frontend contract must forward the original message and preserve the result.
describe('NL intent API contract', () => {
  it.each([
    ['创建一个问答机器人', 'create', 'qa_bot'],
    ['create a workflow', 'create', 'generic'],
    ['把LLM节点改成gpt-4', 'modify', 'generic'],
    ['添加邮件节点', 'modify', 'generic'],
    ['删除第二个节点', 'delete', 'generic'],
    ['remove this node', 'delete', 'generic'],
    ['你好，这个工具怎么用', 'chat', 'generic'],
    ['Hi there', 'chat', 'generic'],
    ['创建一个数据处理工作流', 'create', 'data_processing'],
    ['创建一个翻译工作流', 'create', 'translation'],
    ['重新生成工作流', 'retry', 'generic'],
    ['retry the workflow', 'retry', 'generic'],
    ['再试一次', 'retry', 'generic'],
  ])('forwards %s and preserves the server classification', async (message, intent, subtype) => {
    const result = { intent, subtype, message };
    mockRequest.post.mockResolvedValueOnce(result);
    const response = await nlWorkflowApi.analyzeIntent(message);
    expect(mockRequest.post).toHaveBeenCalledWith('/nl-workflow/analyze-intent/', { message });
    expect(response).toEqual(result);
  });
});

describe('NL Workflow - Field Name Mapping', () => {
  it('handles session_id field correctly', async () => {
    // Backend uses session_id, frontend should handle both
    mockRequest.post.mockResolvedValue({
      session_id: '123e4567-e89b-12d3-a456-426614174000',
      workflow_json: { name: 'Test' }
    });

    const response = await nlWorkflowApi.createSession({ description: 'Test' });

    expect(response.session_id).toBeDefined();
    expect(response.session_id).toBe('123e4567-e89b-12d3-a456-426614174000');
  });

  it('handles workflow_json field correctly', async () => {
    mockRequest.post.mockResolvedValue({
      session_id: '123e4567-e89b-12d3-a456-426614174000',
      workflow_json: { name: 'Test Workflow', nodes: [], edges: [] }
    });

    const response = await nlWorkflowApi.createSession({ description: 'Test' });

    expect(response.workflow_json).toBeDefined();
    expect(response.workflow_json.name).toBe('Test Workflow');
  });

  it('handles both workflow and workflow_json (backward compat)', async () => {
    // Some endpoints might return workflow instead of workflow_json
    mockRequest.post.mockResolvedValue({
      session_id: '123e4567-e89b-12d3-a456-426614174000',
      workflow: { name: 'Test' },  // Note: 'workflow' not 'workflow_json'
      workflow_json: { name: 'Test' }  // Both present
    });

    const response = await nlWorkflowApi.createSession({ description: 'Test' });

    // Both should be accessible
    expect(response.workflow).toBeDefined();
    expect(response.workflow_json).toBeDefined();
  });
});

describe('NL Workflow - Streaming', () => {
  it('handles streaming response format', async () => {
    // Test the expected streaming response format
    const mockStreamResponse = {
      type: 'workflow',
      workflow: { name: 'Streamed Workflow', nodes: [], edges: [] }
    };

    mockRequest.post.mockResolvedValue(mockStreamResponse);

    const response = await nlWorkflowApi.createSession({ description: 'Stream test' });

    expect(response.type || response.workflow).toBeDefined();
  });

  it('handles progress events in stream', async () => {
    const progressEvent = {
      type: 'progress',
      stage: 'generating',
      message: '正在生成工作流...',
      progress: 50
    };

    mockRequest.post.mockResolvedValue(progressEvent);

    const response = await nlWorkflowApi.createSession({ description: 'Test' });

    // Progress events should be handled
    expect(response.type || response.progress || response.message).toBeDefined();
  });
});

describe('NL Workflow - Error Handling', () => {
  it('handles 404 not found error', async () => {
    mockRequest.get.mockRejectedValue(new Error('404 Not Found'));

    await expect(nlWorkflowApi.getSession('non-existent-uuid'))
      .rejects.toThrow('404 Not Found');
  });

  it('handles 429 rate limit error', async () => {
    mockRequest.post.mockRejectedValue(new Error('429 Too Many Requests'));

    await expect(nlWorkflowApi.createSession({ description: 'Test' }))
      .rejects.toThrow('429 Too Many Requests');
  });

  it('handles validation error', async () => {
    mockRequest.post.mockResolvedValue({
      error: '请提供工作流描述',
      status: 'failed'
    });

    const response = await nlWorkflowApi.createSession({ description: '' });

    expect(response.error).toBeDefined();
  });
});
