"""Vertex AI Embeddings Service

This module provides embedding generation and semantic search capabilities
for the conversational query system using Vertex AI Embeddings API.
"""

import json
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import asyncio

import vertexai
from vertexai.language_models import TextEmbeddingModel
from google.cloud import bigquery
from google.cloud import storage
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingRequest:
    """Request structure for embedding generation."""
    text: str
    task_type: str = "SEMANTIC_SIMILARITY"  # SEMANTIC_SIMILARITY, CLASSIFICATION, CLUSTERING
    title: Optional[str] = None
    context: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """Response structure for embedding generation."""
    embedding: List[float]
    text: str
    embedding_id: str
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class SemanticSearchResult:
    """Result structure for semantic search."""
    text: str
    similarity_score: float
    metadata: Dict[str, Any]
    embedding_id: str


class EmbeddingsService:
    """Service for generating and managing embeddings using Vertex AI."""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model_name: str = "textembedding-gecko@003"
    ):
        """Initialize the embeddings service.
        
        Args:
            project_id: GCP project ID
            location: Vertex AI location
            model_name: Embedding model to use
        """
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        self.model = TextEmbeddingModel.from_pretrained(model_name)
        
        # Initialize clients
        self.bq_client = bigquery.Client(project=project_id)
        self.storage_client = storage.Client(project=project_id)
        
        # Cache for frequently used embeddings
        self.embedding_cache: Dict[str, EmbeddingResponse] = {}
        self.cache_ttl = timedelta(hours=24)
    
    def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embedding for text.
        
        Args:
            request: Embedding generation request
            
        Returns:
            Embedding response with vector and metadata
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(request.text, request.task_type)
            if cache_key in self.embedding_cache:
                cached = self.embedding_cache[cache_key]
                if datetime.now() - cached.created_at < self.cache_ttl:
                    logger.info(f"Using cached embedding for: {request.text[:50]}...")
                    return cached
            
            # Generate embedding
            embeddings = self.model.get_embeddings([request.text], task_type=request.task_type)
            embedding_vector = embeddings[0].values
            
            # Create response
            embedding_id = self._generate_embedding_id(request.text)
            response = EmbeddingResponse(
                embedding=embedding_vector,
                text=request.text,
                embedding_id=embedding_id,
                metadata={
                    "task_type": request.task_type,
                    "title": request.title,
                    "context": request.context,
                    "model": self.model_name,
                    "dimensions": len(embedding_vector)
                },
                created_at=datetime.now()
            )
            
            # Cache the result
            self.embedding_cache[cache_key] = response
            
            logger.info(f"Generated embedding for: {request.text[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def generate_batch_embeddings(
        self, 
        texts: List[str], 
        task_type: str = "SEMANTIC_SIMILARITY"
    ) -> List[EmbeddingResponse]:
        """Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            task_type: Task type for embeddings
            
        Returns:
            List of embedding responses
        """
        try:
            # Check cache for existing embeddings
            responses = []
            texts_to_process = []
            cache_keys = []
            
            for text in texts:
                cache_key = self._get_cache_key(text, task_type)
                if cache_key in self.embedding_cache:
                    cached = self.embedding_cache[cache_key]
                    if datetime.now() - cached.created_at < self.cache_ttl:
                        responses.append(cached)
                        continue
                
                texts_to_process.append(text)
                cache_keys.append(cache_key)
            
            # Process remaining texts
            if texts_to_process:
                embeddings = self.model.get_embeddings(texts_to_process, task_type=task_type)
                
                for i, (text, embedding) in enumerate(zip(texts_to_process, embeddings)):
                    embedding_id = self._generate_embedding_id(text)
                    response = EmbeddingResponse(
                        embedding=embedding.values,
                        text=text,
                        embedding_id=embedding_id,
                        metadata={
                            "task_type": task_type,
                            "model": self.model_name,
                            "dimensions": len(embedding.values)
                        },
                        created_at=datetime.now()
                    )
                    
                    responses.append(response)
                    self.embedding_cache[cache_keys[i]] = response
            
            logger.info(f"Generated {len(responses)} embeddings")
            return responses
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise
    
    def semantic_search(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[Tuple[List[float], Dict[str, Any]]], 
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[SemanticSearchResult]:
        """Perform semantic search using cosine similarity.
        
        Args:
            query_embedding: Query vector
            candidate_embeddings: List of (embedding, metadata) tuples
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results ordered by similarity
        """
        try:
            results = []
            query_vector = np.array(query_embedding)
            
            for candidate_embedding, metadata in candidate_embeddings:
                candidate_vector = np.array(candidate_embedding)
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_vector, candidate_vector)
                
                if similarity >= similarity_threshold:
                    results.append(SemanticSearchResult(
                        text=metadata.get('text', ''),
                        similarity_score=float(similarity),
                        metadata=metadata,
                        embedding_id=metadata.get('embedding_id', '')
                    ))
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to perform semantic search: {str(e)}")
            return []
    
    def embed_dataset_schemas(self, schemas: List[Dict[str, Any]]) -> List[EmbeddingResponse]:
        """Generate embeddings for dataset schemas for RAG retrieval.
        
        Args:
            schemas: List of dataset schema dictionaries
            
        Returns:
            List of embedding responses for schemas
        """
        try:
            schema_texts = []
            
            for schema in schemas:
                # Create comprehensive text representation of schema
                schema_text = self._schema_to_text(schema)
                schema_texts.append(schema_text)
            
            # Generate embeddings
            embeddings = self.generate_batch_embeddings(schema_texts, "CLASSIFICATION")
            
            # Add schema metadata
            for i, embedding in enumerate(embeddings):
                embedding.metadata.update({
                    "type": "schema",
                    "table_name": schemas[i].get("table_name", ""),
                    "column_count": len(schemas[i].get("columns", [])),
                    "schema_data": schemas[i]
                })
            
            logger.info(f"Generated embeddings for {len(schemas)} schemas")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to embed schemas: {str(e)}")
            raise
    
    def embed_query_history(self, queries: List[Dict[str, Any]]) -> List[EmbeddingResponse]:
        """Generate embeddings for query history for similar query retrieval.
        
        Args:
            queries: List of query history dictionaries
            
        Returns:
            List of embedding responses for queries
        """
        try:
            query_texts = []
            
            for query in queries:
                # Combine natural language query with context
                query_text = query.get('natural_language_query', '')
                if query.get('explanation'):
                    query_text += f" -- {query['explanation']}"
                query_texts.append(query_text)
            
            # Generate embeddings
            embeddings = self.generate_batch_embeddings(query_texts, "SEMANTIC_SIMILARITY")
            
            # Add query metadata
            for i, embedding in enumerate(embeddings):
                embedding.metadata.update({
                    "type": "query",
                    "query_id": queries[i].get("id", ""),
                    "sql_query": queries[i].get("sql_query", ""),
                    "success": queries[i].get("success", False),
                    "query_data": queries[i]
                })
            
            logger.info(f"Generated embeddings for {len(queries)} queries")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to embed query history: {str(e)}")
            raise
    
    def find_similar_queries(
        self, 
        query_text: str, 
        query_embeddings: List[EmbeddingResponse],
        top_k: int = 3
    ) -> List[SemanticSearchResult]:
        """Find similar queries from history.
        
        Args:
            query_text: New query text
            query_embeddings: Existing query embeddings
            top_k: Number of similar queries to return
            
        Returns:
            List of similar queries
        """
        try:
            # Generate embedding for new query
            query_request = EmbeddingRequest(
                text=query_text,
                task_type="SEMANTIC_SIMILARITY"
            )
            query_embedding = self.generate_embedding(query_request)
            
            # Prepare candidates
            candidates = [
                (emb.embedding, emb.metadata) 
                for emb in query_embeddings 
                if emb.metadata.get("type") == "query"
            ]
            
            # Perform search
            results = self.semantic_search(
                query_embedding.embedding,
                candidates,
                top_k=top_k,
                similarity_threshold=0.6  # Lower threshold for query similarity
            )
            
            logger.info(f"Found {len(results)} similar queries")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar queries: {str(e)}")
            return []
    
    def find_relevant_schemas(
        self, 
        query_text: str, 
        schema_embeddings: List[EmbeddingResponse],
        top_k: int = 5
    ) -> List[SemanticSearchResult]:
        """Find relevant schemas for a query.
        
        Args:
            query_text: Natural language query
            schema_embeddings: Schema embeddings
            top_k: Number of schemas to return
            
        Returns:
            List of relevant schemas
        """
        try:
            # Generate embedding for query
            query_request = EmbeddingRequest(
                text=query_text,
                task_type="CLASSIFICATION"
            )
            query_embedding = self.generate_embedding(query_request)
            
            # Prepare candidates
            candidates = [
                (emb.embedding, emb.metadata) 
                for emb in schema_embeddings 
                if emb.metadata.get("type") == "schema"
            ]
            
            # Perform search
            results = self.semantic_search(
                query_embedding.embedding,
                candidates,
                top_k=top_k,
                similarity_threshold=0.5  # Schema relevance threshold
            )
            
            logger.info(f"Found {len(results)} relevant schemas")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find relevant schemas: {str(e)}")
            return []
    
    def _schema_to_text(self, schema: Dict[str, Any]) -> str:
        """Convert schema dictionary to text representation."""
        table_name = schema.get('table_name', 'unknown_table')
        columns = schema.get('columns', [])
        description = schema.get('description', '')
        
        text_parts = [f"Table: {table_name}"]
        
        if description:
            text_parts.append(f"Description: {description}")
        
        text_parts.append("Columns:")
        for col in columns:
            col_name = col.get('name', '')
            col_type = col.get('type', '')
            col_desc = col.get('description', '')
            
            col_text = f"- {col_name} ({col_type})"
            if col_desc:
                col_text += f": {col_desc}"
            text_parts.append(col_text)
        
        return "\n".join(text_parts)
    
    def _get_cache_key(self, text: str, task_type: str) -> str:
        """Generate cache key for text and task type."""
        return hashlib.md5((text + task_type).encode()).hexdigest()
    
    def _generate_embedding_id(self, text: str) -> str:
        """Generate unique ID for embedding."""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256((text + timestamp).encode()).hexdigest()[:16]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norms == 0:
            return 0.0
        
        return dot_product / norms
    
    def save_embeddings_to_bigquery(
        self, 
        embeddings: List[EmbeddingResponse],
        table_id: str
    ) -> None:
        """Save embeddings to BigQuery for persistent storage.
        
        Args:
            embeddings: List of embeddings to save
            table_id: BigQuery table ID (dataset.table)
        """
        try:
            # Prepare data for BigQuery
            rows = []
            for emb in embeddings:
                row = {
                    "embedding_id": emb.embedding_id,
                    "text": emb.text,
                    "embedding": json.dumps(emb.embedding),  # Store as JSON string
                    "metadata": json.dumps(emb.metadata),
                    "created_at": emb.created_at.isoformat(),
                    "dimensions": len(emb.embedding)
                }
                rows.append(row)
            
            # Insert into BigQuery
            table = self.bq_client.get_table(table_id)
            errors = self.bq_client.insert_rows_json(table, rows)
            
            if errors:
                logger.error(f"Failed to insert embeddings: {errors}")
                raise Exception(f"BigQuery insert errors: {errors}")
            
            logger.info(f"Saved {len(embeddings)} embeddings to {table_id}")
            
        except Exception as e:
            logger.error(f"Failed to save embeddings: {str(e)}")
            raise
    
    def load_embeddings_from_bigquery(
        self, 
        table_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[EmbeddingResponse]:
        """Load embeddings from BigQuery.
        
        Args:
            table_id: BigQuery table ID
            filters: Optional filters for the query
            
        Returns:
            List of embedding responses
        """
        try:
            # Build query
            query = f"SELECT * FROM `{table_id}`"
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, str):
                        conditions.append(f"{key} = '{value}'")
                    else:
                        conditions.append(f"{key} = {value}")
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            # Execute query
            results = self.bq_client.query(query)
            
            # Convert to EmbeddingResponse objects
            embeddings = []
            for row in results:
                embedding = EmbeddingResponse(
                    embedding=json.loads(row.embedding),
                    text=row.text,
                    embedding_id=row.embedding_id,
                    metadata=json.loads(row.metadata),
                    created_at=datetime.fromisoformat(row.created_at)
                )
                embeddings.append(embedding)
            
            logger.info(f"Loaded {len(embeddings)} embeddings from {table_id}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {str(e)}")
            return []


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize service
    service = EmbeddingsService(PROJECT_ID)
    
    # Example: Generate single embedding
    request = EmbeddingRequest(
        text="Show me the top customers by revenue",
        task_type="SEMANTIC_SIMILARITY"
    )
    
    try:
        response = service.generate_embedding(request)
        print(f"Generated embedding with {len(response.embedding)} dimensions")
        print(f"Embedding ID: {response.embedding_id}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example: Batch embeddings
    texts = [
        "Customer revenue analysis",
        "Product sales trends",
        "Order volume by region"
    ]
    
    try:
        batch_responses = service.generate_batch_embeddings(texts)
        print(f"Generated {len(batch_responses)} embeddings")
    except Exception as e:
        print(f"Error: {e}")