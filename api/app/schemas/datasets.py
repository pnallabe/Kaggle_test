"""
Pydantic schemas for dataset and ETL operations
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


# Enums
class IngestionType(str, Enum):
    BATCH = "batch"
    STREAMING = "streaming"
    MANUAL = "manual"


class DatasetStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    DATAFLOW_BATCH = "dataflow_batch"
    DATAFLOW_STREAMING = "dataflow_streaming"
    COMPOSER_DAG = "composer_dag"


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# Base schemas
class DatasetBase(BaseModel):
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    ingestion_type: IngestionType = Field(..., description="Type of ingestion")
    
    # File information
    source_paths: Optional[List[str]] = Field(None, description="Source file paths")
    file_formats: Optional[List[str]] = Field(None, description="File formats")
    
    # BigQuery information
    bq_dataset_id: Optional[str] = Field(None, description="BigQuery dataset ID")
    bq_table_id: Optional[str] = Field(None, description="BigQuery table ID")
    bq_location: str = Field("US", description="BigQuery location")
    
    # Configuration
    ingestion_config: Optional[Dict[str, Any]] = Field(None, description="Ingestion configuration")
    
    # Streaming-specific
    pubsub_topic: Optional[str] = Field(None, description="Pub/Sub topic for streaming")
    pubsub_subscription: Optional[str] = Field(None, description="Pub/Sub subscription")


class DatasetCreate(DatasetBase):
    project_id: str = Field(..., description="Project ID")


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DatasetStatus] = None
    ingestion_config: Optional[Dict[str, Any]] = None
    bq_dataset_id: Optional[str] = None
    bq_table_id: Optional[str] = None
    pubsub_topic: Optional[str] = None
    pubsub_subscription: Optional[str] = None


class Dataset(DatasetBase):
    id: str
    project_id: str
    status: DatasetStatus
    
    # File information
    file_count: int = 0
    total_size_bytes: int = 0
    
    # Processing information
    records_processed: int = 0
    processing_time_seconds: Optional[float] = None
    
    # Data quality metrics
    data_quality_score: Optional[float] = None
    completeness_score: Optional[float] = None
    validation_success_rate: Optional[float] = None
    error_rate: Optional[float] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Error information
    error_message: Optional[str] = None
    error_count: int = 0
    
    class Config:
        from_attributes = True


# Column profile schemas
class ColumnProfile(BaseModel):
    column_name: str
    data_type: str
    null_count: int
    non_null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    
    # Statistical measures
    min_value: Optional[Union[str, int, float]] = None
    max_value: Optional[Union[str, int, float]] = None
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    std_dev: Optional[float] = None
    
    # String-specific measures
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    avg_length: Optional[float] = None
    
    # Top values
    top_values: Optional[List[tuple]] = None
    
    # Data quality flags
    has_duplicates: bool = False
    has_outliers: bool = False
    potential_pii: bool = False
    suggested_constraints: Optional[List[str]] = None


class DatasetProfileBase(BaseModel):
    total_rows: int
    total_columns: int
    memory_usage_mb: float
    data_quality_score: float
    completeness_score: float
    column_profiles: List[ColumnProfile]
    suggested_schema: List[Dict[str, Any]]
    data_quality_issues: List[str]
    optimization_recommendations: List[str]


class DatasetProfileCreate(DatasetProfileBase):
    dataset_id: str


class DatasetProfile(DatasetProfileBase):
    id: str
    dataset_id: str
    profiling_timestamp: datetime
    version: int
    
    class Config:
        from_attributes = True


# Validation schemas
class ValidationResult(BaseModel):
    rule_name: str
    passed: bool
    error_message: Optional[str] = None
    error_count: int = 0
    total_count: int = 0
    severity: ValidationSeverity = ValidationSeverity.ERROR
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 100.0
        return ((self.total_count - self.error_count) / self.total_count) * 100


class ValidationReportBase(BaseModel):
    total_rules: int
    passed_rules: int
    failed_rules: int
    overall_score: float
    validation_results: List[ValidationResult]
    severity_counts: Dict[str, int]
    validation_config: Dict[str, Any]


class ValidationReportCreate(ValidationReportBase):
    dataset_id: str


class ValidationReport(ValidationReportBase):
    id: str
    dataset_id: str
    validation_timestamp: datetime
    
    @property
    def success_rate(self) -> float:
        if self.total_rules == 0:
            return 100.0
        return (self.passed_rules / self.total_rules) * 100
    
    class Config:
        from_attributes = True


# Data lineage schemas
class DataLineageBase(BaseModel):
    source_dataset_id: str
    target_dataset_id: str
    transformation_type: str
    transformation_config: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None
    job_type: Optional[str] = None
    records_processed: int = 0
    processing_time_seconds: Optional[float] = None


class DataLineageCreate(DataLineageBase):
    pass


class DataLineage(DataLineageBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Ingestion job schemas
class IngestionJobBase(BaseModel):
    job_name: str
    job_type: JobType
    job_config: Dict[str, Any]
    max_retries: int = 3


class IngestionJobCreate(IngestionJobBase):
    dataset_id: str
    project_id: str


class IngestionJobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    dataflow_job_id: Optional[str] = None
    composer_dag_id: Optional[str] = None
    composer_run_id: Optional[str] = None
    records_processed: Optional[int] = None
    bytes_processed: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    cost_estimate_usd: Optional[float] = None
    progress_percentage: Optional[float] = None
    current_stage: Optional[str] = None
    stages_completed: Optional[List[str]] = None
    error_message: Optional[str] = None


class IngestionJob(IngestionJobBase):
    id: str
    dataset_id: str
    project_id: str
    status: JobStatus
    
    # External job references
    dataflow_job_id: Optional[str] = None
    composer_dag_id: Optional[str] = None
    composer_run_id: Optional[str] = None
    
    # Metrics
    records_processed: int = 0
    bytes_processed: int = 0
    processing_time_seconds: Optional[float] = None
    cost_estimate_usd: Optional[float] = None
    
    # Progress
    progress_percentage: float = 0.0
    current_stage: Optional[str] = None
    stages_completed: Optional[List[str]] = None
    
    # Error information
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Dataset metrics schemas
class DatasetMetricsBase(BaseModel):
    window_start: datetime
    window_end: datetime
    records_processed: int = 0
    bytes_processed: int = 0
    processing_rate_records_per_second: Optional[float] = None
    validation_success_rate: Optional[float] = None
    error_rate: Optional[float] = None
    schema_violations: int = 0
    late_data_count: int = 0
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    worker_count: Optional[int] = None
    cost_usd: Optional[float] = None


class DatasetMetricsCreate(DatasetMetricsBase):
    dataset_id: str


class DatasetMetrics(DatasetMetricsBase):
    id: str
    dataset_id: str
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Upload and ingestion request schemas
class FileUploadRequest(BaseModel):
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    file_format: str = Field(..., description="File format (csv, parquet, json)")
    dataset_name: Optional[str] = Field(None, description="Target dataset name")
    ingestion_config: Optional[Dict[str, Any]] = Field(None, description="Ingestion configuration")


class FileUploadResponse(BaseModel):
    upload_url: str = Field(..., description="Signed URL for file upload")
    dataset_id: str = Field(..., description="Created dataset ID")
    expires_at: datetime = Field(..., description="Upload URL expiration")


class IngestionTriggerRequest(BaseModel):
    dataset_id: str = Field(..., description="Dataset to process")
    job_type: JobType = Field(JobType.DATAFLOW_BATCH, description="Type of processing job")
    job_config: Optional[Dict[str, Any]] = Field(None, description="Job configuration overrides")
    force_reprocess: bool = Field(False, description="Force reprocessing even if already completed")


class IngestionTriggerResponse(BaseModel):
    job_id: str = Field(..., description="Created ingestion job ID")
    estimated_duration_minutes: Optional[int] = Field(None, description="Estimated processing time")
    cost_estimate_usd: Optional[float] = Field(None, description="Estimated cost")


# Batch operation schemas
class BatchDatasetOperation(BaseModel):
    dataset_ids: List[str] = Field(..., description="Dataset IDs to operate on")
    operation: str = Field(..., description="Operation to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class BatchOperationResult(BaseModel):
    success_count: int
    failure_count: int
    results: List[Dict[str, Any]]
    errors: List[str]


# Dashboard and analytics schemas
class DatasetSummary(BaseModel):
    id: str
    name: str
    status: DatasetStatus
    ingestion_type: IngestionType
    records_processed: int
    data_quality_score: Optional[float]
    last_updated: datetime
    
    class Config:
        from_attributes = True


class ProjectDataSummary(BaseModel):
    total_datasets: int
    active_datasets: int
    total_records_processed: int
    avg_data_quality_score: Optional[float]
    datasets_by_status: Dict[str, int]
    datasets_by_type: Dict[str, int]
    recent_datasets: List[DatasetSummary]