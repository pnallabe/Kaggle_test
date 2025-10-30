"""Conversational Query API Endpoints

This module provides REST API endpoints for conversational querying functionality
including natural language to SQL conversion, query execution, and result management.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query as QueryParam
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import asyncio

# Import conversational services
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conversational.text_to_sql import TextToSQLService, SQLGenerationRequest, SQLGenerationResponse
from conversational.embeddings import EmbeddingsService
from conversational.matching_engine import MatchingEngineRAGService
from conversational.query_validator import BigQueryValidationService, QueryValidationResult, QueryExecutionResult
from conversational.models import ConversationalQueryDAO, QueryStatus, RiskLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/conversational", tags=["Conversational Queries"])

# Pydantic models for API
class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language queries."""
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language query")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_id: str = Field(..., description="User identifier")
    max_results: int = Field(1000, ge=1, le=10000, description="Maximum number of results")
    include_explanation: bool = Field(True, description="Whether to include SQL explanation")
    dataset_context: Optional[List[str]] = Field(None, description="Specific datasets to query")
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if v is None:
            return str(uuid.uuid4())
        return v


class QueryResponse(BaseModel):
    """Response model for query results."""
    query_id: str
    session_id: str
    natural_language_query: str
    generated_sql: Optional[str]
    explanation: Optional[str]
    status: str
    risk_level: Optional[str]
    confidence_score: Optional[float]
    validation: Optional[Dict[str, Any]]
    execution: Optional[Dict[str, Any]]
    results_preview: Optional[List[Dict[str, Any]]]
    suggested_follow_ups: Optional[List[str]]
    warnings: Optional[List[str]]
    recommendations: Optional[List[str]]
    metadata: Dict[str, Any]


class QueryExecutionRequest(BaseModel):
    """Request model for query execution."""
    query_id: str = Field(..., description="Query ID to execute")
    force_execution: bool = Field(False, description="Force execution despite warnings")
    save_results: bool = Field(True, description="Whether to save full results")


class SessionResponse(BaseModel):
    """Response model for query sessions."""
    session_id: str
    user_id: str
    title: Optional[str]
    query_count: int
    total_cost: float
    is_active: bool
    created_at: str
    last_activity: str
    recent_queries: List[Dict[str, Any]]


class FeedbackRequest(BaseModel):
    """Request model for query feedback."""
    query_id: str
    feedback_type: str = Field(..., regex="^(helpful|incorrect|improvement)$")
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = Field(None, max_length=1000)
    sql_accuracy: Optional[int] = Field(None, ge=1, le=5)
    result_relevance: Optional[int] = Field(None, ge=1, le=5)
    explanation_clarity: Optional[int] = Field(None, ge=1, le=5)


# Service dependencies (these would be injected via FastAPI dependency injection in production)
class ConversationalServices:
    """Container for conversational services."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.text_to_sql = TextToSQLService(project_id)
        self.embeddings = EmbeddingsService(project_id)
        self.rag_service = MatchingEngineRAGService(project_id, embeddings_service=self.embeddings)
        self.validator = BigQueryValidationService(project_id)


# Global services instance (in production, use proper dependency injection)
PROJECT_ID = os.getenv("PROJECT_ID", "your-project-id")
services = ConversationalServices(PROJECT_ID)


# Dependency to get database session (placeholder - implement based on your DB setup)
def get_db():
    """Get database session (placeholder)."""
    # In production, implement proper database session management
    pass


def get_conversational_dao():
    """Get conversational query DAO (placeholder)."""
    # In production, implement proper DAO injection
    pass


@router.post("/query", response_model=QueryResponse)
async def create_natural_language_query(
    request: NaturalLanguageQueryRequest,
    background_tasks: BackgroundTasks,
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Create and process a natural language query.
    
    This endpoint accepts a natural language query, converts it to SQL,
    validates it, and optionally executes it with proper safety checks.
    """
    try:
        logger.info(f"Processing natural language query: {request.query[:100]}...")
        
        # Create query record
        query_record = dao.create_query(
            session_id=request.session_id,
            user_id=request.user_id,
            natural_language_query=request.query
        )
        
        # Generate SQL using RAG-enhanced context
        background_tasks.add_task(
            process_query_with_rag,
            str(query_record.id),
            request,
            dao
        )
        
        # Return initial response
        return QueryResponse(
            query_id=str(query_record.id),
            session_id=request.session_id,
            natural_language_query=request.query,
            generated_sql=None,
            explanation=None,
            status=QueryStatus.PENDING.value,
            risk_level=None,
            confidence_score=None,
            validation=None,
            execution=None,
            results_preview=None,
            suggested_follow_ups=None,
            warnings=None,
            recommendations=None,
            metadata={
                "created_at": query_record.created_at.isoformat(),
                "processing_started": True
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


async def process_query_with_rag(
    query_id: str, 
    request: NaturalLanguageQueryRequest,
    dao: ConversationalQueryDAO
):
    """Background task to process query with RAG enhancement."""
    try:
        # Get dataset schemas for context
        # In production, this would fetch from your dataset metadata
        example_schemas = [
            {
                "table_name": "customers",
                "columns": [
                    {"name": "customer_id", "type": "STRING", "description": "Unique customer identifier"},
                    {"name": "name", "type": "STRING", "description": "Customer name"},
                    {"name": "email", "type": "STRING", "description": "Customer email address"},
                    {"name": "total_spent", "type": "FLOAT", "description": "Total amount spent by customer"}
                ]
            }
        ]
        
        # Get similar queries and schema embeddings for RAG
        schema_embeddings = []  # In production, load from database
        query_embeddings = []   # In production, load from database
        
        # Build enhanced context
        rag_context = services.rag_service.build_enhanced_context(
            request.query,
            schema_embeddings,
            query_embeddings
        )
        
        # Generate SQL with enhanced context
        sql_request = SQLGenerationRequest(
            natural_language_query=request.query,
            dataset_schemas=example_schemas,
            user_context={
                "user_id": request.user_id,
                "session_id": request.session_id,
                "rag_context": rag_context.retrieval_metadata
            },
            max_results=request.max_results
        )
        
        sql_response = services.text_to_sql.generate_sql(sql_request)
        
        # Validate generated SQL
        validation_result = services.validator.validate_query(sql_response.sql_query)
        
        # Update query record
        dao.update_query_status(
            query_id,
            QueryStatus.VALIDATED,
            generated_sql=sql_response.sql_query,
            explanation=sql_response.explanation,
            confidence_score=sql_response.confidence_score,
            risk_level=validation_result.risk_level.value
        )
        
        # Auto-execute if safe and high confidence
        if validation_result.is_safe and sql_response.confidence_score > 0.8:
            execution_result = services.validator.execute_query_safely(
                sql_response.sql_query,
                validation_result,
                request.max_results
            )
            
            if execution_result.success:
                # Update with execution results
                dao.update_query_status(
                    query_id,
                    QueryStatus.COMPLETED,
                    query_job_id=execution_result.query_job_id,
                    rows_returned=execution_result.rows_returned,
                    bytes_processed=execution_result.bytes_processed,
                    execution_time=execution_result.execution_time,
                    cost_estimate=execution_result.cost_estimate,
                    results_preview=execution_result.results[:10] if execution_result.results else None,
                    executed_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )
            else:
                dao.update_query_status(
                    query_id,
                    QueryStatus.FAILED,
                    error_message=execution_result.error_message
                )
        
        logger.info(f"Completed processing query {query_id}")
        
    except Exception as e:
        logger.error(f"Failed to process query {query_id}: {str(e)}")
        dao.update_query_status(
            query_id,
            QueryStatus.FAILED,
            error_message=str(e)
        )


@router.get("/query/{query_id}", response_model=QueryResponse)
async def get_query_status(
    query_id: str,
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Get the current status and results of a query."""
    try:
        query = dao.get_query(query_id)
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        # Build response
        return QueryResponse(
            query_id=str(query.id),
            session_id=query.session_id,
            natural_language_query=query.natural_language_query,
            generated_sql=query.generated_sql,
            explanation=query.explanation,
            status=query.status,
            risk_level=query.risk_level,
            confidence_score=query.confidence_score,
            validation={
                "is_valid": query.validation.is_valid if query.validation else None,
                "is_safe": query.validation.is_safe if query.validation else None,
                "warnings": query.validation.warnings if query.validation else None,
                "errors": query.validation.errors if query.validation else None
            } if query.validation else None,
            execution={
                "rows_returned": query.rows_returned,
                "bytes_processed": query.bytes_processed,
                "execution_time": query.execution_time,
                "cost_estimate": query.cost_estimate,
                "job_id": query.query_job_id
            } if query.status in [QueryStatus.COMPLETED.value, QueryStatus.FAILED.value] else None,
            results_preview=query.results_preview,
            suggested_follow_ups=None,  # Could be generated based on results
            warnings=query.validation.warnings if query.validation else None,
            recommendations=query.validation.recommendations if query.validation else None,
            metadata={
                "created_at": query.created_at.isoformat(),
                "updated_at": query.updated_at.isoformat(),
                "executed_at": query.executed_at.isoformat() if query.executed_at else None,
                "completed_at": query.completed_at.isoformat() if query.completed_at else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get query status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get query status: {str(e)}")


@router.post("/query/{query_id}/execute")
async def execute_query(
    query_id: str,
    request: QueryExecutionRequest,
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Execute a validated query."""
    try:
        query = dao.get_query(query_id)
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        if not query.generated_sql:
            raise HTTPException(status_code=400, detail="Query has no generated SQL")
        
        # Re-validate if needed
        validation_result = services.validator.validate_query(query.generated_sql)
        
        if not validation_result.is_safe and not request.force_execution:
            raise HTTPException(
                status_code=400, 
                detail="Query is not safe to execute. Use force_execution=true to override."
            )
        
        # Execute query
        execution_result = services.validator.execute_query_safely(
            query.generated_sql,
            validation_result,
            1000  # Max results
        )
        
        if execution_result.success:
            # Update query with results
            dao.update_query_status(
                query_id,
                QueryStatus.COMPLETED,
                query_job_id=execution_result.query_job_id,
                rows_returned=execution_result.rows_returned,
                bytes_processed=execution_result.bytes_processed,
                execution_time=execution_result.execution_time,
                cost_estimate=execution_result.cost_estimate,
                results_preview=execution_result.results[:10] if execution_result.results else None,
                executed_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            # Save full results if requested
            if request.save_results and execution_result.results:
                dao.add_query_result(
                    query_id,
                    "data",
                    "json",
                    execution_result.results,
                    row_count=execution_result.rows_returned
                )
            
            return {
                "success": True,
                "query_id": query_id,
                "rows_returned": execution_result.rows_returned,
                "execution_time": execution_result.execution_time,
                "cost_estimate": execution_result.cost_estimate,
                "results_preview": execution_result.results[:10] if execution_result.results else None
            }
        else:
            dao.update_query_status(
                query_id,
                QueryStatus.FAILED,
                error_message=execution_result.error_message
            )
            
            return {
                "success": False,
                "query_id": query_id,
                "error": execution_result.error_message
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to execute query: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Get session information and recent queries."""
    try:
        session = dao.create_or_get_session(session_id, "placeholder_user")  # In production, get from auth
        queries = dao.get_session_queries(session_id, limit=20)
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            title=session.title,
            query_count=session.query_count,
            total_cost=session.total_cost,
            is_active=session.is_active,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            recent_queries=[q.to_dict() for q in queries]
        )
        
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    user_id: str = QueryParam(..., description="User ID"),
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Submit feedback for a query."""
    try:
        feedback = dao.add_feedback(
            request.query_id,
            user_id,
            request.feedback_type,
            rating=request.rating,
            feedback_text=request.feedback_text,
            sql_accuracy=request.sql_accuracy,
            result_relevance=request.result_relevance,
            explanation_clarity=request.explanation_clarity
        )
        
        return {
            "success": True,
            "feedback_id": str(feedback.id),
            "message": "Feedback submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.get("/query/{query_id}/similar")
async def get_similar_queries(
    query_id: str,
    limit: int = QueryParam(5, ge=1, le=20),
    dao: ConversationalQueryDAO = Depends(get_conversational_dao)
):
    """Get similar queries based on embeddings."""
    try:
        query = dao.get_query(query_id)
        if not query:
            raise HTTPException(status_code=404, detail="Query not found")
        
        # In production, this would use the embeddings service to find similar queries
        similar_queries = dao.get_similar_queries(query.user_id, limit)
        
        return {
            "query_id": query_id,
            "similar_queries": [
                {
                    "id": str(q.id),
                    "natural_language_query": q.natural_language_query,
                    "generated_sql": q.generated_sql,
                    "confidence_score": q.confidence_score,
                    "created_at": q.created_at.isoformat()
                }
                for q in similar_queries
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get similar queries: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar queries: {str(e)}")


@router.get("/analytics/usage")
async def get_usage_analytics(
    days: int = QueryParam(7, ge=1, le=90),
    user_id: Optional[str] = QueryParam(None)
):
    """Get usage analytics for conversational queries."""
    try:
        # Get query statistics from validator
        stats = services.validator.get_query_statistics(days)
        
        # In production, add more detailed analytics from database
        return {
            "period_days": days,
            "bigquery_stats": stats,
            "conversational_stats": {
                "total_conversations": 0,  # Would query from database
                "avg_queries_per_session": 0,
                "most_common_query_types": [],
                "user_satisfaction_rating": 0
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for conversational query services."""
    try:
        # Test basic service connectivity
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "text_to_sql": "unknown",  # Would test actual service
                "embeddings": "unknown",
                "validator": "unknown",
                "database": "unknown"
            }
        }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }