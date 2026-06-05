# Flowly 工作流工具包扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
>
> **用户目标：** 为 Flowly 工作流编辑器构建领域级工具包系统。包括：
> - 模板画廊数据库与 API
> - 垂直领域工作流节点（文生视频、模型训练、RAG、Agent）
> - 开箱即用的完整预置工作流模板
> - 前端模板画廊 UI

---

## 目标

在现有原子节点（llm, http, code 等）之上，构建三层能力：

1. **领域节点** — 高内聚的垂直领域复合节点（如 `video_generation`、`model_training`）
2. **模板系统** — 存储预置工作流模板的数据库和 API
3. **画廊 UI** — 让用户从模板一键创建工作流的界面

---

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vue Flow)               │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ 画廊首页  │  │ 编辑器扩展 │  │ 领域节点组件+表单  │  │
│  └────┬─────┘  └────┬─────┘  └─────────┬─────────┘  │
│       │              │                   │             │
│  ┌────▼──────────────▼───────────────────▼─────────┐   │
│  │     API 层 (workflow.js) + Pinia (marketplace) │   │
│  └────────────────────────┬────────────────────────┘   │
└───────────────────────────┼────────────────────────────┘
                            │ REST API
┌───────────────────────────┼────────────────────────────┐
│                    后端 (Django)                        │
│  ┌────────────────────────▼────────────────────────┐   │
│  │         ViewSet 层 (templates, domain nodes)   │   │
│  └────────────────────────┬────────────────────────┘   │
│  ┌────────────────────────▼────────────────────────┐   │
│  │              Service 层                          │   │
│  │   workflow_executor.py + langchain_service.py   │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Model 层 (新增)                          │   │
│  │  TemplateCategory / WorkflowTemplate             │   │
│  │  WorkflowTemplateNode / WorkflowTemplateEdge     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 新增节点类型清单

### A. 多模态与生成 (Multimodal & Generation)

| node_type | 中文名 | 描述 | 配置字段 |
|-----------|--------|------|----------|
| `image_generation` | 图像生成 | 调用图像生成 API（支持 DALL-E、Stable Diffusion、Flux） | provider, model, prompt, size, quality, style, n |
| `video_generation` | 视频生成 | 文生视频或图生视频 | provider, model, prompt, duration, fps, resolution, input_image |
| `audio_generation` | 音频生成 | TTS 语音合成 | provider, model, text, voice, speed, format |
| `subtitle_generation` | 字幕生成 | 从音频或视频提取/生成字幕 | input_type, language, format |
| `image_editing` | 图像编辑 | 编辑或增强现有图像 | provider, model, image, instruction, mask |

### B. 模型训练 (ML & Training)

| node_type | 中文名 | 描述 | 配置字段 |
|-----------|--------|------|----------|
| `dataset_upload` | 数据集上传 | 上传训练数据集 | source, format, path, validation |
| `data_annotation` | 数据标注 | 标注或预标注数据 | annotation_type, model_assisted, labels |
| `data_augmentation` | 数据增强 | 扩充训练数据 | strategy, transformations, ratio |
| `model_training` | 模型训练 | 训练 ML 模型 | framework, model_type, hyperparameters, epochs, dataset |
| `model_evaluation` | 模型评估 | 评估模型性能 | model_path, metrics, test_dataset, thresholds |
| `model_deployment` | 模型部署 | 部署模型到端点 | platform, endpoint_type, autoscaling |

### C. RAG 与检索 (Retrieval & Knowledge)

| node_type | 中文名 | 描述 | 配置字段 |
|-----------|--------|------|----------|
| `document_loader` | 文档加载 | 从多种格式加载文档 | source_type, path/url, parser, chunk_size, overlap |
| `embedding` | 向量化 | 将文本转为向量 | provider, model, batch_size |
| `vector_store` | 向量存储 | 存储和检索向量 | provider, index_name, metric, top_k |
| `retriever` | 检索器 | 语义检索 | query, top_k, filter, rerank |
| `reranker` | 重排序 | 对检索结果重排序 | model, top_n |

### D. Agent 系统 (Agent)

| node_type | 中文名 | 描述 | 配置字段 |
|-----------|--------|------|----------|
| `agent` | Agent | 自主执行任务的 AI Agent | model, tools, max_iterations, system_prompt |
| `planner` | 任务规划 | 将复杂任务分解为子任务 | model, decomposition_strategy |
| `executor` | 任务执行 | 执行规划的子任务 | context, tool_selection |
| `memory` | 记忆管理 | 管理 Agent 的长期和短期记忆 | memory_type, max_items, ttl |

### E. 数据处理 (Data Pipeline)

| node_type | 中文名 | 描述 | 配置字段 |
|-----------|--------|------|----------|
| `file_reader` | 文件读取 | 读取多种格式文件 | path, format, encoding |
| `file_writer` | 文件写入 | 写入文件 | path, format, content |
| `web_scraper` | 网页爬取 | 爬取网页内容 | url, selector, wait_for |
| `csv_transform` | CSV 转换 | ETL 中的 CSV 处理 | operation, columns, filters |
| `json_transform` | JSON 转换 | JSON 数据转换 | operation, schema, mappings |

---

## 数据库模型变更

### 迁移文件：`workflows/migrations/0008_domain_nodes_and_templates.py`

#### 新增 Model: `TemplateCategory`

```python
class TemplateCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)          # "文生视频"
    slug = models.SlugField(max_length=100, unique=True)  # "video-generation"
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # "lucide-video"
    color = models.CharField(max_length=20, default="#8b5cf6")  # hex color
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 新增 Model: `WorkflowTemplate`

```python
class WorkflowTemplate(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '进阶'),
        ('advanced', '高级'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(TemplateCategory, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    tags = models.JSONField(default=list, blank=True)  # ["AI视频", "自动化", "YOLO"]
    thumbnail_url = models.URLField(max_length=500, blank=True)
    workflow_data = models.JSONField()  # 完整的工作流 JSON（nodes + edges）
    variables_schema = models.JSONField(default=list, blank=True)  # 用户需填写的变量定义
    estimated_duration = models.CharField(max_length=50, blank=True)  # "5-10分钟"
    required_apis = models.JSONField(default=list, blank=True)  # ["openai", "replicate"]
    use_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 实施任务清单

### Task 1: 数据库层 — 创建迁移文件

**Files:**
- Create: `Backend/workflows/migrations/0008_domain_nodes_and_templates.py`
- Modify: `Backend/workflows/models.py` — 添加 `TemplateCategory` 和 `WorkflowTemplate` 模型
- Modify: `Backend/config/constants.py` — 添加所有新 `NodeType` 常量
- Modify: `Backend/workflows/serializers.py` — 添加模板序列化器

**Steps:**

- [ ] **Step 1: 在 `workflows/models.py` 末尾添加两个新 Model**

在文件末尾（`AuditLog` 模型之后）添加：

```python
class TemplateCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=20, default="#8b5cf6")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'template_categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class WorkflowTemplate(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', '入门'),
        ('intermediate', '进阶'),
        ('advanced', '高级'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(TemplateCategory, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    tags = models.JSONField(default=list, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    workflow_data = models.JSONField()  # { nodes: [], edges: [] }
    variables_schema = models.JSONField(default=list, blank=True)
    estimated_duration = models.CharField(max_length=50, blank=True)
    required_apis = models.JSONField(default=list, blank=True)
    use_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workflow_templates'
        ordering = ['-use_count', '-rating']

    def __str__(self):
        return self.name
```

- [ ] **Step 2: 在 `config/constants.py` 的 `NodeType` 类中添加新常量**

在 `NodeType` 类中添加：

```python
# Multimodal & Generation
IMAGE_GENERATION = "image_generation"
VIDEO_GENERATION = "video_generation"
AUDIO_GENERATION = "audio_generation"
SUBTITLE_GENERATION = "subtitle_generation"
IMAGE_EDITING = "image_editing"

# ML & Training
DATASET_UPLOAD = "dataset_upload"
DATA_ANNOTATION = "data_annotation"
DATA_AUGMENTATION = "data_augmentation"
MODEL_TRAINING = "model_training"
MODEL_EVALUATION = "model_evaluation"
MODEL_DEPLOYMENT = "model_deployment"

# RAG & Retrieval
DOCUMENT_LOADER = "document_loader"
EMBEDDING = "embedding"
VECTOR_STORE = "vector_store"
RETRIEVER = "retriever"
RERANKER = "reranker"

# Agent
AGENT = "agent"
PLANNER = "planner"
EXECUTOR = "executor"
MEMORY = "memory"

# Data Pipeline
FILE_READER = "file_reader"
FILE_WRITER = "file_writer"
WEB_SCRAPER_NODE = "web_scraper_node"
CSV_TRANSFORM = "csv_transform"
JSON_TRANSFORM = "json_transform"
```

同时更新 `NODE_TYPE_CHOICES` 列表（动态从 `NodeType` 类属性生成，移除手动列表）。

- [ ] **Step 3: 在 `workflows/serializers.py` 中添加模板序列化器**

在文件末尾添加：

```python
class TemplateCategorySerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color',
                   'sort_order', 'is_active', 'template_count', 'created_at']

    def get_template_count(self, obj):
        return obj.templates.filter(is_active=True).count()


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = ['id', 'category', 'category_name', 'category_slug', 'name',
                   'description', 'difficulty', 'tags', 'thumbnail_url',
                   'estimated_duration', 'required_apis', 'use_count', 'rating',
                   'rating_count', 'is_featured', 'is_verified', 'creator_name',
                   'created_at']


class WorkflowTemplateDetailSerializer(serializers.ModelSerializer):
    category = TemplateCategorySerializer(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = ['id', 'category', 'name', 'description', 'difficulty', 'tags',
                   'thumbnail_url', 'workflow_data', 'variables_schema',
                   'estimated_duration', 'required_apis', 'use_count', 'rating',
                   'rating_count', 'is_featured', 'is_verified', 'version',
                   'creator_name', 'created_at', 'updated_at']


class WorkflowTemplateCreateFromSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    variables = serializers.DictField(required=False, default=dict)
```

- [ ] **Step 4: 在 `workflows/views.py` 中添加模板 ViewSet**

在文件末尾（所有 ViewSet 之后）添加：

```python
class TemplateCategoryViewSet(ReadOnlyModelViewSet):
    queryset = TemplateCategory.objects.filter(is_active=True)
    serializer_class = TemplateCategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class WorkflowTemplateViewSet(ReadOnlyModelViewSet):
    queryset = WorkflowTemplate.objects.filter(is_active=True).select_related('category', 'created_by')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowTemplateListSerializer
        return WorkflowTemplateDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        difficulty = self.request.query_params.get('difficulty')
        featured = self.request.query_params.get('featured')
        search = self.request.query_params.get('search')
        tag = self.request.query_params.get('tag')

        if category:
            queryset = queryset.filter(category__slug=category)
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if featured:
            queryset = queryset.filter(is_featured=True)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset.order_by('-use_count', '-rating')

    @action(detail=True, methods=['post'])
    def create_from_template(self, request, pk=None):
        template = self.get_object()
        serializer = WorkflowTemplateCreateFromSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        workflow_name = data.get('name') or f"{template.name} (副本)"
        variables = data.get('variables', {})

        workflow = Workflow.objects.create(
            name=workflow_name,
            description=template.description,
            owner=request.user,
            tenant=getattr(request.user, 'tenant', None),
        )

        node_id_map = {}
        for node_data in template.workflow_data.get('nodes', []):
            new_node = Node.objects.create(
                workflow=workflow,
                node_type=node_data['type'],
                name=node_data.get('data', {}).get('name', node_data.get('data', {}).get('label', 'Node')),
                description=node_data.get('data', {}).get('description', ''),
                position_x=node_data['position']['x'],
                position_y=node_data['position']['y'],
                config=node_data.get('data', {}).get('config', {}),
            )
            node_id_map[node_data['id']] = str(new_node.id)

        for edge_data in template.workflow_data.get('edges', []):
            Edge.objects.create(
                workflow=workflow,
                source_node_id=node_id_map.get(edge_data['source']),
                source_handle=edge_data.get('sourceHandle', 'default'),
                target_node_id=node_id_map.get(edge_data['target']),
                target_handle=edge_data.get('targetHandle', 'default'),
                label=edge_data.get('label', ''),
            )

        template.use_count += 1
        template.save(update_fields=['use_count'])

        return Response(WorkflowDetailSerializer(workflow).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        queryset = self.get_queryset().filter(is_featured=True)[:6]
        serializer = WorkflowTemplateListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        categories = TemplateCategory.objects.filter(is_active=True).prefetch_related('templates')
        result = []
        for cat in categories:
            templates = cat.templates.filter(is_active=True).order_by('-use_count')[:4]
            result.append({
                'category': TemplateCategorySerializer(cat).data,
                'templates': WorkflowTemplateListSerializer(templates, many=True).data,
            })
        return Response(result)
```

- [ ] **Step 5: 更新 `Backend/config/urls.py` 注册新 URL**

在 workflow urls 中添加：

```python
from workflows.views import TemplateCategoryViewSet, WorkflowTemplateViewSet

router.register(r'template-categories', TemplateCategoryViewSet, basename='template-category')
router.register(r'templates', WorkflowTemplateViewSet, basename='workflow-template')
```

- [ ] **Step 6: 运行迁移**

```bash
cd Backend && python manage.py makemigrations workflows --name domain_nodes_and_templates
python manage.py migrate
```

- [ ] **Step 7: 添加种子数据 — 模板分类**

在 `Backend/workflows/management/commands/seed_templates.py` 创建：

```python
from django.core.management.base import BaseCommand
from workflows.models import TemplateCategory

class Command(BaseCommand):
    def handle(self):
        categories = [
            {"name": "文生视频", "slug": "video-generation", "icon": "Video", "color": "#ec4899", "description": "从文本描述自动生成视频内容"},
            {"name": "AI Agent", "slug": "ai-agent", "icon": "Bot", "color": "#8b5cf6", "description": "自主执行复杂任务的 AI Agent"},
            {"name": "RAG 知识库", "slug": "rag-knowledge", "icon": "BookOpen", "color": "#06b6d4", "description": "基于私有知识库的智能问答"},
            {"name": "模型训练", "slug": "model-training", "icon": "Brain", "color": "#f59e0b", "description": "端到端的机器学习模型训练与部署"},
            {"name": "数据处理", "slug": "data-pipeline", "icon": "Database", "color": "#10b981", "description": "ETL 数据采集、清洗与转换"},
            {"name": "办公自动化", "slug": "office-automation", "icon": "FileText", "color": "#6366f1", "description": "文档处理、邮件自动化等办公场景"},
        ]
        for cat_data in categories:
            obj, created = TemplateCategory.objects.get_or_create(
                slug=cat_data["slug"], defaults=cat_data
            )
            if created:
                self.stdout.write(f"Created category: {obj.name}")
```

运行 `python manage.py seed_templates`

---

### Task 2: 后端 API 层 — 领域节点执行器

**Files:**
- Modify: `Backend/workflows/services/langchain_service.py` — 添加 20 个新节点类型的 handler 方法
- Modify: `Backend/workflows/services/workflow_executor.py` — 调整 `get_next_nodes` 处理新节点类型
- Modify: `Backend/workflows/views.py` — 在 `NodeViewSet.available_types` 中暴露新节点类型

**Steps:**

- [ ] **Step 1: 在 `langchain_service.py` 中添加新 handler 方法**

在 `LangChainService` 类中添加以下方法（每个方法 30-80 行）：

1. `run_image_generation_node(node, context)` — 调用 DALL-E / Stable Diffusion / Flux API，使用 `run_http_node` 模式
2. `run_video_generation_node(node, context)` — 调用 Replicate / Runway / Pika API
3. `run_audio_generation_node(node, context)` — 调用 OpenAI TTS / ElevenLabs API
4. `run_subtitle_generation_node(node, context)` — Whisper API 调用
5. `run_image_editing_node(node, context)` — 调用图像编辑 API

6. `run_dataset_upload_node(node, context)` — 处理文件上传，返回数据集 ID
7. `run_data_annotation_node(node, context)` — 调用标注 API 或模型辅助标注
8. `run_data_augmentation_node(node, context)` — 应用数据增强策略
9. `run_model_training_node(node, context)` — 调用训练 API（支持 PyTorch/TensorFlow 框架）
10. `run_model_evaluation_node(node, context)` — 计算评估指标
11. `run_model_deployment_node(node, context)` — 部署到端点

12. `run_document_loader_node(node, context)` — 加载 PDF/Word/TXT/Markdown，支持 chunk
13. `run_embedding_node(node, context)` — 调用 OpenAI embeddings / HuggingFace
14. `run_vector_store_node(node, context)` — 存储向量到 Pinecone / Chroma / Qdrant
15. `run_retriever_node(node, context)` — 语义检索，组合 embedding + 向量搜索
16. `run_reranker_node(node, context)` — 使用重排序模型优化结果

17. `run_agent_node(node, context)` — Agent 执行循环（参考 LangChain AgentExecutor）
18. `run_planner_node(node, context)` — 任务分解
19. `run_executor_node(node, context)` — 子任务执行
20. `run_memory_node(node, context)` — 记忆读写操作

21. `run_file_reader_node(node, context)` — 文件读取
22. `run_file_writer_node(node, context)` — 文件写入
23. `run_web_scraper_node(node, context)` — 增强版网页爬取（参考现有 tool 中的 scraper）
24. `run_csv_transform_node(node, context)` — CSV 操作
25. `run_json_transform_node(node, context)` — JSON 操作

每个 handler 方法的模板：

```python
def run_image_generation_node(self, node, context):
    """
    Image Generation Node
    Config fields:
        provider: str (openai/dalle, stability, flux)
        model: str
        prompt: str (template)
        size: str (1024x1024, 512x512, etc.)
        quality: str (standard/hd)
        style: str (vivid/natural)
        n: int (1-10)
    """
    config = node.get('config', {})
    provider = config.get('provider', 'openai')
    prompt_template = config.get('prompt', '')
    prompt = self._render_template(prompt_template, context)

    if provider == 'openai':
        # 调用 DALL-E
        return self._call_dalle(prompt, config)
    elif provider == 'stability':
        return self._call_stability(prompt, config)
    elif provider == 'flux':
        return self._call_flux(prompt, config)
    else:
        raise ValueError(f"Unknown image provider: {provider}")
```

- [ ] **Step 2: 更新 `execute_node` 的类型映射**

在 `execute_node` 方法的 node_type 分发字典中添加：

```python
'image_generation': self.run_image_generation_node,
'video_generation': self.run_video_generation_node,
'audio_generation': self.run_audio_generation_node,
'subtitle_generation': self.run_subtitle_generation_node,
'image_editing': self.run_image_editing_node,
'dataset_upload': self.run_dataset_upload_node,
'data_annotation': self.run_data_annotation_node,
'data_augmentation': self.run_data_augmentation_node,
'model_training': self.run_model_training_node,
'model_evaluation': self.run_model_evaluation_node,
'model_deployment': self.run_model_deployment_node,
'document_loader': self.run_document_loader_node,
'embedding': self.run_embedding_node,
'vector_store': self.run_vector_store_node,
'retriever': self.run_retriever_node,
'reranker': self.run_reranker_node,
'agent': self.run_agent_node,
'planner': self.run_planner_node,
'executor': self.run_executor_node,
'memory': self.run_memory_node,
'file_reader': self.run_file_reader_node,
'file_writer': self.run_file_writer_node,
'web_scraper_node': self.run_web_scraper_node,
'csv_transform': self.run_csv_transform_node,
'json_transform': self.run_json_transform_node,
```

- [ ] **Step 3: 更新 `NodeViewSet.available_types` 返回完整节点类型列表**

修改 `available_types` action，返回所有节点类型（包括新增的）：

```python
@action(detail=False, methods=['get'])
def available_types(self, request):
    from config.constants import NodeType
    node_types = []
    for attr in dir(NodeType):
        if not attr.startswith('_') and attr.isupper():
            value = getattr(NodeType, attr)
            node_types.append({'type': value, 'label': attr.replace('_', ' ').title()})
    return Response(node_types)
```

---

### Task 3: 前端节点类型注册

**Files:**
- Modify: `Frontend/src/types/nodes.d.ts` — 添加新节点类型定义和配置接口
- Modify: `Frontend/src/views/workflow/Editor.vue` — 注册新节点类型到 nodeTypes，添加到对应分类

**Steps:**

- [ ] **Step 1: 在 `nodes.d.ts` 中添加新节点类型**

添加 `NodeType` union 类型扩展：

```typescript
type NodeType =
  | 'start' | 'end' | 'llm' | 'prompt' | 'condition'
  | 'tool' | 'input' | 'output' | 'code' | 'loop'
  | 'variable' | 'http' | 'email' | 'webhook' | 'template'
  | 'rag' | 'switch' | 'delay' | 'transform' | 'subworkflow'
  // === 新增：多模态与生成 ===
  | 'image_generation' | 'video_generation' | 'audio_generation'
  | 'subtitle_generation' | 'image_editing'
  // === 新增：模型训练 ===
  | 'dataset_upload' | 'data_annotation' | 'data_augmentation'
  | 'model_training' | 'model_evaluation' | 'model_deployment'
  // === 新增：RAG 与检索 ===
  | 'document_loader' | 'embedding' | 'vector_store'
  | 'retriever' | 'reranker'
  // === 新增：Agent 系统 ===
  | 'agent' | 'planner' | 'executor' | 'memory'
  // === 新增：数据处理 ===
  | 'file_reader' | 'file_writer' | 'web_scraper_node'
  | 'csv_transform' | 'json_transform'
```

添加配置接口：

```typescript
export interface ImageGenerationConfig extends BaseNodeConfig {
  provider: 'openai' | 'stability' | 'flux' | 'replicate'
  model: string
  prompt: string
  size: '1024x1024' | '512x512' | '1792x1024' | '1024x1792'
  quality: 'standard' | 'hd'
  style?: 'vivid' | 'natural'
  n?: number
}

export interface VideoGenerationConfig extends BaseNodeConfig {
  provider: 'runway' | 'pika' | 'replicate' | 'kling'
  model: string
  prompt: string
  duration?: number
  fps?: number
  resolution?: '720p' | '1080p' | '4k'
  inputImage?: string
}

export interface AudioGenerationConfig extends BaseNodeConfig {
  provider: 'openai' | 'elevenlabs' | 'azure'
  model: string
  text: string
  voice?: string
  speed?: number
  format?: 'mp3' | 'wav' | 'ogg'
}

export interface SubtitleGenerationConfig extends BaseNodeConfig {
  inputType: 'audio' | 'video'
  language: string
  format: 'srt' | 'vtt' | 'ass'
}

export interface ImageEditingConfig extends BaseNodeConfig {
  provider: 'openai' | 'stability'
  model: string
  image: string
  instruction: string
  mask?: string
}

// ML & Training
export interface DatasetUploadConfig extends BaseNodeConfig {
  source: 'upload' | 'url' | 's3' | 'database'
  path: string
  format: 'image' | 'video' | 'text' | 'csv' | 'custom'
  validationRules?: Record<string, any>
}

export interface DataAnnotationConfig extends BaseNodeConfig {
  annotationType: 'classification' | 'detection' | 'segmentation' | 'ner'
  labels: string[]
  modelAssisted: boolean
}

export interface DataAugmentationConfig extends BaseNodeConfig {
  strategy: 'geometric' | 'color' | 'noise' | 'mixup' | 'custom'
  transformations: string[]
  ratio: number
}

export interface ModelTrainingConfig extends BaseNodeConfig {
  framework: 'pytorch' | 'tensorflow' | 'transformers' | 'yolo'
  modelType: string
  datasetId?: string
  hyperparameters: {
    epochs?: number
    batchSize?: number
    learningRate?: number
    optimizer?: string
    [key: string]: any
  }
  gpuEnabled: boolean
  checkpointing: boolean
}

export interface ModelEvaluationConfig extends BaseNodeConfig {
  modelPath: string
  testDataset: string
  metrics: string[]
  thresholds?: Record<string, number>
}

export interface ModelDeploymentConfig extends BaseNodeConfig {
  platform: 'sagemaker' | 'lambdagpu' | 'triton' | 'local'
  endpointType: 'realtime' | 'batch' | 'serverless'
  autoscaling: boolean
  minInstances?: number
  maxInstances?: number
}

// RAG
export interface DocumentLoaderConfig extends BaseNodeConfig {
  sourceType: 'file' | 'url' | 's3' | 'notion' | 'confluence' | 'web'
  path: string
  parser: 'pdf' | 'docx' | 'txt' | 'markdown' | 'html'
  chunkSize: number
  chunkOverlap: number
}

export interface EmbeddingConfig extends BaseNodeConfig {
  provider: 'openai' | 'huggingface' | 'cohere' | 'ollama'
  model: string
  batchSize?: number
}

export interface VectorStoreConfig extends BaseNodeConfig {
  provider: 'pinecone' | 'chroma' | 'qdrant' | 'weaviate' | 'milvus'
  indexName: string
  metric: 'cosine' | 'euclidean' | 'dotproduct'
  dimension?: number
}

export interface RetrieverConfig extends BaseNodeConfig {
  query: string
  topK: number
  filter?: Record<string, any>
  enableRerank: boolean
}

export interface RerankerConfig extends BaseNodeConfig {
  model: string
  topN: number
}

// Agent
export interface AgentNodeConfig extends BaseNodeConfig {
  model: string
  tools: string[]
  maxIterations: number
  systemPrompt: string
  memoryEnabled: boolean
}

export interface PlannerConfig extends BaseNodeConfig {
  model: string
  decompositionStrategy: 'sequential' | 'parallel' | 'hierarchical'
  maxSubtasks?: number
}

export interface ExecutorConfig extends BaseNodeConfig {
  toolSelection: 'auto' | 'forced'
  contextWindow?: number
}

export interface MemoryConfig extends BaseNodeConfig {
  memoryType: 'buffer' | 'summary' | 'entity' | 'graph'
  maxItems: number
  ttl?: number
}

// Data Pipeline
export interface FileReaderConfig extends BaseNodeConfig {
  path: string
  format: 'csv' | 'json' | 'txt' | 'parquet' | 'excel'
  encoding?: string
}

export interface FileWriterConfig extends BaseNodeConfig {
  path: string
  format: 'csv' | 'json' | 'txt' | 'parquet' | 'excel'
  overwrite: boolean
}

export interface WebScraperConfig extends BaseNodeConfig {
  url: string
  selectors: { name: string; selector: string }[]
  waitFor?: string
}

export interface CsvTransformConfig extends BaseNodeConfig {
  operation: 'filter' | 'aggregate' | 'join' | 'pivot' | 'melt'
  params: Record<string, any>
}

export interface JsonTransformConfig extends BaseNodeConfig {
  operation: 'map' | 'filter' | 'reduce' | 'flatten' | 'merge'
  schema: Record<string, any>
}
```

- [ ] **Step 2: 在 `Editor.vue` 中更新 nodeTypes 和分类**

在 `nodeTypes` 对象中添加所有新节点类型导入和注册：

```javascript
import ImageGenerationNode from '@/components/workflow/nodes/ImageGenerationNode.vue'
import VideoGenerationNode from '@/components/workflow/nodes/VideoGenerationNode.vue'
import AudioGenerationNode from '@/components/workflow/nodes/AudioGenerationNode.vue'
// ... 其他节点导入

const nodeTypes = {
  // ... 现有节点
  image_generation: ImageGenerationNode,
  video_generation: VideoGenerationNode,
  audio_generation: AudioGenerationNode,
  // ... 其他节点
}
```

更新 `nodeCategories` 数组，添加新的分类：

```javascript
const nodeCategories = [
  // ... 现有分类
  {
    label: '多模态生成',
    icon: 'Sparkles',
    color: 'bg-pink-500',
    nodes: ['image_generation', 'video_generation', 'audio_generation', 'subtitle_generation', 'image_editing'],
  },
  {
    label: '模型训练',
    icon: 'Brain',
    color: 'bg-amber-500',
    nodes: ['dataset_upload', 'data_annotation', 'data_augmentation', 'model_training', 'model_evaluation', 'model_deployment'],
  },
  {
    label: 'RAG 检索',
    icon: 'BookOpen',
    color: 'bg-cyan-500',
    nodes: ['document_loader', 'embedding', 'vector_store', 'retriever', 'reranker'],
  },
  {
    label: 'Agent',
    icon: 'Bot',
    color: 'bg-violet-500',
    nodes: ['agent', 'planner', 'executor', 'memory'],
  },
  {
    label: '数据处理',
    icon: 'Database',
    color: 'bg-emerald-500',
    nodes: ['file_reader', 'file_writer', 'web_scraper_node', 'csv_transform', 'json_transform'],
  },
]
```

---

### Task 4: 前端节点组件

**Files:**
- Create: `Frontend/src/components/workflow/nodes/ImageGenerationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/VideoGenerationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/AudioGenerationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/SubtitleGenerationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/ImageEditingNode.vue`
- Create: `Frontend/src/components/workflow/nodes/DatasetUploadNode.vue`
- Create: `Frontend/src/components/workflow/nodes/DataAnnotationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/DataAugmentationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/ModelTrainingNode.vue`
- Create: `Frontend/src/components/workflow/nodes/ModelEvaluationNode.vue`
- Create: `Frontend/src/components/workflow/nodes/ModelDeploymentNode.vue`
- Create: `Frontend/src/components/workflow/nodes/DocumentLoaderNode.vue`
- Create: `Frontend/src/components/workflow/nodes/EmbeddingNode.vue`
- Create: `Frontend/src/components/workflow/nodes/VectorStoreNode.vue`
- Create: `Frontend/src/components/workflow/nodes/RetrieverNode.vue`
- Create: `Frontend/src/components/workflow/nodes/RerankerNode.vue`
- Create: `Frontend/src/components/workflow/nodes/AgentNode.vue`
- Create: `Frontend/src/components/workflow/nodes/PlannerNode.vue`
- Create: `Frontend/src/components/workflow/nodes/ExecutorNode.vue`
- Create: `Frontend/src/components/workflow/nodes/MemoryNode.vue`
- Create: `Frontend/src/components/workflow/nodes/FileReaderNode.vue`
- Create: `Frontend/src/components/workflow/nodes/FileWriterNode.vue`
- Create: `Frontend/src/components/workflow/nodes/WebScraperNode.vue`
- Create: `Frontend/src/components/workflow/nodes/CsvTransformNode.vue`
- Create: `Frontend/src/components/workflow/nodes/JsonTransformNode.vue`

**每个节点组件的结构模板：**

```vue
<template>
  <div class="domain-node" @click="$emit('node-click', $event)">
    <Handle type="target" :position="Position.Left" />
    <div class="node-content" :style="{ borderColor: nodeColor }">
      <div class="node-header" :style="{ backgroundColor: nodeColor }">
        <component :is="iconComponent" :size="14" class="node-icon" />
        <span class="node-label">{{ config.label || name }}</span>
      </div>
      <div class="node-body">
        <div class="node-info">
          <span class="node-model">{{ config.model || config.provider || '-' }}</span>
          <span v-if="config.prompt || config.text" class="node-preview">
            {{ truncate(config.prompt || config.text, 40) }}
          </span>
        </div>
      </div>
    </div>
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Sparkles, Video, Volume2, Image, Upload, Tags, Layers,
         Brain, CheckCircle, Rocket, FileText, Hash, Database,
         Search, Bot, ListTodo, Cog, MemoryStick,
         FileInput, FileOutput, Globe, Table, Braces } from 'lucide-vue-next'

const props = defineProps({
  id: String,
  type: String,
  data: Object,
  selected: Boolean,
})

defineEmits(['node-click'])

const config = computed(() => props.data?.config || {})
const name = computed(() => props.data?.name || '节点')
const nodeColor = computed(() => {
  const colors = {
    image_generation: '#ec4899',
    video_generation: '#ec4899',
    audio_generation: '#d946ef',
    subtitle_generation: '#d946ef',
    image_editing: '#ec4899',
    dataset_upload: '#f59e0b',
    data_annotation: '#f59e0b',
    data_augmentation: '#f59e0b',
    model_training: '#f59e0b',
    model_evaluation: '#f59e0b',
    model_deployment: '#f59e0b',
    document_loader: '#06b6d4',
    embedding: '#06b6d4',
    vector_store: '#06b6d4',
    retriever: '#06b6d4',
    reranker: '#06b6d4',
    agent: '#8b5cf6',
    planner: '#8b5cf6',
    executor: '#8b5cf6',
    memory: '#8b5cf6',
    file_reader: '#10b981',
    file_writer: '#10b981',
    web_scraper_node: '#10b981',
    csv_transform: '#10b981',
    json_transform: '#10b981',
  }
  return colors[props.type] || '#6366f1'
})

const iconComponent = computed(() => {
  const icons = {
    image_generation: Sparkles,
    video_generation: Video,
    audio_generation: Volume2,
    subtitle_generation: Image,
    image_editing: Image,
    dataset_upload: Upload,
    data_annotation: Tags,
    data_augmentation: Layers,
    model_training: Brain,
    model_evaluation: CheckCircle,
    model_deployment: Rocket,
    document_loader: FileText,
    embedding: Hash,
    vector_store: Database,
    retriever: Search,
    reranker: Layers,
    agent: Bot,
    planner: ListTodo,
    executor: Cog,
    memory: MemoryStick,
    file_reader: FileInput,
    file_writer: FileOutput,
    web_scraper_node: Globe,
    csv_transform: Table,
    json_transform: Braces,
  }
  return icons[props.type] || Sparkles
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}
</script>

<style scoped>
.domain-node { /* 同现有节点样式 */ }
</style>
```

---

### Task 5: 前端节点配置表单

**Files:**
- Create: `Frontend/src/components/workflow/config-forms/ImageGenerationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/VideoGenerationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/AudioGenerationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/SubtitleGenerationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/ImageEditingConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/DatasetUploadConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/DataAnnotationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/DataAugmentationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/ModelTrainingConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/ModelEvaluationConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/ModelDeploymentConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/DocumentLoaderConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/EmbeddingConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/VectorStoreConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/RetrieverConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/RerankerConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/AgentNodeConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/PlannerConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/ExecutorConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/MemoryConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/FileReaderConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/FileWriterConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/WebScraperConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/CsvTransformConfigForm.vue`
- Create: `Frontend/src/components/workflow/config-forms/JsonTransformConfigForm.vue`
- Modify: `Frontend/src/components/workflow/NodeConfigForm.vue` — 注册所有新配置表单
- Modify: `Frontend/src/components/workflow/PropertyPanel.vue` — 添加新分类的节点配置面板支持

**每个配置表单的通用模板（以 ImageGenerationConfigForm 为例）：**

```vue
<template>
  <div class="config-form">
    <div class="form-section">
      <h4>模型配置</h4>
      <el-form-item label="服务商">
        <el-select v-model="localConfig.provider" @change="onProviderChange">
          <el-option label="OpenAI DALL-E" value="openai" />
          <el-option label="Stability AI" value="stability" />
          <el-option label="Flux" value="flux" />
          <el-option label="Replicate" value="replicate" />
        </el-select>
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="localConfig.model" filterable allow-create>
          <el-option v-for="m in availableModels" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item label="尺寸">
        <el-select v-model="localConfig.size">
          <el-option label="1024x1024" value="1024x1024" />
          <el-option label="512x512" value="512x512" />
          <el-option label="1792x1024 (横版)" value="1792x1024" />
          <el-option label="1024x1792 (竖版)" value="1024x1792" />
        </el-select>
      </el-form-item>
      <el-form-item label="质量">
        <el-radio-group v-model="localConfig.quality">
          <el-radio label="standard">标准</el-radio>
          <el-radio label="hd">高清</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="数量">
        <el-input-number v-model="localConfig.n" :min="1" :max="10" />
      </el-form-item>
    </div>

    <div class="form-section">
      <h4>提示词</h4>
      <el-form-item label="图像描述">
        <el-input
          v-model="localConfig.prompt"
          type="textarea"
          :rows="4"
          placeholder="描述你想要生成的图像，支持 {{variable}} 变量"
        />
      </el-form-item>
      <div class="variable-hint">
        可用变量: {{ availableVariables.join(', ') }}
      </div>
    </div>

    <div class="form-section">
      <h4>输出</h4>
      <div class="preview-box">
        <div class="preview-label">输出格式</div>
        <div class="preview-value">image_url (string)</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({ nodeData: Object })
const emit = defineEmits(['update'])

const localConfig = ref({
  provider: 'openai',
  model: 'dall-e-3',
  prompt: '',
  size: '1024x1024',
  quality: 'standard',
  n: 1,
  ...props.nodeData?.config,
})

const providerModels = {
  openai: ['dall-e-3', 'dall-e-2'],
  stability: ['stable-diffusion-xl-1024-v1-0', 'stable-diffusion-v1-6'],
  flux: ['flux-pro', 'flux-dev', 'flux-schnell'],
  replicate: ['stability-ai/sdxl', 'black-forest-labs/flux-schnell'],
}

const availableModels = computed(() => providerModels[localConfig.value.provider] || [])

function onProviderChange(provider) {
  localConfig.value.model = providerModels[provider]?.[0] || ''
}

watch(localConfig, (val) => {
  emit('update', { config: val })
}, { deep: true })
</script>

<style scoped>
.config-form { /* 同现有表单样式 */ }
</style>
```

---

### Task 6: 前端 API 层

**Files:**
- Modify: `Frontend/src/api/workflow.js` — 添加模板相关 API 函数
- Create: `Frontend/src/stores/marketplace.js` — 模板画廊 Pinia store

**Steps:**

- [ ] **Step 1: 在 `workflow.js` 中添加模板 API**

```javascript
// 模板画廊
export const getTemplateCategories = (params) => request.get('/template-categories/', { params })
export const getTemplateCategory = (id) => request.get(`/template-categories/${id}/`)
export const getWorkflowTemplates = (params) => request.get('/templates/', { params })
export const getTemplate = (id) => request.get(`/templates/${id}/`)
export const createFromTemplate = (id, data) => request.post(`/templates/${id}/create_from_template/`, data)
export const getFeaturedTemplates = () => request.get('/templates/featured/')
export const getTemplatesByCategory = () => request.get('/templates/by_category/')

// 领域节点元数据
export const getDomainNodeTypes = () => request.get('/nodes/available_types/')
```

- [ ] **Step 2: 创建 `marketplace.js` store**

```javascript
import { defineStore } from 'pinia'
import {
  getTemplateCategories,
  getWorkflowTemplates,
  getTemplate,
  createFromTemplate,
  getFeaturedTemplates,
  getTemplatesByCategory,
} from '@/api/workflow'

export const useMarketplaceStore = defineStore('marketplace', {
  state: () => ({
    categories: [],
    templates: [],
    featuredTemplates: [],
    categoryTemplates: [],
    currentTemplate: null,
    loading: false,
    filters: {
      category: '',
      difficulty: '',
      search: '',
      tag: '',
    },
  }),
  actions: {
    async fetchCategories() { /* 实现 */ },
    async fetchTemplates(params = {}) { /* 实现 */ },
    async fetchFeatured() { /* 实现 */ },
    async fetchByCategory() { /* 实现 */ },
    async applyTemplate(templateId, data = {}) {
      const workflow = await createFromTemplate(templateId, data)
      return workflow
    },
  },
})
```

---

### Task 7: 预置模板数据

**Files:**
- Create: `Backend/workflows/management/commands/seed_workflow_templates.py`
- Create: `Frontend/src/data/default-templates.json` — 前端备份

**Steps:**

- [ ] **Step 1: 创建 6 个完整预置模板的种子数据命令**

每个模板是一个完整工作流 JSON（nodes + edges），包含真实可运行的节点配置：

**模板 1: "AI 短视频自动生成" (video-generation)**
```
[文本输入] → [主题理解(LLM)] → [分镜规划(Code)] → [画面生成(Image Gen)]
→ [音频合成(TTS)] → [视频合成(Video Gen)] → [字幕生成] → [结束]
```

**模板 2: "智能客服 RAG 机器人" (rag-knowledge)**
```
[用户问题] → [向量检索(Retriever)] → [上下文组装(Prompt)]
→ [LLM回答] → [生成工单?] → [结束]
```

**模板 3: "YOLO 目标检测模型训练" (model-training)**
```
[数据集上传] → [数据标注] → [数据增强] → [模型训练]
→ [模型评估] → [导出模型] → [部署端点] → [结束]
```

**模板 4: "多模态内容分析" (ai-agent)**
```
[图片+文本输入] → [Agent(规划)] → [子任务:图像分析]
→ [子任务:网页搜索] → [子任务:文本总结] → [结果汇总] → [结束]
```

**模板 5: "竞品数据采集 ETL" (data-pipeline)**
```
[定时触发] → [网页爬取(循环)] → [数据清洗(Code)]
→ [格式转换(JSON)] → [存储到DB] → [结束]
```

**模板 6: "自动化邮件报告" (office-automation)**
```
[定时触发] → [数据查询(HTTP)] → [生成图表(Code)]
→ [渲染报告(Prompt)] → [发送邮件] → [结束]
```

- [ ] **Step 2: 运行种子命令**

```bash
python manage.py seed_workflow_templates
```

---

### Task 8: 前端模板画廊 UI

**Files:**
- Create: `Frontend/src/views/workflow/TemplateGallery.vue` — 模板画廊首页
- Create: `Frontend/src/views/workflow/TemplateDetail.vue` — 模板详情页
- Create: `Frontend/src/views/workflow/TemplateApply.vue` — 模板应用弹窗
- Modify: `Frontend/src/router/routes.js` — 添加画廊路由
- Modify: `Frontend/src/components/layout/Sidebar.vue` — 添加"模板市场"入口

**TemplateGallery.vue 的结构：**

```vue
<template>
  <div class="template-gallery">
    <!-- 顶部 Hero -->
    <div class="gallery-hero">
      <h1>工作流模板市场</h1>
      <p>从预置模板快速创建完整工作流</p>
      <div class="search-bar">
        <el-input v-model="search" placeholder="搜索模板..." prefix-icon="Search" size="large" />
      </div>
    </div>

    <!-- 特色模板轮播 -->
    <section v-if="featuredTemplates.length" class="featured-section">
      <h2>精选模板</h2>
      <div class="featured-grid">
        <TemplateCard v-for="t in featuredTemplates" :key="t.id" :template="t" @use="handleUse" />
      </div>
    </section>

    <!-- 分类浏览 -->
    <section v-for="catGroup in categoryTemplates" :key="catGroup.category.id" class="category-section">
      <div class="category-header">
        <component :is="getCategoryIcon(catGroup.category.icon)" :size="24" />
        <h2>{{ catGroup.category.name }}</h2>
        <span class="category-desc">{{ catGroup.category.description }}</span>
        <el-button text @click="$router.push(`/templates?category=${catGroup.category.slug}`)">
          查看全部 →
        </el-button>
      </div>
      <div class="template-grid">
        <TemplateCard
          v-for="t in catGroup.templates"
          :key="t.id"
          :template="t"
          @click="openDetail(t)"
        />
      </div>
    </section>
  </div>
</template>
```

**TemplateDetail.vue 的结构：**

```vue
<template>
  <div class="template-detail" v-if="template">
    <!-- 左侧: 预览 -->
    <div class="preview-panel">
      <VueFlow v-if="workflowData" :nodes="workflowData.nodes" :edges="workflowData.edges" :node-types="nodeTypes" disabled />
      <div class="template-meta">
        <el-tag>{{ getDifficultyLabel(template.difficulty) }}</el-tag>
        <el-tag v-for="tag in template.tags" :key="tag">{{ tag }}</el-tag>
        <span>使用 {{ template.use_count }} 次</span>
        <span>⭐ {{ template.rating.toFixed(1) }}</span>
      </div>
    </div>

    <!-- 右侧: 信息 + 操作 -->
    <div class="info-panel">
      <h1>{{ template.name }}</h1>
      <p>{{ template.description }}</p>
      <div class="required-apis">
        <h3>需要的 API</h3>
        <el-tag v-for="api in template.required_apis" :key="api">{{ api }}</el-tag>
      </div>
      <div class="variables-form" v-if="template.variables_schema.length">
        <h3>配置参数</h3>
        <el-form>
          <el-form-item v-for="v in template.variables_schema" :key="v.name" :label="v.label">
            <el-input v-model="variables[v.name]" :placeholder="v.placeholder" />
          </el-form-item>
        </el-form>
      </div>
      <el-button type="primary" size="large" @click="applyTemplate">使用此模板创建</el-button>
    </div>
  </div>
</template>
```

---

### Task 9: 端到端验证

**Steps:**

- [ ] **Step 1: 验证数据库迁移**

```bash
cd Backend && python manage.py migrate --check
python manage.py migrate
python manage.py seed_templates
python manage.py seed_workflow_templates
```

- [ ] **Step 2: 验证 API 端点**

测试以下端点返回正确数据：
- `GET /api/v1/template-categories/` → 6 个分类
- `GET /api/v1/templates/` → 6 个模板
- `GET /api/v1/templates/featured/` → 特色模板
- `POST /api/v1/templates/{id}/create_from_template/` → 创建工作流

- [ ] **Step 3: 验证前端**

- 打开编辑器，新分类出现在左侧节点面板
- 点击画廊入口，能看到模板列表
- 从模板创建工作流后，编辑器中加载正确节点

- [ ] **Step 4: 验证执行**

- 创建包含新节点的工作流
- 执行工作流，验证后端能正确路由到 handler
- 检查 NodeExecution 记录中 token usage / cost 正确

---

## 任务依赖关系

```
Task 1 (数据库迁移) ──────┐
                          ├─► Task 2 (后端执行器) ──┐
Task 6 (前端 API) ────────┤                        │
                          │                        ├─► Task 9 (端到端验证)
Task 3 (前端节点类型) ───┤                        │
                          ├─► Task 4 (节点组件) ──┤
Task 5 (配置表单) ────────┘                        │
                          │                        │
Task 7 (预置模板) ────────┴─► Task 8 (画廊 UI) ──┘
```

---

## 自查清单

- [ ] 数据库迁移成功，6 个分类和 6 个模板已创建
- [ ] 所有 25 个新节点类型已注册到前端和后端
- [ ] 每个节点类型有对应的 Vue 组件
- [ ] 每个节点类型有对应的配置表单
- [ ] 后端 executor 正确路由到每个新 handler
- [ ] 模板画廊 UI 可浏览和搜索
- [ ] 从模板创建工作流功能正常
- [ ] 包含新节点的工作流可正常执行
