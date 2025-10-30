"""Database Models for Conversational Querying System

This module defines SQLAlchemy models for storing conversational queries,
embeddings, validation results, and execution history.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid
import json

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Float, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import enum

Base = declarative_base()


class QueryStatus(enum.Enum):
    """Status of conversational queries."""
    PENDING = "pending"
    VALIDATED = "validated"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(enum.Enum):
    """Risk levels for queries."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConversationalQuery(Base):
    """Model for conversational queries and their lifecycle."""
    
    __tablename__ = "conversational_queries"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Query information
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    
    # Status and metadata
    status = Column(String(50), nullable=False, default=QueryStatus.PENDING.value)
    risk_level = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Execution details
    query_job_id = Column(String(255), nullable=True)
    rows_returned = Column(Integer, nullable=True)
    bytes_processed = Column(Integer, nullable=True)
    execution_time = Column(Float, nullable=True)
    cost_estimate = Column(Float, nullable=True)
    
    # Results and errors
    results_preview = Column(JSON, nullable=True)  # First few rows for preview
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Foreign keys
    validation_id = Column(UUID(as_uuid=True), ForeignKey('query_validations.id'), nullable=True)
    embedding_id = Column(UUID(as_uuid=True), ForeignKey('query_embeddings.id'), nullable=True)
    
    # Relationships
    validation = relationship("QueryValidation", back_populates="query")
    embedding = relationship("QueryEmbedding", back_populates="query")
    results = relationship("QueryResult", back_populates="query", cascade="all, delete-orphan")
    feedback = relationship("QueryFeedback", back_populates="query", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conv_queries_user_created', 'user_id', 'created_at'),
        Index('idx_conv_queries_session', 'session_id', 'created_at'),
        Index('idx_conv_queries_status', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': str(self.id),
            'session_id': self.session_id,
            'user_id': self.user_id,
            'natural_language_query': self.natural_language_query,
            'generated_sql': self.generated_sql,
            'explanation': self.explanation,
            'status': self.status,
            'risk_level': self.risk_level,
            'confidence_score': self.confidence_score,
            'query_job_id': self.query_job_id,
            'rows_returned': self.rows_returned,
            'bytes_processed': self.bytes_processed,
            'execution_time': self.execution_time,
            'cost_estimate': self.cost_estimate,
            'results_preview': self.results_preview,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class QueryValidation(Base):
    """Model for query validation results."""
    
    __tablename__ = "query_validations"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_hash = Column(String(255), nullable=False, index=True)  # Hash of SQL for caching
    
    # Validation results
    is_valid = Column(Boolean, nullable=False)
    is_safe = Column(Boolean, nullable=False)
    risk_level = Column(String(50), nullable=False)
    validation_status = Column(String(50), nullable=False)
    
    # Cost and performance estimates
    estimated_cost = Column(Float, nullable=True)
    estimated_runtime = Column(Float, nullable=True)
    bytes_processed = Column(Integer, nullable=True)
    
    # Issues and recommendations
    warnings = Column(JSON, nullable=True)  # List of warning messages
    errors = Column(JSON, nullable=True)    # List of error messages
    recommendations = Column(JSON, nullable=True)  # List of recommendations
    
    # Validation metadata
    validation_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ConversationalQuery", back_populates="validation")
    
    # Indexes
    __table_args__ = (
        Index('idx_validations_hash', 'query_hash'),
        Index('idx_validations_risk', 'risk_level'),
    )


class QueryEmbedding(Base):
    """Model for storing query embeddings for semantic search."""
    
    __tablename__ = "query_embeddings"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding_id = Column(String(255), nullable=False, unique=True)
    
    # Text and embedding
    text = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=False)  # Store as JSON array
    dimensions = Column(Integer, nullable=False)
    
    # Embedding metadata
    task_type = Column(String(100), nullable=False)
    model_name = Column(String(255), nullable=False)
    embedding_metadata = Column(JSON, nullable=True)
    
    # Context information
    context_type = Column(String(100), nullable=False)  # 'query', 'schema', 'domain_knowledge'
    context_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ConversationalQuery", back_populates="embedding")
    
    # Indexes
    __table_args__ = (
        Index('idx_embeddings_context', 'context_type'),
        Index('idx_embeddings_model', 'model_name'),
    )


class QueryResult(Base):
    """Model for storing query execution results."""
    
    __tablename__ = "query_results"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey('conversational_queries.id'), nullable=False)
    
    # Result metadata
    result_type = Column(String(100), nullable=False)  # 'data', 'visualization', 'summary'
    format = Column(String(50), nullable=False)  # 'json', 'csv', 'chart'
    
    # Result data
    data = Column(JSON, nullable=True)  # Actual result data
    data_url = Column(String(500), nullable=True)  # URL to stored result file
    row_count = Column(Integer, nullable=False, default=0)
    
    # Result metadata
    schema_info = Column(JSON, nullable=True)  # Column types and metadata
    result_metadata = Column(JSON, nullable=True)
    
    # Storage information
    storage_location = Column(String(500), nullable=True)  # GCS path or similar
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ConversationalQuery", back_populates="results")
    
    # Indexes
    __table_args__ = (
        Index('idx_results_query', 'query_id'),
        Index('idx_results_type', 'result_type'),
    )


class QuerySession(Base):
    """Model for conversational query sessions."""
    
    __tablename__ = "query_sessions"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Session information
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # Session context
    datasets_used = Column(JSON, nullable=True)  # List of dataset references
    session_context = Column(JSON, nullable=True)  # Session-specific context
    
    # Session statistics
    query_count = Column(Integer, nullable=False, default=0)
    total_cost = Column(Float, nullable=False, default=0.0)
    total_execution_time = Column(Float, nullable=False, default=0.0)
    
    # Session status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_sessions_user_active', 'user_id', 'is_active'),
        Index('idx_sessions_last_activity', 'last_activity'),
    )


class QueryFeedback(Base):
    """Model for user feedback on query results."""
    
    __tablename__ = "query_feedback"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey('conversational_queries.id'), nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Feedback information
    rating = Column(Integer, nullable=True)  # 1-5 scale
    feedback_type = Column(String(100), nullable=False)  # 'helpful', 'incorrect', 'improvement'
    feedback_text = Column(Text, nullable=True)
    
    # Specific feedback categories
    sql_accuracy = Column(Integer, nullable=True)  # 1-5 scale
    result_relevance = Column(Integer, nullable=True)  # 1-5 scale
    explanation_clarity = Column(Integer, nullable=True)  # 1-5 scale
    
    # Improvement suggestions
    suggested_improvements = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("ConversationalQuery", back_populates="feedback")
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_query', 'query_id'),
        Index('idx_feedback_user', 'user_id'),
        Index('idx_feedback_type', 'feedback_type'),
    )


class SchemaEmbedding(Base):
    """Model for storing dataset schema embeddings."""
    
    __tablename__ = "schema_embeddings"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embedding_id = Column(String(255), nullable=False, unique=True)
    
    # Schema reference
    dataset_id = Column(String(255), nullable=False, index=True)
    table_name = Column(String(255), nullable=False)
    
    # Embedding data
    schema_text = Column(Text, nullable=False)
    embedding_vector = Column(JSON, nullable=False)
    dimensions = Column(Integer, nullable=False)
    
    # Schema metadata
    column_count = Column(Integer, nullable=False)
    schema_metadata = Column(JSON, nullable=True)
    
    # Model information
    model_name = Column(String(255), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_schema_embeddings_dataset', 'dataset_id'),
        Index('idx_schema_embeddings_table', 'table_name'),
    )


# Database utility functions
class ConversationalQueryDAO:
    """Data Access Object for conversational queries."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_query(
        self, 
        session_id: str,
        user_id: str,
        natural_language_query: str,
        **kwargs
    ) -> ConversationalQuery:
        """Create a new conversational query."""
        query = ConversationalQuery(
            session_id=session_id,
            user_id=user_id,
            natural_language_query=natural_language_query,
            **kwargs
        )
        self.db.add(query)
        self.db.commit()
        self.db.refresh(query)
        return query
    
    def get_query(self, query_id: str) -> Optional[ConversationalQuery]:
        """Get query by ID."""
        return self.db.query(ConversationalQuery).filter(
            ConversationalQuery.id == query_id
        ).first()
    
    def get_session_queries(
        self, 
        session_id: str, 
        limit: int = 100
    ) -> List[ConversationalQuery]:
        """Get queries for a session."""
        return self.db.query(ConversationalQuery).filter(
            ConversationalQuery.session_id == session_id
        ).order_by(ConversationalQuery.created_at.desc()).limit(limit).all()
    
    def get_user_queries(
        self, 
        user_id: str, 
        limit: int = 100
    ) -> List[ConversationalQuery]:
        """Get queries for a user."""
        return self.db.query(ConversationalQuery).filter(
            ConversationalQuery.user_id == user_id
        ).order_by(ConversationalQuery.created_at.desc()).limit(limit).all()
    
    def update_query_status(
        self, 
        query_id: str, 
        status: QueryStatus,
        **kwargs
    ) -> bool:
        """Update query status and metadata."""
        query = self.get_query(query_id)
        if not query:
            return False
        
        query.status = status.value
        for key, value in kwargs.items():
            if hasattr(query, key):
                setattr(query, key, value)
        
        query.updated_at = datetime.utcnow()
        self.db.commit()
        return True
    
    def add_query_result(
        self, 
        query_id: str,
        result_type: str,
        format: str,
        data: Dict[str, Any],
        **kwargs
    ) -> QueryResult:
        """Add result to query."""
        result = QueryResult(
            query_id=query_id,
            result_type=result_type,
            format=format,
            data=data,
            **kwargs
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result
    
    def create_or_get_session(
        self, 
        session_id: str,
        user_id: str,
        **kwargs
    ) -> QuerySession:
        """Create or get existing session."""
        session = self.db.query(QuerySession).filter(
            QuerySession.session_id == session_id
        ).first()
        
        if not session:
            session = QuerySession(
                session_id=session_id,
                user_id=user_id,
                **kwargs
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        
        return session
    
    def add_feedback(
        self, 
        query_id: str,
        user_id: str,
        feedback_type: str,
        **kwargs
    ) -> QueryFeedback:
        """Add feedback to query."""
        feedback = QueryFeedback(
            query_id=query_id,
            user_id=user_id,
            feedback_type=feedback_type,
            **kwargs
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback
    
    def get_similar_queries(
        self, 
        user_id: str,
        limit: int = 10
    ) -> List[ConversationalQuery]:
        """Get similar successful queries for a user."""
        return self.db.query(ConversationalQuery).filter(
            ConversationalQuery.user_id == user_id,
            ConversationalQuery.status == QueryStatus.COMPLETED.value,
            ConversationalQuery.confidence_score >= 0.7
        ).order_by(ConversationalQuery.confidence_score.desc()).limit(limit).all()


# Example usage and data seeding
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Example database setup (use your actual database URL)
    DATABASE_URL = "postgresql://user:password@localhost/conversational_db"
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Example usage
    db = SessionLocal()
    dao = ConversationalQueryDAO(db)
    
    try:
        # Create a sample query
        query = dao.create_query(
            session_id="session_123",
            user_id="user_456",
            natural_language_query="Show me the top 10 customers by revenue",
            generated_sql="SELECT name, revenue FROM customers ORDER BY revenue DESC LIMIT 10",
            confidence_score=0.85
        )
        
        print(f"Created query: {query.id}")
        
        # Update query status
        dao.update_query_status(
            str(query.id),
            QueryStatus.COMPLETED,
            rows_returned=10,
            execution_time=2.5
        )
        
        # Add feedback
        feedback = dao.add_feedback(
            str(query.id),
            "user_456",
            "helpful",
            rating=5,
            sql_accuracy=5
        )
        
        print(f"Added feedback: {feedback.id}")
        
    finally:
        db.close()