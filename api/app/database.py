"""
Database models and operations
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Boolean, ForeignKey, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import NullPool

from app.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # No connection pooling for Cloud SQL
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(255), primary_key=True)
    email = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    picture_url = Column(String(512), nullable=True)
    workspace_id = Column(String(255), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    projects = relationship("ProjectAccess", back_populates="user")
    jobs = relationship("Job", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), index=True)
    owner_id = Column(String(255), ForeignKey("users.id"))
    description = Column(String(1000), nullable=True)
    billing_tier = Column(String(50), default="free")  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    connectors = relationship("Connector", back_populates="project")
    jobs = relationship("Job", back_populates="project")
    access = relationship("ProjectAccess", back_populates="project")

class ProjectAccess(Base):
    __tablename__ = "project_access"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    user_id = Column(String(255), ForeignKey("users.id"), index=True)
    role = Column(String(50), default="viewer")  # viewer, editor, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="access")
    user = relationship("User", back_populates="projects")

class Connector(Base):
    __tablename__ = "connectors"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    name = Column(String(255))
    type = Column(String(50), index=True)  # bigquery, gcs, postgres, snowflake
    config = Column(JSON)  # Encrypted in production
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="connectors")

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    user_id = Column(String(255), ForeignKey("users.id"), index=True)
    question = Column(String(2000))
    status = Column(String(50), default="pending", index=True)  # pending, running, succeeded, failed
    plan_json = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    
    project = relationship("Project", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
    artifacts = relationship("Artifact", back_populates="job")

class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(String(255), primary_key=True)
    job_id = Column(String(255), ForeignKey("jobs.id"), index=True)
    type = Column(String(50))  # csv, json, png, html, notebook
    gcs_path = Column(String(512), unique=True)
    size_bytes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="artifacts")

class AccessLog(Base):
    __tablename__ = "access_logs"
    
    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), index=True)
    action = Column(String(100))  # query_submitted, job_created, artifact_downloaded
    target = Column(String(255))  # resource being accessed
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Data ingestion and ETL models
class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(String(255), primary_key=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    name = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    ingestion_type = Column(String(50), index=True)  # batch, streaming, manual
    status = Column(String(50), default="created", index=True)  # created, processing, completed, failed, archived
    
    # File information
    source_paths = Column(JSON, nullable=True)  # List of source file paths
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    file_formats = Column(JSON, nullable=True)  # List of file formats
    
    # BigQuery information
    bq_dataset_id = Column(String(255), nullable=True, index=True)
    bq_table_id = Column(String(255), nullable=True, index=True)
    bq_location = Column(String(50), default="US")
    
    # Processing information
    ingestion_config = Column(JSON, nullable=True)  # Validation rules, transformations, etc.
    records_processed = Column(Integer, default=0)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Data quality metrics
    data_quality_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    validation_success_rate = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)
    
    # Streaming-specific fields
    pubsub_topic = Column(String(255), nullable=True)
    pubsub_subscription = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    
    # Relationships
    project = relationship("Project")
    profiles = relationship("DatasetProfile", back_populates="dataset")
    validation_reports = relationship("ValidationReport", back_populates="dataset")
    lineage_sources = relationship("DataLineage", foreign_keys="DataLineage.source_dataset_id", back_populates="source_dataset")
    lineage_targets = relationship("DataLineage", foreign_keys="DataLineage.target_dataset_id", back_populates="target_dataset")


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"
    
    id = Column(String(255), primary_key=True)
    dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    
    # Profile metadata
    profiling_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_rows = Column(Integer)
    total_columns = Column(Integer)
    memory_usage_mb = Column(Float)
    
    # Quality scores
    data_quality_score = Column(Float)
    completeness_score = Column(Float)
    
    # Profile data (JSON)
    column_profiles = Column(JSON)  # Detailed column statistics
    suggested_schema = Column(JSON)  # BigQuery schema
    data_quality_issues = Column(JSON)  # List of issues
    optimization_recommendations = Column(JSON)  # List of recommendations
    
    # Version for profile evolution tracking
    version = Column(Integer, default=1)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="profiles")


class ValidationReport(Base):
    __tablename__ = "validation_reports"
    
    id = Column(String(255), primary_key=True)
    dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    
    # Report metadata
    validation_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    total_rules = Column(Integer)
    passed_rules = Column(Integer)
    failed_rules = Column(Integer)
    
    # Scores
    overall_score = Column(Float)
    
    # Validation results (JSON)
    validation_results = Column(JSON)  # List of ValidationResult objects
    severity_counts = Column(JSON)  # Count by severity
    
    # Configuration used
    validation_config = Column(JSON)  # Rules that were applied
    
    # Relationships
    dataset = relationship("Dataset", back_populates="validation_reports")


class DataLineage(Base):
    __tablename__ = "data_lineage"
    
    id = Column(String(255), primary_key=True)
    
    # Source and target
    source_dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    target_dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    
    # Transformation information
    transformation_type = Column(String(100))  # etl_pipeline, manual_upload, api_ingestion
    transformation_config = Column(JSON, nullable=True)  # Transformation details
    
    # Processing job information
    job_id = Column(String(255), nullable=True, index=True)  # Associated Dataflow/Composer job
    job_type = Column(String(50), nullable=True)  # dataflow, composer, manual
    
    # Metrics
    records_processed = Column(Integer, default=0)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    source_dataset = relationship("Dataset", foreign_keys=[source_dataset_id], back_populates="lineage_targets")
    target_dataset = relationship("Dataset", foreign_keys=[target_dataset_id], back_populates="lineage_sources")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    
    id = Column(String(255), primary_key=True)
    dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    project_id = Column(String(255), ForeignKey("projects.id"), index=True)
    
    # Job information
    job_name = Column(String(255), index=True)
    job_type = Column(String(50))  # dataflow_batch, dataflow_streaming, composer_dag
    status = Column(String(50), default="pending", index=True)  # pending, running, succeeded, failed, cancelled
    
    # External job references
    dataflow_job_id = Column(String(255), nullable=True, index=True)
    composer_dag_id = Column(String(255), nullable=True)
    composer_run_id = Column(String(255), nullable=True)
    
    # Configuration
    job_config = Column(JSON)  # Job parameters and configuration
    
    # Metrics
    records_processed = Column(Integer, default=0)
    bytes_processed = Column(Integer, default=0)
    processing_time_seconds = Column(Float, nullable=True)
    cost_estimate_usd = Column(Float, nullable=True)
    
    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_stage = Column(String(100), nullable=True)  # Current processing stage
    stages_completed = Column(JSON, nullable=True)  # List of completed stages
    
    # Error information
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Relationships
    dataset = relationship("Dataset")
    project = relationship("Project")


class DatasetMetrics(Base):
    __tablename__ = "dataset_metrics"
    
    id = Column(String(255), primary_key=True)
    dataset_id = Column(String(255), ForeignKey("datasets.id"), index=True)
    
    # Time window for metrics
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    window_start = Column(DateTime, index=True)
    window_end = Column(DateTime, index=True)
    
    # Processing metrics
    records_processed = Column(Integer, default=0)
    bytes_processed = Column(Integer, default=0)
    processing_rate_records_per_second = Column(Float, nullable=True)
    
    # Quality metrics
    validation_success_rate = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)
    schema_violations = Column(Integer, default=0)
    late_data_count = Column(Integer, default=0)
    
    # System metrics
    cpu_utilization = Column(Float, nullable=True)
    memory_utilization = Column(Float, nullable=True)
    worker_count = Column(Integer, nullable=True)
    
    # Cost metrics
    cost_usd = Column(Float, nullable=True)
    
    # Relationships
    dataset = relationship("Dataset")

# Database operations
async def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_user_role(user_id: str, project_id: str) -> Optional[str]:
    """Get user's role in a project"""
    db = SessionLocal()
    try:
        access = db.query(ProjectAccess).filter(
            ProjectAccess.user_id == user_id,
            ProjectAccess.project_id == project_id,
        ).first()
        return access.role if access else None
    finally:
        db.close()
