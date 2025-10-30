"""Conversational Query Integration Service

This module provides a high-level integration service that coordinates all
Phase 3 components for end-to-end conversational querying functionality.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import uuid

from .text_to_sql import TextToSQLService, SQLGenerationRequest, SQLGenerationResponse
from .embeddings import EmbeddingsService, EmbeddingRequest, EmbeddingResponse
from .matching_engine import MatchingEngineRAGService, RAGContext
from .query_validator import BigQueryValidationService, QueryValidationResult, QueryExecutionResult
from .models import ConversationalQueryDAO, QueryStatus, RiskLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConversationalQueryRequest:
    """Comprehensive request for conversational querying."""
    natural_language_query: str
    session_id: str
    user_id: str
    max_results: int = 1000
    include_explanation: bool = True
    force_execution: bool = False
    save_results: bool = True
    dataset_context: Optional[List[str]] = None
    user_context: Optional[Dict[str, Any]] = None


@dataclass
class ConversationalQueryResponse:
    """Comprehensive response for conversational querying."""
    query_id: str
    session_id: str
    status: str
    
    # Query generation
    natural_language_query: str
    generated_sql: Optional[str]
    explanation: Optional[str]
    confidence_score: Optional[float]
    
    # Validation
    validation_result: Optional[QueryValidationResult]
    risk_level: Optional[str]
    
    # Execution
    execution_result: Optional[QueryExecutionResult]
    
    # Context and suggestions
    rag_context: Optional[RAGContext]
    suggested_follow_ups: Optional[List[str]]
    similar_queries: Optional[List[Dict[str, Any]]]
    
    # Metadata
    processing_time: float
    cost_estimate: Optional[float]
    warnings: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]


class ConversationalQueryService:
    """High-level service for conversational querying."""
    
    def __init__(
        self, 
        project_id: str,
        location: str = "us-central1",
        dao: Optional[ConversationalQueryDAO] = None
    ):
        """Initialize the conversational query service.
        
        Args:
            project_id: GCP project ID
            location: GCP location
            dao: Database access object
        """
        self.project_id = project_id
        self.location = location
        self.dao = dao
        
        # Initialize component services
        self.text_to_sql = TextToSQLService(project_id, location)
        self.embeddings = EmbeddingsService(project_id, location)
        self.rag_service = MatchingEngineRAGService(project_id, location, self.embeddings)
        self.validator = BigQueryValidationService(project_id, location)
        
        # Cache for embeddings
        self._schema_embeddings_cache: Dict[str, List[EmbeddingResponse]] = {}
        self._query_embeddings_cache: Dict[str, List[EmbeddingResponse]] = {}
        
        logger.info(f"Initialized ConversationalQueryService for project {project_id}")
    
    async def process_query(self, request: ConversationalQueryRequest) -> ConversationalQueryResponse:
        """Process a conversational query end-to-end.
        
        Args:
            request: Conversational query request
            
        Returns:
            Complete query response with all processing results
        """
        start_time = datetime.now()
        warnings = []
        recommendations = []
        
        try:
            logger.info(f"Processing conversational query: {request.natural_language_query[:100]}...")
            
            # Step 1: Create query record if DAO available
            query_record = None
            if self.dao:
                query_record = self.dao.create_query(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    natural_language_query=request.natural_language_query
                )
                query_id = str(query_record.id)
            else:
                query_id = str(uuid.uuid4())
            
            # Step 2: Build RAG context
            rag_context = await self._build_rag_context(request)
            
            # Step 3: Generate SQL with enhanced context
            sql_response = await self._generate_sql_with_context(request, rag_context)
            
            # Step 4: Validate generated SQL
            validation_result = None
            if sql_response.sql_query:
                validation_result = self.validator.validate_query(
                    sql_response.sql_query,
                    context={
                        "user_id": request.user_id,
                        "session_id": request.session_id,
                        "confidence_score": sql_response.confidence_score
                    }
                )
                warnings.extend(validation_result.warnings)
                recommendations.extend(validation_result.recommendations)
            
            # Step 5: Execute if safe and conditions met
            execution_result = None
            if (validation_result and 
                validation_result.is_safe and 
                (sql_response.confidence_score > 0.7 or request.force_execution)):
                
                execution_result = self.validator.execute_query_safely(
                    sql_response.sql_query,
                    validation_result,
                    request.max_results
                )
            
            # Step 6: Update database record
            if self.dao and query_record:
                await self._update_query_record(
                    query_record, sql_response, validation_result, execution_result
                )
            
            # Step 7: Generate follow-up suggestions
            follow_ups = await self._generate_follow_ups(sql_response, rag_context)
            
            # Step 8: Find similar queries
            similar_queries = await self._find_similar_queries(request, rag_context)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Build comprehensive response
            response = ConversationalQueryResponse(
                query_id=query_id,
                session_id=request.session_id,
                status=self._determine_final_status(sql_response, validation_result, execution_result),
                natural_language_query=request.natural_language_query,
                generated_sql=sql_response.sql_query if sql_response else None,
                explanation=sql_response.explanation if sql_response else None,
                confidence_score=sql_response.confidence_score if sql_response else None,
                validation_result=validation_result,
                risk_level=validation_result.risk_level.value if validation_result else None,
                execution_result=execution_result,
                rag_context=rag_context,
                suggested_follow_ups=follow_ups,
                similar_queries=similar_queries,
                processing_time=processing_time,
                cost_estimate=execution_result.cost_estimate if execution_result else validation_result.estimated_cost if validation_result else None,
                warnings=warnings,
                recommendations=recommendations,
                metadata={
                    "processed_at": datetime.now().isoformat(),
                    "project_id": self.project_id,
                    "rag_confidence": rag_context.confidence_score if rag_context else 0.0,
                    "auto_executed": execution_result is not None and execution_result.success
                }
            )
            
            logger.info(f"Completed query processing in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process conversational query: {str(e)}")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            return ConversationalQueryResponse(
                query_id=query_id if 'query_id' in locals() else str(uuid.uuid4()),
                session_id=request.session_id,
                status=QueryStatus.FAILED.value,
                natural_language_query=request.natural_language_query,
                generated_sql=None,
                explanation=None,
                confidence_score=None,
                validation_result=None,
                risk_level=None,
                execution_result=None,
                rag_context=None,
                suggested_follow_ups=None,
                similar_queries=None,
                processing_time=processing_time,
                cost_estimate=None,
                warnings=[],
                recommendations=[],
                metadata={
                    "error": str(e),
                    "failed_at": datetime.now().isoformat()
                }
            )
    
    async def _build_rag_context(self, request: ConversationalQueryRequest) -> RAGContext:
        """Build RAG context for enhanced query generation."""
        try:
            # Get or create schema embeddings
            schema_embeddings = await self._get_schema_embeddings(request.dataset_context)
            
            # Get or create query embeddings for user
            query_embeddings = await self._get_query_embeddings(request.user_id)
            
            # Build enhanced context
            rag_context = self.rag_service.build_enhanced_context(
                request.natural_language_query,
                schema_embeddings,
                query_embeddings,
                additional_context=request.user_context
            )
            
            return rag_context
            
        except Exception as e:
            logger.warning(f"Failed to build RAG context: {e}")
            return RAGContext(
                relevant_schemas=[],
                similar_queries=[],
                domain_knowledge=[],
                confidence_score=0.0,
                retrieval_metadata={"error": str(e)}
            )
    
    async def _generate_sql_with_context(
        self, 
        request: ConversationalQueryRequest, 
        rag_context: RAGContext
    ) -> SQLGenerationResponse:
        """Generate SQL with RAG-enhanced context."""
        try:
            # Prepare schemas from RAG context
            schemas = []
            for schema_context in rag_context.relevant_schemas:
                schemas.append(schema_context.get('schema', {}))
            
            # Add default schemas if no relevant ones found
            if not schemas:
                schemas = self._get_default_schemas()
            
            # Build SQL generation request
            sql_request = SQLGenerationRequest(
                natural_language_query=request.natural_language_query,
                dataset_schemas=schemas,
                user_context={
                    "user_id": request.user_id,
                    "session_id": request.session_id,
                    "similar_queries": rag_context.similar_queries[:3],
                    "domain_knowledge": rag_context.domain_knowledge,
                    "rag_confidence": rag_context.confidence_score
                },
                max_results=request.max_results
            )
            
            # Generate SQL
            return self.text_to_sql.generate_sql(sql_request)
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            raise
    
    async def _update_query_record(
        self, 
        query_record: Any, 
        sql_response: SQLGenerationResponse,
        validation_result: Optional[QueryValidationResult],
        execution_result: Optional[QueryExecutionResult]
    ) -> None:
        """Update database query record with results."""
        try:
            # Determine final status
            if execution_result and execution_result.success:
                status = QueryStatus.COMPLETED
            elif execution_result and not execution_result.success:
                status = QueryStatus.FAILED
            elif validation_result and not validation_result.is_safe:
                status = QueryStatus.BLOCKED
            else:
                status = QueryStatus.VALIDATED
            
            # Update record
            update_data = {
                "generated_sql": sql_response.sql_query,
                "explanation": sql_response.explanation,
                "confidence_score": sql_response.confidence_score,
                "risk_level": validation_result.risk_level.value if validation_result else None
            }
            
            if execution_result:
                update_data.update({
                    "query_job_id": execution_result.query_job_id,
                    "rows_returned": execution_result.rows_returned,
                    "bytes_processed": execution_result.bytes_processed,
                    "execution_time": execution_result.execution_time,
                    "cost_estimate": execution_result.cost_estimate,
                    "results_preview": execution_result.results[:10] if execution_result.results else None,
                    "error_message": execution_result.error_message,
                    "executed_at": datetime.utcnow() if execution_result.success else None,
                    "completed_at": datetime.utcnow() if execution_result.success else None
                })
            
            self.dao.update_query_status(str(query_record.id), status, **update_data)
            
        except Exception as e:
            logger.error(f"Failed to update query record: {e}")
    
    async def _generate_follow_ups(
        self, 
        sql_response: SQLGenerationResponse, 
        rag_context: RAGContext
    ) -> List[str]:
        """Generate follow-up question suggestions."""
        try:
            if not sql_response or not sql_response.sql_query:
                return []
            
            # Extract schemas from RAG context
            schemas = []
            for schema_context in rag_context.relevant_schemas:
                schemas.append(schema_context.get('schema', {}))
            
            # Generate follow-ups using text-to-sql service
            follow_ups = self.text_to_sql.suggest_follow_up_queries(
                sql_response.explanation or "Previous query",
                sql_response.sql_query,
                schemas
            )
            
            return [fup.get('question', '') for fup in follow_ups[:5]]
            
        except Exception as e:
            logger.warning(f"Failed to generate follow-ups: {e}")
            return []
    
    async def _find_similar_queries(
        self, 
        request: ConversationalQueryRequest, 
        rag_context: RAGContext
    ) -> List[Dict[str, Any]]:
        """Find similar queries from RAG context."""
        try:
            similar_queries = []
            
            for query_context in rag_context.similar_queries[:3]:
                similar_queries.append({
                    "natural_language": query_context.get('natural_language', ''),
                    "sql_query": query_context.get('sql_query', ''),
                    "similarity_score": query_context.get('similarity_score', 0.0),
                    "explanation": query_context.get('explanation', '')
                })
            
            return similar_queries
            
        except Exception as e:
            logger.warning(f"Failed to find similar queries: {e}")
            return []
    
    async def _get_schema_embeddings(self, dataset_context: Optional[List[str]]) -> List[EmbeddingResponse]:
        """Get or create schema embeddings."""
        try:
            cache_key = ",".join(sorted(dataset_context)) if dataset_context else "default"
            
            if cache_key in self._schema_embeddings_cache:
                return self._schema_embeddings_cache[cache_key]
            
            # In production, this would load schemas from your dataset metadata service
            schemas = self._get_schemas_for_datasets(dataset_context)
            
            # Generate embeddings
            embeddings = self.embeddings.embed_dataset_schemas(schemas)
            
            # Cache results
            self._schema_embeddings_cache[cache_key] = embeddings
            
            return embeddings
            
        except Exception as e:
            logger.warning(f"Failed to get schema embeddings: {e}")
            return []
    
    async def _get_query_embeddings(self, user_id: str) -> List[EmbeddingResponse]:
        """Get or create query embeddings for user."""
        try:
            if user_id in self._query_embeddings_cache:
                return self._query_embeddings_cache[user_id]
            
            # In production, this would load query history from database
            if self.dao:
                recent_queries = self.dao.get_user_queries(user_id, limit=50)
                query_data = [
                    {
                        "id": str(q.id),
                        "natural_language_query": q.natural_language_query,
                        "sql_query": q.generated_sql,
                        "explanation": q.explanation,
                        "success": q.status == QueryStatus.COMPLETED.value
                    }
                    for q in recent_queries
                    if q.natural_language_query
                ]
            else:
                query_data = []
            
            # Generate embeddings
            embeddings = self.embeddings.embed_query_history(query_data)
            
            # Cache results
            self._query_embeddings_cache[user_id] = embeddings
            
            return embeddings
            
        except Exception as e:
            logger.warning(f"Failed to get query embeddings: {e}")
            return []
    
    def _get_schemas_for_datasets(self, dataset_context: Optional[List[str]]) -> List[Dict[str, Any]]:
        """Get schemas for specified datasets."""
        # In production, this would integrate with your dataset metadata service
        # For now, return example schemas
        return [
            {
                "table_name": "customers",
                "description": "Customer master data",
                "columns": [
                    {"name": "customer_id", "type": "STRING", "description": "Unique customer identifier"},
                    {"name": "name", "type": "STRING", "description": "Customer name"},
                    {"name": "email", "type": "STRING", "description": "Customer email address"},
                    {"name": "signup_date", "type": "DATE", "description": "Customer signup date"},
                    {"name": "total_spent", "type": "FLOAT", "description": "Total amount spent"}
                ]
            },
            {
                "table_name": "orders",
                "description": "Order transaction data",
                "columns": [
                    {"name": "order_id", "type": "STRING", "description": "Unique order identifier"},
                    {"name": "customer_id", "type": "STRING", "description": "Customer who placed order"},
                    {"name": "order_date", "type": "DATE", "description": "Order placement date"},
                    {"name": "amount", "type": "FLOAT", "description": "Order total amount"},
                    {"name": "status", "type": "STRING", "description": "Order status"}
                ]
            }
        ]
    
    def _get_default_schemas(self) -> List[Dict[str, Any]]:
        """Get default schemas when no specific context is provided."""
        return self._get_schemas_for_datasets(None)
    
    def _determine_final_status(
        self,
        sql_response: Optional[SQLGenerationResponse],
        validation_result: Optional[QueryValidationResult],
        execution_result: Optional[QueryExecutionResult]
    ) -> str:
        """Determine the final status of the query."""
        if execution_result:
            return QueryStatus.COMPLETED.value if execution_result.success else QueryStatus.FAILED.value
        elif validation_result:
            if not validation_result.is_safe:
                return QueryStatus.BLOCKED.value
            else:
                return QueryStatus.VALIDATED.value
        elif sql_response and sql_response.sql_query:
            return QueryStatus.PENDING.value
        else:
            return QueryStatus.FAILED.value
    
    # Additional utility methods
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get context for a conversational session."""
        try:
            if self.dao:
                session = self.dao.create_or_get_session(session_id, "placeholder_user")
                recent_queries = self.dao.get_session_queries(session_id, limit=10)
                
                return {
                    "session_id": session_id,
                    "query_count": len(recent_queries),
                    "recent_topics": self._extract_topics_from_queries(recent_queries),
                    "avg_confidence": sum(q.confidence_score or 0 for q in recent_queries) / len(recent_queries) if recent_queries else 0,
                    "total_cost": sum(q.cost_estimate or 0 for q in recent_queries)
                }
            else:
                return {"session_id": session_id, "query_count": 0}
                
        except Exception as e:
            logger.error(f"Failed to get session context: {e}")
            return {"session_id": session_id, "error": str(e)}
    
    def _extract_topics_from_queries(self, queries: List[Any]) -> List[str]:
        """Extract topics from recent queries."""
        # Simple topic extraction - in production, use more sophisticated NLP
        topics = set()
        for query in queries:
            if query.natural_language_query:
                words = query.natural_language_query.lower().split()
                # Extract potential table/entity names
                for word in words:
                    if word in ['customer', 'customers', 'order', 'orders', 'product', 'products', 'revenue', 'sales']:
                        topics.add(word)
        
        return list(topics)[:5]


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Example configuration
    PROJECT_ID = "your-project-id"
    
    # Initialize service
    service = ConversationalQueryService(PROJECT_ID)
    
    # Example request
    request = ConversationalQueryRequest(
        natural_language_query="Show me the top 10 customers by total spending this year",
        session_id="session_123",
        user_id="user_456",
        max_results=10,
        include_explanation=True
    )
    
    async def test_service():
        try:
            response = await service.process_query(request)
            print(f"Query ID: {response.query_id}")
            print(f"Status: {response.status}")
            print(f"Generated SQL: {response.generated_sql}")
            print(f"Confidence: {response.confidence_score}")
            print(f"Processing time: {response.processing_time:.2f}s")
            
            if response.execution_result and response.execution_result.success:
                print(f"Rows returned: {response.execution_result.rows_returned}")
                print(f"Cost: ${response.cost_estimate:.4f}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Run test
    asyncio.run(test_service())