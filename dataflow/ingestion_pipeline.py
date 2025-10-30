"""
Apache Beam Dataflow pipeline for CSV and Parquet ingestion to BigQuery
"""

import argparse
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, WorkerOptions, SetupOptions
from apache_beam.io import ReadFromText, WriteToText
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from google.cloud import storage, bigquery
from google.cloud import logging as cloud_logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileFormatDetector:
    """Detect and validate file formats"""
    
    @staticmethod
    def detect_format(file_path: str) -> str:
        """Detect file format from path"""
        if file_path.lower().endswith('.csv'):
            return 'csv'
        elif file_path.lower().endswith('.parquet'):
            return 'parquet'
        elif file_path.lower().endswith('.json'):
            return 'json'
        else:
            raise ValueError(f"Unsupported file format: {file_path}")


class SchemaInferrer:
    """Infer BigQuery schema from data samples"""
    
    @staticmethod
    def pandas_to_bigquery_schema(df: pd.DataFrame) -> List[Dict[str, str]]:
        """Convert pandas DataFrame schema to BigQuery schema"""
        schema = []
        
        for column, dtype in df.dtypes.items():
            bq_type = SchemaInferrer._pandas_to_bq_type(dtype)
            schema.append({
                'name': str(column),
                'type': bq_type,
                'mode': 'NULLABLE'
            })
        
        return schema
    
    @staticmethod
    def _pandas_to_bq_type(pandas_type) -> str:
        """Map pandas types to BigQuery types"""
        type_mapping = {
            'object': 'STRING',
            'int64': 'INTEGER',
            'float64': 'FLOAT',
            'bool': 'BOOLEAN',
            'datetime64[ns]': 'TIMESTAMP',
            'category': 'STRING'
        }
        
        pandas_type_str = str(pandas_type)
        for pd_type, bq_type in type_mapping.items():
            if pd_type in pandas_type_str:
                return bq_type
        
        return 'STRING'  # Default fallback


class DataValidator:
    """Validate data quality and constraints"""
    
    def __init__(self, validation_rules: Dict[str, Any]):
        self.validation_rules = validation_rules
    
    def validate_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single row and add validation metadata"""
        validation_errors = []
        
        # Check required fields
        required_fields = self.validation_rules.get('required_fields', [])
        for field in required_fields:
            if field not in row or row[field] is None or row[field] == '':
                validation_errors.append(f"Missing required field: {field}")
        
        # Check data types
        type_constraints = self.validation_rules.get('type_constraints', {})
        for field, expected_type in type_constraints.items():
            if field in row and row[field] is not None:
                if not self._validate_type(row[field], expected_type):
                    validation_errors.append(f"Invalid type for field {field}: expected {expected_type}")
        
        # Check value ranges
        range_constraints = self.validation_rules.get('range_constraints', {})
        for field, range_config in range_constraints.items():
            if field in row and row[field] is not None:
                value = row[field]
                if isinstance(value, (int, float)):
                    min_val = range_config.get('min')
                    max_val = range_config.get('max')
                    if min_val is not None and value < min_val:
                        validation_errors.append(f"Value {value} below minimum {min_val} for field {field}")
                    if max_val is not None and value > max_val:
                        validation_errors.append(f"Value {value} above maximum {max_val} for field {field}")
        
        # Add validation metadata
        row['_validation_status'] = 'valid' if not validation_errors else 'invalid'
        row['_validation_errors'] = validation_errors
        row['_processed_at'] = datetime.utcnow().isoformat()
        
        return row
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        try:
            if expected_type == 'INTEGER':
                int(value)
                return True
            elif expected_type == 'FLOAT':
                float(value)
                return True
            elif expected_type == 'STRING':
                return isinstance(value, str)
            elif expected_type == 'BOOLEAN':
                return isinstance(value, bool) or str(value).lower() in ['true', 'false', '1', '0']
            else:
                return True
        except (ValueError, TypeError):
            return False


class CSVProcessor(beam.DoFn):
    """Process CSV files"""
    
    def __init__(self, validation_rules: Dict[str, Any]):
        self.validation_rules = validation_rules
        self.validator = None
    
    def setup(self):
        self.validator = DataValidator(self.validation_rules)
    
    def process(self, file_path: str):
        """Process a CSV file"""
        try:
            # Read CSV file from GCS
            df = pd.read_csv(file_path)
            logger.info(f"Processing CSV file: {file_path} with {len(df)} rows")
            
            # Convert to records and validate
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                validated_row = self.validator.validate_row(row_dict)
                yield validated_row
                
        except Exception as e:
            logger.error(f"Error processing CSV file {file_path}: {str(e)}")
            # Yield error record
            yield {
                '_file_path': file_path,
                '_error': str(e),
                '_validation_status': 'error',
                '_processed_at': datetime.utcnow().isoformat()
            }


class ParquetProcessor(beam.DoFn):
    """Process Parquet files"""
    
    def __init__(self, validation_rules: Dict[str, Any]):
        self.validation_rules = validation_rules
        self.validator = None
    
    def setup(self):
        self.validator = DataValidator(self.validation_rules)
    
    def process(self, file_path: str):
        """Process a Parquet file"""
        try:
            # Read Parquet file from GCS
            table = pq.read_table(file_path)
            df = table.to_pandas()
            logger.info(f"Processing Parquet file: {file_path} with {len(df)} rows")
            
            # Convert to records and validate
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                validated_row = self.validator.validate_row(row_dict)
                yield validated_row
                
        except Exception as e:
            logger.error(f"Error processing Parquet file {file_path}: {str(e)}")
            # Yield error record
            yield {
                '_file_path': file_path,
                '_error': str(e),
                '_validation_status': 'error',
                '_processed_at': datetime.utcnow().isoformat()
            }


class MetadataCollector(beam.DoFn):
    """Collect metadata about processed files"""
    
    def process(self, element, file_path: str):
        """Collect metadata for each processed record"""
        metadata = {
            'source_file': file_path,
            'record_count': 1,
            'validation_status': element.get('_validation_status', 'unknown'),
            'processed_at': element.get('_processed_at'),
            'errors': element.get('_validation_errors', [])
        }
        
        yield beam.pvalue.TaggedOutput('data', element)
        yield beam.pvalue.TaggedOutput('metadata', metadata)


def run_pipeline(argv=None):
    """Run the ingestion pipeline"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_path', required=True, help='GCS path to input files')
    parser.add_argument('--output_table', required=True, help='BigQuery output table')
    parser.add_argument('--temp_location', required=True, help='GCS temp location')
    parser.add_argument('--project', required=True, help='GCP project ID')
    parser.add_argument('--validation_rules', help='JSON string with validation rules')
    parser.add_argument('--file_format', default='csv', choices=['csv', 'parquet'], help='Input file format')
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    # Parse validation rules
    validation_rules = {}
    if known_args.validation_rules:
        validation_rules = json.loads(known_args.validation_rules)
    
    # Set up pipeline options
    pipeline_options = PipelineOptions(pipeline_args)
    google_cloud_options = pipeline_options.view_as(GoogleCloudOptions)
    google_cloud_options.project = known_args.project
    google_cloud_options.temp_location = known_args.temp_location
    google_cloud_options.region = 'us-central1'
    
    # Set up worker options
    worker_options = pipeline_options.view_as(WorkerOptions)
    worker_options.machine_type = 'n1-standard-4'
    worker_options.max_num_workers = 10
    
    setup_options = pipeline_options.view_as(SetupOptions)
    setup_options.save_main_session = True
    
    with beam.Pipeline(options=pipeline_options) as pipeline:
        
        # Read file paths (in real implementation, this would be dynamic)
        file_paths = (
            pipeline
            | 'Create file paths' >> beam.Create([known_args.input_path])
        )
        
        # Process files based on format
        if known_args.file_format == 'csv':
            processed_data = (
                file_paths
                | 'Process CSV files' >> beam.ParDo(CSVProcessor(validation_rules))
            )
        else:
            processed_data = (
                file_paths
                | 'Process Parquet files' >> beam.ParDo(ParquetProcessor(validation_rules))
            )
        
        # Collect metadata and split outputs
        outputs = (
            processed_data
            | 'Collect metadata' >> beam.ParDo(
                MetadataCollector(),
                file_path=beam.pvalue.AsSingleton(file_paths)
            ).with_outputs('data', 'metadata')
        )
        
        # Write validated data to BigQuery
        valid_data = (
            outputs.data
            | 'Filter valid records' >> beam.Filter(lambda x: x.get('_validation_status') == 'valid')
            | 'Remove validation fields' >> beam.Map(
                lambda x: {k: v for k, v in x.items() if not k.startswith('_')}
            )
        )
        
        valid_data | 'Write to BigQuery' >> WriteToBigQuery(
            table=known_args.output_table,
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            additional_bq_parameters={
                'timePartitioning': {
                    'type': 'DAY',
                    'field': '_processed_at'
                }
            }
        )
        
        # Write errors to separate table
        error_data = (
            outputs.data
            | 'Filter error records' >> beam.Filter(lambda x: x.get('_validation_status') in ['invalid', 'error'])
        )
        
        error_data | 'Write errors to BigQuery' >> WriteToBigQuery(
            table=f"{known_args.output_table}_errors",
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )
        
        # Aggregate and write metadata
        metadata_summary = (
            outputs.metadata
            | 'Group metadata by file' >> beam.GroupBy(lambda x: x['source_file'])
            | 'Aggregate metadata' >> beam.Map(
                lambda x: {
                    'source_file': x[0],
                    'total_records': sum(item[1]['record_count'] for item in x[1]),
                    'valid_records': sum(1 for item in x[1] if item[1]['validation_status'] == 'valid'),
                    'invalid_records': sum(1 for item in x[1] if item[1]['validation_status'] == 'invalid'),
                    'error_records': sum(1 for item in x[1] if item[1]['validation_status'] == 'error'),
                    'processed_at': datetime.utcnow().isoformat()
                }
            )
        )
        
        metadata_summary | 'Write metadata to BigQuery' >> WriteToBigQuery(
            table=f"{known_args.output_table}_metadata",
            schema='SCHEMA_AUTODETECT',
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            write_disposition=BigQueryDisposition.WRITE_APPEND
        )


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    run_pipeline()