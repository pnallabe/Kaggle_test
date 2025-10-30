"""
Cloud Composer DAG for batch ETL data ingestion workflow
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowCreateJavaJobOperator, DataflowCreatePythonJobOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateDatasetOperator,
    BigQueryCreateEmptyTableOperator,
    BigQueryCheckOperator,
    BigQueryInsertJobOperator
)
from airflow.providers.google.cloud.operators.gcs import GCSListObjectsOperator
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable


# Default arguments for the DAG
default_args = {
    'owner': 'ai-data-analyst',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Configuration from Airflow Variables
PROJECT_ID = Variable.get("gcp_project_id")
REGION = Variable.get("gcp_region", "us-central1")
GCS_BUCKET = Variable.get("gcs_data_bucket")
BIGQUERY_DATASET = Variable.get("bigquery_dataset", "analytics_data")
DATAFLOW_TEMPLATE_LOCATION = Variable.get("dataflow_template_location")
POSTGRES_CONN_ID = Variable.get("postgres_conn_id", "metadata_db")


def get_files_to_process(**context):
    """Get list of files to process from GCS"""
    from google.cloud import storage
    
    # Get execution date and other context
    execution_date = context['execution_date']
    
    # Initialize storage client
    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET)
    
    # List files in the ingestion folder
    blobs = bucket.list_blobs(prefix='ingestion/')
    
    files_to_process = []
    for blob in blobs:
        # Filter by file extensions and modification time
        if blob.name.endswith(('.csv', '.parquet')):
            # Check if file was modified within the last day
            time_diff = execution_date - blob.time_created.replace(tzinfo=None)
            if time_diff.days <= 1:
                files_to_process.append({
                    'file_path': f'gs://{GCS_BUCKET}/{blob.name}',
                    'file_size': blob.size,
                    'modified_time': blob.updated.isoformat(),
                    'file_format': 'csv' if blob.name.endswith('.csv') else 'parquet'
                })
    
    print(f"Found {len(files_to_process)} files to process")
    
    # Store in XCom for downstream tasks
    return files_to_process


def create_dataset_metadata(**context):
    """Create dataset metadata record"""
    import json
    from datetime import datetime
    
    files_info = context['task_instance'].xcom_pull(task_ids='get_files_to_process')
    execution_date = context['execution_date']
    
    # Generate dataset ID
    dataset_id = f"batch_ingestion_{execution_date.strftime('%Y%m%d_%H%M%S')}"
    
    metadata = {
        'dataset_id': dataset_id,
        'ingestion_type': 'batch',
        'execution_date': execution_date.isoformat(),
        'total_files': len(files_info),
        'file_formats': list(set(f['file_format'] for f in files_info)),
        'total_size_bytes': sum(f['file_size'] for f in files_info),
        'status': 'processing',
        'created_at': datetime.utcnow().isoformat()
    }
    
    print(f"Created metadata for dataset: {dataset_id}")
    return metadata


def prepare_dataflow_config(**context):
    """Prepare Dataflow job configuration"""
    files_info = context['task_instance'].xcom_pull(task_ids='get_files_to_process')
    metadata = context['task_instance'].xcom_pull(task_ids='create_dataset_metadata')
    
    # Group files by format
    csv_files = [f['file_path'] for f in files_info if f['file_format'] == 'csv']
    parquet_files = [f['file_path'] for f in files_info if f['file_format'] == 'parquet']
    
    config = {
        'dataset_id': metadata['dataset_id'],
        'csv_files': csv_files,
        'parquet_files': parquet_files,
        'output_table': f"{PROJECT_ID}:{BIGQUERY_DATASET}.{metadata['dataset_id']}",
        'temp_location': f"gs://{GCS_BUCKET}/temp/dataflow/",
        'validation_rules': {
            'required_fields': [],
            'type_constraints': {},
            'range_constraints': {}
        }
    }
    
    return config


def update_metadata_success(**context):
    """Update metadata on successful completion"""
    metadata = context['task_instance'].xcom_pull(task_ids='create_dataset_metadata')
    
    # This would update the metadata database
    update_query = f"""
    UPDATE datasets 
    SET status = 'completed', 
        completed_at = NOW(),
        processing_time_seconds = EXTRACT(EPOCH FROM (NOW() - created_at))
    WHERE dataset_id = '{metadata['dataset_id']}'
    """
    
    return update_query


def update_metadata_failure(**context):
    """Update metadata on failure"""
    metadata = context['task_instance'].xcom_pull(task_ids='create_dataset_metadata')
    
    update_query = f"""
    UPDATE datasets 
    SET status = 'failed', 
        failed_at = NOW(),
        error_message = 'Pipeline execution failed'
    WHERE dataset_id = '{metadata['dataset_id']}'
    """
    
    return update_query


def notify_completion(**context):
    """Send notification on completion"""
    import json
    
    metadata = context['task_instance'].xcom_pull(task_ids='create_dataset_metadata')
    
    notification_data = {
        'dataset_id': metadata['dataset_id'],
        'status': 'completed',
        'execution_date': context['execution_date'].isoformat(),
        'total_files': metadata['total_files'],
        'processing_duration': 'calculated_duration_here'
    }
    
    print(f"Notification sent for dataset: {metadata['dataset_id']}")
    return notification_data


# Create the DAG
dag = DAG(
    'batch_etl_ingestion',
    default_args=default_args,
    description='Batch ETL pipeline for data ingestion',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    max_active_runs=1,
    tags=['etl', 'batch', 'ingestion']
)

# Task 1: Check for new files in GCS
check_for_files = GCSObjectExistenceSensor(
    task_id='check_for_files',
    bucket=GCS_BUCKET,
    object='ingestion/',
    timeout=300,
    poke_interval=60,
    dag=dag
)

# Task 2: Get list of files to process
get_files_task = PythonOperator(
    task_id='get_files_to_process',
    python_callable=get_files_to_process,
    dag=dag
)

# Task 3: Create dataset metadata
create_metadata_task = PythonOperator(
    task_id='create_dataset_metadata',
    python_callable=create_dataset_metadata,
    dag=dag
)

# Task 4: Insert metadata into PostgreSQL
insert_metadata_task = PostgresOperator(
    task_id='insert_metadata',
    postgres_conn_id=POSTGRES_CONN_ID,
    sql="""
    INSERT INTO datasets (dataset_id, name, description, ingestion_type, status, created_at, file_count, total_size_bytes)
    VALUES (
        '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
        'Batch Ingestion {{ ds }}',
        'Automated batch ingestion pipeline',
        'batch',
        'processing',
        NOW(),
        {{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["total_files"] }},
        {{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["total_size_bytes"] }}
    )
    """,
    dag=dag
)

# Task 5: Prepare Dataflow configuration
prepare_config_task = PythonOperator(
    task_id='prepare_dataflow_config',
    python_callable=prepare_dataflow_config,
    dag=dag
)

# Task 6: Create BigQuery dataset if not exists
create_bq_dataset = BigQueryCreateDatasetOperator(
    task_id='create_bigquery_dataset',
    project_id=PROJECT_ID,
    dataset_id=BIGQUERY_DATASET,
    location=REGION,
    exists_ok=True,
    dag=dag
)

# Task 7: Run CSV Dataflow job
run_csv_dataflow = DataflowCreatePythonJobOperator(
    task_id='run_csv_dataflow',
    py_file=f"gs://{GCS_BUCKET}/dataflow/batch_ingestion_pipeline.py",
    job_name='csv-ingestion-{{ ds_nodash }}-{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
    options={
        'project': PROJECT_ID,
        'region': REGION,
        'temp_location': f"gs://{GCS_BUCKET}/temp/dataflow/",
        'staging_location': f"gs://{GCS_BUCKET}/staging/dataflow/",
        'bucket_name': GCS_BUCKET,
        'file_patterns': 'ingestion/*.csv',
        'output_dataset': BIGQUERY_DATASET,
        'output_table': '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}_csv',
        'dataset_id': '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
        'max_age_hours': '24'
    },
    location=REGION,
    dag=dag
)

# Task 8: Run Parquet Dataflow job
run_parquet_dataflow = DataflowCreatePythonJobOperator(
    task_id='run_parquet_dataflow',
    py_file=f"gs://{GCS_BUCKET}/dataflow/batch_ingestion_pipeline.py",
    job_name='parquet-ingestion-{{ ds_nodash }}-{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
    options={
        'project': PROJECT_ID,
        'region': REGION,
        'temp_location': f"gs://{GCS_BUCKET}/temp/dataflow/",
        'staging_location': f"gs://{GCS_BUCKET}/staging/dataflow/",
        'bucket_name': GCS_BUCKET,
        'file_patterns': 'ingestion/*.parquet',
        'output_dataset': BIGQUERY_DATASET,
        'output_table': '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}_parquet',
        'dataset_id': '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
        'max_age_hours': '24'
    },
    location=REGION,
    dag=dag
)

# Task 9: Merge processed data
merge_data_task = BigQueryInsertJobOperator(
    task_id='merge_processed_data',
    configuration={
        'query': {
            'query': f"""
            CREATE OR REPLACE TABLE `{PROJECT_ID}.{BIGQUERY_DATASET}.{{{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}}}` AS
            SELECT *, 'csv' as source_format FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.{{{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}}}_csv`
            UNION ALL
            SELECT *, 'parquet' as source_format FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.{{{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}}}_parquet`
            """,
            'useLegacySql': False
        }
    },
    location=REGION,
    dag=dag
)

# Task 10: Data quality checks
data_quality_check = BigQueryCheckOperator(
    task_id='data_quality_check',
    sql=f"""
    SELECT COUNT(*) as record_count
    FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.{{{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}}}`
    """,
    use_legacy_sql=False,
    location=REGION,
    dag=dag
)

# Task 11: Update metadata on success
update_success_task = PostgresOperator(
    task_id='update_metadata_success',
    postgres_conn_id=POSTGRES_CONN_ID,
    sql="""
    UPDATE datasets 
    SET status = 'completed', 
        completed_at = NOW(),
        processing_time_seconds = EXTRACT(EPOCH FROM (NOW() - created_at))
    WHERE dataset_id = '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}'
    """,
    dag=dag
)

# Task 12: Update metadata on failure
update_failure_task = PostgresOperator(
    task_id='update_metadata_failure',
    postgres_conn_id=POSTGRES_CONN_ID,
    sql="""
    UPDATE datasets 
    SET status = 'failed', 
        failed_at = NOW(),
        error_message = 'Pipeline execution failed'
    WHERE dataset_id = '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}'
    """,
    trigger_rule=TriggerRule.ONE_FAILED,
    dag=dag
)

# Task 13: Send completion notification
notify_task = SimpleHttpOperator(
    task_id='notify_completion',
    http_conn_id='api_server',
    endpoint='/api/notifications',
    method='POST',
    data={
        'dataset_id': '{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}',
        'status': 'completed',
        'execution_date': '{{ ds }}',
        'message': 'Batch ingestion pipeline completed successfully'
    },
    headers={'Content-Type': 'application/json'},
    dag=dag
)

# Task 14: Cleanup temporary files
cleanup_temp_files = BashOperator(
    task_id='cleanup_temp_files',
    bash_command=f"""
    gsutil -m rm -r gs://{GCS_BUCKET}/temp/dataflow/{{{{ task_instance.xcom_pull(task_ids="create_dataset_metadata")["dataset_id"] }}}}* || true
    """,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag
)

# Define task dependencies
check_for_files >> get_files_task >> create_metadata_task >> insert_metadata_task >> prepare_config_task >> create_bq_dataset

# Parallel processing of different file formats
create_bq_dataset >> [run_csv_dataflow, run_parquet_dataflow] >> merge_data_task >> data_quality_check

# Success and failure paths
data_quality_check >> update_success_task >> notify_task
data_quality_check >> update_failure_task

# Cleanup runs regardless of success/failure
[update_success_task, update_failure_task] >> cleanup_temp_files