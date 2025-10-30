"""
Batch ingestion pipeline for processing multiple files in GCS buckets
"""

import argparse
import logging
import json
from typing import List, Dict, Any
from datetime import datetime, timedelta

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, WorkerOptions
from apache_beam.io.gcp.gcsfilesystem import GCSFileSystem
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
from google.cloud import storage
from google.cloud import bigquery

from ingestion_pipeline import CSVProcessor, ParquetProcessor, FileFormatDetector, MetadataCollector


class FileLister(beam.DoFn):
    """List files in GCS bucket based on patterns"""
    
    def __init__(self, bucket_name: str, file_patterns: List[str], max_age_hours: int = None):
        self.bucket_name = bucket_name
        self.file_patterns = file_patterns
        self.max_age_hours = max_age_hours
    
    def setup(self):
        self.storage_client = storage.Client()
        self.gcs_fs = GCSFileSystem()
    
    def process(self, element):
        """List files matching patterns"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # Calculate cutoff time if max_age_hours is specified
            cutoff_time = None
            if self.max_age_hours:
                cutoff_time = datetime.utcnow() - timedelta(hours=self.max_age_hours)
            
            for pattern in self.file_patterns:
                blobs = bucket.list_blobs(prefix=pattern.replace('*', ''))
                
                for blob in blobs:
                    # Check if file matches pattern
                    if self._matches_pattern(blob.name, pattern):
                        # Check age constraint
                        if cutoff_time and blob.time_created.replace(tzinfo=None) < cutoff_time:
                            continue
                        
                        file_path = f"gs://{self.bucket_name}/{blob.name}"
                        file_info = {
                            'file_path': file_path,
                            'file_size': blob.size,
                            'created_time': blob.time_created.isoformat(),
                            'updated_time': blob.updated.isoformat(),
                            'file_format': FileFormatDetector.detect_format(blob.name)
                        }
                        
                        yield file_info
                        
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            raise
    
    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches pattern (simple wildcard matching)"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)


class FileGrouper(beam.DoFn):
    """Group files by format and processing batch"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
    
    def process(self, element):
        """Group files into processing batches"""
        file_format = element['file_format']
        
        yield beam.pvalue.TaggedOutput(file_format, element)


class BatchProcessor(beam.DoFn):
    """Process files in batches"""
    
    def __init__(self, validation_rules: Dict[str, Any]):
        self.validation_rules = validation_rules
    
    def process(self, files_batch: List[Dict[str, Any]]):
        """Process a batch of files"""
        for file_info in files_batch:
            file_path = file_info['file_path']
            file_format = file_info['file_format']
            
            try:
                if file_format == 'csv':
                    processor = CSVProcessor(self.validation_rules)
                elif file_format == 'parquet':
                    processor = ParquetProcessor(self.validation_rules)
                else:
                    raise ValueError(f"Unsupported format: {file_format}")
                
                processor.setup()
                
                # Process file and yield results
                for record in processor.process(file_path):
                    record['_source_file'] = file_path
                    record['_file_size'] = file_info['file_size']
                    record['_file_created'] = file_info['created_time']
                    yield record
                    
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {str(e)}")
                yield {
                    '_source_file': file_path,
                    '_error': str(e),
                    '_validation_status': 'file_error',
                    '_processed_at': datetime.utcnow().isoformat()
                }


class DatasetStatsCollector(beam.DoFn):
    """Collect statistics about the processed dataset"""
    
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
    
    def process(self, element):
        """Collect dataset-level statistics"""
        stats = {
            'dataset_id': self.dataset_id,
            'record_count': 1,
            'validation_status': element.get('_validation_status', 'unknown'),
            'source_file': element.get('_source_file'),
            'processing_time': datetime.utcnow().isoformat()
        }
        
        yield beam.pvalue.TaggedOutput('data', element)
        yield beam.pvalue.TaggedOutput('stats', stats)


def create_bigquery_schema(sample_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Create BigQuery schema from sample data"""
    if not sample_data:
        return []
    
    # Get all unique fields
    all_fields = set()
    for record in sample_data:
        all_fields.update(record.keys())
    
    schema = []
    for field in sorted(all_fields):
        # Determine field type from samples
        field_type = 'STRING'  # Default
        for record in sample_data:
            if field in record and record[field] is not None:
                value = record[field]
                if isinstance(value, bool):
                    field_type = 'BOOLEAN'
                elif isinstance(value, int):
                    field_type = 'INTEGER'
                elif isinstance(value, float):
                    field_type = 'FLOAT'
                elif isinstance(value, str):
                    # Try to detect datetime
                    try:
                        datetime.fromisoformat(value.replace('Z', '+00:00'))
                        field_type = 'TIMESTAMP'
                    except:
                        field_type = 'STRING'
                break
        
        schema.append({
            'name': field,
            'type': field_type,
            'mode': 'NULLABLE'
        })
    
    return schema


def run_batch_pipeline(argv=None):
    """Run the batch ingestion pipeline"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket_name', required=True, help='GCS bucket name')
    parser.add_argument('--file_patterns', required=True, help='Comma-separated file patterns')
    parser.add_argument('--output_dataset', required=True, help='BigQuery dataset')
    parser.add_argument('--output_table', required=True, help='BigQuery table name')
    parser.add_argument('--dataset_id', required=True, help='Dataset identifier')
    parser.add_argument('--temp_location', required=True, help='GCS temp location')
    parser.add_argument('--project', required=True, help='GCP project ID')
    parser.add_argument('--validation_rules', help='JSON string with validation rules')
    parser.add_argument('--max_age_hours', type=int, help='Maximum file age in hours')
    parser.add_argument('--batch_size', type=int, default=50, help='Files per batch')
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Parse inputs
    file_patterns = [p.strip() for p in known_args.file_patterns.split(',')]
    validation_rules = {}
    if known_args.validation_rules:
        validation_rules = json.loads(known_args.validation_rules)
    
    output_table = f"{known_args.project}:{known_args.output_dataset}.{known_args.output_table}"
    
    # Set up pipeline options
    pipeline_options = PipelineOptions(pipeline_args)
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = known_args.project
    google_cloud_options.temp_location = known_args.temp_location
    google_cloud_options.region = 'us-central1'
    
    worker_options = pipeline_options.view_as(WorkerOptions)
    worker_options.machine_type = 'n1-standard-4'
    worker_options.max_num_workers = 20
    worker_options.autoscaling_algorithm = 'THROUGHPUT_BASED'
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        
        # List files in GCS bucket
        file_list = (
            pipeline
            | 'Start' >> beam.Create(['start'])
            | 'List files' >> beam.ParDo(
                FileLister(
                    known_args.bucket_name,
                    file_patterns,
                    known_args.max_age_hours
                )
            )
        )
        
        # Group files by format
        grouped_files = (
            file_list
            | 'Group by format' >> beam.ParDo(FileGrouper()).with_outputs('csv', 'parquet')
        )
        
        # Process CSV files
        csv_data = None
        if hasattr(grouped_files, 'csv'):
            csv_data = (
                grouped_files.csv
                | 'Batch CSV files' >> beam.BatchElements(
                    min_batch_size=1,
                    max_batch_size=known_args.batch_size
                )
                | 'Process CSV batches' >> beam.ParDo(BatchProcessor(validation_rules))
            )
        
        # Process Parquet files
        parquet_data = None
        if hasattr(grouped_files, 'parquet'):
            parquet_data = (
                grouped_files.parquet
                | 'Batch Parquet files' >> beam.BatchElements(
                    min_batch_size=1,
                    max_batch_size=known_args.batch_size
                )
                | 'Process Parquet batches' >> beam.ParDo(BatchProcessor(validation_rules))
            )
        
        # Combine all processed data
        all_data = []
        if csv_data:
            all_data.append(csv_data)
        if parquet_data:
            all_data.append(parquet_data)
        
        if not all_data:
            logging.warning("No data to process")
            return
        
        combined_data = (
            all_data
            | 'Flatten data' >> beam.Flatten()
        )
        
        # Collect dataset statistics
        outputs = (
            combined_data
            | 'Collect dataset stats' >> beam.ParDo(
                DatasetStatsCollector(known_args.dataset_id)
            ).with_outputs('data', 'stats')
        )
        
        # Write valid data to BigQuery
        valid_data = (
            outputs.data
            | 'Filter valid records' >> beam.Filter(
                lambda x: x.get('_validation_status') == 'valid'
            )
            | 'Clean validation fields' >> beam.Map(
                lambda x: {k: v for k, v in x.items() if not k.startswith('_')}
            )
        )
        
        valid_data | 'Write to BigQuery' >> WriteToBigQuery(
            table=output_table,
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            additional_bq_parameters={
                'timePartitioning': {
                    'type': 'DAY'
                },
                'clustering': {
                    'fields': ['_source_file'] if '_source_file' in validation_rules.get('cluster_fields', []) else []
                }
            }
        )
        
        # Write invalid data to errors table
        invalid_data = (
            outputs.data
            | 'Filter invalid records' >> beam.Filter(
                lambda x: x.get('_validation_status') in ['invalid', 'error', 'file_error']
            )
        )
        
        invalid_data | 'Write errors' >> WriteToBigQuery(
            table=f"{output_table}_errors",
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )
        
        # Aggregate and write processing statistics
        processing_stats = (
            outputs.stats
            | 'Window stats' >> beam.WindowInto(beam.window.GlobalWindows())
            | 'Group stats' >> beam.GroupBy(lambda x: x['dataset_id'])
            | 'Aggregate stats' >> beam.Map(
                lambda x: {
                    'dataset_id': x[0],
                    'total_records': len(list(x[1])),
                    'valid_records': len([s for s in x[1] if s['validation_status'] == 'valid']),
                    'invalid_records': len([s for s in x[1] if s['validation_status'] in ['invalid', 'error']]),
                    'processing_completed_at': datetime.utcnow().isoformat(),
                    'unique_source_files': len(set(s['source_file'] for s in x[1] if s.get('source_file')))
                }
            )
        )
        
        processing_stats | 'Write processing stats' >> WriteToBigQuery(
            table=f"{output_table}_processing_stats",
            schema=[
                {'name': 'dataset_id', 'type': 'STRING', 'mode': 'REQUIRED'},
                {'name': 'total_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'valid_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'invalid_records', 'type': 'INTEGER', 'mode': 'REQUIRED'},
                {'name': 'processing_completed_at', 'type': 'TIMESTAMP', 'mode': 'REQUIRED'},
                {'name': 'unique_source_files', 'type': 'INTEGER', 'mode': 'REQUIRED'}
            ],
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run_batch_pipeline()