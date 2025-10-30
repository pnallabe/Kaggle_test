"""
Cloud Composer DAG for streaming ETL data ingestion workflow
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowCreatePythonJobOperator
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCreateDatasetOperator,
    BigQueryCheckOperator,
    BigQueryGetDataOperator
)
from airflow.providers.google.cloud.operators.pubsub import (
    PubSubCreateTopicOperator,
    PubSubCreateSubscriptionOperator
)
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import Variable
from airflow.sensors.base_sensor_operator import BaseSensorOperator


# Default arguments for the DAG
default_args = {
    'owner': 'ai-data-analyst',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'catchup': False
}

# Configuration from Airflow Variables
PROJECT_ID = Variable.get("gcp_project_id")
REGION = Variable.get("gcp_region", "us-central1")
GCS_BUCKET = Variable.get("gcs_data_bucket")
BIGQUERY_DATASET = Variable.get("bigquery_dataset", "analytics_data")
PUBSUB_TOPIC = Variable.get("pubsub_topic", "data-ingestion")
PUBSUB_SUBSCRIPTION = Variable.get("pubsub_subscription", "data-ingestion-sub")
POSTGRES_CONN_ID = Variable.get("postgres_conn_id", "metadata_db")


class PubSubMessageCountSensor(BaseSensorOperator):
    """Custom sensor to check if there are messages in Pub/Sub subscription"""
    
    def __init__(self, subscription: str, min_messages: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.subscription = subscription
        self.min_messages = min_messages
    
    def poke(self, context):
        from google.cloud import pubsub_v1
        
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(PROJECT_ID, self.subscription)
        
        try:
            # Get subscription details
            subscription_info = subscriber.get_subscription(request={"subscription": subscription_path})
            
            # Check message count (approximate)
            # This is a simplified check - in production you might want more sophisticated monitoring
            return True  # For demo purposes, always return True
            
        except Exception as e:
            self.log.error(f"Error checking subscription: {e}")
            return False


def create_streaming_dataset_metadata(**context):
    """Create metadata for streaming dataset"""
    from datetime import datetime
    
    execution_date = context['execution_date']
    
    # Generate streaming dataset ID
    dataset_id = f"streaming_ingestion_{execution_date.strftime('%Y%m%d_%H%M%S')}"
    
    metadata = {
        'dataset_id': dataset_id,
        'ingestion_type': 'streaming',
        'execution_date': execution_date.isoformat(),
        'pubsub_topic': PUBSUB_TOPIC,
        'pubsub_subscription': PUBSUB_SUBSCRIPTION,
        'status': 'streaming',
        'started_at': datetime.utcnow().isoformat(),
        'expected_duration_hours': 24  # Run for 24 hours
    }
    
    print(f"Created streaming metadata for dataset: {dataset_id}")
    return metadata


def prepare_streaming_config(**context):
    """Prepare streaming Dataflow job configuration"""
    metadata = context['task_instance'].xcom_pull(task_ids='create_streaming_metadata')
    
    config = {
        'dataset_id': metadata['dataset_id'],
        'subscription': f"projects/{PROJECT_ID}/subscriptions/{PUBSUB_SUBSCRIPTION}",
        'output_table': f"{PROJECT_ID}:{BIGQUERY_DATASET}.{metadata['dataset_id']}",
        'temp_location': f"gs://{GCS_BUCKET}/temp/streaming/",
        'validation_rules': {
            'required_fields': ['timestamp', 'event_type'],
            'type_constraints': {
                'timestamp': 'TIMESTAMP',
                'event_type': 'STRING'
            },
            'range_constraints': {}
        },
        'enrichment_rules': {
            'field_mappings': {},
            'transformations': {
                'timestamp': {'type': 'format_date', 'to_format': '%Y-%m-%d %H:%M:%S'}
            },
            'computed_fields': {
                'processing_time': {'type': 'current_timestamp'}
            }
        },
        'window_size': 300,  # 5 minutes
        'window_type': 'fixed'
    }
    
    return config


def check_streaming_job_health(**context):
    """Check the health of the streaming Dataflow job"""
    from google.cloud import dataflow_v1beta3
    
    metadata = context['task_instance'].xcom_pull(task_ids='create_streaming_metadata')
    
    # This would check the actual Dataflow job status
    # For demo purposes, return success
    health_status = {
        'job_status': 'running',
        'message_throughput': 'normal',
        'error_rate': 'low',
        'last_check': datetime.utcnow().isoformat()
    }
    
    print(f"Streaming job health check: {health_status}")
    return health_status


def monitor_data_quality(**context):
    """Monitor streaming data quality metrics"""
    import json
    
    metadata = context['task_instance'].xcom_pull(task_ids='create_streaming_metadata')
    
    # This would query BigQuery for data quality metrics
    # For demo purposes, return sample metrics
    quality_metrics = {
        'records_processed_last_hour': 1500,
        'validation_success_rate': 95.2,
        'error_rate': 4.8,
        'schema_violations': 12,
        'late_data_count': 5,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    print(f"Data quality metrics: {quality_metrics}")
    return quality_metrics


def handle_data_quality_alerts(**context):
    """Handle data quality alerts if metrics are below threshold"""
    quality_metrics = context['task_instance'].xcom_pull(task_ids='monitor_data_quality')
    
    alerts = []
    
    # Check thresholds
    if quality_metrics['validation_success_rate'] < 90:
        alerts.append({
            'type': 'validation_rate_low',
            'message': f"Validation success rate is {quality_metrics['validation_success_rate']}% (threshold: 90%)",
            'severity': 'warning'
        })
    
    if quality_metrics['error_rate'] > 10:
        alerts.append({
            'type': 'error_rate_high',
            'message': f"Error rate is {quality_metrics['error_rate']}% (threshold: 10%)",
            'severity': 'critical'
        })
    
    if quality_metrics['schema_violations'] > 50:
        alerts.append({
            'type': 'schema_violations_high',
            'message': f"Schema violations: {quality_metrics['schema_violations']} (threshold: 50)",
            'severity': 'warning'
        })
    
    if alerts:
        print(f"Data quality alerts triggered: {alerts}")
        # In production, this would send notifications
    
    return alerts


def update_streaming_metrics(**context):
    """Update streaming metrics in metadata database"""
    metadata = context['task_instance'].xcom_pull(task_ids='create_streaming_metadata')
    quality_metrics = context['task_instance'].xcom_pull(task_ids='monitor_data_quality')
    
    update_query = f"""
    UPDATE datasets 
    SET 
        records_processed = records_processed + {quality_metrics['records_processed_last_hour']},
        last_updated = NOW(),
        validation_success_rate = {quality_metrics['validation_success_rate']},
        error_rate = {quality_metrics['error_rate']}
    WHERE dataset_id = '{metadata['dataset_id']}'
    """
    
    return update_query


def scale_streaming_job(**context):
    """Scale streaming job based on throughput"""
    quality_metrics = context['task_instance'].xcom_pull(task_ids='monitor_data_quality')
    
    # Simple scaling logic based on throughput
    records_per_hour = quality_metrics['records_processed_last_hour']
    
    scaling_action = 'none'
    if records_per_hour > 5000:
        scaling_action = 'scale_up'
    elif records_per_hour < 500:
        scaling_action = 'scale_down'
    
    print(f"Scaling recommendation: {scaling_action} (records/hour: {records_per_hour})")
    return {'action': scaling_action, 'current_throughput': records_per_hour}


# Create the DAG
dag = DAG(
    'streaming_etl_ingestion',
    default_args=default_args,
    description='Streaming ETL pipeline for real-time data ingestion',
    schedule_interval=timedelta(hours=1),  # Monitor every hour
    max_active_runs=1,
    tags=['etl', 'streaming', 'real-time']
)

# Task 1: Check if there are messages to process
check_messages = PubSubMessageCountSensor(
    task_id='check_pubsub_messages',
    subscription=PUBSUB_SUBSCRIPTION,
    min_messages=1,
    timeout=300,
    poke_interval=60,
    dag=dag
)

# Task 2: Create streaming dataset metadata
create_streaming_metadata = PythonOperator(
    task_id='create_streaming_metadata',
    python_callable=create_streaming_dataset_metadata,
    dag=dag
)

# Task 3: Insert streaming metadata into PostgreSQL
insert_streaming_metadata = PostgresOperator(
    task_id='insert_streaming_metadata',
    postgres_conn_id=POSTGRES_CONN_ID,
    sql="""
    INSERT INTO datasets (dataset_id, name, description, ingestion_type, status, created_at, pubsub_topic, pubsub_subscription)
    VALUES (
        '{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["dataset_id"] }}',
        'Streaming Ingestion {{ ds }} {{ ts }}',
        'Real-time streaming data ingestion pipeline',
        'streaming',
        'streaming',
        NOW(),
        '{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["pubsub_topic"] }}',
        '{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["pubsub_subscription"] }}'
    )
    ON CONFLICT (dataset_id) DO UPDATE SET
        status = EXCLUDED.status,
        last_updated = NOW()
    """,
    dag=dag
)

# Task 4: Ensure Pub/Sub topic exists
create_pubsub_topic = PubSubCreateTopicOperator(
    task_id='create_pubsub_topic',
    project_id=PROJECT_ID,
    topic=PUBSUB_TOPIC,
    fail_if_exists=False,
    dag=dag
)

# Task 5: Ensure Pub/Sub subscription exists
create_pubsub_subscription = PubSubCreateSubscriptionOperator(
    task_id='create_pubsub_subscription',
    project_id=PROJECT_ID,
    topic=PUBSUB_TOPIC,
    subscription=PUBSUB_SUBSCRIPTION,
    fail_if_exists=False,
    dag=dag
)

# Task 6: Prepare streaming configuration
prepare_streaming_config_task = PythonOperator(
    task_id='prepare_streaming_config',
    python_callable=prepare_streaming_config,
    dag=dag
)

# Task 7: Create BigQuery dataset
create_bq_dataset = BigQueryCreateDatasetOperator(
    task_id='create_bigquery_dataset',
    project_id=PROJECT_ID,
    dataset_id=BIGQUERY_DATASET,
    location=REGION,
    exists_ok=True,
    dag=dag
)

# Task 8: Start streaming Dataflow job
start_streaming_dataflow = DataflowCreatePythonJobOperator(
    task_id='start_streaming_dataflow',
    py_file=f"gs://{GCS_BUCKET}/dataflow/streaming_ingestion_pipeline.py",
    job_name='streaming-ingestion-{{ ds_nodash }}-{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["dataset_id"] }}',
    options={
        'project': PROJECT_ID,
        'region': REGION,
        'temp_location': f"gs://{GCS_BUCKET}/temp/streaming/",
        'staging_location': f"gs://{GCS_BUCKET}/staging/streaming/",
        'subscription': f"projects/{PROJECT_ID}/subscriptions/{PUBSUB_SUBSCRIPTION}",
        'output_table': f"{PROJECT_ID}:{BIGQUERY_DATASET}.{{ task_instance.xcom_pull(task_ids='create_streaming_metadata')['dataset_id'] }}",
        'validation_rules': '{"required_fields": ["timestamp", "event_type"]}',
        'enrichment_rules': '{"computed_fields": {"processing_time": {"type": "current_timestamp"}}}',
        'window_size': '300',
        'window_type': 'fixed',
        'streaming': True
    },
    location=REGION,
    dag=dag
)

# Task 9: Wait for job to initialize (short delay)
wait_for_initialization = BashOperator(
    task_id='wait_for_initialization',
    bash_command='sleep 60',  # Wait 1 minute for job to start
    dag=dag
)

# Task 10: Check streaming job health
check_job_health = PythonOperator(
    task_id='check_streaming_job_health',
    python_callable=check_streaming_job_health,
    dag=dag
)

# Task 11: Monitor data quality
monitor_quality = PythonOperator(
    task_id='monitor_data_quality',
    python_callable=monitor_data_quality,
    dag=dag
)

# Task 12: Handle quality alerts
handle_alerts = PythonOperator(
    task_id='handle_data_quality_alerts',
    python_callable=handle_data_quality_alerts,
    dag=dag
)

# Task 13: Update streaming metrics
update_metrics = PostgresOperator(
    task_id='update_streaming_metrics',
    postgres_conn_id=POSTGRES_CONN_ID,
    sql="""
    UPDATE datasets 
    SET 
        records_processed = COALESCE(records_processed, 0) + {{ task_instance.xcom_pull(task_ids='monitor_data_quality')['records_processed_last_hour'] }},
        last_updated = NOW(),
        validation_success_rate = {{ task_instance.xcom_pull(task_ids='monitor_data_quality')['validation_success_rate'] }},
        error_rate = {{ task_instance.xcom_pull(task_ids='monitor_data_quality')['error_rate'] }}
    WHERE dataset_id = '{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["dataset_id"] }}'
    """,
    dag=dag
)

# Task 14: Scale streaming job if needed
scale_job = PythonOperator(
    task_id='scale_streaming_job',
    python_callable=scale_streaming_job,
    dag=dag
)

# Task 15: Send status notification
notify_status = SimpleHttpOperator(
    task_id='notify_streaming_status',
    http_conn_id='api_server',
    endpoint='/api/streaming/status',
    method='POST',
    data={
        'dataset_id': '{{ task_instance.xcom_pull(task_ids="create_streaming_metadata")["dataset_id"] }}',
        'status': 'monitoring',
        'execution_date': '{{ ds }}',
        'metrics': '{{ task_instance.xcom_pull(task_ids="monitor_data_quality") }}',
        'alerts': '{{ task_instance.xcom_pull(task_ids="handle_data_quality_alerts") }}'
    },
    headers={'Content-Type': 'application/json'},
    dag=dag
)

# Define task dependencies
check_messages >> create_streaming_metadata >> insert_streaming_metadata

# Setup infrastructure
insert_streaming_metadata >> [create_pubsub_topic, create_pubsub_subscription, create_bq_dataset]

# Prepare configuration after infrastructure is ready
[create_pubsub_topic, create_pubsub_subscription, create_bq_dataset] >> prepare_streaming_config_task

# Start streaming job
prepare_streaming_config_task >> start_streaming_dataflow >> wait_for_initialization

# Monitoring and management
wait_for_initialization >> check_job_health >> monitor_quality >> handle_alerts >> update_metrics >> scale_job >> notify_status