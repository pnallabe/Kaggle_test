# Phase 2: Data Ingestion & ETL - Implementation Guide

## Overview
Phase 2 implements comprehensive data ingestion and ETL workflows for the AI Data Analyst platform, including Apache Beam pipelines, schema inference, Cloud Composer orchestration, and metadata management.

## Architecture Components

### 1. Dataflow Pipelines (`dataflow/`)

#### Core Ingestion Pipeline (`ingestion_pipeline.py`)
- **Apache Beam pipeline** for processing individual CSV/Parquet files
- **Data validation** with configurable rules and quality checks
- **Schema inference** and BigQuery schema generation
- **Error handling** with separate error and metadata tables
- **Metadata collection** for lineage and processing statistics

**Key Features:**
- File format detection (CSV, Parquet, JSON)
- Schema inference with type detection
- Data quality validation with error reporting
- BigQuery integration with auto-partitioning
- PII detection and data security measures

#### Batch Ingestion Pipeline (`batch_ingestion_pipeline.py`)
- **Bulk processing** of multiple files from GCS buckets
- **File pattern matching** with age-based filtering
- **Parallel processing** with configurable batch sizes
- **Processing statistics** and monitoring integration
- **Cost optimization** with worker scaling

**Features:**
- GCS file discovery and batching
- Format-based processing grouping
- Comprehensive error handling
- Processing metrics collection
- Dynamic scaling based on workload

#### Streaming Ingestion Pipeline (`streaming_ingestion_pipeline.py`)
- **Real-time processing** from Pub/Sub messages
- **Windowing functions** (fixed, sliding, session windows)
- **Data enrichment** with computed fields and transformations
- **Real-time validation** and quality monitoring
- **Stream processing statistics**

**Streaming Features:**
- Pub/Sub message parsing and validation
- Real-time data enrichment
- Windowed aggregations
- Late data handling
- Stream monitoring and alerting

### 2. Schema Inference System (`schema_inference/`)

#### Data Profiler (`profiler.py`)
- **Comprehensive data profiling** with statistical analysis
- **Schema inference** with BigQuery type mapping
- **Data quality scoring** and completeness analysis
- **PII detection** with pattern matching
- **Optimization recommendations** for storage and performance

**Profiling Capabilities:**
- Column-level statistics (null rates, uniqueness, distributions)
- Data type inference with confidence scoring
- Outlier detection using statistical methods
- Pattern-based PII identification
- Storage optimization suggestions

#### Validation Engine (`validator.py`)
- **Rule-based validation** with configurable constraints
- **Data quality rules** (NOT NULL, UNIQUE, ranges, patterns)
- **Custom validation functions** with extensible framework
- **Validation reporting** with HTML and JSON output
- **Severity-based error classification**

**Validation Rules:**
- Field presence and null checks
- Data type and format validation
- Range and constraint validation
- Pattern matching (email, phone, etc.)
- Custom business rule validation

#### Integration Service (`service.py`)
- **GCS integration** for automated file profiling
- **BigQuery table creation** with inferred schemas
- **Data drift detection** and monitoring
- **Batch profiling operations** for multiple files
- **Profile comparison** and evolution tracking

### 3. Cloud Composer Orchestration (`composer/`)

#### Batch ETL DAG (`batch_etl_dag.py`)
- **Scheduled batch processing** with dependency management
- **File discovery** and validation workflows
- **Parallel Dataflow job execution** for different formats  
- **Data quality checks** and validation steps
- **Metadata updates** and notification system

**DAG Features:**
- Dynamic file discovery from GCS
- Format-based parallel processing
- Data quality validation gates
- Metadata database integration
- Error handling and retry logic

#### Streaming ETL DAG (`streaming_etl_dag.py`)
- **Streaming job management** and monitoring
- **Real-time quality monitoring** with alerting
- **Auto-scaling** based on throughput metrics
- **Pub/Sub infrastructure** management
- **Performance optimization** and cost control

**Streaming Management:**
- Streaming job health monitoring
- Data quality metric collection
- Auto-scaling recommendations
- Cost optimization alerts
- Performance tuning automation

### 4. Metadata Management System

#### Extended Database Schema (`api/app/database.py`)
**New Models:**
- `Dataset`: Core dataset metadata and status tracking
- `DatasetProfile`: Data profiling results and schema information
- `ValidationReport`: Data quality validation reports
- `DataLineage`: Dataset dependency and transformation tracking
- `IngestionJob`: ETL job execution and monitoring
- `DatasetMetrics`: Time-series metrics and performance data

**Key Features:**
- Complete dataset lifecycle tracking
- Data lineage and dependency management
- Processing job monitoring and history
- Quality metrics over time
- Cost and performance analytics

#### Dataset Operations (`api/app/operations/datasets.py`)
- **CRUD operations** for all dataset entities
- **Analytics functions** for project-level insights
- **Lineage graph construction** with configurable depth
- **Quality trend analysis** and drift detection
- **Batch operations** for dataset management

### 5. API Integration (`api/app/routers/`)

#### Dataset Management API (`datasets.py`)
**Endpoints:**
- Dataset CRUD operations
- Profile creation and history
- Validation report management
- Data lineage tracking
- Job monitoring and control
- Analytics and insights

#### File Upload API (`uploads.py`)
**Upload Capabilities:**
- Signed URL generation for large files
- Direct upload for smaller files
- Format validation and size limits
- Automatic ingestion triggering
- Cost and time estimation

**Ingestion Management:**
- ETL pipeline triggering
- Job type selection (Dataflow/Composer)
- Configuration override support
- Status monitoring and webhooks
- Background processing tasks

## Configuration and Setup

### Environment Variables
```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCS_BUCKET=your-data-bucket
BIGQUERY_DATASET=analytics_data

# Database Configuration
DATABASE_URL=postgresql://user:pass@host:5432/db

# Dataflow Configuration
DATAFLOW_TEMPLATE_LOCATION=gs://your-bucket/templates/
TEMP_LOCATION=gs://your-bucket/temp/
STAGING_LOCATION=gs://your-bucket/staging/
```

### Required Dependencies
```bash
# Dataflow pipelines
pip install apache-beam[gcp]==2.52.0
pip install pandas==2.1.3 pyarrow==14.0.1

# Schema inference
pip install scikit-learn==1.3.2
pip install matplotlib==3.8.2 seaborn==0.13.0

# API and database
pip install fastapi uvicorn sqlalchemy
pip install google-cloud-storage google-cloud-bigquery
```

## Usage Examples

### 1. Upload and Process File
```python
# Request upload URL
response = requests.post("/api/v1/upload/request-upload", data={
    "project_id": "my-project",
    "filename": "sales_data.csv",
    "file_size": 1024000,
    "dataset_name": "Q4 Sales Data"
})

upload_url = response.json()["upload_url"]
dataset_id = response.json()["dataset_id"]

# Upload file to signed URL
with open("sales_data.csv", "rb") as f:
    requests.put(upload_url, data=f.read())

# Trigger processing
response = requests.post("/api/v1/upload/trigger-ingestion", json={
    "dataset_id": dataset_id,
    "job_type": "dataflow_batch",
    "job_config": {
        "validation_rules": {
            "required_fields": ["customer_id", "amount"],
            "range_constraints": {
                "amount": {"min": 0, "max": 10000}
            }
        }
    }
})
```

### 2. Monitor Processing
```python
# Get job status
job_id = response.json()["job_id"]
response = requests.get(f"/api/v1/datasets/jobs/{job_id}")
job_status = response.json()["status"]

# Get dataset profile
response = requests.get(f"/api/v1/datasets/{dataset_id}/profiles/latest")
profile = response.json()

# Get validation report
response = requests.get(f"/api/v1/datasets/{dataset_id}/validation-reports/latest")
validation = response.json()
```

### 3. Data Lineage Tracking
```python
# Create lineage relationship
requests.post("/api/v1/datasets/lineage", json={
    "source_dataset_id": "raw_data_id",
    "target_dataset_id": "processed_data_id", 
    "transformation_type": "etl_pipeline",
    "job_id": "dataflow_job_123"
})

# Get lineage graph
response = requests.get(f"/api/v1/datasets/{dataset_id}/lineage/graph?depth=3")
lineage_graph = response.json()
```

## Monitoring and Observability

### Key Metrics
- **Processing throughput** (records/second)
- **Data quality scores** and trends
- **Job success/failure rates**
- **Processing costs** and resource utilization
- **Schema drift** detection and alerts

### Dashboards
- Dataset processing overview
- Data quality trends
- Job performance metrics
- Cost optimization insights
- Lineage visualization

### Alerting
- Data quality threshold violations
- Job failures and retries
- Processing delays and bottlenecks  
- Cost budget overruns
- Schema drift detection

## Security and Compliance

### Data Protection
- **PII detection** and masking capabilities
- **Encryption at rest** in GCS and BigQuery
- **Access controls** with project-based permissions
- **Audit logging** for data access and modifications

### Compliance Features
- Data lineage for compliance reporting
- Validation rule enforcement
- Processing audit trails
- Data retention policies
- Privacy impact assessments

## Performance Optimization

### Cost Optimization
- **Preemptible workers** for batch processing
- **Smart file batching** to reduce job overhead
- **Compression recommendations** based on data profiles
- **Partitioning strategies** for BigQuery tables

### Processing Optimization  
- **Dynamic scaling** based on data volume
- **Format-specific optimizations** (Parquet vs CSV)
- **Parallel processing** for independent datasets
- **Caching strategies** for repeated operations

## Troubleshooting

### Common Issues
1. **File format not supported**: Check supported formats endpoint
2. **Processing job stuck**: Monitor job logs and retry mechanisms
3. **Data quality failures**: Review validation rules and data profiles
4. **Schema drift alerts**: Compare profile versions and update rules
5. **Cost overruns**: Review processing configurations and optimizations

### Debug Endpoints
- `/api/v1/datasets/{id}/jobs` - Job execution history
- `/api/v1/datasets/{id}/metrics` - Processing performance metrics  
- `/api/v1/datasets/{id}/validation-reports` - Data quality history
- `/api/v1/datasets/{id}/profiles` - Schema evolution tracking

## Next Steps
Phase 2 provides a complete data ingestion and ETL foundation. Consider these enhancements:

1. **Advanced ML-based quality detection**
2. **Real-time streaming dashboards**
3. **Automated data cataloging**
4. **Cross-dataset relationship discovery**
5. **Predictive cost optimization**