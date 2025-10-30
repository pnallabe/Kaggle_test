"""
Dataset management API endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.auth import get_current_user, require_project_access
from app.schemas.auth import User
from app.schemas.datasets import (
    Dataset, DatasetCreate, DatasetUpdate, DatasetProfile, DatasetProfileCreate,
    ValidationReport, ValidationReportCreate, DataLineage, DataLineageCreate,
    IngestionJob, IngestionJobCreate, IngestionJobUpdate, DatasetMetrics,
    DatasetMetricsCreate, FileUploadRequest, FileUploadResponse,
    IngestionTriggerRequest, IngestionTriggerResponse, BatchDatasetOperation,
    BatchOperationResult, DatasetSummary, ProjectDataSummary,
    DatasetStatus, JobType, JobStatus
)
from app.operations.datasets import (
    DatasetOperations, DatasetProfileOperations, ValidationReportOperations,
    DataLineageOperations, IngestionJobOperations, DatasetMetricsOperations,
    DatasetAnalytics
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


# Dataset CRUD endpoints
@router.post("/", response_model=Dataset)
async def create_dataset(
    dataset: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new dataset"""
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Create dataset
    db_dataset = DatasetOperations.create_dataset(db, dataset)
    return db_dataset


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dataset by ID"""
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    return dataset


@router.put("/{dataset_id}", response_model=Dataset)
async def update_dataset(
    dataset_id: str,
    dataset_update: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update dataset"""
    # Get existing dataset
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Update dataset
    updated_dataset = DatasetOperations.update_dataset(db, dataset_id, dataset_update)
    return updated_dataset


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (archive) dataset"""
    # Get existing dataset
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "admin")
    
    # Delete dataset
    success = DatasetOperations.delete_dataset(db, dataset_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete dataset")
    
    return {"message": "Dataset archived successfully"}


@router.get("/project/{project_id}", response_model=List[Dataset])
async def get_project_datasets(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[DatasetStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get datasets for a project"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    if status:
        datasets = DatasetOperations.get_datasets_by_status(db, project_id, status)
    else:
        datasets = DatasetOperations.get_datasets_by_project(db, project_id, skip, limit)
    
    return datasets


@router.get("/project/{project_id}/search", response_model=List[Dataset])
async def search_datasets(
    project_id: str,
    query: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search datasets by name or description"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    datasets = DatasetOperations.search_datasets(db, project_id, query, limit)
    return datasets


# Dataset profiling endpoints
@router.post("/{dataset_id}/profiles", response_model=DatasetProfile)
async def create_dataset_profile(
    dataset_id: str,
    profile: DatasetProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a dataset profile"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Ensure profile is for the correct dataset
    profile.dataset_id = dataset_id
    
    # Create profile
    db_profile = DatasetProfileOperations.create_profile(db, profile)
    return db_profile


@router.get("/{dataset_id}/profiles/latest", response_model=Optional[DatasetProfile])
async def get_latest_profile(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get latest profile for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    profile = DatasetProfileOperations.get_latest_profile(db, dataset_id)
    return profile


@router.get("/{dataset_id}/profiles", response_model=List[DatasetProfile])
async def get_profile_history(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get profile history for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    profiles = DatasetProfileOperations.get_profile_history(db, dataset_id)
    return profiles


# Validation report endpoints
@router.post("/{dataset_id}/validation-reports", response_model=ValidationReport)
async def create_validation_report(
    dataset_id: str,
    report: ValidationReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a validation report"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Ensure report is for the correct dataset
    report.dataset_id = dataset_id
    
    # Create report
    db_report = ValidationReportOperations.create_report(db, report)
    return db_report


@router.get("/{dataset_id}/validation-reports/latest", response_model=Optional[ValidationReport])
async def get_latest_validation_report(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get latest validation report for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    report = ValidationReportOperations.get_latest_report(db, dataset_id)
    return report


@router.get("/{dataset_id}/validation-reports", response_model=List[ValidationReport])
async def get_validation_report_history(
    dataset_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get validation report history"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    reports = ValidationReportOperations.get_report_history(db, dataset_id, limit)
    return reports


# Data lineage endpoints
@router.post("/lineage", response_model=DataLineage)
async def create_data_lineage(
    lineage: DataLineageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a data lineage record"""
    # Check access to both source and target datasets
    source_dataset = DatasetOperations.get_dataset(db, lineage.source_dataset_id)
    target_dataset = DatasetOperations.get_dataset(db, lineage.target_dataset_id)
    
    if not source_dataset or not target_dataset:
        raise HTTPException(status_code=404, detail="Source or target dataset not found")
    
    await require_project_access(current_user.id, source_dataset.project_id, "editor")
    await require_project_access(current_user.id, target_dataset.project_id, "editor")
    
    # Create lineage
    db_lineage = DataLineageOperations.create_lineage(db, lineage)
    return db_lineage


@router.get("/{dataset_id}/lineage/downstream", response_model=List[DataLineage])
async def get_downstream_datasets(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get downstream datasets"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    lineages = DataLineageOperations.get_downstream_datasets(db, dataset_id)
    return lineages


@router.get("/{dataset_id}/lineage/upstream", response_model=List[DataLineage])
async def get_upstream_datasets(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get upstream datasets"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    lineages = DataLineageOperations.get_upstream_datasets(db, dataset_id)
    return lineages


@router.get("/{dataset_id}/lineage/graph", response_model=Dict[str, Any])
async def get_lineage_graph(
    dataset_id: str,
    depth: int = 2,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lineage graph for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    graph = DataLineageOperations.get_lineage_graph(db, dataset_id, depth)
    return graph


# Ingestion job endpoints
@router.post("/{dataset_id}/jobs", response_model=IngestionJob)
async def create_ingestion_job(
    dataset_id: str,
    job: IngestionJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an ingestion job"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Set dataset and project IDs
    job.dataset_id = dataset_id
    job.project_id = dataset.project_id
    
    # Create job
    db_job = IngestionJobOperations.create_job(db, job)
    return db_job


@router.get("/jobs/{job_id}", response_model=IngestionJob)
async def get_ingestion_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ingestion job by ID"""
    job = IngestionJobOperations.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check project access
    await require_project_access(current_user.id, job.project_id, "viewer")
    
    return job


@router.put("/jobs/{job_id}", response_model=IngestionJob)
async def update_ingestion_job(
    job_id: str,
    job_update: IngestionJobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update ingestion job"""
    # Get existing job
    job = IngestionJobOperations.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check project access
    await require_project_access(current_user.id, job.project_id, "editor")
    
    # Update job
    updated_job = IngestionJobOperations.update_job(db, job_id, job_update)
    return updated_job


@router.get("/{dataset_id}/jobs", response_model=List[IngestionJob])
async def get_dataset_jobs(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get jobs for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    jobs = IngestionJobOperations.get_jobs_by_dataset(db, dataset_id)
    return jobs


@router.get("/project/{project_id}/jobs/active", response_model=List[IngestionJob])
async def get_active_jobs(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active jobs for a project"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    jobs = IngestionJobOperations.get_active_jobs(db, project_id)
    return jobs


# Dataset metrics endpoints
@router.post("/{dataset_id}/metrics", response_model=DatasetMetrics)
async def create_dataset_metrics(
    dataset_id: str,
    metrics: DatasetMetricsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create dataset metrics"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Set dataset ID
    metrics.dataset_id = dataset_id
    
    # Create metrics
    db_metrics = DatasetMetricsOperations.create_metrics(db, metrics)
    return db_metrics


@router.get("/{dataset_id}/metrics", response_model=List[DatasetMetrics])
async def get_dataset_metrics(
    dataset_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dataset metrics for a time range"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    # Default to last 24 hours if no time range specified
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    metrics = DatasetMetricsOperations.get_metrics_by_timerange(db, dataset_id, start_time, end_time)
    return metrics


@router.get("/{dataset_id}/metrics/latest", response_model=Optional[DatasetMetrics])
async def get_latest_metrics(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get latest metrics for a dataset"""
    # Get dataset and check access
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    await require_project_access(current_user.id, dataset.project_id, "viewer")
    
    metrics = DatasetMetricsOperations.get_latest_metrics(db, dataset_id)
    return metrics


# Analytics endpoints
@router.get("/project/{project_id}/summary", response_model=ProjectDataSummary)
async def get_project_summary(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project-level dataset summary"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    summary = DatasetAnalytics.get_project_summary(db, project_id)
    return summary


@router.get("/project/{project_id}/trends", response_model=Dict[str, Any])
async def get_processing_trends(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get processing trends over time"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    trends = DatasetAnalytics.get_processing_trends(db, project_id, days)
    return trends


@router.get("/project/{project_id}/quality-distribution", response_model=Dict[str, Any])
async def get_quality_distribution(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data quality score distribution"""
    # Check project access
    await require_project_access(current_user.id, project_id, "viewer")
    
    distribution = DatasetAnalytics.get_data_quality_distribution(db, project_id)
    return distribution