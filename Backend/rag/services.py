"""
RAG (Retrieval-Augmented Generation) service for vector storage and retrieval.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from config.constants import OLLAMA_MODEL_PREFIXES
from core.runtime_config import resolve_default_embedding_model

logger = logging.getLogger(__name__)

EMBEDDING_TIMEOUT_SECONDS = 45
VECTOR_UPSERT_TIMEOUT_SECONDS = 30

# Known embedding output dimensions, used to size the random-vector fallback
# consistently with whichever real embedding model was configured for a collection
# (mixing dimensions within a collection silently breaks similarity search).
EMBEDDING_MODEL_DIMENSIONS = {
    'text-embedding-ada-002': 1536,
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 3072,
    'nomic-embed-text': 768,
}
DEFAULT_FALLBACK_DIMENSION = 1536


class VectorStoreClient(ABC):
    """Abstract base class for vector store clients."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the vector store."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from the vector store."""
        pass

    @abstractmethod
    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        """Create a collection."""
        pass

    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        pass

    @abstractmethod
    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        """Insert or update vectors."""
        pass

    @abstractmethod
    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        """Delete vectors."""
        pass


class InMemoryVectorStore(VectorStoreClient):
    """In-memory vector store for development/testing."""

    def __init__(self):
        self.collections: Dict[str, List[Dict[str, Any]]] = {}
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        self.collections = {}

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        if name not in self.collections:
            self.collections[name] = []
        return True

    def delete_collection(self, name: str) -> bool:
        if name in self.collections:
            del self.collections[name]
        return True

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        if collection not in self.collections:
            self.collections[collection] = []
        self.collections[collection].extend(vectors)
        return True

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if collection not in self.collections:
            return []

        # Simple cosine similarity (for demo)
        results = []
        for item in self.collections[collection]:
            vector = item.get('vector', [])
            if len(vector) == len(query_vector):
                # Calculate cosine similarity
                dot = sum(a * b for a, b in zip(query_vector, vector))
                mag1 = sum(a * a for a in query_vector) ** 0.5
                mag2 = sum(a * a for a in vector) ** 0.5
                score = dot / (mag1 * mag2) if mag1 and mag2 else 0

                results.append({
                    'id': item.get('id'),
                    'score': score,
                    'payload': item.get('payload', {})
                })

        # Sort by score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        if collection in self.collections:
            self.collections[collection] = [
                v for v in self.collections[collection]
                if v.get('id') not in vector_ids
            ]
        return True


def get_vector_store_client(vector_store) -> Optional[VectorStoreClient]:
    """Get vector store client based on configuration."""
    store_type = getattr(vector_store, 'store_type', 'memory')

    if store_type == 'memory':
        return InMemoryVectorStore()
    elif store_type == 'qdrant':
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                host=getattr(vector_store, 'host', 'localhost'),
                port=getattr(vector_store, 'port', 6333),
                api_key=getattr(vector_store, 'api_key', None)
            )
            return QdrantAdapter(client, vector_store)
        except ImportError:
            return InMemoryVectorStore()
    elif store_type == 'chroma':
        try:
            import chromadb
            client = chromadb.Client()
            return ChromaAdapter(client, vector_store)
        except Exception as exc:
            logger.warning("Chroma unavailable (%s), using in-memory store", exc)
            return InMemoryVectorStore()
    elif store_type == 'milvus':
        try:
            from pymilvus import connections
            host = getattr(vector_store, 'host', 'localhost')
            port = getattr(vector_store, 'port', 19530)
            connections.connect(host=host, port=port)
            return MilvusAdapter(connections, vector_store)
        except ImportError:
            return InMemoryVectorStore()
    elif store_type == 'pinecone':
        try:
            from pinecone import Pinecone
            api_key = getattr(vector_store, 'api_key', '')
            environment = getattr(vector_store, 'environment', 'us-east-1')
            client = Pinecone(api_key=api_key)
            return PineconeAdapter(client, vector_store)
        except ImportError:
            return InMemoryVectorStore()
    elif store_type == 'weaviate':
        try:
            import weaviate
            host = getattr(vector_store, 'host', 'localhost')
            port = getattr(vector_store, 'port', 8080)
            client = weaviate.Client(f"http://{host}:{port}")
            return WeaviateAdapter(client, vector_store)
        except ImportError:
            return InMemoryVectorStore()

    return InMemoryVectorStore()


class QdrantAdapter(VectorStoreClient):
    """Adapter for Qdrant client."""

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        from qdrant_client.models import Distance, VectorParams
        distance_map = {'cosine': Distance.COSINE, 'euclidean': Distance.EUCLID}
        self.client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=dimension,
                distance=distance_map.get(metric, Distance.COSINE)
            )
        )
        return True

    def delete_collection(self, name: str) -> bool:
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        return True

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        from qdrant_client.models import PointStruct
        points = [
            PointStruct(
                id=v.get('id'),
                vector=v.get('vector'),
                payload=v.get('payload', {})
            )
            for v in vectors
        ]
        self.client.upsert(collection_name=collection, points=points)
        return True

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k
        )
        return [
            {'id': r.id, 'score': r.score, 'payload': r.payload}
            for r in results
        ]

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        from qdrant_client.models import PointsSelector
        self.client.delete(collection_name=collection, points_selector=PointsSelector(point_ids=vector_ids))
        return True


class ChromaAdapter(VectorStoreClient):
    """Adapter for Chroma client."""

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        self.client.create_collection(name=name)
        return True

    def delete_collection(self, name: str) -> bool:
        self.client.delete_collection(name=name)
        return True

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        try:
            coll = self.client.get_collection(name=collection)
        except Exception:
            self.client.create_collection(name=collection)
            coll = self.client.get_collection(name=collection)
        coll.add(
            ids=[v.get('id') for v in vectors],
            embeddings=[v.get('vector') for v in vectors],
            documents=[v.get('payload', {}).get('content', '') for v in vectors],
            metadatas=[v.get('payload', {}) for v in vectors]
        )
        return True

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        coll = self.client.get_collection(name=collection)
        results = coll.query(query_embeddings=[query_vector], n_results=top_k)
        return [
            {
                'id': results['ids'][0][i],
                'score': results['distances'][0][i] if 'distances' in results else 1,
                'payload': {
                    'content': results['documents'][0][i] if 'documents' in results else ''
                }
            }
            for i in range(len(results['ids'][0]))
        ]

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        coll = self.client.get_collection(name=collection)
        coll.delete(ids=vector_ids)
        return True


class MilvusAdapter(VectorStoreClient):
    """Adapter for Milvus client."""

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.collection_name = getattr(config, 'collection', 'default')

    def connect(self) -> bool:
        try:
            self.client.connect()
            return True
        except Exception:
            return False

    def disconnect(self):
        try:
            self.client.disconnect()
        except Exception:
            pass

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        try:
            from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=200),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            ]

            schema = CollectionSchema(fields=fields, description=f"Collection: {name}")
            collection = Collection(name=name, schema=schema)

            index_params = {
                "metric_type": metric.upper(),
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="vector", index_params=index_params)
            return True
        except Exception:
            return False

    def delete_collection(self, name: str) -> bool:
        try:
            from pymilvus import Collection
            collection = Collection(name)
            collection.drop()
            return True
        except Exception:
            return False

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        try:
            from pymilvus import Collection

            coll = Collection(collection)
            data = [
                [v.get('id') for v in vectors],
                [v.get('vector') for v in vectors]
            ]
            coll.insert(data)
            coll.flush()
            return True
        except Exception:
            return False

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            from pymilvus import Collection

            coll = Collection(collection)
            coll.load()

            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            results = coll.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k
            )

            return [
                {
                    'id': hit.id,
                    'score': 1 - hit.distance,
                    'payload': {}
                }
                for hit in results[0]
            ]
        except Exception:
            return []

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        try:
            from pymilvus import Collection
            coll = Collection(collection)
            expr = f'id in {vector_ids}'
            coll.delete(expr)
            return True
        except Exception:
            return False


class PineconeAdapter(VectorStoreClient):
    """Adapter for Pinecone vector database."""

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self.environment = getattr(config, 'environment', 'us-east-1')

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        try:
            metric_map = {'cosine': 'Cosine', 'euclidean': 'Euclidean', 'dotproduct': 'DotProduct'}
            self.client.create_index(
                name=name,
                dimension=dimension,
                metric=metric_map.get(metric, 'Cosine')
            )
            return True
        except Exception:
            return False

    def delete_collection(self, name: str) -> bool:
        try:
            self.client.delete_index(name)
            return True
        except Exception:
            return False

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        try:
            records = [
                {
                    'id': v.get('id'),
                    'values': v.get('vector'),
                    'metadata': v.get('payload', {})
                }
                for v in vectors
            ]
            self.client.Index(collection).upsert(records)
            return True
        except Exception:
            return False

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.client.Index(collection).query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            return [
                {
                    'id': match['id'],
                    'score': match['score'],
                    'payload': match.get('metadata', {})
                }
                for match in results['matches']
            ]
        except Exception:
            return []

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        try:
            self.client.Index(collection).delete(ids=vector_ids)
            return True
        except Exception:
            return False


class WeaviateAdapter(VectorStoreClient):
    """Adapter for Weaviate vector database."""

    def __init__(self, client, config):
        self.client = client
        self.config = config

    def connect(self) -> bool:
        try:
            meta = self.client.meta.get()
            return meta is not None
        except Exception:
            return False

    def disconnect(self):
        pass

    def create_collection(self, name: str, dimension: int, metric: str = 'cosine') -> bool:
        try:
            schema = {
                "class": name,
                "vectorizer": "none",
                "vectorIndexConfig": {
                    "distanceMetric": metric
                }
            }
            self.client.schema.create_class(schema)
            return True
        except Exception:
            return False

    def delete_collection(self, name: str) -> bool:
        try:
            self.client.schema.delete_class(name)
            return True
        except Exception:
            return False

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> bool:
        try:
            for v in vectors:
                self.client.data_object.create(
                    class_name=collection,
                    data_object=v.get('payload', {}),
                    vector=v.get('vector')
                )
            return True
        except Exception:
            return False

    def search(self, collection: str, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            result = self.client.query.get(
                collection,
                ["content"]
            ).with_near_vector(
                {"vector": query_vector}
            ).with_limit(top_k).do()

            items = result.get('data', {}).get('Get', {}).get(collection, [])
            return [
                {
                    'id': item.get('_additional', {}).get('id'),
                    'score': 1 - item.get('_additional', {}).get('certainty', 0),
                    'payload': item
                }
                for item in items
            ]
        except Exception:
            return []

    def delete(self, collection: str, vector_ids: List[str]) -> bool:
        try:
            for vid in vector_ids:
                self.client.data_object.delete(vid, class_name=collection)
            return True
        except Exception:
            return False


class EmbeddingService:
    """Service for generating embeddings.

    Provider priority: OpenAI-compatible API (if OPENAI_API_KEY configured and the
    model doesn't look like a local Ollama model) -> local Ollama embeddings (if
    reachable) -> random vector fallback (degraded mode, logged as an error since
    it silently produces meaningless similarity scores).
    """

    def __init__(self, model: str = 'text-embedding-ada-002'):
        self.model = model
        self._client = None
        self._provider = None

    def _is_ollama_model(self) -> bool:
        model_lower = (self.model or '').lower()
        return any(prefix in model_lower for prefix in OLLAMA_MODEL_PREFIXES)

    def _get_client(self):
        if self._client is not None:
            return self._client

        from django.conf import settings

        prefer_ollama = self._is_ollama_model()

        if not prefer_ollama:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key and str(api_key).strip():
                try:
                    from langchain_openai import OpenAIEmbeddings
                    base_url = getattr(settings, 'OPENAI_BASE_URL', None)
                    self._client = OpenAIEmbeddings(
                        model=self.model,
                        api_key=api_key,
                        base_url=base_url if base_url else None
                    )
                    self._provider = 'openai'
                    return self._client
                except ImportError:
                    logger.warning("langchain_openai not installed, cannot use OpenAI embeddings")

        try:
            from langchain_ollama import OllamaEmbeddings
            ollama_model = self.model if prefer_ollama else getattr(
                settings, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text'
            )
            base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            self._client = OllamaEmbeddings(
                model=ollama_model,
                base_url=base_url,
                client_kwargs={'trust_env': False},
            )
            self._provider = 'ollama'
            return self._client
        except ImportError:
            logger.error("langchain_ollama not installed, cannot use Ollama embeddings")
        except Exception as exc:
            logger.error("Failed to initialize Ollama embeddings client: %s", exc)

        return None

    def _fallback_dimension(self) -> int:
        return EMBEDDING_MODEL_DIMENSIONS.get(self.model, DEFAULT_FALLBACK_DIMENSION)

    def _log_fallback_degraded_mode(self) -> None:
        logger.error(
            "No embedding provider available (model=%s); falling back to random "
            "vector(s). Retrieval quality will be meaningless until OPENAI_API_KEY "
            "or a reachable local Ollama embedding model is configured.",
            self.model,
        )

    def _random_vector(self, dimension: Optional[int] = None) -> List[float]:
        import random
        return [random.random() for _ in range(dimension or self._fallback_dimension())]

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        client = self._get_client()
        if client:
            try:
                return client.embed_query(text)
            except Exception as exc:
                logger.error("Embedding provider (%s) failed, using fallback: %s", self._provider, exc)
        self._log_fallback_degraded_mode()
        return self._random_vector()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        client = self._get_client()
        if client:
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(client.embed_documents, texts).result(
                        timeout=EMBEDDING_TIMEOUT_SECONDS
                    )
            except FuturesTimeoutError:
                logger.error(
                    "Embedding provider (%s) timed out after %ss, using fallback",
                    self._provider, EMBEDDING_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.error("Embedding provider (%s) failed, using fallback: %s", self._provider, exc)
        self._log_fallback_degraded_mode()
        dimension = self._fallback_dimension()
        return [self._random_vector(dimension) for _ in texts]


class RAGService:
    """RAG (Retrieval-Augmented Generation) service."""

    def __init__(self, collection, top_k: int = 5, min_similarity: float = 0.7):
        self.collection = collection
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.embedding_service = EmbeddingService(
            model=getattr(collection, 'embedding_model', None) or resolve_default_embedding_model()
        )
        self.vector_client = None
        self._using_memory_fallback = False

    def _use_in_memory_fallback(self, reason: str) -> None:
        logger.warning("Using in-memory vector store fallback: %s", reason)
        self.vector_client = InMemoryVectorStore()
        self.vector_client.connect()
        self._using_memory_fallback = True

    def initialize(self) -> bool:
        """Initialize the vector store client."""
        vector_store = getattr(self.collection, 'vector_store', None)
        if vector_store:
            client = get_vector_store_client(vector_store)
            if client:
                try:
                    if client.connect():
                        self.vector_client = client
                        self._using_memory_fallback = isinstance(client, InMemoryVectorStore)
                        return True
                except Exception as exc:
                    self._use_in_memory_fallback(str(exc))
                    return True
        self._use_in_memory_fallback('no vector store configured')
        return True

    def process_document(self, content: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Process document into chunks and generate embeddings."""
        chunks = self._split_into_chunks(content)
        embeddings = self.embedding_service.embed_texts(chunks)

        vectors = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_metadata = {**(metadata or {}), 'chunk_index': i}
            vectors.append({
                'id': f"{metadata.get('doc_id', 'doc')}_{i}",
                'vector': embedding,
                'payload': {'content': chunk, **chunk_metadata}
            })

        return vectors

    def _get_collection_name(self) -> str:
        vector_store = getattr(self.collection, 'vector_store', None)
        if vector_store:
            return getattr(vector_store, 'collection', 'default')
        return 'default'

    def index_document(self, document, vectors: List[Dict[str, Any]]) -> bool:
        """Index document vectors."""
        if not self.vector_client:
            self.initialize()

        collection_name = self._get_collection_name()

        def _do_index(client: VectorStoreClient) -> bool:
            if hasattr(client, 'create_collection') and vectors:
                dimension = len(vectors[0].get('vector') or [])
                try:
                    client.create_collection(collection_name, dimension)
                except Exception:
                    pass

            def _upsert():
                client.upsert(collection=collection_name, vectors=vectors)
                return True

            with ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_upsert).result(timeout=VECTOR_UPSERT_TIMEOUT_SECONDS)

        for attempt in range(2):
            try:
                if not self.vector_client:
                    self.initialize()
                return _do_index(self.vector_client)
            except FuturesTimeoutError:
                logger.warning("Vector upsert timed out for document %s", getattr(document, 'id', ''))
            except Exception as exc:
                logger.warning("Vector indexing failed: %s", exc)

            if attempt == 0 and not isinstance(self.vector_client, InMemoryVectorStore):
                self._use_in_memory_fallback('primary vector store failed during upsert')
                continue
            break

        return False

    def retrieve(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query."""
        if not self.vector_client:
            self.initialize()

        if not self.vector_client:
            return []

        query_embedding = self.embedding_service.embed_text(query)
        collection_name = self._get_collection_name()

        results = self.vector_client.search(
            collection=collection_name,
            query_vector=query_embedding,
            top_k=self.top_k
        )

        return [r for r in results if r['score'] >= self.min_similarity]

    def generate_response(
        self,
        query: str,
        context: List[Dict[str, Any]] = None,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """Generate response using retrieved context."""
        context_str = '\n\n'.join([
            f"[Source {i+1}]: {r['payload'].get('content', '')}"
            for i, r in enumerate(context or [])
        ]) if context else ''

        system = system_prompt or '你是一个有帮助的助手。'

        messages = [{'role': 'system', 'content': system}]

        if context_str:
            messages.append({
                'role': 'user',
                'content': f"上下文信息:\n{context_str}\n\n问题: {query}"
            })
        else:
            messages.append({'role': 'user', 'content': query})

        # Call LLM
        try:
            from core.llm_factory import invoke_chat_messages
            from core.runtime_config import resolve_default_chat_model

            response_text = invoke_chat_messages(
                messages,
                model=resolve_default_chat_model(),
            )

            return {
                'response': response_text,
                'sources': context if context else []
            }
        except Exception as e:
            return {
                'response': f'生成失败: {str(e)}',
                'sources': context if context else []
            }

    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks."""
        chunk_size = getattr(self.collection, 'chunk_size', 1000)
        chunk_overlap = getattr(self.collection, 'chunk_overlap', 200)

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk:
                chunks.append(chunk)
            start = end - chunk_overlap

        return chunks


class DocumentProcessor:
    """Process documents for RAG indexing."""

    def __init__(self, collection):
        self.collection = collection
        self.rag_service = RAGService(collection)

    def process_text(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process plain text content."""
        from .models import Document, Chunk

        document = Document.objects.create(
            collection=self.collection,
            title=metadata.get('title', 'Untitled') if metadata else 'Untitled',
            content=content,
            source_type='text',
            metadata=metadata or {},
            status='processing'
        )

        try:
            vectors = self.rag_service.process_document(content, {
                'doc_id': str(document.id),
                'title': metadata.get('title', 'Untitled') if metadata else 'Untitled'
            })

            success = self.rag_service.index_document(document, vectors)

            if success:
                for i, v in enumerate(vectors):
                    Chunk.objects.create(
                        document=document,
                        content=v['payload'].get('content', ''),
                        chunk_index=i,
                        vector_id=v['id'],
                        metadata=v['payload']
                    )

                document.status = 'completed'
                document.chunk_count = len(vectors)
                document.token_count = sum(len(v['payload'].get('content', '').split()) for v in vectors)
                document.save()

                self.collection.document_count += 1
                self.collection.chunk_count += len(vectors)
                self.collection.save()

                return {'success': True, 'chunks': len(vectors)}

            document.status = 'failed'
            document.error_message = 'Failed to index'
            document.save()
            return {'success': False, 'error': 'Failed to index'}

        except Exception as e:
            document.status = 'failed'
            document.error_message = str(e)
            document.save()
            return {'success': False, 'error': str(e)}

    def process_url(self, url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process content from URL."""
        try:
            import httpx
            response = httpx.get(url, timeout=30)
            response.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')

            for element in soup(['script', 'style']):
                element.decompose()

            content = soup.get_text(separator=' ', strip=True)

            return self.process_text(content, {
                'title': metadata.get('title', url) if metadata else url,
                'source_url': url,
                **(metadata or {})
            })

        except Exception as e:
            return {'success': False, 'error': str(e)}
