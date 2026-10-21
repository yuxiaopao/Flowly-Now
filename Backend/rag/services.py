"""Vector backend adapters. Missing drivers and service failures are explicit errors."""
import json
import hashlib
from django.conf import settings
from .constants import DEFAULT_REQUEST_TIMEOUT
from .pipeline import EmbeddingService, RAGService, DocumentProcessor, RAGUnavailable
from .retrieval import cosine_score


class InMemoryVectorStore:
    """Ephemeral adapter for isolated adapter tests; RAG local storage lives in Chunk.embedding."""
    def __init__(self):
        self.collections = {}

    def connect(self):
        return True

    def disconnect(self):
        self.collections.clear()

    def create_collection(self, name, dimension, metric='cosine'):
        self.collections.setdefault(name, {})
        return True

    def delete_collection(self, name):
        self.collections.pop(name, None)
        return True

    def upsert(self, collection, vectors):
        self.collections.setdefault(collection, {}).update({v['id']: v for v in vectors})
        return True

    def search(self, collection, query_vector, top_k=5):
        results = [{'id': v['id'], 'score': cosine_score(query_vector, v['vector']), 'payload': v['payload']}
                   for v in self.collections.get(collection, {}).values()]
        return sorted(results, key=lambda r: r['score'], reverse=True)[:top_k]

    def delete(self, collection, vector_ids):
        for vector_id in vector_ids:
            self.collections.get(collection, {}).pop(vector_id, None)
        return True


class QdrantAdapter:
    def __init__(self, client, config):
        self.client, self.config = client, config

    def connect(self):
        self.client.get_collections()
        return True

    def disconnect(self):
        self.client.close()

    def create_collection(self, name, dimension, metric='cosine'):
        from qdrant_client.models import Distance, VectorParams
        distance = {'cosine': Distance.COSINE, 'euclidean': Distance.EUCLID, 'dotproduct': Distance.DOT}[metric]
        if self.client.collection_exists(name):
            config = self.client.get_collection(name).config.params.vectors
            if config.size != dimension or config.distance != distance:
                raise RAGUnavailable('已有 Qdrant 索引维度或度量方式不匹配，请新建知识库。')
        else:
            self.client.create_collection(collection_name=name, vectors_config=VectorParams(size=dimension, distance=distance))
        return True

    def delete_collection(self, name):
        if self.client.collection_exists(name):
            self.client.delete_collection(collection_name=name)
        return True

    def upsert(self, collection, vectors):
        from qdrant_client.models import PointStruct
        self.client.upsert(collection_name=collection, points=[PointStruct(**v) for v in vectors], wait=True)
        return True

    def search(self, collection, query_vector, top_k=5):
        results = self.client.query_points(collection_name=collection, query=query_vector, limit=top_k, with_payload=True).points
        return [{'id': str(r.id), 'score': r.score, 'payload': r.payload or {}} for r in results]

    def delete(self, collection, vector_ids):
        from qdrant_client.models import PointIdsList
        if self.client.collection_exists(collection):
            self.client.delete(collection_name=collection, points_selector=PointIdsList(points=vector_ids), wait=True)
        return True


class ChromaAdapter:
    def __init__(self, client, config):
        self.client, self.config = client, config

    def connect(self):
        self.client.heartbeat()
        return True

    def disconnect(self):
        # Chroma owns its process-wide client; there is no public close method.
        self.client = None

    def create_collection(self, name, dimension, metric='cosine'):
        distance = {'cosine': 'cosine', 'euclidean': 'l2', 'dotproduct': 'ip'}[metric]
        self.client.get_or_create_collection(name=name, metadata={'hnsw:space': distance}, embedding_function=None)
        return True

    def delete_collection(self, name):
        self.client.delete_collection(name=name)
        return True

    def upsert(self, collection, vectors):
        self.client.get_collection(collection, embedding_function=None).upsert(
            ids=[v['id'] for v in vectors], embeddings=[v['vector'] for v in vectors],
            documents=[v['payload']['content'] for v in vectors],
            metadatas=[{'payload': json.dumps(v['payload'], ensure_ascii=False)} for v in vectors],
        )
        return True

    def search(self, collection, query_vector, top_k=5):
        coll = self.client.get_collection(collection, embedding_function=None)
        count = coll.count()
        if not count:
            return []
        results = coll.query(query_embeddings=[query_vector], n_results=min(count, top_k))
        return [{'id': key, 'score': 1 - results['distances'][0][i],
                 'payload': json.loads(results['metadatas'][0][i]['payload'])}
                for i, key in enumerate(results['ids'][0])]

    def delete(self, collection, vector_ids):
        self.client.get_collection(collection, embedding_function=None).delete(ids=vector_ids)
        return True


class MilvusAdapter:
    def __init__(self, client, config):
        self.client, self.config = client, config

    def connect(self):
        self.client.list_collections()
        return True

    def disconnect(self):
        self.client.close()

    def create_collection(self, name, dimension, metric='cosine'):
        if not self.client.has_collection(collection_name=name):
            self.client.create_collection(collection_name=name, dimension=dimension,
                primary_field_name='id', id_type='string', max_length=200, vector_field_name='vector',
                metric_type={'cosine': 'COSINE', 'euclidean': 'L2', 'dotproduct': 'IP'}[metric],
                enable_dynamic_field=True, auto_id=False)
        return True

    def delete_collection(self, name):
        self.client.drop_collection(collection_name=name)
        return True

    def upsert(self, collection, vectors):
        self.client.upsert(collection_name=collection, data=vectors)
        self.client.flush(collection_name=collection)
        return True

    def search(self, collection, query_vector, top_k=5):
        results = self.client.search(collection_name=collection, data=[query_vector], limit=top_k,
                                     output_fields=['payload'], consistency_level='Strong')
        return [{'id': str(r['id']), 'score': r['distance'], 'payload': r.get('entity', {}).get('payload', {})} for r in results[0]]

    def delete(self, collection, vector_ids):
        self.client.delete(collection_name=collection, ids=vector_ids)
        return True


class PineconeAdapter:
    def __init__(self, client, config):
        self.client, self.config = client, config

    def connect(self):
        self.client.list_indexes()
        return True

    def disconnect(self):
        self.client.close()

    @staticmethod
    def name(name):
        normalized = name.replace('_', '-').lower()
        return normalized if len(normalized) <= 45 else f'flowly-{hashlib.sha256(normalized.encode()).hexdigest()[:32]}'

    def create_collection(self, name, dimension, metric='cosine'):
        from pinecone import ServerlessSpec
        name = self.name(name)
        if name not in self.client.list_indexes().names():
            self.client.create_index(name=name, dimension=dimension, metric=metric,
                spec=ServerlessSpec(cloud=getattr(settings, 'RAG_PINECONE_CLOUD', 'aws'),
                                    region=getattr(settings, 'RAG_PINECONE_REGION', 'us-east-1')),
                timeout=getattr(settings, 'RAG_REQUEST_TIMEOUT', DEFAULT_REQUEST_TIMEOUT))
        elif self.client.describe_index(name).dimension != dimension:
            raise RAGUnavailable('Pinecone 索引维度不匹配，请新建知识库。')
        return True

    def delete_collection(self, name):
        self.client.delete_index(self.name(name))
        return True

    def upsert(self, collection, vectors):
        self.client.Index(self.name(collection)).upsert(vectors=[
            {'id': v['id'], 'values': v['vector'], 'metadata': {'payload': json.dumps(v['payload'], ensure_ascii=False)}} for v in vectors])
        return True

    def search(self, collection, query_vector, top_k=5):
        results = self.client.Index(self.name(collection)).query(vector=query_vector, top_k=top_k, include_metadata=True)
        return [{'id': r['id'], 'score': r['score'], 'payload': json.loads(r.get('metadata', {}).get('payload', '{}'))}
                for r in results['matches']]

    def delete(self, collection, vector_ids):
        self.client.Index(self.name(collection)).delete(ids=vector_ids)
        return True


class WeaviateAdapter:
    def __init__(self, client, config):
        self.client, self.config = client, config

    @staticmethod
    def name(name):
        return name[:1].upper() + name[1:]

    def connect(self):
        return self.client.is_ready()

    def disconnect(self):
        self.client.close()

    def create_collection(self, name, dimension, metric='cosine'):
        from weaviate.classes.config import Configure, Property, DataType, VectorDistances
        name = self.name(name)
        if not self.client.collections.exists(name):
            self.client.collections.create(name, vectorizer_config=Configure.Vectorizer.none(),
                vector_index_config=Configure.VectorIndex.hnsw(distance_metric={
                    'cosine': VectorDistances.COSINE, 'euclidean': VectorDistances.L2_SQUARED,
                    'dotproduct': VectorDistances.DOT}[metric]),
                properties=[Property(name='payload', data_type=DataType.TEXT)])
        return True

    def delete_collection(self, name):
        self.client.collections.delete(self.name(name))
        return True

    def upsert(self, collection, vectors):
        coll = self.client.collections.get(self.name(collection))
        for v in vectors:
            properties = {'payload': json.dumps(v['payload'], ensure_ascii=False)}
            if coll.data.exists(v['id']):
                coll.data.replace(uuid=v['id'], properties=properties, vector=v['vector'])
            else:
                coll.data.insert(uuid=v['id'], properties=properties, vector=v['vector'])
        return True

    def search(self, collection, query_vector, top_k=5):
        from weaviate.classes.query import MetadataQuery
        result = self.client.collections.get(self.name(collection)).query.near_vector(
            near_vector=query_vector, limit=top_k, return_metadata=MetadataQuery(distance=True))
        return [{'id': str(r.uuid), 'score': 1 - r.metadata.distance, 'payload': json.loads(r.properties['payload'])} for r in result.objects]

    def delete(self, collection, vector_ids):
        coll = self.client.collections.get(self.name(collection))
        for vector_id in vector_ids:
            coll.data.delete_by_id(vector_id)
        return True


def get_vector_store_client(vector_store):
    kind = vector_store.store_type
    timeout = getattr(settings, 'RAG_REQUEST_TIMEOUT', DEFAULT_REQUEST_TIMEOUT)
    try:
        if kind == 'memory':
            return InMemoryVectorStore()
        if kind == 'qdrant':
            from qdrant_client import QdrantClient
            kwargs = {'api_key': vector_store.api_key or None, 'timeout': timeout}
            if vector_store.path:
                kwargs['path'] = vector_store.path
            elif '://' in vector_store.host:
                kwargs['url'] = vector_store.host
            else:
                kwargs.update(host=vector_store.host, port=vector_store.port)
            return QdrantAdapter(QdrantClient(**kwargs), vector_store)
        if kind == 'chroma':
            import chromadb
            client = chromadb.PersistentClient(path=vector_store.path) if vector_store.path else chromadb.HttpClient(host=vector_store.host, port=vector_store.port)
            return ChromaAdapter(client, vector_store)
        if kind == 'milvus':
            from pymilvus import MilvusClient
            uri = vector_store.host if '://' in vector_store.host else f'http://{vector_store.host}:{vector_store.port}'
            return MilvusAdapter(MilvusClient(uri=uri, token=vector_store.api_key or '', timeout=timeout), vector_store)
        if kind == 'pinecone':
            from pinecone import Pinecone
            return PineconeAdapter(Pinecone(api_key=vector_store.api_key), vector_store)
        if kind == 'weaviate':
            import weaviate
            from weaviate.classes.init import Auth, AdditionalConfig, Timeout
            client = weaviate.connect_to_custom(http_host=vector_store.host, http_port=vector_store.port, http_secure=False,
                grpc_host=vector_store.host, grpc_port=getattr(settings, 'RAG_WEAVIATE_GRPC_PORT', 50051), grpc_secure=False,
                auth_credentials=Auth.api_key(vector_store.api_key) if vector_store.api_key else None,
                additional_config=AdditionalConfig(timeout=Timeout(init=timeout, query=timeout, insert=timeout)))
            return WeaviateAdapter(client, vector_store)
    except ImportError as exc:
        raise RAGUnavailable(f'未安装或驱动版本不兼容: {kind}，请安装 requirements-rag.txt 中的对应驱动。') from exc
    raise RAGUnavailable('不支持此向量存储类型；Ollama 是嵌入服务，请选择本地持久化存储。')
