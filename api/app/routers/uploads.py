"""
File upload and ingestion management API endpoints
"""

import os
import uuid
import mimetypes
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from google.cloud import storage
from google.cloud import dataflow_v1beta3
from google.cloud import composer_v1
import json

from app.database import get_db
from app.auth import get_current_user, require_project_access
from app.schemas.auth import User
from app.schemas.datasets import (
    FileUploadRequest, FileUploadResponse, IngestionTriggerRequest, 
    IngestionTriggerResponse, DatasetCreate, Dataset, IngestionJobCreate,
    JobType, DatasetStatus, IngestionJob
)
from app.operations.datasets import DatasetOperations, IngestionJobOperations
from app.config import settings

router = APIRouter(prefix="/upload", tags=["upload"])

# Initialize GCP clients
storage_client = storage.Client()
dataflow_client = dataflow_v1beta3.JobsV1Beta3Client()


def get_file_format(filename: str) -> str:
    """Detect file format from filename"""
    suffix = Path(filename).suffix.lower()
    format_mapping = {
        '.csv': 'csv',
        '.parquet': 'parquet',
        '.json': 'json',
        '.jsonl': 'json',
        '.xlsx': 'excel',
        '.xls': 'excel'
    }
    return format_mapping.get(suffix, 'unknown')


def validate_file_format(file_format: str) -> bool:
    """Validate if file format is supported"""
    supported_formats = {'csv', 'parquet', 'json'}
    return file_format in supported_formats


def generate_signed_upload_url(bucket_name: str, blob_name: str, expiration_minutes: int = 60) -> str:
    """Generate signed URL for file upload"""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    # Generate signed URL for PUT operation
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="PUT",
        content_type="application/octet-stream"
    )
    
    return signed_url


def estimate_processing_cost(file_size_bytes: int, file_format: str) -> float:
    """Estimate processing cost in USD"""
    # Simple cost estimation based on file size and format
    # In production, this would use more sophisticated pricing models
    
    base_cost_per_gb = {
        'csv': 0.05,
        'parquet': 0.03,
        'json': 0.06
    }
    
    file_size_gb = file_size_bytes / (1024**3)
    base_cost = base_cost_per_gb.get(file_format, 0.05)
    
    return max(0.01, file_size_gb * base_cost)  # Minimum $0.01


def estimate_processing_time(file_size_bytes: int, file_format: str) -> int:
    """Estimate processing time in minutes"""
    # Simple time estimation
    file_size_mb = file_size_bytes / (1024**2)
    
    processing_rate_mb_per_minute = {
        'csv': 100,
        'parquet': 200,
        'json': 80
    }
    
    rate = processing_rate_mb_per_minute.get(file_format, 100)
    estimated_minutes = max(1, int(file_size_mb / rate))
    
    return estimated_minutes


async def trigger_dataflow_job(
    dataset_id: str,
    job_config: Dict[str, Any],
    job_type: JobType
) -> str:
    """Trigger a Dataflow job"""
    
    # Construct job name
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    job_name = f"{job_type.value}-{dataset_id[:8]}-{timestamp}"
    
    # Determine template based on job type
    if job_type == JobType.DATAFLOW_BATCH:
        template_path = f"gs://{settings.GCS_BUCKET}/dataflow/batch_ingestion_pipeline.py"
    elif job_type == JobType.DATAFLOW_STREAMING:
        template_path = f"gs://{settings.GCS_BUCKET}/dataflow/streaming_ingestion_pipeline.py"
    else:
        raise ValueError(f"Unsupported job type: {job_type}")
    
    # Prepare job request
    job_request = {
        "project_id": settings.GCP_PROJECT_ID,
        "job": {
            "name": job_name,
            "type": "JOB_TYPE_BATCH" if job_type == JobType.DATAFLOW_BATCH else "JOB_TYPE_STREAMING",
            "environment": {
                "temp_location": f"gs://{settings.GCS_BUCKET}/temp/dataflow/",
                "staging_location": f"gs://{settings.GCS_BUCKET}/staging/dataflow/",
                "zone": "us-central1-a",
                "machine_type": "n1-standard-4",
                "max_workers": 10
            },
            "steps": [{
                "name": "process_data",
                "kind": "ParDo",
                "properties": {
                    "file_path": job_config.get("file_path"),
                    "output_table": job_config.get("output_table"),
                    "validation_rules": json.dumps(job_config.get("validation_rules", {}))
                }
            }]
        },
        "location": settings.GCP_REGION
    }
    
    try:
        # Create job (this is a simplified version - in production you'd use the actual Dataflow API)
        # response = dataflow_client.create_job(request=job_request)
        # For demo purposes, return a mock job ID
        mock_job_id = f"dataflow-job-{uuid.uuid4().hex[:8]}"
        return mock_job_id
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Dataflow job: {str(e)}")


async def trigger_composer_dag(
    dataset_id: str,
    dag_id: str,
    conf: Dict[str, Any]
) -> str:
    """Trigger a Cloud Composer DAG"""
    
    # This would use the Cloud Composer API to trigger a DAG
    # For demo purposes, return a mock run ID
    mock_run_id = f"composer-run-{uuid.uuid4().hex[:8]}"
    return mock_run_id


@router.post("/request-upload", response_model=FileUploadResponse)
async def request_file_upload(
    project_id: str = Form(...),
    filename: str = Form(...),
    file_size: int = Form(...),
    dataset_name: Optional[str] = Form(None),
    ingestion_config: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request a signed URL for file upload"""
    
    # Check project access
    await require_project_access(current_user.id, project_id, "editor")
    
    # Validate file format
    file_format = get_file_format(filename)
    if not validate_file_format(file_format):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format: {file_format}. Supported formats: csv, parquet, json"
        )
    
    # Validate file size (max 5GB)
    max_file_size = 5 * 1024 * 1024 * 1024  # 5GB
    if file_size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_file_size} bytes)"
        )
    
    # Parse ingestion config
    config_dict = {}
    if ingestion_config:
        try:
            config_dict = json.loads(ingestion_config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid ingestion_config JSON")
    
    # Create dataset
    dataset_create = DatasetCreate(
        project_id=project_id,
        name=dataset_name or Path(filename).stem,
        description=f"Uploaded file: {filename}",
        ingestion_type="manual",
        source_paths=[],  # Will be updated after upload
        file_formats=[file_format],
        ingestion_config=config_dict
    )
    
    dataset = DatasetOperations.create_dataset(db, dataset_create)
    
    # Generate GCS path for upload
    blob_name = f"uploads/{project_id}/{dataset.id}/{filename}"
    
    # Generate signed upload URL
    signed_url = generate_signed_upload_url(
        settings.GCS_BUCKET,
        blob_name,
        expiration_minutes=60
    )
    
    # Update dataset with file path
    from app.schemas.datasets import DatasetUpdate
    dataset_update = DatasetUpdate(
        source_paths=[f"gs://{settings.GCS_BUCKET}/{blob_name}"]
    )
    DatasetOperations.update_dataset(db, dataset.id, dataset_update)
    
    return FileUploadResponse(
        upload_url=signed_url,
        dataset_id=dataset.id,
        expires_at=datetime.utcnow() + timedelta(minutes=60)
    )


@router.post("/upload-direct")
async def upload_file_direct(
    project_id: str = Form(...),
    dataset_name: Optional[str] = Form(None),
    ingestion_config: Optional[str] = Form(None),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload file directly to the API"""
    
    # Check project access
    await require_project_access(current_user.id, project_id, "editor")
    
    # Validate file format
    file_format = get_file_format(file.filename)
    if not validate_file_format(file_format):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_format}"
        )
    
    # Validate file size
    max_file_size = 100 * 1024 * 1024  # 100MB for direct upload
    if file.size and file.size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large for direct upload. Use request-upload for files > 100MB"
        )
    
    # Parse ingestion config
    config_dict = {}
    if ingestion_config:
        try:
            config_dict = json.loads(ingestion_config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid ingestion_config JSON")
    
    # Create dataset
    dataset_create = DatasetCreate(
        project_id=project_id,
        name=dataset_name or Path(file.filename).stem,
        description=f"Direct upload: {file.filename}",
        ingestion_type="manual",
        file_formats=[file_format],
        ingestion_config=config_dict
    )
    
    dataset = DatasetOperations.create_dataset(db, dataset_create)
    
    # Upload file to GCS
    blob_name = f"uploads/{project_id}/{dataset.id}/{file.filename}"
    bucket = storage_client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(blob_name)
    
    try:
        # Upload file content
        file_content = await file.read()
        blob.upload_from_string(file_content, content_type=file.content_type)
        
        # Update dataset with file information
        from app.schemas.datasets import DatasetUpdate
        dataset_update = DatasetUpdate(
            source_paths=[f"gs://{settings.GCS_BUCKET}/{blob_name}"],
            file_count=1,
            total_size_bytes=len(file_content),
            status=DatasetStatus.PROCESSING
        )
        DatasetOperations.update_dataset(db, dataset.id, dataset_update)
        
        # Schedule background processing
        background_tasks.add_task(
            process_uploaded_file,
            dataset.id,
            f"gs://{settings.GCS_BUCKET}/{blob_name}",
            file_format,
            config_dict
        )
        
        return {
            "message": "File uploaded successfully",
            "dataset_id": dataset.id,
            "file_path": f"gs://{settings.GCS_BUCKET}/{blob_name}",
            "status": "processing"
        }
        
    except Exception as e:
        # Update dataset status to failed
        from app.schemas.datasets import DatasetUpdate
        dataset_update = DatasetUpdate(
            status=DatasetStatus.FAILED,
            error_message=str(e)
        )
        DatasetOperations.update_dataset(db, dataset.id, dataset_update)
        
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.post("/trigger-ingestion", response_model=IngestionTriggerResponse)
async def trigger_ingestion(
    request: IngestionTriggerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger ingestion processing for a dataset"""
    
    # Get dataset and validate
    dataset = DatasetOperations.get_dataset(db, request.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Check if already processing (unless force_reprocess is True)
    if dataset.status == DatasetStatus.PROCESSING and not request.force_reprocess:
        raise HTTPException(
            status_code=400,
            detail="Dataset is already being processed. Use force_reprocess=true to override."
        )
    
    # Estimate cost and time
    total_size = dataset.total_size_bytes or 0
    file_format = dataset.file_formats[0] if dataset.file_formats else 'csv'
    
    estimated_cost = estimate_processing_cost(total_size, file_format)
    estimated_time = estimate_processing_time(total_size, file_format)
    
    # Prepare job configuration
    job_config = {
        "dataset_id": dataset.id,
        "file_paths": dataset.source_paths or [],
        "output_table": f"{settings.GCP_PROJECT_ID}:{settings.BIGQUERY_DATASET}.{dataset.id}",
        "validation_rules": dataset.ingestion_config or {},
        "file_format": file_format
    }
    
    # Merge with request config overrides
    if request.job_config:
        job_config.update(request.job_config)
    
    # Create ingestion job record
    ingestion_job = IngestionJobCreate(
        dataset_id=dataset.id,
        project_id=dataset.project_id,
        job_name=f"{request.job_type.value}_{dataset.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        job_type=request.job_type,
        job_config=job_config,
        max_retries=3
    )
    
    db_job = IngestionJobOperations.create_job(db, ingestion_job)
    
    try:
        # Trigger appropriate job type
        if request.job_type in [JobType.DATAFLOW_BATCH, JobType.DATAFLOW_STREAMING]:
            external_job_id = await trigger_dataflow_job(dataset.id, job_config, request.job_type)
            
            # Update job with external ID
            from app.schemas.datasets import IngestionJobUpdate
            job_update = IngestionJobUpdate(
                dataflow_job_id=external_job_id,
                status="running",
                cost_estimate_usd=estimated_cost
            )
            IngestionJobOperations.update_job(db, db_job.id, job_update)
            
        elif request.job_type == JobType.COMPOSER_DAG:
            dag_id = "batch_etl_ingestion"  # Default DAG
            external_run_id = await trigger_composer_dag(dataset.id, dag_id, job_config)
            
            # Update job with external ID
            from app.schemas.datasets import IngestionJobUpdate
            job_update = IngestionJobUpdate(
                composer_dag_id=dag_id,
                composer_run_id=external_run_id,
                status="running",
                cost_estimate_usd=estimated_cost
            )
            IngestionJobOperations.update_job(db, db_job.id, job_update)
        
        # Update dataset status
        from app.schemas.datasets import DatasetUpdate
        dataset_update = DatasetUpdate(status=DatasetStatus.PROCESSING)
        DatasetOperations.update_dataset(db, dataset.id, dataset_update)
        
        return IngestionTriggerResponse(
            job_id=db_job.id,
            estimated_duration_minutes=estimated_time,
            cost_estimate_usd=estimated_cost
        )
        
    except Exception as e:
        # Update job status to failed
        from app.schemas.datasets import IngestionJobUpdate
        job_update = IngestionJobUpdate(
            status="failed",
            error_message=str(e)
        )
        IngestionJobOperations.update_job(db, db_job.id, job_update)
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger ingestion: {str(e)}")


@router.post("/refresh-dataset/{dataset_id}")
async def refresh_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Refresh/reprocess a dataset"""
    
    # Get dataset and validate
    dataset = DatasetOperations.get_dataset(db, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check project access
    await require_project_access(current_user.id, dataset.project_id, "editor")
    
    # Trigger refresh processing
    background_tasks.add_task(refresh_dataset_background, dataset_id)
    
    return {"message": "Dataset refresh initiated", "dataset_id": dataset_id}


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "supported_formats": [
            {
                "format": "csv",
                "extensions": [".csv"],
                "description": "Comma-separated values",
                "max_size_gb": 5
            },
            {
                "format": "parquet",
                "extensions": [".parquet"],
                "description": "Apache Parquet columnar format",
                "max_size_gb": 10
            },
            {
                "format": "json",
                "extensions": [".json", ".jsonl"],
                "description": "JSON or JSON Lines format",
                "max_size_gb": 2
            }
        ],
        "max_direct_upload_mb": 100,
        "max_signed_upload_gb": 5
    }


# Background task functions
async def process_uploaded_file(
    dataset_id: str,
    file_path: str,
    file_format: str,
    config: Dict[str, Any]
):
    """Background task to process uploaded file"""
    # This would integrate with the schema inference and validation services
    # For now, just update the dataset status
    
    # Simulate processing delay
    import asyncio
    await asyncio.sleep(5)
    
    # In production, this would:
    # 1. Run schema inference
    # 2. Validate data quality
    # 3. Load into BigQuery
    # 4. Update dataset metadata
    
    print(f"Processing file {file_path} for dataset {dataset_id}")


async def refresh_dataset_background(dataset_id: str):
    """Background task to refresh dataset"""
    # This would re-run the ingestion pipeline
    print(f"Refreshing dataset {dataset_id}")


# Webhook endpoints for external job status updates
@router.post("/webhooks/dataflow-status")
async def dataflow_status_webhook(
    job_id: str = Form(...),
    status: str = Form(...),
    error_message: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Webhook to receive Dataflow job status updates"""
    
    # Find ingestion job by dataflow job ID
    # This would require a database query to find the job
    # For demo purposes, just log the status
    
    print(f"Dataflow job {job_id} status: {status}")
    if error_message:
        print(f"Error: {error_message}")
    
    return {"message": "Status update received"}


@router.post("/webhooks/composer-status")
async def composer_status_webhook(
    dag_id: str = Form(...),
    run_id: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Webhook to receive Cloud Composer DAG run status updates"""
    
    print(f"Composer DAG {dag_id} run {run_id} status: {status}")
    
    return {"message": "Status update received"}