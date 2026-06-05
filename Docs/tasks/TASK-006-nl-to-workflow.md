# 任务 6：自然语言生成工作流 (NL to Workflow)

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | NL to Workflow（自然语言生成工作流） |
| **优先级** | P1 - 重要功能 |
| **预估工时** | 4-5 天 |
| **前置依赖** | 工作流模型、执行引擎、LLM 集成 |

## 任务目标

实现自然语言生成工作流功能，用户可以用自然语言描述需求，系统自动生成可视化工作流。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                       NL to Workflow 架构                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                           用户输入                                    │
│  "创建一个工作流：先让用户输入问题，然后用 GPT-4 回答问题，              │
│   如果回答包含 '错误' 就发邮件通知我，否则保存到数据库"                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          LLM 解析层                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Prompt Engineering                        │   │
│  │  • 意图识别    • 实体提取    • 工作流结构化                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                  │                                  │
│                                  ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     结构化输出 (JSON)                        │   │
│  │  {                                                           │   │
│  │    "nodes": [...],                                          │   │
│  │    "edges": [...],                                          │   │
│  │    "explanation": "..."                                    │   │
│  │  }                                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         工作流验证层                                 │
│  • 节点有效性检查    • 连线完整性检查    • 配置验证                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         工作流预览与编辑                              │
│  • 可视化预览        • 用户确认/修改    • 保存到数据库                │
└─────────────────────────────────────────────────────────────────────┘
```

## 详细需求

### 1.1 NL 解析服务

#### 1.1.1 解析器核心

```python
# Backend/nl_to_workflow/services/parser.py

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """节点类型枚举"""
    START = "start"
    END = "end"
    LLM = "llm"
    PROMPT = "prompt"
    INPUT = "input"
    OUTPUT = "output"
    CONDITION = "condition"
    TOOL = "tool"
    CODE = "code"
    HTTP = "http"
    EMAIL = "email"
    DATABASE = "database"
    LOOP = "loop"
    VARIABLE = "variable"


@dataclass
class ParsedNode:
    """解析后的节点"""
    node_type: NodeType
    name: str
    description: Optional[str] = None
    config: Dict = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    conditions: List[Dict] = field(default_factory=list)


@dataclass
class ParsedEdge:
    """解析后的连线"""
    source: str
    target: str
    source_handle: str = "default"
    target_handle: str = "default"
    label: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class ParsedWorkflow:
    """解析后的工作流"""
    name: str
    description: Optional[str] = None
    nodes: List[ParsedNode] = field(default_factory=list)
    edges: List[ParsedEdge] = field(default_factory=list)
    variables: List[Dict] = field(default_factory=list)
    explanation: str = ""


class NLToWorkflowParser:
    """自然语言到工作流解析器"""
    
    # 系统提示词模板
    SYSTEM_PROMPT = """你是一个工作流设计助手。用户会用自然语言描述他们想要的工作流，你需要：
    
1. 识别工作流的目标和组成部分
2. 确定需要的节点类型和顺序
3. 识别条件判断和分支逻辑
4. 提取配置参数

请严格按照以下 JSON 格式输出（不要输出其他内容）：

{
    "name": "工作流名称",
    "description": "工作流描述",
    "nodes": [
        {
            "type": "节点类型",
            "name": "节点名称",
            "description": "节点描述",
            "config": { /* 节点配置 */ }
        }
    ],
    "edges": [
        {
            "source": "源节点名称",
            "target": "目标节点名称",
            "label": "连线标签(可选)"
        }
    ],
    "variables": [
        {
            "name": "变量名",
            "type": "变量类型",
            "default": "默认值"
        }
    ],
    "explanation": "你对工作流的解释说明"
}

节点类型说明：
- start: 开始节点
- end: 结束节点
- input: 用户输入节点
- llm: 大语言模型节点 (需要指定 model)
- prompt: 提示词节点
- condition: 条件判断节点
- tool: 工具调用节点
- code: 代码执行节点
- http: HTTP 请求节点
- email: 邮件发送节点
- database: 数据库操作节点
- output: 输出节点

示例输入：
"创建一个工作流：先让用户输入名字，然后用 GPT-4 回复'你好 {名字}'，最后打印结果"

示例输出：
{
    "name": "问候工作流",
    "description": "简单的用户问候流程",
    "nodes": [
        {"type": "start", "name": "开始", "config": {}},
        {"type": "input", "name": "获取用户名", "config": {"variable": "name", "prompt": "请输入您的名字"}},
        {"type": "llm", "name": "AI 回复", "config": {"model": "gpt-4", "prompt": "你好 {name}"}},
        {"type": "output", "name": "打印结果", "config": {"template": "AI 回复: {llm_output}"}},
        {"type": "end", "name": "结束", "config": {}}
    ],
    "edges": [
        {"source": "开始", "target": "获取用户名"},
        {"source": "获取用户名", "target": "AI 回复"},
        {"source": "AI 回复", "target": "打印结果"},
        {"source": "打印结果", "target": "结束"}
    ],
    "variables": [{"name": "name", "type": "string"}],
    "explanation": "这个工作流会先让用户输入名字，然后调用 GPT-4 生成回复，最后输出结果"
}"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or self._get_default_llm_service()
    
    def _get_default_llm_service(self):
        """获取默认的 LLM 服务"""
        from gateway.services import LLMGateway
        return LLMGateway()
    
    async def parse(self, user_input: str) -> ParsedWorkflow:
        """解析用户输入为工作流"""
        # 调用 LLM 获取结构化输出
        response = await self.llm_service.chat(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,  # 低温度确保输出稳定
            max_tokens=4000
        )
        
        # 解析 JSON 响应
        content = response.get('content', '')
        workflow_data = self._extract_json(content)
        
        # 构建工作流对象
        return self._build_workflow(workflow_data)
    
    def _extract_json(self, text: str) -> Dict:
        """从文本中提取 JSON"""
        # 尝试提取代码块中的 JSON
        json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(json_pattern, text)
        
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass
        
        # 尝试直接解析整个文本
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试找到 JSON 对象
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        
        raise ValueError("无法解析 LLM 返回的 JSON")
    
    def _build_workflow(self, data: Dict) -> ParsedWorkflow:
        """构建工作流对象"""
        nodes = []
        node_map = {}  # 名称到节点的映射
        
        # 解析节点
        for i, node_data in enumerate(data.get('nodes', [])):
            node_type = self._normalize_node_type(node_data.get('type'))
            node = ParsedNode(
                node_type=node_type,
                name=node_data.get('name', f'Node_{i}'),
                description=node_data.get('description'),
                config=node_data.get('config', {}),
                position=self._calculate_position(i, len(data.get('nodes', [])))
            )
            nodes.append(node)
            node_map[node.name] = node
        
        # 解析连线
        edges = []
        for edge_data in data.get('edges', []):
            source = edge_data.get('source')
            target = edge_data.get('target')
            
            if source in node_map and target in node_map:
                edge = ParsedEdge(
                    source=source,
                    target=target,
                    label=edge_data.get('label'),
                    condition=edge_data.get('condition')
                )
                edges.append(edge)
        
        return ParsedWorkflow(
            name=data.get('name', '未命名工作流'),
            description=data.get('description'),
            nodes=nodes,
            edges=edges,
            variables=data.get('variables', []),
            explanation=data.get('explanation', '')
        )
    
    def _normalize_node_type(self, type_str: str) -> NodeType:
        """规范化节点类型"""
        type_mapping = {
            'start': NodeType.START,
            'end': NodeType.END,
            'input': NodeType.INPUT,
            'llm': NodeType.LLM,
            'prompt': NodeType.PROMPT,
            'condition': NodeType.CONDITION,
            'tool': NodeType.TOOL,
            'code': NodeType.CODE,
            'http': NodeType.HTTP,
            'email': NodeType.EMAIL,
            'database': NodeType.DATABASE,
            'output': NodeType.OUTPUT,
            'loop': NodeType.LOOP,
            'variable': NodeType.VARIABLE,
        }
        
        normalized = type_str.lower().strip()
        return type_mapping.get(normalized, NodeType.LLM)
    
    def _calculate_position(self, index: int, total: int) -> Tuple[int, int]:
        """计算节点位置"""
        # 简单布局：水平排列
        x = 100 + (index % 4) * 250
        y = 100 + (index // 4) * 150
        return (x, y)
```

### 1.2 工作流验证器

```python
# Backend/nl_to_workflow/services/validator.py

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """验证错误"""
    field: str
    message: str
    severity: str = "error"  # error, warning


class WorkflowValidator:
    """工作流验证器"""
    
    def validate(self, workflow) -> Tuple[bool, List[ValidationError]]:
        """验证工作流"""
        errors = []
        
        # 1. 检查开始和结束节点
        errors.extend(self._check_start_end_nodes(workflow))
        
        # 2. 检查节点连接
        errors.extend(self._check_node_connections(workflow))
        
        # 3. 检查必需节点
        errors.extend(self._check_required_nodes(workflow))
        
        # 4. 检查配置有效性
        errors.extend(self._check_node_configs(workflow))
        
        # 5. 检查循环依赖
        errors.extend(self._check_cycles(workflow))
        
        has_errors = any(e.severity == "error" for e in errors)
        return not has_errors, errors
    
    def _check_start_end_nodes(self, workflow) -> List[ValidationError]:
        """检查开始和结束节点"""
        errors = []
        node_types = [n.node_type for n in workflow.nodes]
        
        if "start" not in node_types:
            errors.append(ValidationError(
                field="nodes",
                message="工作流必须包含开始节点",
                severity="error"
            ))
        
        if "end" not in node_types:
            errors.append(ValidationError(
                field="nodes",
                message="工作流必须包含结束节点",
                severity="error"
            ))
        
        # 检查开始和结束节点数量
        start_count = node_types.count("start")
        end_count = node_types.count("end")
        
        if start_count > 1:
            errors.append(ValidationError(
                field="nodes",
                message=f"开始节点数量不应超过 1 个，当前有 {start_count} 个",
                severity="warning"
            ))
        
        if end_count == 0:
            errors.append(ValidationError(
                field="nodes",
                message="工作流没有结束节点",
                severity="warning"
            ))
        
        return errors
    
    def _check_node_connections(self, workflow) -> List[ValidationError]:
        """检查节点连接"""
        errors = []
        node_names = {n.name for n in workflow.nodes}
        
        # 检查连线引用的节点是否存在
        for edge in workflow.edges:
            if edge.source not in node_names:
                errors.append(ValidationError(
                    field=f"edge:{edge.source}->{edge.target}",
                    message=f"连线源节点 '{edge.source}' 不存在",
                    severity="error"
                ))
            
            if edge.target not in node_names:
                errors.append(ValidationError(
                    field=f"edge:{edge.source}->{edge.target}",
                    message=f"连线目标节点 '{edge.target}' 不存在",
                    severity="error"
                ))
        
        # 检查孤立节点
        connected_nodes = set()
        for edge in workflow.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)
        
        for node in workflow.nodes:
            if node.node_type not in ["start", "end"]:
                if node.name not in connected_nodes:
                    errors.append(ValidationError(
                        field=f"node:{node.name}",
                        message=f"节点 '{node.name}' 没有连接到任何其他节点",
                        severity="warning"
                    ))
        
        return errors
    
    def _check_required_nodes(self, workflow) -> List[ValidationError]:
        """检查必需节点配置"""
        errors = []
        
        for node in workflow.nodes:
            if node.node_type == "llm":
                if not node.config.get("model"):
                    errors.append(ValidationError(
                        field=f"node:{node.name}",
                        message=f"LLM 节点 '{node.name}' 必须指定模型",
                        severity="error"
                    ))
            
            elif node.node_type == "condition":
                if not node.config.get("conditions"):
                    errors.append(ValidationError(
                        field=f"node:{node.name}",
                        message=f"条件节点 '{node.name}' 必须指定条件",
                        severity="error"
                    ))
            
            elif node.node_type == "input":
                if not node.config.get("variable"):
                    errors.append(ValidationError(
                        field=f"node:{node.name}",
                        message=f"输入节点 '{node.name}' 必须指定变量名",
                        severity="warning"
                    ))
        
        return errors
    
    def _check_node_configs(self, workflow) -> List[ValidationError]:
        """检查节点配置"""
        errors = []
        
        for node in workflow.nodes:
            # 检查 LLM 配置
            if node.node_type == "llm":
                model = node.config.get("model", "")
                if model and not self._is_valid_model(model):
                    errors.append(ValidationError(
                        field=f"node:{node.name}",
                        message=f"模型 '{model}' 不在支持列表中",
                        severity="warning"
                    ))
        
        return errors
    
    def _check_cycles(self, workflow) -> List[ValidationError]:
        """检查循环依赖"""
        errors = []
        
        # 构建邻接表
        graph = {n.name: [] for n in workflow.nodes}
        for edge in workflow.edges:
            graph[edge.source].append(edge.target)
        
        # DFS 检测循环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if has_cycle(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    errors.append(ValidationError(
                        field="edges",
                        message=f"检测到循环依赖: {' -> '.join(cycle)}",
                        severity="error"
                    ))
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node, []):
                    break
        
        return errors
    
    def _is_valid_model(self, model: str) -> bool:
        """检查模型是否有效"""
        valid_models = [
            "gpt-4", "gpt-4-turbo", "gpt-4o",
            "gpt-3.5-turbo",
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
            "claude-2", "claude-instant"
        ]
        return any(model.lower().startswith(m.lower()) for m in valid_models)
```

### 1.3 转换服务

```python
# Backend/nl_to_workflow/services/converters.py

from typing import Dict, List
from workflows.models import Workflow, Node, Edge


class WorkflowConverter:
    """工作流转换器 - 将解析结果转换为数据库模型"""
    
    def convert_to_db(self, parsed_workflow, owner) -> Workflow:
        """将解析的工作流转换为数据库工作流"""
        # 创建工作流
        workflow = Workflow.objects.create(
            name=parsed_workflow.name,
            description=parsed_workflow.description or "",
            owner=owner,
            status='draft',
            version=1
        )
        
        # 创建节点映射
        node_map = {}
        
        # 添加开始节点（如果不存在）
        has_start = any(n.node_type.value == "start" for n in parsed_workflow.nodes)
        if not has_start:
            start_node = Node.objects.create(
                workflow=workflow,
                node_type="start",
                name="开始",
                position_x=100,
                position_y=100
            )
            node_map["开始"] = start_node
        
        # 创建节点
        for i, parsed_node in enumerate(parsed_workflow.nodes):
            # 跳过开始和结束节点（自动添加）
            if parsed_node.node_type.value in ["start", "end"]:
                continue
            
            node = Node.objects.create(
                workflow=workflow,
                node_type=parsed_node.node_type.value,
                name=parsed_node.name,
                description=parsed_node.description or "",
                position_x=parsed_node.position[0],
                position_y=parsed_node.position[1],
                config=parsed_node.config
            )
            node_map[parsed_node.name] = node
        
        # 添加结束节点（如果不存在）
        has_end = any(n.node_type.value == "end" for n in parsed_workflow.nodes)
        if not has_end:
            end_node = Node.objects.create(
                workflow=workflow,
                node_type="end",
                name="结束",
                position_x=700,
                position_y=100
            )
            node_map["结束"] = end_node
        
        # 创建连线
        for parsed_edge in parsed_workflow.edges:
            if parsed_edge.source in node_map and parsed_edge.target in node_map:
                Edge.objects.create(
                    workflow=workflow,
                    source_node=node_map[parsed_edge.source],
                    target_node=node_map[parsed_edge.target],
                    label=parsed_edge.label
                )
        
        # 连接开始和结束节点到已有节点
        if has_start and not has_end:
            # 找到第一个非开始节点
            first_node = next(
                (n for n in parsed_workflow.nodes if n.node_type.value != "start"),
                None
            )
            if first_node and first_node.name in node_map:
                start_node_obj = Node.objects.filter(
                    workflow=workflow,
                    node_type="start"
                ).first()
                if start_node_obj:
                    Edge.objects.create(
                        workflow=workflow,
                        source_node=start_node_obj,
                        target_node=node_map[first_node.name]
                    )
        
        if has_end and not has_start:
            # 找到最后一个非结束节点
            last_node = next(
                (n for n in reversed(parsed_workflow.nodes) 
                 if n.node_type.value != "end"),
                None
            )
            if last_node and last_node.name in node_map:
                end_node_obj = Node.objects.filter(
                    workflow=workflow,
                    node_type="end"
                ).first()
                if end_node_obj:
                    Edge.objects.create(
                        workflow=workflow,
                        source_node=node_map[last_node.name],
                        target_node=end_node_obj
                    )
        
        return workflow
    
    def convert_to_frontend(self, workflow: Workflow) -> Dict:
        """将数据库工作流转换为前端格式"""
        nodes = []
        edges = []
        
        # 转换节点
        for node in workflow.nodes.all():
            nodes.append({
                "id": str(node.id),
                "type": node.node_type,
                "name": node.name,
                "description": node.description,
                "position_x": node.position_x,
                "position_y": node.position_y,
                "config": node.config,
                "style": node.style or {}
            })
        
        # 转换连线
        for edge in workflow.edges.all():
            edges.append({
                "id": str(edge.id),
                "source": str(edge.source_node_id),
                "target": str(edge.target_node_id),
                "label": edge.label,
                "type": edge.type,
                "animated": edge.animated
            })
        
        return {
            "id": str(workflow.id),
            "name": workflow.name,
            "description": workflow.description,
            "version": workflow.version,
            "status": workflow.status,
            "nodes": nodes,
            "edges": edges
        }
```

### 1.4 API 视图

```python
# Backend/nl_to_workflow/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import StreamingHttpResponse
import json
import asyncio

from .services.parser import NLToWorkflowParser
from .services.validator import WorkflowValidator
from .services.converters import WorkflowConverter


class NLToWorkflowViewSet(viewsets.ViewSet):
    """自然语言生成工作流 ViewSet"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = NLToWorkflowParser()
        self.validator = WorkflowValidator()
        self.converter = WorkflowConverter()
    
    @action(detail=False, methods=['post'])
    def parse(self, request):
        """
        解析自然语言为工作流结构
        POST /api/nl-workflow/parse/
        
        Request Body:
        {
            "text": "创建一个工作流：先让用户输入问题，然后用 GPT-4 回答"
        }
        """
        user_input = request.data.get('text')
        if not user_input:
            return Response(
                {'error': '请提供自然语言描述'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 异步解析
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            parsed_workflow = loop.run_until_complete(self.parser.parse(user_input))
            loop.close()
            
            # 验证
            is_valid, errors = self.validator.validate(parsed_workflow)
            
            # 转换为前端格式
            workflow_data = {
                'name': parsed_workflow.name,
                'description': parsed_workflow.description,
                'nodes': [
                    {
                        'id': f'generated_{i}',
                        'type': node.node_type.value,
                        'name': node.name,
                        'description': node.description,
                        'position_x': node.position[0],
                        'position_y': node.position[1],
                        'config': node.config
                    }
                    for i, node in enumerate(parsed_workflow.nodes)
                ],
                'edges': [
                    {
                        'id': f'edge_{i}',
                        'source': edge.source,
                        'target': edge.target,
                        'label': edge.label
                    }
                    for i, edge in enumerate(parsed_workflow.edges)
                ],
                'explanation': parsed_workflow.explanation
            }
            
            return Response({
                'workflow': workflow_data,
                'is_valid': is_valid,
                'errors': [
                    {'field': e.field, 'message': e.message, 'severity': e.severity}
                    for e in errors
                ]
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def create(self, request):
        """
        根据自然语言描述创建工作流
        POST /api/nl-workflow/create/
        """
        user_input = request.data.get('text')
        if not user_input:
            return Response(
                {'error': '请提供自然语言描述'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 解析
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            parsed_workflow = loop.run_until_complete(self.parser.parse(user_input))
            loop.close()
            
            # 验证
            is_valid, errors = self.validator.validate(parsed_workflow)
            if not is_valid:
                return Response({
                    'error': '生成的工作流验证失败',
                    'errors': [
                        {'field': e.field, 'message': e.message}
                        for e in errors if e.severity == 'error'
                    ]
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 转换并保存
            workflow = self.converter.convert_to_db(parsed_workflow, request.user)
            
            # 返回前端格式
            workflow_data = self.converter.convert_to_frontend(workflow)
            
            return Response({
                'workflow': workflow_data,
                'message': '工作流创建成功'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def refine(self, request):
        """
        优化生成的工作流
        POST /api/nl-workflow/refine/
        
        Request Body:
        {
            "workflow_id": "uuid",
            "feedback": "请添加一个条件判断节点"
        }
        """
        workflow_id = request.data.get('workflow_id')
        feedback = request.data.get('feedback')
        
        if not workflow_id or not feedback:
            return Response(
                {'error': '缺少必要参数'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取现有工作流
        try:
            workflow = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': '工作流不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 获取当前工作流配置
        current_config = self.converter.convert_to_frontend(workflow)
        current_text = self._workflow_to_text(current_config)
        
        # 组合反馈
        combined_input = f"""
当前工作流：
{current_text}

用户反馈：{feedback}
"""
        
        try:
            # 重新解析
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            parsed_workflow = loop.run_until_complete(self.parser.parse(combined_input))
            loop.close()
            
            # 验证
            is_valid, errors = self.validator.validate(parsed_workflow)
            
            # 返回预览
            workflow_data = {
                'name': parsed_workflow.name,
                'description': parsed_workflow.description,
                'nodes': [
                    {
                        'id': f'generated_{i}',
                        'type': node.node_type.value,
                        'name': node.name,
                        'position_x': node.position[0],
                        'position_y': node.position[1],
                        'config': node.config
                    }
                    for i, node in enumerate(parsed_workflow.nodes)
                ],
                'edges': [
                    {
                        'id': f'edge_{i}',
                        'source': edge.source,
                        'target': edge.target
                    }
                    for i, edge in enumerate(parsed_workflow.edges)
                ],
                'explanation': parsed_workflow.explanation
            }
            
            return Response({
                'workflow': workflow_data,
                'is_valid': is_valid,
                'errors': [
                    {'field': e.field, 'message': e.message}
                    for e in errors
                ]
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _workflow_to_text(self, workflow_data: Dict) -> str:
        """将工作流数据转换为文本描述"""
        lines = [f"工作流: {workflow_data['name']}"]
        if workflow_data.get('description'):
            lines.append(f"描述: {workflow_data['description']}")
        
        lines.append("节点:")
        for node in workflow_data.get('nodes', []):
            lines.append(f"  - [{node['type']}] {node['name']}")
        
        lines.append("连线:")
        for edge in workflow_data.get('edges', []):
            lines.append(f"  - {edge['source']} -> {edge['target']}")
        
        return '\n'.join(lines)
```

### 1.5 前端组件

```vue
<!-- Frontend/src/views/nl-workflow/Creator.vue -->

<template>
  <div class="nl-workflow-creator">
    <div class="creator-header">
      <h2>AI 工作流生成器</h2>
      <p class="subtitle">用自然语言描述你的需求，AI 自动生成工作流</p>
    </div>
    
    <div class="creator-content">
      <!-- 左侧：输入区域 -->
      <div class="input-section">
        <div class="input-card">
          <h3>描述你的工作流</h3>
          
          <el-input
            v-model="userInput"
            type="textarea"
            :rows="6"
            :placeholder="placeholderText"
            @keydown.ctrl.enter="handleGenerate"
          />
          
          <div class="input-actions">
            <el-button @click="clearInput">
              <el-icon><Delete /></el-icon>
              清空
            </el-button>
            <el-button 
              type="primary" 
              :loading="isGenerating"
              :disabled="!userInput.trim()"
              @click="handleGenerate"
            >
              <el-icon v-if="!isGenerating"><MagicStick /></el-icon>
              {{ isGenerating ? '生成中...' : '生成工作流' }}
            </el-button>
          </div>
          
          <!-- 示例提示 -->
          <div class="examples">
            <p>示例描述：</p>
            <div class="example-tags">
              <el-tag
                v-for="example in examples"
                :key="example"
                class="example-tag"
                @click="useExample(example)"
              >
                {{ example }}
              </el-tag>
            </div>
          </div>
        </div>
        
        <!-- 生成结果 -->
        <div v-if="generatedWorkflow" class="result-card">
          <div class="result-header">
            <h3>生成结果</h3>
            <el-tag :type="isValid ? 'success' : 'danger'">
              {{ isValid ? '验证通过' : '存在问题' }}
            </el-tag>
          </div>
          
          <!-- 错误提示 -->
          <div v-if="errors.length > 0" class="errors-section">
            <el-alert
              v-for="(error, index) in errors"
              :key="index"
              :title="error.message"
              type="warning"
              show-icon
              :closable="false"
              class="error-item"
            />
          </div>
          
          <!-- 操作按钮 -->
          <div class="result-actions">
            <el-button @click="viewPreview">
              <el-icon><View /></el-icon>
              预览工作流
            </el-button>
            <el-button 
              type="success" 
              :disabled="!isValid"
              @click="handleSave"
            >
              <el-icon><Check /></el-icon>
              保存到工作流
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 右侧：预览区域 -->
      <div class="preview-section">
        <div class="preview-card">
          <h3>工作流预览</h3>
          
          <div v-if="generatedWorkflow" class="workflow-preview">
            <div class="preview-info">
              <h4>{{ generatedWorkflow.name }}</h4>
              <p>{{ generatedWorkflow.description }}</p>
            </div>
            
            <!-- 节点列表 -->
            <div class="preview-nodes">
              <h5>节点 ({{ generatedWorkflow.nodes?.length || 0 }})</h5>
              <div class="node-list">
                <div
                  v-for="node in generatedWorkflow.nodes"
                  :key="node.id"
                  class="preview-node"
                  :class="`node-${node.type}`"
                >
                  <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
                  <span class="node-name">{{ node.name }}</span>
                  <span class="node-type">{{ node.type }}</span>
                </div>
              </div>
            </div>
            
            <!-- 连线列表 -->
            <div class="preview-edges">
              <h5>连线 ({{ generatedWorkflow.edges?.length || 0 }})</h5>
              <div class="edge-list">
                <div
                  v-for="edge in generatedWorkflow.edges"
                  :key="edge.id"
                  class="preview-edge"
                >
                  {{ edge.source }} → {{ edge.target }}
                  <span v-if="edge.label" class="edge-label">{{ edge.label }}</span>
                </div>
              </div>
            </div>
            
            <!-- AI 解释 -->
            <div v-if="generatedWorkflow.explanation" class="preview-explanation">
              <h5>AI 解释</h5>
              <p>{{ generatedWorkflow.explanation }}</p>
            </div>
          </div>
          
          <div v-else class="preview-empty">
            <el-icon class="empty-icon"><Document /></el-icon>
            <p>在这里预览生成的工作流</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="工作流预览"
      width="80%"
      fullscreen
    >
      <div class="full-preview">
        <WorkflowCanvas
          v-if="previewDialogVisible"
          :nodes="canvasNodes"
          :edges="canvasEdges"
          :readonly="true"
        />
      </div>
      <template #footer>
        <el-button @click="previewDialogVisible = false">关闭</el-button>
        <el-button type="success" @click="handleSave">保存工作流</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { nlWorkflowApi } from '@/api/nl-workflow'

const router = useRouter()

// 状态
const userInput = ref('')
const isGenerating = ref(false)
const generatedWorkflow = ref(null)
const isValid = ref(false)
const errors = ref([])
const previewDialogVisible = ref(false)

// 示例
const placeholderText = `例如：创建一个工作流，先让用户输入问题，然后用 GPT-4 回答问题，如果回答包含"错误"就发邮件通知我，否则保存到数据库`

const examples = [
  '简单对话流程',
  '条件分支处理',
  'API 数据获取',
  '多步骤数据处理',
  '带错误处理的工作流'
]

const exampleTexts = {
  '简单对话流程': '创建一个工作流：先让用户输入问题，然后调用 GPT-4 回答问题，最后输出结果',
  '条件分支处理': '创建一个工作流：用户输入一个数字，如果是正数输出"正数"，否则输出"负数"或"零"',
  'API 数据获取': '创建一个工作流：获取用户输入的搜索关键词，调用天气 API 获取数据，然后输出结果',
  '多步骤数据处理': '创建一个工作流：用户上传文件，提取文本内容，总结要点，保存到数据库',
  '带错误处理的工作流': '创建一个工作流：调用外部 API 获取数据，如果失败就发送邮件通知，否则处理数据'
}

// 计算属性
const canvasNodes = computed(() => {
  if (!generatedWorkflow.value) return []
  return generatedWorkflow.value.nodes.map((node, index) => ({
    id: node.id,
    type: node.type,
    data: {
      label: node.name,
      description: node.description,
      config: node.config
    },
    position: {
      x: node.position_x || (100 + (index % 4) * 200),
      y: node.position_y || (100 + Math.floor(index / 4) * 100)
    }
  }))
})

const canvasEdges = computed(() => {
  if (!generatedWorkflow.value) return []
  
  // 转换节点名称到 ID
  const nodeNameToId = {}
  generatedWorkflow.value.nodes.forEach(node => {
    nodeNameToId[node.name] = node.id
  })
  
  return generatedWorkflow.value.edges
    .filter(edge => nodeNameToId[edge.source] && nodeNameToId[edge.target])
    .map(edge => ({
      id: edge.id,
      source: nodeNameToId[edge.source],
      target: nodeNameToId[edge.target],
      label: edge.label,
      animated: true
    }))
})

// 方法
function useExample(example) {
  userInput.value = exampleTexts[example] || example
}

function clearInput() {
  userInput.value = ''
  generatedWorkflow.value = null
  isValid.value = false
  errors.value = []
}

async function handleGenerate() {
  if (!userInput.value.trim()) return
  
  isGenerating.value = true
  errors.value = []
  
  try {
    const response = await nlWorkflowApi.parse({ text: userInput.value })
    
    generatedWorkflow.value = response.workflow
    isValid.value = response.is_valid
    errors.value = response.errors || []
    
    if (response.is_valid) {
      ElMessage.success('工作流生成成功！')
    } else {
      ElMessage.warning('工作流已生成，但存在一些问题')
    }
  } catch (error) {
    ElMessage.error(error.message || '生成失败')
  } finally {
    isGenerating.value = false
  }
}

function viewPreview() {
  previewDialogVisible.value = true
}

async function handleSave() {
  if (!isValid.value) {
    ElMessage.warning('请先修复工作流中的问题')
    return
  }
  
  try {
    const response = await nlWorkflowApi.create({ text: userInput.value })
    ElMessage.success('工作流保存成功！')
    
    // 跳转到工作流编辑器
    router.push(`/workflow/${response.workflow.id}/edit`)
  } catch (error) {
    ElMessage.error(error.message || '保存失败')
  }
}

function getNodeIcon(type) {
  const icons = {
    start: '▶',
    end: '■',
    input: '📝',
    llm: '🤖',
    condition: '🔀',
    tool: '🔧',
    code: '💻',
    http: '🌐',
    email: '📧',
    database: '💾',
    output: '📤'
  }
  return icons[type] || '📦'
}
</script>

<style scoped>
.nl-workflow-creator {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.creator-header {
  text-align: center;
  margin-bottom: 32px;
}

.creator-header h2 {
  font-size: 28px;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 16px;
}

.creator-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.input-card,
.preview-card,
.result-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.result-card {
  margin-top: 16px;
}

.input-card h3,
.preview-card h3,
.result-card h3 {
  margin-bottom: 16px;
  font-size: 18px;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.examples {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.examples p {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.example-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.example-tag {
  cursor: pointer;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.errors-section {
  margin-bottom: 16px;
}

.error-item {
  margin-bottom: 8px;
}

.result-actions {
  display: flex;
  gap: 12px;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.workflow-preview {
  max-height: 600px;
  overflow-y: auto;
}

.preview-info {
  margin-bottom: 20px;
}

.preview-info h4 {
  margin-bottom: 8px;
}

.preview-nodes,
.preview-edges,
.preview-explanation {
  margin-bottom: 20px;
}

.preview-nodes h5,
.preview-edges h5,
.preview-explanation h5 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.node-list,
.edge-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-node {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #f5f7fa;
  border-radius: 8px;
}

.node-icon {
  font-size: 18px;
}

.node-name {
  flex: 1;
  font-weight: 500;
}

.node-type {
  font-size: 12px;
  color: #999;
  background: #e4e7ed;
  padding: 2px 8px;
  border-radius: 4px;
}

.preview-edge {
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  font-size: 14px;
}

.edge-label {
  color: #409eff;
  margin-left: 8px;
}

.full-preview {
  height: calc(100vh - 200px);
}
</style>
```

## 验收标准

- [ ] 自然语言解析功能
- [ ] 工作流结构验证
- [ ] 可视化预览
- [ ] 一键保存到工作流
- [ ] 优化/修改已有工作流
- [ ] 错误处理和提示
- [ ] 单元测试

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `Backend/nl_to_workflow/services/parser.py` | NL 解析器 |
| `Backend/nl_to_workflow/services/validator.py` | 工作流验证器 |
| `Backend/nl_to_workflow/services/converters.py` | 转换器 |
| `Backend/nl_to_workflow/views.py` | API 视图 |
| `Backend/nl_to_workflow/serializers.py` | 序列化器 |
| `Frontend/src/views/nl-workflow/Creator.vue` | 生成器页面 |
| `Frontend/src/api/nl-workflow.js` | NL API 服务 |
