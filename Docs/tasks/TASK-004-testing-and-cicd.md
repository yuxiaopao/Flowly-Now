# 任务 4：测试框架与 CI/CD 流水线

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | 测试框架与 CI/CD 流水线 |
| **优先级** | P1 - 重要功能 |
| **预估工时** | 3-4 天 |
| **前置依赖** | 核心功能开发完成 |

## 任务目标

建立完整的测试体系，实现自动化 CI/CD 流水线。

## 详细需求

### 1.1 后端测试框架

#### 1.1.1 测试目录结构

```
Backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # pytest 配置
│   ├── factories/                  # Factory 模式
│   │   ├── __init__.py
│   │   ├── user_factory.py
│   │   ├── workflow_factory.py
│   │   ├── node_factory.py
│   │   └── execution_factory.py
│   │
│   ├── unit/                      # 单元测试
│   │   ├── __init__.py
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_services.py
│   │   └── test_utils.py
│   │
│   ├── integration/               # 集成测试
│   │   ├── __init__.py
│   │   ├── test_workflows.py
│   │   ├── test_api.py
│   │   └── test_executor.py
│   │
│   └── e2e/                      # 端到端测试
│       ├── __init__.py
│       └── test_workflow_execution.py
│
├── pytest.ini
├── setup.cfg
└── .coveragerc
```

#### 1.1.2 pytest 配置

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=.
    --cov-report=term-missing
    --cov-report=html:coverage_html
    --cov-branch
testpaths = tests
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    api: API 测试
    executor: 执行器测试
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

#### 1.1.3 conftest.py 配置

```python
# tests/conftest.py

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import factory

User = get_user_model()


# ============== Fixtures ==============

@pytest.fixture
def user(db):
    """创建测试用户"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def api_client():
    """API 测试客户端"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """已认证的 API 客户端"""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.user = user
    return api_client


@pytest.fixture
def admin_user(db):
    """创建管理员用户"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


# ============== Workflow Fixtures ==============

@pytest.fixture
def workflow(db, user):
    """创建测试工作流"""
    from tests.factories import WorkflowFactory
    return WorkflowFactory(owner=user)


@pytest.fixture
def workflow_with_nodes(db, user):
    """创建带节点的工作流"""
    from tests.factories import WorkflowFactory, NodeFactory, EdgeFactory
    
    workflow = WorkflowFactory(owner=user)
    
    # 创建节点
    start_node = NodeFactory(
        workflow=workflow,
        node_type='start',
        name='开始',
        position_x=100,
        position_y=100
    )
    
    llm_node = NodeFactory(
        workflow=workflow,
        node_type='llm',
        name='LLM处理',
        position_x=300,
        position_y=100,
        config={'model': 'gpt-4', 'temperature': 0.7}
    )
    
    end_node = NodeFactory(
        workflow=workflow,
        node_type='end',
        name='结束',
        position_x=500,
        position_y=100
    )
    
    # 创建连线
    EdgeFactory(workflow=workflow, source_node=start_node, target_node=llm_node)
    EdgeFactory(workflow=workflow, source_node=llm_node, target_node=end_node)
    
    return workflow


# ============== Database Fixtures ==============

@pytest.fixture
def clean_db(db):
    """清理数据库（每个测试前）"""
    yield
    # 测试后清理
    pass


@pytest.fixture(scope='session')
def django_db_setup():
    """会话级数据库设置"""
    pass


# ============== Celery Fixtures ==============

@pytest.fixture
def celery_eager_setup(settings):
    """启用 Celery eager 模式（同步执行）"""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
```

#### 1.1.4 Factory 模式

```python
# tests/factories/__init__.py

from .user_factory import UserFactory
from .workflow_factory import WorkflowFactory
from .node_factory import NodeFactory
from .edge_factory import EdgeFactory
from .execution_factory import ExecutionFactory

__all__ = [
    'UserFactory',
    'WorkflowFactory',
    'NodeFactory',
    'EdgeFactory',
    'ExecutionFactory',
]
```

```python
# tests/factories/workflow_factory.py

import factory
from django.contrib.auth import get_user_model
from workflows.models import Workflow, Node, Edge

User = get_user_model()


class WorkflowFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workflow
    
    name = factory.Sequence(lambda n: f'工作流 {n}')
    description = factory.Faker('sentence')
    owner = factory.SubFactory('tests.factories.UserFactory')
    status = 'draft'
    version = 1
    
    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.tags = extracted


class NodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Node
    
    workflow = factory.SubFactory('tests.factories.WorkflowFactory')
    node_type = 'llm'
    name = factory.Sequence(lambda n: f'节点 {n}')
    position_x = 100
    position_y = factory.Sequence(lambda n: n * 100)
    config = factory.Dict({})
    
    class Params:
        is_start = factory.Trait(node_type='start', name='开始')
        is_end = factory.Trait(node_type='end', name='结束')
        is_llm = factory.Trait(
            node_type='llm',
            name='LLM处理',
            config={'model': 'gpt-4', 'temperature': 0.7}
        )
        is_condition = factory.Trait(
            node_type='condition',
            name='条件判断',
            config={'conditions': []}
        )


class EdgeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Edge
    
    workflow = factory.SubFactory('tests.factories.WorkflowFactory')
    source_node = factory.SubFactory(NodeFactory, workflow=factory.SelfAttribute('..workflow'))
    target_node = factory.SubFactory(NodeFactory, workflow=factory.SelfAttribute('..workflow'))
    label = factory.Faker('word')
```

### 1.2 后端单元测试

#### 1.2.1 模型测试

```python
# tests/unit/test_models.py

import pytest
from workflows.models import Workflow, Node, Edge


@pytest.mark.unit
class TestWorkflowModel:
    """工作流模型测试"""
    
    def test_workflow_creation(self, user):
        """测试工作流创建"""
        workflow = Workflow.objects.create(
            name='测试工作流',
            owner=user,
            status='draft'
        )
        
        assert workflow.id is not None
        assert workflow.name == '测试工作流'
        assert workflow.owner == user
        assert workflow.status == 'draft'
        assert workflow.version == 1
    
    def test_workflow_str(self, workflow):
        """测试工作流字符串表示"""
        assert str(workflow) == workflow.name
    
    def test_workflow_node_count(self, workflow_with_nodes):
        """测试节点计数属性"""
        assert workflow_with_nodes.node_count == 3
    
    def test_workflow_execution_count(self, workflow_with_nodes):
        """测试执行计数属性"""
        assert workflow_with_nodes.execution_count == 0
    
    def test_workflow_tags(self, user):
        """测试标签功能"""
        workflow = Workflow.objects.create(
            name='带标签的工作流',
            owner=user,
            tags=['AI', '自动化', '测试']
        )
        
        assert workflow.tags == ['AI', '自动化', '测试']


@pytest.mark.unit
class TestNodeModel:
    """节点模型测试"""
    
    def test_node_creation(self, workflow):
        """测试节点创建"""
        node = Node.objects.create(
            workflow=workflow,
            node_type='llm',
            name='LLM节点',
            position_x=100,
            position_y=200
        )
        
        assert node.id is not None
        assert node.workflow == workflow
        assert node.node_type == 'llm'
    
    def test_node_str(self, node):
        """测试节点字符串表示"""
        assert 'LLM处理' in str(node)
    
    def test_node_config(self, workflow):
        """测试节点配置"""
        config = {
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        node = Node.objects.create(
            workflow=workflow,
            node_type='llm',
            name='配置的节点',
            config=config
        )
        
        assert node.config == config
        assert node.config['model'] == 'gpt-4'
```

#### 1.2.2 服务层测试

```python
# tests/unit/test_services.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from workflows.services.executor import WorkflowExecutor, ExecutionContext
from workflows.services.workflow_service import WorkflowService


@pytest.mark.unit
class TestExecutionContext:
    """执行上下文测试"""
    
    def test_context_initialization(self):
        """测试上下文初始化"""
        input_data = {'key': 'value'}
        context = ExecutionContext(input_data)
        
        assert context.input_data == input_data
        assert context.variables == {}
        assert context.nodes_output == {}
    
    def test_set_and_get_variable(self):
        """测试变量设置和获取"""
        context = ExecutionContext({})
        
        context.set_var('name', 'Alice')
        assert context.get_var('name') == 'Alice'
    
    def test_get_var_default(self):
        """测试获取不存在的变量"""
        context = ExecutionContext({})
        
        assert context.get_var('nonexistent', 'default') == 'default'
    
    def test_node_output_storage(self):
        """测试节点输出存储"""
        context = ExecutionContext({})
        
        context.set_node_output('node-1', {'result': 'success'})
        assert context.get_node_output('node-1') == {'result': 'success'}


@pytest.mark.unit
class TestWorkflowService:
    """工作流服务测试"""
    
    def test_create_workflow(self, user):
        """测试创建工作流"""
        data = {
            'name': '新工作流',
            'description': '测试描述',
            'tags': ['test']
        }
        
        workflow = WorkflowService.create_workflow(user, data)
        
        assert workflow.id is not None
        assert workflow.name == '新工作流'
        assert workflow.owner == user
    
    def test_validate_workflow_valid(self, workflow_with_nodes):
        """测试验证有效的工作流"""
        is_valid, errors = WorkflowService.validate_workflow(workflow_with_nodes)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_workflow_missing_start(self, workflow, user):
        """测试缺少开始节点"""
        from tests.factories import NodeFactory
        
        # 创建只有结束节点的无效工作流
        NodeFactory(workflow=workflow, node_type='end', name='结束')
        
        is_valid, errors = WorkflowService.validate_workflow(workflow)
        
        assert is_valid is False
        assert any('开始节点' in e for e in errors)
    
    @patch('workflows.services.llm_gateway.LLMGateway.chat')
    def test_execute_llm_node(self, mock_chat, workflow_with_nodes):
        """测试 LLM 节点执行"""
        mock_chat.return_value = {
            'content': '测试响应',
            'usage': {'total_tokens': 100}
        }
        
        executor = WorkflowExecutor(workflow_with_nodes)
        result = executor._execute_llm_node(
            workflow_with_nodes.nodes.get(node_type='llm')
        )
        
        assert result == '测试响应'
        mock_chat.assert_called_once()
```

### 1.3 API 测试

```python
# tests/integration/test_api.py

import pytest
from rest_framework import status


@pytest.mark.integration
@pytest.mark.api
class TestWorkflowAPI:
    """工作流 API 测试"""
    
    def test_list_workflows(self, authenticated_client, workflow):
        """测试列出工作流"""
        response = authenticated_client.get('/api/workflows/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.json()
    
    def test_create_workflow(self, authenticated_client):
        """测试创建工作流"""
        data = {
            'name': '新工作流',
            'description': '测试描述'
        }
        
        response = authenticated_client.post('/api/workflows/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['name'] == '新工作流'
    
    def test_get_workflow_detail(self, authenticated_client, workflow):
        """测试获取工作流详情"""
        response = authenticated_client.get(f'/api/workflows/{workflow.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['id'] == str(workflow.id)
    
    def test_update_workflow(self, authenticated_client, workflow):
        """测试更新工作流"""
        data = {'name': '更新后的名称'}
        
        response = authenticated_client.patch(
            f'/api/workflows/{workflow.id}/',
            data
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['name'] == '更新后的名称'
    
    def test_delete_workflow(self, authenticated_client, workflow):
        """测试删除工作流"""
        response = authenticated_client.delete(f'/api/workflows/{workflow.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # 验证已删除
        response = authenticated_client.get(f'/api/workflows/{workflow.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_execute_workflow(self, authenticated_client, workflow_with_nodes):
        """测试执行工作流"""
        data = {'input_data': {'query': '测试输入'}}
        
        response = authenticated_client.post(
            f'/api/workflows/{workflow_with_nodes.id}/execute/',
            data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['status'] in ['queued', 'running']


@pytest.mark.integration
@pytest.mark.api
class TestAuthentication:
    """认证 API 测试"""
    
    def test_register_user(self, api_client):
        """测试用户注册"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123'
        }
        
        response = api_client.post('/api/auth/register/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.json()
        assert 'refresh' in response.json()
    
    def test_login(self, api_client, user):
        """测试登录"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = api_client.post('/api/auth/login/', data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.json()
        assert 'refresh' in response.json()
    
    def test_login_invalid_credentials(self, api_client, user):
        """测试无效凭证登录"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        
        response = api_client.post('/api/auth/login/', data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_token(self, api_client, user):
        """测试刷新 Token"""
        # 先登录获取 refresh token
        login_response = api_client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        refresh_token = login_response.json()['refresh']
        
        # 刷新 Token
        response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.json()
```

### 1.4 前端测试

#### 1.4.1 Vitest 配置

```javascript
// Frontend/vitest.config.js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,ts}', 'tests/**/*.{test,spec}.{js,ts}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: 'coverage',
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.d.ts',
        '**/*.config.js'
      ]
    },
    setupFiles: ['./tests/setup.js'],
    testTimeout: 10000
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  }
})
```

#### 1.4.2 测试设置

```javascript
// Frontend/tests/setup.js
import { expect } from 'vitest'
import * as matchers from '@testing-library/jest-dom/matchers'

// 添加 jest-dom 匹配器
expect.extend(matchers)

// 全局 Mock
global.fetch = vi.fn()

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url
    this.readyState = 1
    this.onopen = null
    this.onmessage = null
    this.onclose = null
    this.send = vi.fn()
    this.close = vi.fn()
  }
  
  // 模拟方法
  _simulateOpen() {
    if (this.onopen) this.onopen()
  }
  
  _simulateMessage(data) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(data) })
  }
  
  _simulateClose() {
    if (this.onclose) this.onclose()
  }
}

global.WebSocket = MockWebSocket

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn()
  },
  ElNotification: {
    success: vi.fn(),
    error: vi.fn()
  }
}))
```

#### 1.4.3 组件测试

```javascript
// Frontend/tests/unit/components/WorkflowCanvas.spec.js

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WorkflowCanvas from '@/components/workflow/WorkflowCanvas.vue'
import { useWorkflowStore } from '@/stores/workflow'

describe('WorkflowCanvas', () => {
  let wrapper
  let store
  
  beforeEach(() => {
    setActivePinia(createPinia())
    store = useWorkflowStore()
    
    wrapper = mount(WorkflowCanvas, {
      global: {
        stubs: {
          'el-button': true,
          'el-icon': true
        }
      }
    })
  })
  
  it('renders canvas correctly', () => {
    expect(wrapper.find('.workflow-canvas').exists()).toBe(true)
  })
  
  it('adds node via store action', async () => {
    const nodeData = {
      node_type: 'llm',
      name: '测试节点',
      position_x: 100,
      position_y: 100
    }
    
    store.addNode(nodeData)
    
    expect(store.nodes.length).toBe(1)
    expect(store.nodes[0].name).toBe('测试节点')
  })
  
  it('updates node position', async () => {
    store.addNode({
      node_type: 'llm',
      name: '测试节点',
      position_x: 0,
      position_y: 0
    })
    
    const nodeId = store.nodes[0].id
    store.updateNode(nodeId, { position_x: 200, position_y: 300 })
    
    const updatedNode = store.nodes.find(n => n.id === nodeId)
    expect(updatedNode.position_x).toBe(200)
    expect(updatedNode.position_y).toBe(300)
  })
  
  it('removes node', async () => {
    store.addNode({
      node_type: 'llm',
      name: '测试节点'
    })
    
    const nodeId = store.nodes[0].id
    store.removeNode(nodeId)
    
    expect(store.nodes.length).toBe(0)
  })
})
```

#### 1.4.4 Store 测试

```javascript
// Frontend/tests/unit/stores/workflow.spec.js

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkflowStore } from '@/stores/workflow'

// Mock API
vi.mock('@/api/workflow', () => ({
  workflowApi: {
    getList: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    execute: vi.fn()
  }
}))

describe('useWorkflowStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  
  describe('State', () => {
    it('initializes with empty state', () => {
      const store = useWorkflowStore()
      
      expect(store.workflows).toEqual([])
      expect(store.currentWorkflow).toBe(null)
      expect(store.nodes).toEqual([])
      expect(store.edges).toEqual([])
    })
  })
  
  describe('Actions', () => {
    it('fetches workflow list', async () => {
      const mockWorkflows = [
        { id: '1', name: '工作流1' },
        { id: '2', name: '工作流2' }
      ]
      
      const { workflowApi } = await import('@/api/workflow')
      workflowApi.getList.mockResolvedValue({ results: mockWorkflows })
      
      const store = useWorkflowStore()
      await store.fetchWorkflows()
      
      expect(store.workflows).toEqual(mockWorkflows)
      expect(workflowApi.getList).toHaveBeenCalled()
    })
    
    it('creates workflow', async () => {
      const newWorkflow = { name: '新工作流' }
      const createdWorkflow = { id: '1', ...newWorkflow }
      
      const { workflowApi } = await import('@/api/workflow')
      workflowApi.create.mockResolvedValue(createdWorkflow)
      
      const store = useWorkflowStore()
      const result = await store.createWorkflow(newWorkflow)
      
      expect(result).toEqual(createdWorkflow)
      expect(store.workflows[0]).toEqual(createdWorkflow)
    })
    
    it('sets dirty flag on node change', async () => {
      const store = useWorkflowStore()
      
      // 模拟加载工作流
      store.nodes = [{ id: '1', name: '节点1' }]
      
      // 修改节点
      store.updateNode('1', { name: '修改后的节点' })
      
      expect(store.isDirty).toBe(true)
    })
  })
  
  describe('Getters', () => {
    it('calculates hasUnsavedChanges correctly', () => {
      const store = useWorkflowStore()
      
      // 无工作流时
      expect(store.hasUnsavedChanges).toBe(false)
      
      // 有工作流但无更改
      store.currentWorkflow = { nodes: [] }
      store.nodes = []
      expect(store.hasUnsavedChanges).toBe(false)
      
      // 有更改
      store.nodes = [{ id: '1', name: '新节点' }]
      expect(store.hasUnsavedChanges).toBe(true)
    })
  })
})
```

### 1.5 CI/CD 流水线

#### 1.5.1 GitHub Actions 配置

```yaml
# .github/workflows/ci.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  NODE_VERSION: '20'
  PYTHON_VERSION: '3.12'
  DB_ENGINE: 'mysql'
  DB_NAME: 'flowly_test'
  DB_HOST: '127.0.0.1'
  DB_PORT: '3306'

jobs:
  # ============== 代码检查 ==============
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: ${{ env.DB_NAME }}
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r Backend/requirements.txt
          pip install flake8 black isort
      
      - name: Run Python linters
        run: |
          flake8 Backend --max-line-length=120 --ignore=E203,W503
          black --check Backend
          isort --check-only Backend
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: Frontend/package-lock.json
      
      - name: Install Node dependencies
        run: npm ci
      
      - name: Run ESLint
        run: npm run lint
      
      - name: Run Prettier
        run: npm run format:check

  # ============== 后端测试 ==============
  backend-test:
    name: Backend Tests
    runs-on: ubuntu-latest
    needs: lint
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: ${{ env.DB_NAME }}
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('Backend/requirements.txt') }}
      
      - name: Install dependencies
        run: |
          pip install -r Backend/requirements.txt
          pip install pytest pytest-django pytest-cov pytest-asyncio factory-boy
      
      - name: Setup test database
        run: |
          mysql -h 127.0.0.1 -u root -proot -e "CREATE DATABASE IF NOT EXISTS ${{ env.DB_NAME }};"
      
      - name: Run backend tests
        env:
          DJANGO_SETTINGS_MODULE: config.settings.test
          DB_NAME: ${{ env.DB_NAME }}
          DB_HOST: ${{ env.DB_HOST }}
          DB_PORT: ${{ env.DB_PORT }}
          DB_USER: root
          DB_PASSWORD: root
          REDIS_URL: redis://localhost:6379/0
        run: |
          cd Backend
          pytest tests/ -v --cov=. --cov-report=xml --cov-report=html
        continue-on-error: true
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: Backend/coverage.xml
          flags: backend

  # ============== 前端测试 ==============
  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    needs: lint
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: Frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run frontend tests
        run: npm run test:unit
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: Frontend/coverage/coverage-summary.json
          flags: frontend

  # ============== 构建 ==============
  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Build Docker images
        run: |
          docker-compose -f docker/docker-compose.yml build
      
      - name: Save Docker images
        run: |
          docker save flowly-backend -o backend.tar
          docker save flowly-frontend -o frontend.tar
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: docker-images
          path: |
            backend.tar
            frontend.tar
          retention-days: 7

  # ============== 部署预览环境 ==============
  deploy-preview:
    name: Deploy Preview
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'pull_request'
    
    environment:
      name: preview
      url: ${{ steps.deploy.outputs.url }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to preview
        id: deploy
        run: |
          # 部署脚本
          echo "url=https://preview-${{ github.event.number }}.flowly.example.com" >> $GITHUB_OUTPUT
      
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Preview deployed to: ${{ steps.deploy.outputs.url }}'
            })

  # ============== 部署生产环境 ==============
  deploy-production:
    name: Deploy Production
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    environment:
      name: production
      url: https://flowly.example.com
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download Docker images
        uses: actions/download-artifact@v4
        with:
          name: docker-images
      
      - name: Deploy to production
        run: |
          docker load -i backend.tar
          docker load -i frontend.tar
          # 部署脚本
        environment:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
```

## 验收标准

- [ ] pytest 配置完成
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖主要 API
- [ ] 前端 Vitest 配置完成
- [ ] 前端测试覆盖率 > 70%
- [ ] GitHub Actions CI/CD 流水线配置完成
- [ ] 自动代码检查（ESLint, Flake8）
- [ ] 自动化测试和部署

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `Backend/tests/conftest.py` | pytest 配置 |
| `Backend/tests/factories/` | Factory 模式 |
| `Backend/tests/unit/` | 单元测试 |
| `Backend/tests/integration/` | 集成测试 |
| `Backend/pytest.ini` | pytest 配置 |
| `Backend/.coveragerc` | 覆盖率配置 |
| `Frontend/vitest.config.js` | Vitest 配置 |
| `Frontend/tests/setup.js` | 测试设置 |
| `Frontend/tests/unit/` | 单元测试 |
| `.github/workflows/ci.yml` | CI/CD 配置 |
