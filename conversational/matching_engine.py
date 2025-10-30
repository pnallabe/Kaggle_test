"""Matching Engine RAG Service

This module implements RAG (Retrieval-Augmented Generation) using Google Cloud
Matching Engine for enhanced context retrieval in conversational querying.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import uuid

from google.cloud import aiplatform
from google.cloud import storage
from google.cloud.aiplatform import MatchingEngineIndex, MatchingEngineIndexEndpoint
import numpy as np

from .embeddings import EmbeddingsService, EmbeddingResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context retrieved for RAG-enhanced generation."""
    relevant_schemas: List[Dict[str, Any]]
    similar_queries: List[Dict[str, Any]]
    domain_knowledge: List[Dict[str, Any]]
    confidence_score: float
    retrieval_metadata: Dict[str, Any]


@dataclass
class IndexingRequest:
    """Request for indexing data in Matching Engine."""
    embeddings: List[EmbeddingResponse]
    index_name: str
    metadata: Dict[str, Any]


class MatchingEngineRAGService:
    """Service for RAG-based context retrieval using Matching Engine."""
    
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        embeddings_service: Optional[EmbeddingsService] = None
    ):
        """Initialize the RAG service.
        
        Args:
            project_id: GCP project ID
            location: GCP location
            embeddings_service: Embeddings service instance
        """
        self.project_id = project_id
        self.location = location
        
        # Initialize AI Platform
        aiplatform.init(project=project_id, location=location)
        
        # Initialize clients
        self.storage_client = storage.Client(project=project_id)
        
        # Embeddings service
        self.embeddings_service = embeddings_service or EmbeddingsService(project_id, location)
        
        # Index configuration
        self.index_config = {
            "dimensions": 768,  # Default for textembedding-gecko
            "approximate_neighbors_count": 150,
            "distance_measure_type": "COSINE_DISTANCE",
            "algorithm_config": {
                "tree_ah_config": {
                    "leaf_node_embedding_count": 500,
                    "leaf_nodes_to_search_percent": 7
                }
            }
        }
        
        # Active indexes
        self.indexes: Dict[str, MatchingEngineIndex] = {}
        self.endpoints: Dict[str, MatchingEngineIndexEndpoint] = {}
    
    def create_index(
        self, 
        index_name: str, 
        display_name: str,
        dimensions: int = 768
    ) -> MatchingEngineIndex:
        """Create a new Matching Engine index.
        
        Args:
            index_name: Unique index name
            display_name: Human-readable display name
            dimensions: Embedding dimensions
            
        Returns:
            Created index
        """
        try:
            logger.info(f"Creating Matching Engine index: {display_name}")
            
            # Update config with dimensions
            config = self.index_config.copy()
            config["dimensions"] = dimensions
            
            # Create index
            index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name=display_name,
                contents_delta_uri=f"gs://{self.project_id}-matching-engine/{index_name}",
                dimensions=dimensions,
                approximate_neighbors_count=config["approximate_neighbors_count"],
                distance_measure_type=config["distance_measure_type"],
                leaf_node_embedding_count=config["algorithm_config"]["tree_ah_config"]["leaf_node_embedding_count"],
                leaf_nodes_to_search_percent=config["algorithm_config"]["tree_ah_config"]["leaf_nodes_to_search_percent"]
            )
            
            self.indexes[index_name] = index
            logger.info(f"Created index: {index.resource_name}")
            return index
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise
    
    def create_endpoint(
        self, 
        endpoint_name: str, 
        display_name: str
    ) -> MatchingEngineIndexEndpoint:
        """Create a new Matching Engine endpoint.
        
        Args:
            endpoint_name: Unique endpoint name
            display_name: Human-readable display name
            
        Returns:
            Created endpoint
        """
        try:
            logger.info(f"Creating Matching Engine endpoint: {display_name}")
            
            endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
                display_name=display_name,
                public_endpoint_enabled=True
            )
            
            self.endpoints[endpoint_name] = endpoint
            logger.info(f"Created endpoint: {endpoint.resource_name}")
            return endpoint
            
        except Exception as e:
            logger.error(f"Failed to create endpoint: {str(e)}")
            raise
    
    def index_embeddings(
        self, 
        request: IndexingRequest,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Index embeddings in Matching Engine.
        
        Args:
            request: Indexing request with embeddings
            bucket_name: GCS bucket for storing embeddings
            
        Returns:
            Success status
        """
        try:
            bucket_name = bucket_name or f"{self.project_id}-matching-engine"
            
            # Prepare embeddings data
            embeddings_data = self._prepare_embeddings_for_indexing(request.embeddings)
            
            # Upload to GCS
            blob_path = f"{request.index_name}/embeddings_{int(time.time())}.json"
            self._upload_embeddings_to_gcs(embeddings_data, bucket_name, blob_path)
            
            # Update index with new data
            if request.index_name in self.indexes:
                index = self.indexes[request.index_name]
                index.update_embeddings(
                    contents_delta_uri=f"gs://{bucket_name}/{blob_path}"
                )
            
            logger.info(f"Indexed {len(request.embeddings)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index embeddings: {str(e)}")
            return False
    
    def deploy_index(
        self, 
        index_name: str, 
        endpoint_name: str,
        deployed_index_id: str
    ) -> bool:
        """Deploy index to endpoint.
        
        Args:
            index_name: Name of index to deploy
            endpoint_name: Name of endpoint
            deployed_index_id: ID for deployed index
            
        Returns:
            Success status
        """
        try:
            if index_name not in self.indexes:
                raise ValueError(f"Index {index_name} not found")
            
            if endpoint_name not in self.endpoints:
                raise ValueError(f"Endpoint {endpoint_name} not found")
            
            index = self.indexes[index_name]
            endpoint = self.endpoints[endpoint_name]
            
            logger.info(f"Deploying index {index_name} to endpoint {endpoint_name}")
            
            endpoint.deploy_index(
                index=index,
                deployed_index_id=deployed_index_id,
                display_name=f"Deployed {index_name}"
            )
            
            logger.info(f"Successfully deployed index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy index: {str(e)}")
            return False
    
    def retrieve_context(
        self, 
        query: str, 
        index_name: str,
        endpoint_name: str,
        deployed_index_id: str,
        num_neighbors: int = 10
    ) -> RAGContext:
        """Retrieve relevant context for a query using RAG.
        
        Args:
            query: Natural language query
            index_name: Index to search
            endpoint_name: Endpoint name
            deployed_index_id: Deployed index ID
            num_neighbors: Number of neighbors to retrieve
            
        Returns:
            RAG context with relevant information
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings_service.generate_embedding(
                self.embeddings_service.EmbeddingRequest(
                    text=query,
                    task_type="SEMANTIC_SIMILARITY"
                )
            )
            
            # Search for similar embeddings
            endpoint = self.endpoints[endpoint_name]
            matches = endpoint.find_neighbors(
                deployed_index_id=deployed_index_id,
                queries=[query_embedding.embedding],
                num_neighbors=num_neighbors
            )
            
            # Process matches to extract context
            context = self._process_matches_to_context(matches[0], query)
            
            logger.info(f"Retrieved RAG context with confidence {context.confidence_score}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {str(e)}")
            return RAGContext(
                relevant_schemas=[],
                similar_queries=[],
                domain_knowledge=[],
                confidence_score=0.0,
                retrieval_metadata={"error": str(e)}
            )
    
    def retrieve_schema_context(
        self, 
        query: str,
        schema_embeddings: List[EmbeddingResponse],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant schemas using local embeddings search.
        
        Args:
            query: Natural language query
            schema_embeddings: Pre-computed schema embeddings
            top_k: Number of schemas to return
            
        Returns:
            List of relevant schema contexts
        """
        try:
            # Find relevant schemas using embeddings service
            relevant_schemas = self.embeddings_service.find_relevant_schemas(
                query, schema_embeddings, top_k
            )
            
            # Extract schema data
            schema_contexts = []
            for result in relevant_schemas:
                schema_data = result.metadata.get('schema_data', {})
                schema_contexts.append({
                    "schema": schema_data,
                    "relevance_score": result.similarity_score,
                    "table_name": schema_data.get('table_name', ''),
                    "description": self._generate_schema_description(schema_data)
                })
            
            logger.info(f"Retrieved {len(schema_contexts)} relevant schemas")
            return schema_contexts
            
        except Exception as e:
            logger.error(f"Failed to retrieve schema context: {str(e)}")
            return []
    
    def retrieve_query_context(
        self, 
        query: str,
        query_embeddings: List[EmbeddingResponse],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Retrieve similar queries for context.
        
        Args:
            query: Natural language query
            query_embeddings: Pre-computed query embeddings
            top_k: Number of similar queries to return
            
        Returns:
            List of similar query contexts
        """
        try:
            # Find similar queries using embeddings service
            similar_queries = self.embeddings_service.find_similar_queries(
                query, query_embeddings, top_k
            )
            
            # Extract query data
            query_contexts = []
            for result in similar_queries:
                query_data = result.metadata.get('query_data', {})
                query_contexts.append({
                    "natural_language": query_data.get('natural_language_query', ''),
                    "sql_query": query_data.get('sql_query', ''),
                    "explanation": query_data.get('explanation', ''),
                    "similarity_score": result.similarity_score,
                    "success": query_data.get('success', False)
                })
            
            logger.info(f"Retrieved {len(query_contexts)} similar queries")
            return query_contexts
            
        except Exception as e:
            logger.error(f"Failed to retrieve query context: {str(e)}")
            return []
    
    def build_enhanced_context(
        self, 
        query: str,
        schema_embeddings: List[EmbeddingResponse],
        query_embeddings: List[EmbeddingResponse],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> RAGContext:
        """Build comprehensive context for enhanced SQL generation.
        
        Args:
            query: Natural language query
            schema_embeddings: Schema embeddings
            query_embeddings: Query history embeddings
            additional_context: Additional context information
            
        Returns:
            Comprehensive RAG context
        """
        try:
            # Retrieve schema context
            relevant_schemas = self.retrieve_schema_context(query, schema_embeddings)
            
            # Retrieve query context
            similar_queries = self.retrieve_query_context(query, query_embeddings)
            
            # Build domain knowledge from schemas and queries
            domain_knowledge = self._extract_domain_knowledge(
                relevant_schemas, similar_queries
            )
            
            # Calculate overall confidence
            confidence_score = self._calculate_context_confidence(
                relevant_schemas, similar_queries
            )
            
            # Build metadata
            retrieval_metadata = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "schema_count": len(relevant_schemas),
                "similar_query_count": len(similar_queries),
                "domain_knowledge_count": len(domain_knowledge)
            }
            
            if additional_context:
                retrieval_metadata.update(additional_context)
            
            return RAGContext(
                relevant_schemas=relevant_schemas,
                similar_queries=similar_queries,
                domain_knowledge=domain_knowledge,
                confidence_score=confidence_score,
                retrieval_metadata=retrieval_metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to build enhanced context: {str(e)}")
            return RAGContext(
                relevant_schemas=[],
                similar_queries=[],
                domain_knowledge=[],
                confidence_score=0.0,
                retrieval_metadata={"error": str(e)}
            )
    
    def _prepare_embeddings_for_indexing(
        self, 
        embeddings: List[EmbeddingResponse]
    ) -> List[Dict[str, Any]]:
        """Prepare embeddings for Matching Engine indexing format."""
        data = []
        for i, emb in enumerate(embeddings):
            item = {
                "id": emb.embedding_id,
                "embedding": emb.embedding,
                "metadata": {
                    "text": emb.text,
                    "created_at": emb.created_at.isoformat(),
                    **emb.metadata
                }
            }
            data.append(item)
        return data
    
    def _upload_embeddings_to_gcs(
        self, 
        embeddings_data: List[Dict[str, Any]], 
        bucket_name: str, 
        blob_path: str
    ) -> None:
        """Upload embeddings data to GCS."""
        bucket = self.storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        # Convert to JSONL format
        jsonl_data = "\n".join([json.dumps(item) for item in embeddings_data])
        blob.upload_from_string(jsonl_data)
    
    def _process_matches_to_context(
        self, 
        matches: List[Any], 
        query: str
    ) -> RAGContext:
        """Process Matching Engine matches into RAG context."""
        relevant_schemas = []
        similar_queries = []
        domain_knowledge = []
        
        for match in matches:
            metadata = match.metadata
            similarity_score = 1.0 - match.distance  # Convert distance to similarity
            
            if metadata.get("type") == "schema":
                relevant_schemas.append({
                    "schema": metadata.get("schema_data", {}),
                    "relevance_score": similarity_score,
                    "table_name": metadata.get("table_name", "")
                })
            elif metadata.get("type") == "query":
                similar_queries.append({
                    "natural_language": metadata.get("text", ""),
                    "sql_query": metadata.get("sql_query", ""),
                    "similarity_score": similarity_score
                })
        
        # Calculate confidence
        confidence_score = np.mean([1.0 - match.distance for match in matches]) if matches else 0.0
        
        return RAGContext(
            relevant_schemas=relevant_schemas,
            similar_queries=similar_queries,
            domain_knowledge=domain_knowledge,
            confidence_score=float(confidence_score),
            retrieval_metadata={
                "matches_count": len(matches),
                "query": query
            }
        )
    
    def _generate_schema_description(self, schema: Dict[str, Any]) -> str:
        """Generate human-readable description of schema."""
        table_name = schema.get('table_name', 'Unknown')
        columns = schema.get('columns', [])
        
        if not columns:
            return f"Table {table_name} with no column information"
        
        column_names = [col.get('name', '') for col in columns[:5]]  # First 5 columns
        column_str = ", ".join(column_names)
        
        if len(columns) > 5:
            column_str += f" and {len(columns) - 5} more columns"
        
        return f"Table {table_name} with columns: {column_str}"
    
    def _extract_domain_knowledge(
        self, 
        schemas: List[Dict[str, Any]], 
        queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract domain knowledge from schemas and queries."""
        knowledge = []
        
        # Extract common patterns from successful queries
        successful_queries = [q for q in queries if q.get('success', False)]
        if successful_queries:
            knowledge.append({
                "type": "pattern",
                "description": "Common successful query patterns",
                "examples": [q['sql_query'] for q in successful_queries[:3]]
            })
        
        # Extract table relationships
        table_names = [s['table_name'] for s in schemas if s.get('table_name')]
        if len(table_names) > 1:
            knowledge.append({
                "type": "relationships",
                "description": "Available tables for potential joins",
                "tables": table_names
            })
        
        return knowledge
    
    def _calculate_context_confidence(
        self, 
        schemas: List[Dict[str, Any]], 
        queries: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence score for context."""
        if not schemas and not queries:
            return 0.0
        
        # Average relevance scores
        schema_scores = [s.get('relevance_score', 0.0) for s in schemas]
        query_scores = [q.get('similarity_score', 0.0) for q in queries]
        
        all_scores = schema_scores + query_scores
        return np.mean(all_scores) if all_scores else 0.0


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize services
    embeddings_service = EmbeddingsService(PROJECT_ID)
    rag_service = MatchingEngineRAGService(PROJECT_ID, embeddings_service=embeddings_service)
    
    # Example: Create index
    try:
        index = rag_service.create_index(
            "conversational-schemas",
            "Conversational Query Schemas",
            dimensions=768
        )
        print(f"Created index: {index.display_name}")
    except Exception as e:
        print(f"Error creating index: {e}")
    
    # Example: Build enhanced context
    query = "Show me customer revenue trends"
    try:
        context = rag_service.build_enhanced_context(
            query, 
            schema_embeddings=[], 
            query_embeddings=[]
        )
        print(f"Built context with confidence: {context.confidence_score}")
    except Exception as e:
        print(f"Error building context: {e}")