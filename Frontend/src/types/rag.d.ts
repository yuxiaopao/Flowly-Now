/**
 * RAG API Type Definitions
 * Vector stores, document collections, documents, chunks, and RAG pipelines.
 */

/** Vector store configuration */
export interface VectorStore {
  id: string
  name: string
  store_type: VectorStoreType
  store_type_display?: string
  host: string | null
  port: number | null
  collection: string | null
  dimension: number | null
  metric: DistanceMetric | null
  api_key?: string
  path: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export type VectorStoreType = 'chroma' | 'pinecone' | 'milvus' | 'qdrant' | 'weaviate' | 'pgvector'
export type DistanceMetric = 'cosine' | 'euclidean' | 'dotproduct'

/** Data for creating a vector store */
export interface CreateVectorStoreData {
  name: string
  store_type: VectorStoreType
  host?: string
  port?: number
  collection?: string
  api_key?: string
  path?: string
  dimension?: number
  metric?: DistanceMetric
  is_default?: boolean
}

/** Vector store connection test result */
export interface VectorStoreConnectionTest {
  success: boolean
  latency_ms?: number
  error?: string
  collections?: string[]
}

/** Document collection */
export interface DocumentCollection {
  id: string
  name: string
  description: string | null
  vector_store: string
  vector_store_name?: string
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  document_count: number
  chunk_count: number
  created_at: string
  updated_at: string
}

/** Data for creating a collection */
export interface CreateCollectionData {
  name: string
  description?: string
  vector_store: string
  embedding_model?: string
  chunk_size?: number
  chunk_overlap?: number
}

/** Document in a collection */
export interface Document {
  id: string
  title: string
  source_type: SourceType
  source_url: string | null
  status: DocumentStatus
  status_display?: string
  chunk_count: number
  token_count: number
  metadata: Record<string, unknown>
  error_message?: string
  created_at: string
  processed_at: string | null
}

export type SourceType = 'text' | 'url' | 'file' | 'api'
export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed'

/** Data for creating a document */
export interface CreateDocumentData {
  title: string
  content: string
  metadata?: Record<string, unknown>
}

/** URL document creation */
export interface CreateURLDocumentData {
  url: string
  title?: string
}

/** Document chunk */
export interface Chunk {
  id: string
  content: string
  chunk_index: number
  metadata: Record<string, unknown>
  created_at: string
}

/** RAG Pipeline configuration */
export interface RAGPipeline {
  id: string
  name: string
  description: string | null
  collection: string
  collection_name?: string
  top_k: number
  min_similarity: number
  system_prompt: string | null
  include_sources: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

/** Data for creating a RAG pipeline */
export interface CreatePipelineData {
  name: string
  description?: string
  collection: string
  top_k?: number
  min_similarity?: number
  system_prompt?: string
  include_sources?: boolean
}

/** RAG query request */
export interface RAGQueryRequest {
  query: string
  filters?: Record<string, unknown>
  top_k?: number
  include_sources?: boolean
}

/** RAG query response */
export interface RAGQueryResponse {
  answer: string
  sources?: DocumentSource[]
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

/** Document source from RAG retrieval */
export interface DocumentSource {
  document_id: string
  title: string
  content: string
  score: number
  metadata?: Record<string, unknown>
}

/** Collection search result */
export interface CollectionSearchResult {
  documents: DocumentSource[]
  query: string
  total: number
}
