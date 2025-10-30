"""
Dataset CRUD operations and business logic
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from app.database import (
    Dataset, DatasetProfile, ValidationReport, DataLineage, 
    IngestionJob, DatasetMetrics
)
from app.schemas.datasets import (
    DatasetCreate, DatasetUpdate, DatasetProfileCreate, 
    ValidationReportCreate, DataLineageCreate, IngestionJobCreate,
    IngestionJobUpdate, DatasetMetricsCreate, DatasetStatus, JobStatus
)


class DatasetOperations:
    """Dataset CRUD operations"""
    
    @staticmethod
    def create_dataset(db: Session, dataset: DatasetCreate) -> Dataset:
        """Create a new dataset"""
        db_dataset = Dataset(
            id=str(uuid.uuid4()),
            **dataset.dict()
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def get_dataset(db: Session, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        return db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    @staticmethod
    def get_datasets_by_project(db: Session, project_id: str, skip: int = 0, limit: int = 100) -> List[Dataset]:
        """Get datasets for a project"""
        return db.query(Dataset).filter(
            Dataset.project_id == project_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_dataset(db: Session, dataset_id: str, dataset_update: DatasetUpdate) -> Optional[Dataset]:
        """Update dataset"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if db_dataset:
            update_data = dataset_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_dataset, field, value)
            db_dataset.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_dataset)
        return db_dataset
    
    @staticmethod
    def delete_dataset(db: Session, dataset_id: str) -> bool:
        """Delete dataset (soft delete by archiving)"""
        db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if db_dataset:
            db_dataset.status = DatasetStatus.ARCHIVED
            db_dataset.archived_at = datetime.utcnow()
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_datasets_by_status(db: Session, project_id: str, status: DatasetStatus) -> List[Dataset]:
        """Get datasets by status"""
        return db.query(Dataset).filter(
            and_(Dataset.project_id == project_id, Dataset.status == status)
        ).all()
    
    @staticmethod
    def search_datasets(db: Session, project_id: str, query: str, limit: int = 50) -> List[Dataset]:
        """Search datasets by name or description"""
        return db.query(Dataset).filter(
            and_(
                Dataset.project_id == project_id,
                or_(
                    Dataset.name.ilike(f"%{query}%"),
                    Dataset.description.ilike(f"%{query}%")
                )
            )
        ).limit(limit).all()


class DatasetProfileOperations:
    """Dataset profile CRUD operations"""
    
    @staticmethod
    def create_profile(db: Session, profile: DatasetProfileCreate) -> DatasetProfile:
        """Create a new dataset profile"""
        # Get current max version for this dataset
        max_version = db.query(func.max(DatasetProfile.version)).filter(
            DatasetProfile.dataset_id == profile.dataset_id
        ).scalar() or 0
        
        db_profile = DatasetProfile(
            id=str(uuid.uuid4()),
            version=max_version + 1,
            **profile.dict()
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
        return db_profile
    
    @staticmethod
    def get_latest_profile(db: Session, dataset_id: str) -> Optional[DatasetProfile]:
        """Get the latest profile for a dataset"""
        return db.query(DatasetProfile).filter(
            DatasetProfile.dataset_id == dataset_id
        ).order_by(desc(DatasetProfile.version)).first()
    
    @staticmethod
    def get_profile_history(db: Session, dataset_id: str) -> List[DatasetProfile]:
        """Get profile history for a dataset"""
        return db.query(DatasetProfile).filter(
            DatasetProfile.dataset_id == dataset_id
        ).order_by(desc(DatasetProfile.profiling_timestamp)).all()


class ValidationReportOperations:
    """Validation report CRUD operations"""
    
    @staticmethod
    def create_report(db: Session, report: ValidationReportCreate) -> ValidationReport:
        """Create a validation report"""
        db_report = ValidationReport(
            id=str(uuid.uuid4()),
            **report.dict()
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def get_latest_report(db: Session, dataset_id: str) -> Optional[ValidationReport]:
        """Get the latest validation report for a dataset"""
        return db.query(ValidationReport).filter(
            ValidationReport.dataset_id == dataset_id
        ).order_by(desc(ValidationReport.validation_timestamp)).first()
    
    @staticmethod
    def get_report_history(db: Session, dataset_id: str, limit: int = 10) -> List[ValidationReport]:
        """Get validation report history"""
        return db.query(ValidationReport).filter(
            ValidationReport.dataset_id == dataset_id
        ).order_by(desc(ValidationReport.validation_timestamp)).limit(limit).all()


class DataLineageOperations:
    """Data lineage CRUD operations"""
    
    @staticmethod
    def create_lineage(db: Session, lineage: DataLineageCreate) -> DataLineage:
        """Create a data lineage record"""
        db_lineage = DataLineage(
            id=str(uuid.uuid4()),
            **lineage.dict()
        )
        db.add(db_lineage)
        db.commit()
        db.refresh(db_lineage)
        return db_lineage
    
    @staticmethod
    def get_downstream_datasets(db: Session, source_dataset_id: str) -> List[DataLineage]:
        """Get datasets that depend on the source dataset"""
        return db.query(DataLineage).filter(
            DataLineage.source_dataset_id == source_dataset_id
        ).all()
    
    @staticmethod
    def get_upstream_datasets(db: Session, target_dataset_id: str) -> List[DataLineage]:
        """Get datasets that the target dataset depends on"""
        return db.query(DataLineage).filter(
            DataLineage.target_dataset_id == target_dataset_id
        ).all()
    
    @staticmethod
    def get_lineage_graph(db: Session, dataset_id: str, depth: int = 2) -> Dict[str, Any]:
        """Get lineage graph for a dataset with specified depth"""
        visited = set()
        graph = {"nodes": [], "edges": []}
        
        def traverse(current_id: str, current_depth: int, direction: str):
            if current_depth > depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Add current node
            dataset = db.query(Dataset).filter(Dataset.id == current_id).first()
            if dataset:
                graph["nodes"].append({
                    "id": current_id,
                    "name": dataset.name,
                    "status": dataset.status,
                    "type": dataset.ingestion_type
                })
            
            # Get connected datasets
            if direction in ["both", "downstream"]:
                downstream = DataLineageOperations.get_downstream_datasets(db, current_id)
                for lineage in downstream:
                    graph["edges"].append({
                        "source": lineage.source_dataset_id,
                        "target": lineage.target_dataset_id,
                        "transformation": lineage.transformation_type
                    })
                    traverse(lineage.target_dataset_id, current_depth + 1, "downstream")
            
            if direction in ["both", "upstream"]:
                upstream = DataLineageOperations.get_upstream_datasets(db, current_id)
                for lineage in upstream:
                    graph["edges"].append({
                        "source": lineage.source_dataset_id,
                        "target": lineage.target_dataset_id,
                        "transformation": lineage.transformation_type
                    })
                    traverse(lineage.source_dataset_id, current_depth + 1, "upstream")
        
        traverse(dataset_id, 0, "both")
        return graph


class IngestionJobOperations:
    """Ingestion job CRUD operations"""
    
    @staticmethod
    def create_job(db: Session, job: IngestionJobCreate) -> IngestionJob:
        """Create an ingestion job"""
        db_job = IngestionJob(
            id=str(uuid.uuid4()),
            **job.dict()
        )
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    
    @staticmethod
    def get_job(db: Session, job_id: str) -> Optional[IngestionJob]:
        """Get job by ID"""
        return db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    
    @staticmethod
    def update_job(db: Session, job_id: str, job_update: IngestionJobUpdate) -> Optional[IngestionJob]:
        """Update ingestion job"""
        db_job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if db_job:
            update_data = job_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_job, field, value)
            
            # Update timestamps based on status changes
            if "status" in update_data:
                if update_data["status"] == JobStatus.RUNNING and not db_job.started_at:
                    db_job.started_at = datetime.utcnow()
                elif update_data["status"] in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    db_job.finished_at = datetime.utcnow()
                    if db_job.started_at:
                        db_job.processing_time_seconds = (db_job.finished_at - db_job.started_at).total_seconds()
            
            db.commit()
            db.refresh(db_job)
        return db_job
    
    @staticmethod
    def get_jobs_by_dataset(db: Session, dataset_id: str) -> List[IngestionJob]:
        """Get jobs for a dataset"""
        return db.query(IngestionJob).filter(
            IngestionJob.dataset_id == dataset_id
        ).order_by(desc(IngestionJob.created_at)).all()
    
    @staticmethod
    def get_active_jobs(db: Session, project_id: str) -> List[IngestionJob]:
        """Get active jobs for a project"""
        return db.query(IngestionJob).filter(
            and_(
                IngestionJob.project_id == project_id,
                IngestionJob.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
            )
        ).all()


class DatasetMetricsOperations:
    """Dataset metrics CRUD operations"""
    
    @staticmethod
    def create_metrics(db: Session, metrics: DatasetMetricsCreate) -> DatasetMetrics:
        """Create dataset metrics"""
        db_metrics = DatasetMetrics(
            id=str(uuid.uuid4()),
            **metrics.dict()
        )
        db.add(db_metrics)
        db.commit()
        db.refresh(db_metrics)
        return db_metrics
    
    @staticmethod
    def get_metrics_by_timerange(
        db: Session, 
        dataset_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[DatasetMetrics]:
        """Get metrics for a time range"""
        return db.query(DatasetMetrics).filter(
            and_(
                DatasetMetrics.dataset_id == dataset_id,
                DatasetMetrics.timestamp >= start_time,
                DatasetMetrics.timestamp <= end_time
            )
        ).order_by(DatasetMetrics.timestamp).all()
    
    @staticmethod
    def get_latest_metrics(db: Session, dataset_id: str) -> Optional[DatasetMetrics]:
        """Get latest metrics for a dataset"""
        return db.query(DatasetMetrics).filter(
            DatasetMetrics.dataset_id == dataset_id
        ).order_by(desc(DatasetMetrics.timestamp)).first()


class DatasetAnalytics:
    """Dataset analytics and aggregation operations"""
    
    @staticmethod
    def get_project_summary(db: Session, project_id: str) -> Dict[str, Any]:
        """Get project-level dataset summary"""
        datasets = db.query(Dataset).filter(Dataset.project_id == project_id).all()
        
        total_datasets = len(datasets)
        active_datasets = len([d for d in datasets if d.status not in [DatasetStatus.ARCHIVED, DatasetStatus.FAILED]])
        total_records = sum(d.records_processed for d in datasets)
        
        # Calculate average data quality score
        quality_scores = [d.data_quality_score for d in datasets if d.data_quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Group by status and type
        status_counts = {}
        type_counts = {}
        
        for dataset in datasets:
            status_counts[dataset.status] = status_counts.get(dataset.status, 0) + 1
            type_counts[dataset.ingestion_type] = type_counts.get(dataset.ingestion_type, 0) + 1
        
        # Get recent datasets
        recent_datasets = sorted(datasets, key=lambda x: x.updated_at, reverse=True)[:10]
        
        return {
            "total_datasets": total_datasets,
            "active_datasets": active_datasets,
            "total_records_processed": total_records,
            "avg_data_quality_score": avg_quality,
            "datasets_by_status": status_counts,
            "datasets_by_type": type_counts,
            "recent_datasets": recent_datasets
        }
    
    @staticmethod
    def get_processing_trends(
        db: Session, 
        project_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get processing trends over time"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get datasets created in the time range
        datasets = db.query(Dataset).filter(
            and_(
                Dataset.project_id == project_id,
                Dataset.created_at >= start_date
            )
        ).all()
        
        # Aggregate by day
        daily_stats = {}
        for dataset in datasets:
            day = dataset.created_at.date()
            if day not in daily_stats:
                daily_stats[day] = {
                    "datasets_created": 0,
                    "records_processed": 0,
                    "avg_quality_score": []
                }
            
            daily_stats[day]["datasets_created"] += 1
            daily_stats[day]["records_processed"] += dataset.records_processed
            if dataset.data_quality_score:
                daily_stats[day]["avg_quality_score"].append(dataset.data_quality_score)
        
        # Calculate daily averages
        for day_stats in daily_stats.values():
            scores = day_stats["avg_quality_score"]
            day_stats["avg_quality_score"] = sum(scores) / len(scores) if scores else None
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "daily_stats": daily_stats,
            "total_datasets_created": len(datasets),
            "total_records_processed": sum(d.records_processed for d in datasets)
        }
    
    @staticmethod
    def get_data_quality_distribution(db: Session, project_id: str) -> Dict[str, Any]:
        """Get data quality score distribution"""
        datasets = db.query(Dataset).filter(
            and_(
                Dataset.project_id == project_id,
                Dataset.data_quality_score.isnot(None)
            )
        ).all()
        
        if not datasets:
            return {"distribution": {}, "statistics": {}}
        
        scores = [d.data_quality_score for d in datasets]
        
        # Create distribution buckets
        buckets = {
            "0-20": 0, "21-40": 0, "41-60": 0, 
            "61-80": 0, "81-100": 0
        }
        
        for score in scores:
            if score <= 20:
                buckets["0-20"] += 1
            elif score <= 40:
                buckets["21-40"] += 1
            elif score <= 60:
                buckets["41-60"] += 1
            elif score <= 80:
                buckets["61-80"] += 1
            else:
                buckets["81-100"] += 1
        
        # Calculate statistics
        statistics = {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "median": sorted(scores)[len(scores) // 2],
            "count": len(scores)
        }
        
        return {
            "distribution": buckets,
            "statistics": statistics
        }