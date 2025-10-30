"""Conversational Querying Module

Phase 3 implementation providing natural language-driven data exploration
through Vertex AI integration, RAG enhancement, and safe query execution.
"""

__version__ = "1.0.0"
__author__ = "AI Data Analyst Team"

# Main service exports
from .service import ConversationalQueryService, ConversationalQueryRequest, ConversationalQueryResponse
from .text_to_sql import TextToSQLService, SQLGenerationRequest, SQLGenerationResponse
from .embeddings import EmbeddingsService, EmbeddingRequest, EmbeddingResponse
from .matching_engine import MatchingEngineRAGService, RAGContext
from .query_validator import BigQueryValidationService, QueryValidationResult, QueryExecutionResult
from .models import (
    ConversationalQuery, 
    QueryValidation,
    QueryEmbedding,
    QueryResult,
    QuerySession,
    QueryFeedback,
    ConversationalQueryDAO,
    QueryStatus,
    RiskLevel
)

__all__ = [
    # Main service
    "ConversationalQueryService",
    "ConversationalQueryRequest", 
    "ConversationalQueryResponse",
    
    # Component services
    "TextToSQLService",
    "EmbeddingsService", 
    "MatchingEngineRAGService",
    "BigQueryValidationService",
    
    # Request/Response models
    "SQLGenerationRequest",
    "SQLGenerationResponse",
    "EmbeddingRequest",
    "EmbeddingResponse", 
    "RAGContext",
    "QueryValidationResult",
    "QueryExecutionResult",
    
    # Database models
    "ConversationalQuery",
    "QueryValidation",
    "QueryEmbedding", 
    "QueryResult",
    "QuerySession",
    "QueryFeedback",
    "ConversationalQueryDAO",
    
    # Enums
    "QueryStatus",
    "RiskLevel"
]

# Module metadata
PHASE = 3
COMPONENT_NAME = "Conversational Querying"
DESCRIPTION = "Natural language-driven data exploration with AI-powered SQL generation"

# Feature flags (for production deployment)
FEATURES = {
    "text_to_sql": True,
    "embeddings": True, 
    "rag_enhancement": True,
    "query_validation": True,
    "safe_execution": True,
    "session_management": True,
    "feedback_collection": True
}

# Default configuration
DEFAULT_CONFIG = {
    "project_id": None,  # Must be set
    "location": "us-central1",
    "model_name": "gemini-1.5-pro",
    "embedding_model": "textembedding-gecko@003",
    "max_cost_threshold": 10.0,  # USD
    "max_execution_time": 300,   # seconds
    "max_results_default": 1000,
    "confidence_threshold": 0.7,
    "similarity_threshold": 0.6
}

def get_version_info():
    """Get comprehensive version and feature information."""
    return {
        "version": __version__,
        "phase": PHASE,
        "component": COMPONENT_NAME,
        "description": DESCRIPTION,
        "features": FEATURES,
        "author": __author__
    }

def validate_config(config):
    """Validate conversational querying configuration."""
    required_fields = ["project_id"]
    
    for field in required_fields:
        if not config.get(field):
            raise ValueError(f"Required configuration field missing: {field}")
    
    # Validate numeric thresholds
    if config.get("max_cost_threshold", 0) <= 0:
        raise ValueError("max_cost_threshold must be positive")
    
    if config.get("max_execution_time", 0) <= 0:
        raise ValueError("max_execution_time must be positive")
    
    if not 0 <= config.get("confidence_threshold", 0.7) <= 1:
        raise ValueError("confidence_threshold must be between 0 and 1")
    
    return True

# Quick start helper
def create_conversational_service(project_id, **kwargs):
    """Quick start helper to create a conversational query service.
    
    Args:
        project_id: GCP project ID
        **kwargs: Additional configuration options
        
    Returns:
        ConversationalQueryService instance
    """
    config = DEFAULT_CONFIG.copy()
    config["project_id"] = project_id
    config.update(kwargs)
    
    validate_config(config)
    
    return ConversationalQueryService(
        project_id=config["project_id"],
        location=config["location"]
    )

# Example usage
def example_usage():
    """Example usage of the conversational querying system."""
    return """
    # Basic usage example
    from conversational import create_conversational_service, ConversationalQueryRequest
    
    # Initialize service
    service = create_conversational_service("your-project-id")
    
    # Create query request
    request = ConversationalQueryRequest(
        natural_language_query="Show me the top 10 customers by revenue",
        session_id="session_123",
        user_id="user_456"
    )
    
    # Process query
    response = await service.process_query(request)
    
    print(f"Generated SQL: {response.generated_sql}")
    print(f"Status: {response.status}")
    print(f"Confidence: {response.confidence_score}")
    """

if __name__ == "__main__":
    print(f"Conversational Querying Module v{__version__}")
    print(f"Phase {PHASE}: {COMPONENT_NAME}")
    print(f"Features: {', '.join(k for k, v in FEATURES.items() if v)}")
    print("\nExample usage:")
    print(example_usage())