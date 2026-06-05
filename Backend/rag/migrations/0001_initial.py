# Generated migration for RAG app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='VectorStore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('store_type', models.CharField(choices=[('qdrant', 'Qdrant'), ('milvus', 'Milvus'), ('chroma', 'Chroma'), ('pinecone', 'Pinecone'), ('weaviate', 'Weaviate')], max_length=50, verbose_name='类型')),
                ('host', models.CharField(default='localhost', max_length=255, verbose_name='主机')),
                ('port', models.IntegerField(default=6333, verbose_name='端口')),
                ('collection', models.CharField(default='default', max_length=200, verbose_name='集合名')),
                ('api_key', models.CharField(blank=True, max_length=500, verbose_name='API Key')),
                ('path', models.CharField(blank=True, max_length=500, verbose_name='本地路径')),
                ('dimension', models.IntegerField(default=1536, verbose_name='向量维度')),
                ('metric', models.CharField(default='cosine', max_length=50, verbose_name='度量方式')),
                ('is_default', models.BooleanField(default=False, verbose_name='是否为默认')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vector_stores', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
            ],
            options={
                'verbose_name': '向量存储',
                'verbose_name_plural': '向量存储',
                'db_table': 'rag_vector_stores',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RAGPipeline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('top_k', models.IntegerField(default=5, verbose_name='返回数量')),
                ('min_similarity', models.FloatField(default=0.7, verbose_name='最低相似度')),
                ('system_prompt', models.TextField(default='你是一个有帮助的助手。使用以下上下文信息回答用户问题。', verbose_name='系统提示词')),
                ('include_sources', models.BooleanField(default=True, verbose_name='包含来源')),
                ('usage_count', models.IntegerField(default=0, verbose_name='使用次数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rag_pipelines', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
            ],
            options={
                'verbose_name': 'RAG流水线',
                'verbose_name_plural': 'RAG流水线',
                'db_table': 'rag_pipelines',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='DocumentCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('embedding_model', models.CharField(default='text-embedding-ada-002', max_length=100, verbose_name='Embedding 模型')),
                ('chunk_size', models.IntegerField(default=1000, verbose_name='分块大小')),
                ('chunk_overlap', models.IntegerField(default=200, verbose_name='分块重叠')),
                ('document_count', models.IntegerField(default=0, verbose_name='文档数')),
                ('chunk_count', models.IntegerField(default=0, verbose_name='分块数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_collections', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
                ('vector_store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collections', to='rag.vectorstore', verbose_name='向量存储')),
            ],
            options={
                'verbose_name': '文档集合',
                'verbose_name_plural': '文档集合',
                'db_table': 'rag_document_collections',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500, verbose_name='标题')),
                ('source_type', models.CharField(choices=[('file', '文件'), ('url', '网址'), ('text', '文本')], default='text', max_length=50, verbose_name='来源类型')),
                ('source_url', models.URLField(blank=True, max_length=2000, verbose_name='来源URL')),
                ('content', models.TextField(verbose_name='内容')),
                ('metadata', models.JSONField(default=dict, verbose_name='元数据')),
                ('status', models.CharField(choices=[('pending', '等待处理'), ('processing', '处理中'), ('completed', '已完成'), ('failed', '失败')], default='pending', max_length=20, verbose_name='状态')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('chunk_count', models.IntegerField(default=0, verbose_name='分块数')),
                ('token_count', models.IntegerField(default=0, verbose_name='Token数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='处理时间')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='rag.documentcollection', verbose_name='所属集合')),
            ],
            options={
                'verbose_name': '文档',
                'verbose_name_plural': '文档',
                'db_table': 'rag_documents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Chunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(verbose_name='内容')),
                ('chunk_index', models.IntegerField(default=0, verbose_name='分块索引')),
                ('vector_id', models.CharField(blank=True, max_length=200, verbose_name='向量ID')),
                ('metadata', models.JSONField(default=dict, verbose_name='元数据')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='rag.document', verbose_name='所属文档')),
            ],
            options={
                'verbose_name': '文档分块',
                'verbose_name_plural': '文档分块',
                'db_table': 'rag_chunks',
                'ordering': ['chunk_index'],
            },
        ),
        migrations.AddField(
            model_name='ragpipeline',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pipelines', to='rag.documentcollection', verbose_name='文档集合'),
        ),
    ]
