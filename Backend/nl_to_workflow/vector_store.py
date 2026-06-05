"""
Vector Store Service for Template Storage.

Provides semantic search capabilities using PostgreSQL + pgvector for:
- Workflow template embedding and storage
- Semantic similarity search
- Template retrieval based on user queries

Requirements:
- PostgreSQL with pgvector extension installed
- Set environment variables: PG_HOST, PG_PORT, PG_NAME, PG_USER, PG_PASSWORD
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def get_pg_connection_params() -> Dict[str, Any]:
    """Get PostgreSQL connection parameters from environment variables."""
    return {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': int(os.getenv('PG_PORT', 5432)),
        'database': os.getenv('PG_NAME', 'flowly_vector'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', ''),
    }


@dataclass
class TemplateEmbedding:
    """Template with its embedding vector."""
    template_id: str
    name: str
    description: str
    category: str
    embedding: List[float]
    metadata: Dict[str, Any]


class PgVectorConnection:
    """
    Connection manager for PgVector operations.

    Ensures the pgvector extension and table exist.
    Uses separate PostgreSQL connection (not Django's MySQL connection).
    """

    _initialized = False

    @classmethod
    def _get_pg_connection(cls):
        """Get a PostgreSQL connection."""
        try:
            import psycopg2
            return psycopg2.connect(**get_pg_connection_params())
        except ImportError:
            logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
            return None
        except Exception as e:
            # Distinguish between connection errors and config errors
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, OperationalError):
                logger.error(f"PostgreSQL connection failed: {e}")
            elif isinstance(e, ProgrammingError):
                logger.error(f"PostgreSQL configuration error: {e}")
            else:
                logger.error(f"PostgreSQL unexpected error: {e}")
            return None

    @classmethod
    def ensure_extension(cls) -> bool:
        """Ensure pgvector extension is enabled."""
        if cls._initialized:
            return True

        conn = cls._get_pg_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
            cursor.close()
            conn.close()
            cls._initialized = True
            return True
        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Failed to create vector extension (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Failed to create vector extension (connection error): {e}")
            else:
                logger.error(f"Failed to create vector extension: {e}")
            if conn:
                conn.close()
            return False

    @classmethod
    def create_table(cls) -> bool:
        """Create the template embeddings table."""
        conn = cls._get_pg_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_template_embeddings (
                    id SERIAL PRIMARY KEY,
                    template_id VARCHAR(255) NOT NULL UNIQUE,
                    name VARCHAR(500),
                    description TEXT,
                    category VARCHAR(100),
                    embedding VECTOR(1536),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_template_embeddings_vector
                ON workflow_template_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_template_embeddings_category
                ON workflow_template_embeddings (category);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Failed to create embeddings table (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Failed to create embeddings table (connection error): {e}")
            else:
                logger.error(f"Failed to create embeddings table: {e}")
            if conn:
                conn.close()
            return False

    @classmethod
    def initialize(cls) -> bool:
        """Initialize PgVector for template embeddings."""
        cls.ensure_extension()
        cls.create_table()
        return True


class EmbeddingService:
    """
    Service for generating and managing embeddings.

    Uses OpenAI's text-embedding-3-small model by default.
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self._embedding_cache: Dict[str, List[float]] = {}

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None on error
        """
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, embeddings will not work")
            return None

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            response = client.embeddings.create(
                model=self.model,
                input=text
            )

            embedding = response.data[0].embedding
            self._embedding_cache[text] = embedding
            return embedding

        except ImportError as e:
            logger.error(f"OpenAI SDK not installed: {e}")
            return None
        except Exception as e:
            from openai import AuthenticationError, RateLimitError, APIError
            if isinstance(e, AuthenticationError):
                logger.error(f"OpenAI authentication failed: {e}")
            elif isinstance(e, RateLimitError):
                logger.error(f"OpenAI rate limit exceeded: {e}")
            elif isinstance(e, APIError):
                logger.error(f"OpenAI API error: {e}")
            else:
                logger.error(f"Failed to generate embedding: {e}")
            return None

    def generate_batch_embeddings(
        self,
        texts: List[str]
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        api_key = os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            return [None] * len(texts)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            response = client.embeddings.create(
                model=self.model,
                input=texts
            )

            embeddings = [item.embedding for item in response.data]
            return embeddings

        except ImportError as e:
            logger.error(f"OpenAI SDK not installed: {e}")
            return [None] * len(texts)
        except Exception as e:
            from openai import AuthenticationError, RateLimitError, APIError
            if isinstance(e, AuthenticationError):
                logger.error(f"OpenAI authentication failed: {e}")
            elif isinstance(e, RateLimitError):
                logger.error(f"OpenAI rate limit exceeded: {e}")
            elif isinstance(e, APIError):
                logger.error(f"OpenAI API error: {e}")
            else:
                logger.error(f"Failed to generate batch embeddings: {e}")
            return [None] * len(texts)


class TemplateVectorStore:
    """
    Vector store for workflow templates.

    Provides semantic search capabilities using PostgreSQL + pgvector.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self.embedding_service = embedding_service or EmbeddingService()
        PgVectorConnection.initialize()

    def _get_pg_connection(self):
        """Get a PostgreSQL connection."""
        return PgVectorConnection._get_pg_connection()

    def index_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Index a workflow template for semantic search.

        Args:
            template_id: Unique template identifier
            name: Template name
            description: Template description
            category: Template category
            metadata: Additional metadata

        Returns:
            True if indexed successfully
        """
        conn = self._get_pg_connection()
        if not conn:
            return False

        try:
            text_to_embed = f"{name}. {description}"
            embedding = self.embedding_service.generate_embedding(text_to_embed)

            if not embedding:
                logger.error(f"Failed to generate embedding for template {template_id}")
                conn.close()
                return False

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_template_embeddings
                    (template_id, name, description, category, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (template_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                template_id,
                name,
                description,
                category,
                json.dumps(embedding),
                json.dumps(metadata or {})
            ))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Indexed template {template_id}")
            return True

        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Failed to index template {template_id} (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Failed to index template {template_id} (connection error): {e}")
            else:
                logger.error(f"Failed to index template {template_id}: {e}")
            if conn:
                conn.close()
            return False

    def search_similar(
        self,
        query: str,
        limit: int = 5,
        category: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar templates using semantic similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            category: Optional category filter
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of similar templates with similarity scores
        """
        conn = self._get_pg_connection()
        if not conn:
            return []

        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            if not query_embedding:
                conn.close()
                return []

            cursor = conn.cursor()

            if category:
                cursor.execute("""
                    SELECT
                        template_id,
                        name,
                        description,
                        category,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM workflow_template_embeddings
                    WHERE category = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """, (json.dumps(query_embedding), category,
                      json.dumps(query_embedding), limit))
            else:
                cursor.execute("""
                    SELECT
                        template_id,
                        name,
                        description,
                        category,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM workflow_template_embeddings
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                """, (json.dumps(query_embedding),
                      json.dumps(query_embedding), limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            results = []
            for row in rows:
                similarity = float(row[5]) if row[5] else 0.0
                if similarity >= min_similarity:
                    results.append({
                        'template_id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'category': row[3],
                        'metadata': row[4],
                        'similarity': round(similarity, 4)
                    })

            return results

        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Template search failed (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Template search failed (connection error): {e}")
            else:
                logger.error(f"Template search failed: {e}")
            if conn:
                conn.close()
            return []

    def search_by_keyword(
        self,
        keyword: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search templates by keyword (fallback if embeddings unavailable).

        Args:
            keyword: Search keyword
            limit: Maximum results

        Returns:
            List of matching templates
        """
        conn = self._get_pg_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    template_id,
                    name,
                    description,
                    category,
                    metadata,
                    1.0 AS similarity
                FROM workflow_template_embeddings
                WHERE name ILIKE %s OR description ILIKE %s
                ORDER BY name
                LIMIT %s;
            """, (f"%{keyword}%", f"%{keyword}%", limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            return [
                {
                    'template_id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'metadata': row[4],
                    'similarity': float(row[5])
                }
                for row in rows
            ]

        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Keyword search failed (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Keyword search failed (connection error): {e}")
            else:
                logger.error(f"Keyword search failed: {e}")
            if conn:
                conn.close()
            return []

    def delete_template(self, template_id: str) -> bool:
        """Delete a template from the vector store."""
        conn = self._get_pg_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM workflow_template_embeddings
                WHERE template_id = %s;
            """, (template_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            from psycopg2 import OperationalError, ProgrammingError
            if isinstance(e, ProgrammingError):
                logger.error(f"Failed to delete template {template_id} (SQL error): {e}")
            elif isinstance(e, OperationalError):
                logger.error(f"Failed to delete template {template_id} (connection error): {e}")
            else:
                logger.error(f"Failed to delete template {template_id}: {e}")
            if conn:
                conn.close()
            return False

    def bulk_index(self, templates: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk index multiple templates.

        Args:
            templates: List of template dicts with id, name, description, category

        Returns:
            Dict with success and failure counts
        """
        success = 0
        failed = 0

        for template in templates:
            result = self.index_template(
                template_id=template['id'],
                name=template['name'],
                description=template.get('description', ''),
                category=template.get('category', ''),
                metadata=template.get('metadata', {})
            )
            if result:
                success += 1
            else:
                failed += 1

        return {'success': success, 'failed': failed}


class TemplateIndexManager:
    """
    Manager for indexing workflow templates.

    Handles initial indexing and updates.
    """

    def __init__(self):
        self.vector_store = TemplateVectorStore()

    def index_existing_templates(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Index all existing workflow templates.

        Args:
            batch_size: Number of templates to process at once

        Returns:
            Dict with counts
        """
        from workflows.models import WorkflowTemplate

        total = 0
        success = 0
        failed = 0

        templates = WorkflowTemplate.objects.all()
        batch = []

        for template in templates.iterator():
            batch.append({
                'id': str(template.id),
                'name': template.name,
                'description': template.description or '',
                'category': template.category or '',
                'metadata': {
                    'created_at': template.created_at.isoformat() if template.created_at else None,
                    'is_public': template.is_public,
                }
            })

            if len(batch) >= batch_size:
                result = self.vector_store.bulk_index(batch)
                success += result['success']
                failed += result['failed']
                total += len(batch)
                batch = []

        if batch:
            result = self.vector_store.bulk_index(batch)
            success += result['success']
            failed += result['failed']
            total += len(batch)

        return {'total': total, 'success': success, 'failed': failed}

    def index_domain_templates(self) -> Dict[str, int]:
        """Index domain templates."""
        from workflows.models import DomainTemplate

        templates = DomainTemplate.objects.all()
        data = [
            {
                'id': str(t.id),
                'name': t.name,
                'description': t.description or '',
                'category': t.domain or '',
                'metadata': {
                    'use_count': t.use_count,
                }
            }
            for t in templates
        ]

        return self.vector_store.bulk_index(data)


_embedding_service: Optional[EmbeddingService] = None
_vector_store: Optional[TemplateVectorStore] = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_vector_store() -> TemplateVectorStore:
    """Get singleton vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = TemplateVectorStore(get_embedding_service())
    return _vector_store


def search_templates(
    query: str,
    limit: int = 5,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Convenience function to search templates."""
    store = get_vector_store()
    return store.search_similar(query, limit=limit, category=category)
