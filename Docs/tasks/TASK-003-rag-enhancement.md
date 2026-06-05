# 任务 3：RAG 增强功能开发

## 任务概述

| 属性 | 值 |
|------|-----|
| **任务名称** | RAG（检索增强生成）功能开发 |
| **优先级** | P1 - 重要功能 |
| **预估工时** | 5-7 天 |
| **前置依赖** | 工作流执行引擎、向量数据库 |

## 任务目标

实现完整的 RAG 功能，支持：
- 文档上传和解析
- 文本分块和向量化
- 向量检索
- 与工作流集成

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          RAG 架构图                                  │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │  用户上传    │         │  文档解析    │         │  文本分块   │
    │  (多格式)    │ ──────▶ │  (PDF/Word/ │ ──────▶ │  (Chunking) │
    │              │         │   TXT/HTML) │         │              │
    └──────────────┘         └──────────────┘         └──────┬───────┘
                                                               │
                                                               ▼
    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │  检索结果    │         │  上下文组装  │         │  向量化存储  │
    │  (Results)  │ ◀────── │  (Context)  │ ◀────── │  (Qdrant/    │
    │              │         │              │         │   Milvus)    │
    └──────────────┘         └──────────────┘         └──────────────┘
           │
           ▼
    ┌──────────────┐
    │  LLM 生成    │
    │  (Response)  │
    └──────────────┘
```

## 详细需求

### 1.1 文档上传与解析

#### 1.1.1 支持的文档格式

| 格式 | 解析方式 | 库/工具 |
|------|---------|---------|
| PDF | 文本提取 | PyPDF2, pdfplumber |
| Word (.docx) | XML 解析 | python-docx |
| PPT (.pptx) | XML 解析 | python-pptx |
| Excel (.xlsx) | openpyxl | openpyxl |
| TXT | 直接读取 | 内置 |
| Markdown | 直接读取 | 内置 |
| HTML | BeautifulSoup | beautifulsoup4 |
| URL | 网页抓取 | requests, bs4 |
| CSV | pandas | pandas |

#### 1.1.2 文档解析服务

```python
# Backend/rag/services/document_parser.py

class DocumentParser:
    """文档解析器"""
    
    PARSERS = {
        'pdf': PDFParser,
        'docx': DOCXParser,
        'pptx': PPTXParser,
        'xlsx': XLSXParser,
        'txt': TXTParser,
        'md': MarkdownParser,
        'html': HTMLParser,
        'url': URLParser,
        'csv': CSVParser,
    }
    
    @classmethod
    def parse(cls, file_path: str, metadata: dict = None) -> Document:
        """解析文档"""
        ext = Path(file_path).suffix.lower().lstrip('.')
        
        parser_class = cls.PARSERS.get(ext)
        if not parser_class:
            raise ValueError(f"不支持的文件格式: {ext}")
        
        parser = parser_class()
        content = parser.extract_text(file_path)
        metadata = parser.extract_metadata(file_path, metadata or {})
        
        return Document(
            content=content,
            metadata=metadata,
            source=file_path
        )
```

#### 1.1.3 文档解析 API

```python
# Backend/rag/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, KnowledgeBase, Chunk
from .serializers import DocumentSerializer, KnowledgeBaseSerializer
from .services import DocumentParser, EmbeddingService, VectorStoreService

class DocumentUploadViewSet(viewsets.ModelViewSet):
    """文档上传 ViewSet"""
    
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = DocumentSerializer
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """上传并解析文档"""
        file = request.FILES.get('file')
        knowledge_base_id = request.data.get('knowledge_base_id')
        
        if not file:
            return Response(
                {'error': '请上传文件'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 保存文件
        file_path = self._save_file(file)
        
        # 解析文档
        try:
            document = DocumentParser.parse(file_path, {
                'filename': file.name,
                'size': file.size,
                'knowledge_base_id': knowledge_base_id
            })
            
            # 触发异步处理任务
            from .tasks import process_document_task
            process_document_task.delay(str(document.id))
            
            return Response({
                'id': str(document.id),
                'status': 'processing',
                'message': '文档已上传，正在处理中'
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _save_file(self, file):
        """保存上传的文件"""
        import os
        from django.conf import settings
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_{file.name}")
        with open(file_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)
        
        return file_path
```

### 1.2 文本分块 (Chunking)

#### 1.2.1 分块策略

```python
# Backend/rag/services/chunker.py

class TextChunker:
    """文本分块器"""
    
    STRATEGIES = {
        'fixed': FixedSizeChunker,
        'recursive': RecursiveChunker,
        'semantic': SemanticChunker,
        'document': DocumentChunker,
    }
    
    @classmethod
    def chunk(cls, text: str, strategy: str = 'recursive', **kwargs):
        """分块"""
        chunker_class = cls.STRATEGIES.get(strategy, RecursiveChunker)
        chunker = chunker_class(**kwargs)
        return chunker.chunk(text)


class RecursiveChunker:
    """递归字符分块"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str) -> List[Chunk]:
        """分块"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            # 尝试在句子边界断开
            if end < len(text):
                last_period = chunk_text.rfind('。')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(Chunk(
                content=chunk_text.strip(),
                start_char=start,
                end_char=end,
                index=len(chunks)
            ))
            
            start = end - self.overlap
        
        return chunks


class SemanticChunker:
    """语义分块 - 基于句子相似度"""
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
    
    def chunk(self, text: str) -> List[Chunk]:
        """语义分块"""
        sentences = self._split_sentences(text)
        embeddings = self._get_embeddings(sentences)
        
        chunks = []
        current_chunk = [sentences[0]]
        current_embedding = embeddings[0]
        
        for i in range(1, len(sentences)):
            similarity = self._cosine_similarity(current_embedding, embeddings[i])
            
            if similarity >= self.similarity_threshold:
                current_chunk.append(sentences[i])
                current_embedding = (current_embedding * (len(current_chunk) - 1) + embeddings[i]) / len(current_chunk)
            else:
                # 保存当前块
                chunks.append(Chunk(
                    content=''.join(current_chunk),
                    sentences=current_chunk.copy()
                ))
                # 开始新块
                current_chunk = [sentences[i]]
                current_embedding = embeddings[i]
        
        # 保存最后一块
        if current_chunk:
            chunks.append(Chunk(
                content=''.join(current_chunk),
                sentences=current_chunk
            ))
        
        return chunks
```

#### 1.2.2 分块配置

```python
# 分块配置模型
class ChunkConfig(models.Model):
    """分块配置"""
    
    KNOWLEDGE_BASE_TYPES = [
        ('qdrant', 'Qdrant'),
        ('milvus', 'Milvus'),
        ('chroma', 'Chroma'),
        ('pgvector', 'PostgreSQL + pgvector'),
        ('pinecone', 'Pinecone'),
    ]
    
    CHUNK_STRATEGIES = [
        ('fixed', '固定大小'),
        ('recursive', '递归字符'),
        ('semantic', '语义分块'),
        ('document', '按文档结构'),
    ]
    
    EMBEDDING_PROVIDERS = [
        ('openai', 'OpenAI'),
        ('azure', 'Azure OpenAI'),
        ('huggingface', 'HuggingFace'),
        ('local', '本地模型'),
    ]
    
    name = models.CharField(max_length=100)
    knowledge_base = models.ForeignKey('KnowledgeBase', on_delete=models.CASCADE)
    
    # 分块配置
    chunk_strategy = models.CharField(
        max_length=20,
        choices=CHUNK_STRATEGIES,
        default='recursive'
    )
    chunk_size = models.IntegerField(default=500, help_text='每块字符数')
    chunk_overlap = models.IntegerField(default=50, help_text='块重叠字符数')
    
    # 向量化配置
    embedding_provider = models.CharField(
        max_length=20,
        choices=EMBEDDING_PROVIDERS,
        default='openai'
    )
    embedding_model = models.CharField(max_length=100)
    embedding_dimension = models.IntegerField(default=1536)
    
    # 检索配置
    top_k = models.IntegerField(default=5)
    min_similarity = models.FloatField(default=0.5)
    enable_rerank = models.BooleanField(default=False)
```

### 1.3 向量化与存储

#### 1.3.1 嵌入服务

```python
# Backend/rag/services/embedding.py

class EmbeddingService:
    """嵌入服务"""
    
    PROVIDERS = {
        'openai': OpenAIEmbedding,
        'azure': AzureOpenAIEmbedding,
        'huggingface': HuggingFaceEmbedding,
        'local': LocalEmbedding,
    }
    
    def __init__(self, provider: str = 'openai', model: str = None):
        self.provider = self.PROVIDERS[provider](model)
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        return self.provider.embed(texts)
    
    def embed_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """批量生成嵌入向量"""
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.embed(batch)
            all_embeddings.extend(embeddings)
        
        return all_embeddings


class OpenAIEmbedding:
    """OpenAI 嵌入"""
    
    def __init__(self, model: str = 'text-embedding-ada-002'):
        self.model = model
        self.client = OpenAI()
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]


class HuggingFaceEmbedding:
    """HuggingFace 本地嵌入"""
    
    def __init__(self, model: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model)
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """生成嵌入向量"""
        return self.model.encode(texts).tolist()
```

#### 1.3.2 向量存储服务

```python
# Backend/rag/services/vector_store.py

class VectorStoreService:
    """向量存储服务"""
    
    def __init__(self, store_type: str, config: dict):
        self.store_type = store_type
        self.config = config
        self.client = self._get_client()
    
    def _get_client(self):
        """获取向量存储客户端"""
        clients = {
            'qdrant': QdrantClient,
            'milvus': MilvusClient,
            'chroma': ChromaClient,
            'pgvector': PGVectorClient,
            'pinecone': PineconeClient,
        }
        client_class = clients.get(self.store_type)
        if not client_class:
            raise ValueError(f"不支持的向量存储: {self.store_type}")
        return client_class(**self.config)
    
    def upsert(self, collection_name: str, vectors: List[dict]):
        """插入或更新向量"""
        self.client.upsert(collection_name, vectors)
    
    def search(self, collection_name: str, query_vector: List[float], 
               top_k: int = 5, filter: dict = None) -> List[dict]:
        """向量检索"""
        return self.client.search(
            collection_name,
            query_vector,
            top_k=top_k,
            filter=filter
        )
    
    def delete(self, collection_name: str, ids: List[str]):
        """删除向量"""
        self.client.delete(collection_name, ids)


class QdrantClient:
    """Qdrant 向量存储"""
    
    def __init__(self, host: str, port: int, api_key: str = None):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(host=host, port=port, api_key=api_key)
    
    def upsert(self, collection_name: str, vectors: List[dict]):
        """插入向量"""
        self.client.upsert(
            collection_name=collection_name,
            points=[
                {
                    'id': vector['id'],
                    'vector': vector['embedding'],
                    'payload': vector.get('payload', {})
                }
                for vector in vectors
            ]
        )
    
    def search(self, collection_name: str, query_vector: List[float],
               top_k: int = 5, filter: dict = None) -> List[dict]:
        """检索"""
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filter
        )
        return [
            {
                'id': result.id,
                'score': result.score,
                'payload': result.payload
            }
            for result in results
        ]
```

### 1.4 RAG 检索

#### 1.4.1 检索服务

```python
# Backend/rag/services/retriever.py

class RAGRetriever:
    """RAG 检索器"""
    
    def __init__(self, knowledge_base_id: str):
        self.knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id)
        self.config = self.knowledge_base.chunk_config
        self.embedding_service = EmbeddingService(
            provider=self.config.embedding_provider,
            model=self.config.embedding_model
        )
        self.vector_store = VectorStoreService(
            store_type=self.knowledge_base.vector_store_type,
            config=self.knowledge_base.vector_store_config
        )
    
    def retrieve(self, query: str, top_k: int = None, 
                 filters: dict = None) -> List[dict]:
        """检索相关文档"""
        top_k = top_k or self.config.top_k
        
        # 生成查询向量
        query_embedding = self.embedding_service.embed([query])[0]
        
        # 向量检索
        results = self.vector_store.search(
            collection_name=self.knowledge_base.collection_name,
            query_vector=query_embedding,
            top_k=top_k,
            filter=filters
        )
        
        # 过滤低相似度结果
        results = [
            r for r in results 
            if r['score'] >= self.config.min_similarity
        ]
        
        # 可选：重排序
        if self.config.enable_rerank:
            results = self._rerank(query, results)
        
        return results
    
    def _rerank(self, query: str, results: List[dict]) -> List[dict]:
        """重排序"""
        from .services.reranker import RerankerService
        
        reranker = RerankerService()
        reranked = reranker.rerank(query, results)
        
        return reranked
    
    def retrieve_with_context(self, query: str, context_window: int = 3) -> dict:
        """检索并组装上下文"""
        results = self.retrieve(query)
        
        # 收集相关块
        chunks = []
        for result in results:
            chunk_data = result.get('payload', {})
            chunks.append({
                'content': chunk_data.get('content'),
                'source': chunk_data.get('source'),
                'score': result['score']
            })
        
        # 组装上下文
        context = '\n\n'.join([
            f"[Source: {c['source']}]\n{c['content']}"
            for c in chunks
        ])
        
        return {
            'context': context,
            'sources': [
                {'source': c['source'], 'score': c['score']}
                for c in chunks
            ],
            'count': len(chunks)
        }
```

### 1.5 工作流节点集成

#### 1.5.1 RAG 检索节点

```python
# Backend/workflows/nodes/rag_node.py

class RAGRetrievalNode(BaseNode):
    """RAG 检索节点"""
    
    node_type = 'rag'
    
    def execute(self, context: ExecutionContext) -> dict:
        """执行 RAG 检索"""
        config = self.node.config
        
        # 获取配置
        knowledge_base_id = config.get('knowledge_base_id')
        query = self._resolve_query(config.get('query'), context)
        top_k = config.get('top_k', 5)
        
        # 执行检索
        retriever = RAGRetriever(knowledge_base_id)
        results = retriever.retrieve(query, top_k=top_k)
        
        # 组装上下文
        context_text = '\n\n'.join([
            f"[文档{i+1}] {r['payload']['content']}"
            for i, r in enumerate(results)
        ])
        
        # 返回结果
        return {
            'query': query,
            'context': context_text,
            'sources': [r['payload'] for r in results],
            'count': len(results),
            'scores': [r['score'] for r in results]
        }
    
    def _resolve_query(self, query_template: str, context: ExecutionContext) -> str:
        """解析查询模板"""
        # 支持变量插值
        return interpolate(query_template, context.variables)
```

### 1.6 前端集成

#### 1.6.1 知识库管理页面

```vue
<!-- Frontend/src/views/knowledge/Index.vue -->
<template>
  <div class="knowledge-base-list">
    <div class="header">
      <h2>知识库</h2>
      <el-button type="primary" @click="showCreateDialog">
        创建知识库
      </el-button>
    </div>
    
    <el-row :gutter="20">
      <el-col
        v-for="kb in knowledgeBases"
        :key="kb.id"
        :span="8"
      >
        <el-card class="kb-card">
          <template #header>
            <div class="card-header">
              <span>{{ kb.name }}</span>
              <el-tag :type="kb.is_active ? 'success' : 'info'">
                {{ kb.is_active ? '活跃' : '停用' }}
              </el-tag>
            </div>
          </template>
          
          <div class="kb-stats">
            <div class="stat-item">
              <span class="label">文档数</span>
              <span class="value">{{ kb.document_count }}</span>
            </div>
            <div class="stat-item">
              <span class="label">切片数</span>
              <span class="value">{{ kb.chunk_count }}</span>
            </div>
          </div>
          
          <div class="kb-actions">
            <el-button size="small" @click="openDocumentUpload(kb.id)">
              上传文档
            </el-button>
            <el-button size="small" @click="testRetrieval(kb.id)">
              测试检索
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档">
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :file-list="fileList"
        multiple
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF, Word, TXT, Markdown, HTML 等格式
          </div>
        </template>
      </el-upload>
      
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="uploadDocuments">
          开始上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '@/api/rag'

const knowledgeBases = ref([])
const uploadDialogVisible = ref(false)
const fileList = ref([])
const currentKbId = ref(null)

async function fetchKnowledgeBases() {
  const response = await knowledgeApi.getList()
  knowledgeBases.value = response.results
}

function showCreateDialog() {
  // 显示创建对话框
}

function openDocumentUpload(kbId) {
  currentKbId.value = kbId
  fileList.value = []
  uploadDialogVisible.value = true
}

async function uploadDocuments() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }
  
  for (const file of fileList.value) {
    const formData = new FormData()
    formData.append('file', file.raw)
    formData.append('knowledge_base_id', currentKbId.value)
    
    await knowledgeApi.uploadDocument(formData)
  }
  
  ElMessage.success('上传成功')
  uploadDialogVisible.value = false
}

onMounted(() => {
  fetchKnowledgeBases()
})
</script>
```

## 验收标准

- [ ] 支持多种文档格式上传和解析
- [ ] 实现多种分块策略
- [ ] 支持主流向量数据库
- [ ] 实现混合检索（向量 + 关键词）
- [ ] RAG 检索节点集成到工作流
- [ ] 前端知识库管理界面
- [ ] 文档上传和处理进度显示
- [ ] 检索结果预览

## 关键文件清单

| 文件路径 | 说明 |
|---------|------|
| `Backend/rag/models.py` | RAG 数据模型 |
| `Backend/rag/serializers.py` | 序列化器 |
| `Backend/rag/views.py` | API 视图 |
| `Backend/rag/services/document_parser.py` | 文档解析 |
| `Backend/rag/services/chunker.py` | 文本分块 |
| `Backend/rag/services/embedding.py` | 嵌入服务 |
| `Backend/rag/services/vector_store.py` | 向量存储 |
| `Backend/rag/services/retriever.py` | 检索服务 |
| `Backend/rag/tasks.py` | 异步任务 |
| `Backend/workflows/nodes/rag_node.py` | RAG 节点 |
| `Frontend/src/views/knowledge/Index.vue` | 知识库页面 |
| `Frontend/src/api/rag.js` | RAG API |
