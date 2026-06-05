# Phase 1: 测试覆盖详细方案

> 项目: Flowly-now  
> 技术栈: Django + DRF (Backend) / Vue 3 + Playwright (Frontend)  
> 版本: v1.0  
> 日期: 2026-06-03

---

## 一、当前测试现状分析

### 1.1 测试文件统计

| 测试目录 | 文件数 | 说明 |
|---------|-------|------|
| `tests/backend/` | 12 | Backend 单元/集成测试 |
| `tests/nl_workflow/` | 8 | NL Workflow 测试 |
| `tests/e2e/` | 10 | E2E 测试 (Python) |
| `tests/frontend/` | 19 | Frontend Jest 测试 |

### 1.2 已有测试覆盖模块

**Backend (`tests/backend/`)**
- ✅ `test_auth.py` - 认证测试
- ✅ `test_workflows.py` - Workflow 测试
- ✅ `test_agents.py` - Agent 测试
- ✅ `test_rag.py` - RAG 测试
- ✅ `test_nl_workflow.py` - NL Workflow 测试
- ✅ `test_tenants.py` - 租户测试
- ✅ `test_monitoring.py` - 监控测试
- ✅ `test_prompts.py` - Prompt 测试
- ✅ `test_api_error.py` - API 错误处理测试

**NL Workflow (`tests/nl_workflow/`)**
- ✅ `test_nl_api.py` - NL API 测试
- ✅ `test_nl_validation.py` - NL 验证测试
- ✅ `test_nl_cost.py` - NL 成本测试
- ✅ `test_nl_cycle.py` - NL 循环检测测试
- ✅ `test_nl_intent.py` - NL 意图检测测试
- ✅ `test_nl_rate_limit.py` - NL 限流测试

**Frontend Unit (`tests/frontend/unit/`)**
- ✅ `auth.api.spec.js`
- ✅ `workflow.api.spec.js`
- ✅ `agent.api.spec.js`
- ✅ `rag.api.spec.js`
- ✅ `billing.api.spec.js`
- ✅ `monitoring.api.spec.js`

**Playwright E2E (`Frontend/tests/e2e/`)**
- ✅ `nl-creator.spec.js` - NL Creator 测试
- ✅ `workflow-editor.spec.js` - Workflow Editor 测试
- ✅ `test-workflow-execution.spec.js` - 执行测试
- ✅ `test-nl-to-workflow.spec.js` - NL 到 Workflow 测试
- ✅ `test-model-training.spec.js` - 模型训练测试

### 1.3 未测试模块识别

| 模块 | 状态 | 说明 |
|-----|------|------|
| `gateway` | ❌ 未测试 | API Gateway (ModelProvider, AIModel, UserAPIKey, APICallLog) |
| `billing` | ⚠️ 部分测试 | 需补充 Subscription, Coupon, Invoice 端点测试 |
| `agents` | ⚠️ 部分测试 | 需补充 chat, stream_chat, debug 端点测试 |
| `rag` | ⚠️ 部分测试 | 需补充 search, query, upload_file 端点测试 |
| `knowledge` | ❌ 未测试 | 知识库模块 |
| `marketplace` | ❌ 未测试 | 市场模块 |
| `monitoring` | ⚠️ 部分测试 | 需补充 metrics, alerts 端点测试 |
| `settings` | ❌ 未测试 | 设置模块 |
| `vector-store` | ❌ 未测试 | 向量存储模块 |

---

## 二、Backend 模块测试方案

### 2.1 gateway 模块

**模块概述**: API Gateway 模块，负责 AI 模型提供商管理、API Key 管理和调用日志

**端点覆盖**:

| 端点 | 方法 | 描述 | 测试优先级 |
|-----|------|-----|----------|
| `/api/v1/gateway/providers/` | GET | 列出模型提供商 | P1 |
| `/api/v1/gateway/models/` | GET | 列出 AI 模型 | P1 |
| `/api/v1/gateway/models/default_models/` | GET | 获取默认模型 | P2 |
| `/api/v1/gateway/models/available/` | GET | 获取可用模型列表 | P1 |
| `/api/v1/gateway/models/{id}/test/` | POST | 测试模型连接 | P2 |
| `/api/v1/gateway/api-keys/` | GET/POST | API Key CRUD | P1 |
| `/api/v1/gateway/api-keys/{id}/` | GET/PUT/DELETE | API Key 操作 | P1 |
| `/api/v1/gateway/api-keys/{id}/verify/` | POST | 验证 API Key | P2 |
| `/api/v1/gateway/logs/` | GET | API 调用日志 | P2 |
| `/api/v1/gateway/logs/aggregate/` | GET | 聚合统计 | P2 |
| `/api/v1/gateway/logs/recent/` | GET | 最近调用 | P2 |
| `/api/v1/gateway/chat/` | POST | 统一 Chat 接口 | P1 |
| `/api/v1/gateway/embeddings/` | POST | 统一 Embeddings 接口 | P1 |
| `/api/v1/gateway/health/` | GET | 健康检查 | P1 |

**需要的 Fixtures**:

```python
@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()

@pytest.fixture
def authenticated_client(db, user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client

@pytest.fixture
def model_provider(db):
    """Create a test model provider."""
    from gateway.models import ModelProvider
    return ModelProvider.objects.create(
        name='OpenAI',
        slug='openai',
        logo_url='https://example.com/openai.png',
        website='https://openai.com',
        is_active=True
    )

@pytest.fixture
def ai_model(db, model_provider):
    """Create a test AI model."""
    from gateway.models import AIModel
    return AIModel.objects.create(
        provider=model_provider,
        name='GPT-4',
        model_id='gpt-4',
        model_type='chat',
        max_tokens=8192,
        supports_streaming=True,
        supports_function_calling=True,
        input_price=0.03,
        output_price=0.06,
        is_active=True,
        is_default=True
    )

@pytest.fixture
def user_api_key(db, user, model_provider):
    """Create a test user API key."""
    from gateway.models import UserAPIKey
    return UserAPIKey.objects.create(
        user=user,
        provider=model_provider,
        name='Test Key',
        api_key='sk-test-xxx',
        endpoint='https://api.openai.com/v1',
        is_active=True
    )

@pytest.fixture
def api_call_log(db, user, model_provider):
    """Create a test API call log."""
    from gateway.models import APICallLog
    return APICallLog.objects.create(
        user=user,
        provider='openai',
        model='gpt-4',
        endpoint='/chat/completions',
        input_tokens=100,
        output_tokens=200,
        total_tokens=300,
        latency_ms=500,
        status_code=200,
        cost=0.01
    )
```

**Mock 策略**:

```python
# Mock GatewayService for chat/embeddings tests
@pytest.fixture
def mock_gateway_service(mocker):
    """Mock GatewayService."""
    mock_service = mocker.patch('gateway.views.GatewayService')
    mock_instance = MagicMock()
    mock_instance.chat.return_value = MagicMock(
        content='Test response',
        model='gpt-4',
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=100,
        cost=0.001
    )
    mock_instance.stream_chat.return_value = iter([
        {'type': 'content', 'content': 'Test'},
        {'type': 'done'}
    ])
    mock_instance.embeddings.return_value = [[0.1, 0.2, 0.3]]
    mock_service.return_value = mock_instance
    return mock_instance
```

**测试用例清单**:

#### TestModelProviderViewSet
```python
class TestModelProviderViewSet:
    def test_list_providers_authenticated(self, authenticated_client, model_provider):
        """已认证用户可以列出提供商"""
        response = authenticated_client.get('/api/v1/gateway/providers/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_providers_unauthenticated(self, api_client):
        """未认证用户不能列出提供商"""
        response = api_client.get('/api/v1/gateway/providers/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_provider(self, authenticated_client, model_provider):
        """获取单个提供商详情"""
        response = authenticated_client.get(f'/api/v1/gateway/providers/{model_provider.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'OpenAI'
```

#### TestAIModelViewSet
```python
class TestAIModelViewSet:
    def test_list_models(self, authenticated_client, ai_model):
        """列出 AI 模型"""
        response = authenticated_client.get('/api/v1/gateway/models/')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_provider(self, authenticated_client, ai_model, model_provider):
        """按提供商筛选模型"""
        response = authenticated_client.get(f'/api/v1/gateway/models/?provider={model_provider.slug}')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_type(self, authenticated_client, ai_model):
        """按类型筛选模型"""
        response = authenticated_client.get('/api/v1/gateway/models/?type=chat')
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_capability(self, authenticated_client, ai_model):
        """按能力筛选模型"""
        response = authenticated_client.get('/api/v1/gateway/models/?capability=streaming')
        assert response.status_code == status.HTTP_200_OK

    def test_default_models(self, authenticated_client, ai_model):
        """获取默认模型"""
        response = authenticated_client.get('/api/v1/gateway/models/default_models/')
        assert response.status_code == status.HTTP_200_OK

    def test_available_models(self, authenticated_client):
        """获取可用模型列表"""
        response = authenticated_client.get('/api/v1/gateway/models/available/')
        assert response.status_code == status.HTTP_200_OK

    def test_test_model(self, authenticated_client, ai_model, mock_gateway_service):
        """测试模型连接"""
        response = authenticated_client.post(f'/api/v1/gateway/models/{ai_model.id}/test/')
        assert response.status_code == status.HTTP_200_OK
        assert 'success' in response.data
```

#### TestUserAPIKeyViewSet
```python
class TestUserAPIKeyViewSet:
    def test_list_api_keys(self, authenticated_client, user_api_key):
        """列出用户的 API Keys"""
        response = authenticated_client.get('/api/v1/gateway/api-keys/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_api_key(self, authenticated_client, model_provider):
        """创建 API Key"""
        data = {
            'provider': 'openai',
            'name': 'New Key',
            'api_key': 'sk-new-key-xxx'
        }
        response = authenticated_client.post('/api/v1/gateway/api-keys/', data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_api_key_masked(self, authenticated_client, user_api_key):
        """API Key 应该被掩码"""
        response = authenticated_client.get('/api/v1/gateway/api-keys/')
        assert 'sk-test' not in response.data[0]['masked_key']
        assert '*' in response.data[0]['masked_key']

    def test_verify_api_key(self, authenticated_client, user_api_key, mock_gateway_service):
        """验证 API Key"""
        response = authenticated_client.post(f'/api/v1/gateway/api-keys/{user_api_key.id}/verify/')
        assert response.status_code == status.HTTP_200_OK
```

#### TestAPICallLogViewSet
```python
class TestAPICallLogViewSet:
    def test_list_logs(self, authenticated_client, api_call_log):
        """列出 API 调用日志"""
        response = authenticated_client.get('/api/v1/gateway/logs/')
        assert response.status_code == status.HTTP_200_OK

    def test_aggregate_logs(self, authenticated_client, api_call_log):
        """获取聚合统计"""
        response = authenticated_client.get('/api/v1/gateway/logs/aggregate/')
        assert response.status_code == status.HTTP_200_OK
        assert 'overall' in response.data
        assert 'by_provider' in response.data

    def test_recent_logs(self, authenticated_client, api_call_log):
        """获取最近日志"""
        response = authenticated_client.get('/api/v1/gateway/logs/recent/?limit=10')
        assert response.status_code == status.HTTP_200_OK
```

#### TestGatewayChatView
```python
class TestGatewayChatView:
    def test_chat_success(self, authenticated_client, mock_gateway_service):
        """Chat 成功"""
        data = {
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'model': 'gpt-4'
        }
        response = authenticated_client.post('/api/v1/gateway/chat/', data)
        assert response.status_code == status.HTTP_200_OK
        assert 'content' in response.data

    def test_chat_missing_messages(self, authenticated_client):
        """Chat 缺少 messages"""
        data = {'model': 'gpt-4'}
        response = authenticated_client.post('/api/v1/gateway/chat/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chat_unauthenticated(self, api_client):
        """Chat 未认证"""
        data = {'messages': [{'role': 'user', 'content': 'Hello'}]}
        response = api_client.post('/api/v1/gateway/chat/', data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_chat_stream(self, authenticated_client, mock_gateway_service):
        """Chat 流式响应"""
        data = {
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'model': 'gpt-4',
            'stream': True
        }
        response = authenticated_client.post('/api/v1/gateway/chat/', data, format='json')
        assert response.status_code == status.HTTP_200_OK
```

#### TestGatewayHealthView
```python
class TestGatewayHealthView:
    def test_health_check(self, authenticated_client):
        """健康检查"""
        response = authenticated_client.get('/api/v1/gateway/health/')
        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert 'providers' in response.data
```

---

### 2.2 agents 模块

**模块概述**: AI Agent 模块，负责 Agent 创建、对话、工具管理

**已有测试**: `test_agents.py` (基础 CRUD + 简单对话)

**需要补充的测试**:

| 端点 | 方法 | 描述 | 测试优先级 |
|-----|------|-----|----------|
| `/api/v1/agents/{id}/chat/` | POST | Agent 对话 | P1 |
| `/api/v1/agents/{id}/stream_chat/` | POST | Agent 流式对话 | P1 |
| `/api/v1/agents/{id}/debug/` | POST | Agent 调试 | P1 |
| `/api/v1/agents/{id}/debug_history/` | GET/DELETE | 调试历史 | P2 |
| `/api/v1/agents/{id}/debug/sessions/{id}/` | GET | 调试会话详情 | P2 |
| `/api/v1/agents/{id}/tools/` | GET/POST | Agent 工具管理 | P1 |
| `/api/v1/agents/{id}/tools_remove/` | DELETE | 移除工具 | P2 |
| `/api/v1/agents/{id}/reset_memory/` | POST | 重置记忆 | P2 |
| `/api/v1/agents/{id}/skills/` | GET | 获取技能 | P2 |
| `/api/v1/agents/{id}/skills/` | PATCH | 更新技能 | P2 |
| `/api/v1/agents/conversations/` | GET/POST | 会话列表 | P2 |
| `/api/v1/agents/conversations/{id}/` | GET | 会话详情 | P2 |
| `/api/v1/agents/conversations/{id}/messages/` | GET | 获取消息 | P2 |
| `/api/v1/agents/conversations/{id}/add_message/` | POST | 添加消息 | P2 |
| `/api/v1/agents/tools/available/` | GET | 可用工具列表 | P1 |

**需要的 Fixtures**:

```python
@pytest.fixture
def agent(db, user):
    """Create a test agent."""
    from agents.models import Agent
    return Agent.objects.create(
        owner=user,
        name='Test Agent',
        description='A test AI agent',
        agent_type='assistant',
        model='gpt-4',
        system_prompt='You are a helpful assistant.',
        temperature=0.7,
        max_tokens=2048,
        tools=['calculator', 'search'],
        skills=['coding', 'writing'],
        memory_enabled=True,
        context_window=10,
        is_active=True
    )

@pytest.fixture
def agent_conversation(db, agent, user):
    """Create a test agent conversation."""
    from agents.models import AgentConversation
    return AgentConversation.objects.create(
        agent=agent,
        user=user,
        messages=[
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ],
        message_count=2
    )

@pytest.fixture
def agent_execution(db, agent):
    """Create a test agent execution."""
    from agents.models import AgentExecution
    from django.utils import timezone
    return AgentExecution.objects.create(
        agent=agent,
        status='completed',
        input_data={'message': 'Test'},
        output_data={'response': 'Test response'},
        started_at=timezone.now(),
        completed_at=timezone.now()
    )

@pytest.fixture
def mock_agent_engine(mocker):
    """Mock AgentEngine."""
    mock_engine = mocker.patch('agents.views.create_agent_engine')
    mock_instance = MagicMock()
    mock_instance.chat.return_value = {
        'success': True,
        'response': 'Test response',
        'tool_calls': []
    }
    mock_instance.stream_chat.return_value = iter([
        {'type': 'content', 'content': 'Test'},
        {'type': 'done'}
    ])
    mock_instance.reset_memory.return_value = None
    mock_engine.return_value = mock_instance
    return mock_instance
```

**测试用例清单**:

```python
@pytest.mark.django_db
class TestAgentChat:
    """Test agent chat endpoint."""

    def test_chat_success(self, authenticated_client, agent, mock_agent_engine):
        """Agent 对话成功"""
        data = {'message': 'Hello'}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/chat/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'response' in response.data
        assert 'conversation_id' in response.data

    def test_chat_with_existing_conversation(self, authenticated_client, agent, agent_conversation, mock_agent_engine):
        """带现有会话 ID 的对话"""
        data = {
            'message': 'Continue',
            'conversation_id': str(agent_conversation.id)
        }
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/chat/',
            data
        )
        assert response.status_code == status.HTTP_200_OK

    def test_chat_missing_message(self, authenticated_client, agent):
        """缺少消息内容"""
        response = authenticated_client.post(f'/api/v1/agents/{agent.id}/chat/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_chat_unauthenticated(self, api_client, agent):
        """未认证用户"""
        data = {'message': 'Hello'}
        response = api_client.post(f'/api/v1/agents/{agent.id}/chat/', data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_chat_with_tools(self, authenticated_client, agent, mock_agent_engine):
        """带工具调用的对话"""
        mock_agent_engine.chat.return_value = {
            'success': True,
            'response': 'Let me calculate...',
            'tool_calls': [
                {'name': 'calculator', 'args': {'expression': '2+2'}}
            ]
        }
        data = {'message': 'What is 2+2?'}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/chat/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'tool_calls' in response.data

    def test_chat_error_handling(self, authenticated_client, agent, mock_agent_engine):
        """对话错误处理"""
        mock_agent_engine.chat.return_value = {
            'success': False,
            'error': 'Model unavailable'
        }
        data = {'message': 'Hello'}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/chat/',
            data
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.django_db
class TestAgentStreamChat:
    """Test agent streaming chat endpoint."""

    def test_stream_chat(self, authenticated_client, agent, mock_agent_engine):
        """流式对话"""
        data = {'message': 'Hello'}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/stream_chat/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/event-stream'

    def test_stream_chat_missing_message(self, authenticated_client, agent):
        """流式对话缺少消息"""
        response = authenticated_client.post(f'/api/v1/agents/{agent.id}/stream_chat/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAgentDebug:
    """Test agent debug endpoint."""

    def test_debug_success(self, authenticated_client, agent, mock_agent_engine):
        """调试成功"""
        data = {
            'message': 'Test debug',
            'context': {'key': 'value'}
        }
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/debug/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'response' in response.data or 'error' in response.data
        assert 'execution_id' in response.data

    def test_debug_creates_execution_record(self, authenticated_client, agent, mock_agent_engine):
        """调试创建执行记录"""
        data = {'message': 'Test'}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/debug/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        # Verify execution record was created
        from agents.models import AgentExecution
        assert AgentExecution.objects.filter(agent=agent).exists()


@pytest.mark.django_db
class TestAgentDebugHistory:
    """Test agent debug history endpoint."""

    def test_get_debug_history(self, authenticated_client, agent, agent_execution):
        """获取调试历史"""
        response = authenticated_client.get(f'/api/v1/agents/{agent.id}/debug_history/')
        assert response.status_code == status.HTTP_200_OK

    def test_clear_debug_history(self, authenticated_client, agent, agent_execution):
        """清除调试历史"""
        response = authenticated_client.delete(f'/api/v1/agents/{agent.id}/debug_history/')
        assert response.status_code == status.HTTP_200_OK

    def test_get_debug_session_detail(self, authenticated_client, agent, agent_execution):
        """获取调试会话详情"""
        response = authenticated_client.get(
            f'/api/v1/agents/{agent.id}/debug/sessions/{agent_execution.id}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'messages' in response.data


@pytest.mark.django_db
class TestAgentTools:
    """Test agent tools endpoint."""

    def test_get_available_tools(self, authenticated_client, agent):
        """获取可用工具"""
        response = authenticated_client.get('/api/v1/agents/tools/available/')
        assert response.status_code == status.HTTP_200_OK
        assert 'available_tools' in response.data

    def test_update_agent_tools(self, authenticated_client, agent):
        """更新 Agent 工具"""
        data = {'tools': ['calculator', 'search', 'weather']}
        response = authenticated_client.post(
            f'/api/v1/agents/{agent.id}/tools/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert set(response.data['tools']) == set(data['tools'])

    def test_remove_agent_tool(self, authenticated_client, agent):
        """移除 Agent 工具"""
        data = {'tool': 'calculator'}
        response = authenticated_client.delete(
            f'/api/v1/agents/{agent.id}/tools_remove/',
            data
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAgentMemory:
    """Test agent memory management."""

    def test_reset_memory(self, authenticated_client, agent, mock_agent_engine):
        """重置记忆"""
        response = authenticated_client.post(f'/api/v1/agents/{agent.id}/reset_memory/')
        assert response.status_code == status.HTTP_200_OK
        mock_agent_engine.reset_memory.assert_called_once()


@pytest.mark.django_db
class TestAgentSkills:
    """Test agent skills management."""

    def test_get_skills(self, authenticated_client, agent):
        """获取技能列表"""
        response = authenticated_client.get(f'/api/v1/agents/{agent.id}/skills/')
        assert response.status_code == status.HTTP_200_OK
        assert 'skills' in response.data

    def test_update_skills(self, authenticated_client, agent):
        """更新技能"""
        data = {'skills': ['coding', 'writing', 'analysis']}
        response = authenticated_client.patch(
            f'/api/v1/agents/{agent.id}/skills/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['skills'] == data['skills']
```

---

### 2.3 rag 模块

**模块概述**: RAG (Retrieval-Augmented Generation) 模块，负责文档处理、向量存储和 RAG 管道

**已有测试**: `test_rag.py` (基础 CRUD + 简单操作)

**需要补充的测试**:

| 端点 | 方法 | 描述 | 测试优先级 |
|-----|------|-----|----------|
| `/api/v1/rag/vector-stores/{id}/test_connection/` | POST | 测试连接 | P1 |
| `/api/v1/rag/vector-stores/{id}/create_collection/` | POST | 创建集合 | P2 |
| `/api/v1/rag/vector-stores/{id}/delete_collection/` | DELETE | 删除集合 | P2 |
| `/api/v1/rag/vector-stores/types/` | GET | 列出类型 | P1 |
| `/api/v1/rag/collections/{id}/stats/` | GET | 集合统计 | P2 |
| `/api/v1/rag/collections/{id}/add_url/` | POST | 添加 URL 文档 | P2 |
| `/api/v1/rag/collections/{id}/upload_file/` | POST | 上传文件 | P1 |
| `/api/v1/rag/collections/{id}/search/` | GET | 搜索文档 | P1 |
| `/api/v1/rag/pipelines/{id}/query/` | POST | RAG 查询 | P1 |
| `/api/v1/rag/documents/{id}/reprocess/` | POST | 重新处理文档 | P2 |
| `/api/v1/rag/documents/{id}/chunks/` | GET | 获取文档块 | P2 |

**需要的 Fixtures**:

```python
@pytest.fixture
def vector_store(db, user):
    """Create a test vector store."""
    from rag.models import VectorStore
    return VectorStore.objects.create(
        owner=user,
        name='Test Vector Store',
        store_type='memory',
        dimension=1536,
        metric='cosine',
        is_default=True
    )

@pytest.fixture
def document_collection(db, vector_store, user):
    """Create a test document collection."""
    from rag.models import DocumentCollection
    return DocumentCollection.objects.create(
        owner=user,
        name='Test Collection',
        description='A test collection',
        vector_store=vector_store,
        embedding_model='text-embedding-ada-002',
        chunk_size=1000,
        chunk_overlap=200
    )

@pytest.fixture
def document(db, document_collection):
    """Create a test document."""
    from rag.models import Document
    return Document.objects.create(
        collection=document_collection,
        title='Test Document',
        source_type='text',
        content='This is test content for RAG.',
        status='processed',
        chunk_count=1,
        token_count=10
    )

@pytest.fixture
def rag_pipeline(db, document_collection, user):
    """Create a test RAG pipeline."""
    from rag.models import RAGPipeline
    return RAGPipeline.objects.create(
        owner=user,
        name='Test Pipeline',
        description='A test RAG pipeline',
        collection=document_collection,
        top_k=5,
        min_similarity=0.7,
        system_prompt='Use context to answer.',
        include_sources=True
    )

@pytest.fixture
def mock_rag_service(mocker):
    """Mock RAGService."""
    mock_service = mocker.patch('rag.views.RAGService')
    mock_instance = MagicMock()
    mock_instance.initialize.return_value = None
    mock_instance.retrieve.return_value = [
        {'score': 0.9, 'payload': {'content': 'Test content'}}
    ]
    mock_instance.generate_response.return_value = {
        'response': 'Test RAG response'
    }
    mock_service.return_value = mock_instance
    return mock_instance

@pytest.fixture
def mock_document_processor(mocker):
    """Mock DocumentProcessor."""
    mock_processor = mocker.patch('rag.views.DocumentProcessor')
    mock_instance = MagicMock()
    mock_instance.process_text.return_value = {
        'success': True,
        'chunks': [{'content': 'Test chunk', 'index': 0}]
    }
    mock_instance.process_url.return_value = {
        'success': True,
        'chunks': [{'content': 'URL content', 'index': 0}]
    }
    mock_processor.return_value = mock_instance
    return mock_instance

@pytest.fixture
def mock_vector_store_client(mocker):
    """Mock vector store client."""
    mock_client = mocker.patch('rag.views.get_vector_store_client')
    mock_instance = MagicMock()
    mock_instance.connect.return_value = True
    mock_instance.create_collection.return_value = True
    mock_instance.delete_collection.return_value = True
    mock_client.return_value = mock_instance
    return mock_instance
```

**测试用例清单**:

```python
@pytest.mark.django_db
class TestVectorStoreConnection:
    """Test vector store connection operations."""

    def test_test_connection_success(self, authenticated_client, vector_store, mock_vector_store_client):
        """测试连接成功"""
        response = authenticated_client.post(
            f'/api/v1/rag/vector-stores/{vector_store.id}/test_connection/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_create_collection(self, authenticated_client, vector_store, mock_vector_store_client):
        """创建集合"""
        data = {'name': 'new_collection', 'dimension': 1536}
        response = authenticated_client.post(
            f'/api/v1/rag/vector-stores/{vector_store.id}/create_collection/',
            data
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_collection(self, authenticated_client, vector_store, mock_vector_store_client):
        """删除集合"""
        data = {'name': 'collection_to_delete'}
        response = authenticated_client.delete(
            f'/api/v1/rag/vector-stores/{vector_store.id}/delete_collection/',
            data
        )
        assert response.status_code == status.HTTP_200_OK

    def test_list_vector_store_types(self, authenticated_client):
        """列出向量存储类型"""
        response = authenticated_client.get('/api/v1/rag/vector-stores/types/')
        assert response.status_code == status.HTTP_200_OK
        assert 'types' in response.data


@pytest.mark.django_db
class TestDocumentCollectionSearch:
    """Test document collection search operations."""

    def test_search_collection(self, authenticated_client, document_collection, mock_rag_service):
        """搜索集合"""
        response = authenticated_client.get(
            f'/api/v1/rag/collections/{document_collection.id}/search/',
            {'query': 'test query', 'top_k': 5}
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'count' in response.data

    def test_search_missing_query(self, authenticated_client, document_collection):
        """搜索缺少查询参数"""
        response = authenticated_client.get(
            f'/api/v1/rag/collections/{document_collection.id}/search/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_collection_stats(self, authenticated_client, document_collection, document):
        """集合统计"""
        response = authenticated_client.get(
            f'/api/v1/rag/collections/{document_collection.id}/stats/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'document_count' in response.data
        assert 'chunk_count' in response.data


@pytest.mark.django_db
class TestDocumentUpload:
    """Test document upload operations."""

    def test_add_url_document(self, authenticated_client, document_collection, mock_document_processor):
        """添加 URL 文档"""
        data = {
            'url': 'https://example.com/article',
            'title': 'Example Article'
        }
        response = authenticated_client.post(
            f'/api/v1/rag/collections/{document_collection.id}/add_url/',
            data
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_file(self, authenticated_client, document_collection, mock_document_processor):
        """上传文件"""
        import io
        file_content = b'Test file content'
        file_obj = io.BytesIO(file_content)
        file_obj.name = 'test.txt'
        
        response = authenticated_client.post(
            f'/api/v1/rag/collections/{document_collection.id}/upload_file/',
            {'file': file_obj},
            format='multipart'
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_file_no_file(self, authenticated_client, document_collection):
        """上传文件未提供"""
        response = authenticated_client.post(
            f'/api/v1/rag/collections/{document_collection.id}/upload_file/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRAGPipelineQuery:
    """Test RAG pipeline query operations."""

    def test_query_pipeline(self, authenticated_client, rag_pipeline, mock_rag_service):
        """RAG 管道查询"""
        data = {'query': 'What is this about?'}
        response = authenticated_client.post(
            f'/api/v1/rag/pipelines/{rag_pipeline.id}/query/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'response' in response.data
        assert 'sources' in response.data

    def test_query_pipeline_with_filters(self, authenticated_client, rag_pipeline, mock_rag_service):
        """带过滤器的查询"""
        data = {
            'query': 'Test query',
            'filters': {'source': 'article'}
        }
        response = authenticated_client.post(
            f'/api/v1/rag/pipelines/{rag_pipeline.id}/query/',
            data
        )
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_documents(self, authenticated_client, rag_pipeline, mock_rag_service):
        """仅检索文档"""
        response = authenticated_client.get(
            f'/api/v1/rag/pipelines/{rag_pipeline.id}/retrieve/',
            {'query': 'test query'}
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data


@pytest.mark.django_db
class TestDocumentOperations:
    """Test document operations."""

    def test_reprocess_document(self, authenticated_client, document, mock_document_processor):
        """重新处理文档"""
        response = authenticated_client.post(
            f'/api/v1/rag/documents/{document.id}/reprocess/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_document_chunks(self, authenticated_client, document):
        """获取文档块"""
        response = authenticated_client.get(
            f'/api/v1/rag/documents/{document.id}/chunks/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
```

---

### 2.4 billing 模块

**模块概述**: Billing 模块，负责订阅管理、计费和优惠券

**已有测试**: 基础测试需补充

**需要补充的测试**:

| 端点 | 方法 | 描述 | 测试优先级 |
|-----|------|-----|----------|
| `/api/v1/billing/plans/` | GET | 获取所有计划 | P1 |
| `/api/v1/billing/subscription/my/` | GET | 获取我的订阅 | P1 |
| `/api/v1/billing/subscription/subscribe/` | POST | 订阅计划 | P1 |
| `/api/v1/billing/subscription/cancel/` | POST | 取消订阅 | P2 |
| `/api/v1/billing/subscription/reactivate/` | POST | 重新激活订阅 | P2 |
| `/api/v1/billing/subscription/usage/` | GET | 用量统计 | P1 |
| `/api/v1/billing/usage/history/` | GET | 用量历史 | P2 |
| `/api/v1/billing/invoices/{id}/download/` | GET | 下载发票 | P2 |
| `/api/v1/billing/coupons/validate/` | POST | 验证优惠券 | P1 |
| `/api/v1/billing/coupons/my/` | GET | 我的优惠券 | P2 |

**测试用例清单**:

```python
@pytest.mark.django_db
class TestSubscriptionManagement:
    """Test subscription management."""

    def test_get_my_subscription_new_user(self, authenticated_client):
        """新用户获取订阅（自动创建免费订阅）"""
        response = authenticated_client.get('/api/v1/billing/subscription/my/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['plan_type'] == 'free'
        assert response.data['status'] == 'active'

    def test_get_my_subscription_existing(self, authenticated_client, subscription):
        """获取现有订阅"""
        response = authenticated_client.get('/api/v1/billing/subscription/my/')
        assert response.status_code == status.HTTP_200_OK

    def test_subscribe_to_plan(self, authenticated_client):
        """订阅计划"""
        data = {'plan_type': 'starter', 'billing_cycle': 'monthly'}
        response = authenticated_client.post(
            '/api/v1/billing/subscription/subscribe/',
            data
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_cancel_subscription(self, authenticated_client, subscription):
        """取消订阅"""
        response = authenticated_client.post(
            '/api/v1/billing/subscription/cancel/'
        )
        assert response.status_code == status.HTTP_200_OK
        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end == True

    def test_reactivate_subscription(self, authenticated_client, subscription):
        """重新激活订阅"""
        subscription.cancel_at_period_end = True
        subscription.save()
        
        response = authenticated_client.post(
            '/api/v1/billing/subscription/reactivate/'
        )
        assert response.status_code == status.HTTP_200_OK
        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end == False


@pytest.mark.django_db
class TestSubscriptionUsage:
    """Test subscription usage tracking."""

    def test_get_usage(self, authenticated_client, subscription):
        """获取用量统计"""
        response = authenticated_client.get(
            '/api/v1/billing/subscription/usage/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'current_usage' in response.data
        assert 'limits' in response.data
        assert 'usage_percentages' in response.data
        assert 'remaining' in response.data

    def test_usage_percentages_calculation(self, authenticated_client, subscription, usage_record):
        """用量百分比计算"""
        response = authenticated_client.get(
            '/api/v1/billing/subscription/usage/'
        )
        assert response.status_code == status.HTTP_200_OK
        percentages = response.data['usage_percentages']
        assert all(0 <= v <= 100 for v in percentages.values())


@pytest.mark.django_db
class TestPriceTiers:
    """Test price tiers."""

    def test_list_plans(self, authenticated_client, price_tier):
        """列出所有计划"""
        response = authenticated_client.get('/api/v1/billing/plans/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCouponValidation:
    """Test coupon validation."""

    def test_validate_valid_coupon(self, authenticated_client, coupon):
        """验证有效优惠券"""
        data = {'code': coupon.code}
        response = authenticated_client.post(
            '/api/v1/billing/coupons/validate/',
            data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] == True

    def test_validate_invalid_coupon(self, authenticated_client):
        """验证无效优惠券"""
        data = {'code': 'INVALID_CODE'}
        response = authenticated_client.post(
            '/api/v1/billing/coupons/validate/',
            data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['valid'] == False

    def test_validate_expired_coupon(self, authenticated_client, expired_coupon):
        """验证过期优惠券"""
        data = {'code': expired_coupon.code}
        response = authenticated_client.post(
            '/api/v1/billing/coupons/validate/',
            data
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_my_coupons(self, authenticated_client, coupon_usage):
        """获取我的优惠券"""
        response = authenticated_client.get('/api/v1/billing/coupons/my/')
        assert response.status_code == status.HTTP_200_OK
```

---

## 三、Playwright E2E 方案

### 3.1 核心用户路径

| 路径 ID | 用户路径 | 步骤数 | 测试优先级 |
|--------|---------|-------|----------|
| AUTH-001 | 用户登录流程 | 4 | P0 |
| AUTH-002 | 用户注册流程 | 6 | P0 |
| AUTH-003 | 密码重置流程 | 5 | P1 |
| NL-001 | NL 创建工作流完整流程 | 8 | P0 |
| NL-002 | NL 对话继续修改 | 5 | P1 |
| NL-003 | NL 历史记录管理 | 4 | P2 |
| WF-001 | 工作流编辑器 - 节点操作 | 10 | P0 |
| WF-002 | 工作流编辑器 - 连线操作 | 6 | P0 |
| WF-003 | 工作流编辑器 - 保存执行 | 5 | P0 |
| WF-004 | 工作流列表管理 | 5 | P1 |
| EX-001 | 执行历史查看 | 4 | P1 |
| EX-002 | 执行取消/重试 | 4 | P2 |
| AG-001 | Agent 创建和对话 | 6 | P1 |
| KG-001 | 知识库管理 | 6 | P1 |
| ST-001 | 设置页面导航 | 5 | P2 |

### 3.2 详细测试用例矩阵

#### 认证流程 (AUTH)

| 用例 ID | 描述 | 前提条件 | 测试步骤 | 预期结果 |
|--------|-----|---------|---------|---------|
| AUTH-001-01 | 有效登录 | 无 | 1. 输入正确邮箱 2. 输入正确密码 3. 点击登录 | 登录成功跳转首页 |
| AUTH-001-02 | 无效密码 | 无 | 1. 输入邮箱 2. 输入错误密码 3. 点击登录 | 显示错误提示 |
| AUTH-001-03 | 未注册邮箱 | 无 | 1. 输入未注册邮箱 2. 输入密码 3. 点击登录 | 显示错误提示 |
| AUTH-002-01 | 成功注册 | 无 | 1. 点击注册 2. 填写信息 3. 确认密码 4. 提交 | 注册成功跳转 |
| AUTH-003-01 | 密码重置请求 | 无 | 1. 点击忘记密码 2. 输入邮箱 3. 提交 | 显示成功消息 |

#### NL Creator 流程 (NL)

| 用例 ID | 描述 | 前提条件 | 测试步骤 | 预期结果 |
|--------|-----|---------|---------|---------|
| NL-001-01 | 创建翻译工作流 | 已登录 | 1. 进入 NL Creator 2. 输入描述 3. 发送 4. 等待生成 5. 预览 6. 保存 | 工作流创建成功 |
| NL-001-02 | 流式输出显示 | 已登录 | 1. 输入 NL 2. 发送 3. 观察输出 | 逐字显示流式输出 |
| NL-001-03 | 意图检测显示 | 已登录 | 1. 输入创建意图 2. 发送 | 显示意图标签 |
| NL-002-01 | 继续对话修改 | 已登录 | 1. 创建工作流 2. 输入修改请求 3. 发送 | 工作流被修改 |
| NL-003-01 | 查看历史 | 已登录 | 1. 打开历史侧边栏 2. 浏览列表 | 显示历史会话 |
| NL-003-02 | 删除历史会话 | 已登录 | 1. 打开历史 2. 选择会话 3. 删除 | 会话被删除 |

#### 工作流编辑器 (WF)

| 用例 ID | 描述 | 前提条件 | 测试步骤 | 预期结果 |
|--------|-----|---------|---------|---------|
| WF-001-01 | 添加节点 | 打开编辑器 | 1. 从面板拖拽节点 2. 放到画布 | 节点出现在画布 |
| WF-001-02 | 选择节点 | 有节点 | 1. 点击节点 | 节点高亮选中 |
| WF-001-03 | 删除节点 | 有节点 | 1. 选择节点 2. 按 Delete | 节点被删除 |
| WF-001-04 | 配置节点 | 有节点 | 1. 双击节点 2. 修改配置 3. 保存 | 配置更新 |
| WF-002-01 | 创建连线 | 2+ 节点 | 1. 拖拽源节点输出桩 2. 连接到目标输入桩 | 连线创建 |
| WF-002-02 | 删除连线 | 有连线 | 1. 点击连线 2. 按 Delete | 连线被删除 |
| WF-003-01 | 保存工作流 | 有节点 | 1. 修改内容 2. Ctrl+S | 显示保存成功 |
| WF-003-02 | 执行工作流 | 有有效工作流 | 1. 点击执行 2. 观察状态 | 执行开始 |
| WF-003-03 | 执行成功 | 有有效工作流 | 1. 执行 2. 等待完成 | 显示执行结果 |

### 3.3 需要添加的 data-testid

#### NL Creator 页面

| 组件 | data-testid | 用途 |
|-----|------------|------|
| 聊天输入框 | `nl-chat-input` | 输入 NL 描述 |
| 发送按钮 | `nl-send-button` | 提交消息 |
| 模型选择器 | `nl-model-selector` | 选择 AI 模型 |
| 消息列表 | `nl-message-list` | 显示对话消息 |
| 用户消息 | `nl-message-user` | 用户消息容器 |
| AI 消息 | `nl-message-assistant` | AI 消息容器 |
| 意图标签 | `nl-intent-badge` | 显示检测到的意图 |
| 进度条 | `nl-progress-bar` | 显示生成进度 |
| 预览区域 | `nl-workflow-preview` | 显示生成的工作流 |
| 历史按钮 | `nl-history-button` | 打开历史侧边栏 |
| 历史列表 | `nl-history-list` | 历史会话列表 |
| 历史项 | `nl-history-item` | 单个历史会话 |
| 清空按钮 | `nl-clear-button` | 清空当前对话 |

#### 工作流编辑器页面

| 组件 | data-testid | 用途 |
|-----|------------|------|
| 画布 | `workflow-canvas` | Vue Flow 画布 |
| 节点面板 | `node-panel` | 左侧节点面板 |
| 节点项 | `node-item-{type}` | 面板中的节点项 |
| 节点 (画布上) | `canvas-node-{id}` | 画布上的节点 |
| 节点标签 | `node-label` | 节点显示名称 |
| 保存按钮 | `save-button` | 保存工作流 |
| 执行按钮 | `execute-button` | 执行工作流 |
| 验证按钮 | `validate-button` | 验证工作流 |
| 缩放按钮 | `zoom-in-button`, `zoom-out-button` | 画布缩放 |
| 适应窗口按钮 | `fit-view-button` | 适应窗口 |
| 撤销/重做 | `undo-button`, `redo-button` | 操作历史 |
| 节点配置面板 | `node-config-panel` | 节点配置表单 |
| 变量面板 | `variable-panel` | 变量管理 |
| 执行面板 | `execution-panel` | 执行状态显示 |
| 执行状态 | `execution-status` | 当前执行状态 |
| 取消按钮 | `cancel-button` | 取消执行 |
| 重试按钮 | `retry-button` | 重试执行 |

#### 执行历史页面

| 组件 | data-testid | 用途 |
|-----|------------|------|
| 执行列表 | `execution-list` | 执行记录列表 |
| 执行项 | `execution-item` | 单个执行记录 |
| 状态徽章 | `execution-status-badge` | 状态标签 |
| 详情按钮 | `execution-detail-button` | 查看详情 |
| 重新执行按钮 | `execution-rerun-button` | 重新执行 |
| 过滤选择器 | `execution-filter` | 状态过滤 |

#### Agent 页面

| 组件 | data-testid | 用途 |
|-----|------------|------|
| Agent 列表 | `agent-list` | Agent 列表 |
| Agent 项 | `agent-item` | 单个 Agent |
| 创建按钮 | `create-agent-button` | 创建新 Agent |
| 对话输入 | `agent-chat-input` | Agent 对话输入 |
| 对话列表 | `agent-conversation` | 对话记录 |
| 工具选择 | `agent-tools-selector` | 选择工具 |

#### 知识库页面

| 组件 | data-testid | 用途 |
|-----|------------|------|
| 知识库列表 | `knowledge-list` | 知识库列表 |
| 文档列表 | `document-list` | 文档列表 |
| 上传按钮 | `upload-button` | 上传文档 |
| 搜索框 | `knowledge-search` | 搜索知识库 |
| 删除按钮 | `delete-button` | 删除项 |

### 3.4 建议的 Playwright 测试文件结构

```
Frontend/tests/e2e/
├── specs/
│   ├── auth/
│   │   ├── login.spec.js
│   │   ├── register.spec.js
│   │   └── password-reset.spec.js
│   ├── nl-creator/
│   │   ├── chat-flow.spec.js
│   │   ├── streaming.spec.js
│   │   └── history.spec.js
│   ├── workflow-editor/
│   │   ├── node-operations.spec.js
│   │   ├── connection.spec.js
│   │   ├── save-execute.spec.js
│   │   └── keyboard-shortcuts.spec.js
│   ├── execution/
│   │   ├── history.spec.js
│   │   └── controls.spec.js
│   ├── agents/
│   │   ├── chat.spec.js
│   │   └── tools.spec.js
│   └── knowledge/
│       ├── upload.spec.js
│       └── search.spec.js
├── mocks/
│   ├── auth.mock.js
│   ├── nl.mock.js
│   ├── workflow.mock.js
│   ├── execution.mock.js
│   └── agent.mock.js
└── helpers/
    ├── login.helper.js
    └── navigation.helper.js
```

### 3.5 全局测试配置

```javascript
// playwright.config.js 建议配置
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }]
  ],
  
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],
  
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 四、Frontend Unit 测试补充

### 4.1 当前覆盖情况

已覆盖模块:
- `auth.api.spec.js`
- `workflow.api.spec.js`
- `agent.api.spec.js`
- `rag.api.spec.js`
- `billing.api.spec.js`
- `monitoring.api.spec.js`

### 4.2 需要补充的测试

| 文件 | 需要补充的测试 |
|-----|---------------|
| `gateway.api.spec.js` | API Key 管理, Chat, Embeddings, Health |
| `nl-workflow.api.spec.js` | 意图检测, 流式输出 |
| `tenant.api.spec.js` | 租户成员管理 |
| `marketplace.api.spec.js` | 模板浏览, 购买 |
| `integrations.api.spec.js` | 集成配置 |
| `prompt.api.spec.js` | Prompt 模板管理 |
| `admin.api.spec.js` | 管理后台 API |

---

## 五、执行检查清单

### Phase 1 实施计划

#### Week 1: Backend Gateway 模块
- [ ] 创建 `tests/backend/test_gateway.py`
- [ ] 添加 gateway fixtures 到 `tests/backend/conftest.py`
- [ ] 实现 ModelProvider ViewSet 测试
- [ ] 实现 AIModel ViewSet 测试
- [ ] 实现 UserAPIKey ViewSet 测试
- [ ] 实现 APICallLog ViewSet 测试
- [ ] 实现 GatewayChatView 测试
- [ ] 实现 GatewayHealthView 测试
- [ ] Mock GatewayService 测试
- [ ] 运行测试验证覆盖率

#### Week 2: Backend Agents 模块补充
- [ ] 创建 `tests/backend/test_agents_extended.py`
- [ ] 添加 agent fixtures
- [ ] 实现 chat 端点测试
- [ ] 实现 stream_chat 端点测试
- [ ] 实现 debug 端点测试
- [ ] 实现 tools 端点测试
- [ ] Mock AgentEngine 测试
- [ ] 运行测试验证覆盖率

#### Week 3: Backend RAG 模块补充
- [ ] 创建 `tests/backend/test_rag_extended.py`
- [ ] 添加 RAG fixtures
- [ ] 实现 search 端点测试
- [ ] 实现 upload_file 端点测试
- [ ] 实现 pipeline query 测试
- [ ] Mock RAGService 测试
- [ ] 运行测试验证覆盖率

#### Week 4: Billing 模块 + E2E 规划
- [ ] 创建 `tests/backend/test_billing_extended.py`
- [ ] 实现 subscription 测试
- [ ] 实现 coupon 验证测试
- [ ] 创建 E2E 测试规范文档
- [ ] 添加 data-testid 到组件
- [ ] 审查现有 E2E 测试

### 验收标准

- [ ] Gateway 模块测试覆盖率 > 80%
- [ ] Agents 模块测试覆盖率 > 85%
- [ ] RAG 模块测试覆盖率 > 80%
- [ ] Billing 模块测试覆盖率 > 75%
- [ ] 所有关键用户路径有 E2E 测试覆盖
- [ ] 测试通过率 100%
- [ ] CI 流水线测试通过

---

## 六、附录

### A. 测试数据管理

#### 开发环境测试数据
```python
# tests/factories.py - 使用 Factory Boy
import factory
from factory.django import DjangoModelFactory

class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')

class AgentFactory(DjangoModelFactory):
    class Meta:
        model = Agent
    
    name = factory.Sequence(lambda n: f'Agent {n}')
    owner = factory.SubFactory(UserFactory)
    model = 'gpt-4'
    system_prompt = 'You are a helpful assistant.'
```

### B. 测试辅助函数

```python
# tests/helpers.py
def create_authenticated_client(user=None):
    """创建认证客户端"""
    if user is None:
        user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client

def mock_llm_response(text="Test response"):
    """模拟 LLM 响应"""
    return MagicMock(
        content=text,
        model='gpt-4',
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=100,
        cost=0.001
    )
```

### C. 测试覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|-----|----------|----------|
| gateway | 0% | 80% |
| agents | 40% | 85% |
| rag | 45% | 80% |
| billing | 30% | 75% |
| nl_workflow | 70% | 85% |
| workflows | 65% | 80% |
| monitoring | 50% | 70% |

---

**文档版本**: 1.0  
**创建日期**: 2026-06-03  
**下次审查**: 2026-06-10
